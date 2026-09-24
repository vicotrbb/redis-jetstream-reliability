"""Check submission preservation against the exact previously audited delivery."""
import difflib
import hashlib
import json
from pathlib import Path
import re
import sys
import tarfile

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'bench'))
from campaign_identity import verify_original_evidence
from check_document_provenance import source_hashes, validate_review


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


baseline=json.loads((HERE/'baseline-manifest.json').read_text())['files']
primary=[name for name in baseline if name.startswith('data/derived/')
         and name not in {'data/derived/build-receipt.json','data/derived/paper-check.json',
                          'data/derived/visual-review.json'}]
primary += [name for name in baseline if name.startswith('paper/figures/')]
for name in primary:
    assert digest(ROOT/name)==baseline[name],f'Numerical evidence or figure changed: {name}'
evidence=verify_original_evidence()
formal=digest(ROOT/'formal/DeliveryModel.lean')
assert formal==baseline['formal/DeliveryModel.lean']
with tarfile.open(HERE/'previous-source-and-paper.tar.gz') as tf:
    old=tf.extractfile('paper/main.tex').read().decode()
    current=(ROOT/'paper/main.tex').read_text()
    pattern=r'\\begin\{(theorem|proposition|corollary|definition|proof)\}.*?\\end\{\1\}'
    old_math=[m.group(0) for m in re.finditer(pattern,old,re.S)]
    new_math=[m.group(0) for m in re.finditer(pattern,current,re.S)]
    assert old_math and old_math==new_math,'Formal statement or proof changed'
    assert old.split('\\begin{document}')[0]==current.split('\\begin{document}')[0]
    assert re.findall(r'\\section\{([^}]+)\}',old)==re.findall(r'\\section\{([^}]+)\}',current)
    diffs=[]
    for name in ('main','abstract','results','conclusion'):
        path=f'paper/{name}.tex'
        before=tf.extractfile(path).read().decode().splitlines(keepends=True)
        after=(ROOT/path).read_text().splitlines(keepends=True)
        diffs.extend(difflib.unified_diff(before,after,fromfile='previous/'+path,tofile='v1.1.0/'+path))
(HERE/'manuscript-changes.patch').write_text(''.join(diffs))
review=json.loads((ROOT/'data/derived/visual-review.json').read_text())
validate_review(review)
check=json.loads((ROOT/'data/derived/paper-check.json').read_text())
assert review['pdf_sha256']==check['pdf_sha256']
stats=json.loads((ROOT/'data/derived/statistics.json').read_text())
trials=sum(stats['checks'][name]['trials'] for name in ('main','durability','serial'))
messages=sum(stats['checks'][name]['messages'] for name in ('main','durability','serial'))
assert (trials,messages)==(419,17411288)
tests=(HERE/'package-tests.log').read_text()
assert 'Ran 9 tests' in tests and tests.rstrip().endswith('OK')
result={'status':'pass','version':'1.1.0','previous_manifest_entries':len(baseline),
        'original_evidence_files_unchanged':evidence,
        'unchanged_numerical_and_figure_files':primary,
        'primary_timing_trials':trials,'primary_message_records':messages,
        'active_recoveries':stats['checks']['recovery']['successful_recoveries'],
        'nominal_controls':stats['checks']['recovery']['no_reclaim_censored'],
        'mathematical_statement_and_proof_blocks_unchanged':len(old_math),
        'lean_source_sha256':formal,'fresh_lean_compile':False,'new_broker_experiments':False,
        'template_and_section_order_preserved':True,
        'pdf_sha256':check['pdf_sha256'],'pages':check['pages'],'references':check['reference_count'],
        'source_sha256':source_hashes(),'packaging_integrity_fixture_tests_passed':9,
        'packaging_test_log_sha256':digest(HERE/'package-tests.log'),
        'license_scope':'LICENSE.md','public_deposit_performed':False,
        'archive_verification_receipt':'releases/v1.1.0/RELEASE.json (distributed separately from the archive)',
        'validation_scope':'Internal local reanalysis, preservation checks, and document inspection; not independent replication or external peer review.'}
(HERE/'submission-check.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ('source_sha256','unchanged_numerical_and_figure_files')},indent=2))
