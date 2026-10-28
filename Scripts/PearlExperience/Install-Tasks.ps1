[CmdletBinding()]
param([string]$EvidenceDirectory='')
$ErrorActionPreference='Stop'
$repo=Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$python=Join-Path $repo '.venv\Scripts\python.exe'
$root='D:\Apps\KRig';$pwsh='D:\Apps\PowerShell\7\pwsh.exe'
$names=@('LazyPC-PearlMining','LazyPC-PearlExperience','LazyPC-PearlTuning','LazyPC-PearlMining-Recover','LazyPC-PearlPanel')
foreach($file in @($python,$pwsh,(Join-Path $PSScriptRoot 'payout_experience.py'),(Join-Path $PSScriptRoot 'recover_session.py'),(Join-Path $PSScriptRoot 'Pearl-Panel.ps1'),(Join-Path $root 'Runtime\payout-experience.json'))){
 if(-not(Test-Path -LiteralPath $file)){throw "Required existing installation missing: $file"}
}
foreach($name in $names){if((Get-ScheduledTask -TaskName $name).State -eq 'Running'){throw "Stop the existing task first: $name"}}
foreach($check in @('test_experience.py','test_compute_backend.py','test_tls_transport.py','test_recovery.py','test_process_identity.py')){
 & $python (Join-Path $PSScriptRoot $check)
 if($LASTEXITCODE -ne 0){throw "Safety check failed: $check. Tasks were not changed."}
}
if(-not $EvidenceDirectory){$EvidenceDirectory='D:\AI\Playgrounds\RainbowMiner\'+(Get-Date -Format 'yyyyMMdd-HHmmss')+'-supervisor-install'}
New-Item -ItemType Directory -Path $EvidenceDirectory -Force|Out-Null
foreach($name in $names){Export-ScheduledTask -TaskName $name|Set-Content -LiteralPath (Join-Path $EvidenceDirectory ($name+'.before.xml')) -Encoding UTF8}
$principal=New-ScheduledTaskPrincipal -UserId ([Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive -RunLevel Highest
$settings=New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Hours 50) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
foreach($name in 'LazyPC-PearlMining','LazyPC-PearlExperience','LazyPC-PearlTuning'){
 $arguments='-u "'+(Join-Path $PSScriptRoot 'payout_experience.py')+'"'
 if($name -eq 'LazyPC-PearlTuning'){$arguments+=' --calibrate'}
 $action=New-ScheduledTaskAction -Execute $python -Argument $arguments -WorkingDirectory $root
 Register-ScheduledTask -TaskName $name -Action $action -Principal $principal -Settings $settings -Force -Description 'Versioned one-shot PRL supervisor; original deadline and first threshold; no triggers.'|Out-Null
}
$action=New-ScheduledTaskAction -Execute $python -Argument ('-u "'+(Join-Path $PSScriptRoot 'recover_session.py')+'"') -WorkingDirectory $root
$recoverySettings=New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 3)
Register-ScheduledTask -TaskName 'LazyPC-PearlMining-Recover' -Action $action -Principal $principal -Settings $recoverySettings -Force -Description 'Explicit owned-process stop and power recovery; exact creation-time/image/hash identity; no triggers.'|Out-Null
$action=New-ScheduledTaskAction -Execute $pwsh -Argument ('-NoProfile -STA -File "'+(Join-Path $PSScriptRoot 'Pearl-Panel.ps1')+'"') -WorkingDirectory $root
Register-ScheduledTask -TaskName 'LazyPC-PearlPanel' -Action $action -Principal $principal -Settings $settings -Force -Description 'Versioned Pearl control panel; explicit compute units; on-demand only.'|Out-Null
$oldStart=Join-Path $root 'Start-PearlMining.ps1';$oldPanel=Join-Path $root 'Pearl-Mining-Panel.ps1';$oldRecovery=Join-Path $root 'Stop-And-Recover.ps1'
Copy-Item -LiteralPath $oldStart -Destination (Join-Path $EvidenceDirectory 'Start-PearlMining.before.ps1')
Copy-Item -LiteralPath $oldPanel -Destination (Join-Path $EvidenceDirectory 'Pearl-Mining-Panel.before.ps1')
Copy-Item -LiteralPath $oldRecovery -Destination (Join-Path $EvidenceDirectory 'Stop-And-Recover.before.ps1')
$entry=Join-Path $PSScriptRoot 'Manage-Pearl.ps1'
$wrapper=@"
param([ValidateRange(1,2160)][int]`$Minutes,[switch]`$CheckOnly)
`$ErrorActionPreference='Stop'
if(`$CheckOnly){& '$entry' -Action Status;exit `$LASTEXITCODE}
if(`$PSBoundParameters.ContainsKey('Minutes')){& '$entry' -Action Start -Minutes `$Minutes}else{& '$entry' -Action Start}
"@
[IO.File]::WriteAllText($oldStart,$wrapper,[Text.UTF8Encoding]::new($true))
$wrapper="& '$pwsh' -NoProfile -STA -File '"+(Join-Path $PSScriptRoot 'Pearl-Panel.ps1')+"'"
[IO.File]::WriteAllText($oldPanel,$wrapper,[Text.UTF8Encoding]::new($true))
$wrapper="& '$python' -u '"+(Join-Path $PSScriptRoot 'recover_session.py')+"'`nexit `$LASTEXITCODE"
[IO.File]::WriteAllText($oldRecovery,$wrapper,[Text.UTF8Encoding]::new($true))
$receipt=[ordered]@{InstalledAt=(Get-Date).ToString('o');SourceDirectory=$PSScriptRoot;Python=$python;Tasks=$names;TriggersCreated=0;StartedMining=$false;EvidenceDirectory=$EvidenceDirectory;SourceCommit=(& 'D:\Apps\Git\cmd\git.exe' -C $repo rev-parse HEAD).Trim();Policy='Exact captured handles before forced owned termination. No global process kills, boot triggers, Defender or driver changes.'}
$receipt|ConvertTo-Json -Depth 5|Set-Content -LiteralPath (Join-Path $EvidenceDirectory 'install-result.json') -Encoding UTF8
$receipt|ConvertTo-Json -Depth 5
