using module ..\Modules\Include.psm1
param([string]$Name,[PSCustomObject]$Pools,[bool]$InfoOnly)
if (-not $IsWindows) {return}
Import-Module (Join-Path (Split-Path $PSScriptRoot) 'Modules/KRig.psm1')
$Path = if ($env:KRIG_MINER_PATH) {$env:KRIG_MINER_PATH} else {'.\Bin\GPU-KRig\krig-miner.exe'}
$Uri = 'https://github.com/kryptex/krig-miner/releases/download/v1.5.12/krig-miner-1.5.12-win-x64.zip'
$ManualUri='https://github.com/kryptex/krig-miner/releases/tag/v1.5.12'
$Version='1.5.12'
$MainAlgorithm=Get-Algorithm 'pearlhash'
if ($InfoOnly) {
    [PSCustomObject]@{Type=@('NVIDIA');Name=$Name;Path=$Path;Uri=$Uri;ManualUri=$ManualUri;Version=$Version;DevFee=0;Commands=@([PSCustomObject]@{MainAlgorithm='pearlhash';Vendor=@('NVIDIA');Fee=0})}
    return
}
if (-not $Global:DeviceCache.DevicesByTypes.NVIDIA) {return}
$Global:DeviceCache.DevicesByTypes.NVIDIA | Where-Object Type -eq 'GPU' | Select-Object Model -Unique | ForEach-Object {
    $model=$_.Model
    $devices=@($Global:DeviceCache.DevicesByTypes.NVIDIA | Where-Object {$_.Type -eq 'GPU' -and $_.Model -eq $model})
    if (-not $devices.Count -or @($devices | Where-Object {-not $_.BusId}).Count) {return}
    $minerName=(@($Name)+@($devices.Name | Sort-Object)) -join '-'
    $port=37400+[int]($devices | Select-Object -First 1 -ExpandProperty Index)
    foreach($key in @(Get-PoolAlgorithmKeys -Pools $Pools -Algorithm $MainAlgorithm -Model $model)) {
        $pool=$Pools.$key
        if (-not $pool.Host -or -not $pool.SSL -or $pool.Host -notmatch '^prl(?:-[a-z0-9-]+)?\.kryptex\.network$') {continue}
        $poolPort=if($pool.Ports -and $pool.Ports.GPU){[int]$pool.Ports.GPU}else{[int]$pool.Port}
        try {
            $arguments=KRig\Get-KRigArguments -HostName $pool.Host -Port $poolPort -Wallet $pool.Wallet -Worker $(if($pool.Worker){$pool.Worker}else{'RainbowMiner'}) -PciDevices @($devices.BusId) -ApiPort '$mport' -Password $(if($pool.Pass){$pool.Pass}else{'x'}) -SSL ([bool]$pool.SSL)
        } catch {Write-Log -Level Warn "Skipping unsafe KRig configuration: $($_.Exception.Message)";continue}
        [PSCustomObject]@{
            Name=$minerName;DeviceName=$devices.Name;DeviceModel=$model;Path=$Path;Arguments=$arguments
            HashRates=[PSCustomObject]@{$key=$Global:StatsCache."$($minerName)_pearlhash_HashRate".Week}
            API='KRig';Port=$port;Uri=$Uri;ManualUri=$ManualUri;Version=$Version;DevFee=0
            ExtendInterval=3;Penalty=0;PowerDraw=0;BaseName=$Name;BaseAlgorithm='pearlhash'
            Benchmarked=$Global:StatsCache."$($minerName)_pearlhash_HashRate".Benchmarked
            LogFile=$Global:StatsCache."$($minerName)_pearlhash_HashRate".LogFile;EnvVars=@()
        }
    }
}
