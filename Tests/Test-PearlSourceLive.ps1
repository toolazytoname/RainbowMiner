[CmdletBinding()]
param(
 [Parameter(Mandatory)][string]$EvidenceDirectory,
 [string]$ExpectedExecutable='D:\Projects\toolazytoname\soat-miner\build\prl3090-large\soat-miner.exe',
 [string]$ExpectedSha256='5157eeda4d5583c4453b30c39a00ca00cdb3d2b0038544bfd9232c7fde67b947',
 [switch]$RequireAccepted
)
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot;$source=Join-Path $root 'Scripts/PearlExperience'
Import-Module (Join-Path $root 'Modules/KRig.psm1') -Force
function Assert-True($Value,[string]$Message){if(-not $Value){throw $Message}}
$s=Get-Content -LiteralPath 'D:\Apps\KRig\Runtime\session.json' -Raw -Encoding UTF8|ConvertFrom-Json
Assert-True ($s.Status -eq 'running' -and $s.ComputeBackend.Kind -eq 'soat') 'No active source-managed session'
Assert-True ($s.ReportedRateUnit -ceq 'T MAC/s' -and [double]$s.ReportedRate -gt 0) 'No positive source rate with exact units'
Assert-True (-not $s.PSObject.Properties['HashrateTHs']) 'Source MAC rate was mislabeled as native TH/s'
Assert-True ($s.ManagementSourceDirectory -ieq $source) 'Unexpected management source directory'
foreach($file in @('pearl_controller.py','payout_experience.py','compute_backend.py','pool_transport.py','tls_relay.py','process_identity.py','recover_session.py','coexist_monitor.py')){
 $recorded=$s.ManagementSourceSha256.PSObject.Properties[$file].Value
 Assert-True ($recorded -and (Get-FileHash -LiteralPath (Join-Path $source $file) -Algorithm SHA256).Hash -ieq $recorded) ('Changed management source: '+$file)
}
$miner=Get-CimInstance Win32_Process -Filter ('ProcessId='+[int]$s.MinerPid)
Assert-True ($null -ne $miner -and $miner.ExecutablePath -ieq $ExpectedExecutable -and [int]$miner.ParentProcessId -eq [int]$s.ControllerPid) 'Unexpected source executable or parent'
Assert-True ((Get-FileHash -LiteralPath $ExpectedExecutable -Algorithm SHA256).Hash -ieq $ExpectedSha256 -and $s.ComputeBackend.Sha256 -ieq $ExpectedSha256) 'Source binary is not the validated build'
$birth=[long]([datetime]$miner.CreationDate).ToUniversalTime().ToFileTimeUtc()
Assert-True ([math]::Abs($birth-[long]$s.MinerIdentity.CreationFileTime) -lt 10) 'Miner creation identity does not match'
$parent=Get-CimInstance Win32_Process -Filter ('ProcessId='+[int]$s.ControllerPid)
Assert-True ($parent -and $parent.CommandLine.Replace('/','\').Contains((Join-Path $source 'payout_experience.py'))) 'Unexpected source supervisor process'
$endpoint=[string]$s.VerifiedTlsRelay.ClientEndpoint
Assert-True ($endpoint -match '^stratum\+tcp://127\.0\.0\.1:(\d+)$') 'Source transport is not loopback-only'
$port=[int]$Matches[1]
Assert-True ($miner.CommandLine -match ('--pool\s+127\.0\.0\.1:'+ $port +'(?:\s|$)') -and $miner.CommandLine -match '--algo\s+pearl-pow(?:\s|$)' -and $miner.CommandLine -match '--device\s+0(?:\s|$)' -and $miner.CommandLine -notmatch '--bench') 'Unexpected source compute command'
$sockets=@(Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction Stop)
Assert-True ($sockets.Count -eq 1 -and $sockets[0].LocalAddress -eq '127.0.0.1') 'Unexpected source relay listener'
$run=[IO.Path]::GetFullPath($s.RunDirectory).TrimEnd('\');$receiptPath=[IO.Path]::GetFullPath($s.VerifiedTlsRelay.Receipt)
Assert-True ($run.StartsWith('D:\AI\Playgrounds\RainbowMiner\',[StringComparison]::OrdinalIgnoreCase) -and $receiptPath.StartsWith($run+'\',[StringComparison]::OrdinalIgnoreCase) -and [IO.Path]::GetFileName($receiptPath) -eq 'tls-status.json') 'Unexpected source run/receipt location'
$tls=Get-Content -LiteralPath $receiptPath -Raw -Encoding UTF8|ConvertFrom-Json
$proof=KRig\Get-KRigSupervisorTlsEvidence -Session $s -Receipt $tls -MinerPid ([int]$miner.ProcessId) -ParentPid ([int]$miner.ParentProcessId) -LocalPort $port -SocketOwnerPid ([int]$sockets[0].OwningProcess)
$log=Join-Path (Split-Path $receiptPath) 'miner.log'
$rows=@(Get-Content -LiteralPath $log -Tail 200 -Encoding UTF8|ForEach-Object {try{$v=$_|ConvertFrom-Json;if($v.PSObject.Properties['rate']){$v}}catch{}})
$sampleMatches=@($rows|Where-Object {$_.uptime_s -eq $s.BackendUptimeSeconds -and $_.backend -ceq 'CUDA' -and $_.unit -ceq 'T MAC/s' -and $_.algo -ceq 'pearl-pow' -and [double]$_.rate -eq [double]$s.ReportedRate -and $_.accepted -eq $s.AcceptedShares -and $_.rejected -eq $s.RejectedShares})
Assert-True ($sampleMatches.Count -ge 1) 'Manager counters do not match an actual source JSON sample'
$headers=@(foreach($file in @($log,(Join-Path (Split-Path $log) 'miner-error.log'))){if(Test-Path -LiteralPath $file){Get-Content -LiteralPath $file -TotalCount 100 -Encoding UTF8}})
$selected=$headers|Where-Object {$_ -match '\[pearl-pow\] 4096x65536 with ampere large s3 fold k64:'}
Assert-True ($selected -and $s.ComputeBackend.Shape -ceq '4096x65536' -and $s.ComputeBackend.Tile -ceq '=ampere large s3 fold k64') 'Validated source configuration was not selected'
if($RequireAccepted){Assert-True ([int]$s.AcceptedShares -gt 0 -and [int]$s.RejectedShares -eq 0) 'No accepted source proof or a rejection is present'}
New-Item -ItemType Directory -Path $EvidenceDirectory -Force|Out-Null
$result=[ordered]@{Time=[datetime]::UtcNow.ToString('o');Passed=$true;PowerShell=$PSVersionTable.PSVersion.ToString();SessionId=$s.SessionId;MinerPid=$s.MinerPid;ControllerPid=$s.ControllerPid;Executable=$miner.ExecutablePath;ExecutableSha256=$ExpectedSha256;Rate=$s.ReportedRate;RateUnit=$s.ReportedRateUnit;Accepted=$s.AcceptedShares;Rejected=$s.RejectedShares;BackendUptimeSeconds=$s.BackendUptimeSeconds;CertificateAndHostnameVerified=$proof.Verified;TlsVersion=$proof.TlsVersion;Scope='Actual source process, creation identity, binary/source hashes, CUDA JSON sample and owned authenticated TLS socket. No separate HTTP API or full upstream web UI claim.';GPUWorkStarted=$false;MinerStarted=$false}
$result|ConvertTo-Json -Depth 5|Set-Content -LiteralPath (Join-Path $EvidenceDirectory 'source-live-result.json') -Encoding UTF8
$result|ConvertTo-Json -Depth 5
