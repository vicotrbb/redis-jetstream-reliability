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
