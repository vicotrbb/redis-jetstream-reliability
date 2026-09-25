# An Empirical Evaluation of Message Delivery Reliability and Recovery Characteristics in Redis Streams and NATS JetStream

Research by Victor Bona. This repository contains one complete article with proofs and diagnostics in appendices, recorded homelab measurements, experiment source, and reproducible analysis. It retains the original 11-point LaTeX template, 1.1-inch margins, author block, and original section order.

**Artifact version 1.3.0.** The study compares recovery policies, consumer concurrency, and publication/acknowledgment costs. It distinguishes append synchronization from consumer-progress persistence. The extension adds current releases, fresh broker processes and stores for every trial, matched publication durations, live recovery controls, CPU sensitivity, synchronization traces, and compression-policy diagnostics. Original and follow-up evidence remain unchanged. Version 1.3.0 integrates the former supplement into the article and adds explicit reporting of retained timeouts, long requests, and version contrasts.

The original paper and research material use CC-BY-4.0; original code and formalization use MIT. See [LICENSE.md](LICENSE.md), [CITATION.cff](CITATION.cff), and the [release guide](release/README.md). GitHub access is public. No Zenodo deposit, DOI assignment, external replication, journal acceptance, or implementation-verification claim is made.

## Read and inspect

- [Complete article, including appendices](output/pdf/redis-jetstream-reliability.pdf): 43 pages, with all proofs, detailed results and diagnostics.
- [Current validation](docs/FINAL_REVISION_VALIDATION.md), [prospective follow-up protocol](docs/FOLLOWUP_PROTOCOL.md), and [development/validation record](docs/FOLLOWUP_VALIDATION.md).
- [Pinned source and literature review](docs/FOLLOWUP_SOURCE_REVIEW.md) and [historical source corrections](docs/SOURCE_REVALIDATION.md).
- Original results: `data/derived/statistics.json` and `aggregate.csv`.
- Follow-up results: `followup/derived/statistics.json`, `trials.csv`, and `report.json`.
- Publication failures, request maxima and version contrasts: `data/derived/operational-report.json`; regenerate with `make report-operational`.
- [Artifact version map](docs/ARTIFACT_MAP.md) and [GitHub provenance](docs/GITHUB_PUBLICATION.md).

The current validation record is `docs/FINAL_REVISION_VALIDATION.md`. Successful-build receipts, PDF content checks, and visual-review records under `data/derived/` bind the complete article to its exact source and rendered pages. Earlier validation records describe the historical documents identified in the artifact map.

## Experimental scope

All broker workloads, runtime Go tests, tracing, and Lean compilation use **only `kubectl --context homelab`**. The workstation performs authoring, offline data checks, analysis, and PDF compilation. Brokers run on the Ryzen-based `homelab-01`; drivers run on the Intel N100 `homelab-02`. Other services share the hosts. The broker storage is Btrfs/NVMe with zstd compression enabled by default.

The original campaign evaluates Redis 7.4.2 and NATS 2.10.24 with 550 planned outcomes: 300 drain trials, 60 publication trials, 60 serial trials, 120 killed-consumer recoveries, and ten plain-read controls. Its 419 completed timing trials contain 17,411,288 message records. D038's failed publication has no reconstructible client timing/count trace; it stays a failed outcome. Its accidental replay remains excluded. Exact historical censor endpoints also remain unavailable.

The follow-up preserves those releases and adds Redis 8.10.2 and NATS 2.15.0. Three separately provisioned deployments, `main01` through `main03`, each have 204 prospective cells, totaling 612:

- 216 publication trials: four engine/version combinations, three profiles, 1/16 publishers, three blocks per deployment, and a matched 15-second admission budget.
- 96 drain trials: current releases, memory/periodic profiles, 1/16 consumers, 2/4 driver CPUs, two blocks, and 65536 messages.
- 240 active recovery episodes and 12 plain-read controls: historical/current XAUTOCLAIM, current Redis CLAIM, historical/current JetStream, killed/live-unacknowledging consumers, two thresholds and two receipt ages.
- 24 synchronization-trace trials and 24 compression-policy/payload diagnostics: current always profiles, one observation per diagnostic condition per deployment.

Each follow-up trial starts a fresh broker process and store, with a common separate-stream warm-up. Successful publication and drain trials read back all stored IDs and 512 payload bytes outside timing. Failed outcomes remain represented; successful-run rates and paired comparisons report their completion counts. The six development pilots are excluded and retained separately.

All 612 planned outcomes were collected: 601 completed procedures and eleven publication failures, comprising four warm-up and seven timed failures. Full analysis reconstructed 80,263,171 timed event records. A completed plain-read control means that its observation procedure ended with the message still pending, not that redelivery succeeded.

The follow-up reports deployment means and their observed ranges, not confidence intervals with asserted population coverage. The deployments share hardware and are not independent-host replications. Consumer kills do not test power-loss durability. Fresh stores remove known file accumulation without resetting host caches or unrelated device activity. The mathematical results remain conditional abstract identities, bounds, and counterexamples.

## Verify the delivered artifact

Start with an unchanged release or checkout, before reanalysis or rebuilding:

```sh
python3 bench/verify_release.py --directory .
uv venv .venv --python 3.13
uv pip install --python .venv/bin/python -r requirements-analysis.txt
make verify-revision
```

`make verify-revision` checks original evidence, independently recalculates follow-up condition/paired summaries, binds 73 displayed numbers to the verified reports, reconstructs the new operational summaries from retained traces, checks integration against the archived documents, verifies source-bound proof receipts, and checks the exact delivered PDF and retained renderings. It runs no brokers. See the release guide for detached archive verification and the distinction between GitHub source archives and the named sealed artifact.

## Reanalyze and rebuild in a working copy

```sh
make analyze
make analyze-followup
make paper
.venv/bin/python bench/check_paper.py
```

Original analysis reconstructs every retained timing record, ID set, percentile, throughput and occupancy value. Follow-up analysis also checks every planned invocation, input seal, image/binary receipt, raw-file manifest, stored-payload outcome, CPU bracket and inventoried syscall trace. Paired comparisons use jointly completed blocks and retain unavailable pairs. Neither analyzer imputes throughput for failed workloads or combines original and follow-up measurements.

The PDF build uses `latexmk`, pdfLaTeX, BibTeX and `plainurl.bst`. A rebuilt PDF can differ across TeX environments and needs its own honest rendering/visual review before the provenance gate can pass. The supplied visual receipt covers only the shipped PDF. Keep the sealed distribution unchanged and perform reanalysis in a working copy.

The selected Lean model is `formal/DeliveryModel.lean`. Its original and subsequent homelab compilation receipts are retained, including the version 1.2.0 receipt `revisions/20260924-followup/lean-recheck.json`. Compilation checks ten abstract declarations; it does not verify broker implementations, the harness, stable storage, or statistical coverage.

## Run a new follow-up campaign in the homelab

Choose a new campaign name; existing names, directories and invocation destinations cannot be reused. The following commands execute the current follow-up protocol, not the frozen historical campaign:

```sh
python3 bench/followup/run.py prepare --campaign newstudy01 --seed 2026092501
python3 bench/followup/run.py bootstrap --campaign newstudy01
python3 bench/followup/run.py run --campaign newstudy01
python3 bench/followup/run.py cleanup --campaign newstudy01
```

Read `python3 bench/followup/run.py --help` and the protocol before starting. The runner pins the homelab context, snapshots inputs, provisions only its owned namespace, builds/tests remotely, and verifies deployed bytes. A failed timed outcome can proceed to the next planned cell only after verified broker shutdown and store cleanup. An incomplete invocation or infrastructure/reset failure pauses without automatic replay. Preserve the attempt and investigate instead of overwriting it.

Publication-error recording covers returned errors and caught panics after workers join. Abrupt driver/host loss before serialization remains outside that guarantee. New measurements require their own analysis and must not replace historical observations. The older `bench/run_homelab.py` campaign/attempt workflow remains available for reproducing the earlier functional-validation harness; it is not the collector used for the new study.

## Version and publication boundaries

Version 1.1.0 preserves the preceding 30-page manuscript and evidence. Version 1.2.0 added a separately identified experimental campaign and separate article/supplement. Version 1.3.0 combines those documents into one article with appendices and adds descriptive reporting against the unchanged evidence. Existing sealed distributions are never overwritten. Input snapshots and manifests identify pre-Git observations without inventing a retrospective Git history.

`SHA256SUMS` covers delivered source, raw/derived evidence, documents and QA, excluding caches and duplicate distributions under `releases/`. The release builder verifies a fresh extraction and refuses an existing version. These checks establish content consistency, not independent certification of collection time, complete fault coverage, or scientific peer review. The manuscript and software were developed with AI assistance, disclosed in the article.
