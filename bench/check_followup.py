"""Independent offline checks of follow-up summaries, pairing, and provenance.

The full event reconstruction is bench/followup/analyze.py. This second check
uses Python's standard library to independently aggregate the retained trial
measurements and reject stale, missing, or incorrectly paired results.
"""
from collections import Counter, defaultdict
import csv
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
from statistics import fmean, median

ROOT = Path(__file__).resolve().parents[1]
DERIVED = ROOT/'followup/derived'


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(1 << 20), b''): h.update(block)
    return h.hexdigest()


def near(a, b):
    assert math.isclose(float(a), float(b), rel_tol=3e-12, abs_tol=1e-8), (a, b)


def parsed(value):
    if value == '': return None
    if value in ('True', 'False'): return value == 'True'
    try: return float(value)
    except ValueError: return value


def read_json(path):
    return json.loads(path.read_text())


def main():
    stats = read_json(DERIVED/'statistics.json')
    assert stats['analysis_sha256'] == digest(ROOT/'bench/followup/analyze.py')
    assert stats['trials_csv_sha256'] == digest(DERIVED/'trials.csv')
    with (DERIVED/'trials.csv').open(newline='') as source:
        rows = [{k: parsed(v) for k, v in r.items()} for r in csv.DictReader(source)]
    assert len(rows) == 612
    assert Counter(r['kind'] for r in rows) == stats['kinds'] == {
        'publication': 216, 'drain': 96, 'recovery': 252, 'trace': 24, 'compression': 24}
    assert Counter(r['status'] for r in rows) == stats['outcomes']
    by_id = {(r['campaign'], r['id']): r for r in rows}
    assert len(by_id) == 612
    raw_files, sealed_inputs = 0, 0
    campaign_cleanup_times = []
    for campaign in ('main01', 'main02', 'main03'):
        folder = ROOT/'followup/campaigns'/campaign
        identity, plan = read_json(folder/'identity.json'), read_json(folder/'plan.json')
        assert not identity['pilot'] and identity['context'] == 'homelab'
        assert identity['plan_sha256'] == digest(folder/'plan.json')
        assert len(plan) == 204
        completion, cleanup = read_json(folder/'completion.json'), read_json(folder/'cleanup.json')
        assert completion['planned'] == completion['collected'] == 204
        assert completion['context'] == cleanup['context'] == 'homelab'
        assert cleanup['namespace'] == identity['namespace']
        assert datetime.fromisoformat(completion['completed_utc']) <= datetime.fromisoformat(cleanup['deleted_utc'])
        campaign_cleanup_times.append(datetime.fromisoformat(cleanup['deleted_utc']))
        assert {(campaign, t['id']) for t in plan} == {key for key in by_id if key[0] == campaign}
        assert not list(folder.glob('*-infrastructure-error.json'))
        for name, expected in read_json(folder/'inputs/SHA256.json').items():
            assert digest(folder/'inputs'/name) == expected, name
            sealed_inputs += 1
        for name in ('main.go', 'client.go', 'control.go', 'main_test.go', 'run.py'):
            relative = 'bench/followup/'+name
            assert (folder/'inputs'/relative).read_bytes() == (ROOT/relative).read_bytes(), relative
        lock = read_json(folder/'RAW_SHA256.json')
        assert set(lock) == {str(p.relative_to(folder)) for p in (folder/'raw').rglob('*') if p.is_file()}
        for name, expected in lock.items():
            assert digest(folder/name) == expected, name
            raw_files += 1
        for trial in plan:
            observed = read_json(folder/'raw'/trial['id']/'result.json')
            flat = by_id[campaign, trial['id']]
            assert flat['status'] == observed['status'] and flat['stage'] == observed['stage']
            if observed['status'] == 'complete' and trial['kind'] != 'recovery':
                near(flat['throughput_mps'], observed['throughput_mps'])
                near(flat['p99_ms'], observed['latency_ms']['p99'])
                assert flat['sample_count'] == observed['confirmed']
            if trial['kind'] == 'recovery' and trial['recovery'] != 'none' and observed['status'] == 'complete':
                near(flat['receipt_excess_ms'], (observed['redelivery_ns']-observed['receipt_ns'])/1e6-trial['delta_ms'])

    aggregate_cells = 0
    for kind in ('publication', 'drain', 'recovery', 'trace', 'compression'):
        metric = 'receipt_excess_ms' if kind == 'recovery' else 'throughput_mps'
        grouping = ['engine','version','recovery','delta_ms','age','kill'] if kind == 'recovery' else [
            'engine','version','profile','publishers','consumers','cpus','payload','compression','trace']
        groups = defaultdict(list)
        for row in rows:
            if row['kind'] != kind or (kind == 'recovery' and row['recovery'] == 'none'): continue
            groups[tuple(row[k] for k in ['campaign']+grouping)].append(row)
        reported = stats[kind]
        assert len(groups) == len(reported['outcome_counts'])
        for count in reported['outcome_counts']:
            group = groups[tuple(count[k] for k in ['campaign']+grouping)]
            complete = [r for r in group if r['status'] == 'complete']
            assert (count['planned'], count['completed'], count['failed']) == (len(group), len(complete), len(group)-len(complete))
        means_by_condition = defaultdict(list)
        expected_complete_groups = {key for key, group in groups.items()
                                    if any(r['status'] == 'complete' for r in group)}
        assert {tuple(cell[k] for k in ['campaign']+grouping)
                for cell in reported['per_campaign']} == expected_complete_groups
        for cell in reported['per_campaign']:
            group = groups[tuple(cell[k] for k in ['campaign']+grouping)]
            values = [r[metric] for r in group if r['status'] == 'complete']
            assert len(values) == cell['count']
            for key, value in [('mean', fmean(values)), ('median', median(values)), ('min', min(values)), ('max', max(values))]:
                near(cell[key], value)
            means_by_condition[tuple(cell[k] for k in grouping)].append(fmean(values))
            aggregate_cells += 1
        assert len(means_by_condition) == len(reported['across_campaign_means'])
        for cell in reported['across_campaign_means']:
            values = means_by_condition[tuple(cell[k] for k in grouping)]
            assert len(values) == cell['count']
            near(cell['mean'], fmean(values)); near(cell['min'], min(values)); near(cell['max'], max(values))

    paired_cells, paired_blocks = 0, 0
    expected_contrasts = {
        'periodic_memory':(24,72),'always_memory':(24,72),
        'publishers_16_1':(36,108),'redis_current_historical':(18,54),
        'nats_current_historical':(18,54),'consumers_16_1':(24,48),
        'driver_cpus_4_2':(24,48),'kill_live_receipt_excess_ms':(60,120),
        'kill_live_reference_to_redelivery_ms':(60,120),'trace_untraced':(12,12),
        'compression_off_inherited':(12,12),'random_compressible':(12,12)}
    assert set(stats['paired_contrasts']) == set(expected_contrasts)
    for name, (cells, blocks) in expected_contrasts.items():
        observed = stats['paired_contrasts'][name]['per_campaign']
        assert len(observed) == cells and sum(c['planned_pairs'] for c in observed) == blocks
    for contrast in stats['paired_contrasts'].values():
        identity_keys = sorted(contrast['per_campaign'][0].keys()-{
            'planned_pairs','complete_pairs','unavailable_pairs','estimate','pairs'})
        supplied = [tuple(c[k] for k in identity_keys) for c in contrast['per_campaign']]
        intended = {tuple(r[k] for k in identity_keys) for r in rows
                    if r['kind'] == contrast['kind']
                    and r[contrast['factor']] in (contrast['numerator'],contrast['denominator'])
                    and not (r['kind'] == 'recovery' and r['recovery'] == 'none')}
        assert len(supplied) == len(set(supplied)) and set(supplied) == intended
        for cell in contrast['per_campaign']:
            selectors = {key: cell[key] for key in cell.keys()-{
                'planned_pairs','complete_pairs','unavailable_pairs','estimate','pairs'}}
            eligible = [r for r in rows if r['kind'] == contrast['kind']
                        and r[contrast['factor']] in (contrast['numerator'], contrast['denominator'])
                        and all(r[k] == v for k, v in selectors.items())]
            assert {p['block'] for p in cell['pairs']} == {r['block'] for r in eligible}
            assert len(cell['pairs']) == len({p['block'] for p in cell['pairs']})
            positive, negative = [], []
            for pair in cell['pairs']:
                pairrows = [by_id.get((cell['campaign'], pair[k])) for k in ('numerator_trial', 'denominator_trial')]
                a, b = pairrows
                for r, value in zip(pairrows, (contrast['numerator'], contrast['denominator'])):
                    if r is not None:
                        assert r['kind'] == contrast['kind'] and r['block'] == pair['block']
                        assert r[contrast['factor']] == value
                        for key in cell.keys()-{'planned_pairs','complete_pairs','unavailable_pairs','estimate','pairs'}:
                            assert r[key] == cell[key]
                completed = a is not None and b is not None and a['status'] == b['status'] == 'complete'
                assert completed == pair['complete']
                if completed:
                    near(pair['numerator'], a[contrast['metric']]); near(pair['denominator'], b[contrast['metric']])
                    positive.append(a[contrast['metric']]); negative.append(b[contrast['metric']])
                else: assert pair['numerator'] is None and pair['denominator'] is None
                paired_blocks += 1
            assert cell['planned_pairs'] == len(cell['pairs'])
            assert cell['complete_pairs'] == len(positive)
            assert cell['unavailable_pairs'] == len(cell['pairs'])-len(positive)
            if positive:
                estimate = fmean(positive)-fmean(negative) if contrast['estimand'].startswith('difference') else fmean(positive)/fmean(negative)
                near(cell['estimate'], estimate)
            else: assert cell['estimate'] is None
            paired_cells += 1

    report = read_json(DERIVED/'report.json')
    assert report['generator_sha256'] == digest(ROOT/'bench/followup/report.py')
    assert report['statistics_sha256'] == digest(DERIVED/'statistics.json')
    assert report['trials_sha256'] == digest(DERIVED/'trials.csv')
    for name, expected in report['generated_sha256'].items(): assert digest(ROOT/name) == expected
    # A report range is over campaign means, never a pooled-message interval.
    def inspect(node):
        if isinstance(node, list):
            for child in node: inspect(child)
        elif isinstance(node, dict):
            key = 'campaign_means' if 'campaign_means' in node else 'campaign_estimates' if 'campaign_estimates' in node else None
            if key:
                values = [v for v in node[key].values() if v is not None]
                assert node['campaigns'] == len(values)
                if values:
                    near(node['mean'], fmean(values)); near(node['min'], min(values)); near(node['max'], max(values))
                else: assert node['mean'] is node['min'] is node['max'] is None
            for child in node.values(): inspect(child)
    inspect(report)

    # Independently bind every displayed measure to its intended raw condition.
    # Internal mean/range consistency alone would not detect mixed-up selectors.
    def selected(kind, **conditions):
        return [r for r in rows if r['kind'] == kind and all(r[k] == v for k, v in conditions.items())]

    def check_measure(observed, group, metric):
        complete = [r for r in group if r['status'] == 'complete' and r.get(metric) is not None]
        campaigns = defaultdict(list)
        for r in complete: campaigns[r['campaign']].append(r[metric])
        assert observed['planned'] == len(group) and observed['completed'] == len(complete)
        assert set(observed['campaign_means']) == set(campaigns)
        for campaign, values in campaigns.items(): near(observed['campaign_means'][campaign], fmean(values))

    def check_contrast(observed, name, **conditions):
        cells = [c for c in stats['paired_contrasts'][name]['per_campaign']
                 if all(c[k] == v for k, v in conditions.items())]
        assert observed['planned_pairs'] == sum(c['planned_pairs'] for c in cells)
        assert observed['complete_pairs'] == sum(c['complete_pairs'] for c in cells)
        assert set(observed['campaign_estimates']) == {c['campaign'] for c in cells}
        for c in cells:
            if c['estimate'] is None: assert observed['campaign_estimates'][c['campaign']] is None
            else: near(observed['campaign_estimates'][c['campaign']], c['estimate'])

    assert {k: len(report[k]) for k in ('publication','drain','recovery','trace','compression')} == {
        'publication':24,'drain':8,'recovery':20,'trace':4,'compression':4}
    display_keys = {
        'publication':('engine','version','profile','publishers'),
        'drain':('engine','version','profile','cpus'),
        'recovery':('engine','version','recovery','delta_ms','age'),
        'trace':('engine','version','profile','publishers'),
        'compression':('engine','version','profile','payload')}
    for kind, keys in display_keys.items():
        expected = {tuple(r[k] for k in keys) for r in rows if r['kind'] == kind
                    and not (kind == 'recovery' and r['recovery'] == 'none')}
        displayed = [tuple(entry[k] for k in keys) for entry in report[kind]]
        assert len(displayed) == len(set(displayed)) and set(displayed) == expected
    for entry in report['publication']:
        conditions = {k: entry[k] for k in ('engine','version','profile','publishers')}
        group = selected('publication', **conditions)
        check_measure(entry['throughput_mps'], group, 'throughput_mps')
        check_measure(entry['mean_trial_p99_ms'], group, 'p99_ms')
        for field, metric in [('sample_count_range','sample_count'),('positions_above_p99_range','positions_above_p99')]:
            values = [r[metric] for r in group if r['status'] == 'complete']
            assert entry[field] == ([min(values),max(values)] if values else None)
    for entry in report['drain']:
        conditions = {k: entry[k] for k in ('engine','version','profile','cpus')}
        for consumers in (1,16):
            check_measure(entry[f'c{consumers}_throughput_mps'], selected('drain', consumers=consumers, **conditions), 'throughput_mps')
            check_measure(entry[f'c{consumers}_p99_ms'], selected('drain', consumers=consumers, **conditions), 'p99_ms')
        high = selected('drain', consumers=16, **conditions)
        for who in ('driver','broker'): check_measure(entry['c16_cpu'][who], high, who+'_mean_cores')
        check_contrast(entry['paired_speedup'], 'consumers_16_1', **conditions)
    for entry in report['recovery']:
        conditions = {k: entry[k] for k in ('engine','version','recovery','delta_ms','age')}
        for killed, field in ((False,'live_excess_ms'),(True,'killed_excess_ms')):
            check_measure(entry[field], selected('recovery', kill=killed, **conditions), 'receipt_excess_ms')
        check_contrast(entry['paired_kill_minus_live_ms'], 'kill_live_receipt_excess_ms', **conditions)
    for entry in report['trace']:
        conditions = {k: entry[k] for k in ('engine','version','profile','publishers')}
        for metric in ('sync_complete_calls','sync_calls_per_confirmed_message','sync_p50_ms',
                       'sync_p99_ms','sync_sum_call_seconds','sync_errors'):
            check_measure(entry[metric], selected('trace', trace=True, **conditions), metric)
        check_contrast(entry['traced_untraced_ratio'], 'trace_untraced', **conditions)
    for entry in report['compression']:
        conditions = {k: entry[k] for k in ('engine','version','profile','payload')}
        for policy in ('inherited','off'):
            check_measure(entry[policy], selected('compression', compression=policy, **conditions), 'throughput_mps')
        check_contrast(entry['off_inherited_ratio'], 'compression_off_inherited', **conditions)

    formal = read_json(ROOT/'revisions/20260924-followup/lean-recheck.json')
    assert formal['status'] == 'pass' and formal['exit_code'] == 0 and formal['execution_context'] == 'homelab'
    assert formal['execution_after_benchmark_collection']
    proof_start = read_json(ROOT/'revisions/20260924-followup/lean-recheck-started.json')
    assert max(campaign_cleanup_times) <= datetime.fromisoformat(proof_start['started_utc']) <= datetime.fromisoformat(formal['checked_at_utc'])
    proof_cleanup = read_json(ROOT/'revisions/20260924-followup/lean-cleanup.json')
    assert proof_cleanup['context'] == 'homelab' and proof_cleanup['namespace'] == formal['namespace']
    assert proof_cleanup['absence_returncode'] != 0 and 'NotFound' in proof_cleanup['absence_stderr']
    assert formal['source_sha256'] == digest(ROOT/formal['source'])
    log = (ROOT/formal['log']).read_text()
    assert formal['source_sha256'] in log and formal['compiler_binary_sha256'] in log
    assert len(formal['logical_dependencies']) == 10 and 'error:' not in log and 'warning:' not in log
    original_proof = read_json(ROOT/'formal/verification.json')
    for key in ('logical_dependencies','compiler_version','compiler_commit','compiler_binary_sha256',
                'toolchain_archive_sha256','imports'):
        assert formal[key] == original_proof[key]
    result = {'status': 'pass', 'outcomes': stats['outcomes'], 'planned': len(rows),
              'raw_files_checked': raw_files, 'sealed_inputs_checked': sealed_inputs,
              'independently_aggregated_campaign_cells': aggregate_cells,
              'paired_contrast_cells': paired_cells, 'paired_blocks': paired_blocks,
              'statistics_sha256': digest(DERIVED/'statistics.json'), 'report_sha256': digest(DERIVED/'report.json'),
              'fresh_homelab_lean_receipt_sha256': digest(ROOT/'revisions/20260924-followup/lean-recheck.json'),
              'scope': 'Offline consistency and independent summary recalculation; not external experimental replication.'}
    (ROOT/'revisions/20260924-followup/followup-check.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__': main()
