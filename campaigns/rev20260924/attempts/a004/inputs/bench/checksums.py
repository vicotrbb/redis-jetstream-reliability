"""Create a portable content manifest, excluding caches and build intermediates."""
import hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
omit={".venv",".git","tmp","__pycache__"}
suffixes={".aux",".bbl",".blg",".fdb_latexmk",".fls",".log",".out",".toc"}
lines=[]
for p in sorted(ROOT.rglob("*")):
    rel=p.relative_to(ROOT)
    if not p.is_file() or any(x in omit for x in rel.parts) or p.name=="SHA256SUMS":continue
    if rel.parts[0]=="paper" and p.suffix in suffixes:continue
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1<<20),b""):h.update(b)
    lines.append(f"{h.hexdigest()}  {rel.as_posix()}")
(ROOT/"SHA256SUMS").write_text("\n".join(lines)+"\n")
print(f"Hashed {len(lines)} files")
