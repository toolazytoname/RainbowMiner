# Backend selection and measured limits

The selected daily backend is open SOAT for modifiable CUDA compute, verified pool compatibility and zero developer fee. The counter-corrected 2026-10-29 matched run passed its declared checks, but **KRig remains faster** on this RTX 3090: open 53.831424 versus KRig 59.305502 T MAC/s, gross KRig advantage 10.1689%. Both used a 220 W cap. This is a full-loop throughput observation, not a measured earning advantage.

| Item | Open SOAT (selected) | KRig 1.5.12 (alternative) |
| --- | --- | --- |
| Compute source | MIT CUDA; native SM86 build; complete-buffer proof checks | Public binary; buildable compute source not supplied |
| Current normalized rate | 53.831424 T MAC/s, bracketed A1/A2 mean | 59.305502 T MAC/s |
| Mean GPU board power | 219.783 W | 219.679 W |
| Current accepted counts | A1: 2; A2: 7 | B: 3 |
| Failure readout | Combined local/unsent/uncertain/negative results; zero in both cases, independently log-checked | API rejected/stale zero; closed reporting scope retained |
| Developer fee | Upstream and fork both 0%; no fee was removed | Advertised recognized Kryptex 0%; observed localhost route 3% |
| TLS | Own Windows relay verifies certificate chain and hostname before forwarding payload | Same verified relay for comparison; native recognized-host policy unproven |
| Ownership | Own buildable compute plus own bounded manager | Own manager around vendor compute |

The sequence was open / KRig / open, 600 seconds per case from first selected-profile telemetry, fixed +420..+600 reporting windows including zero rates. Source-control drift was 0.557690%; all core/hotspot/memory stability ranges were <=2 C. Every planned stop verified owned processes gone and original 370 W restored. Exact logs and unchanged config/binary hashes were checked. Source stale is only a compatibility placeholder; zero does not independently prove no stale work.

KRig's 3% acknowledgement was RAM-only for B. Applying that rate to observed work gives 57.526337 T MAC/s, an arithmetic 6.8639% lead over open. This is not payout, and native recognized-Kryptex 0% remains the legitimate competitive reference. Pool service fees are separate. All management, compute and TLS processes are on Windows; Mac is only an SSH operator.

The independent PearlExperience entry does not execute the full upstream RainbowMiner donation/support loop. The manager's native KRig adapter was checked offline and against the real native API in PowerShell 7 and 5.1. Source CLI/panel controls, incoming-GPU yield, exact child identity, original deadline/threshold and power restoration have recorded acceptance. Current host checks pass 89 cases in normal Python and -O. Neither full upstream web UI coverage nor successful payout is implied.

The source counter fix distinguishes combined client failures from pool-only rejection verdicts. Current source proof/readout checks and the full result are in the [source comparison report](https://github.com/toolazytoname/soat-miner/blob/xiaotutou-prl3090/docs/PRL3090-KRIG-COMPARISON.md). Rate normalization transfers the [prior hardware calibration](https://github.com/toolazytoname/soat-miner/blob/xiaotutou-prl3090/docs/PRL3090-UNIT-CALIBRATION.md) through unchanged work accounting and matching proof checks; it is not a fresh hardware replay for the new binary.

Historical comparisons remain flagged and preserved: one older set failed thermal/stale checks; the aa693 set contained a locally obsolete unsent proof hidden by the old synchronous failure counter. Its earlier all-gates-pass classification was withdrawn. The current repaired run is separate. The +9.709% and later +3.4216% source optimizations are against their respective open baselines, not wins over KRig. Four slower follow-up candidates were rejected rather than promoted.

Current comparison records: D:\AI\Playgrounds\soat-miner\20261029-submission-readout\matched. Managed source sessions: D:\AI\Playgrounds\RainbowMiner. The original first-threshold/absolute-deadline experience remains pending; there are no boot mining triggers, automatic retries, wallet signing or automatic currency trades.
