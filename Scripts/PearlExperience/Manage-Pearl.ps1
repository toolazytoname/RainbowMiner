[CmdletBinding()]
param(
 [ValidateSet('Start','Stop','Status')][string]$Action='Status',
 [ValidateRange(1,1440)][int]$Minutes,
 [switch]$NoPanel
)
$ErrorActionPreference='Stop'
$root=if($env:PRL_EXPERIENCE_HOME){$env:PRL_EXPERIENCE_HOME}else{'D:\Apps\KRig'}
$runtime=Join-Path $root 'Runtime'
if($Action -eq 'Status'){
 foreach($name in 'session.json','payout-experience.json'){
  $f=Join-Path $runtime $name
  if(Test-Path -LiteralPath $f){Get-Content -LiteralPath $f -Raw -Encoding UTF8}
 }
 exit 0
}
if($Action -eq 'Stop'){
 Start-ScheduledTask -TaskName 'LazyPC-PearlMining-Recover'
 Write-Host 'Stop requested. Check Status for miner exit and power restoration.'
 exit 0
}
if((Get-ScheduledTask -TaskName 'LazyPC-PearlMining-Recover').State -eq 'Running'){throw 'Stop/recovery is still running.'}
foreach($name in 'LazyPC-PearlMining','LazyPC-PearlExperience','LazyPC-PearlTuning'){
 if((Get-ScheduledTask -TaskName $name).State -eq 'Running'){throw 'A mining session is already active.'}
}
$state=Get-Content -LiteralPath (Join-Path $runtime 'payout-experience.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$deadline=[DateTimeOffset]::Parse($state.MiningDeadline)
if($deadline -le [DateTimeOffset]::Now){throw 'The original mining deadline has expired. This command never renews it.'}
if($PSBoundParameters.ContainsKey('Minutes')){
 $file=Join-Path $root 'mining-config.json'
 $cfg=Get-Content -LiteralPath $file -Raw -Encoding UTF8 | ConvertFrom-Json
 $cfg.default_minutes=$Minutes
 $cfg | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $file -Encoding UTF8
}
Start-ScheduledTask -TaskName 'LazyPC-PearlMining'
if(-not $NoPanel){Start-ScheduledTask -TaskName 'LazyPC-PearlPanel'}
Write-Host 'Started one bounded experience. The original deadline and first payout threshold still apply.'
