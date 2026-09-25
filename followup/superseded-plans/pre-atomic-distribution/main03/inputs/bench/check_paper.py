"""Offline artifact checks; this script does not execute broker experiments."""
import json
import re
import hashlib
from pathlib import Path
from pypdf import PdfReader
from check_document_provenance import source_hashes

ROOT=Path(__file__).resolve().parents[1]
paper=ROOT/"output/pdf/redis-jetstream-reliability.pdf"
text="\n".join(p.extract_text() or "" for p in PdfReader(paper).pages)
required=["Abstract","Introduction","Background and related work","System model and formal results","Experimental method","Results","Discussion","Threats to validity","Artifact availability and reproducibility","Conclusion","References"]
missing=[s for s in required if s not in text]
assert not missing,missing
for bad in ("??","TODO","TBD","PLACEHOLDER","\u2014"):
    assert bad not in text,bad
log=(ROOT/"paper/main.log").read_text()
for bad in ("undefined references","undefined citations","There were undefined","Overfull ","LaTeX Error","Undefined control sequence","Emergency stop","Fatal error","\\Url Error"):
    assert bad not in log,bad
build=json.loads((ROOT/'data/derived/build-receipt.json').read_text())
assert build['status']=='pass' and build['compiler_exit_code']==0
assert build['source_sha256']==source_hashes(),'Document sources changed after the successful build'
assert build['pdf_sha256']==hashlib.sha256(paper.read_bytes()).hexdigest(),'PDF does not match the successful build'
assert build['latex_log_sha256']==hashlib.sha256((ROOT/'paper/main.log').read_bytes()).hexdigest(),'Build log changed after successful build'
checks=json.loads((ROOT/"data/derived/statistics.json").read_text())["checks"]
assert checks["main"]["trials"]==300
assert checks["durability"]["planned_trials"]==60
assert checks["durability"]["trials"]+len(checks["durability"]["failed_planned_trials"])==60
assert checks["serial"]["trials"]==60
assert checks["recovery"]["successful_recoveries"]==120
assert checks["recovery"]["no_reclaim_censored"]==10
formal=json.loads((ROOT/"formal/verification.json").read_text())
formal_log=(ROOT/"formal/verification.log").read_text()
assert formal["status"]=="pass" and formal["exit_code"]==0
assert formal["execution_context"]=="homelab"
assert hashlib.sha256((ROOT/formal["source"]).read_bytes()).hexdigest()==formal["source_sha256"]
assert formal["source_sha256"] in formal_log
assert len(formal["logical_dependencies"])==10
assert {a for deps in formal["logical_dependencies"].values() for a in deps}<={"propext","Quot.sound","Classical.choice"}
assert "error:" not in formal_log and "warning:" not in formal_log
result={"pages":len(PdfReader(paper).pages),"required_sections":required,"unresolved_references":False,"overfull_boxes":False,"raw_data_checks":checks,"formal_receipt_matches_source":True,"formal_declarations":10}
result['pdf_sha256']=hashlib.sha256(paper.read_bytes()).hexdigest()
result['source_sha256']=source_hashes()
result['successful_build_receipt_verified']=True
result['reference_count']=len(re.findall(r'\\bibitem',(ROOT/'paper/main.bbl').read_text()))
(ROOT/"data/derived/paper-check.json").write_text(json.dumps(result,indent=2)+"\n")
print(json.dumps({"pages":result["pages"],"sections":len(required),"status":"pass"},indent=2))
