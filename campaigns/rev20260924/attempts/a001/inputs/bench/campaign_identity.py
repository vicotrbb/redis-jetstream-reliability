"""Fail-closed identity and content seals for new, separately collected attempts."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ID = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,18}[a-z0-9])?\Z")


def identity(campaign_id, attempt_id):
    if not all(ID.fullmatch(s) for s in (campaign_id, attempt_id)):
        raise ValueError("Campaign and attempt IDs must be 1-20 lowercase DNS characters")
    return {"campaign_id": campaign_id, "attempt_id": attempt_id,
            "namespace": f"msgrel-{campaign_id}-{attempt_id}", "context": "homelab"}


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_new(path, value):
    with Path(path).open("x") as f:
        json.dump(value, f, indent=2)
        f.write("\n")


def check_record(record, expected):
    for key in ("campaign_id", "attempt_id"):
        if record.get(key) != expected[key]:
            raise ValueError(f"Mismatched {key}: {record.get(key)!r}")


def check_records(directory, expected):
    """Validate rows in data, failure ledgers, runtime records and structured logs."""
    directory = Path(directory)
    for path in directory.rglob("*"):
        if path.is_symlink():
            raise ValueError(f"Symlink is not an immutable evidence file: {path}")
        if path.suffix == ".jsonl":
            for line in path.read_text().splitlines():
                if line.strip():
                    check_record(json.loads(line), expected)
        elif path.suffix == ".log":
            for line in path.read_text(errors="replace").splitlines():
                if line.startswith('{"'):
                    check_record(json.loads(line), expected)
        elif path.name.startswith("runtime") and path.suffix == ".json":
            check_record(json.loads(path.read_text()), expected)


def seal(directory, expected):
    directory = Path(directory)
    target = directory / "manifest.json"
    if target.exists():
        raise FileExistsError(target)
    check_records(directory, expected)
    files = {str(p.relative_to(directory)): digest(p)
             for p in sorted(directory.rglob("*")) if p.is_file()}
    write_new(target, {**expected, "schema": 1, "files": files,
                       "role": "Content seal; no scientific success adjudication implied"})
    return verify_seal(directory, expected)


def verify_seal(directory, expected):
    directory = Path(directory)
    manifest = json.loads((directory / "manifest.json").read_text())
    check_record(manifest, expected)
    actual = {str(p.relative_to(directory)) for p in directory.rglob("*")
              if p.is_file() and p != directory / "manifest.json"}
    if actual != set(manifest["files"]):
        raise ValueError("Collection file set differs from its seal")
    for name, expected_hash in manifest["files"].items():
        path = directory / name
        if path.is_symlink() or path.resolve().is_relative_to(directory.resolve()) is False:
            raise ValueError(f"Unsafe evidence path: {name}")
        if digest(path) != expected_hash:
            raise ValueError(f"Evidence hash changed: {name}")
    check_records(directory, expected)
    return manifest


def verify_original_evidence():
    """Legacy records predate IDs. Bind them by their complete, frozen file hashes."""
    lock = json.loads((ROOT / "revisions/20260924/original-evidence-lock.json").read_text())
    if lock["campaign_id"] != "msgrel-20260923":
        raise ValueError("Unexpected legacy campaign")
    files = {n: h for n, h in lock["files"].items()
             if n.startswith(("data/raw/", "data/environment/"))}
    actual = {str(p.relative_to(ROOT)) for folder in ("data/raw", "data/environment")
              for p in (ROOT / folder).rglob("*") if p.is_file()}
    if actual != set(files):
        raise ValueError("Legacy campaign file set changed; new collections belong in campaigns/")
    for name, expected_hash in files.items():
        if digest(ROOT / name) != expected_hash:
            raise ValueError(f"Original campaign evidence changed: {name}")
    return len(files)
