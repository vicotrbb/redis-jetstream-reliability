"""Recompute follow-up observations without running brokers or replacing old data."""
import argparse
from collections import Counter
from decimal import Decimal
import gzip
import hashlib
import json
import math
from pathlib import Path
import re

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]


def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()


def exact(a,b):
    assert math.isclose(float(a),float(b),rel_tol=2e-12,abs_tol=1e-9),(a,b)


def sample_cpu(before,after,quota):
    assert {'usage_usec','nr_throttled','throttled_usec'} <= before['cpu'].keys()
    assert {'usage_usec','nr_throttled','throttled_usec'} <= after['cpu'].keys()
    interval=(after['start_ns']-before['start_ns'])/1e9
    assert interval>0
    delta={k:after['cpu'][k]-before['cpu'][k] for k in before['cpu']}
    assert all(v>=0 for v in delta.values())
    cores=delta['usage_usec']/1e6/interval
    def host(s):
        first=s['host_cpu_stat'].splitlines()[0].split()
        assert first[0]=='cpu'
        return np.array([int(v) for v in first[1:9]],dtype=np.int64)
    hd=host(after)-host(before)
    host_busy=(hd.sum()-hd[3]-hd[4])/hd.sum() if hd.sum()>0 else None
    return {'sample_seconds':interval,'mean_cores':cores,'quota_percent':100*cores/quota,
            'throttled_usec':delta['throttled_usec'],'throttled_periods':delta['nr_throttled'],
            'host_busy_fraction':host_busy,'host_iowait_fraction':hd[4]/hd.sum() if hd.sum()>0 else None}


def events(path,receipt):
    assert path.name==receipt['path'] and digest(path)==receipt['sha256'],path
    frame=pd.read_csv(path,dtype={'id':'int64','start_ns':'int64','end_ns':'int64',
                                  'received_ns':'int64','worker':'int64','confirmed':'bool'},keep_default_na=False)
    assert len(frame)==receipt['records']
    assert (frame.start_ns>0).all()
    assert ((frame.end_ns>=frame.start_ns)|(frame.end_ns==0)).all()
    assert (frame.loc[frame.confirmed,'end_ns']>=frame.loc[frame.confirmed,'start_ns']).all()
    for _,group in frame.groupby('worker',sort=False):
        previous=group.end_ns.to_numpy()[:-1]
        following=group.start_ns.to_numpy()[1:]
        assert (following>=previous).all()
    return frame


def syscall_summary(folder,row):
    # Broker and driver monotonic clocks are distinct; only broker wall time is used.
    low=row['publication_broker_before']['wall_ns']
    high=row['publication_broker_after']['wall_ns']
    calls=[];unparsed=[];boundary=0
    for path in sorted(folder.glob('sync.trace*.gz')):
        pending=None
        for line in gzip.open(path,'rt'):
            m=re.match(r'^(\d+\.\d+)\s+(.*)',line)
            if not m: continue
            stamp=int(Decimal(m[1])*1000000000);body=m[2].strip()
            start=re.match(r'(fsync|fdatasync)\(',body)
            resumed=re.match(r'<\.\.\. (fsync|fdatasync) resumed>',body)
            if not start and not resumed: continue
            if start and '<unfinished ...>' in body:
                assert pending is None,(path,line)
                pending=(stamp,start[1]);continue
            if resumed:
                assert pending is not None,(path,line)
                stamp,name=pending;pending=None
            else: name=start[1]
            duration=re.search(r'<([0-9.]+)>\s*$',body)
            result=re.search(r'=\s*(-?\d+)',body)
            if not duration or not result:
                unparsed.append({'file':path.name,'line':line.strip()});continue
            nanos=int(Decimal(duration[1])*1000000000)
            if stamp>=low and stamp+nanos<=high:
                calls.append({'call':name,'duration_ms':nanos/1e6,'return':int(result[1])})
            elif stamp<high and stamp+nanos>low: boundary+=1
        if pending: unparsed.append({'file':path.name,'pending':pending})
    assert not unparsed,unparsed[:3]
    assert calls,'No complete synchronization calls in broker-side phase brackets'
    durations=np.array([c['duration_ms'] for c in calls])
    return {'complete_calls':len(calls),'by_call':dict(Counter(c['call'] for c in calls)),
            'errors':sum(c['return']<0 for c in calls),'mean_ms':float(durations.mean()),
            'p50_ms':float(np.quantile(durations,.5,method='inverted_cdf')),
            'p99_ms':float(np.quantile(durations,.99,method='inverted_cdf')),
            'max_ms':float(durations.max()),'sum_call_seconds':float(durations.sum()/1000),
            'broker_bracket_seconds':(high-low)/1e9,'boundary_overlap_calls':boundary,
            'calls_per_confirmed_message':len(calls)/row['confirmed']}


def verify_trial(folder,expected):
    row=json.loads((folder/'result.json').read_text());t=row['trial']
    assert {k:v for k,v in t.items() if k!='fault'}=={k:v for k,v in expected.items() if k!='fault'}
    assert t.get('fault','')==expected.get('fault','')
    assert row['gomaxprocs']==t['cpus']
    record={**t,'status':row['status'],'error':row.get('error'),'stage':row['stage']}
    for field in ('trace','preload_trace'):
        if field in row and row[field]:
            frame=events(folder/row[field]['path'],row[field])
            if field=='preload_trace' and row['status']=='complete':
                assert len(frame)==t['count'] and frame.confirmed.all()
                assert np.array_equal(np.sort(frame.id),np.arange(t['count']))
            if field=='trace':
                complete=frame[frame.confirmed]
                record['attempt_records']=len(frame);record['confirmed_records']=len(complete)
                if t['kind']!='drain':
                    assert np.array_equal(np.sort(frame.id),np.arange(len(frame)))
                    assert row['attempted']==len(frame) and row['confirmed']==len(complete)
                    if 'admitted_ns' in frame:
                        assert ((frame.admitted_ns>=row['start_ns'])&(frame.admitted_ns<row['admission_deadline_ns'])).all()
                        assert (frame.start_ns>=frame.admitted_ns).all()
                if row['status']=='complete':
                    assert frame.confirmed.all() and len(frame)>0
                    assert row['confirmed']==len(frame)
                    assert row['end_ns']==int(frame.end_ns.max())
                    exact(row['throughput_mps'],len(frame)*1e9/(row['end_ns']-row['start_ns']))
                    latency=(frame.end_ns-frame.start_ns).to_numpy()/1e6
                    for q,key in ((.5,'p50'),(.99,'p99'),(1,'max')):
                        exact(row['latency_ms'][key],np.quantile(latency,q,method='inverted_cdf'))
                    exact(row['latency_ms']['mean'],latency.mean())
                    assert (frame.start_ns>=row['start_ns']).all()
                    record.update(throughput_mps=row['throughput_mps'],p50_ms=row['latency_ms']['p50'],
                                  p99_ms=row['latency_ms']['p99'],sample_count=len(frame),
                                  p99_rank=math.ceil(.99*len(frame)),positions_above_p99=len(frame)-math.ceil(.99*len(frame)),
                                  measured_seconds=(row['end_ns']-row['start_ns'])/1e9)
                    if t['kind']=='drain':
                        assert np.array_equal(np.sort(frame.id),np.arange(t['count']))
                        assert ((frame.received_ns>=frame.start_ns)&(frame.received_ns<=frame.end_ns)).all()
                        occupancy=(frame.end_ns-frame.start_ns).sum()/(row['end_ns']-row['start_ns'])/t['consumers']
                        assert 0<=occupancy<=1+1e-12
                        record['occupancy']=float(occupancy)
    if row['status']!='complete':
        return record
    assert 'stop_error' not in row and 'diagnostic_collection_error' not in row
    stop=row['broker_stop'];assert stop['process_group_gone'] and stop['broker_port_closed']
    assert stop['cleanup_error']=='<nil>'
    if t['compression']=='off':
        files=[f for f in stop['storage_inventory'] if f['path'].startswith('store/') and not f['mode'].startswith('d')]
        assert files and all(f['flags_error']=='<nil>' and f['flags']&0x400 and not f['flags']&0x4 for f in files)
    if t['kind']=='recovery':
        assert row['receipt_ns']<=row['survivor_first_request_ns']<=row['reference_start_ns']<=row['reference_end_ns']
        assert row['survivor_end_ns']<=row['controller_end_ns']<=row['reconciliation_start_ns']<=row['reconciliation_end_ns']
        assert row['inventory']['stored']==1
        record.update(delta_ms=t['delta_ms'],censored=row['censored'],actual_age_ms=row['actual_receipt_age_ms'],
                      observation_seconds=(row['survivor_end_ns']-row['reference_start_ns'])/1e9)
        if t['recovery']=='none':
            assert row['censored'] and row['timer_branch_selected'] and row['inventory']['pending']==1
            assert row['nominal_deadline_ns']<=row['timer_observed_ns']<=row['survivor_end_ns']
        else:
            assert not row['censored'] and row['inventory']['pending']==0
            if t['engine']=='nats': assert row['deliveries']==2
            exact(row['receipt_excess_ms'],(row['redelivery_ns']-row['receipt_ns'])/1e6-t['delta_ms'])
            exact(row['reference_to_redelivery_ms'],(row['redelivery_ns']-row['reference_start_ns'])/1e6)
            record.update(receipt_excess_ms=row['receipt_excess_ms'],reference_to_redelivery_ms=row['reference_to_redelivery_ms'],
                          redelivery_before_reference=row['redelivery_before_reference'],after_nominal_deadline=row['redelivery_after_nominal_deadline'])
    else:
        assert row['payload_verification']['all_512_bytes_equal']
        assert row['payload_verification']['expected_ids']==row['payload_verification']['readback_ids']==row['confirmed']
        assert row['inventory']['stored']==row['confirmed'] and row['inventory']['pending']==0
        phase='drain' if t['kind']=='drain' else 'publication'
        for who,quota in (('driver',t['cpus']),('broker',2)):
            before=row[f'{phase}_{who}_before'];after=row[f'{phase}_{who}_after']
            if who=='driver':assert before['end_ns']<=row['start_ns']<=row['end_ns']<=after['start_ns']
            for name,value in sample_cpu(before,after,quota).items():record[f'{who}_{name}']=value
        if t['trace']:
            for name,value in syscall_summary(folder,row).items():record['sync_'+name]=value
    return record


def summary(frame,keys,value):
    selected=frame[(frame.status=='complete')&frame[value].notna()]
    campaigns=selected.groupby(['campaign']+keys,dropna=False)[value].agg(['count','mean','median','min','max']).reset_index()
    across=campaigns.groupby(keys,dropna=False)['mean'].agg(['count','mean','min','max']).reset_index()
    return {'per_campaign':json.loads(campaigns.to_json(orient='records')),
            'across_campaign_means':json.loads(across.to_json(orient='records'))}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--campaigns',nargs='+',default=['main01','main02','main03'])
    parser.add_argument('--output',default='followup/derived')
    parser.add_argument('--pilot',action='store_true')
    args=parser.parse_args();records=[];receipts=[]
    for name in args.campaigns:
        folder=ROOT/'followup/campaigns'/name
        identity=json.loads((folder/'identity.json').read_text())
        assert identity['context']=='homelab' and identity['pilot']==args.pilot
        assert digest(folder/'plan.json')==identity['plan_sha256']
        for relative,expected in json.loads((folder/'inputs/SHA256.json').read_text()).items():
            assert digest(folder/'inputs'/relative)==expected
        lock=json.loads((folder/'RAW_SHA256.json').read_text())
        actual={str(p.relative_to(folder)) for p in (folder/'raw').rglob('*') if p.is_file()}
        assert actual==set(lock)
        for relative,expected in lock.items():assert digest(folder/relative)==expected
        plan=json.loads((folder/'plan.json').read_text())
        assert {p.parent.name for p in (folder/'raw').glob('*/result.json')}=={t['id'] for t in plan}
        for trial in plan:records.append(verify_trial(folder/'raw'/trial['id'],trial))
        receipts.append({'campaign':name,'planned':len(plan),'raw_files':len(lock),'plan_sha256':digest(folder/'plan.json'),'raw_manifest_sha256':digest(folder/'RAW_SHA256.json')})
    output=ROOT/args.output;output.mkdir(parents=True,exist_ok=True)
    frame=pd.DataFrame(records);frame.to_csv(output/'trials.csv',index=False)
    result={'campaigns':receipts,'outcomes':dict(Counter(r['status'] for r in records)),
            'kinds':dict(Counter(r['kind'] for r in records)),'verified_event_records':sum(r.get('attempt_records',0) for r in records),
            'scope':'Separate deployments on shared hardware; ranges of campaign means, no asserted population interval coverage.'}
    keys=['engine','version','profile','publishers','consumers','cpus','payload','compression','trace']
    for kind in ('publication','drain','trace','compression'):
        part=frame[frame.kind==kind]
        if len(part):result[kind]=summary(part,keys,'throughput_mps')
    recovery=frame[(frame.kind=='recovery')&(frame.recovery!='none')]
    if len(recovery):result['recovery']=summary(recovery,['engine','version','recovery','delta_ms','age','kill'],'receipt_excess_ms')
    (output/'statistics.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:result[k] for k in ('outcomes','kinds','verified_event_records')},indent=2))


if __name__=='__main__':main()
