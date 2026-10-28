# Xiaotutou fork: local, explicit PRL-only donation policy. GPL-3.0.
# No network calls, miner launches, system settings or ordinary user-wallet writes.
function Test-PrlDonationAddress {
    [CmdletBinding()]
    param([AllowEmptyString()][string]$Address)
    # Mainnet witness-v1, 32-byte program, lower-case Bech32m (BIP-350).
    if ($Address -cnotmatch '^prl1p[qpzry9x8gf2tvdw0s3jn54khce6mua7l]{58}$') {return $false}
    $charset = 'qpzry9x8gf2tvdw0s3jn54khce6mua7l'
    if (($charset.IndexOf($Address[$Address.Length - 7]) -band 15) -ne 0) {return $false}
    $values = [System.Collections.Generic.List[int]]::new()
    foreach ($ch in 'prl'.ToCharArray()) {$values.Add(([int]$ch -shr 5))}
    $values.Add(0)
    foreach ($ch in 'prl'.ToCharArray()) {$values.Add(([int]$ch -band 31))}
    foreach ($ch in $Address.Substring(4).ToCharArray()) {$values.Add($charset.IndexOf($ch))}
    [uint32]$check = 1
    $generators = @(0x3b6a57b2,0x26508e6d,0x1ea119fa,0x3d4233dd,0x2a1462b3)
    foreach ($value in $values) {
        $top = $check -shr 25
        $check = (($check -band 0x1ffffff) -shl 5) -bxor $value
        for ($i = 0; $i -lt 5; $i++) {
            if (($top -shr $i) -band 1) {$check = $check -bxor $generators[$i]}
        }
    }
    return $check -eq 0x2bc830a3
}

function Get-ForkDonationPlan {
    [CmdletBinding()]
    param(
        [int]$DailyMinutes,
        [AllowEmptyCollection()][string[]]$AvailablePools = @(),
        [string]$Path = (Join-Path (Split-Path $PSScriptRoot) 'Data/ForkDonation.json')
    )
    $plan = [PSCustomObject]@{Enabled=$false;Reason='';MinutesPerRound=0;DelayHours=24;DailyMinutes=$DailyMinutes;RatePercent=0;Recipient='';Data=$null}
    if ($DailyMinutes -eq 0) {$plan.Reason='Donation disabled (Donate=0).';return $plan}
    if ($DailyMinutes -lt 0 -or $DailyMinutes -gt 1440) {$plan.Reason='Donate must be between 0 and 1440 minutes per day.';return $plan}
    try {
        $data = Get-Content -LiteralPath $Path -Raw -Encoding UTF8 -ErrorAction Stop | ConvertFrom-Json -ErrorAction Stop
        if ($data.Enabled -isnot [bool]) {throw 'Enabled must be a JSON boolean.'}
        if (-not $data.Enabled) {$plan.Reason='Fork donation policy disabled.';return $plan}
        if (-not $data.Recipient -or $data.Network -cne 'PRL') {throw 'Expected a named PRL recipient.'}
        if (@($data.Pools).Count -ne 1 -or $data.Pools[0] -cne 'Kryptex') {throw 'Only the Kryptex PRL pool is supported by this policy.'}
        if (@($data.Algorithm).Count -ne 1 -or $data.Algorithm[0] -cne 'PearlHash') {throw 'Donation must use PearlHash only.'}
        if (@($data.Wallets.PSObject.Properties.Name | Where-Object {$_ -notin @('Kryptex','Default')}).Count) {throw 'Unexpected donation pool wallet.'}
        $wallet = $data.Wallets.Kryptex
        if (-not (Test-PrlDonationAddress $wallet.PRL)) {throw 'PRL mainnet Bech32m address is invalid.'}
        if (@($wallet.PSObject.Properties.Name | Where-Object {$_ -notin @('PRL','Worker','DataWindow','Penalty','SSL','CoinSymbol')}).Count) {throw 'Account credentials or a non-PRL wallet are not allowed.'}
        if (($wallet.SSL -isnot [int] -and $wallet.SSL -isnot [long]) -or $wallet.SSL -ne 2 -or $wallet.CoinSymbol -cne 'PRL') {throw 'Donation requires SSL=2 (TLS only) and CoinSymbol=PRL.'}
        if ($wallet.Worker -notmatch '^[A-Za-z0-9_-]{1,32}$') {throw 'Invalid donation worker name.'}
        if ($data.Wallets.Default -isnot [PSCustomObject]) {throw 'Default must be an empty-wallet object.'}
        if (@($data.Wallets.Default.PSObject.Properties.Name | Where-Object {$_ -ne 'Worker'}).Count) {throw 'Default must not contain any payout wallet.'}
        if ($AvailablePools -notcontains 'Kryptex') {$plan.Reason='Kryptex unavailable; skip donation without a fallback recipient.';return $plan}
        $plan.Enabled = $true
        $plan.MinutesPerRound = if ($DailyMinutes -gt 15) {$DailyMinutes / 2.0} else {$DailyMinutes}
        $plan.DelayHours = if ($DailyMinutes -gt 15) {12} else {24}
        $plan.RatePercent = [Math]::Round($DailyMinutes / 14.4,4)
        $plan.Recipient = [string]$data.Recipient
        $plan.Data = $data
        $plan.Reason = 'Local PRL donation policy validated.'
    } catch {
        # An invalid/missing policy never downloads somebody else's wallet as a fallback.
        $plan.Reason = "Donation skipped: $($_.Exception.Message)"
    }
    return $plan
}
Export-ModuleMember -Function Test-PrlDonationAddress,Get-ForkDonationPlan
