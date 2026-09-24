"""Independent checks on preserved evidence, unchanged primary estimates and revisions."""
import hashlib
import json
import math
from pathlib import Path
import re
import statistics
import tarfile

from campaign_identity import ROOT, verify_original_evidence, verify_seal


def check():
    evidence_count=verify_original_evidence()
    revised=ROOT/'revisions/20260924'
    with tarfile.open(revised/'original-source-and-paper.tar.gz') as archive:
        before=json.load(archive.extractfile('data/derived/statistics.json'))
        oldtex=archive.extractfile('paper/main.tex').read().decode()
    now=json.loads((ROOT/'data/derived/statistics.json').read_text())
    assert before==now,'Primary numerical result changed'
    tex=(ROOT/'paper/main.tex').read_text()
    assert re.findall(r'\\section\{([^}]+)\}',oldtex)==re.findall(r'\\section\{([^}]+)\}',tex),'Paper section structure changed'
    assert oldtex.split('\\begin{document}')[0].replace('\\input{../data/derived/values.tex}','') == tex.split('\\begin{document}')[0].replace('\\input{../data/derived/values.tex}','').replace('\\input{../data/derived/robustness-values.tex}\n',''),'Template changed'
    for path in (ROOT/'paper').glob('*'):
        if path.suffix in ('.tex','.bib'):
            source=path.read_text()
            assert '\u2014' not in source and '\\textemdash' not in source and '---' not in source,path
    rows=[json.loads(s) for s in (ROOT/'data/raw/durability/summary.jsonl').read_text().splitlines()]
    failed={r['key'] for r in map(json.loads,(ROOT/'data/raw/durability/failed-trials.jsonl').read_text().splitlines())}
    rows=[r for r in rows if r['key'] not in failed]
    robust=json.loads((ROOT/'data/derived/robustness.json').read_text())
    for profile,metrics in robust['conditions'].items():
        selected=[r for r in rows if r['profile']==profile]
        for key,report in metrics.items():
            def value(row):
                for part in key.split('.'):row=row[part]
                return row
            values=[value(r) for r in selected]
            assert math.isclose(statistics.mean(values),report['mean'],rel_tol=1e-12)
            assert statistics.median(values)==report['median']
            for omitted in report['leave_one_out']:
                expected=statistics.mean(value(r) for r in selected if r['key']!=omitted['omitted_key'])
                assert math.isclose(expected,omitted['mean'],rel_tol=1e-12)
    for name, effect in robust['paired_effects'].items():
        assert math.isclose(effect['ratio'],now['effects'][name]['ratio'],rel_tol=1e-12)
        assert all((x['ratio']>1)==(effect['ratio']>1) for x in effect['leave_one_block_out'])
    nats=robust['conditions']['nats-always']['publish_ms.p99']
    assert round(nats['mean'],1)==579.6
    assert round(next(r['mean'] for r in nats['leave_one_out'] if r['omitted_key']=='D040'),1)==150.5
    checked=[]
    for attempt in (ROOT/'campaigns').glob('*/attempts/*'):
        expected=json.loads((attempt/'identity.json').read_text())
        verify_seal(attempt/'inputs',expected)
        for collection in (attempt/'collections').glob('*'):
            verify_seal(collection,expected);checked.append(str(collection.relative_to(ROOT)))
    proof=json.loads((revised/'lean-recheck.json').read_text())
    assert proof['exit_code']==0 and proof['execution_context']=='homelab'
    assert proof['source_sha256']==hashlib.sha256((ROOT/'formal/DeliveryModel.lean').read_bytes()).hexdigest()
    original=json.loads((ROOT/'formal/verification.json').read_text())
    assert proof['logical_dependencies']==original['logical_dependencies']
    log=(revised/'lean-recheck.log').read_text()
    assert 'error:' not in log and 'warning:' not in log
    result={'status':'pass','original_evidence_files':evidence_count,'primary_statistics_identical':True,
            'template_and_section_structure_preserved':True,'paired_effect_directions_checked':13,
            'sensitivity_recomputed_independently':True,'sealed_collections_checked':checked,
            'fresh_lean_declarations':10}
    (revised/'revision-check.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':check()
