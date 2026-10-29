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

`Tests/Test-KRig.ps1` has **19 passing offline checks on each of PS7 and Windows PowerShell 5.1**, including execution of the real miner definition and API class with local stand-ins, plus the actual algorithm database and pool-key helper bodies. No GPU, miner or pool is contacted by these tests. The actual KRig API and exact native update class have now passed live checks on PS7 and PS5.1. The complete upstream RainbowMiner web UI/download/start orchestration is outside those checks.

KRig is a separate upstream binary: this repository does not contain its GPU kernel source. Actual open-kernel development is in [toolazytoname/soat-miner](https://github.com/toolazytoname/soat-miner). Fees are separate: KRig's Kryptex developer-fee policy, the pool fee and this fork's disclosed optional support time must not be confused with one another. This adapter does not change them.


A read-only real-API check is available as `Tests/Test-KRigLive.ps1 -ApiPort 18490 -EvidenceDirectory <Windows experiment directory>`. It requires the separately authorized guarded KRig process to be running already; the checker never starts a miner. It verifies the actual listener owner/path/hash and loopback binding, then executes the exact native KRig API class against actual HTTP responses. Its larger manager base remains a stand-in, so success must not be represented as validation of the complete web UI or manager startup flow. The live check passed against KRig 1.5.12 on both PS7 7.6.9 and Windows PowerShell 5.1. Each test made two real loopback HTTP requests and matched the exact native class rate/share updates. The actual algorithm label is `pearlhash`.


On this Windows system, `Get-NetTCPConnection` attributes the loopback listener to **System PID 4**, because it is served through HTTP.sys. The checker now binds the exact loopback URL's request-queue entry to its user-mode KRig handler, then validates that handler's executable path, pinned SHA-256 and TLS pool command. PID 4 alone is never treated as proof of ownership. An additional offline case checks separate queues, ambiguous/missing handlers and exact port matching.

The own versioned supervisor also completed a real 220 W run with **5 accepted / 0 rejected** shares, BelowNormal controller/miner priority, and automatic power restore. A later live incoming-GPU test started a bounded 8 MiB CUDA context while mining had positive reported hashrate: the miner yielded in **2 seconds**, restored the previous **370 W** cap, and left the incoming context running to normal exit. The ordinary Start/Stop entry test stopped in approximately **5 seconds** and preserved the original mining deadline. These are evidence for the local supervisor, not a claim that a different manager increases hashrate.

Windows evidence: `D:\AI\Playgrounds\RainbowMiner\20261028-krig-integration\live-manager-20261029-002834`. Test artifacts retain the exact kernel listener/user-mode owner distinction and the stated stand-in base-class scope.

## Certificate policy boundary

A bounded local negative test of the pinned KRig 1.5.12 binary completed TLS with a self-signed localhost certificate and received 166 application bytes. No jobs or rewards were involved, and no trust roots were installed. This demonstrates that a `stratum+ssl` command alone does not prove certificate-chain rejection in that binary; hostname policy was not separately tested. The probe used localhost; it does not establish how a recognized native Kryptex hostname validates its certificate.

The own one-shot supervisor now launches KRig against a loopback-only relay that requires the original pool certificate and hostname before forwarding payloads, with no plaintext upstream fallback. Six local TLS/pool-policy tests cover valid delivery, untrusted chains, hostname mismatch, disabled verification and endpoint changes. New read-only live checks validate the actual relay socket owner, miner parent, supervisor source hashes and positive authenticated TLS receipt. A direct-vendor API check still reports API correctness but explicitly marks certificate policy as unproven. The full upstream adapter/startup path is separate and is not represented as supplying this relay.
