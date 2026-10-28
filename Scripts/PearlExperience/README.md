# One-shot Pearl experience supervisor

This directory is the versioned management entry for an existing, authorized Windows RTX 3090 / KRig installation. It does not contain a mining compute kernel. The MIT [soat-miner experiment](https://github.com/toolazytoname/soat-miner/tree/xiaotutou-prl3090) owns the separate open CUDA kernel work. KRig is a separately obtained release binary; no kernel source is claimed for KRig.

## Responsibilities and limits

- One user start/stop entry; an interactive scheduled task starts the backend. No boot or login mining trigger is added.
- SHA-256 checks on the configured KRig executable; verified TLS URL stays in existing local configuration.
- At most 220 W; core / hotspot / memory guards are 80 / 100 / 96 C. Clocks, voltage and fans remain automatic.
- A named mutex is shared with the source experiment; another GPU application prevents startup or stops our own miner. CPU workloads are allowed, and our processes use BelowNormal priority.
- Stop and restore the starting board power cap. Preserve an external cap change. An owned child that cannot stop keeps its reduced cap and process reference.
- Stop when confirmed plus pending pool balance reaches the first payout threshold, or the pool records a payout. Pending maturity does not require further mining.
- Preserve the original mining deadline from `Runtime/payout-experience.json` across every restart. The per-run minutes limit can be shorter. No implicit extension, currency trading, wallet signing or automatic restart.
- The public pool API is checked before mining and watched while running. Thirty minutes of continuous pool API failure ends mining. After reaching the threshold, read-only payout watching lasts at most 12 hours.

These files are a local supervisor in this fork, not a claim that the full upstream RainbowMiner web UI has been validated. The native KRig adapter is documented separately in `Doc/KRIG-INTEGRATION.md`.

## Environment

Windows only; Python 3.12.15 in this repository's `.venv`; standard library only. The existing install is `D:\Apps\KRig`, with binary `1.5.12/krig-miner.exe`, `mining-config.json`, and runtime state. `PRL_EXPERIENCE_HOME` can select a different local root for Python checks; the install script intentionally targets the existing local installation. Configuration, logs, wallet keys and executables are not committed.

Run the hardware-free checks (including `-O` so runtime guards cannot depend on assertions):

```powershell
.\.venv\Scripts\python.exe Scripts\PearlExperience\test_experience.py
.\.venv\Scripts\python.exe -O Scripts\PearlExperience\test_experience.py
```

`Install-Tasks.ps1` is an explicit local deployment, not a miner start. It checks stopped tasks and safety tests, backs up the two task XML definitions and existing launcher to `D:\AI\Playgrounds\RainbowMiner`, points the two bounded mining tasks at this source, and leaves recovery and the existing desktop panel installed. Inspect the receipt and source before running it. No Defender or global execution-policy changes are made.

```powershell
.\Scripts\PearlExperience\Install-Tasks.ps1
.\Scripts\PearlExperience\Manage-Pearl.ps1 -Action Status
.\Scripts\PearlExperience\Manage-Pearl.ps1 -Action Start -Minutes 60
.\Scripts\PearlExperience\Manage-Pearl.ps1 -Action Stop
```

A previous one-shot experience state is deliberately required by the entry script. This installation preserves an existing authorized experiment; it does not silently create a fresh unlimited mining budget. Runtime records are under `D:\Apps\KRig\Runtime`, mining evidence under `D:\AI\Playgrounds\KRig`.
