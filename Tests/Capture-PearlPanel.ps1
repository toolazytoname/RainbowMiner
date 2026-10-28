[CmdletBinding()]
param([Parameter(Mandatory)][string]$OutputDirectory,[switch]$CloseAfter)
$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
Add-Type @'
using System;
using System.Runtime.InteropServices;
public static class PearlPanelCapture {
 [StructLayout(LayoutKind.Sequential)] public struct Rect {public int Left,Top,Right,Bottom;}
 [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h,out Rect r);
 [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr h,IntPtr dc,uint flags);
 [DllImport("user32.dll")] public static extern bool PostMessage(IntPtr h,uint msg,IntPtr w,IntPtr l);
}
'@
$panelPid=[int](Get-Content -LiteralPath 'D:\Apps\KRig\Runtime\panel-pid.txt' -Raw)
$panel=Get-CimInstance Win32_Process -Filter ('ProcessId='+$panelPid)
if(-not $panel -or $panel.CommandLine -notlike '*RainbowMiner*Pearl-Panel.ps1*'){throw 'Expected owned panel process is not active'}
$process=Get-Process -Id $panelPid
$hwnd=$process.MainWindowHandle
if($hwnd -eq 0){throw 'Owned panel has no window handle'}
$element=[Windows.Automation.AutomationElement]::FromHandle($hwnd)
$controls=$element.FindAll([Windows.Automation.TreeScope]::Descendants,[Windows.Automation.Condition]::TrueCondition)
$rows=@(foreach($control in $controls){try{[pscustomobject]@{Name=$control.Current.Name;Id=$control.Current.AutomationId;Enabled=$control.Current.IsEnabled;Type=$control.Current.ControlType.ProgrammaticName}}catch{}})
New-Item -ItemType Directory -Path $OutputDirectory -Force|Out-Null
$rect=New-Object PearlPanelCapture+Rect
if(-not [PearlPanelCapture]::GetWindowRect($hwnd,[ref]$rect)){throw 'Cannot read owned window bounds'}
$bitmap=New-Object Drawing.Bitmap(($rect.Right-$rect.Left),($rect.Bottom-$rect.Top))
$graphics=[Drawing.Graphics]::FromImage($bitmap);$dc=$graphics.GetHdc()
try{$captured=[PearlPanelCapture]::PrintWindow($hwnd,$dc,2)}finally{$graphics.ReleaseHdc($dc);$graphics.Dispose()}
try{$bitmap.Save((Join-Path $OutputDirectory 'panel.png'),[Drawing.Imaging.ImageFormat]::Png)}finally{$bitmap.Dispose()}
$result=[ordered]@{Time=[datetime]::UtcNow.ToString('o');PanelPid=$panelPid;WindowHandle=[long]$hwnd;WindowTitle=$process.MainWindowTitle;PrintWindow=$captured;Controls=$rows;Image=(Join-Path $OutputDirectory 'panel.png');Scope='Only the owned Pearl panel window; no full-desktop or unrelated app capture.'}
$result|ConvertTo-Json -Depth 5|Set-Content -LiteralPath (Join-Path $OutputDirectory 'panel-capture.json') -Encoding UTF8
if($CloseAfter){[void][PearlPanelCapture]::PostMessage($hwnd,0x10,[IntPtr]::Zero,[IntPtr]::Zero)}
$result|ConvertTo-Json -Depth 5
