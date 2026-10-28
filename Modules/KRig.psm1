# Native KRig integration helpers. No miner launch, network or hardware calls.
Import-Module (Join-Path $PSScriptRoot 'ForkDonation.psm1')

function Get-KRigArguments {
    [CmdletBinding()]
    param([Parameter(Mandatory)][string]$HostName,
          [Parameter(Mandatory)][int]$Port,
          [Parameter(Mandatory)][string]$Wallet,
          [string]$Worker = 'RainbowMiner',
          [Parameter(Mandatory)][string[]]$PciDevices,
          [string]$ApiPort = '$mport',
          [string]$Password = 'x',
          [bool]$SSL = $true)
    # This first adapter intentionally supports the already-tested PRL Kryptex route.
    if (-not $SSL -or $HostName -notmatch '^prl(?:-[a-z0-9-]+)?\.kryptex\.network$') {throw 'KRig adapter requires a Kryptex PRL TLS endpoint'}
    if ($Port -lt 1 -or $Port -gt 65535) {throw 'Invalid pool port'}
    if (-not (ForkDonation\Test-PrlDonationAddress $Wallet)) {throw 'Invalid PRL mainnet receive address'}
    if ($Worker -notmatch '^[A-Za-z0-9_-]{1,64}$') {throw 'Worker must contain 1..64 letters, digits, underscores or hyphens'}
    if ($Password -notmatch '^[A-Za-z0-9_.,@=:+/-]{1,128}$') {throw 'Unsupported password characters in miner command'}
    if (-not $PciDevices.Count) {throw 'An explicit NVIDIA PCI device list is required'}
    $devices = @($PciDevices | ForEach-Object {
        if ($_ -notmatch '^[0-9a-fA-F]{2}:[0-9a-fA-F]{2}(?:\.[0-7])?$') {throw 'Invalid PCI device address'}
        if ($_ -match '\.') {$_.ToLowerInvariant()} else {$_.ToLowerInvariant()+'.0'}
    })
    if ($ApiPort -ne '$mport') {
        $number=0
        if (-not [int]::TryParse($ApiPort,[ref]$number) -or $number -lt 1024 -or $number -gt 65535) {throw 'Invalid API port'}
    }
    return "--coin pearl --url stratum+ssl://${HostName}:$Port --user $Wallet/$Worker --password $Password --devices-pci $($devices -join ',') --no-rocm --no-intel --api-host 127.0.0.1 --api-port $ApiPort --no-tui --log-level info"
}

function ConvertTo-KRigNumber {
    param($Value,[bool]$Integral = $false)
    $number=0.0
    if ($null -eq $Value -or -not [double]::TryParse([string]$Value,[Globalization.NumberStyles]::Float,[Globalization.CultureInfo]::InvariantCulture,[ref]$number) -or [double]::IsNaN($number) -or [double]::IsInfinity($number) -or $number -lt 0 -or ($Integral -and [Math]::Truncate($number) -ne $number)) {throw 'Invalid KRig API number'}
    return $number
}

function Get-KRigApiSummary {
    [CmdletBinding()]
    param([Parameter(Mandatory)]$Data)
    if ($null -eq $Data.devices -or @($Data.devices).Count -eq 0) {throw 'KRig API has no devices'}
    $rate=0.0;$accepted=0.0;$rejected=0.0;$stale=0.0
    foreach ($device in @($Data.devices)) {
        if ($null -eq $device.algorithms -or @($device.algorithms).Count -eq 0) {throw 'KRig device has no algorithms yet'}
        foreach ($algo in @($device.algorithms)) {
            $label=if($algo.name){[string]$algo.name}elseif($algo.algorithm){[string]$algo.algorithm}else{''}
            if ($label -and $label -notmatch '^(?:pearl|prl|pearlhash|pearl-pow)$') {throw 'Unexpected non-Pearl KRig algorithm'}
            if ($null -eq $algo.shares) {throw 'KRig API is missing share counters'}
            $rate += ConvertTo-KRigNumber $algo.hashrate
            $accepted += ConvertTo-KRigNumber $algo.shares.accepted -Integral $true
            $rejected += ConvertTo-KRigNumber $algo.shares.rejected -Integral $true
            if($null -ne $algo.shares.stale){$stale += ConvertTo-KRigNumber $algo.shares.stale -Integral $true}
        }
    }
    # API hashrate is already in base units. Do not multiply a TH/s display twice.
    [PSCustomObject]@{Hashrate=$rate;Accepted=$accepted;Rejected=$rejected;Stale=$stale;PowerDraw=0.0}
}
Export-ModuleMember -Function Get-KRigArguments,Get-KRigApiSummary
