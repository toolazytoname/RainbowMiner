# One-shot Pearl workstation manager

The default workstation route runs the pinned MIT [SOAT CUDA backend](https://github.com/toolazytoname/soat-miner/tree/xiaotutou-prl3090) through an owned, certificate- and hostname-verified TLS relay to the original Kryptex PRL pool. This GPL management repository owns start/stop, telemetry, resource guards and the first-payout experience. The separate MIT repository contains the modifiable compute kernels. Users need one start/stop entry.

The tested source build has no miner developer-fee round. The full upstream RainbowMiner profit-switching/support loop is not run by this local manager. KRig remains a separate optional binary and native adapter. A local negative test showed that KRig 1.5.12 accepted a self-signed certificate; the verified loopback relay then made that vendor classify the visible endpoint as a third-party pool and charge 3%. The backend selector therefore refuses KRig relay use unless `allow_krig_relay_fee` is explicitly true. It never silently falls back to KRig or CPU.

## Operation

Use the existing desktop Pearl panel, or from this repository:

```powershell
.\Scripts\PearlExperience\Manage-Pearl.ps1 -Action Status
.\Scripts\PearlExperience\Manage-Pearl.ps1 -Action Start -Minutes 60
.\Scripts\PearlExperience\Manage-Pearl.ps1 -Action Stop
```

Source rates are explicitly **T MAC/s**. They are not relabeled as KRig TH/s, pool credits or currency. The source backend has an append-only JSON log, not a separate HTTP API. Session records identify the actual compute executable/hash, selected shape/tile, source-file hashes, exact process creation identities, reported units, temperatures and TLS receipt.

## Invariants

- One heavy GPU workload: a named mutex is shared with source experiments. Existing GPU work blocks startup; an incoming GPU client stops only our owned miner. CPU workloads are allowed, and our controller/miner use BelowNormal priority.
- At most 220 W, with core/hotspot/memory guards of 80/100/96 C. Clocks, voltage and fans remain automatic. No CPU fallback, Defender exclusions, driver changes or boot/login mining trigger.
- Stop and restore the starting power cap; preserve an external cap change. A child that cannot exit keeps the reduced cap and a `stop-failed` state. Recovery verifies the original Windows process handle's PID, exact creation FILETIME, executable and SHA-256 before any forced owned termination. It does not kill processes by name or restore power while owned work remains alive.
- Preserve the original `MiningDeadline` in the existing payout state across restarts. A shorter manual duration still applies. Stop at confirmed plus pending balance reaching the first payout threshold, or at a recorded payout. No automatic restart, currency exchange, wallet signing or private-key access.
- Check the public pool before startup and while mining. Thirty minutes of continuous pool API failure ends mining. After the threshold, release the GPU and watch payout read-only for at most 12 hours. Manual Stop cancels read-only watching too; idle gaps check every second, and each public API request has an 8-second network timeout.
- Authenticate the original pool before forwarding a single miner payload. The child command's `127.0.0.1` endpoint is internal traffic. There is no plaintext Internet fallback. A failed relay thread, invalid source units/backend, or stale source telemetry stops the session.

Only the GPU-validated `4096x65536` / `=ampere large s3 fold k64` source configuration is enabled here. The local config pins the executable SHA-256. Rebuilding a changed kernel requires repeating complete-transcript, performance and pool gates before updating that pin.

## Deployment and checks

Windows Python 3.12.15 uses this repository's `.venv`; runtime code uses the standard library. The vendored relay retains its MIT attribution in `TLS-RELAY-LICENSE.txt`.

```powershell
.\.venv\Scripts\python.exe Scripts\PearlExperience\test_experience.py
.\.venv\Scripts\python.exe Scripts\PearlExperience\test_compute_backend.py
.\.venv\Scripts\python.exe Scripts\PearlExperience\test_tls_transport.py
.\.venv\Scripts\python.exe Scripts\PearlExperience\test_process_identity.py
.\.venv\Scripts\python.exe Scripts\PearlExperience\test_recovery.py
```

The 49 CPU-side checks also pass with `-O`: local TLS servers and bounded owned CPU children are used, with no GPU workload. The native KRig adapter's separate 19 offline cases pass in both PS7 and PS5.1.

`Install-Tasks.ps1` is an explicit deployment, not a mining start. It requires stopped tasks, runs the checks, backs up all five task XML definitions and old launchers, and installs versioned mining/experience/calibration, exact-identity recovery, and the unit-aware panel. None has a boot/login trigger. Existing local config and the previous payout deadline are deliberately required; installation does not create a new unlimited budget.

The live source checker is `Tests/Test-PearlSourceLive.ps1 -EvidenceDirectory <Windows run folder> -RequireAccepted`. It checks the actual process, creation identity, pinned binary/management hashes, exact CUDA JSON sample, selected configuration and authenticated relay socket without starting a miner. `test_live_gpu_yield.py` and `test_live_manual_stop.py` are explicit live integration tests. The current source-manager live gates remain pending until their Windows receipts pass; old KRig tests are not substituted for them. No full upstream web UI/download/startup claim is made.

## Storage

Config and shared runtime state stay in `D:\Apps\KRig` for existing entry compatibility. New source-managed sessions are under `D:\AI\Playgrounds\RainbowMiner`; prior KRig runs remain under `D:\AI\Playgrounds\KRig`. Source-kernel experiments remain under `D:\AI\Playgrounds\soat-miner`. Code stays one repository per `D:\Projects\<owner>\<repo>`. Config, logs, wallet keys and binaries are not committed.
