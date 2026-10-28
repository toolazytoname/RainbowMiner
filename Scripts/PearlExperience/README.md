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
- Preserve the original `MiningDeadline` in the existing payout state across restarts. A shorter manual duration still applies. The CLI accepts at most 2160 minutes (36 hours), but the unchanged original absolute deadline always clips the actual run; restarting never grants another 36 hours. Stop at confirmed plus pending balance reaching the first payout threshold, or at a recorded payout. No automatic restart, currency exchange, wallet signing or private-key access.
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

The 54 CPU-side checks also pass with `-O`: local TLS servers and bounded owned CPU children are used, with no GPU workload. The native KRig adapter's separate 19 offline cases pass in both PS7 and PS5.1.

`Install-Tasks.ps1` is an explicit deployment, not a mining start. It requires stopped tasks, runs the checks, backs up all five task XML definitions and old launchers, and installs versioned mining/experience/calibration, exact-identity recovery, and the unit-aware panel. None has a boot/login trigger. Existing local config and the previous payout deadline are deliberately required; installation does not create a new unlimited budget.

The live source checker is `Tests/Test-PearlSourceLive.ps1 -EvidenceDirectory <Windows run folder> -RequireAccepted`. It checks the actual process, creation identity, pinned binary/management hashes, exact CUDA JSON sample, selected configuration and authenticated relay socket without starting a miner. `test_live_gpu_yield.py` and `test_live_manual_stop.py` are explicit live integration tests. The source-manager live gate passed in both PS7 and PS5.1 with actual source process/log/identity/TLS verification. The managed source session recorded 2 accepted / 0 rejected shares. An incoming bounded CUDA context caused a 3-second yield with original power restored and the new context left alive; ordinary Start/Stop completed in 5 seconds without forced termination and without changing the original deadline. Actual Start/Stop buttons were invoked successfully in a separate bounded source session (approximately 2 seconds to stop). The panel was captured and visually inspected, with explicit T MAC/s units and matching counters. These short acceptance results are separate from the continuing first-threshold/payout experience. No full upstream web UI/download/startup claim is made.

## Storage

Config and shared runtime state stay in `D:\Apps\KRig` for existing entry compatibility. New source-managed sessions are under `D:\AI\Playgrounds\RainbowMiner`; prior KRig runs remain under `D:\AI\Playgrounds\KRig`. Source-kernel experiments remain under `D:\AI\Playgrounds\soat-miner`. Code stays one repository per `D:\Projects\<owner>\<repo>`. Config, logs, wallet keys and binaries are not committed.


### Fresh statistics during a pool-side wait

The selected source binary emits `timestamp_unix_ms` on every rate record.
After the first prepared job, failed/retired job fetches emit fresh zero-rate
heartbeats instead of leaving the previous positive rate on screen. Initial
startup still waits for real work under the existing 90-second statistics guard.
The reader checks the record timestamp (30 seconds maximum age, at most 5 seconds
in the future), not just log modification time. Repeated warnings cannot refresh
an old record; disappearing statistics cannot reuse a cached positive rate.

The bounded source test `tools/test_waiting_telemetry.py` exercises actual CUDA
work, 50 seconds with a retired mock job, and resumed work. It runs only against
a loopback fixture, uses the source guard, and never proves pool earnings. Real
pool acceptance and TLS validation are recorded separately. The CUDA kernels and
proof encoding are unchanged by this host-side statistics correction.

## One-case backend comparison

The experimental run_backend_comparison_case.py entry selects SOAT or KRig in memory for one bounded 1..15 minute case under the existing payout, original deadline, TLS, ownership, temperature and coexistence guards. It never writes the production mining configuration. KRig on the authenticated localhost relay requires --accept-krig-relay-fee-percent 3; the source route rejects that fee option. Use a new absolute --receipt path and an operator-started elevated interactive task. There is no retry or scheduled boot trigger. The default desktop Start entry continues to use the production configuration.

Production uses per-socket TCP keepalive and no application-traffic idle deadline: a quiet valid job does not need a new notification or winning share to keep its connection open. The optional application timeout remains shared across both directions when explicitly requested. The status receipt records application_idle_seconds and the actual TCP keepalive settings, plus connection_idle_timeouts; payloads are not logged. TLS, the original mining deadline and the payout/thermal/manual-stop guards remain unchanged.
