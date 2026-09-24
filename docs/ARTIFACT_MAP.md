# Artifact versions and reproduction scope

The study was collected and validated before Git initialization. Tag `v1.1.0` imports the exact validated snapshot at commit `69b9295b379adaa63bdb1151e6db36ae807fe31a`; later commits add repository publication metadata. The retained source snapshots, archives, input seals, and manifests identify the earlier versions below. Git history does not retrospectively certify collection time or completeness before sealing. See [GITHUB_PUBLICATION.md](GITHUB_PUBLICATION.md) for the public release and the distinction between the frozen artifact and the current checkout.

| Artifact | Role and identity |
|---|---|
| `data/raw/` and `data/environment/` | Frozen original campaign `msgrel-20260923`. All 537 files are bound by `revisions/20260924/original-evidence-lock.json`. No later validation observations are added here. |
| `data/environment/harness-v1/` through `harness-v4/` | Historical measured implementations and continuation changes. `docs/DEVIATIONS.md`, driver build receipts, and execution logs identify their use. Earlier snapshots are part of the frozen evidence. |
| `revisions/20260924/original-source-and-paper.tar.gz` | Source and document archive from before the first scientific revision. Includes the original measured implementation and the 25-page PDF with hash `386e1c56f5aad3cf3a054daf1043225e7af738139350fdb1fb8d2be55f084472`. |
| `campaigns/rev20260924/attempts/a004/inputs/` | Sealed first-revision harness: publication-error capture and campaign isolation. Its separate functional collection and run result identify successful validation. It did not generate the original performance data. |
| `revisions/20260924-final/previous-revision-source-and-paper.tar.gz` | Previous audited revision, including the 27-page PDF with hash `458f1f005872ddb807a9273315b65c28132f2b888889388b6288abf8d56ee555`, its source, and historical QA. The adjacent baseline inventory identifies all 816 files in that delivery. |
| `revisions/20260924-submission/previous-source-and-paper.tar.gz` | Pre-submission audited revision, including the 29-page PDF with hash `7a6aeb9a37ca031b5ddfcd22ca103ebda3d05b02ed53c492906e86944b521247`, its source, and QA. The adjacent baseline inventory identifies all 937 files in that delivery. |
| `campaigns/final20260924/attempts/a001/inputs/` | Sealed final recovery-controller source and functional-validation input. Adds separate observation endpoints and retention of a receipt returned during shutdown. Its collection is functional evidence only. |
| `bench/`, `paper/`, `data/derived/`, `output/pdf/` | Current collection source, analysis, manuscript, generated results, and reader-facing document. Current `SHA256SUMS` identifies them. No assertion is made that current `bench/` was used for historical observations. |
| `formal/DeliveryModel.lean` | Unchanged selected abstract model. `formal/verification.json` identifies the original successful compile; `revisions/20260924/lean-recheck.json` identifies the independent later invocation on the homelab. Neither verifies broker implementations. |
| `data/derived/visual-review.json` | Current PDF hash, source inputs, retained rendered-page hashes, and review scope. `bench/check_document_provenance.py` rejects a receipt for a different PDF or source snapshot. |
| `data/derived/build-receipt.json` | Successful compiler exit and exact input, PDF, and compiler-log hashes. The paper checker rejects stale outputs after failed builds or later source changes. |
| `release/manifest.json`, `CITATION.cff`, and `LICENSE.md` | Version 1.1.0 submission artifact, exact document and core evidence identities, citation metadata, and component-specific CC-BY-4.0/MIT licensing. The archive's detached checksum identifies the complete sealed release. |
| `docs/EXECUTION_RECEIPT.md`, `docs/REVISION_VALIDATION.md` | Explicitly historical validation narratives. The current narrative is `docs/FINAL_REVISION_VALIDATION.md`. |

## Reanalysis versus new experiments

Reanalyze retained data with the pinned Python dependencies and `make analyze`. Build the manuscript with `make paper`, render and inspect that exact output, and then use `make verify-revision`. Regenerate `SHA256SUMS` only after all source, evidence, and review records are finalized. A changed PDF requires new document QA; changing a checksum file cannot substitute for inspection.

New broker execution is permitted only through `kubectl --context homelab`. It requires new campaign and attempt identifiers and its own adjudication and analysis. Original D038 and D043 client traces and exact historical control endpoints remain unavailable. Existing evidence must not be rewritten to imply that later instrumentation was present during collection.

## Archival release boundary

The locally prepared version 1.1.0 is licensed and packaged with source, raw and derived data, pinned dependencies, historical and revised harness maps, formal receipts, current document QA, and content manifests. Caches and unnecessary build intermediates are excluded; the final compiler log and bibliography output are retained for offline validation. `release/README.md` explains verification and deposit preparation. Existing release versions cannot be overwritten by the builder; changed content requires a new version and new validation.

The artifact has not been publicly deposited, externally executed, or externally artifact-evaluated. No DOI or acceptance is asserted. Local read-only files and checksums make replacement detectable; they do not constitute independent archival custody or prevent the filesystem owner from changing permissions. A public archive must assign its identifier before that identifier is added to a later manuscript or release. Third-party material retains its own terms as specified in `LICENSE.md`.
