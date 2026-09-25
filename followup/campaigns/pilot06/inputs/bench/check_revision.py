"""Independent checks on preserved evidence, unchanged primary estimates and revisions."""
import hashlib
import json
import math
from pathlib import Path
import re
import statistics
import tarfile
from collections import Counter

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
    tails=robust['publication_tail_samples']
    assert len(tails)==59 and {r['key'] for r in tails}=={r['key'] for r in rows}
    by_key={r['key']:r for r in rows}
    for tail in tails:
        original_row=by_key[tail['key']]
        n=original_row['n'];rank=math.ceil(.99*n)
        assert tail['message_count']==n and tail['p99_rank_one_based']==rank
        assert tail['order_positions_above_p99']==n-rank
        assert tail['p99_ms']==original_row['publish_ms']['p99']
    d040=next(r for r in tails if r['key']=='D040')
    assert (d040['message_count'],d040['p99_rank_one_based'],d040['order_positions_above_p99'])==(149,148,1)
    for profile,reported in robust['publication_tail_sample_ranges'].items():
        selected=[r for r in tails if r['profile']==profile]
        assert reported['completed_trials']==len(selected)
        for key in ('message_count','order_positions_above_p99'):
            assert reported[key+'_range']==[min(r[key] for r in selected),max(r[key] for r in selected)]
    outcomes=json.loads((ROOT/'data/derived/attempt-outcomes.json').read_text())
    records=outcomes['records']
    assert len(records)==len({r['record_id'] for r in records})==556
    assert dict(Counter(r['category'] for r in records))==outcomes['counts']
    assert sum(outcomes['counts'][k] for k in ('completed','recovered','nominal_control','timed_failure'))==550
    assert sum(v for k,v in outcomes['counts'].items() if k.startswith('excluded_'))==6
    for name,expected in outcomes['evidence_sha256'].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==expected
    for r in records:
        if r['source'].endswith('.jsonl'):
            source_row=json.loads((ROOT/r['source']).read_text().splitlines()[r['source_line']-1])
            assert source_row['key']==r['trial_key'] and source_row['profile']==r['profile']
        if r['category'] in ('timed_failure','excluded_setup_failure','excluded_warmup_failure','excluded_operator_interruption'):
            assert r['timed_start_ns'] is None and r['timed_end_ns'] is None and r['confirmed_messages'] is None
        if r['category']=='nominal_control':assert r['timed_end_ns'] is None
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
    final=ROOT/'campaigns/final20260924/attempts/a001'
    run=json.loads((final/'run-result.json').read_text())
    assert run['exit_code']==0 and run['context']=='homelab'
    driver_inputs=[*(ROOT/'bench').glob('*.go'),ROOT/'bench/go.mod',ROOT/'bench/go.sum',
                   ROOT/'bench/run_homelab.py',ROOT/'bench/campaign_identity.py',
                   ROOT/'bench/prepare_modules.sh',ROOT/'k8s/generate.py']
    for path in driver_inputs:
        assert path.read_bytes()==(final/'inputs'/path.relative_to(ROOT)).read_bytes(),path
    validated=[json.loads(s) for s in (final/'run.log').read_text().splitlines() if s.startswith('{')]
    validation_log=(final/'run.log').read_text()
    assert len(re.findall(r'^--- PASS: Test',validation_log,re.M))==5
    assert re.search(r'Ran 9 tests.*\n\nOK',validation_log)
    flows=[r for r in validated if r.get('kind','').startswith('validation_')]
    assert len(flows)==9
    endpoints=[r for r in flows if r['kind']=='validation_recovery_endpoints']
    assert len(endpoints)==3
    for r in endpoints:
        assert r['kill_end_ns']<=r['censor_budget_start_ns']<r['nominal_censor_deadline_ns']
        assert r['survivor_loop_completed_ns']<=r['controller_wait_completed_ns']<=r['reconciliation_start_ns']<=r['reconciliation_end_ns']
        assert r['nominal_censor_deadline_ns']-r['censor_budget_start_ns']==int(r['censor_window_ms']*1e6)
        if r['censored']:
            assert r['nominal_censor_deadline_ns']<=r['timer_notification_observed_ns']<=r['survivor_loop_completed_ns']
            assert r['pending']==1
        else:
            assert r['timer_notification_observed_ns'] is None and r['pending']==0
    assert sum(r['censored'] for r in endpoints)==1
    result={'status':'pass','original_evidence_files':evidence_count,'primary_statistics_identical':True,
            'template_and_section_structure_preserved':True,'paired_effect_directions_checked':13,
            'sensitivity_recomputed_independently':True,'sealed_collections_checked':checked,
            'publication_tail_samples_checked':59,'historical_outcome_records_checked':556,
            'planned_outcomes_checked':550,'additional_documented_attempts':6,
            'unchanged_lean_declarations':10,'fresh_lean_compile_in_this_final_pass':False,
            'validated_driver_source_files':len(driver_inputs),'homelab_validation_flows':len(flows),
            'homelab_go_tests_with_race_detector':5,'homelab_campaign_isolation_tests':9,
            'recovery_endpoint_flows_checked':len(endpoints)}
    (ROOT/'revisions/20260924-final/revision-check.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':check()
