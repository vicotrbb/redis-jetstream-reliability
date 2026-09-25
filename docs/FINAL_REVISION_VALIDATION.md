# Current validation: integrated article, version 1.3.0

This record concerns the complete article and artifact prepared on 25 September 2026. Version 1.3.0 integrates the former supplementary document into the article's appendices and improves descriptive reporting against retained observations. It adds no benchmark measurements and performs no new Lean compilation. Version 1.2.0's collection, analysis and proof execution remain separately identified historical evidence.

The current article has **43 pages and 44 cited references**. Its SHA-256 is `e97cf988ef4dde5acd4df9de0d04d8dc88f2f94c5f184f4ece48747c86246a24`. The original title, Victor Bona authorship, 11-point template, 1.1-inch margins and main section order remain intact. Appendices A through F contain the complete concurrency matrix, serial sensitivity, analytical assumptions and full proofs, historical statistical diagnostics, client waits and complete follow-up results. There is no separate current supplementary PDF.

## Preserved evidence and mathematical material

Before editing, the prior article, supplement, LaTeX source and validation identities were archived in `revisions/20260925-integrated/previous-v1.2.0-document.tar.gz`. The adjacent `baseline.json` records the starting commit, all 27 archived document-file hashes and nineteen protected evidence identities. The scientific version 1.2.0 tag and distribution remain unchanged.

`bench/check_integrated_paper.py` verifies the archived bytes, protected primary and follow-up results, prior generated figures/tables, and the complete hand-model source after removing only its redundant top-level heading. All thirteen theorem, proposition, corollary, definition and proof environments are preserved byte for byte. The historical statistics/diagnostics and client-wait text are preserved with only section-level and internal-reference adjustments. Every previous follow-up paragraph and every prior supplementary table/figure input is retained. Added reporting appears alongside that material rather than replacing it.

All 537 original raw/environment files remain bound by the original evidence lock. The original 419 completed timing trials, 17,411,288 message records, 420 aggregate rows and thirteen paired effects are unchanged. D038's missing client measurements, the interrupted D043 trace and exact historical censor endpoints remain unavailable.

The three primary follow-up deployments retain all 612 planned outcomes: 205 completed and eleven failed publication trials, 96 completed drains, 240 active recoveries, twelve completed plain-read observation procedures, 24 trace-family and 24 compression-family trials. The previous full analysis reconstructed 80,263,171 timed records, including 22 unknown client outcomes. Original and follow-up measurements remain separate. `bench/check_followup.py` again verifies the 2,373 raw-file identities, 108 sealed input entries, 288 condition summaries, 324 paired contrast cells and 732 planned paired blocks. It checks the retained proof/cleanup receipts without rerunning the cluster.

The Lean source is unchanged: `169fa4a50504ba59b34a3159bcdc0c1a1d89139c28a323856e4be40805928d03`. The latest compilation remains the successful Lean 4.24.0 homelab invocation after follow-up collection, retained in `revisions/20260924-followup/lean-recheck.json`. It checks ten selected abstract declarations, not either broker implementation, the measurement harness, storage survival or statistical coverage. The original full hand arguments now appear in Appendix C.

## Reporting corrections verified against retained observations

`bench/report_operational.py` creates and, by default, independently reconstructs the new operational report. It does not mutate observations. Its receipt binds the script, prior trial/statistics files and fourteen selected raw event traces. The resulting JSON and four LaTeX tables are under `data/derived/`.

| Profile | Planned | Completed | Warm-up failures | Timed failures | Failed/planned |
|---|---:|---:|---:|---:|---:|
| Memory | 72 | 72 | 0 | 0 | 0.0% |
| Periodic | 72 | 71 | 0 | 1 | 1.4% |
| Always | 72 | 62 | 4 | 6 | 13.9% |

These are descriptive fractions of the balanced configuration matrix. Four failures occurred before timing; they are not fifteen-second measurement windows. Seven timed failures contain 22 unknown requests, with recorded waits of 5.000095525 to 5.002364731 seconds. Four trials returned Redis I/O timeouts and three returned NATS response timeouts; the sixteen-publisher NATS failure contains sixteen unknown calls. A returned timeout does not identify when the broker completed or abandoned the operation.

Seven completed primary publication trials have a maximum confirmed-request latency of at least one second, all in always profiles and spanning both brokers and both versions. Four exceed two seconds, with maxima from 2.297 to 4.183 seconds; the next is 1.969 seconds. The supplied audit's count of five and its proposed one-in-five-window inference were not adopted. Thresholds are explicitly post-observation descriptions, no slow trial is removed, and every trial remains in the full results.

The eight memory/periodic current/historical version-contrast means range from 0.9603 to 1.0232, with deployment-specific ratios ranging from 0.9401 to 1.1237. All have nine completed matched pairs except JetStream periodic at one publisher, with eight. Proximity to one is not an equivalence test.

The text now states the source-consistent synchronization mechanism explicitly. JetStream's one synchronization call per confirmation at both publisher counts agrees with its pinned serialized single-stream append path; Redis's concurrent aggregate corresponds to approximately 8.3 confirmations per synchronization call. These observations do not assign individual confirmations to calls, measure physical device flushes or decompose the whole performance gap. The largest traced synchronization call is 544.563 ms. Separate diagnostic traces did not capture the untraced multi-second request events and do not establish their cause.

`bench/check_manuscript_numbers.py` binds 73 displayed values and associated outcome relationships to the separately checked numerical reports. These checks establish agreement with retained evidence, not independent external replication or broader population inference.

## Document review and reproducibility

The complete article compiled successfully with pdfLaTeX/BibTeX through latexmk. `data/derived/build-receipt.json` binds that success to the exact source inputs, PDF and compiler log. `paper-check.json` checks the document structure, current source identity, bibliography, original/follow-up outcome relationships and retained proof receipt. It rejects em dashes, missing characters, unresolved or duplicate references, overfull boxes and stale builds.

All 43 final pages were rendered at a maximum dimension of 1600 pixels and inspected on eight contact sheets. Full-page inspection additionally covered pages 1, 10, 14, 19, 20, 35 and 38, including the abstract, revised results, source explanation, claim map, mathematical notation, version contrasts and timeout table. No unresolved visual defects were found. All fonts are embedded. `data/derived/visual-review.json` binds the review to the PDF, every source input and retained renderings under `revisions/20260925-integrated/document-qa/`. Historical visual-review receipts are explicitly rejected for the current document.

`make verify-revision` runs seven offline gates: paper content/build identity, original evidence, follow-up provenance/arithmetic, operational-report reconstruction, manuscript numbers, document integration and current visual provenance. The current integration, number and provenance receipts are in `revisions/20260925-integrated/`; prior version 1.2.0 receipts remain historical. Nine package-integrity tests cover changed, missing and unlisted content, unsafe paths, duplicate archive members, symbolic links, version disagreement, and refusal to overwrite an existing release before any write. These tests check artifact logic rather than broker reliability.

## Release and scientific boundary

Version 1.3.0 retains CC-BY-4.0 for original paper/research material and MIT for original code/formalization, with third-party terms scoped in `LICENSE.md`. Its distribution comprises one complete article PDF, the full artifact archive, `RELEASE.json`, `VERIFICATION.log` and detached `SHA256SUMS`. The builder refuses version reuse and verifies all seven offline gates on a fresh extraction before sealing. Actual archive identities and execution outcomes are recorded in those distribution files. Earlier versions remain unchanged.

No new performance campaign is needed for these reporting and document-integration changes. Shared hardware, finite workloads, conditional successful-run summaries, source-based mechanism evidence and untested storage-fault guarantees retain their stated limits. All broker/runtime/proof executions in the study are identified homelab operations; this revision uses only offline reanalysis and document tooling.

Public GitHub hosting is distinct from DOI-bearing archival custody, external replication and peer review. `docs/GITHUB_PUBLICATION.md` records actual hosting status. No Zenodo deposit, DOI assignment, journal acceptance, external artifact evaluation or claim of perfection is made.
