# An Empirical Evaluation of Message Delivery Reliability and Recovery Characteristics in Redis Streams and NATS JetStream

This folder contains the manuscript, experiment implementation, raw homelab evidence, deterministic statistical analysis, and generated figures. The article follows the LaTeX typography of `bfs-avoidance-frontier`: an 11-point single-column article, 1.1-inch margins, the same author block, numbered mathematical results, and a linked bibliography.

**Artifact version 1.1.0, prepared 24 September 2026.** The contribution is an auditable, computationally reproducible comparison of specific recovery policies, concurrency behavior, and acknowledgment costs under documented conditions in one homelab deployment. It is a descriptive case study. The original paper and research material use CC-BY-4.0; original code and formalization use MIT. See [LICENSE.md](LICENSE.md), [CITATION.cff](CITATION.cff), and [release/README.md](release/README.md).

The versioned release archive has a detached SHA-256 checksum and an internal file manifest. `release/manifest.json` identifies its exact manuscript, evidence lock, and primary statistics. The release builder refuses to overwrite an existing version. Zenodo deposit, DOI assignment, and journal submission have not occurred.

## GitHub repository and frozen release

[Repository](https://github.com/vicotrbb/redis-jetstream-reliability) · [Version 1.1.0 and downloadable paper/artifact](https://github.com/vicotrbb/redis-jetstream-reliability/releases/tag/v1.1.0)

Tag `v1.1.0` imports the exact validated artifact snapshot. The `main` branch adds repository setup, this publication guide, and a refreshed manifest for the current checkout. The sealed version 1.1.0 archive, paper, and evidence remain unchanged. The archive and its detached checksum are GitHub Release assets; local copies under `releases/` are excluded from Git. The repository itself retains the source, raw data, figures, PDFs, compiler evidence, and validation records.

See [docs/GITHUB_PUBLICATION.md](docs/GITHUB_PUBLICATION.md) for tag provenance, exact release downloads, and verification. Statements in the frozen release about publication state describe its preparation checkpoint. GitHub hosting supplies public access; it does not constitute a Zenodo deposit, DOI assignment, independent replication, or journal peer review.

## Read the paper

- `output/pdf/redis-jetstream-reliability.pdf`: final reader-facing PDF.
- `paper/main.tex`: editable source; `abstract.tex`, `results.tex`, and `conclusion.tex` contain the corresponding prose.
- `data/derived/statistics.json`: numerical results and integrity receipts.
- `data/derived/aggregate.csv`: machine-readable estimates and confidence intervals.
- `formal/DeliveryModel.lean` and `formal/verification.json`: ten conditional model declarations checked with Lean 4.24.0 on the homelab.
- `docs/PRIMARY_SOURCES.md`: verified official documentation, pinned source-code references, and literature boundaries.
- `docs/MANUSCRIPT_REVIEW.md`: internal AI-assisted methods/proof/source review, not external peer review.
- `docs/FINAL_REVISION_VALIDATION.md`: current revision coverage, validation, and scientific limits.
- `data/derived/visual-review.json`: current document QA, bound to the PDF hash and retained page renderings.
- `docs/ARTIFACT_MAP.md`: historical measured sources, later validation snapshots, and current deliverables.

## Experimental scope

The only broker/test environment is `kubectl --context homelab`. The original measurement namespace was `msgrel-20260923`; later validation uses separate namespaces. The workstation performs authoring, raw-data verification, statistical analysis, and LaTeX compilation only.

Redis 7.4.2 and NATS Server 2.10.24, one replica each, run on `homelab-01`. The Go 1.24.4 driver runs on `homelab-02`. The broker volume is Btrfs/NVMe with `compress=zstd:3`; payloads contain an eight-byte ID and repeated `x` bytes, so they are highly compressible. Six persistence profiles, one shared consumer group/durable consumer, 512-byte application payloads, explicit confirmed acknowledgment, and independent TCP connections are used.

- RQ1: 120 consumer SIGKILL/recovery trials plus 10 Redis no-reclaimer controls. Timeout 250/1000 ms, kill age 10%/75%, Redis reclaim sleeps 10/100 ms.
- RQ2: 300 completed fixed-backlog trials, 16384 messages each, C=1/2/4/8/16, ten randomized complete blocks.
- RQ3: 60 planned five-second closed-loop publication trials, 16 outstanding publishers (one retained Redis-always timeout and 59 completed planned trials); a separate 60-trial one-publisher sensitivity uses 1024 messages.
- Two 12-trial pilot datasets are excluded from the reported main estimates.

The fixed-backlog and closed-loop latencies are not open-loop production SLA estimates. Consumer death is not a power-loss test. Model theorems are conditional mathematical results, not formal verification of the vendor implementations or a universal empirical ranking. All runtime incidents and protocol changes are retained in `docs/DEVIATIONS.md` and `data/environment/`.

## Delivered validation

All 550 planned experimental outcomes are accounted for: 300 completed drain trials, 59 completed primary publication trials plus one retained timeout, 60 completed serial trials, 120 recovered consumer kills, and ten nominal-budget negative controls. Raw timings and adjudication records remain available. The current validation record is `docs/FINAL_REVISION_VALIDATION.md`; current document QA is `data/derived/visual-review.json`, identified by the reviewed PDF hash. `docs/EXECUTION_RECEIPT.md` concerns the historical 25-page version, and `docs/REVISION_VALIDATION.md` concerns the subsequent 27-page version. The immediately preceding 29-page document is preserved in `revisions/20260924-submission/previous-source-and-paper.tar.gz`. Those historical counts and hashes must not be attributed to the current PDF.

The temporary namespace was removed after data and proof collection. `data/environment/cleanup.json` records the successful delete and the subsequent Kubernetes `NotFound` confirmation. Reanalysis requires no live broker.

## Reanalyze the existing measurements

The pinned analysis dependencies are in `requirements-analysis.txt`. For example:

```sh
uv venv .venv
uv pip install --python .venv/bin/python -r requirements-analysis.txt
python3 bench/verify_release.py --directory .
make analyze
.venv/bin/python bench/check_revision.py
make paper
.venv/bin/python bench/check_paper.py
```

Python 3.13 was used for analysis. LaTeX requires `latexmk`, pdfLaTeX, BibTeX, the packages declared in `paper/main.tex`, and `plainurl.bst`. Verify the distributed files before rebuilding, and keep the sealed archive unchanged. Reanalysis and compilation write to the extracted working copy. A new PDF needs its own rendered-page inspection and visual-review receipt before `make verify-revision` can pass; the distributed receipt only covers the shipped PDF. `make verify` checks existing data and the compiled paper; it does not start a broker or execute a performance experiment on the workstation. The release guide separates verification of the delivered document from rebuilding it.

`bench/analyze.py` verifies every retained main/durability/serial raw CSV against its summary: IDs, ordering, percentiles, means, throughput, worker counts, and finite-window occupancy bounds. It reconstructs recovery intervals from the recorded monotonic timestamps. It then generates tables, figures, 10000-resample bootstrap intervals, and paired block ratios. Publication metrics condition on completed planned trials; the failed D038 outcome is retained in a separate adjudication ledger, its accidental replay is excluded, and comparisons use common completed blocks. No failure is assigned a made-up throughput or latency. A p99 interval describes uncertainty in the mean of run-level p99 values, not a pooled-message percentile or a distribution-free prediction interval.

## Run new experiments, only in the homelab

The paper's original campaign is frozen. New collection requires explicit campaign and attempt IDs, a fresh namespace, and a fresh attempt directory. It never writes to `data/raw`, `data/environment`, or the original adjudication ledger.

```sh
make experiment CAMPAIGN=study20260924 ATTEMPT=a001
make collect CAMPAIGN=study20260924 ATTEMPT=a001
make clean-homelab CAMPAIGN=study20260924 ATTEMPT=a001
```

Use new IDs for each attempt. IDs contain 1-20 lowercase DNS characters. The namespace is `msgrel-<campaign>-<attempt>`. A namespace ownership token is checked before collection or cleanup. Existing attempt and series destinations are rejected. Failed attempts stop and remain inspectable; there is no automatic replay or resume. Only the dedicated namespace is created or removed.

Inputs, their content seal, and execution records reside in `campaigns/<campaign>/attempts/<attempt>/`. Each collection receives a new timestamped directory containing raw records, logs, environment observations, and an identity-bound hash manifest. Structured observations, failure ledgers, and runtime records carry campaign and attempt IDs. A mismatch fails validation. A content seal records an artifact snapshot, not a successful scientific outcome. New data require a separate analysis and outcome adjudication; they cannot be substituted into the publication's fixed historical analyzer.

The runner compiles and executes the Go program in the homelab using locked modules and pinned images. It snapshots the selected source before execution. The original measured implementation is retained in `revisions/20260924/original-source-and-paper.tar.gz` and the earlier harness snapshots. The revised collection harness adds failure capture and campaign identities; new measurements would constitute a separately identified campaign with that revision.

The publication path records attempted IDs, successful confirmations, and unknown outcomes after returned errors or caught worker panics. Buffered partial observations are serialized and synchronized before inventory and cleanup. Cleanup errors are recorded separately. Abrupt process or host loss before serialization can still lose buffered observations. This correction cannot recover the original D038 timings or confirmation count.

Redis publication and acknowledgment use five-second default socket read and write timeouts, not an absolute whole-call deadline. Positive blocking `XREADGROUP` calls use a socket read timeout of `BLOCK + 10 seconds`: 10.1 seconds for ordinary 100 ms reads and 15 seconds for the victim's five-second read. NATS publication and acknowledgment use five-second response waits; Fetch receives its explicit 100 ms or five-second wait. Administrative Redis socket settings and NATS response waits are 30 seconds. See `docs/SOURCE_REVALIDATION.md` for pinned sources.

For a bounded functional validation of the revised harness, including ambiguous publication errors, use a separate attempt:

```sh
make validate-homelab CAMPAIGN=validation20260924 ATTEMPT=a001
```

These functional checks are excluded from the paper's performance dataset. They cover successful and ambiguous publication in memory profiles, active recovery in both periodic profiles, and a Redis no-reclaimer control. The workstation performs data analysis and document compilation; Go tests and broker execution run only in the homelab.

Future recovery records distinguish the nominal budget origin/deadline, observation of the timer notification, completion of survivor work and controller waiting, and reconciliation start/end. A timer timestamp is null when its branch was not taken; a receipt returned during shutdown is retained separately. The loop-completion timestamp is taken immediately before sending its terminal result. These fields measure the observation procedure, not an exact kernel timer-firing instant or an upper bound on broker response time. They do not exist in the frozen historical records, whose exact censor endpoints remain unavailable.

## Evidence layout

`data/raw/{main,durability,serial}` contains JSONL summaries and one gzip-compressed CSV per measured trial. Main/serial event columns are application ID, publication invocation, publication confirmation, receive-request invocation, client receipt, consumer-acknowledgment completion, and worker. Times are integer Linux monotonic nanoseconds from the driver node. The durability files contain publication events only; their broker-side integrity check reconciles stored count, not all payload identities. `data/raw/recovery/summary.jsonl` records receipt, kill-call start, process-exit observation, redelivery, configuration, identity checks, and censoring. Pilot directories are not inputs to inference.

`data/environment` records hardware, exact image digests, effective server configuration, initial and resumed driver details, source revisions, retained error logs, and periodic cgroup/resource telemetry. The failed setup attempt remains in the original raw main summary. A later failed warm-up/cleanup is preserved in its original panic log and the deviation ledger, rather than reconstructed as a successful timing sample. `SHA256SUMS` covers delivered source, evidence, and final artifacts, excluding caches and LaTeX intermediates.

The delivered analyzer requires `data/environment/outcome-manifest.json` and the failure ledger, so a missing ledger cannot silently promote the diagnostic replay into a planned success. The original raw and environment file set is additionally bound to a frozen hash inventory, checked before analysis. New campaign records and their content seals remain under `campaigns/` and cannot be classified with the old failure ledger.

The dataset is synthetic and was collected locally in the homelab. The manuscript and software were developed with AI assistance. The repository and versioned release provide public GitHub access. No DOI-bearing archival deposit, external artifact evaluation, scientific peer review, or journal acceptance is claimed.

## Revision validation

The 2026-09-24 revisions add storage-history disclosure, influence and execution-order diagnostics, deadline/source corrections, and safe future collection. `data/derived/robustness.json` retains all leave-one-out and paired-block diagnostics plus interruption segment memberships. The final pass also provides all 59 publication sample counts and p99 ranks in `data/derived/publication-tail-samples.csv` and a 556-record retrospective inventory in `data/derived/attempt-outcomes.{json,csv}`. The inventory comprises 550 planned outcomes and six additional documented attempts, excludes pilots and infrastructure provisioning, and does not invent unavailable stage durations. These post-observation diagnostics do not replace primary observations or establish confidence-interval coverage.

`revisions/20260924/baseline-manifest.json` and `original-evidence-lock.json` preserve original provenance. `revisions/20260924-final/baseline-manifest.json` identifies the previously audited 816-file delivery. `bench/check_revision.py` independently checks the unchanged primary numerical results, original evidence, template, sensitivity summaries, sealed collections, and source-bound Lean receipts. `bench/check_document_provenance.py` rejects stale document QA. Run `make verify-revision` after analysis, paper compilation, and visual review of that exact PDF. A new PDF build needs a corresponding new visual-review receipt. The current resolution and scientific limits are recorded in `docs/FINAL_REVISION_VALIDATION.md`.
