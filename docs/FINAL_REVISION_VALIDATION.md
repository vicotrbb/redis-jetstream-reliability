# Scientific revision and submission validation

Revision date: 24 September 2026. This is the current validation narrative, including submission preparation for version 1.1.0. The current PDF and document-source identities are recorded in `data/derived/build-receipt.json`, `paper-check.json`, and `visual-review.json`. Earlier 25-page, 27-page, and pre-submission 29-page receipts are historical; [ARTIFACT_MAP.md](ARTIFACT_MAP.md) identifies their archived documents and source snapshots.

The revisions preserve the title, author, section order, template, original evidence, primary estimates, mathematical results, and scientific scope. The preceding scientific pass addressed reporting, observation, and provenance issues from the second audit; the submission pass below corrects remaining causal wording and prepares the licensed release. Missing historical observations remain unavailable, and disclosed design limitations have not been experimentally removed. The contribution is an auditable, computationally reproducible descriptive comparison of specific recovery policies, concurrency behavior, and acknowledgment costs under documented conditions.

## Submission preparation, version 1.1.0

The initial submission-preparation state matched all **937** checksums reviewed by the latest audit. `revisions/20260924-submission/baseline-manifest.json` preserves that inventory; `previous-source-and-paper.tar.gz` preserves the prior manuscript, PDF, code, derived results, and receipts. The three publication-preparation changes are:

1. Replace residual causal descriptions of persistence with observed configuration comparisons. State storage-history confounding beside the RQ3 results. Clarify that RQ1 measures recovery after a kill and lacks a matched live, unacknowledging control through expiry; message eligibility is not death detection.
2. State the same bounded contribution in the abstract, introduction, discussion, and conclusion, preserving all primary values and formal statements.
3. Prepare version 1.1.0 with CC-BY-4.0 for original paper/research material, MIT for original code/formalization, a third-party scope notice, citation/deposit metadata, a full file manifest, and a release builder that refuses version reuse. The archive has a detached digest and is verified against its internal manifest. Local read-only packaging is distinct from public archival custody.

`revisions/20260924-submission/submission-check.json` records the current numerical/evidence preservation checks, source/proof equality, and document binding. The release's `RELEASE.json` records verification of the final archived bytes; `release/manifest.json` identifies the current document and core evidence. These are internal validation receipts, not independent replication or external peer review. No new broker experiment or Lean compiler invocation was performed during submission preparation.

All 537 original evidence files and all previously generated numerical outputs and primary figures remain byte-identical. The current manuscript preserves all thirteen explicit mathematical statement/proof environments and the Lean source. Nine synthetic package-integrity tests pass, covering a valid directory/archive round trip, altered and missing content, unlisted members, duplicate entries, unsafe paths, version disagreement, symbolic links, and refusal to overwrite an existing release before any write. These tests concern artifact handling, not broker reliability. Their retained log is `revisions/20260924-submission/package-tests.log`; the preservation check can be rerun with `python revisions/20260924-submission/validate_submission.py` in the pinned analysis environment.

## Disposition of all fourteen findings

| Audit finding | Final disposition | Verification or remaining limit |
|---|---|---|
| 1. Storage-history confounding | Retained prominently in methods, discussion, RQ3 interpretation, and threats. Original final AOF lengths and delayed-fsync counter remain unchanged. | No causal storage-reset experiment was added. Configured policy and evolving storage history remain entangled. |
| 2. D038 failed-trial missingness | Retained the planned failure, missing confirmation/timing data, and excluded completed replay. The new outcome inventory includes them as separate entries. | No snapshot count is imputed as confirmed throughput. Missing original client measurements remain irrecoverable. |
| 3. Bootstrap coverage and deployment dependence | Retained nominal, conditional intervals and the working IID block-resampling assumption, with existing influence and execution-order analyses. | No claim of demonstrated 95% coverage or independent-campaign precision. Independent replication remains necessary for broader inference. |
| 4. Sparse information behind publication p99 | Added the 59 per-trial message counts, nearest-rank indices, and higher order-statistic position counts. Added a six-profile table and explicit D040 interpretation to the paper. | Counts/ranks independently recomputed. D040 has 149 observations, p99 rank 148, and one higher position. The observation stays in the primary estimate. |
| 5. Untested storage durability and unequal contracts | Preserved separation of confirmation cost, consumer-state behavior, and the conditional storage proposition. | Consumer kills and latency measurements still do not establish power-loss survival or equal-guarantee efficiency. |
| 6. Operational setup/warm-up costs | Added an evidence-linked retrospective inventory of 556 records, plus a manuscript table distinguishing all 550 planned outcomes from six additional documented attempts. | Successful warm-ups belong to their completed attempts. Pilots and infrastructure provisioning are outside this inventory. Missing durations remain null. No full-stage availability or total-cost estimate is inferred. |
| 7. Narrow recovery workload | Retained one pending message, periodic profiles, survivor demand before failure, and absence of concurrent publication load beside the method and interpretation. | No large-PEL, saturated-load, or application-work generalization. |
| 8. Missing historical censor endpoints | Added an explicit historical measurement limitation and excluded exact censor-time or survival interpretation. Implemented distinct endpoints for future recovery observations. | Unit and real-broker checks validate current recording. Historical endpoints remain unavailable. A timer-notification observation is not an exact kernel timer-firing timestamp. |
| 9. Partial integrity construct | Retained the distinction between identifier/count reconciliation and complete payload preservation. | No full-payload readback or corruption-free-storage claim. |
| 10. Serial sensitivity confounding | Preserved differences in duration, count, concurrency, and storage history. | Serial results do not identify batching or prove equivalence. |
| 11. Platform/workload generalization | Preserved shared Btrfs/NVMe, compression, client, message, duration, and concurrency limitations. | No production SLA, saturation ceiling, or hardware-independent ranking. |
| 12. Bounded failure-capture validation | Kept the returned-error/caught-panic promise and its abrupt-driver-loss boundary. Existing memory-profile ambiguity checks still pass. | No network-loss, host-crash persistence, or universal failure-preservation guarantee. |
| 13. Stale validation references | Marked older receipts historical, redirected the README to this current record, archived the historical visual receipt, and introduced hash-bound build and document-QA gates. | Current source inputs, successful build, PDF, and retained rendered pages must agree. The old visual receipt is rejected. |
| 14. Local versus external reproducibility | Added the artifact version map and explicit limits on what hashes establish. Submission version 1.1.0 adds component licenses and a sealed local release. | Public DOI, public archival custody, and external execution remain unperformed. Computational reproduction is distinct from externally executed replication. |

## Preserved scientific evidence

The initial state of this pass matched all **816** checksums supplied to the second audit. That inventory is retained in `revisions/20260924-final/baseline-manifest.json` and `baseline-SHA256SUMS`. The previous source, PDF, and QA are archived in `previous-revision-source-and-paper.tar.gz`.

All **537 original raw-data and environment files** remain byte-identical to the frozen original evidence lock. Full raw-event analysis passed again for **419 completed primary timing trials and 17,411,288 message records**. The 120 active recovery outcomes and ten controls retain their original interpretation. The primary `statistics.json`, all 420 aggregate CSV rows, the original result tables, all four primary figures, and the Lean source are byte-identical to the previously audited revision. All thirteen paired primary effects therefore retain their original estimates and intervals.

The new publication-tail records describe existing observations. Their count, selected rank, upper-position count, profile, and p99 value are checked independently against the retained summaries, whose values are reconstructed from raw events by the main analyzer. The new outcome inventory links original rows or documented incidents to their source files and lines, records source hashes, and marks unavailable times and counts as missing. It is a retrospective inventory, not new experimental data or a prospective exclusion rule.

## Recovery instrumentation and homelab execution

The final functional validation used campaign `final20260924`, attempt `a001`, exclusively through `kubectl --context homelab` in namespace `msgrel-final20260924-a001`. Its successful run, sealed inputs, collection, and environment receipts are retained under `campaigns/final20260924/attempts/a001/`. Current driver and collection sources match the validated input snapshot.

- Five Go regression tests passed with the race detector. They cover publication-error preservation, caught worker panic, identity/destination protection, waiting for an outstanding operation after the censor budget, retaining a late returned receipt, and success without an invented timer-expiry timestamp. One test contains two subcases.
- Nine Python campaign-isolation tests passed in the same homelab runner.
- Nine real broker scenarios passed: two memory-profile drains, two successful memory-profile publication runs, two ambiguous-confirmation injections, two active periodic-profile recoveries, and one Redis periodic no-reclaimer control.

Future records distinguish `censor_budget_start_ns`, `nominal_censor_deadline_ns`, `timer_notification_observed_ns`, `survivor_loop_completed_ns`, `controller_wait_completed_ns`, `reconciliation_start_ns`, and `reconciliation_end_ns`. The timer observation is null for recovery before its branch is taken. Loop completion is timestamped immediately before sending the terminal result. A receipt returned during shutdown is recorded explicitly, rather than silently being treated as an empty observation.

The real control retained pending state after the outstanding read returned, with the observed completion later than its 500 ms nominal budget. This confirms the purpose of separating the endpoints; it is a functional check, not a new performance sample. It does not establish a hard response-time bound or crash-persistent recording.

The final driver was built with Go 1.24.4 for Linux/amd64. Binary SHA-256: `fcd1a414857d0e0338c6b35402d9b50375ecd11a47656e2ba2dac981cd7a5da2`. The binary receipt is `revisions/20260924-final/driver-binary-receipt.json`. Validation evidence was collected before namespace deletion. `revisions/20260924-final/cleanup.json` records successful cleanup and a subsequent absence check. Original namespaces and unrelated resources were not changed by this pass.

## Formal and source grounding

The hand arguments and their stated domains were reread against the manuscript's claim boundaries. The new p99-rank discussion follows directly from the already defined nearest-rank statistic. It introduces no population-tail theorem or additional independence claim.

The selected Lean model was not changed. Both retained successful receipts match its current source digest and the same ten declarations. The latest compiler invocation was the prior revision's separate homelab check on 24 September; this final pass verifies those receipts and source identity rather than claiming another compiler execution. The source and literature checks recorded in [SOURCE_REVALIDATION.md](SOURCE_REVALIDATION.md), together with the supplied second audit, remain the foundation for the unchanged version-specific implementation claims. No new broker semantics or bibliographic claims were introduced.

## Build, document, and provenance verification

The current manuscript has **30 pages and 31 cited references**, preserving the original template and section order. All pages are rendered, and the current visual-review receipt records exactly which renderings were inspected. Changed contribution statements, RQ1/RQ3 interpretation, artifact licensing, conclusion, appendix transitions, and bibliography receive additional inspection. The Appendix C heading is kept with its claim-to-evidence table. Source and extracted PDF text contain no em dashes; fonts are embedded, with no unresolved references or overfull boxes.

During document production, a caption containing a file-path macro caused a LaTeX build failure. Moving the path into the body resolved the formatting error. This also exposed an artifact-gate weakness: the old content check could inspect the previous PDF after a failed build. That gate is now strengthened. `bench/build_paper.py` records a successful compiler exit, exact source-input hashes, output PDF hash, page count, and compiler-log hash. `bench/check_paper.py` verifies that binding and rejects failed-build diagnostics. `bench/check_document_provenance.py` additionally requires matching current visual QA and retained page-render hashes and explicitly rejects the old receipt.

Current receipts are `data/derived/build-receipt.json`, `paper-check.json`, and `visual-review.json`, plus `revisions/20260924-final/revision-check.json` and `document-provenance-check.json`. `SHA256SUMS` is regenerated only after document inspection and final report completion. A subsequent source or PDF change requires the relevant checks and visual review again; updating a manifest alone cannot substitute for them.

## Final scope

The local submission revision reports observations, conditional proofs, documented missingness, and unverified assumptions distinctly. Version 1.1.0 supplies component licenses and a fixed local distribution with verification instructions. No absolute perfection, peer-review acceptance, independent replication, tested storage durability, or broader population claim is asserted. Public deposit, DOI assignment, and journal submission remain unperformed. Accepted experimental limitations require new evidence only if stronger claims are pursued; editorial changes and packaging do not remove them.
