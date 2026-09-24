# Submission artifact, version 1.1.0

Prepared on 24 September 2026 for the paper by Victor Bona. This release contains a descriptive comparison of specific recovery policies, concurrency behavior, and acknowledgment costs under the documented conditions. The numerical results and proof statements are unchanged from the preceding audited revision.

## Delivered files and identity

The distribution consists of `redis-jetstream-reliability-v1.1.0.tar.gz`, the matching standalone PDF, `RELEASE.json`, `VERIFICATION.log`, and a detached `SHA256SUMS`. In the authoring workspace these files are under `releases/v1.1.0/`. The archive expands to `redis-jetstream-reliability-v1.1.0/` and contains its own `SHA256SUMS` covering all delivered members except that manifest itself. `release/manifest.json` binds the version to the exact paper, primary statistics, evidence lock, proof, and license files. Before sealing, the builder extracts the archive to a fresh temporary directory, verifies all content, runs the offline document/revision/provenance checks there, and confirms those checks did not change delivered files. The accompanying log records those checks; they are local verification, not independent external replication.

The package builder refuses an existing destination and makes completed release files read-only. These controls and hashes provide a fixed, verifiable local release. They do not prevent an owner from changing permissions, certify collection time, or constitute public archival custody. Keep the sealed distribution unchanged. Any subsequent source, result, document, or metadata change belongs in a new version.

## Verify the supplied package

From the distribution directory, use the platform's SHA-256 tool to check its detached manifest before extraction:

```sh
shasum -a 256 -c SHA256SUMS
tar -xzf redis-jetstream-reliability-v1.1.0.tar.gz
cd redis-jetstream-reliability-v1.1.0
python3 bench/verify_release.py --directory .
```

The Python verifier uses only the standard library. It verifies every internal manifest entry, rejects extra unlisted deliverable files and symbolic links, and checks version, PDF, primary-result, evidence-lock, formal-source, and license identities. It verifies supplied content, not experimental truth or external certification. Python 3.13 is the analysis environment; use Python 3.10 or later for the standalone verifier.

Install the analysis dependencies in the extracted working copy, then inspect the shipped PDF and its source-bound receipts without rebuilding:

```sh
uv venv .venv --python 3.13
uv pip install --python .venv/bin/python -r requirements-analysis.txt
.venv/bin/python bench/check_paper.py
.venv/bin/python bench/check_revision.py
.venv/bin/python bench/check_document_provenance.py
```

The final LaTeX log and generated bibliography are supplied because these checks use them. The document receipt records the internal visual inspection of the shipped rendering. An independent reader may inspect the PDF directly; the existing receipt does not certify that reader's review.

## Recompute numerical results and rebuild the paper

Run `make analyze` in the extracted working copy. It reads the frozen original data, reconstructs all 419 completed primary timing trials and 17,411,288 message records, and verifies the 120 active recovery outcomes and ten controls. All 550 planned outcomes, including the failed publication trial, remain accounted for. `bench/check_revision.py` checks equality of primary statistics with the retained historical snapshot and separately verifies sensitivity summaries, outcome accounting, template structure, source-bound proof receipts, and prior functional-validation evidence.

Use `make paper` to compile with `latexmk`, pdfLaTeX, BibTeX, the packages in `paper/main.tex`, and `plainurl.bst`. Then run `bench/check_paper.py` with the analysis Python. The supplied PDF is the reference artifact. A local rebuild can change PDF metadata or rendering with the TeX environment; byte-identical PDF output across arbitrary TeX installations is not asserted. The successful-build receipt binds each build to its own sources and output.

A different PDF invalidates the existing visual-review receipt. Render and inspect that output and create its own accurate review record before using the document-provenance gate. Do not copy the previous review's pass status onto a new PDF or regenerate checksums to hide changes. Preserve the original sealed archive for comparison.

## Evidence and implementation boundaries

`docs/ARTIFACT_MAP.md` distinguishes the original measured harness from later functional improvements. All 537 original data/environment files are frozen by `revisions/20260924/original-evidence-lock.json`. Neither D038's missing client measurements nor exact historical censor endpoints are reconstructed. Later validation collections do not replace performance observations.

The ten selected Lean declarations retain their original source and successful homelab compiler receipts. The current submission pass checks those identities; it does not claim a fresh compile or formal verification of Redis or NATS. `formal/README.md` describes an independent check with the pinned compiler.

New broker measurements or runtime/proof validation must use a fresh, separately identified homelab environment through `kubectl --context homelab`. The original namespace was deleted. Follow the campaign/attempt workflow in the main README. Numerical reanalysis and PDF compilation require no cluster.

## Licensing, citation, and deposit preparation

`LICENSE.md` assigns CC-BY-4.0 to the original paper and research material and MIT to original code and formalization. It identifies third-party exceptions and the retained MIT template notice. `CITATION.cff` supplies the author, title, and version. `release/metadata.json` supplies a deposit description and license scopes without inventing a DOI, ORCID, funding declaration, or peer-review status.

For a Zenodo deposit, upload the sealed archive and matching PDF, with `RELEASE.json` and the detached checksum file as provenance. Use the paper title, Victor Bona's authorship, version 1.1.0, and the supplied description. Declare both component licenses and retain their scope in the description. Use the platform's actual publication date and identifier. Verify that the uploaded file checksums match the local release before publishing. This package is prepared for deposit; no public deposit, DOI assignment, or journal submission has been performed.

If an archival DOI is later added to the manuscript, issue a new document/artifact version and repeat its build and visual checks. Keep version 1.1.0 unchanged. Journal-specific declarations and formatting depend on the chosen venue and must reflect the author's actual circumstances.

Official deposit references checked during preparation: [Zenodo licenses and mixed uploads](https://help.zenodo.org/docs/deposit/describe-records/licenses/), [CC BY 4.0 legal code](https://creativecommons.org/licenses/by/4.0/legalcode.txt), and [MIT License](https://opensource.org/license/mit).
