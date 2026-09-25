"""Post-observation diagnostics. No observations are removed from primary results."""
import csv
import json
from pathlib import Path
import numpy as np


def mean(rows,key):
    parts=key.split('.')
    values=[]
    for row in rows:
        value=row
        for part in parts:value=value[part]
        values.append(value)
    return float(np.mean(values))


def spearman(x,y):
    def ranks(values):
        values=np.asarray(values)
        order=np.argsort(values,kind='stable');result=np.empty(len(values),float)
        i=0
        while i<len(values):
            j=i+1
            while j<len(values) and values[order[j]]==values[order[i]]:j+=1
            result[order[i:j]]=(i+j-1)/2+1
            i=j
        return result
    a,b=ranks(x),ranks(y)
    if np.std(a)==0 or np.std(b)==0:return None
    return float(np.corrcoef(a,b)[0,1])


def diagnose(durability,main,serial,out):
    out=Path(out)
    profiles=sorted({r['profile'] for r in durability})
    output={'role':'Post-observation descriptive sensitivity; not additional independent trials or corrected inference',
            'omissions':'Leave-one-out values are influence diagnostics only; primary data remain intact',
            'conditions':{},'paired_effects':{},'execution_segments':[],
            'publication_tail_samples':[], 'publication_tail_sample_ranges':{}}
    for row in sorted(durability,key=lambda r:r['key']):
        n=row['n']
        rank=(99*n+99)//100
        output['publication_tail_samples'].append({
            'key':row['key'],'profile':row['profile'],'block_zero_based':row['block'],
            'message_count':n,'p99_rank_one_based':rank,
            'order_positions_above_p99':n-rank,'p99_ms':row['publish_ms']['p99']})
    fields=list(output['publication_tail_samples'][0])
    with (out/'publication-tail-samples.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=fields)
        writer.writeheader();writer.writerows(output['publication_tail_samples'])
    table=[]
    for profile in profiles:
        rows=sorted([r for r in durability if r['profile']==profile],key=lambda r:r['block'])
        condition={}
        for key in ('publish_mps','publish_ms.p99'):
            values=[mean([r],key) for r in rows]
            omitted=[{'omitted_key':r['key'],'omitted_block':r['block'],
                      'mean':mean([x for x in rows if x is not r],key)} for r in rows]
            early=[r for r in rows if r['block']<5];late=[r for r in rows if r['block']>=5]
            condition[key]={'n':len(rows),'mean':mean(rows,key),'median':float(np.median(values)),
                'range':[min(values),max(values)],'leave_one_out':omitted,
                'leave_one_out_mean_range':[min(x['mean'] for x in omitted),max(x['mean'] for x in omitted)],
                'early_mean':mean(early,key),'late_mean':mean(late,key),
                'early_n':len(early),'late_n':len(late),
                'spearman_block':spearman([r['block'] for r in rows],values)}
        output['conditions'][profile]=condition
        samples=[r for r in output['publication_tail_samples'] if r['profile']==profile]
        output['publication_tail_sample_ranges'][profile]={
            'completed_trials':len(samples),
            'message_count_range':[min(r['message_count'] for r in samples),max(r['message_count'] for r in samples)],
            'order_positions_above_p99_range':[min(r['order_positions_above_p99'] for r in samples),max(r['order_positions_above_p99'] for r in samples)]}
        p99=condition['publish_ms.p99'];rate=condition['publish_mps']
        table.append([profile,len(rows),p99['mean'],p99['median'],*p99['leave_one_out_mean_range'],rate['early_mean'],rate['late_mean']])
    pairs=[]
    for profile in profiles:
        pairs.append((f'{profile}:C16/C1',[r for r in main if r['profile']==profile and r['consumers']==16],
                      [r for r in main if r['profile']==profile and r['consumers']==1],'drain_mps'))
    for engine in ('redis','nats'):
        for mode in ('periodic','always'):
            pairs.append((f'{engine}:{mode}/memory:publish',[r for r in durability if r['profile']==f'{engine}-{mode}'],
                          [r for r in durability if r['profile']==f'{engine}-memory'],'publish_mps'))
    for mode in ('memory','periodic','always'):
        pairs.append((f'redis/nats:{mode}:publish',[r for r in durability if r['profile']==f'redis-{mode}'],
                      [r for r in durability if r['profile']==f'nats-{mode}'],'publish_mps'))
    for name,a,b,key in pairs:
        common=sorted({r['block'] for r in a}&{r['block'] for r in b})
        def ratio_for(blocks):
            aa=[r for r in a if r['block'] in blocks];bb=[r for r in b if r['block'] in blocks]
            return mean(aa,key)/mean(bb,key) if aa and bb else None
        omitted=[{'omitted_block':block,'ratio':ratio_for([x for x in common if x!=block])} for block in common]
        output['paired_effects'][name]={'paired_blocks':common,'ratio':ratio_for(common),'leave_one_block_out':omitted,
            'leave_one_block_out_range':[min(x['ratio'] for x in omitted),max(x['ratio'] for x in omitted)],
            'early_ratio':ratio_for([x for x in common if x<5]),'late_ratio':ratio_for([x for x in common if x>=5])}
    # Boundaries derive from retained interruption records, not outcome values.
    for low,high in ((1,21),(22,30),(31,37),(38,42),(43,60)):
        segment={'planned_keys':f'D{low:03d}-D{high:03d}','profiles':{}}
        for profile in profiles:
            rows=[r for r in durability if r['profile']==profile and low<=int(r['key'][1:])<=high]
            if rows:segment['profiles'][profile]={'n':len(rows),'keys':[r['key'] for r in rows],
                'publish_mps':mean(rows,'publish_mps'),'mean_trial_p99_ms':mean(rows,'publish_ms.p99')}
        output['execution_segments'].append(segment)
    (out/'robustness.json').write_text(json.dumps(output,indent=2)+'\n')
    with (out/'robustness.csv').open('w') as f:
        w=csv.writer(f);w.writerow(['profile','n','p99_mean_ms','p99_median_ms','loo_min_ms','loo_max_ms','early_mps','late_mps']);w.writerows(table)
    tex=[r'\begin{tabular}{llrrrr}',r'\toprule',
         r'System & Mode & Mean p99 & Median p99 & LOO means & Early / late rate\\',
         r' & & (ms) & (ms) & (ms) & (kmsg/s)\\',r'\midrule']
    for profile,n,avg,median,lo,hi,early,late in sorted(table,key=lambda r: (r[0].startswith('nats'),{'memory':0,'periodic':1,'always':2}[r[0].split('-')[1]])):
        engine,mode=profile.split('-')
        tex.append(f"{'Redis' if engine=='redis' else 'JetStream'} & {mode} & {avg:.2f} & {median:.2f} & [{lo:.2f}, {hi:.2f}] & {early/1000:.2f} / {late/1000:.2f}\\\\")
    tex.extend([r'\bottomrule',r'\end{tabular}'])
    (out/'robustness-table.tex').write_text('\n'.join(tex)+'\n')
    tail_tex=[r'\begin{tabular}{llrrr}',r'\toprule',
              r'System & Mode & Trials & Messages per trial & Positions above p99\\',r'\midrule']
    for profile in sorted(profiles,key=lambda p:(p.startswith('nats'),{'memory':0,'periodic':1,'always':2}[p.split('-')[1]])):
        engine,mode=profile.split('-');r=output['publication_tail_sample_ranges'][profile]
        a,b=r['message_count_range'];c,d=r['order_positions_above_p99_range']
        tail_tex.append(f"{'Redis' if engine=='redis' else 'JetStream'} & {mode} & {r['completed_trials']} & {a:,}--{b:,} & {c:,}--{d:,}\\\\")
    tail_tex.extend([r'\bottomrule',r'\end{tabular}'])
    (out/'publication-tail-counts.tex').write_text('\n'.join(tail_tex)+'\n')
    macros={}
    for prefix,profile in [('Redis','redis-always'),('Nats','nats-always')]:
        p99=output['conditions'][profile]['publish_ms.p99']
        for label,value in [('Mean',p99['mean']),('Median',p99['median']),('LooMin',p99['leave_one_out_mean_range'][0]),('LooMax',p99['leave_one_out_mean_range'][1])]:
            macros[prefix+'AlwaysPnn'+label]=f'{value:.1f}'
    (out/'robustness-values.tex').write_text('\n'.join('\\newcommand{\\'+k+'}{'+v+'}' for k,v in macros.items())+'\n')
    return output
