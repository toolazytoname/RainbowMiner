# Backend selection and measured limits

Workstation: one RTX 3090 24 GB, Windows, 220 W cap, original pool/wallet/PPS+ mode retained. Source and management evidence remain in their separate Windows playgrounds.

| Item | Open SOAT backend (selected) | KRig 1.5.12 (retained alternative) |
| --- | --- | --- |
| Compute source | MIT CUDA source; native SM86 build, preserved original and complete transcript oracle checks | Public release binary; buildable compute source not supplied |
| Device-reported unit | Explicit T MAC/s | Native TH/s API/display; internal conversion formula not established |
| Controlled source optimization | 46.6475 / 51.3258 / 46.9197 T MAC/s A/B/A, +9.709%, A drift 0.582%, all steady and restored | Prior approximately 59 TH/s at 220 W; not a matched, normalized source-versus-KRig percentage |
| Real proof path | Exact optimized binary: standalone 3 accepted / 0 rejected; own manager 2 accepted / 0 rejected | Prior own-manager native run: 5 accepted / 0 rejected |
| Authenticated TLS | Own relay requires certificate chain and hostname before forwarding payload | Native negative test accepted a self-signed certificate; own relay works but vendor then charges its 3% third-party-pool fee |
| Miner fee | No developer-fee round in this source backend | 0% Kryptex hostname policy, observed 3% on loopback; explicit fee configuration required in own manager |
| Local operator acceptance | Source process/log/identity/TLS checks in PS7 and PS5.1; incoming-GPU yield 3 seconds; CLI stop 5 seconds, actual panel button stop approximately 2 seconds; power restore and panel inspected | Native API class validated against real HTTP.sys service in both shells; full upstream web UI not covered |

The source route is selected for modifiable compute ownership, verified pool compatibility, an authenticated transport and transparent fees. A rate or earning advantage over KRig is not claimed from incompatible labels. The measured 9.709% improvement is over the preserved original SOAT kernel, with the complete candidate package; it does not isolate one instruction or memory change.

Kernel experiment receipts: `D:\AI\Playgrounds\soat-miner\20261028-prl3090`. Management acceptance: `D:\AI\Playgrounds\RainbowMiner\20261028-krig-integration\source-supervisor\source-acceptance-summary.json`. New managed source sessions live directly under `D:\AI\Playgrounds\RainbowMiner`.

The original hard mining deadline and first payout threshold remain in force. A completed short proof/stop test is not represented as a completed payout experience. No currency trading or wallet signing occurs.
