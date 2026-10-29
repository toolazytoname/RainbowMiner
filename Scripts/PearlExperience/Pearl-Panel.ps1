Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
[Windows.Forms.Application]::EnableVisualStyles()
$root='D:\Apps\KRig';$rt=Join-Path $root 'Runtime';$manager=Join-Path $PSScriptRoot 'Manage-Pearl.ps1'
$form=New-Object Windows.Forms.Form
$form.Text='珍珠挖矿控制台';$form.ClientSize=New-Object Drawing.Size(650,475);$form.StartPosition='CenterScreen';$form.FormBorderStyle='FixedDialog';$form.MaximizeBox=$false
$form.Font=New-Object Drawing.Font('Microsoft YaHei UI',10)
$form.BackColor=[Drawing.Color]::FromArgb(247,248,250)
function LabelAt($text,$x,$y,$width,$height){$l=New-Object Windows.Forms.Label;$l.Text=$text;$l.Location=New-Object Drawing.Point($x,$y);$l.Size=New-Object Drawing.Size($width,$height);$form.Controls.Add($l);return $l}
$title=LabelAt '珍珠挖矿' 25 20 400 40;$title.Font=New-Object Drawing.Font('Microsoft YaHei UI',21,[Drawing.FontStyle]::Bold)
$sub=LabelAt 'RTX 3090 · 本地 GPU · 手动启停' 27 68 570 24;$sub.ForeColor=[Drawing.Color]::DimGray
$status=LabelAt '正在读取状态…' 27 108 590 30;$status.Name='MiningStatus';$status.Font=New-Object Drawing.Font('Microsoft YaHei UI',13,[Drawing.FontStyle]::Bold)
$phase=LabelAt '' 27 143 590 30;$phase.Name='MiningPhase'
$metrics=LabelAt '' 27 184 590 85;$metrics.Name='MiningMetrics';$metrics.Font=New-Object Drawing.Font('Microsoft YaHei UI',11)
$durationLabel=LabelAt '单次运行时限' 27 283 115 28
$duration=New-Object Windows.Forms.ComboBox;$duration.DropDownStyle='DropDownList';$duration.Location=New-Object Drawing.Point(150,280);$duration.Size=New-Object Drawing.Size(120,28)
$durationMinutes=[Collections.Generic.List[int]]::new();foreach($value in @(240,480,720,1440)){$durationMinutes.Add($value)}
[void]$duration.Items.AddRange(@('4 小时','8 小时','12 小时','24 小时'));$duration.SelectedIndex=1;$form.Controls.Add($duration)
try{$current=Get-Content -LiteralPath (Join-Path $root 'mining-config.json') -Raw -Encoding UTF8|ConvertFrom-Json;$minutes=[int]$current.default_minutes;$idx=$durationMinutes.IndexOf($minutes);if($idx -lt 0 -and $minutes -ge 1 -and $minutes -le 2160){$durationMinutes.Add($minutes);[void]$duration.Items.Add(([string]$minutes+' 分钟'));$idx=$durationMinutes.Count-1};if($idx -ge 0){$duration.SelectedIndex=$idx}}catch{}
function ButtonAt($text,$name,$x,$y,$width){$b=New-Object Windows.Forms.Button;$b.Text=$text;$b.Name=$name;$b.Location=New-Object Drawing.Point($x,$y);$b.Size=New-Object Drawing.Size($width,42);$form.Controls.Add($b);return $b}
$start=ButtonAt '开始挖矿' 'StartMining' 27 325 180;$start.BackColor=[Drawing.Color]::FromArgb(30,95,170);$start.ForeColor=[Drawing.Color]::White;$start.FlatStyle='Flat'
$stop=ButtonAt '停止并恢复功率' 'StopMining' 222 325 190
$report=ButtonAt '查看运行记录' 'ViewReport' 427 325 195
$pool=ButtonAt '打开矿池收益页' 'OpenPool' 27 383 180
$copy=ButtonAt '复制公开收款地址' 'CopyAddress' 222 383 190
$help=ButtonAt '操作说明' 'OpenHelp' 427 383 195
$foot=LabelAt '关闭本窗口不会停止后台挖矿。停止请点按钮；不随开机自动启动。' 27 442 600 23;$foot.Font=New-Object Drawing.Font('Microsoft YaHei UI',9);$foot.ForeColor=[Drawing.Color]::DimGray
$start.Add_Click({try{
 $minutes=[int]($durationMinutes[$duration.SelectedIndex])
 $job=Start-Process -FilePath 'D:\Apps\PowerShell\7\pwsh.exe' -ArgumentList @('-NoProfile','-File',('"'+$manager+'"'),'-Action','Start','-Minutes',[string]$minutes,'-NoPanel') -WindowStyle Hidden -PassThru -Wait
 if($job.ExitCode -ne 0){throw 'Start was refused. Check the current task and original deadline.'}
 $status.Text='正在启动…'
}catch{[Windows.Forms.MessageBox]::Show($_.Exception.Message,'启动失败')|Out-Null}})
$stop.Add_Click({try{
 $job=Start-Process -FilePath 'D:\Apps\PowerShell\7\pwsh.exe' -ArgumentList @('-NoProfile','-File',('"'+$manager+'"'),'-Action','Stop') -WindowStyle Hidden -PassThru -Wait
 if($job.ExitCode -ne 0){throw 'Stop request was not accepted.'}
 $status.Text='正在停止并恢复原功率…'
}catch{[Windows.Forms.MessageBox]::Show($_.Exception.Message,'停止失败')|Out-Null}})
$pool.Add_Click({Start-Process 'https://pool.kryptex.com/prl'})
$copy.Add_Click({$c=Get-Content -LiteralPath (Join-Path $root 'mining-config.json') -Raw -Encoding UTF8|ConvertFrom-Json;[Windows.Forms.Clipboard]::SetText([string]$c.wallet)})
$help.Add_Click({Start-Process 'D:\Data\Learning\Materials\Pearl体验\02-挖矿启停与查看收益.txt'})
$report.Add_Click({try{$s=Get-Content -LiteralPath (Join-Path $rt 'session.json') -Raw -Encoding UTF8|ConvertFrom-Json;if(Test-Path -LiteralPath $s.RunDirectory){Start-Process explorer.exe -ArgumentList ('"'+$s.RunDirectory+'"')}}catch{}})
$timer=New-Object Windows.Forms.Timer;$timer.Interval=2000
$timer.Add_Tick({try{
 if(-not(Test-Path -LiteralPath (Join-Path $rt 'session.json'))){return}
 $s=Get-Content -LiteralPath (Join-Path $rt 'session.json') -Raw -Encoding UTF8|ConvertFrom-Json
 $live=$s.Status -in @('starting','running','calibrating','cooling')
 $recovering=(Get-ScheduledTask -TaskName 'LazyPC-PearlMining-Recover').State -eq 'Running'
 $payout=$null;$waiting=$false
 if(Test-Path -LiteralPath (Join-Path $rt 'payout-experience.json')){$payout=Get-Content -LiteralPath (Join-Path $rt 'payout-experience.json') -Raw -Encoding UTF8|ConvertFrom-Json;$waiting=$payout.Phase -eq 'waiting_for_pool_payout'}
 $busy=@(Get-ScheduledTask -TaskName 'LazyPC-PearlMining','LazyPC-PearlExperience','LazyPC-PearlTuning'|Where-Object {$_.State -eq 'Running'}).Count -gt 0
 $start.Enabled=(-not $live -and -not $recovering -and -not $busy -and $s.Status -ne 'stop-failed');$duration.Enabled=$start.Enabled;$stop.Enabled=($live -or $busy -or $waiting -or $s.Status -eq 'stop-failed')
 $report.Enabled=($s.RunDirectory -and (Test-Path -LiteralPath $s.RunDirectory))
 $backend=if($s.ComputeBackend.Kind -eq 'soat'){'开源 CUDA 内核'}elseif($s.ComputeBackend.Kind -eq 'krig'){'KRig'}else{'历史记录'}
 $sub.Text='RTX 3090 · '+$backend+' · 手动启停'

 $names=@{starting='正在启动';running='正在挖矿';calibrating='正在对比功率';cooling='正在冷却';stopped='已停止';'stop-failed'='停止未完成'}
 $status.Text=$names[$s.Status];if(-not $status.Text){$status.Text=[string]$s.Status}
 $status.ForeColor=if($s.Status -eq 'stopped'){[Drawing.Color]::DimGray}else{[Drawing.Color]::FromArgb(25,110,60)}
 if($s.Phase){$phase.Text=([string]$s.Phase -replace '^profile-(\d+)W$','$1 W 稳态测试' -replace '^selected-profile$','日常挖矿')}else{$phase.Text=''}
 if($s.Status -eq 'stopped'){$reasons=@{user_stop='收到停止请求';completed='本轮时限结束';manual_recovery='已手动恢复';core_temperature_guard='核心温度保护';hotspot_temperature_guard='热点温度保护';memory_temperature_guard='显存温度保护';external_power_limit_change='外部修改功率';other_gpu_workload='已为其他 GPU 任务让路';other_gpu_workload_during_cooldown='冷却时检测到其他 GPU 任务';other_gpu_workload_before_start='显卡正被其他任务使用'};$why=$reasons[$s.StopReason];if(-not $why){$why=[string]$s.StopReason};$restore=if($s.PowerRestored){'已恢复原功率'}else{'保留外部功率，请查看记录'};$phase.Text=$why+'；'+$restore}
 $g=$s.LastTelemetry
 $shownRate=if($s.Status -in @('cooling','stopped')){0}elseif($s.PSObject.Properties['ReportedRate']){$s.ReportedRate}else{$s.HashrateTHs}
 $unit=if($s.ReportedRateUnit){[string]$s.ReportedRateUnit}else{'TH/s'}
 if($g){
  $metrics.Text=('核心 {0}℃    热点 {1}℃    显存 {2}℃    （最近记录）' -f $g.Temperature,$g.Hotspot,$g.MemoryJunction)+"`r`n"+('显卡 {0:N0}W / 上限 {1:N0}W    算力 {2} {3}' -f $g.Power,$g.PowerLimit,$shownRate,$unit)+"`r`n"+$(if($s.ComputeBackend.Kind -eq 'soat'){('本轮结果：已接受 {0}    失败/未提交 {1}' -f $s.AcceptedShares,$s.RejectedShares)}else{('本轮份额：已接受 {0}    已拒绝 {1}' -f $s.AcceptedShares,$s.RejectedShares)})
 }
 if($s.Status -eq 'running' -and $s.PlannedStop){$phase.Text='本轮计划停止：'+([datetimeoffset]::Parse($s.PlannedStop).LocalDateTime.ToString('MM-dd HH:mm'))}
 if($s.Status -eq 'cooling'){$phase.Text=[string]$s.Phase+'；等待温度稳定后自动继续'}
 if($waiting -and -not $live){$status.Text='显卡已停止，等待矿池打款';$phase.Text='后台只查询公开矿池状态；可点停止结束查询'}
 if($s.Status -eq 'stop-failed'){$status.ForeColor=[Drawing.Color]::Firebrick;$phase.Text='本轮进程尚未确认退出；保留低功率，请查看运行记录'}
 if(-not $live -and (Test-Path -LiteralPath (Join-Path $rt 'last-start-error.json'))){$e=Get-Content -LiteralPath (Join-Path $rt 'last-start-error.json') -Raw -Encoding UTF8|ConvertFrom-Json;if([datetimeoffset]::Parse($e.Time) -gt [datetimeoffset]::Parse($s.StartTime)){$status.Text='启动未进行';$phase.Text=if($e.Reason -like '*GPU is busy*'){'显卡正被其他任务占用，请先结束GPU任务再开始'}else{[string]$e.Reason}}}
}catch{$status.Text='状态读取失败';$start.Enabled=$false;$stop.Enabled=$true;($_|Out-String)+$_.ScriptStackTrace|Set-Content -LiteralPath (Join-Path $rt 'panel-refresh-error.txt') -Encoding UTF8}})
$form.Add_Shown({$PID|Set-Content -LiteralPath 'D:\Apps\KRig\Runtime\panel-pid.txt' -Encoding ascii;$timer.Start()});$form.Add_FormClosed({$timer.Stop();$timer.Dispose()})
[void]$form.ShowDialog()
