[CmdletBinding()]
param([string]$WorkDirectory = [IO.Path]::GetTempPath(), [string]$ResultPath = '')
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot
Import-Module (Join-Path $root 'Modules/ForkDonation.psm1') -Force
$checks = [System.Collections.Generic.List[object]]::new()
function Assert-True($Condition,[string]$Message) {if (-not $Condition) {throw $Message}}
function Test-Case([string]$Name,[scriptblock]$Body) {
    try {& $Body;[void]$checks.Add([PSCustomObject]@{Name=$Name;Passed=$true;Error=$null})}
    catch {[void]$checks.Add([PSCustomObject]@{Name=$Name;Passed=$false;Error=$_.Exception.Message})}
}
New-Item -ItemType Directory -Path $WorkDirectory -Force | Out-Null
$temp = Join-Path $WorkDirectory ('rainbow-fork-test-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $temp | Out-Null
$script:policyPath = Join-Path $temp 'policy.json'
$fixture = Get-Content (Join-Path $root 'Data/ForkDonation.json') -Raw -Encoding UTF8
$address = ($fixture | ConvertFrom-Json).Wallets.Kryptex.PRL
function New-Policy { $fixture | ConvertFrom-Json }
function Save-Policy($Value) {[IO.File]::WriteAllText($script:policyPath,($Value | ConvertTo-Json -Depth 20),[Text.UTF8Encoding]::new($false))}
function Read-Plan([int]$Minutes = 24,[string[]]$Pools = @('Kryptex')) {ForkDonation\Get-ForkDonationPlan -DailyMinutes $Minutes -AvailablePools $Pools -Path $script:policyPath}
try {
    Test-Case 'Supplied PRL mainnet address passes Bech32m checksum' {Assert-True (Test-PrlDonationAddress $address) 'Valid address was rejected'}
    Test-Case 'Checksum typo is rejected' {Assert-True (-not (Test-PrlDonationAddress ($address.Substring(0,$address.Length-1)+'q'))) 'Invalid checksum accepted'}
    Test-Case 'Wrong network, mixed case and whitespace are rejected' {
        foreach ($bad in @($address.Replace('prl1','bc1'),('P'+$address.Substring(1)),(' '+$address),($address+' '),'')) {Assert-True (-not (Test-PrlDonationAddress $bad)) 'Invalid network/encoding accepted'}
    }
    Test-Case 'Default policy path works outside the application working directory' {
        Push-Location $temp
        try {$plan=ForkDonation\Get-ForkDonationPlan -DailyMinutes 24 -AvailablePools @('Kryptex');Assert-True ($plan.Enabled -and $plan.Data.Wallets.Kryptex.PRL -ceq $address) 'Module-relative policy path failed'}
        finally {Pop-Location}
    }
    Save-Policy (New-Policy)
    Test-Case '24 minutes/day produces two 12-minute rounds and the declared recipient' {
        $p=Read-Plan;Assert-True ($p.Enabled -and $p.MinutesPerRound -eq 12 -and $p.DelayHours -eq 12 -and $p.DailyMinutes -eq 24 -and $p.Data.Wallets.Kryptex.PRL -ceq $address) 'Wrong fee schedule or recipient'
    }
    Test-Case 'Donate=0 disables support time' {Assert-True (-not (Read-Plan -Minutes 0).Enabled) 'Opt-out ignored'}
    Test-Case 'Small budgets are not silently raised to ten minutes' {Assert-True ((Read-Plan -Minutes 1).MinutesPerRound -eq 1) 'Budget was increased'}
    Test-Case '15-minute budget remains a once-daily round' {Assert-True ((Read-Plan -Minutes 15).DelayHours -eq 24) 'Wrong daily scheduling'}
    Test-Case 'Invalid budgets are disabled' {foreach($n in @(-1,1441)){Assert-True (-not (Read-Plan -Minutes $n).Enabled) 'Invalid budget enabled'}}
    Test-Case 'Unavailable PRL pool never falls back to another recipient' {Assert-True (-not (Read-Plan -Pools @('Zpool')).Enabled) 'Fallback recipient enabled'}
    Test-Case 'Missing policy skips donation' {Assert-True (-not (ForkDonation\Get-ForkDonationPlan -DailyMinutes 24 -AvailablePools @('Kryptex') -Path (Join-Path $temp 'absent.json')).Enabled) 'Missing policy accepted'}
    Test-Case 'Malformed JSON skips donation' {[IO.File]::WriteAllText($script:policyPath,'{bad json');Assert-True (-not (Read-Plan).Enabled) 'Malformed policy accepted'}
    foreach ($case in @('checksum','account','foreign-pool','foreign-wallet','no-default','plain-http','ssl-preference','wrong-symbol','string-enabled','disabled')) {
        Test-Case "Invalid or disabled policy: $case" {
            $d=New-Policy
            switch ($case) {
                'checksum' {$d.Wallets.Kryptex.PRL=$address.Substring(0,$address.Length-1)+'q'}
                'account' {$d.Wallets.Kryptex | Add-Member Email 'test@example.invalid'}
                'foreign-pool' {$d.Pools=@('Zpool')}
                'foreign-wallet' {$d.Wallets.Default | Add-Member BTC 'invalid-test-wallet'}
                'no-default' {$d.Wallets.PSObject.Properties.Remove('Default')}
                'plain-http' {$d.Wallets.Kryptex.SSL=$false}
                'ssl-preference' {$d.Wallets.Kryptex.SSL=1}
                'wrong-symbol' {$d.Wallets.Kryptex.CoinSymbol='BTC'}
                'string-enabled' {$d.Enabled='false'}
                'disabled' {$d.Enabled=$false}
            }
            Save-Policy $d;Assert-True (-not (Read-Plan).Enabled) "Unsafe policy $case accepted"
        }
    }
    Save-Policy (New-Policy)

    # Execute the real core donation transition block with pure local stand-ins for I/O.
    # This does not import Core, detect hardware, start miners, or contact a mining pool.
    $coreText=Get-Content (Join-Path $root 'Modules/Core.psm1') -Raw -Encoding UTF8
    $start=$coreText.IndexOf('    #Activate or deactivate donation')
    $finish=$coreText.IndexOf('    $UserConfig = if ($Session.IsDonationRun)', $start)
    Assert-True ($start -ge 0 -and $finish -gt $start) 'Core transition block was not found'
    $transition=[scriptblock]::Create($coreText.Substring($start,$finish-$start))
    function Get-ForkDonationPlan {param([int]$DailyMinutes,[string[]]$AvailablePools);ForkDonation\Get-ForkDonationPlan -DailyMinutes $DailyMinutes -AvailablePools $AvailablePools -Path $script:policyPath}
    function Write-Log {param([string]$Message,[string]$Level);[void]$script:messages.Add($Message)}
    function Get-LastDrun {$script:Session.Timer.AddHours(-24)}
    function Set-LastDrun($Value) {$Value}
    function Update-WatchdogLevels {param([switch]$Reset)}
    function Get-Algorithm($Value) {$Value}
    function Get-YiiMPDataWindow($Value) {$Value}
    function Invoke-GetUrl {throw 'Network access is forbidden in this test'}
    function Get-ContentByStreamReader {throw 'Legacy donation fallback is forbidden in this test'}
    function Get-Unzip {throw 'Compressed donation fallback is forbidden in this test'}
    $tokens=$null;$parseErrors=$null
    $includeAst=[System.Management.Automation.Language.Parser]::ParseFile((Join-Path $root 'Modules/Include.psm1'),[ref]$tokens,[ref]$parseErrors)
    $payoutFunction=$includeAst.Find({param($node) $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq 'Get-PoolPayoutCurrencies'},$true)
    . ([scriptblock]::Create($payoutFunction.Extent.Text))
    function New-TestSession {
        $script:messages=[System.Collections.Generic.List[string]]::new()
        $Global:AllPools=@{}
        $Global:WatchdogTimers=@{}
        $Global:GlobalPoolFields=@('Worker','Penalty','Algorithm','ExcludeAlgorithm','CoinName','ExcludeCoin','CoinSymbol','CoinSymbolPBM','ExcludeCoinSymbol','MinerName','ExcludeMinerName','FocusWallet','DataWindow','SSL','Wallets','Params','MaxMarginOfError')
        $Global:PauseMiners=[PSCustomObject]@{}
        $Global:PauseMiners | Add-Member -MemberType ScriptMethod -Name Test -Value {return $false}
        $t=[datetime]'2026-10-28T12:00:00'
        $user=[PSCustomObject]@{Donate=24;Algorithm=@('PearlHash');ExcludeAlgorithm=@();ExcludeCoin=@();ExcludeCoinSymbol=@();PoolName=@('Kryptex');ExcludePoolName=@();EnableAlgorithmVariants=$false;MinerName=@('OneZeroMiner');ExcludeMinerName=@();Pools=[PSCustomObject]@{Kryptex=[PSCustomObject]@{PRL='ordinary-user-wallet-do-not-replace';Worker='ordinary-user'};Zpool=[PSCustomObject]@{BTC='ordinary-btc-wallet-do-not-replace';Worker='ordinary-user'}}}
        return @{Config=$user;UserConfig=$null;AvailPools=@('Kryptex','Zpool');Timer=$t;LastDonated=$t.AddHours(-12).AddMinutes(6);RoundCounter=1;IsDonationRun=$false;IsServerDonationRun=$false;ForkDonationReason=$null}
    }
    Test-Case 'Donation round uses PRL recipient and leaves ordinary wallet object unchanged' {
        Save-Policy (New-Policy);$script:Session=New-TestSession;$original=$Session.Config
        & $transition
        Assert-True $Session.IsDonationRun 'Donation did not start'
        Assert-True ($Session.Config.Pools.Kryptex.Wallets.PRL -ceq $address) 'Wrong PRL recipient'
        Assert-True (@($Session.Config.Pools.Zpool.Wallets.PSObject.Properties | Select-Object).Count -eq 0) 'Unexpected fallback wallet'
        Assert-True ($original.Pools.Kryptex.PRL -ceq 'ordinary-user-wallet-do-not-replace') 'Ordinary wallet was changed'
        Assert-True ([Object]::ReferenceEquals($Session.UserConfig,$original)) 'Ordinary configuration snapshot lost'
        Assert-True (($script:messages -join ' ') -match [regex]::Escape($address)) 'Recipient not disclosed in startup log'
    }
    Test-Case 'Real Core pool filter excludes plaintext candidates during PRL support' {
        Save-Policy (New-Policy);$script:Session=New-TestSession;& $transition
        $t=$null;$e=$null;$ast=[System.Management.Automation.Language.Parser]::ParseInput($coreText,[ref]$t,[ref]$e)
        $predicate=$ast.Find({param($node) $node -is [System.Management.Automation.Language.BinaryExpressionAst] -and $node.Extent.Text.Trim() -ceq '$Pool.SSL -or $Session.Config.Pools.$Pool_Name.SSL -ne 2'},$true)
        Assert-True ($null -ne $predicate) 'Core TLS filtering expression was not found'
        $filter=[scriptblock]::Create($predicate.Extent.Text)
        $Pool_Name='Kryptex';$Pool=[PSCustomObject]@{SSL=$false}
        Assert-True (-not (& $filter)) 'Plaintext candidate was allowed'
        $Pool.SSL=$true;Assert-True (& $filter) 'TLS candidate was excluded'
    }
    Test-Case 'Expired donation restores the exact ordinary configuration' {
        Save-Policy (New-Policy);$script:Session=New-TestSession;$original=$Session.Config;& $transition
        $Session.Timer=$Session.Timer.AddMinutes(8);$Global:AllPools=@{};& $transition
        Assert-True (-not $Session.IsDonationRun -and [Object]::ReferenceEquals($Session.Config,$original) -and -not $Session.UserConfig) 'Wallet/configuration was not restored'
    }
    Test-Case 'Donate=0 ends an active support round and restores the ordinary wallet' {
        Save-Policy (New-Policy);$script:Session=New-TestSession;$original=$Session.Config;& $transition
        $Session.Config.Donate=0;$Global:AllPools=@{};& $transition
        Assert-True (-not $Session.IsDonationRun -and [Object]::ReferenceEquals($Session.Config,$original)) 'Opt-out failed to restore ordinary mining'
    }
    Test-Case 'Unavailable donation pool leaves ordinary mining untouched' {
        Save-Policy (New-Policy);$script:Session=New-TestSession;$Session.AvailPools=@('Zpool');$original=$Session.Config;& $transition
        Assert-True (-not $Session.IsDonationRun -and [Object]::ReferenceEquals($Session.Config,$original)) 'Normal mining was diverted'
    }
    Test-Case 'Invalid policy during a round restores user configuration without any network fallback' {
        Save-Policy (New-Policy);$script:Session=New-TestSession;$original=$Session.Config;& $transition
        [IO.File]::WriteAllText($script:policyPath,'{bad json');$Global:AllPools=@{};& $transition
        Assert-True (-not $Session.IsDonationRun -and [Object]::ReferenceEquals($Session.Config,$original)) 'Bad policy did not restore user configuration'
    }
    Test-Case 'Application defaults pause mining and disable upstream automatic updates' {
        function Get-CPUAffinity {param($Value,[switch]$ToHex);'1'}
        function Get-LinuxXAuthority {''}
        $Global:GlobalCPUInfo=[PSCustomObject]@{Cores=1;RealCores=@(0)}
        $defaults=& (Join-Path $root 'Data/ConfigDefault.ps1')
        Assert-True ($defaults.StartPaused -and -not $defaults.EnableAutoUpdate -and -not $defaults.EnableUpdateDuringPause -and -not $defaults.EnableMinerStatus) 'Unexpected automatic startup/update/monitoring default'
    }
    Test-Case 'Startup and installation do not add antivirus exclusions' {
        foreach($name in @('RainbowMiner.ps1','Scripts/Install.ps1')) {
            $s=Get-Content (Join-Path $root $name) -Raw -Encoding UTF8
            Assert-True ($s -notmatch '(?i)Add-MpPreference|Set-MpPreference|DisableRealtimeMonitoring') "Antivirus modification remains in $name"
        }
    }
    Test-Case 'Donation page discloses the same address, opt-out and separate fee layers' {
        $page=Get-Content (Join-Path $root 'web/donate.html') -Raw -Encoding UTF8
        Assert-True ($page.Contains($address) -and $page.Contains('24') -and $page.Contains('0') -and $page.Contains('1.67%')) 'Donation page disclosure does not match the local policy'
    }
    Test-Case 'ZIP updater exits before imports, downloads and file changes' {
        $psi=[Diagnostics.ProcessStartInfo]::new()
        $psi.FileName=(Get-Process -Id $PID).Path
        $psi.Arguments='-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "'+(Join-Path $root 'Updater.ps1')+'"'
        $psi.WorkingDirectory=$root;$psi.UseShellExecute=$false;$psi.RedirectStandardOutput=$true;$psi.RedirectStandardError=$true;$psi.CreateNoWindow=$true
        $child=[Diagnostics.Process]::Start($psi)
        if (-not $child.WaitForExit(15000)) {$child.Kill();throw 'Updater guard timed out'}
        $text=$child.StandardOutput.ReadToEnd()+$child.StandardError.ReadToEnd()
        Assert-True ($child.ExitCode -eq 2 -and $text -match 'disabled for the Xiaotutou fork') 'Updater was not blocked'
        Assert-True (-not (Test-Path (Join-Path $root 'Downloads'))) 'Updater created a download directory'
    }
    Test-Case 'Changed PowerShell files parse without executing hardware/mining code' {
        foreach($name in @('Modules/ForkDonation.psm1','Modules/Core.psm1','Modules/Setup.psm1','RainbowMiner.ps1','Scripts/Install.ps1','Updater.ps1','Data/ConfigDefault.ps1')) {
            $t=$null;$e=$null;[void][System.Management.Automation.Language.Parser]::ParseFile((Join-Path $root $name),[ref]$t,[ref]$e)
            Assert-True (-not $e.Count) ("Syntax errors in ${name}: "+($e.Message -join '; '))
        }
    }
} finally {
    if (Test-Path -LiteralPath $temp) {Remove-Item -LiteralPath $temp -Recurse -Force}
}
$failures=@($checks | Where-Object {-not $_.Passed})
$result=[PSCustomObject]@{Time=[datetime]::UtcNow.ToString('o');PowerShell=$PSVersionTable.PSVersion.ToString();Passed=($checks.Count-$failures.Count);Failed=$failures.Count;Checks=@($checks.ToArray());GPUWorkStarted=$false;NetworkPoolCalls=0}
if($ResultPath){$parent=Split-Path $ResultPath;if($parent){New-Item -ItemType Directory -Path $parent -Force|Out-Null};$result|ConvertTo-Json -Depth 8|Set-Content -LiteralPath $ResultPath -Encoding UTF8}
foreach($item in $checks){Write-Host "$(if($item.Passed){'PASS'}else{'FAIL'}) $($item.Name)$(if($item.Error){': '+$item.Error})"}
Write-Host "PowerShell $($result.PowerShell): $($result.Passed) passed, $($result.Failed) failed. No GPU/miner/pool activity."
if($failures.Count){exit 1}
