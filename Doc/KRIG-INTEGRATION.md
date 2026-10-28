# Native KRig integration

This fork adds a Windows/NVIDIA adapter for **KRig 1.5.12**, scoped to Pearl on Kryptex over TLS. It uses the existing pool module. This is management integration, not a replacement CUDA kernel and not a hashrate improvement.

`Miners/KRig.ps1` selects explicit PCI devices, disables other vendor backends, preserves `wallet/worker` login syntax, and binds the miner API to `127.0.0.1`. `Modules/KRig.psm1` validates launch values and parses the native device/algorithm API without multiplying its base-unit rate a second time. `KRig` in `Modules/MinerAPIs.psm1` feeds rates and accepted/rejected/stale shares into RainbowMiner. Invalid addresses, foreign pool hosts, plaintext transport, malformed rates and unsafe command values fail closed.

The download is pinned to the official Windows x64 release asset:

- [KRig v1.5.12](https://github.com/kryptex/krig-miner/releases/tag/v1.5.12)
- ZIP SHA-256: `0f2dd59b7473fff9e511bf044a39b329491dd3be62dc515b5382083c932ca6c5`
- The existing validated executable on this workstation has SHA-256 `61fc4ff4fa111a641f3d70345ff74d8620ab16db12319f29ed89791e9034f22f`.

To use an already-installed executable without duplicating it, set the process-local `KRIG_MINER_PATH` before starting RainbowMiner. Otherwise the normal miner directory is used. Do not weaken Defender or restore a quarantined file to make a launch succeed.

```powershell
$env:KRIG_MINER_PATH='D:\Apps\KRig\1.5.12\krig-miner.exe'
# Configure your own ordinary payout wallet and explicitly select KRig/PearlHash/Kryptex.
# New fork configurations start paused; do not start competing miners.
```

`Tests/Test-KRig.ps1` has **14 passing offline checks on each of PS7 and Windows PowerShell 5.1**, including execution of the real miner definition and API class with local stand-ins. No GPU, miner or pool is contacted by these tests. **The complete RainbowMiner GUI/download/mining flow and actual KRig API have not yet been validated for this adapter.**

KRig is a separate upstream binary: this repository does not contain its GPU kernel source. Actual open-kernel development is in [toolazytoname/soat-miner](https://github.com/toolazytoname/soat-miner). Fees are separate: KRig's Kryptex developer-fee policy, the pool fee and this fork's disclosed optional support time must not be confused with one another. This adapter does not change them.
