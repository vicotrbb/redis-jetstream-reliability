"""Bind the revised article's displayed numbers to the verified follow-up report."""
import csv
import json
from statistics import fmean
from check_followup import ROOT, digest, parsed


def main():
    folder = ROOT/'followup/derived'
    stats = json.loads((folder/'statistics.json').read_text())
    report = json.loads((folder/'report.json').read_text())
    with (folder/'trials.csv').open(newline='') as stream:
        rows = [{k: parsed(v) for k,v in row.items()} for row in csv.DictReader(stream)]
    sources = ['paper/'+name+'.tex' for name in ('abstract','main','results','followup-results','conclusion','appendix-followup')]
    text = '\n'.join((ROOT/name).read_text() for name in sources)
    checks = []

    def displayed(label, value, digits, written):
        assert f'{value:.{digits}f}' == written, (label,value,written)
        assert written in text, (label,'number absent from manuscript')
        checks.append({'claim':label,'unrounded':value,'displayed':written})

    def select(kind, **conditions):
        return next(r for r in report[kind] if all(r[k] == v for k,v in conditions.items()))

    def paired(name, **conditions):
        return [r for r in stats['paired_contrasts'][name]['per_campaign']
                if all(r[k] == v for k,v in conditions.items())]

    for label,value,written in (
            ('planned outcomes',len(rows),'612'),('complete procedures',stats['outcomes']['complete'],'601'),
            ('timed records',stats['verified_event_records'],'80263171'),
            ('complete timed workloads',sum(r['status']=='complete' and r['kind']!='recovery' for r in rows),'349')):
        displayed(label,value,0,written)
    failures = [r for r in rows if r['status']=='failed']
    assert len(failures)==11 and sum(r['stage']=='warmup' for r in failures)==4
    assert sum(r['stage']=='measurement' for r in failures)==7
    displayed('confirmed failed prefixes',sum(r['confirmed_records'] or 0 for r in failures),0,'14651')
    displayed('unknown failed requests',sum(r['unknown_records'] or 0 for r in failures),0,'22')

    for policy,minimum,maximum in [('autoclaim','0.98','10.70'),('jetstream','1.62','9.80'),('claim','20.52','87.83')]:
        values = [v for r in report['recovery'] if r['recovery']==policy
                  for state in ('live_excess_ms','killed_excess_ms') for v in r[state]['campaign_means'].values()]
        displayed(policy+' minimum campaign-cell excess',min(values),2,minimum)
        displayed(policy+' maximum campaign-cell excess',max(values),2,maximum)
    differences = [c['estimate'] for c in paired('kill_live_receipt_excess_ms',recovery='claim')]
    displayed('CLAIM minimum killed-live difference',min(differences),2,'-26.91')
    displayed('CLAIM maximum killed-live difference',max(differences),2,'14.64')
    controls = [r for r in rows if r['kind']=='recovery' and r['recovery']=='none']
    assert len(controls)==12 and all(r['status']=='complete' for r in controls)
    displayed('minimum control observation',min(r['observation_seconds'] for r in controls),3,'0.503')
    displayed('maximum control observation',max(r['observation_seconds'] for r in controls),3,'0.699')
    active = [r for r in rows if r['kind']=='recovery' and r['recovery']!='none']
    assert len(active)==240 and all(r['status']=='complete' for r in active)
    assert sum(r['kill'] for r in active)==120

    gains = [r['estimate'] for r in paired('consumers_16_1')]
    displayed('minimum consumer gain',min(gains),2,'10.43')
    displayed('maximum consumer gain',max(gains),2,'14.49')
    drains = [r for r in rows if r['kind']=='drain']
    assert len(drains)==96 and all(r['status']=='complete' for r in drains)
    assert all(r['driver_throttled_periods']==r['broker_throttled_periods']==0 for r in drains)
    assert all(r['c16_p99_ms']['mean']>r['c1_p99_ms']['mean'] for r in report['drain'])
    durations = [r['sample_count']/r['throughput_mps'] for r in drains]
    displayed('minimum drain seconds',min(durations),2,'1.77')
    displayed('maximum drain seconds',max(durations),2,'30.11')
    for engine,profile,written in [('redis','memory','1.031'),('redis','periodic','1.026'),('nats','memory','1.107'),('nats','periodic','1.102')]:
        displayed(f'{engine} {profile} driver gain',fmean(r['estimate'] for r in paired('driver_cpus_4_2',engine=engine,profile=profile,consumers=16)),3,written)

    for engine,version,rates,tails,ratio,bounds,gain,gainbounds,pairs in (
        ('redis','8.10.2',['73.26','60.49','4.35'],['0.470','0.563','16.98'],'0.8257',['0.8082','0.8397'],'9.41',['6.06','13.67'],6),
        ('nats','2.15.0',['60.62','49.75','0.565'],['0.639','0.796','295.64'],'0.8207',['0.8091','0.8296'],'1.55',['0.73','2.46'],7)):
        for i,profile in enumerate(('memory','periodic','always')):
            cell = select('publication',engine=engine,version=version,profile=profile,publishers=16)
            displayed(f'{engine} {profile} kmsg/s',cell['throughput_mps']['mean']/1000,len(rates[i].split('.')[1]),rates[i])
            displayed(f'{engine} {profile} mean trial p99',cell['mean_trial_p99_ms']['mean'],len(tails[i].split('.')[1]),tails[i])
        values = [r['estimate'] for r in paired('periodic_memory',engine=engine,version=version,publishers=16)]
        for label,value,written in [('mean',fmean(values),ratio),('minimum',min(values),bounds[0]),('maximum',max(values),bounds[1])]:
            displayed(engine+' periodic/memory '+label,value,4,written)
        cells = paired('publishers_16_1',engine=engine,version=version,profile='always')
        assert sum(r['complete_pairs'] for r in cells)==pairs
        values = [r['estimate'] for r in cells]
        for label,value,written in [('mean',fmean(values),gain),('minimum',min(values),gainbounds[0]),('maximum',max(values),gainbounds[1])]:
            displayed(engine+' publishers 16/1 '+label,value,2,written)
    tail = next(r for r in rows if r['campaign']=='main03' and r['id']=='F0039')
    assert tail['sample_count']==976 and tail['positions_above_p99']==9
    displayed('retained F0039 p99',tail['p99_ms'],1,'1968.6')
    for engine,publishers,written in [('redis',1,'0.943'),('redis',16,'0.815'),('nats',1,'0.920'),('nats',16,'0.934')]:
        cell = select('trace',engine=engine,publishers=publishers)
        displayed(f'{engine} P{publishers} traced/plain',cell['traced_untraced_ratio']['mean'],3,written)
        assert cell['sync_errors']['max']==0
    displayed('Redis P16 calls per confirmation',select('trace',engine='redis',publishers=16)['sync_calls_per_confirmed_message']['mean'],3,'0.120')
    for engine,payload,written in [('redis','compressible','1.036'),('redis','random','0.995'),('nats','compressible','1.021'),('nats','random','0.988')]:
        displayed(f'{engine} {payload} compression ratio',select('compression',engine=engine,payload=payload)['off_inherited_ratio']['mean'],3,written)
    values = [v for r in report['compression'] for v in r['off_inherited_ratio']['campaign_estimates'].values()]
    displayed('minimum compression ratio',min(values),3,'0.935')
    displayed('maximum compression ratio',max(values),3,'1.063')
    operational=json.loads((ROOT/'data/derived/operational-report.json').read_text())
    assert operational['profiles']['always']=={'planned':72,'completed':62,'failed':10,
        'warmup_failed':4,'timed_failed':6,'failed_percent':100*10/72}
    for profile,written in [('always','13.9'),('periodic','1.4')]:
        displayed(profile+' planned-attempt failure percentage',operational['profiles'][profile]['failed_percent'],1,written)
    waits=[v for r in operational['timed_timeouts'] for v in r['request_wait_seconds']]
    assert len(waits)==22 and len(operational['timed_timeouts'])==7
    displayed('minimum unknown request wait seconds',min(waits),3,'5.000')
    displayed('maximum unknown request wait seconds',max(waits),3,'5.002')
    maxima=operational['completed_max_at_least_1000_ms']
    assert len(maxima)==7 and all(r['profile']=='always' for r in maxima)
    above=[r['max_ms']/1000 for r in maxima if r['max_ms']>=2000]
    assert len(above)==4
    displayed('minimum completed maximum above two seconds',min(above),3,'2.297')
    displayed('maximum completed publication request seconds',max(above),3,'4.183')
    displayed('next completed request maximum seconds',max(r['max_ms']/1000 for r in maxima if r['max_ms']<2000),3,'1.969')
    versions=operational['versions']
    displayed('minimum version contrast mean',min(r['mean_ratio'] for r in versions),4,'0.9603')
    displayed('maximum version contrast mean',max(r['mean_ratio'] for r in versions),4,'1.0232')
    displayed('minimum deployment version contrast',min(r['min_ratio'] for r in versions),4,'0.9401')
    displayed('maximum deployment version contrast',max(r['max_ratio'] for r in versions),4,'1.1237')
    displayed('largest traced sync milliseconds',operational['largest_traced_sync_ms'],1,'544.6')
    displayed('Redis P16 confirmations per synchronization, reciprocal aggregate',
              1/select('trace',engine='redis',publishers=16)['sync_calls_per_confirmed_message']['mean'],1,'8.3')
    receipt = {'status':'pass','displayed_numbers':checks,'source_sha256':{n:digest(ROOT/n) for n in sources},
               'statistics_sha256':digest(folder/'statistics.json'),'report_sha256':digest(folder/'report.json'),
               'operational_report_sha256':digest(ROOT/'data/derived/operational-report.json'),
               'scope':'Displayed-number binding to the separately verified report; not external replication.'}
    (ROOT/'revisions/20260925-integrated/manuscript-number-check.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({'status':'pass','displayed_numbers_checked':len(checks)}))


if __name__=='__main__': main()
