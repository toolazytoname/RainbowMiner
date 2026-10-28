# One-shot Pearl experience supervisor

This directory is the versioned management entry for an existing, authorized Windows RTX 3090 / KRig installation. It does not contain a mining compute kernel. The MIT [soat-miner experiment](https://github.com/toolazytoname/soat-miner/tree/xiaotutou-prl3090) owns the separate open CUDA kernel work. KRig is a separately obtained release binary; no kernel source is claimed for KRig.

## Responsibilities and limits

- One user start/stop entry; an interactive scheduled task starts the backend. No boot or login mining trigger is added.
- SHA-256 checks on the configured KRig executable. The original TLS pool URL stays in local configuration; our loopback relay requires a trusted certificate and matching hostname before forwarding any miner payload. KRig connects only to the relay, so a `stratum+tcp://127.0.0.1` child command is local traffic, not a plaintext Internet route.
- At most 220 W; core / hotspot / memory guards are 80 / 100 / 96 C. Clocks, voltage and fans remain automatic.
- A named mutex is shared with the source experiment; another GPU application prevents startup or stops our own miner. CPU workloads are allowed, and our processes use BelowNormal priority.
- Stop and restore the starting board power cap. Preserve an external cap change. An owned child that cannot stop keeps its reduced cap and process reference. Finalization records `stop-failed`, not `stopped`, and raises instead of entering read-only payout waiting.
- Stop when confirmed plus pending pool balance reaches the first payout threshold, or the pool records a payout. Pending maturity does not require further mining.
- Preserve the original mining deadline from `Runtime/payout-experience.json` across every restart. The per-run minutes limit can be shorter. No implicit extension, currency trading, wallet signing or automatic restart.
- The public pool API is checked before mining and watched while running. Thirty minutes of continuous pool API failure ends mining. After reaching the threshold, read-only payout watching lasts at most 12 hours. Manual Stop cancels this watcher as well: idle gaps check the stop request every second; each of the two public API requests has an 8-second network timeout. Cancelling queries never changes the pool balance or starts the GPU.

These files are a local supervisor in this fork, not a claim that the full upstream RainbowMiner web UI has been validated. The native KRig adapter is documented separately in `Doc/KRIG-INTEGRATION.md`.

## Environment

Windows only; Python 3.12.15 in this repository's `.venv`; standard library only. The vendored MIT relay retains its source attribution and `TLS-RELAY-LICENSE.txt`. The existing install is `D:\Apps\KRig`, with binary `1.5.12/krig-miner.exe`, `mining-config.json`, and runtime state. `PRL_EXPERIENCE_HOME` can select a different local root for Python checks; the install script intentionally targets the existing local installation. Configuration, logs, wallet keys and executables are not committed.

Run the hardware-free checks (including `-O` so runtime guards cannot depend on assertions):

```powershell
.\.venv\Scripts\python.exe Scripts\PearlExperience\test_experience.py
.\.venv\Scripts\python.exe -O Scripts\PearlExperience\test_experience.py
.\.venv\Scripts\python.exe Scripts\PearlExperience\test_tls_transport.py
```

`Install-Tasks.ps1` is an explicit local deployment, not a miner start. It checks stopped tasks and safety tests, backs up the three task XML definitions and existing launcher to `D:\AI\Playgrounds\RainbowMiner`, points the three bounded mining/calibration tasks at this source, and leaves recovery and the existing desktop panel installed. Inspect the receipt and source before running it. No Defender or global execution-policy changes are made.

```powershell
.\Scripts\PearlExperience\Install-Tasks.ps1
.\Scripts\PearlExperience\Manage-Pearl.ps1 -Action Status
.\Scripts\PearlExperience\Manage-Pearl.ps1 -Action Start -Minutes 60
.\Scripts\PearlExperience\Manage-Pearl.ps1 -Action Stop
```

A previous one-shot experience state is deliberately required by the entry script. This installation preserves an existing authorized experiment; it does not silently create a fresh unlimited mining budget. Runtime records are under `D:\Apps\KRig\Runtime`, mining evidence under `D:\AI\Playgrounds\KRig`.


The `LazyPC-PearlTuning` task now uses this same bounded experience with `--calibrate`. Its public-pool watcher remains active across the calibration profiles and intervening cooldowns. Thermal/resource failure aborts the calibration instead of choosing an earlier profile and resuming automatically. Cooldown also yields to a newly present GPU application. The original deadline and first payout threshold apply throughout; no new heavy calibration is launched by deployment.

`test_live_gpu_yield.py` and `test_live_manual_stop.py` are explicit live integration checks, not import-time actions or ordinary offline tests. The former requires the separately compiled bounded context helper from the source repository, checks actual native APIs, then simulates an incoming tiny GPU client. Do not run it casually while using your own GPU work. The latter starts a two-minute bounded test through the ordinary Start entry and invokes Stop once hashrate is positive. Evidence lives outside Git.

Ordinary users should use `Manage-Pearl.ps1` or the existing panel. `pearl_controller.py` is a developer building block; the payout experience supplies the cumulative goal and deadline bounds. Session records now include management source-file SHA-256 values so a live run can be tied to its code.

A local negative probe against the pinned KRig 1.5.12 binary found that it accepted an untrusted self-signed certificate and sent application bytes. No jobs were provided. Our supervisor therefore supplies mandatory certificate and hostname verification independently of vendor TLS behavior. TLS receipts and supervisor source hashes are recorded with each session; a failed relay thread ends mining. Native API checks bind the actual miner parent and relay socket to this receipt. The standalone full RainbowMiner adapter still uses vendor TLS and has no claim of an independently verified certificate policy.
