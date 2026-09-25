"""Describe retained publication failures, request tails, and version contrasts.

Use --write to generate the report. The default independently reconstructs and
compares its supplied bytes. No broker is started and no observation is changed.
"""
import argparse
from collections import Counter
import csv
import gzip
import json
import math
from statistics import fmean

from check_followup import ROOT, digest, parsed


def table(headers, rows, alignment):
    lines = [r'\begin{tabular}{'+alignment+'}', r'\toprule',
             ' & '.join(headers)+r'\\', r'\midrule']
    lines += [' & '.join(map(str, row))+r'\\' for row in rows]
    return '\n'.join(lines+[r'\bottomrule', r'\end{tabular}'])+'\n'


def expected_outputs():
    folder = ROOT/'followup/derived'
    with (folder/'trials.csv').open(newline='') as source:
        trials = [{k: parsed(v) for k,v in row.items()} for row in csv.DictReader(source)]
    stats = json.loads((folder/'statistics.json').read_text())
    pubs = [r for r in trials if r['kind']=='publication']
    assert len(pubs)==216
    report = {'scope':'Post-observation descriptive reporting of retained primary trials; no new experiment or population failure-rate estimate.',
              'script_sha256':digest(ROOT/'bench/report_operational.py'),
              'trials_sha256':digest(folder/'trials.csv'),
              'statistics_sha256':digest(folder/'statistics.json'),
              'profiles':{}, 'timed_timeouts':[], 'completed_max_at_least_1000_ms':[],
              'versions':[], 'raw_event_sha256':{}}
    profile_rows=[]
    for profile in ('memory','periodic','always'):
        rows=[r for r in pubs if r['profile']==profile]
        failed=[r for r in rows if r['status']=='failed']
        stages=Counter(r['stage'] for r in failed)
        assert len(rows)==72 and set(stages)<={'warmup','measurement'}
        values={'planned':len(rows),'completed':len(rows)-len(failed),'failed':len(failed),
                'warmup_failed':stages['warmup'],'timed_failed':stages['measurement'],
                'failed_percent':100*len(failed)/len(rows)}
        report['profiles'][profile]=values
        profile_rows.append([profile.capitalize(),len(rows),values['completed'],stages['warmup'],
                             stages['measurement'],f"{values['failed_percent']:.1f}"])
    for row in pubs:
        timeout=row['status']=='failed' and row['stage']=='measurement'
        slow=row['status']=='complete' and row['max_ms']>=1000
        if not (timeout or slow): continue
        relative=f"followup/campaigns/{row['campaign']}/raw/{row['id']}/events.csv.gz"
        with gzip.open(ROOT/relative,'rt',newline='') as source:
            events=list(csv.DictReader(source))
        report['raw_event_sha256'][relative]=digest(ROOT/relative)
        confirmed=[e for e in events if e['confirmed']=='true']
        unknown=[e for e in events if e['confirmed']=='false']
        assert len(confirmed)==row['confirmed_records'] and len(unknown)==row['unknown_records']
        base={k:row[k] for k in ('campaign','id','engine','version','profile','publishers')}
        if timeout:
            assert unknown
            waits=[(int(e['end_ns'])-int(e['start_ns']))/1e9 for e in unknown]
            classes=Counter('nats: timeout' if e['error']=='nats: timeout' else
                            'Redis i/o timeout' if e['error'].endswith('i/o timeout') else e['error']
                            for e in unknown)
            assert set(classes)<={'nats: timeout','Redis i/o timeout'}
            report['timed_timeouts'].append({**base,'unknown_requests':len(unknown),
                'request_wait_seconds':waits,'wait_min_seconds':min(waits),'wait_max_seconds':max(waits),
                'error_classes':dict(classes)})
        else:
            assert not unknown
            maximum=max((int(e['end_ns'])-int(e['start_ns']))/1e6 for e in confirmed)
            assert math.isclose(maximum,row['max_ms'],rel_tol=1e-12)
            report['completed_max_at_least_1000_ms'].append({**base,'max_ms':maximum})
    report['completed_max_at_least_1000_ms'].sort(key=lambda r:r['max_ms'],reverse=True)
    assert len(report['timed_timeouts'])==7
    assert sum(r['unknown_requests'] for r in report['timed_timeouts'])==22
    assert len(report['completed_max_at_least_1000_ms'])==7
    assert sum(r['max_ms']>=2000 for r in report['completed_max_at_least_1000_ms'])==4
    for engine,key in [('redis','redis_current_historical'),('nats','nats_current_historical')]:
        for profile in ('memory','periodic'):
            for publishers in (1,16):
                cells=[r for r in stats['paired_contrasts'][key]['per_campaign']
                       if r['profile']==profile and r['publishers']==publishers]
                assert len(cells)==3
                values=[r['estimate'] for r in cells]
                report['versions'].append({'engine':engine,'profile':profile,'publishers':publishers,
                    'mean_ratio':fmean(values),'min_ratio':min(values),'max_ratio':max(values),
                    'complete_pairs':sum(r['complete_pairs'] for r in cells),'planned_pairs':9})
    traces=[r for r in trials if r['kind']=='trace' and r['trace']]
    assert len(traces)==12
    report['largest_traced_sync_ms']=max(r['sync_max_ms'] for r in traces)
    names={'redis':'Redis','nats':'JetStream'}
    short=lambda r:r['campaign'].removeprefix('main')+'/'+r['id']
    slow_rows=[[short(r),names[r['engine']],r['version'],int(r['publishers']),f"{r['max_ms']:.3f}"]
               for r in report['completed_max_at_least_1000_ms']]
    timeout_rows=[[short(r),names[r['engine']],r['profile'].capitalize(),int(r['unknown_requests']),
                   f"{r['wait_min_seconds']:.6f}--{r['wait_max_seconds']:.6f}",
                   'I/O timeout' if r['engine']=='redis' else 'NATS timeout'] for r in report['timed_timeouts']]
    version_rows=[[names[r['engine']],r['profile'].capitalize(),r['publishers'],
                   f"{r['mean_ratio']:.4f} [{r['min_ratio']:.4f}, {r['max_ratio']:.4f}]",
                   f"{r['complete_pairs']}/{r['planned_pairs']}"] for r in report['versions']]
    return {
        'data/derived/operational-report.json':json.dumps(report,indent=2)+'\n',
        'data/derived/publication-profile-failures.tex':table(['Profile','Planned','Complete','Warm-up','Timed','Failed, \\%'],profile_rows,'lrrrrr'),
        'data/derived/publication-request-maxima.tex':table(['Trial','System','Version','$P$','Maximum, ms'],slow_rows,'lllrr'),
        'data/derived/publication-timeouts.tex':table(['Trial','System','Profile','Unknown','Wait range, s','Error class'],timeout_rows,'lllrll'),
        'data/derived/publication-version-contrasts.tex':table(['System','Profile','$P$','Current/historical','Pairs'],version_rows,'llrlr')}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write',action='store_true')
    args=parser.parse_args()
    outputs=expected_outputs()
    for name,expected in outputs.items():
        path=ROOT/name
        if args.write: path.write_text(expected)
        else: assert path.read_text()==expected, f'Stale operational report: {name}'
    print(json.dumps({'status':'pass','generated' if args.write else 'verified':len(outputs),
                      'timed_failure_traces':7,'completed_slow_traces':7}))


if __name__=='__main__': main()
