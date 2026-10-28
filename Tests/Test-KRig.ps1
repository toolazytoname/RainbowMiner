[CmdletBinding()]
param([string]$ResultPath='')
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot
Import-Module (Join-Path $root 'Modules/KRig.psm1') -Force
$checks=[Collections.Generic.List[object]]::new()
function Assert-True($Condition,[string]$Message) {if(-not $Condition){throw $Message}}
function Test-Case([string]$Name,[scriptblock]$Body) {
    try {& $Body;[void]$checks.Add([pscustomobject]@{Name=$Name;Passed=$true;Error=$null})}
    catch {[void]$checks.Add([pscustomobject]@{Name=$Name;Passed=$false;Error=$_.Exception.Message})}
}
$wallet=(Get-Content (Join-Path $root 'Data/ForkDonation.json') -Raw -Encoding UTF8|ConvertFrom-Json).Wallets.Kryptex.PRL
function New-Args {KRig\Get-KRigArguments -HostName 'prl-hk.kryptex.network' -Port 8048 -Wallet $wallet -Worker Lazy3090 -PciDevices @('01:00') -ApiPort 37400}
function New-ApiFixture { '{"devices":[{"algorithms":[{"hashrate":59000000000000,"shares":{"accepted":11,"rejected":2,"stale":1}}]}]}' | ConvertFrom-Json }
Test-Case 'Explicit PCI, TLS, wallet/worker and loopback API command' {
    $a=New-Args
    Assert-True ($a.Contains('--url stratum+ssl://prl-hk.kryptex.network:8048') -and $a.Contains("--user $wallet/Lazy3090") -and $a.Contains('--devices-pci 01:00.0') -and $a.Contains('--no-rocm --no-intel') -and $a.Contains('--api-host 127.0.0.1 --api-port 37400')) 'Incorrect miner arguments'
    Assert-True ($a -notmatch '(gpu-cclock|gpu-mclock|gpu-coffset|gpu-moffset|gpu-plimit|gpu-fan)') 'Adapter changes GPU tuning'
}
Test-Case 'RainbowMiner port placeholder is preserved literally' {
    $a=KRig\Get-KRigArguments -HostName prl.kryptex.network -Port 8048 -Wallet $wallet -PciDevices @('01:00.0')
    Assert-True ($a.Contains('--api-port $mport')) 'Lost manager port placeholder'
}
foreach($bad in @('not-an-address',($wallet+' '),($wallet.Substring(0,$wallet.Length-1)+'q'))) {
    Test-Case 'Invalid payout address is rejected' {
        $threw=$false;try {KRig\Get-KRigArguments -HostName prl.kryptex.network -Port 8048 -Wallet $bad -PciDevices @('01:00')|Out-Null}catch{$threw=$true};Assert-True $threw 'Accepted invalid wallet'
    }
}
Test-Case 'Foreign pool and plaintext transport are rejected' {
    foreach($hostName in @('evil.example','prl.kryptex.network.evil.example')) {
        $threw=$false;try{KRig\Get-KRigArguments -HostName $hostName -Port 8048 -Wallet $wallet -PciDevices @('01:00')|Out-Null}catch{$threw=$true};Assert-True $threw 'Accepted foreign host'
    }
    $threw=$false;try{KRig\Get-KRigArguments -HostName prl.kryptex.network -Port 7048 -Wallet $wallet -PciDevices @('01:00') -SSL $false|Out-Null}catch{$threw=$true};Assert-True $threw 'Accepted plaintext'
}
Test-Case 'Worker and PCI command injection are rejected' {
    foreach($worker in @('x --wallet other','x"','x`nother')) {
        $threw=$false;try{KRig\Get-KRigArguments -HostName prl.kryptex.network -Port 8048 -Wallet $wallet -Worker $worker -PciDevices @('01:00')|Out-Null}catch{$threw=$true};Assert-True $threw 'Accepted unsafe worker'
    }
    $threw=$false;try{KRig\Get-KRigArguments -HostName prl.kryptex.network -Port 8048 -Wallet $wallet -PciDevices @('all')|Out-Null}catch{$threw=$true};Assert-True $threw 'Unbounded GPU selection accepted'
}
Test-Case 'Native API hashrate is not multiplied again' {
    $r=KRig\Get-KRigApiSummary -Data (New-ApiFixture)
    Assert-True ($r.Hashrate -eq 59000000000000 -and $r.Accepted -eq 11 -and $r.Rejected -eq 2 -and $r.Stale -eq 1) 'Bad rate/share conversion'
}
Test-Case 'Multiple GPU counters are summed once' {
    $d=New-ApiFixture;$d.devices=@($d.devices[0],$d.devices[0]);$r=KRig\Get-KRigApiSummary -Data $d
    Assert-True ($r.Hashrate -eq 118000000000000 -and $r.Accepted -eq 22) 'Bad multi-GPU aggregation'
}
Test-Case 'Malformed, missing and non-finite API values fail closed' {
    foreach($bad in @($null,-1,'NaN','Infinity','bad')) {
        $d=New-ApiFixture;$d.devices[0].algorithms[0].hashrate=$bad
        $threw=$false;try{KRig\Get-KRigApiSummary -Data $d|Out-Null}catch{$threw=$true};Assert-True $threw 'Invalid rate accepted'
    }
    $d=New-ApiFixture;$d.devices[0].algorithms[0].shares.accepted=1.5
    $threw=$false;try{KRig\Get-KRigApiSummary -Data $d|Out-Null}catch{$threw=$true};Assert-True $threw 'Fractional share count accepted'
}
Test-Case 'A different reported coin is rejected' {
    $d=New-ApiFixture;$d.devices[0].algorithms[0]|Add-Member name quantus
    $threw=$false;try{KRig\Get-KRigApiSummary -Data $d|Out-Null}catch{$threw=$true};Assert-True $threw 'Different coin accepted'
}
Test-Case 'Changed adapter files parse' {
    foreach($name in @('Modules/KRig.psm1','Miners/KRig.ps1','Modules/MinerAPIs.psm1')) {
        $tokens=$null;$errors=$null;[void][Management.Automation.Language.Parser]::ParseFile((Join-Path $root $name),[ref]$tokens,[ref]$errors)
        Assert-True (-not $errors.Count) ($errors.Message -join '; ')
    }
}
Test-Case 'The actual miner definition emits a safe PRL launch specification' {
    if($PSVersionTable.PSVersion.Major -lt 6){$script:IsWindows=$true;$script:IsLinux=$false}
    $Global:DeviceCache=[pscustomobject]@{DevicesByTypes=[pscustomobject]@{NVIDIA=@([pscustomobject]@{Type='GPU';Model='RTX3090';Name='GPU#00';Index=0;BusId='01:00'})}}
    $Global:StatsCache=[pscustomobject]@{}
    function Get-Algorithm($Name){'PearlHash'}
    function Get-PoolAlgorithmKeys {param($Pools,$Algorithm,$Model);'PearlHash'}
    function Write-Log {param($Level,$Message);throw $Message}
    $pools=[pscustomobject]@{PearlHash=[pscustomobject]@{Host='prl-hk.kryptex.network';Port=8048;SSL=$true;Wallet=$wallet;Worker='Lazy3090';Pass='x'}}
    $text=Get-Content (Join-Path $root 'Miners/KRig.ps1') -Raw -Encoding UTF8
    $block=[scriptblock]::Create((($text -replace '^using module[^\r\n]+[\r\n]+','') -replace '(?m)^Import-Module[^\r\n]+[\r\n]+',''))
    $items=@(& $block -Name KRig -Pools $pools -InfoOnly $false)
    Assert-True ($items.Count -eq 1 -and $items[0].API -eq 'KRig' -and $items[0].DevFee -eq 0 -and $items[0].Arguments.Contains('--devices-pci 01:00.0') -and $items[0].Uri.EndsWith('krig-miner-1.5.12-win-x64.zip')) 'Definition did not produce expected launch spec'
    $pools.PearlHash.SSL=$false
    Assert-True (@(& $block -Name KRig -Pools $pools -InfoOnly $false).Count -eq 0) 'Definition included a plaintext pool'
}
Test-Case 'The actual API class updates rates and shares through loopback only' {
    $text=Get-Content (Join-Path $root 'Modules/MinerAPIs.psm1') -Raw -Encoding UTF8
    $tokens=$null;$errors=$null;$ast=[Management.Automation.Language.Parser]::ParseInput($text,[ref]$tokens,[ref]$errors)
    $node=$ast.Find({param($n)$n -is [Management.Automation.Language.TypeDefinitionAst] -and $n.Name -eq 'KRig'},$true)
    Assert-True ($null -ne $node) 'Missing actual KRig class'
    $stub=@'
enum MinerStatus {Running;Idle}
class Miner {
    [string]$Name;[int]$Port;[string[]]$Algorithm;[object]$LastRates;[object]$LastShares;[int]$Cleanups
    [MinerStatus]GetStatus(){return [MinerStatus]::Running}
    UpdateShares([int]$Index,[double]$Accepted,[double]$Rejected,[double]$Stale){$this.LastShares=@($Accepted,$Rejected,$Stale)}
    AddMinerData([string]$Line,[object]$Rates,[object]$Device,[double]$Power){$this.LastRates=$Rates}
    CleanupMinerData(){$this.Cleanups++}
}
'@
    Invoke-Expression ($stub+"`n"+$node.Extent.Text)
    function Invoke-GetUrl {param($Url,$Timeout,[switch]$ForceHttpClient);Assert-True ($Url -ceq 'http://127.0.0.1:37400/') 'API exposed outside loopback';New-ApiFixture}
    function Write-Log {param($Level,$Message);throw $Message}
    $api=New-Object -TypeName KRig;$api.Name='fixture';$api.Port=37400;$api.Algorithm=@('PearlHash');$api.UpdateMinerData()
    Assert-True ($api.LastRates.PearlHash -eq 59000000000000 -and $api.LastShares[0] -eq 11 -and $api.LastShares[1] -eq 2 -and $api.LastShares[2] -eq 1 -and $api.Cleanups -eq 1) 'Actual API class did not update counters'
}
Test-Case 'Real algorithm database and pool-key helper produce the KRig launch specification' {
    $db=Get-Content (Join-Path $root 'Data/algorithms.json') -Raw -Encoding UTF8 | ConvertFrom-Json
    $map=@{};foreach($property in $db.PSObject.Properties){$map[$property.Name]=$property.Value}
    $Session=@{GlobalAlgorithms=$map}
    foreach($item in @(@('Modules/Include.psm1','Get-Algorithm'),@('Modules/MinersLib.psm1','Get-PoolAlgorithmKeys'))) {
        $tokens=$null;$errors=$null
        $ast=[Management.Automation.Language.Parser]::ParseFile((Join-Path $root $item[0]),[ref]$tokens,[ref]$errors)
        $wanted=$item[1]
        $node=$ast.Find({param($n)$n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -eq $wanted},$true)
        Assert-True ($null -ne $node) 'Actual mapping helper is missing'
        Invoke-Expression $node.Extent.Text
    }
    Assert-True ((Get-Algorithm 'pearlhash') -ceq 'PearlHash') 'Actual algorithm database maps Pearl incorrectly'
    $Global:DeviceCache=[pscustomobject]@{DevicesByTypes=[pscustomobject]@{NVIDIA=@([pscustomobject]@{Type='GPU';Model='RTX3090';Name='GPU#00';Index=0;BusId='01:00'})}}
    $Global:StatsCache=[pscustomobject]@{}
    if($PSVersionTable.PSVersion.Major -lt 6){$script:IsWindows=$true}
    $pools=[pscustomobject]@{PearlHash=[pscustomobject]@{Host='prl-hk.kryptex.network';Port=8048;SSL=$true;Wallet=$wallet;Worker='Lazy3090';Pass='x'}}
    $keys=@(Get-PoolAlgorithmKeys -Pools $pools -Algorithm (Get-Algorithm pearlhash) -Model RTX3090)
    Assert-True ($keys -contains 'PearlHash' -and $keys -contains 'PearlHash-GPU') 'Actual pool key enumeration is incompatible'
    $text=Get-Content (Join-Path $root 'Miners/KRig.ps1') -Raw -Encoding UTF8
    $block=[scriptblock]::Create((($text -replace '^using module[^\r\n]+[\r\n]+','') -replace '(?m)^Import-Module[^\r\n]+[\r\n]+',''))
    $items=@(& $block -Name KRig -Pools $pools -InfoOnly $false)
    Assert-True ($items.Count -eq 1 -and $items[0].API -eq 'KRig' -and $items[0].HashRates.PSObject.Properties.Name -contains 'PearlHash') 'Definition is incompatible with actual algorithm/pool mapping'
}
$failed=@($checks|Where-Object {-not $_.Passed})
$result=[pscustomobject]@{Time=[datetime]::UtcNow.ToString('o');PowerShell=$PSVersionTable.PSVersion.ToString();Passed=$checks.Count-$failed.Count;Failed=$failed.Count;Checks=@($checks.ToArray());GPUWorkStarted=$false;PoolCalls=0;MinerStarted=$false}
if($ResultPath){$result|ConvertTo-Json -Depth 7|Set-Content -LiteralPath $ResultPath -Encoding UTF8}
$checks|ForEach-Object {Write-Host "$(if($_.Passed){'PASS'}else{'FAIL'}) $($_.Name) $($_.Error)"}
Write-Host "$($result.Passed) passed, $($result.Failed) failed. No GPU/miner/network work."
if($failed.Count){exit 1}
