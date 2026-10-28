[CmdletBinding()]
param([string]$EvidenceDirectory='')
$ErrorActionPreference='Stop'
$repo=Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$python=Join-Path $repo '.venv\Scripts\python.exe'
$root='D:\Apps\KRig'
foreach($f in @($python,(Join-Path $PSScriptRoot 'payout_experience.py'),(Join-Path $root 'Runtime\payout-experience.json'),(Join-Path $root 'Stop-And-Recover.ps1'))){
 if(-not(Test-Path -LiteralPath $f)){throw "Required existing installation missing: $f"}
}
foreach($name in 'LazyPC-PearlMining','LazyPC-PearlExperience','LazyPC-PearlTuning','LazyPC-PearlMining-Recover'){
 if((Get-ScheduledTask -TaskName $name).State -eq 'Running'){throw "Stop the existing task first: $name"}
}
& $python (Join-Path $PSScriptRoot 'test_experience.py')
if($LASTEXITCODE -ne 0){throw 'Safety tests failed. Tasks were not changed.'}
& $python (Join-Path $PSScriptRoot 'test_tls_transport.py')
if($LASTEXITCODE -ne 0){throw 'Strict TLS tests failed. Tasks were not changed.'}
if(-not $EvidenceDirectory){$EvidenceDirectory='D:\AI\Playgrounds\RainbowMiner\'+(Get-Date -Format 'yyyyMMdd-HHmmss')+'-supervisor-install'}
New-Item -ItemType Directory -Path $EvidenceDirectory -Force | Out-Null
$principal=New-ScheduledTaskPrincipal -UserId ([Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive -RunLevel Highest
$settings=New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Hours 50) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
foreach($name in 'LazyPC-PearlMining','LazyPC-PearlExperience','LazyPC-PearlTuning'){
 Export-ScheduledTask -TaskName $name | Set-Content -LiteralPath (Join-Path $EvidenceDirectory ($name+'.before.xml')) -Encoding UTF8
 $arguments='-u "'+(Join-Path $PSScriptRoot 'payout_experience.py')+'"'
 if($name -eq 'LazyPC-PearlTuning'){$arguments+=' --calibrate'}
 $action=New-ScheduledTaskAction -Execute $python -Argument $arguments -WorkingDirectory $root
 Register-ScheduledTask -TaskName $name -Action $action -Principal $principal -Settings $settings -Force -Description 'Versioned one-shot PRL supervisor; original deadline and first payout threshold; no triggers.' | Out-Null
}
$oldStart=Join-Path $root 'Start-PearlMining.ps1'
Copy-Item -LiteralPath $oldStart -Destination (Join-Path $EvidenceDirectory 'Start-PearlMining.before.ps1')
$entry=Join-Path $PSScriptRoot 'Manage-Pearl.ps1'
$wrapper=@"
param([ValidateRange(1,1440)][int]`$Minutes,[switch]`$CheckOnly)
`$ErrorActionPreference='Stop'
if(`$CheckOnly){& '$entry' -Action Status;exit `$LASTEXITCODE}
if(`$PSBoundParameters.ContainsKey('Minutes')){& '$entry' -Action Start -Minutes `$Minutes}else{& '$entry' -Action Start}
"@
[IO.File]::WriteAllText($oldStart,$wrapper,[Text.UTF8Encoding]::new($true))
$receipt=[ordered]@{InstalledAt=(Get-Date).ToString('o');SourceDirectory=$PSScriptRoot;Python=$python;Tasks=@('LazyPC-PearlMining','LazyPC-PearlExperience','LazyPC-PearlTuning');TriggersCreated=0;StartedMining=$false;EvidenceDirectory=$EvidenceDirectory;SourceCommit=(& 'D:\Apps\Git\cmd\git.exe' -C $repo rev-parse HEAD).Trim()}
$receipt | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $EvidenceDirectory 'install-result.json') -Encoding UTF8
$receipt | ConvertTo-Json -Depth 4
