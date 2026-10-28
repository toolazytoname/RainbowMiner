[CmdletBinding()]
param(
 [ValidateRange(1024,65535)][int]$ApiPort=18490,
 [Parameter(Mandatory)][string]$EvidenceDirectory,
 [string]$ExpectedExecutable='D:\Apps\KRig\1.5.12\krig-miner.exe',
 [string]$ExpectedSha256='61fc4ff4fa111a641f3d70345ff74d8620ab16db12319f29ed89791e9034f22f'
)
$ErrorActionPreference='Stop'
$ExpectedExecutable=[IO.Path]::GetFullPath($ExpectedExecutable)
$root=Split-Path $PSScriptRoot
Import-Module (Join-Path $root 'Modules/KRig.psm1') -Force
function Assert-True($Value,[string]$Message){if(-not $Value){throw $Message}}
# Read-only: a separately authorized, guarded backend must already be running.
$listeners=@(Get-NetTCPConnection -LocalPort $ApiPort -State Listen -ErrorAction Stop)
Assert-True ($listeners.Count -ge 1) 'No active KRig API listener'
Assert-True (@($listeners|Where-Object {$_.LocalAddress -ne '127.0.0.1'}).Count -eq 0) 'KRig API is not loopback-only'
$ownerIds=@($listeners.OwningProcess|Select-Object -Unique)
Assert-True ($ownerIds.Count -eq 1) 'Unexpected multiple listener owners'
New-Item -ItemType Directory -Path $EvidenceDirectory -Force | Out-Null
$listenerOwner=[int]$ownerIds[0]
$apiTransport='Winsock listener'
if($listenerOwner -eq 4){
    # Windows HttpListener uses kernel-owned sockets. Tie the exact URL's
    # request queue to its user-mode handler; do not accept PID 4 by itself.
    $snapshot=(& netsh.exe http show servicestate view=requestq verbose=yes | Out-String)
    Assert-True ($LASTEXITCODE -eq 0) 'Cannot inspect HTTP.sys request queues'
    $handler=KRig\Get-KRigHttpSysHandler -Snapshot $snapshot -ApiPort $ApiPort
    $ownerIds=@([int]$handler.ProcessId);$apiTransport='HTTP.sys request queue'
    $handler.RequestQueue|Set-Content -LiteralPath (Join-Path $EvidenceDirectory 'http-sys-request-queue.txt') -Encoding UTF8
}
$miner=Get-CimInstance Win32_Process -Filter ('ProcessId='+[int]$ownerIds[0])
Assert-True ($null -ne $miner -and $miner.ExecutablePath -ieq $ExpectedExecutable) 'API owner is not the expected KRig binary'
Assert-True ((Get-FileHash -LiteralPath $ExpectedExecutable -Algorithm SHA256).Hash -ieq $ExpectedSha256) 'KRig executable hash mismatch'
$poolTransport='direct vendor TLS (certificate policy not proven by this API check)'
$authenticatedPool=$false
if($miner.CommandLine -match '--url\s+stratum\+tcp://127\.0\.0\.1:(\d+)(?:\s|$)'){
    $relayPort=[int]$Matches[1]
    $session=Get-Content -LiteralPath 'D:\Apps\KRig\Runtime\session.json' -Raw -Encoding UTF8|ConvertFrom-Json
    $source=Join-Path $root 'Scripts/PearlExperience'
    Assert-True ($session.ManagementSourceDirectory -ieq $source) 'Unexpected supervisor source directory'
    foreach($file in @('pearl_controller.py','payout_experience.py','pool_transport.py','tls_relay.py')){
        $recorded=$session.ManagementSourceSha256.PSObject.Properties[$file].Value
        Assert-True ($recorded -and (Get-FileHash -LiteralPath (Join-Path $source $file) -Algorithm SHA256).Hash -ieq $recorded) ('Supervisor source changed: '+$file)
    }
    $parent=Get-CimInstance Win32_Process -Filter ('ProcessId='+[int]$miner.ParentProcessId)
    Assert-True ($null -ne $parent -and $parent.CommandLine.Replace('/','\').Contains((Join-Path $source 'payout_experience.py'))) 'Unexpected supervisor parent process'
    $relaySockets=@(Get-NetTCPConnection -LocalPort $relayPort -State Listen -ErrorAction Stop)
    Assert-True ($relaySockets.Count -eq 1 -and $relaySockets[0].LocalAddress -eq '127.0.0.1') 'Relay listener is not one loopback socket'
    $run=[IO.Path]::GetFullPath($session.RunDirectory).TrimEnd('\')
    $receiptPath=[IO.Path]::GetFullPath($session.VerifiedTlsRelay.Receipt)
    Assert-True ($run.StartsWith('D:\AI\Playgrounds\KRig\',[StringComparison]::OrdinalIgnoreCase) -and $receiptPath.StartsWith($run+'\',[StringComparison]::OrdinalIgnoreCase) -and [IO.Path]::GetFileName($receiptPath) -eq 'tls-status.json') 'Unexpected TLS receipt location'
    $receipt=Get-Content -LiteralPath $receiptPath -Raw -Encoding UTF8|ConvertFrom-Json
    $proof=KRig\Get-KRigSupervisorTlsEvidence -Session $session -Receipt $receipt -MinerPid ([int]$miner.ProcessId) -ParentPid ([int]$miner.ParentProcessId) -LocalPort $relayPort -SocketOwnerPid ([int]$relaySockets[0].OwningProcess)
    $proof|ConvertTo-Json -Depth 4|Set-Content -LiteralPath (Join-Path $EvidenceDirectory 'verified-pool-transport.json') -Encoding UTF8
    $poolTransport='supervisor loopback to certificate- and hostname-verified TLS';$authenticatedPool=$true
}else{
    Assert-True ($miner.CommandLine -match '--url\s+stratum\+ssl://prl-hk\.kryptex\.network:8048(?:\s|$)') 'Unexpected pool or transport'
}

Assert-True ($miner.CommandLine -notmatch '--gpu-(?:cclock|mclock|coffset|moffset|plimit|fan)') 'Unexpected miner-side hardware tuning'
New-Item -ItemType Directory -Path $EvidenceDirectory -Force | Out-Null
$script:ExpectedUrl="http://127.0.0.1:$ApiPort/"
$script:ObservedUrls=[Collections.Generic.List[string]]::new()
$script:LastPayload=$null
function Invoke-GetUrl {
 param($Url,$Timeout,[switch]$ForceHttpClient)
 Assert-True ($Url -ceq $script:ExpectedUrl) 'Native API class requested a non-loopback URL'
 [void]$script:ObservedUrls.Add($Url)
 $request=[Net.HttpWebRequest]::Create($Url);$request.Proxy=$null;$request.Timeout=8000;$request.ReadWriteTimeout=8000
 $response=$request.GetResponse()
 try {
  $reader=[IO.StreamReader]::new($response.GetResponseStream())
  try {$raw=$reader.ReadToEnd()}finally{$reader.Dispose()}
 }finally{$response.Dispose()}
 $script:LastPayload=$raw|ConvertFrom-Json
 return $script:LastPayload
}
$raw=Invoke-GetUrl $script:ExpectedUrl -Timeout 8 -ForceHttpClient
$summary=KRig\Get-KRigApiSummary -Data $raw
Assert-True ($summary.Hashrate -gt 0) 'Backend has no positive hashrate yet'
$raw|ConvertTo-Json -Depth 16|Set-Content -LiteralPath (Join-Path $EvidenceDirectory 'api-response.json') -Encoding UTF8
# Exercise the exact native API class. Only the larger manager base is a stand-in;
# the HTTP request, parser, class body and update branch are actual implementations.
$text=Get-Content -LiteralPath (Join-Path $root 'Modules/MinerAPIs.psm1') -Raw -Encoding UTF8
$tokens=$null;$parseErrors=$null;$ast=[Management.Automation.Language.Parser]::ParseInput($text,[ref]$tokens,[ref]$parseErrors)
Assert-True (-not $parseErrors.Count) 'Miner API module no longer parses'
$node=$ast.Find({param($n)$n -is [Management.Automation.Language.TypeDefinitionAst] -and $n.Name -eq 'KRig'},$true)
Assert-True ($null -ne $node) 'Native KRig API class is missing'
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
function Write-Log {param($Level,$Message);throw $Message}
$api=New-Object -TypeName KRig;$api.Name='actual-local-KRig';$api.Port=$ApiPort;$api.Algorithm=@('PearlHash');$api.UpdateMinerData()
$observed=KRig\Get-KRigApiSummary -Data $script:LastPayload
Assert-True ($api.Cleanups -eq 1 -and $script:ObservedUrls.Count -eq 2) 'Native API update did not complete'
Assert-True ($api.LastRates.PearlHash -eq $observed.Hashrate) 'Native class changed base-unit hashrate'
Assert-True ($api.LastShares[0] -eq $observed.Accepted -and $api.LastShares[1] -eq $observed.Rejected -and $api.LastShares[2] -eq $observed.Stale) 'Native class changed share counters'
$result=[ordered]@{
 Time=[datetime]::UtcNow.ToString('o');PowerShell=$PSVersionTable.PSVersion.ToString();Passed=$true
 ApiUrl=$script:ExpectedUrl;ApiTransport=$apiTransport;KernelListenerPid=$listenerOwner;MinerPid=[int]$ownerIds[0];Executable=$miner.ExecutablePath;ExecutableSha256=$ExpectedSha256
 HashrateBaseUnits=$observed.Hashrate;Accepted=$observed.Accepted;Rejected=$observed.Rejected;Stale=$observed.Stale
 AlgorithmLabels=@($script:LastPayload.devices|ForEach-Object {$_.algorithms}|ForEach-Object {if($_.name){$_.name}elseif($_.algorithm){$_.algorithm}else{'not-reported'}})
 NativeClassSourceSha256=(Get-FileHash -LiteralPath (Join-Path $root 'Modules/MinerAPIs.psm1') -Algorithm SHA256).Hash.ToLowerInvariant()
 PoolTransport=$poolTransport;CertificateAndHostnameVerified=$authenticatedPool
 ActualHttpRequests=$script:ObservedUrls.Count;LoopbackOnly=$true;GPUWorkStarted=$false;MinerStarted=$false
 Scope='Real KRig API and exact native update class with a stand-in manager base. Full RainbowMiner web UI/download/start orchestration is not covered.'
}
$result|ConvertTo-Json -Depth 6|Set-Content -LiteralPath (Join-Path $EvidenceDirectory 'live-api-result.json') -Encoding UTF8
$result|ConvertTo-Json -Depth 6
