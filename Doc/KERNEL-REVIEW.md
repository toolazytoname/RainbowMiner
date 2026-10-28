# Pearl GPU kernel review

Current implementation/result: the MIT SOAT SM86 source backend is now built and validated, with a controlled +9.709% gain over its original kernel and source-manager live acceptance. See [backend selection and evidence](COMPUTE-BACKEND-COMPARISON.md). The initial review below records the earlier investigation; it is not the final runtime status.

Review date: 2026-10-28. Scope: RTX 3090 (Ampere, SM86), Windows, one GPU. This is a source review, not a performance result. The existing KRig experience is still running independently.

## What is actually controlled by this fork

`RainbowMiner -> miner process -> GPU kernel -> pool` is the relevant chain. RainbowMiner selects and supervises miners; changing its donation or launch code does not rewrite CUDA instructions. The Kryptex pool module already exists. KRig integration remains a separate, pending management task.

| Project | Source inspected | Practical consequence |
| --- | --- | --- |
| RainbowMiner | PowerShell manager and miner definitions | We can modify launch, monitoring and selection behavior. |
| [KRig](https://github.com/kryptex/krig-miner) | Public tree contains release documentation, not buildable CUDA/C++ kernels | Its installed binary cannot be optimized at source level here. |
| [OneZeroMiner](https://github.com/OneZeroMiner/onezerominer), [BzMiner](https://github.com/bzminer/bzminer) | Inspected public trees are release/documentation repositories | Adapter changes do not grant access to their compute kernels. |
| [Pearl reference miner](https://github.com/pearl-research-labs/pearl/tree/master/miner) | CUDA reference implementation; documented target is SM90 H100/H200 | It is not a ready-to-build SM86 replacement. |

The local RainbowMiner definitions list Pearl developer fees of 1% for OneZeroMiner/NVIDIA and 2% for BzMiner. KRig's published release notes describe 0% developer fee on Kryptex and a separate fee for third-party pools. Pool fees and this fork's optional support time are additional layers. Moving the existing KRig task under a manager does not create a fee saving by itself.

## Source candidates and provenance

- [Open-Pearl-Miner, inspected revision](https://github.com/Muskwak/Open-Pearl-Miner/tree/ac3d992d7eb6ca1bb344d5d3ee125eecb182248d): actual Ampere-capable CUDA kernels. Its current [custom license](https://github.com/Muskwak/Open-Pearl-Miner/blob/ac3d992d7eb6ca1bb344d5d3ee125eecb182248d/LICENSE) requires retention of the original 2% developer fee for distributed derivatives. Keep that code separate from the GPL fork. Its pool client currently targets LuckyPool, so it cannot simply replace the current Kryptex route.
- The same author's [earlier MIT snapshot](https://github.com/Muskwak/Open-Pearl-Miner/tree/b1f24627004f96254ca5dce3b5917bb842e9379e) contains full Pascal/DP4A sources and an [MIT license](https://github.com/Muskwak/Open-Pearl-Miner/blob/b1f24627004f96254ca5dce3b5917bb842e9379e/LICENSE). Any work based on that revision must preserve attribution and track that exact baseline. Later code must be assessed under its own license; it is not automatically part of this MIT snapshot.
- [Nacre Miner](https://github.com/andrii-stasiuk/nacre-miner/tree/705a0605a6356747612d7a35f1b0b0b62b43e1c6) publishes MIT licensing and SM86 CUDA sources, but only a LuckyPool client. Code ancestry and third-party attribution still need checking before redistribution. No binary was run.
- [CanaryMiner](https://github.com/bucnazty2020/CanaryMiner/tree/dc68ead009c60999d66b865baa729ef512027edc) publishes MIT CUDA C++ sources and Kryptex support. The current public build explicitly accepts only Blackwell/RTX 50-series. An Ampere port would require kernel and correctness work; bypassing the device check alone is insufficient.
- Neil's linked repository is access-blocked by GitHub after a [published copyright complaint](https://github.com/github/dmca/blob/master/2026/07/2026-07-01-open-pearl-miner.md). The complaint is an allegation, not our independent legal finding. It is excluded as a source baseline.

## Concrete opportunities found in the current Open-Pearl source

These are review hypotheses, not measured gains or copied implementation changes.

1. **SM86-specific tiling and pipeline tuning.** The [Ampere dispatcher](https://github.com/Muskwak/Open-Pearl-Miner/blob/ac3d992d7eb6ca1bb344d5d3ee125eecb182248d/csrc/gemm/pearl_ampere_tc.cu#L1408) selects a fixed 128x256, K32, three-stage CuTe path for the normal supported shape, with several shape fallbacks. Its comment describes Ada measurements. Test structurally valid tile/stage alternatives on the 3090; inspect registers, spills, barriers and occupancy before choosing a configuration.
2. **Reuse job-setup scratch.** [p40_setup_job](https://github.com/Muskwak/Open-Pearl-Miner/blob/ac3d992d7eb6ca1bb344d5d3ee125eecb182248d/csrc/capi/p40_capi.cu#L113) allocates and frees three temporary buffers and queries device properties at each setup. A persistent context could reuse these. This is setup overhead, not a per-region allocation problem; its value depends on setup frequency.
3. **Reduce hit-path transfer stalls.** The [host loop](https://github.com/Muskwak/Open-Pearl-Miner/blob/ac3d992d7eb6ca1bb344d5d3ee125eecb182248d/python/miner_capi.py#L168) already batches found checks and submits proofs in a background thread, but synchronously snapshots A/B to ordinary NumPy buffers first. Evaluate pinned buffers and event-controlled overlap while keeping winning inputs immutable. Batch size tuning must also measure stale-job latency.

Tensor Cores, asynchronous shared-memory copies, fused GEMM/transcript folding, cached launch attributes and background proof submission are already implemented in that revision. They must not be presented as new optimizations. See the [NVIDIA Ampere tuning guide](https://docs.nvidia.com/cuda/ampere-tuning-guide/index.html) for architectural constraints.

## Acceptance before switching

- Build a precisely identified, appropriately licensed source revision in an isolated project; record compiler, dependency and source versions.
- Compare transcripts/hashes/proofs against a reference on boundary shapes and random inputs. Preserve the protocol's exact arithmetic.
- Compare baseline/candidate at the same power cap, workload and thermal steady state, with an A/B/A order. Record core/hotspot/memory temperatures, wall-clock throughput, invalid/stale work, fees and accepted weighted work. Raw share counts are not comparable across changing difficulty.
- Use the same Kryptex payment mode and public wallet to preserve pool accounting. No parallel miners. Verify clean stop, manual stop, thermal stop and restoration of the previous power cap.
- Retain the experience's first-threshold stop policy. A source-controlled build is not automatically faster, and a local hashrate counter is not proof of higher paid work.

## Protocol roadmap

[PIP-3](https://github.com/pearl-research-labs/pips/blob/main/PIPS/pip-0003.md), inspected on the review date, is **Draft**, with deployment marked TBD. It proposes an FP protocol with hardware-specific verification, currently listing Hopper and Blackwell. It is not evidence that an activation has happened or that the 3090 has already stopped working. This unresolved roadmap affects the value of a large Ampere-only rewrite.

## Local records

Source checkouts remain under `D:\Projects\<owner>\<repo>`. Research and future benchmark records belong under `D:\AI\Playgrounds\RainbowMiner\20261028-kernel-review`. No new miner, CUDA toolchain, clock setting, Defender exclusion or GPU workload was started for this source review. Benchmarking and live migration remain pending.
