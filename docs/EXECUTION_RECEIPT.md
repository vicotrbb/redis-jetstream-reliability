# Historical execution and validation receipt: 23 September 2026

This receipt applies only to the 25-page PDF identified by SHA-256 `386e1c56f5aad3cf3a054daf1043225e7af738139350fdb1fb8d2be55f084472`. That PDF and its original source are preserved in `revisions/20260924/original-source-and-paper.tar.gz`. The stable output path now contains a later revision. Current validation is in [FINAL_REVISION_VALIDATION.md](FINAL_REVISION_VALIDATION.md); current hash-bound document QA is `data/derived/visual-review.json`. The original visual receipt is preserved as `revisions/20260924-final/historical-visual-review.json`.

At this historical checkpoint, the article had 25 pages, four vector figures, tables, a conclusion, appendices, and 29 cited references. Its title, typography, margins, and author block followed the supplied `bfs-avoidance-frontier` template. Validation at that checkpoint: 2026-09-23T23:35:29.549845+00:00.

## Experimental accounting

All broker workloads and Lean execution occurred strictly in the authorized `homelab` context. The workstation was used for authoring, numerical reanalysis, data validation, and PDF generation/rendering.

| Series | Planned outcomes | Recorded disposition |
|---|---:|---|
| Consumer concurrency | 300 | 300 completed trials; 4,915,200 drained messages |
| Timed publication | 60 | 59 completed planned trials; 12,434,648 confirmed appends; one retained Redis-always timeout |
| Serial-publisher sensitivity | 60 | 60 completed trials; 61,440 messages |
| Active consumer recovery | 120 | 120 recovered original IDs, successful acknowledgment, zero pending |
| Redis no-reclaimer control | 10 | Ten censored observations with the message still pending |
| Total | 550 | All planned outcomes accounted for |

Two 12-trial pilots, setup/warm-up interruptions, one excluded diagnostic D038 replay, and an operator-interrupted D043 partial attempt are retained separately. They are not silently mixed into the primary completed-run estimates. The independent outcome manifest and failure ledger are mandatory analysis inputs. See `docs/DEVIATIONS.md` and `data/environment/outcome-manifest.json`.

## Verification

- Raw-data analysis completed with all identity/count, monotonic timing, quantile, throughput, worker-assignment, and occupancy checks passing. Receipt: `data/derived/analysis-receipt.json`; numerical output: `data/derived/statistics.json`.
- An independent internal read-only agent audit checked the final abstract, results, conclusion, and all 420 aggregate CSV rows against the JSON statistics. No material error was found. This is AI-assisted internal review, not external peer review.
- Ten selected conditional model statements passed Lean 4.24.0 inside the homelab runner after collection ended. Warnings were treated as errors; the exact source and toolchain are identified in `formal/verification.json`. Only standard logical dependencies were present; the finite crash traces are axiom-free. A successful check is not formal verification of Redis or NATS.
- `make paper` completed. `bench/check_paper.py` passed all 11 required-section checks, sample-accounting checks, reference/overflow checks, and exact-source formal-receipt checks.
- All 25 pages of that PDF were rendered and visually inspected. Its QA receipt is now preserved in `revisions/20260924-final/historical-visual-review.json`. At that checkpoint all fonts were embedded and no LaTeX warnings, unresolved references, or overfull boxes remained.

Historical PDF SHA-256: `386e1c56f5aad3cf3a054daf1043225e7af738139350fdb1fb8d2be55f084472`.

## Cleanup and publication state

Only namespace `msgrel-20260923`, verified by its experiment-purpose label and UID, was deleted. Kubernetes subsequently returned `NotFound`; `data/environment/cleanup.json` retains the receipt. All local raw data and proof receipts were collected before cleanup. No unrelated namespace, application, node configuration, or production service was changed.

No public repository, DOI, journal submission, external artifact evaluation, or peer-review acceptance is claimed. The manuscript explicitly distinguishes conditional mathematical proofs from measurements bounded by the selected releases, workload, hardware, storage, and failure model. Funding, conflict-of-interest, venue formatting, licensing, and public-archival declarations should be finalized with the author for any external submission.

`SHA256SUMS` is generated after the final source, receipt, and PDF edits. It covers delivered evidence and source files while excluding caches, rendering intermediates, and LaTeX auxiliary files.
