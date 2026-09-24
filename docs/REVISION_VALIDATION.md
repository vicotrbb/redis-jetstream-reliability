# Historical scientific revision and validation record

This record describes the first 24 September revision, whose 27-page PDF has SHA-256 `458f1f005872ddb807a9273315b65c28132f2b888889388b6288abf8d56ee555`. Its source and PDF are preserved in `revisions/20260924-final/previous-revision-source-and-paper.tar.gz`. For the current document and later recovery-endpoint validation, see [FINAL_REVISION_VALIDATION.md](FINAL_REVISION_VALIDATION.md). Counts and validation statements below apply to this historical checkpoint.

Date: 24 September 2026. Scope: implement the supplied scientific audit's revisions while preserving the article's title, author, section order, LaTeX template, original observations, and primary numerical results.

The six required audit corrections have been addressed. The resulting article supports a bounded descriptive study of the recorded workloads and deployment. It does not establish universal broker correctness, power-loss durability, a general performance ranking, or the absence of every possible scientific error. Internal validation is distinct from independent peer review.

## Disposition of the audit findings

| Finding | Revision and evidence | Remaining boundary |
|---|---|---|
| Unequal accumulated storage history | Methods, RQ3 results, discussion, and threats now explain that Redis stream deletion does not reset its unre-written AOF, whereas JetStream removes individual stream stores. The paper reports final logical AOF lengths of 2,590,379,564 and 907,510,749 bytes and the periodic profile's `aof_delayed_fsync:1`. | These observations establish the asymmetry, not that it caused a particular stall. Independent deployments or a justified storage-reset design are needed to isolate that effect. |
| Fragile small-sample intervals | Added reproducible leave-one-trial-out, leave-one-common-block-out, early/late, and interruption-segment diagnostics. Table 5 and accompanying text report influence and variation. The bootstrap assumption is explicitly IID completed block vectors as a working resampling model. Intervals remain nominal and conditional. | Neither diagnostics nor additional bootstrap draws establish independence, correct coverage, or repeatability across deployments. |
| Lost failed-trial measurements | D038 remains a failed planned trial with unavailable client confirmation history. Its replay remains excluded. The revised publication harness preserves partial attempts, confirmed and unknown outcomes, primary errors, and caught worker panics, and synchronizes those records before cleanup. | D038's missing timings cannot be recovered. Abrupt driver or host loss before buffered observations are serialized can still lose them. The new safeguards were not used retroactively in the original campaign. |
| Campaign/adjudication contamination risk | New collection requires explicit campaign and attempt identifiers, fresh destinations and namespaces, matching structured-record identities, exclusive writes, input snapshots, and sealed collections. Namespace ownership is checked before collection or cleanup. Original analysis first verifies a frozen inventory of the original raw and environment files. | A new performance campaign needs its own adjudication and analysis; it is deliberately not merged into the manuscript's historical dataset. |
| Incorrect Redis receive timeout description | Corrected the manuscript, README, and deviation log. Positive blocking `XREADGROUP` calls have a command-specific socket-read timeout of `BLOCK + 10 s`: 10.1 s for normal/control reads and 15 s for the victim's initial read. General five-second read/write settings are not a whole-call five-second budget. | Receive blocking, socket timeouts, publication waits, and acknowledgment waits remain different quantities. The actual original measured settings are unchanged. |
| Incorrect source anchors | Corrected NATS `opts.go` to lines 2188-2195 and Redis `redis.conf` to lines 1429-1499 at the pinned commits. Added the pinned go-redis timeout calculation to the bibliography. | Source inspection supports statements about the selected releases, not every future release or execution. |

The full publisher HTML for Lim, Gu, and Yoon was also assessed. The related-work section now distinguishes their KEDA-driven autoscaling workloads from this study's fixed within-trial concurrency, recovery interventions, and persistence-policy treatments. Its DOI and publication metadata were verified. No first-comparison claim was added. The detailed source and foundational audit is in [SOURCE_REVALIDATION.md](SOURCE_REVALIDATION.md).

The mathematical presentation now states positive denominators and parameter domains explicitly, identifies the occupancy decomposition as a per-trial identity, and separates the finite-delay theorem from an alternative model with its upper-bound premise removed. The synchronization-service bound specifies a window containing complete nonoverlapping operations. These refinements do not change the measured results or enlarge the Lean proof's scope.

## Preservation and analysis

Before editing, all 596 entries in the delivered checksum manifest were verified. The original source, manuscript, PDF, derived statistics, and other non-observation files were archived in `revisions/20260924/original-source-and-paper.tar.gz`. `baseline-manifest.json` retains the initial hash inventory, and `original-evidence-lock.json` binds the original campaign's evidence.

All **537 original raw-data and environment files remain byte-identical**. The primary `data/derived/statistics.json` is exactly equal to the archived original. All 419 completed primary timing trials remain in their original analysis: 300 concurrency, 59 publication, and 60 serial trials. The failed planned publication outcome, diagnostic replay exclusion, 120 active recovery episodes, and ten negative controls retain their original interpretation. Every active recovery observation was also checked to follow confirmed victim-process exit.

New diagnostics are generated by `bench/robustness.py`, invoked from `bench/analyze.py`, and retained as JSON, CSV, and LaTeX in `data/derived/robustness*`. `bench/check_revision.py` separately recomputes the mean, median, and leave-one-out summaries using Python's standard-library statistics, checks all thirteen paired-effect directions, verifies evidence and collection seals, and confirms the unchanged primary estimates and template.

For example, JetStream-always's mean of trial p99 values remains 579.6 ms. Its median is 160.3 ms, and omitting D040 solely for diagnosis gives a mean of 150.5 ms. D040 remains in the primary estimate. All thirteen paired effect directions survive each corresponding leave-one-common-block-out calculation. That directional consistency does not remove uncertainty in effect magnitude or establish a causal explanation of execution-order variation.

## Homelab validation

All broker execution, Go test execution, and fresh Lean compilation for this revision used **`kubectl --context homelab`** in isolated revision namespaces. Local work was limited to authoring, source inspection, data analysis, and document production. Validation observations are separate from the paper's performance data.

The final harness validation is campaign `rev20260924`, attempt `a004`, with an exit status of zero. Its immutable collection is:

`campaigns/rev20260924/attempts/a004/collections/20260924T165357741389Z/`

Its retained `run.log`, `run-result.json`, input seal, collection manifest, raw records, and environment receipts establish:

- **Three Go regression tests passed with the race detector.** They cover returned request failures, caught worker panics, confirmed versus unknown attempts, primary-error preservation, and destination/identity protection.
- **Nine campaign-isolation tests passed.** They cover stale campaign and attempt identities, mismatched identity sidecars, changed or added sealed evidence, symlinks, invalid identifiers, destination reuse, and namespace ownership.
- **Six real broker validation scenarios passed.** Each system completed a 32-message drain, a short successful publication run, and publication with an injected lost confirmation after a real successful append. Both injected failures retained 18 confirmed requests, one unknown request, and 19 stored messages, demonstrating why an unconfirmed request cannot be classified as absent. These short checks use the memory profiles and validate harness behavior, not durability or comparative performance.

The final driver was built with Go 1.24.4 for Linux/amd64. Its binary SHA-256 is `4a2d6fc4829f32dc6a3374dd13ca93d42ea73313a6706ac88ebf8ff9f479b6e2`. The input snapshot contains the locked module files; module downloads were verified before execution.

Attempt `a001` was stopped by local sandbox network access before cluster creation. Attempt `a002` retained a dependency-download failure and a sealed collection. After bounded download retries were added, attempts `a003` and `a004` passed; `a004` includes the additional identity-sidecar regression. Earlier failures are retained as setup outcomes and are not counted as successful validations or performance trials.

Fresh compilation of the unchanged formal model succeeded with Lean 4.24.0 inside `msgrel-rev20260924-a002`. All **ten declarations** compiled with warnings treated as errors. The transitive logical dependency lists match the original receipt, with no admitted proof or custom axiom. See `revisions/20260924/lean-recheck.json` and `lean-recheck.log`. This checks the selected abstract model, not either broker implementation or the validity of the bootstrap intervals.

## Document and artifact checks

The final PDF has **27 pages and 31 references**. All pages were rendered and visually inspected; changed reference pages were rendered again after pagination adjustment. Tables, figures, mathematical notation, and bibliography links are legible without clipping or overlap. The build has no unresolved citations or references and no overfull boxes. Source and extracted PDF text contain no em dashes. The title, author, original section order, and template preamble are preserved, apart from loading the added generated diagnostic values.

Reproduction commands from the project root:

```sh
make analyze
make paper
make verify-revision
make checksums
```

`revisions/20260924/revision-check.json` records the automated revision checks. `SHA256SUMS` identifies the final deliverable, including preserved evidence, original source archive, revised analysis and harness, homelab receipts, and revised PDF. The temporary revision namespaces are removed only after their records have been collected; the cleanup and final absence check are retained in `revisions/20260924/cleanup.json`.

## Scientific limits that remain explicit

The revised paper answers its three research questions within the measured deployment, versions, profiles, client paths, and workloads. Independent campaign repetitions, storage or power faults, large-PEL recovery, recovery under publication load, complete payload readback, and implementation-level verification remain outside its evidence. The serial sensitivity changes duration and workload size as well as publisher count, so it does not isolate batching. Different consumer-state persistence paths still prevent an equal-guarantee interpretation of cross-system always-mode drain performance.

These limits are carried into the methods, discussion, threats, abstract, conclusion, and claim-to-evidence map as applicable. They are not concealed by a general claim of reliability or perfection. No public archival deposit, journal submission, external artifact evaluation, or independent peer review has been performed by this revision.
