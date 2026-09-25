# GitHub repository and release provenance

Repository: https://github.com/vicotrbb/redis-jetstream-reliability

Historical release: https://github.com/vicotrbb/redis-jetstream-reliability/releases/tag/v1.1.0

## Historical version 1.1.0

The annotated tag `v1.1.0` points to commit `69b9295b379adaa63bdb1151e6db36ae807fe31a`, the initial import of all 994 files from the validated artifact plus its internal `SHA256SUMS`. Git was initialized after collection and scientific validation. The tag does not create a retrospective execution history or independent certification of measurements.

The repository-import commits after that tag added `.gitignore`, byte-preserving Git attributes, repository documentation, and a refreshed checksum manifest. Those import changes did not replace the sealed artifact or alter the paper, measurements, numerical results, or proofs. Subsequent version 1.2.0 work adds a separately identified experimental follow-up and revises the article; it preserves the version 1.1.0 distribution. `SHA256SUMS` at each commit identifies that checkout; the detached release checksum identifies the original distribution archive. The original snapshot's citation/deposit metadata describe the preparation checkpoint, before GitHub hosting.

## Historical distribution files

The version 1.1.0 GitHub Release carries its original five distribution files:

- `redis-jetstream-reliability-v1.1.0.tar.gz`: complete sealed artifact, 315,823,904 bytes.
- `redis-jetstream-reliability-v1.1.0.pdf`: the 30-page manuscript.
- `RELEASE.json`: content identities and fresh-extraction verification outcomes.
- `VERIFICATION.log`: offline checks performed on the extracted archive.
- `SHA256SUMS`: detached checksums for the other four files.

Archive SHA-256: `1e8d8b54463a84ae9e7e6836456f20d4a6cd58c2f3449765609ffb742a45c75c`.

PDF SHA-256: `d26b97ccc214ac0b1d7a16315fc9a5430d4ff04eaf33265db1b1ab0e12a35051`.

Use the named artifact asset when exact archive bytes matter. GitHub's automatically generated source-code archives use a different container and directory prefix. Their contents correspond to the Git tag, while their archive checksum is not the checksum above.

Download the distribution into a new directory with GitHub CLI:

```sh
gh release download v1.1.0 --repo vicotrbb/redis-jetstream-reliability --dir artifact-v1.1.0
cd artifact-v1.1.0
shasum -a 256 -c SHA256SUMS
tar -xzf redis-jetstream-reliability-v1.1.0.tar.gz
cd redis-jetstream-reliability-v1.1.0
python3 bench/verify_release.py --directory .
```

For a Git checkout of the original snapshot:

```sh
git clone --branch v1.1.0 https://github.com/vicotrbb/redis-jetstream-reliability.git
cd redis-jetstream-reliability
python3 bench/verify_release.py --directory .
```

The historical and current Git checkouts intentionally retain `paper/main.log` and `paper/main.bbl`, because offline document validation reads them. Python environments, caches, temporary work, local credentials, and duplicate distribution archives are excluded. No benchmark or proof execution is required merely to clone or verify the files.

## Verified version 1.2.0 publication

Version 1.2.0 was published at `2026-09-25T00:44:22Z`. Its annotated tag resolves to scientific-artifact commit `10b5c96196b6e337a38d236cac0eb44a95f4f5fd`. All six GitHub asset digests and sizes match the sealed local distribution. The five historical version 1.1.0 assets and its original tag also match their preserved identities.

Archive SHA-256: `199c3a01cbb13145e788b96f46a5d7480e35b227760e261b083401f4fba130eb`.

`revisions/20260924-followup/github-publication.json` records the remote references, publication timestamp, asset URLs, sizes, and server-reported SHA-256 digests. This hosting receipt and documentation are a subsequent provenance-only commit. They do not modify the scientific release tag or either sealed distribution. The checkout checksum manifest consequently identifies the current repository, while the detached distribution manifests identify the original release files.

## Publication status

Version 1.2.0 adds the separately collected 612-outcome extension, the 21-page main article, and the 20-page supplement. Its distribution has six files: the named versioned archive, both matching PDFs, `RELEASE.json`, `VERIFICATION.log`, and detached `SHA256SUMS`. The public release location is `https://github.com/vicotrbb/redis-jetstream-reliability/releases/tag/v1.2.0`. The sealed archive records its preparation checkpoint; subsequent repository publication receipts identify the actual tag, commit, upload time, sizes, and server-reported digests. Preparation and successful upload are separate events.

To obtain this version after publication:

```sh
gh release download v1.2.0 --repo vicotrbb/redis-jetstream-reliability --dir artifact-v1.2.0
cd artifact-v1.2.0
shasum -a 256 -c SHA256SUMS
tar -xzf redis-jetstream-reliability-v1.2.0.tar.gz
cd redis-jetstream-reliability-v1.2.0
python3 bench/verify_release.py --directory .
```

Public GitHub hosting is distinct from DOI-bearing archival deposit, independent replication, external artifact evaluation, and scientific peer review. No Zenodo DOI or journal acceptance is claimed. The paper and artifact licenses are in `LICENSE.md`; third-party material retains its applicable terms. The original release's preparation-time declarations and validation receipts remain historical records and have not been rewritten to imply earlier publication.

## Verified version 1.3.0 publication

Version 1.3.0 was published at `2026-09-25T02:33:55Z`. Its annotated tag resolves to scientific-artifact commit `4856144649df217c01e23b8f65fa5479378e1305`. The GitHub release reports its immutable flag as `true`. All five server-reported asset digests and sizes match the sealed local distribution. The prior version 1.1.0 and 1.2.0 tags and all eleven older assets also match their preserved identities.

The public release is [https://github.com/vicotrbb/redis-jetstream-reliability/releases/tag/v1.3.0](https://github.com/vicotrbb/redis-jetstream-reliability/releases/tag/v1.3.0). It contains the complete 43-page article, its full evidence archive, `RELEASE.json`, `VERIFICATION.log` and detached `SHA256SUMS`. There is no separate supplementary PDF in version 1.3.0. Earlier documents remain in their historical releases and the retained document archive.

Archive SHA-256: `afc9dc2be42cb15e834e45862e940fa1e485be0517ac86adcb8443f303cbb517`.

Complete article SHA-256: `e97cf988ef4dde5acd4df9de0d04d8dc88f2f94c5f184f4ece48747c86246a24`.

`revisions/20260925-integrated/github-publication.json` binds release and tag identities, publication timestamps, asset URLs, sizes and server-reported digests to local sealed files. This hosting receipt and documentation are recorded after the scientific tag and do not modify any sealed distribution, paper, measurement or proof. The updated checkout manifest covers that provenance-only addition. DOI-bearing deposit and peer review remain unperformed.
