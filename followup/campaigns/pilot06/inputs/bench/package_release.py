"""Create a new sealed release; never overwrite an existing version."""
import datetime as dt
import gzip
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile

from checksums import ROOT, sha256, write_manifest
from check_document_provenance import source_hashes, validate_review
from verify_release import verify_archive, verify_directory


def main():
    metadata=json.loads((ROOT/'release/metadata.json').read_text())
    version=metadata['version']
    if not re.fullmatch(r'\d+\.\d+\.\d+',version):
        raise ValueError('Expected a numeric major.minor.patch release version')
    destination=ROOT/'releases'/f'v{version}'
    if destination.exists():
        raise FileExistsError(f'Release {version} already exists; prepare a new version')
    review=json.loads((ROOT/'data/derived/visual-review.json').read_text())
    validate_review(review)
    build=json.loads((ROOT/'data/derived/build-receipt.json').read_text())
    check=json.loads((ROOT/'data/derived/paper-check.json').read_text())
    if not (build['status']=='pass' and build['compiler_exit_code']==0
            and build['pdf_sha256']==check['pdf_sha256']==review['pdf_sha256']
            and build['source_sha256']==check['source_sha256']==source_hashes()
            and build['latex_log_sha256']==sha256(ROOT/'paper/main.log')):
        raise ValueError('Build, content, source, and visual review do not agree')
    core=['output/pdf/redis-jetstream-reliability.pdf','paper/abstract.tex',
          'paper/main.tex','paper/results.tex','paper/conclusion.tex','paper/references.bib',
          'data/derived/statistics.json','data/derived/aggregate.csv',
          'data/derived/build-receipt.json','data/derived/paper-check.json',
          'data/derived/visual-review.json','formal/DeliveryModel.lean',
          'formal/verification.json','revisions/20260924/lean-recheck.json',
          'revisions/20260924/original-evidence-lock.json',
          'LICENSE.md','LICENSES/CC-BY-4.0.txt','LICENSES/MIT.txt','CITATION.cff']
    manifest={'schema_version':1,'version':version,'prepared_date':metadata['prepared_date'],
              'archive_name':f'redis-jetstream-reliability-v{version}.tar.gz',
              'package_root':f'redis-jetstream-reliability-v{version}',
              'public_deposit_status':metadata['public_deposit_status'],
              'doi':metadata['doi'],'core_sha256':{name:sha256(ROOT/name) for name in core},
              'full_file_manifest':'SHA256SUMS',
              'archive_identity':'Detached distribution SHA256SUMS and RELEASE.json',
              'historical_versions':'docs/ARTIFACT_MAP.md',
              'scope':'Content identity and local reproducibility, not independent archival certification.'}
    (ROOT/'release/manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    entries=write_manifest()
    verify_directory(ROOT)
    destination.parent.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f'.v{version}-',dir=destination.parent) as staging_name:
        staging=Path(staging_name)
        archive=staging/manifest['archive_name']
        stamp=int(dt.datetime.fromisoformat(metadata['prepared_date']).replace(tzinfo=dt.timezone.utc).timestamp())
        with archive.open('wb') as raw:
            with gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0) as zipped:
                with tarfile.open(fileobj=zipped,mode='w|',format=tarfile.PAX_FORMAT) as tf:
                    for name in sorted([*entries,'SHA256SUMS']):
                        path=ROOT/name
                        info=tarfile.TarInfo(f"{manifest['package_root']}/{name}")
                        info.size=path.stat().st_size
                        info.mtime=stamp
                        info.mode=0o755 if path.stat().st_mode&0o111 else 0o644
                        with path.open('rb') as source:tf.addfile(info,source)
        verified=verify_archive(archive)
        verify_directory(ROOT)
        fresh_checks=[]; outputs=[]
        with tempfile.TemporaryDirectory(prefix='msgrel-release-verification-') as extracted_name:
            extracted=Path(extracted_name)
            with tarfile.open(archive,'r:gz') as tf:tf.extractall(extracted,filter='data')
            copy_root=extracted/manifest['package_root']
            verify_directory(copy_root)
            for script in ('check_paper.py','check_revision.py','check_document_provenance.py'):
                run=subprocess.run([sys.executable,str(copy_root/'bench'/script)],
                                   cwd=copy_root,text=True,capture_output=True)
                outputs.append(f'$ python bench/{script}\n{run.stdout}{run.stderr}')
                if run.returncode:
                    raise RuntimeError(f'Extracted release check failed: {script}\n{run.stdout}{run.stderr}')
                fresh_checks.append({'script':f'bench/{script}','exit_code':run.returncode})
            verify_directory(copy_root)
        validation_log=staging/'VERIFICATION.log'
        validation_log.write_text('\n'.join(outputs))
        pdf=staging/f'redis-jetstream-reliability-v{version}.pdf'
        shutil.copyfile(ROOT/'output/pdf/redis-jetstream-reliability.pdf',pdf)
        receipt={'status':'pass','version':version,'prepared_at_utc':dt.datetime.now(dt.timezone.utc).isoformat(),
                 'public_deposit_status':'not_deposited','doi':None,
                 'verified_internal_files':verified['files_verified'],
                 'files':{p.name:{'sha256':sha256(p),'bytes':p.stat().st_size} for p in (archive,pdf,validation_log)},
                 'fresh_extraction_checks':fresh_checks,
                 'extracted_files_unchanged_after_checks':True,
                 'verification':'Every archived member matches the supplied internal manifest and working snapshot; core identities and document review agree.',
                 'immutability_scope':'Local builder refuses version reuse; files are read-only. No public archival custody is asserted.'}
        (staging/'RELEASE.json').write_text(json.dumps(receipt,indent=2)+'\n')
        (staging/'SHA256SUMS').write_text(''.join(f'{sha256(p)}  {p.name}\n' for p in sorted(staging.iterdir())))
        destination.mkdir(exist_ok=False)
        for path in staging.iterdir():
            shutil.move(str(path),destination/path.name)
            (destination/path.name).chmod(0o444)
        destination.chmod(0o555)
    print(json.dumps({'status':'pass','release_directory':str(destination),**verified},indent=2))


if __name__=='__main__':main()
