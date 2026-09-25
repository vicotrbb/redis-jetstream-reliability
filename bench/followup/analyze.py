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
    assert (frame.loc[frame.confirmed,'error']=='').all()
    assert (frame.worker>=0).all()
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
    expected={f['path']+'.gz' for f in row['broker_stop']['storage_inventory'] if f['path'].startswith('sync.trace')}
    assert expected and {p.name for p in folder.glob('sync.trace*.gz')}==expected, 'Missing or extra syscall trace files'
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
    if row['status']=='complete' and t['kind']!='recovery':
        assert row.get('trace'), 'Completed workload is missing its event trace'
        if t['kind']=='drain':assert row.get('preload_trace'), 'Completed drain is missing its preload trace'
    for field in ('trace','preload_trace'):
        if field in row and row[field]:
            frame=events(folder/row[field]['path'],row[field])
            workers=t['consumers'] if field=='trace' and t['kind']=='drain' else t['publishers']
            assert (frame.worker<workers).all()
            if field=='preload_trace' and row['status']=='complete':
                assert len(frame)==t['count'] and frame.confirmed.all()
                assert np.array_equal(np.sort(frame.id),np.arange(t['count']))
            if field=='trace':
                complete=frame[frame.confirmed]
                record['attempt_records']=len(frame);record['confirmed_records']=len(complete)
                record['unknown_records']=len(frame)-len(complete)
                if t['kind']!='drain':
                    assert np.array_equal(np.sort(frame.id),np.arange(len(frame)))
                    assert row['attempted']==len(frame) and row['confirmed']==len(complete)
                    assert 'admitted_ns' in frame
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
                                  mean_ms=row['latency_ms']['mean'],max_ms=row['latency_ms']['max'],
                                  p99_rank=math.ceil(.99*len(frame)),positions_above_p99=len(frame)-math.ceil(.99*len(frame)),
                                  measured_seconds=(row['end_ns']-row['start_ns'])/1e9)
                    if t['kind']=='drain':
                        assert np.array_equal(np.sort(frame.id),np.arange(t['count']))
                        assert ((frame.received_ns>=frame.start_ns)&(frame.received_ns<=frame.end_ns)).all()
                        occupancy=(frame.end_ns-frame.start_ns).sum()/(row['end_ns']-row['start_ns'])/t['consumers']
                        assert 0<=occupancy<=1+1e-12
                        record['occupancy']=float(occupancy)
    if row['status']!='complete':
        if row.get('joined_ns') and row.get('start_ns'):
            record['seconds_until_workers_joined']=(row['joined_ns']-row['start_ns'])/1e9
        if row.get('inventory'):
            record['retained_count_at_reconciliation']=row['inventory'].get('stored')
        record['reset_verified']=bool(row.get('broker_stop',{}).get('process_group_gone') and row.get('broker_stop',{}).get('broker_port_closed') and row.get('broker_stop',{}).get('cleanup_error')=='<nil>')
        return record
    assert 'stop_error' not in row and 'diagnostic_collection_error' not in row
    assert (folder/'server.conf.gz').is_file() and (folder/'server.log.gz').is_file()
    stop=row['broker_stop'];assert stop['process_group_gone'] and stop['broker_port_closed']
    assert stop['cleanup_error']=='<nil>'
    if t['compression']=='off':
        files=[f for f in stop['storage_inventory'] if f['path'].startswith('store/') and not f['mode'].startswith('d')]
        assert files and all(f['flags_error']=='<nil>' and f['flags']&0x400 and not f['flags']&0x4 for f in files)
    if t['kind']=='recovery':
        if t['kill']:assert row['victim_exit']=='signal: killed'
        else:assert 'victim_exit' not in row
        assert row['receipt_ns']<=row['survivor_first_request_ns']<=row['reference_start_ns']<=row['reference_end_ns']
        assert row['reference_end_ns']<=row['budget_start_ns']<row['nominal_deadline_ns']
        budget_ms=2*t['delta_ms'] if t['recovery']=='none' else 5*t['delta_ms']+2000
        assert row['nominal_deadline_ns']-row['budget_start_ns']==budget_ms*1000000
        exact(row['actual_receipt_age_ms'],(row['reference_start_ns']-row['receipt_ns'])/1e6)
        assert row['timer_branch_selected']==('timer_observed_ns' in row)
        assert row['censored']==('redelivery_ns' not in row)
        assert row['survivor_end_ns']<=row['controller_end_ns']<=row['reconciliation_start_ns']<=row['reconciliation_end_ns']
        assert row['inventory']['stored']==1
        record.update(delta_ms=t['delta_ms'],censored=row['censored'],actual_age_ms=row['actual_receipt_age_ms'],
                      observation_seconds=(row['survivor_end_ns']-row['reference_start_ns'])/1e9)
        if t['recovery']=='none':
            assert row['censored'] and row['timer_branch_selected'] and row['inventory']['pending']==1
            assert row['nominal_deadline_ns']<=row['timer_observed_ns']<=row['survivor_end_ns']
        else:
            assert not row['censored'] and row['inventory']['pending']==0
            assert row['survivor_first_request_ns']<=row['redelivery_ns']<=row['survivor_end_ns']
            assert row['redelivery_before_reference']==(row['redelivery_ns']<row['reference_start_ns'])
            assert row['redelivery_after_nominal_deadline']==(row['redelivery_ns']>row['nominal_deadline_ns'])
            assert row['received_during_shutdown']==(row['timer_branch_selected'] and row['redelivery_ns']>=row['timer_observed_ns'])
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
    frame=frame.copy()
    if value not in frame:frame[value]=np.nan
    counts=frame.groupby(['campaign']+keys,dropna=False)['status'].agg(
        planned='size',completed=lambda v:int((v=='complete').sum()),failed=lambda v:int((v!='complete').sum())).reset_index()
    selected=frame[(frame.status=='complete')&frame[value].notna()]
    campaigns=selected.groupby(['campaign']+keys,dropna=False)[value].agg(['count','mean','median','min','max']).reset_index()
    across=campaigns.groupby(keys,dropna=False)['mean'].agg(['count','mean','min','max']).reset_index()
    return {'outcome_counts':json.loads(counts.to_json(orient='records')),
            'per_campaign':json.loads(campaigns.to_json(orient='records',double_precision=15)),
            'across_campaign_means':json.loads(across.to_json(orient='records',double_precision=15))}


def paired(frame,kind,factor,numerator,denominator,keys,value='throughput_mps',difference=False):
    frame=frame.copy()
    if value not in frame:frame[value]=np.nan
    selected=frame[(frame.kind==kind)&frame[factor].isin([numerator,denominator])]
    output=[]
    for identity,group in selected.groupby(['campaign']+keys,dropna=False):
        if not isinstance(identity,tuple):identity=(identity,)
        positive=group[group[factor]==numerator].set_index('block')
        negative=group[group[factor]==denominator].set_index('block')
        assert positive.index.is_unique and negative.index.is_unique
        planned=sorted(set(positive.index)|set(negative.index))
        pairs=[]
        for block in planned:
            a=positive.loc[block] if block in positive.index else None
            b=negative.loc[block] if block in negative.index else None
            complete=a is not None and b is not None and a.status==b.status=='complete' and pd.notna(a[value]) and pd.notna(b[value])
            pairs.append({'block':int(block),'numerator_trial':None if a is None else a.id,
                          'denominator_trial':None if b is None else b.id,'complete':bool(complete),
                          'numerator':float(a[value]) if complete else None,'denominator':float(b[value]) if complete else None})
        good=[p for p in pairs if p['complete']]
        a=float(np.mean([p['numerator'] for p in good])) if good else None
        b=float(np.mean([p['denominator'] for p in good])) if good else None
        estimate=(a-b if difference else a/b) if good else None
        identity=tuple(v.item() if isinstance(v,np.generic) else v for v in identity)
        output.append({**dict(zip(['campaign']+keys,identity)),'planned_pairs':len(pairs),
                       'complete_pairs':len(good),'unavailable_pairs':len(pairs)-len(good),
                       'estimate':estimate,'pairs':pairs})
    return {'kind':kind,'factor':factor,'numerator':numerator,'denominator':denominator,'metric':value,
            'estimand':'difference of paired condition means' if difference else 'ratio of paired condition means',
            'per_campaign':output}


def contrasts(frame):
    result={}
    pub=['engine','version','publishers']
    for profile in ('periodic','always'):
        result[profile+'_memory']=paired(frame,'publication','profile',profile,'memory',pub)
    result['publishers_16_1']=paired(frame,'publication','publishers',16,1,['engine','version','profile'])
    for engine,old,current in (('redis','7.4.2','8.10.2'),('nats','2.10.24','2.15.0')):
        result[engine+'_current_historical']=paired(frame[frame.engine==engine],'publication','version',current,old,['engine','profile','publishers'])
    result['consumers_16_1']=paired(frame,'drain','consumers',16,1,['engine','version','profile','cpus'])
    result['driver_cpus_4_2']=paired(frame,'drain','cpus',4,2,['engine','version','profile','consumers'])
    recovery=frame[(frame.kind=='recovery')&(frame.recovery!='none')]
    for value in ('receipt_excess_ms','reference_to_redelivery_ms'):
        if len(recovery):result['kill_live_'+value]=paired(recovery,'recovery','kill',True,False,['engine','version','recovery','delta_ms','age'],value,True)
    result['trace_untraced']=paired(frame,'trace','trace',True,False,['engine','version','profile','publishers'])
    result['compression_off_inherited']=paired(frame,'compression','compression','off','inherited',['engine','version','profile','payload'])
    result['random_compressible']=paired(frame,'compression','payload','random','compressible',['engine','version','profile','compression'])
    return result


def verify_environment(folder,identity,plan):
    desired=json.loads((folder/'resources.json').read_text())
    pins=json.loads((folder/'inputs/bench/followup/image-pins.json').read_text())
    pods={p['metadata']['name']:p for p in json.loads((folder/'pods.json').read_text())['items']}
    trace_tools={};initializers=[]
    for resource in desired['items']:
        if resource['kind']!='Pod':continue
        name=resource['metadata']['name'];actual=pods[name]
        assert actual['metadata']['namespace']==identity['namespace']
        specification=resource['spec']['containers'][0]
        observed=actual['spec']['containers'][0]
        assert observed['image']==specification['image'] and '@sha256:' in observed['image']
        assert observed['resources']['limits']==specification['resources']['limits']
        assert actual['spec']['nodeName']==resource['spec']['nodeSelector']['kubernetes.io/hostname']
        status=actual['status']['containerStatuses'][0]
        assert status['imageID'].split('@sha256:')[-1]==observed['image'].split('@sha256:')[-1]
        assert status['restartCount']==0
        for initializer in resource['spec'].get('initContainers',[]):
            observed_init=next(c for c in actual['spec']['initContainers'] if c['name']==initializer['name'])
            init_status=next(c for c in actual['status']['initContainerStatuses'] if c['name']==initializer['name'])
            assert observed_init['image']==initializer['image'] and '@sha256:' in initializer['image']
            assert init_status['imageID'].split('@sha256:')[-1]==initializer['image'].split('@sha256:')[-1]
            assert init_status['state']['terminated']['exitCode']==0
            initializers.append({'pod':name,'name':initializer['name'],'restart_count_before_measurement':init_status['restartCount'],
                                 'completed':init_status['state']['terminated']})
        if not name.startswith('runner'):
            version=next(tag.partition(':')[2].removesuffix('-alpine') for tag,image in pins.items() if image==observed['image'])
            receipt=json.loads((folder/(name+'-version.json')).read_text())
            assert version in receipt['stdout']+receipt['stderr']
            if any(t['host']==name and t['trace'] for t in plan):
                environment=(folder/(name+'-environment.txt')).read_text()
                tracer=re.search(r'^strace -- version (\S+)',environment,re.M)
                checksum=re.search(r'^([0-9a-f]{64})\s+/tools/strace$',environment,re.M)
                assert tracer and checksum,'Missing tracer version or binary identity'
                trace_tools[name]={'version':tracer[1],'binary_sha256':checksum[1]}
    if not identity['pilot']:
        assert (folder/'inputs/bench/followup/run.py').read_bytes()==(ROOT/'bench/followup/run.py').read_bytes()
        final=json.loads((folder/'final-pods.json').read_text())
        assert {p['metadata']['name'] for p in final['items']}==set(pods)
        assert all(p['status']['containerStatuses'][0]['restartCount']==0 for p in final['items'])
        for pod in final['items']:
            initial=pods[pod['metadata']['name']]
            assert pod['metadata']['uid']==initial['metadata']['uid'],'Pod was replaced during collection'
            before={c['name']:c['restartCount'] for c in initial['status'].get('initContainerStatuses',[])}
            after={c['name']:c['restartCount'] for c in pod['status'].get('initContainerStatuses',[])}
            assert before==after,'Initializer restarted after the measurement-ready snapshot'
        binary=json.loads((folder/'binary.json').read_text())
        distributed=json.loads((folder/'binary-distribution.json').read_text())
        assert set(distributed)==set(pods) and set(distributed.values())=={binary['sha256']}
    return {'trace_tools':trace_tools,'setup_initializers':initializers}


def verify_invocation(folder,trial):
    base=folder/'invocations'
    launch=json.loads((base/(trial['id']+'-started.json')).read_text())
    invoked=json.loads((base/(trial['id']+'.json')).read_text())
    result=json.loads((folder/'raw'/trial['id']/'result.json').read_text())
    assert launch['trial']==invoked['trial']==trial
    assert launch['started']==invoked['started'] and invoked['finished']>=invoked['started']
    assert (invoked['returncode']==0)==(result['status']=='complete')
    assert invoked['returncode'] in (0,2) and json.loads(invoked['stdout'])==result


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
        environment=verify_environment(folder,identity,plan)
        assert {p.parent.name for p in (folder/'raw').glob('*/result.json')}=={t['id'] for t in plan}
        for trial in plan:
            verify_invocation(folder,trial)
            records.append(verify_trial(folder/'raw'/trial['id'],trial))
        receipts.append({'campaign':name,'planned':len(plan),'raw_files':len(lock),'plan_sha256':digest(folder/'plan.json'),'raw_manifest_sha256':digest(folder/'RAW_SHA256.json'),**environment})
    output=ROOT/args.output;output.mkdir(parents=True,exist_ok=True)
    frame=pd.DataFrame(records);frame.to_csv(output/'trials.csv',index=False)
    result={'campaigns':receipts,'outcomes':dict(Counter(r['status'] for r in records)),
            'kinds':dict(Counter(r['kind'] for r in records)),'verified_event_records':sum(r.get('attempt_records',0) for r in records),
            'scope':'Separate deployments on shared hardware; ranges of campaign means, no asserted population interval coverage.'}
    result['analysis_sha256']=digest(Path(__file__).resolve())
    result['trials_csv_sha256']=digest(output/'trials.csv')
    result['failed_outcomes']=[r for r in records if r['status']!='complete']
    result['paired_contrasts']=contrasts(frame)
    keys=['engine','version','profile','publishers','consumers','cpus','payload','compression','trace']
    for kind in ('publication','drain','trace','compression'):
        part=frame[frame.kind==kind]
        if len(part):result[kind]=summary(part,keys,'throughput_mps')
    recovery=frame[(frame.kind=='recovery')&(frame.recovery!='none')]
    if len(recovery):result['recovery']=summary(recovery,['engine','version','recovery','delta_ms','age','kill'],'receipt_excess_ms')
    (output/'statistics.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:result[k] for k in ('outcomes','kinds','verified_event_records')},indent=2))


if __name__=='__main__':main()
