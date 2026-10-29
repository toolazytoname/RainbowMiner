# Backend selection and measured limits

Workstation: one RTX 3090 24 GB, Windows, 220 W cap, original pool/wallet/PPS+ mode retained. Source and management evidence remain in their separate Windows playgrounds.

| Item | Open SOAT backend (selected) | KRig 1.5.12 (retained alternative) |
| --- | --- | --- |
| Compute source | MIT CUDA source; native SM86 build, preserved original and complete transcript oracle checks | Public release binary; buildable compute source not supplied |
| Device-reported unit | Explicit T MAC/s | Native TH/s API/display; calibrated 1:1 to T MAC/s for this pinned RTX3090 / KRig1.5.12 configuration |
| Controlled source optimization | 46.6475 / 51.3258 / 46.9197 T MAC/s A/B/A, +9.709%, A drift 0.582%, all steady and restored | Completed observed fixed-window result 59.7103 T MAC/s at 219.72 W; strict overall comparison remains flagged |
| Real proof path | Exact optimized binary: standalone 3 accepted / 0 rejected; own manager 2 accepted / 0 rejected | Prior own-manager native run: 5 accepted / 0 rejected |
| Authenticated TLS | Own relay requires certificate chain and hostname before forwarding payload | Localhost negative test accepted a self-signed chain; native recognized-Kryptex policy is untested. Our verified relay works and is classified by KRig as a 3% endpoint |
| Miner fee | No developer-fee round in this source backend | 0% Kryptex hostname policy, observed 3% on loopback; explicit fee configuration required in own manager |
| Local operator acceptance | Source process/log/identity/TLS checks in PS7 and PS5.1; incoming-GPU yield 3 seconds; CLI stop 5 seconds, actual panel button stop approximately 2 seconds; power restore and panel inspected | Native API class validated against real HTTP.sys service in both shells; full upstream web UI not covered |

The source route is selected for modifiable compute ownership, verified pool compatibility, an authenticated transport and transparent fees. Unit normalization has now been independently calibrated. The completed open/closed/open fixed-window observations were 50.88 / 59.71 / 50.79 T MAC/s at 220 W. Strict quality checks were not all met: A1 thermal range and B stale-share gates failed. KRig was faster in these observations, including a simple 3% fee work-budget adjustment; a controlled speed or payout advantage is not established. See the [full report](https://github.com/toolazytoname/soat-miner/blob/xiaotutou-prl3090/docs/PRL3090-KRIG-COMPARISON.md). The measured 9.709% improvement is over the preserved original SOAT kernel, with the complete candidate package; it does not isolate one instruction or memory change.

Kernel experiment receipts: `D:\AI\Playgrounds\soat-miner\20261028-prl3090`. Management acceptance: `D:\AI\Playgrounds\RainbowMiner\20261028-krig-integration\source-supervisor\source-acceptance-summary.json`. New managed source sessions live directly under `D:\AI\Playgrounds\RainbowMiner`.

The original hard mining deadline and first payout threshold remain in force. A completed short proof/stop test is not represented as a completed payout experience. No currency trading or wallet signing occurs.

## Independent unit calibration

For the pinned RTX3090 / KRig1.5.12 fixture, native TH/s maps 1:1 to T MAC/s. KRig logs its matrix dimensions and iterations/s, whose product matches both its tmads/s and TH/s readouts. Three independent NVIDIA INT8 operation-count samples per backend agree exactly with twice the declared matrix MAC work; a separate launch activity capture corroborates the scale. This is a synthetic unit calibration, not a steady mining or earnings result. The differing matrix K values (SOAT 2048, KRig 4096) are included in the calculation.

The [source repository calibration report](https://github.com/toolazytoname/soat-miner/blob/xiaotutou-prl3090/docs/PRL3090-UNIT-CALIBRATION.md) documents the tools, exact counts, original failed-run receipts and the reviewed raw-data scope. Evidence remains on Windows in the closed-source-comparison playground. New binaries, ranks, configurations and algorithms need their own unit check.

## Developer fees and pool fees

The original upstream SOAT compute backend already has no developer-fee round. Our source fork retains that behavior; we did not remove an upstream charge. This statement concerns this compute backend, not every open-source miner.

The installed KRig 1.5.12 executable documents 0% developer fee for Kryptex pools and a minimum 3% for other pools in its own `--help` output. Our authenticated local relay is seen as a localhost endpoint: the actual trial logged `devfee 3%`. Therefore a KRig relay comparison must explicitly account for that fee. The production configuration continues to select SOAT with `allow_krig_relay_fee: false`. Closed-source licensing alone does not imply a developer fee.

The full upstream RainbowMiner application has a separate donation/support mechanism. Our `Scripts/PearlExperience` entry runs its own bounded controller and does not execute that full application donation loop. A pool service fee is separate from either mechanism and still applies according to the [current pool policy](https://pool.kryptex.com/prl). Zero developer fee does not mean zero total cost.

Evidence: installed vendor help and the measured loopback-fee receipt are preserved under the Windows playground directories. The next closed-versus-source comparison must distinguish gross device-reported rate, developer-fee-adjusted work and actual pool-accepted work; the 9.709% source optimization above is not a KRig comparison.

## Matched round stability finding

The first normalized real-pool A1/B round was not promoted: B had a connection interruption inside the predeclared final 180 seconds and failed the thermal gate. A1 measured 51.3665 T MAC/s at 219.7968 W, but there is no valid cross-backend winning percentage from that round. The raw cases remain on Windows. An intermediate relay revision used a shared duplex idle deadline, with incoming-only/outgoing-only activity and actual silence tested. All existing certificate, hostname and endpoint guards still pass. The transport investigation is recorded in the [source investigation report](https://github.com/toolazytoname/soat-miner/blob/xiaotutou-prl3090/docs/PRL3090-RELAY-IDLE.md). The default production configuration was restored exactly, with SOAT selected and the KRig fee disabled.

The shared-application-deadline round also failed B stability: its receipt recorded one local idle cutoff during a legitimate quiet mining period. Production now uses TCP keepalive with no application idle cutoff; the original mining/payout deadline remains in force. The previous rounds are retained. The completed third-round observations above use this common liveness policy. The manager and deployed relay pass 66 CPU checks in each of normal and -O modes. An observation timeout during cooldown is not a failed mining task; measurements begin at the first selected-profile GPU telemetry row.
