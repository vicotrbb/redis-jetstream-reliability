"""Create a portable manifest; retain compiler evidence for offline document QA."""
import hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
omit={".venv",".git","tmp","__pycache__","releases"}
suffixes={".aux",".bbl",".blg",".fdb_latexmk",".fls",".log",".out",".toc"}


def included(rel):
    if any(x in omit for x in rel.parts) or rel.name in {"SHA256SUMS", ".DS_Store"}:
        return False
    return not (rel.parts[0]=="paper" and rel.suffix in suffixes
                and rel.as_posix() not in {"paper/main.log", "paper/main.bbl"})


def paths(root):
    # Prune large cache and prior-release trees before descending.
    import os
    result=[]
    for base, dirs, files in os.walk(root):
        dirs[:]=sorted(d for d in dirs if d not in omit)
        for name in files:
            path=Path(base)/name
            if included(path.relative_to(root)):
                if path.is_symlink():
                    raise ValueError(f"Refusing symbolic link: {path}")
                result.append(path)
        for name in dirs:
            if (Path(base)/name).is_symlink():
                raise ValueError(f"Refusing symbolic directory: {Path(base)/name}")
    return sorted(result)


def sha256(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(1<<20),b""):h.update(b)
    return h.hexdigest()


def write_manifest(root=ROOT):
    entries={p.relative_to(root).as_posix():sha256(p) for p in paths(root)}
    (root/"SHA256SUMS").write_text("".join(f"{h}  {name}\n" for name,h in entries.items()))
    return entries


if __name__=="__main__":
    print(f"Hashed {len(write_manifest())} files")
