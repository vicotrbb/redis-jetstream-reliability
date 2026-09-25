"""Bind a successful LaTeX build to its exact inputs and delivered PDF."""
import datetime as dt
import json
import shutil
import subprocess
from pypdf import PdfReader

from check_document_provenance import ROOT, PDF, digest, source_hashes

before=source_hashes()
command=['latexmk','-pdf','-interaction=nonstopmode','-halt-on-error','main.tex']
subprocess.run(command,cwd=ROOT/'paper',check=True)
assert source_hashes()==before,'Document inputs changed while compiling'
PDF.parent.mkdir(exist_ok=True,parents=True)
shutil.copyfile(ROOT/'paper/main.pdf',PDF)
receipt={'status':'pass','command':command,'working_directory':'paper','compiler_exit_code':0,
         'built_at_utc':dt.datetime.now(dt.timezone.utc).isoformat(),
         'pdf':str(PDF.relative_to(ROOT)),'pdf_sha256':digest(PDF),
         'page_count':len(PdfReader(PDF).pages),'source_sha256':before,
         'latex_log_sha256':digest(ROOT/'paper/main.log')}
(ROOT/'data/derived/build-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'build':'pass','pages':receipt['page_count'],'pdf_sha256':receipt['pdf_sha256']}))
