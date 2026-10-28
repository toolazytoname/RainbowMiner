[CmdletBinding()]
param([Parameter(Mandatory)][string]$OutputDirectory)
$ErrorActionPreference='Stop'
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
$source=Join-Path (Split-Path $PSScriptRoot) 'Scripts/PearlExperience'
$rt='D:\Apps\KRig\Runtime'
New-Item -ItemType Directory -Path $OutputDirectory -Force|Out-Null
$original=Get-Content -LiteralPath (Join-Path $rt 'session.json') -Raw -Encoding UTF8|ConvertFrom-Json
$deadline=(Get-Content -LiteralPath (Join-Path $rt 'payout-experience.json') -Raw -Encoding UTF8|ConvertFrom-Json).MiningDeadline
if($original.Status -ne 'stopped' -or $original.MinerPid){throw 'Existing owned mining work is active'}
$result=[ordered]@{Time=[datetime]::UtcNow.ToString('o');Passed=$false;OriginalDeadline=$deadline;Scope='Invoke actual owned WinForms Start/Stop buttons; only the new owned source session may be stopped.'}
$started=$false;$stopped=$false
function Button($window,$id){
 $condition=[Windows.Automation.PropertyCondition]::new([Windows.Automation.AutomationElement]::AutomationIdProperty,$id)
 $element=$window.FindFirst([Windows.Automation.TreeScope]::Descendants,$condition)
 if(-not $element -or -not $element.Current.IsEnabled){throw ('Expected enabled owned button: '+$id)}
 [Windows.Automation.InvokePattern]$element.GetCurrentPattern([Windows.Automation.InvokePattern]::Pattern)
}
try{
 $panelPid=[int](Get-Content -LiteralPath (Join-Path $rt 'panel-pid.txt') -Raw)
 $p=Get-CimInstance Win32_Process -Filter ('ProcessId='+$panelPid)
 if(-not $p -or $p.CommandLine -notlike '*RainbowMiner*Pearl-Panel.ps1*'){throw 'Unexpected panel process'}
 $hwnd=(Get-Process -Id $panelPid).MainWindowHandle
 $window=[Windows.Automation.AutomationElement]::FromHandle($hwnd)
 (Button $window 'StartMining').Invoke();$started=$true
 $end=[datetime]::UtcNow.AddSeconds(240)
 do{
  Start-Sleep -Milliseconds 500
  $current=Get-Content -LiteralPath (Join-Path $rt 'session.json') -Raw -Encoding UTF8|ConvertFrom-Json
  if($current.SessionId -ne $original.SessionId -and $current.Status -eq 'running' -and [double]$current.ReportedRate -gt 0){break}
 }while([datetime]::UtcNow -lt $end)
 if($current.SessionId -eq $original.SessionId -or $current.Status -ne 'running' -or $current.ComputeBackend.Kind -ne 'soat' -or [double]$current.ReportedRate -le 0){throw 'Actual panel Start did not produce a positive owned source session'}
 $result.SessionId=$current.SessionId;$result.BeforeStop=$current
 Start-Sleep -Seconds 2
 & (Join-Path $PSScriptRoot 'Capture-PearlPanel.ps1') -OutputDirectory (Join-Path $OutputDirectory 'running')|Out-Null
 (Button $window 'StopMining').Invoke();$stopTime=[datetime]::UtcNow;$end=$stopTime.AddSeconds(35)
 do{
  Start-Sleep -Milliseconds 500
  $after=Get-Content -LiteralPath (Join-Path $rt 'session.json') -Raw -Encoding UTF8|ConvertFrom-Json
  if($after.SessionId -ne $current.SessionId){throw 'Session changed during UI stop test'}
  if($after.Status -eq 'stopped' -and -not $after.MinerPid){break}
 }while([datetime]::UtcNow -lt $end)
 $stopped=$after.Status -eq 'stopped' -and -not $after.MinerPid
 $result.StopSeconds=([datetime]::UtcNow-$stopTime).TotalSeconds;$result.AfterStop=$after
 $finalDeadline=(Get-Content -LiteralPath (Join-Path $rt 'payout-experience.json') -Raw -Encoding UTF8|ConvertFrom-Json).MiningDeadline
 $result.FinalDeadline=$finalDeadline
 $result.Passed=$stopped -and $after.PowerRestored -eq $true -and $after.StopReason -eq 'user_stop' -and $finalDeadline -eq $deadline
 Start-Sleep -Seconds 2
 & (Join-Path $PSScriptRoot 'Capture-PearlPanel.ps1') -OutputDirectory (Join-Path $OutputDirectory 'stopped') -CloseAfter|Out-Null
}catch{$result.Error=$_.Exception.Message}
finally{
 if($started -and -not $stopped){
  $latest=Get-Content -LiteralPath (Join-Path $rt 'session.json') -Raw -Encoding UTF8|ConvertFrom-Json
  if($latest.SessionId -ne $original.SessionId -and $latest.ComputeBackend.Kind -eq 'soat'){
   Start-Process -FilePath 'D:\Apps\PowerShell\7\pwsh.exe' -ArgumentList @('-NoProfile','-File',('"'+(Join-Path $source 'Manage-Pearl.ps1')+'"'),'-Action','Stop') -Wait -WindowStyle Hidden
  }
 }
 $result.EndTime=[datetime]::UtcNow.ToString('o');$result|ConvertTo-Json -Depth 12|Set-Content -LiteralPath (Join-Path $OutputDirectory 'result.json') -Encoding UTF8
}
if(-not $result.Passed){exit 1}
