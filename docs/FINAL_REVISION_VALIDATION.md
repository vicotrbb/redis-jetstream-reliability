# Scientific revision and submission validation

Version 1.2.0, completed 25 September 2026 UTC. This is the current validation narrative. It covers the separately collected experimental extension, revised article, supplement, and release preparation. The preceding version 1.1.0 narrative and document are preserved in `revisions/20260924-followup/prior-paper-and-validation.tar.gz` and in the unchanged public version 1.1.0 release. Historical receipts do not certify the current PDFs.

The title, Victor Bona authorship, original LaTeX template, and main section order are preserved. The contribution is a reproducible comparison of specific recovery policies, consumer concurrency, and acknowledgment costs under documented conditions. Full hand proofs and detailed historical diagnostics are retained in the supplement. The article distinguishes observed results, conditional model statements, source-based explanations, and untested properties. This is internal scientific and artifact validation, not external peer review or a guarantee of acceptance.

## New experimental evidence

All broker workloads, Go runtime tests, tracing, and Lean compilation ran strictly through `kubectl --context homelab`. The workstation performed authoring, offline analysis, verification, and PDF production. The follow-up protocol and measurement inputs were sealed before each primary deployment began. The prospective plans use three separately provisioned deployments on the same two physical hosts; they are not independent-host replications.

Each trial starts a fresh broker process and exclusive store. The common warm-up uses a separate stream that is deleted before measurement. Verified process-group disappearance and port closure precede store cleanup. Publication trials share a 15-second admission budget and retain their completion tail in the elapsed denominator. This removes cross-trial broker-file accumulation and the historical unmatched-duration comparison. It does not reset host caches, unrelated load, or physical-device history.

All 612 planned primary outcomes were collected, with no primary trial replay:

| Family | Planned | Complete procedures | Failed |
|---|---:|---:|---:|
| Publication | 216 | 205 | 11 |
| Drain | 96 | 96 | 0 |
| Active recovery | 240 | 240 | 0 |
| Plain Redis read controls | 12 | 12 | 0 |
| Synchronization diagnostics | 24 | 24 | 0 |
| Compression/payload diagnostics | 24 | 24 | 0 |
| Total | 612 | 601 | 11 |

For plain-read controls, completion means completion of the observation procedure. The message remained pending without redelivery. All active episodes returned the original application identity and cleared pending state; 120 used killed victims and 120 used live, deliberately unacknowledging victims. Exact control reference-to-loop-completion times range from 0.503 to 0.699 seconds for the nominal 0.500-second budget. These endpoints belong to the new observations and are not imputed to historical controls.

Four publication failures occurred during warm-up and seven during timed measurement. Timed failures retain 14,651 confirmed requests and 22 requests with unknown client outcomes. Warm-up failures have no timed sample. Failed prefixes are not treated as completed-workload throughput, and later broker counts are not substituted for client confirmations. Every condition and paired contrast reports its available completion count. Ten failures occurred in always profiles and one in historical JetStream periodic mode.

The full analyzer reconstructed 80,263,171 timed event records, including the 22 unknown outcomes, and separately checked 96 preload traces. All 349 completed non-recovery workloads passed runtime comparison of the complete stored identifier set and all 512 expected payload bytes per message outside timing. The retained readback receipt records counts and comparison results, not a second copy of every read-back payload. This supports the recorded integrity check; it does not establish power-loss durability or comparison of every payload delivered during the timed drain.

Collection receipts, input snapshots, reset observations, environment state, raw manifests, and cleanup records are under `followup/campaigns/main01/` through `main03/`. All three namespaces were removed after collection. Six excluded development pilots, their failures, unexecuted cells, and cleanup remain documented in [FOLLOWUP_VALIDATION.md](FOLLOWUP_VALIDATION.md). The main01 tracer initializer's single premeasurement restart is disclosed there; its cause is not inferred, and broker/driver work containers did not restart during measurement.

## Results and claim boundaries

| Concern | Evidence added or correction made | Remaining boundary |
|---|---|---|
| Storage accumulation and duration confounding | Fresh process/store for every trial, common warm-up, matched admission budgets, three deployments. | Shared hardware, caches, filesystem, and device activity remain. No isolated causal synchronization-policy estimate. |
| Residual timeout versus failure detection | Matched live unacknowledging and killed victims, measured reference ages, first-request observations, and exact completion endpoints. | One pending message, periodic profiles, available survivor demand, and no concurrent publication load. |
| Current implementation relevance | Added Redis 8.10.2 and NATS 2.15.0 beside the historical versions; current Redis CLAIM is a separate arm. | Version-specific behavior and fixed clients, not all releases or client implementations. |
| Consumer/driver scaling | 65,536-message drains at 1/16 consumers and 2/4 driver CPUs, with phase cgroup/host counters. | Finite workloads and measured client path, not a broker saturation ceiling. |
| Always-mode explanation | Matched traced/plain diagnostics capture fsync and fdatasync across threads, file paths, errors, phase boundaries, and perturbation. | Aggregate syscall counts do not map each confirmation to a physical flush or prove the whole performance gap's cause. |
| Compression hypothesis | Crossed original filler/template-bank payloads with inherited/disabled Btrfs compression policy; verified file flags. | One filesystem/device; no measured extent-compression ratio or dominant-cause claim. |
| Failure and sparse-tail reporting | Failed attempts and prefixes retained; sample counts, ranks, missing pairs, and influential p99 observations shown. | Completed-run summaries are conditional and empirical p99 is not a stable population-tail guarantee. |
| Uncertainty | Separate campaign means and observed ranges, with paired completed-block contrasts. | No asserted deployment-level confidence coverage or independent-hardware generalization. |
| Durability contracts | Append synchronization and consumer-progress persistence distinguished using pinned source. | No storage-fault, power-loss, host-failover, or equivalent-guarantee result. |

All three deployment-specific comparisons support the reported recovery-age direction. Sixteen consumers increased current memory/periodic drain throughput by 10.43 to 14.49 times across deployment-specific comparisons; mean trial cycle p99 also increased in all eight conditions. Driver quota affected observed rates, and no drain cgroup throttling increments were recorded. Current periodic/memory publication ratios at sixteen publishers average 0.8257 for Redis and 0.8207 for JetStream. These are configuration-specific observations, not universal product rankings.

The trace/source evidence supports shared synchronization across concurrent Redis appends in the measured path. Compression-policy ratios span 0.935 to 1.063 across the diagnostic comparisons. Neither observation establishes a dominant filesystem cause. The supplied audit's stronger causal interpretations were not adopted merely because they appeared in a review. [EXTERNAL_REVIEW_RESPONSE.md](EXTERNAL_REVIEW_RESPONSE.md) maps concerns to changes and evidence.

## Numerical and artifact checks

`make analyze-followup` completed the full raw-event reconstruction. `bench/check_followup.py` separately recalculated summary and pairing arithmetic using the standard library. It verified 2,373 raw-file identities, 108 sealed input entries, 288 campaign condition summaries, 324 paired contrast cells, and 732 planned paired blocks across twelve contrast families. It also checked the fresh proof and cleanup receipts. `bench/check_manuscript_numbers.py` binds 60 displayed numerical values and outcome relationships to that verified report. It is a document-binding check, not another independent experimental execution.

The retained logs and JSON receipts are in `revisions/20260924-followup/`, including `final-analysis.log`, `followup-check.json`, `manuscript-number-check.json`, and `legacy-evidence-check.json`. Five offline analyzer rejection tests pass, covering missing required events, missing thread traces, forged invocation completion, entirely failed conditions, and incomplete pairs. Nine package-integrity tests pass, including changed/missing/unlisted content, unsafe paths, duplicate members, symbolic links, version disagreement, and refusal to overwrite an existing release before any write. These test artifact logic, not broker reliability. Three Go tests with the race detector passed in each primary homelab bootstrap; the pilot record identifies their functional coverage.

All 537 original raw/environment files remain identical to their original evidence lock. Reanalysis again checked 419 completed original timing trials and 17,411,288 message records. The original 420 aggregate rows, thirteen paired effects, numerical tables and four figures are preserved. Original and follow-up data are not pooled. D038's missing client trace, the interrupted D043 trace, and exact historical censor endpoints remain unavailable. No later experiment reconstructs these missing observations.

## Formal verification and primary-source grounding

The selected Lean model is unchanged, with source SHA-256 `169fa4a50504ba59b34a3159bcdc0c1a1d89139c28a323856e4be40805928d03`. A fresh Lean 4.24.0 kernel compilation in the homelab passed all ten selected declarations after benchmark collection. `lean-recheck.json` and `lean-recheck.log` bind the source, compiler, invocation, and logical dependencies. The original thirteen explicit hand statement/proof environments remain in the supplement. Their assumptions and domains are retained; Lean does not verify Redis, NATS, the measurement harness, storage guarantees, or statistical coverage.

The initial proof pod did not schedule because its manifest lacked the selected node's required toleration. Its readiness wait expired before any compiler invocation. The owned pod was corrected, its identity and absence of prior invocation were verified, and an explicitly recorded continuation performed the single successful compilation. Both launcher source snapshots, the initial failure log, scheduling correction, continuation, compiler result, and namespace cleanup are retained. This was a setup correction, not a failed proof silently replaced by a success. The proof namespace was removed and its absence checked.

Pinned implementation and release sources were rechecked for reclamation, current CLAIM reply/scheduling behavior, JetStream expiry, append synchronization, synchronization-error handling, and consumer-state persistence. [FOLLOWUP_SOURCE_REVIEW.md](FOLLOWUP_SOURCE_REVIEW.md) records those distinctions. Related work now includes the Kafka/RabbitMQ comparison, SPECjms2007, pinned OpenMessaging Benchmark drivers, MillWheel, and Kafka transaction semantics. The paper makes no exhaustive-novelty or first-comparison claim. Source-supported mechanisms are separated from experimentally identified causes.

## Document and provenance verification

The main article has **21 pages and 44 cited references**, including seventeen pages before the bibliography. The supplement has twenty pages and eight cited references. Both preserve the established typography. All 41 pages were rendered and visually inspected, with additional full-page checks of dense figures, tables, proofs, the abstract, and the claim-to-evidence map. The final figure-label overlap and long numerical lines were corrected and the changed pages reinspected. Fonts are embedded; content checks reject em dashes, undefined references, missing glyphs, and overfull boxes.

Current PDF SHA-256 values are:

- Main: `ca59e23609e4814399ba5321a793046c69272a3c86a0b077f087101acfd381b2`.
- Supplement: `2d8acad2a7d634ec4b2df8eec3d820d847bf3b420ac760eff9041464cfdbb60d`.

`data/derived/build-receipt.json` and `supplement-build-receipt.json` record successful compilation and exact inputs, outputs, and logs. `paper-check.json` verifies both documents. `visual-review.json` and `supplement-visual-review.json` bind the inspected PDFs to every source input and retained page rendering. The provenance gate rejects all superseded review receipts. Source changes after inspection require renewed applicable checks; a checksum update cannot substitute for review.

## Release and publication boundary

Version 1.2.0 carries CC-BY-4.0 for original paper/research material and MIT for original code/formalization, with third-party scope retained in `LICENSE.md`. The release builder refuses version reuse. It verifies the archive, extracts it to a fresh directory, runs five offline document/evidence checks, and rejects any change to delivered bytes during those checks. Actual sealing results are recorded in the distribution's `RELEASE.json` and `VERIFICATION.log`; this narrative does not substitute for successful execution of that gate. The detached manifest identifies the sealed distribution; the repository manifest identifies each checkout. Version 1.1.0 is preserved unchanged.

Public GitHub hosting is distinct from DOI-bearing archival custody and peer review. [GITHUB_PUBLICATION.md](GITHUB_PUBLICATION.md) records hosting status, and [release/README.md](../release/README.md) gives reproduction and deposit instructions. No Zenodo deposit, DOI assignment, journal submission, external experimental replication, or claim of perfection is made. The article supports the stated descriptive and conditional conclusions within its measured scope; broader reliability and durability claims remain outside this study.
