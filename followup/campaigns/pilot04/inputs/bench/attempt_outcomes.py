"""Retrospective inventory of retained historical attempts, without imputed times."""
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def build(out):
    records=[]
    evidence={}

    def source(path):
        p=ROOT/path
        evidence[path]=hashlib.sha256(p.read_bytes()).hexdigest()
        return path

    def add(series,row,category,stage,path,line=None,note=''):
        start=end=None
        scope='Unavailable; no duration is imputed'
        if category in ('completed','excluded_completed_replay'):
            start=row.get('start_ns',row.get('publish_start_ns'))
            end=row.get('end_ns',row.get('drain_end_ns'))
            scope=('Timed publication window including completion of admitted requests' if series=='durability'
                   else 'Prefill start to last consumer acknowledgment; excludes setup and warm-up')
        elif category in ('recovered','nominal_control'):
            start=row['kill_start_ns'];end=row.get('redelivery_ns')
            scope=('Kill invocation to redelivery receipt' if end is not None
                   else 'Kill invocation recorded; exact observation endpoint unavailable')
        records.append({'record_id':f'historical-{len(records)+1:03d}',
            'series':series,'trial_key':row['key'],'profile':row['profile'],
            'category':category,'stage':stage,'source':source(path),'source_line':line,
            'timed_start_ns':start,'timed_end_ns':end,'timing_scope':scope,
            'utc_end':row.get('utc_end'),'nominal_censor_budget_ms':row.get('censor_window_ms'),
            'confirmed_messages':row.get('n') if category in ('completed','excluded_completed_replay') else None,
            'note':note})

    failure_path='data/raw/durability/failed-trials.jsonl'
    failures=[json.loads(s) for s in (ROOT/failure_path).read_text().splitlines()]
    failed_keys={r['key'] for r in failures}
    for series in ('main','durability','serial','recovery'):
        path=f'data/raw/{series}/summary.jsonl'
        for line,text in enumerate((ROOT/path).read_text().splitlines(),1):
            row=json.loads(text)
            if row['kind']=='error':
                assert series=='main' and row['key']=='Tmain052'
                category,stage='excluded_setup_failure','setup'
            elif series=='recovery':
                category='nominal_control' if row['censored'] else 'recovered'
                stage='consumer_recovery'
            else:
                category='excluded_completed_replay' if series=='durability' and row['key'] in failed_keys else 'completed'
                stage='timed_publication' if series=='durability' else 'prefill_and_drain'
            add(series,row,category,stage,path,line)
    for line,row in enumerate(failures,1):
        add('durability',row,'timed_failure','timed_publication',failure_path,line,
            'Client confirmation count and timings irrecoverable; retained broker contents are not confirmations')
        for path in row['evidence']:source(path)

    incidents=[
        ('main','Tmain089','redis-always','excluded_warmup_failure','warmup',
         'data/environment/main-resume-v2.log','panic: read tcp',
         'Warm-up/cleanup failure after Tmain088; cleanup masked the primary error; no timed Tmain089 trace'),
        ('durability','D022','nats-always','excluded_warmup_failure','warmup',
         'data/environment/durability-initial.log','panic: publish: nats: timeout',
         'Warm-up failed after D021; timed D022 had not begun'),
        ('durability','D031','nats-always','excluded_warmup_failure','warmup',
         'data/environment/durability-resume-first.log','panic: warmup D031',
         'Warm-up failed after D030; timed D031 had not begun'),
        ('durability','D043','nats-always','excluded_operator_interruption','timed_publication',
         'data/environment/operator-cleanup-receipt.txt','Deleted only preserved operator-interrupted stream D043',
         'Operator interruption; client timings unavailable; later completion is a separate attempt'),
    ]
    for series,key,profile,category,stage,path,anchor,note in incidents:
        lines=(ROOT/path).read_text().splitlines()
        line=next(i for i,s in enumerate(lines,1) if anchor in s)
        add(series,{'key':key,'profile':profile},category,stage,path,line,note)
    source('data/environment/operator-interruption-D043-jsz.json')
    source('data/environment/accidental-replay-through-D043.log')
    source('data/environment/outcome-manifest.json')
    counts=dict(Counter(r['category'] for r in records))
    assert counts=={'completed':419,'excluded_setup_failure':1,'excluded_completed_replay':1,
                   'recovered':120,'nominal_control':10,'timed_failure':1,
                   'excluded_warmup_failure':3,'excluded_operator_interruption':1},counts
    assert len(records)==556
    output={'role':'Retrospective inventory, not a prospective exclusion rule or complete availability denominator',
            'unit':'One completed measured attempt or documented failed/interrupted attempt; successful warm-ups are not separate rows',
            'scope':'550 planned outcomes plus six additional documented attempts; both 12-trial pilots and infrastructure setup are outside this inventory',
            'time_origin':'Historical driver CLOCK_MONOTONIC nanoseconds; UTC values are copied only where originally recorded',
            'missing_values':'Null means unrecorded, not zero. No setup, warm-up, interrupted, failed or censored endpoint is inferred.',
            'counts':counts,'record_count':len(records),'evidence_sha256':evidence,'records':records}
    out=Path(out)
    (out/'attempt-outcomes.json').write_text(json.dumps(output,indent=2)+'\n')
    with (out/'attempt-outcomes.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(records[0]));writer.writeheader();writer.writerows(records)
    tex=[r'\begin{tabular}{L{.40\linewidth}rL{.43\linewidth}}',r'\toprule',
         r'Retained outcome & Count & Treatment in this study\\',r'\midrule',
         r'Completed timing trials & 419 & 300 drain, 59 publication, 60 serial\\',
         r'Active consumer recovery & 120 & Recovered identifiers and cleared pending state\\',
         r'No-reclaimer controls & 10 & Pending at reconciliation; nominal budgets only\\',
         r'Planned publication failure & 1 & D038; client timings unavailable\\',r'\midrule',
         r'Additional setup failure & 1 & Tmain052; excluded from timed estimates\\',
         r'Additional warm-up failures & 3 & Tmain089, D022, D031; timed trials not begun\\',
         r'Operator interruption & 1 & D043; interrupted client trace unavailable\\',
         r'Completed diagnostic replay & 1 & D038; retained and excluded from estimates\\',r'\bottomrule',r'\end{tabular}']
    (out/'attempt-outcomes-table.tex').write_text('\n'.join(tex)+'\n')
    return output


if __name__=='__main__':
    from campaign_identity import verify_original_evidence
    verify_original_evidence()
    print(json.dumps(build(ROOT/'data/derived')['counts'],indent=2))
