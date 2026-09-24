"""Recompute every reported statistic from retained homelab receipts and raw events."""
from __future__ import annotations
import csv
import gzip
import hashlib
import json
import math
import os
from collections import defaultdict
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", str(Path(__file__).resolve().parents[1] / "tmp/matplotlib"))
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from campaign_identity import verify_original_evidence
from robustness import diagnose

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw"
OUT = ROOT / "data/derived"
FIG = ROOT / "paper/figures"
PROFILES = [f"{e}-{m}" for e in ("redis", "nats") for m in ("memory", "periodic", "always")]
LABEL = {p: f"{'Redis' if p.startswith('redis') else 'JetStream'} / {p.split('-')[1]}" for p in PROFILES}
COLOR = {"memory": "#236493", "periodic": "#b77916", "always": "#9b3956"}
BOOT = np.random.default_rng(20260923).integers(0, 10, (10000, 10))

def load(series):
    return [json.loads(s) for s in (RAW / series / "summary.jsonl").read_text().splitlines()]

def bootstrap_indices(n):
    assert n >= 2, "At least two completed trials are required for these intervals"
    return BOOT if n == 10 else np.random.default_rng(20260923).integers(0,n,(10000,n))

def ci(v):
    a = np.asarray(v, dtype=float)
    ix = bootstrap_indices(len(a))
    lo, hi = np.quantile(a[ix].mean(axis=1), [.025, .975])
    return {"mean": float(a.mean()), "low": float(lo), "high": float(hi), "completed_trials":len(a)}

def ratio(a, b):
    a, b = np.asarray(a), np.asarray(b)
    assert len(a) == len(b)
    ix=bootstrap_indices(len(a))
    v = a[ix].mean(axis=1) / b[ix].mean(axis=1)
    lo, hi = np.quantile(v, [.025, .975])
    return {"ratio": float(a.mean()/b.mean()), "low": float(lo), "high": float(hi), "paired_trials":len(a)}

def paired_ratio(a, b, key):
    common=sorted({r['block'] for r in a}&{r['block'] for r in b})
    result=ratio(metric([r for r in a if r['block'] in common],key),metric([r for r in b if r['block'] in common],key))
    result['paired_blocks']=common
    return result

def metric(rows, key):
    parts = key.split(".")
    vals = []
    for row in sorted(rows, key=lambda r: r["block"]):
        for part in parts:
            row = row[part]
        vals.append(row)
    return vals

def aggregate(rows):
    keys = ["publish_mps", "publish_ms.p50", "publish_ms.p95", "publish_ms.p99"]
    if rows[0]["kind"] == "trial":
        keys += ["drain_mps", "cycle_ms.mean", "cycle_ms.p50", "cycle_ms.p95", "cycle_ms.p99", "ack_ms.p99", "drain_delivery_ms.p99"]
    return {key: ci(metric(rows, key)) for key in keys}

def nice(v, digits=1):
    return f"{v:,.{digits}f}"

def interval(d, scale=1, digits=1):
    return f"{nice(d['mean']/scale,digits)} [{nice(d['low']/scale,digits)}, {nice(d['high']/scale,digits)}]"

def verify_events(series, rows):
    messages, maximum_utilization = 0, 0.0
    minimum_utilization = 1.0
    throttled = []
    assert len({r['key'] for r in rows}) == len(rows)
    for row in rows:
        assert row["kind"] in ("trial", "durability"), row
        with gzip.open(RAW / series / (row["key"] + ".csv.gz"), "rt") as f:
            header = next(f).strip().split(",")
            a = np.loadtxt(f, delimiter=",", dtype=np.int64, ndmin=2)
        n = row["n"]
        assert len(a) == n and np.array_equal(np.sort(a[:,0]), np.arange(n)), row["key"]
        ix = {h: i for i,h in enumerate(header)}
        p = a[:,ix["publish_start_ns"]]
        q = a[:,ix["publish_ack_ns"]]
        assert np.all(q >= p)
        def assert_stats(values, reported):
            ordered=np.sort(values)
            expected={"mean":float(np.mean(values)),"max":float(np.max(values))}
            for quantile in (50,95,99):expected[f"p{quantile}"]=float(ordered[math.ceil(quantile*n/100)-1])
            for name,value in expected.items():assert math.isclose(value,reported[name],abs_tol=1e-7,rel_tol=1e-10),(row["key"],name,value,reported[name])
        pub = (q-p)/1e6
        assert_stats(pub,row["publish_ms"])
        start = row.get("publish_start_ns", row.get("start_ns"))
        end = row.get("publish_end_ns", row.get("end_ns"))
        assert math.isclose(n*1e9/(end-start),row["publish_mps"],rel_tol=1e-10)
        assert int(p.min())>=start and int(q.max())<=end
        if row["kind"]=="durability":assert int(q.max())==end
        assert row["stored"] == n and row["pending"] == 0
        if row["kind"] == "durability":
            assert row["publishers"] == 16 and row["target_seconds"] == 5
            worker_ids = a[:,ix["worker"]]
            assert np.all((worker_ids >= 0) & (worker_ids < 16))
            for worker in range(16):
                pairs = sorted(zip(p[worker_ids==worker], q[worker_ids==worker]))
                assert all(pairs[i][0] >= pairs[i-1][1] for i in range(1,len(pairs)))
        if row["kind"] == "trial":
            expected_n, expected_publishers = (16384,16) if series == "main" else (1024,1)
            assert n == expected_n and row["publishers"] == expected_publishers
            assert row["payload_bytes"] == 512
            assert row["consumers"] in ((1,2,4,8,16) if series == "main" else (1,))
            r = a[:,ix["request_start_ns"]]
            d = a[:,ix["delivery_ns"]]
            k = a[:,ix["consumer_ack_ns"]]
            w = a[:,ix["worker"]]
            assert np.all((w >= 0) & (w < row["consumers"]))
            assert np.all(r >= row["drain_start_ns"])
            assert np.all((d>=r)&(k>=d)&(r>=q))
            assert int(k.max()) == row["drain_end_ns"]
            assert row["duplicates"] == 0
            for worker in range(row["consumers"]):
                pairs = sorted(zip(r[w==worker], k[w==worker]))
                assert all(pairs[i][0]>=pairs[i-1][1] for i in range(1,len(pairs)))
                assert len(pairs)==row["worker_counts"][worker]
            cycle=(k-r)/1e6
            assert_stats(cycle,row["cycle_ms"])
            assert_stats((k-d)/1e6,row["ack_ms"])
            assert_stats((d-row["drain_start_ns"])/1e6,row["drain_delivery_ms"])
            assert_stats((d-p)/1e6,row["publish_to_delivery_ms"])
            elapsed=int(k.max())-row["drain_start_ns"]
            assert math.isclose(n*1e9/elapsed,row["drain_mps"],rel_tol=1e-10)
            util=int((k-r).sum())/(row["consumers"]*elapsed)
            assert util<=1+1e-12
            maximum_utilization=max(util,maximum_utilization)
            minimum_utilization=min(util,minimum_utilization)
        def cpu(s):
            return {p[0]:int(p[1]) for line in s.splitlines() if len(p:=line.split())==2}
        before,after=cpu(row["driver_cpu_before"]),cpu(row["driver_cpu_after"])
        throttled.append(after.get("throttled_usec",0)-before.get("throttled_usec",0))
        messages+=n
    return {"trials":len(rows),"messages":messages,"max_concurrency_bound_utilization":maximum_utilization,"min_concurrency_bound_utilization":minimum_utilization if series != "durability" else None,"driver_throttled_trials":sum(v>0 for v in throttled),"driver_throttled_usec_total":sum(throttled)}

def main():
    verify_original_evidence()
    OUT.mkdir(exist_ok=True);FIG.mkdir(exist_ok=True)
    main_all, dur_all, serial, recovery = (load(s) for s in ("main","durability","serial","recovery"))
    failure_file=RAW/"durability/failed-trials.jsonl"
    assert failure_file.is_file(), "Required failure ledger is missing; refusing to treat the diagnostic replay as a planned success"
    failed=[json.loads(s) for s in failure_file.read_text().splitlines()]
    outcome=json.loads((ROOT/"data/environment/outcome-manifest.json").read_text())
    fields=('key','profile','block','stage')
    assert sorted(tuple(r[k] for k in fields) for r in failed)==sorted(tuple(r[k] for k in fields) for r in outcome['durability_failures'])
    failed_keys={r['key'] for r in failed}
    replays=[r for r in dur_all if r['key'] in failed_keys]
    assert sorted(r['key'] for r in replays)==sorted(outcome['excluded_completed_replays'])
    dur=[r for r in dur_all if r['key'] not in failed_keys]
    errors=[r for r in main_all if r["kind"]=="error"]
    main=[r for r in main_all if r["kind"]=="trial"]
    assert len(main)==300 and len(dur)+len(failed)==60 and len(serial)==60 and len(recovery)==130
    assert len(failed_keys)==len(failed)
    assert {(r['profile'],r['block']) for r in dur+failed}=={(p,b) for p in PROFILES for b in range(10)}
    checks={s:verify_events(s,rows) for s,rows in (("main",main),("durability",dur),("serial",serial))}
    checks["main"]["excluded_setup_attempts"]=errors
    checks['durability'].update({'planned_trials':60,'failed_planned_trials':failed,'excluded_diagnostic_replays':replays})
    mg, dg, sg = defaultdict(list), defaultdict(list), defaultdict(list)
    for r in main:mg[(r["profile"],r["consumers"])].append(r)
    for r in dur:dg[r["profile"]].append(r)
    for r in serial:sg[r["profile"]].append(r)
    for rows in [*mg.values(),*sg.values()]:assert sorted(r["block"] for r in rows)==list(range(10))
    for p,rows in dg.items():
        missing={r['block'] for r in failed if r['profile']==p}
        assert sorted(r['block'] for r in rows)==[b for b in range(10) if b not in missing]
    ma={f"{p}:{c}":aggregate(rows) for (p,c),rows in mg.items()}
    da={p:aggregate(rows) for p,rows in dg.items()};sa={p:aggregate(rows) for p,rows in sg.items()}
    effects={}
    for p in PROFILES:effects[f"{p}:C16/C1"]=ratio(metric(mg[p,16],"drain_mps"),metric(mg[p,1],"drain_mps"))
    for e in ("redis","nats"):
        for m in ("periodic","always"):
            effects[f"{e}:{m}/memory:publish"]=paired_ratio(dg[f"{e}-{m}"],dg[f"{e}-memory"],"publish_mps")
    for mode in ("memory","periodic","always"):
        effects[f"redis/nats:{mode}:publish"]=paired_ratio(dg[f"redis-{mode}"],dg[f"nats-{mode}"],"publish_mps")
    rg=defaultdict(list)
    for r in recovery:
        assert r["kill_exit"]=="signal: killed" and r["stored"]==1
        assert r["kill_end_ns"]>=r["kill_start_ns"]>=r["delivery_ns"]
        if r["no_reclaim"]:assert r["censored"] and r["pending"]==1
        else:
            assert not r["censored"] and r["pending"]==0
            if r["profile"].startswith("nats"):assert r["nats_deliveries"]==2
            assert r["redelivery_ns"]>=r["kill_end_ns"]
            assert math.isclose((r["redelivery_ns"]-r["kill_start_ns"])/1e6,r["failure_to_redelivery_ms"],abs_tol=1e-8)
            assert math.isclose((r["redelivery_ns"]-r["delivery_ns"])/1e6,r["delivery_to_redelivery_ms"],abs_tol=1e-8)
            rg[(r["delta_ms"],r["age_fraction"],r["profile"],r["poll_ms"])].append(r)
    ra={}
    for key,rows in rg.items():
        assert len(rows)==10
        v=np.array([r["failure_to_redelivery_ms"] for r in rows]);x=np.array([r["delivery_to_redelivery_ms"]-r["delta_ms"] for r in rows])
        ra[str(key)]={"median_ms":float(np.median(v)),"min_ms":float(v.min()),"max_ms":float(v.max()),"excess_median_ms":float(np.median(x)),"excess_min_ms":float(x.min()),"excess_max_ms":float(x.max())}
    checks["recovery"]={"trials":len(recovery),"successful_recoveries":len(recovery)-10,"no_reclaim_censored":10,"max_kill_bracket_ms":max((r["kill_end_ns"]-r["kill_start_ns"])/1e6 for r in recovery)}
    diagnostic={p:{"blocks":[r['block'] for r in sorted(dg[p],key=lambda r:r['block'])],"publish_mps_by_block":metric(dg[p],"publish_mps"),"publish_p99_ms_by_block":metric(dg[p],"publish_ms.p99")} for p in PROFILES}
    diagnose(dur, main, serial, OUT)
    result={"checks":checks,"main":ma,"durability":da,"serial":sa,"effects":effects,"recovery":ra,"durability_run_diagnostic":diagnostic}
    (OUT/"statistics.json").write_text(json.dumps(result,indent=2)+"\n")
    # Machine-readable long form for spreadsheets and re-analysis.
    with (OUT/"aggregate.csv").open("w") as f:
        w=csv.writer(f);w.writerow(["series","condition","metric","estimate","ci_low","ci_high"])
        for s,data in (("main",ma),("durability",da),("serial",sa)):
            for condition,metrics in sorted(data.items()):
                for m,v in metrics.items():w.writerow([s,condition,m,v["mean"],v["low"],v["high"]])
    tables={}
    t=[r"\begin{tabular}{llrrr}",r"\toprule",r"System & Mode & $X_1$ (kmsg/s) & $X_{16}$ (kmsg/s) & $X_{16}/X_1$\\",r"\midrule"]
    for p in PROFILES:
        e,m=p.split("-");a=ma[f"{p}:1"]["drain_mps"];b=ma[f"{p}:16"]["drain_mps"];q=effects[f"{p}:C16/C1"]
        t.append(f"{'Redis' if e=='redis' else 'JetStream'} & {m} & {interval(a,1000,2)} & {interval(b,1000,2)} & {q['ratio']:.2f} [{q['low']:.2f}, {q['high']:.2f}]\\\\")
    t += [r"\bottomrule",r"\end{tabular}"];tables["concurrency-table.tex"]="\n".join(t)
    t=[r"\begin{tabular}{llrrrr}",r"\toprule",r"System & Mode & $n$ & Throughput (kmsg/s) & p50 (ms) & p99 (ms)\\",r"\midrule"]
    for p in PROFILES:
        e,m=p.split("-");a=da[p]
        t.append(f"{'Redis' if e=='redis' else 'JetStream'} & {m} & {len(dg[p])} & {interval(a['publish_mps'],1000,2)} & {a['publish_ms.p50']['mean']:.3f} & {interval(a['publish_ms.p99'],1,3)}\\\\")
    t += [r"\bottomrule",r"\end{tabular}"];tables["durability-table.tex"]="\n".join(t)
    t=[r"\begin{tabular}{rrlrrr}",r"\toprule",r"$\Delta$ & $\alpha$ & System / sleep & $\Delta(1-\alpha)$ & Median & Range\\",r" & & & (ms) & (ms) & (ms)\\",r"\midrule"]
    for key in sorted(rg):
        delta,age,p,poll=key;v=ra[str(key)];label="JetStream" if p.startswith("nats") else f"Redis / {poll:g} ms"
        t.append(f"{delta:g} & {age:g} & {label} & {delta*(1-age):.1f} & {v['median_ms']:.1f} & [{v['min_ms']:.1f}, {v['max_ms']:.1f}]\\\\")
    t += [r"\bottomrule",r"\end{tabular}"];tables["recovery-table.tex"]="\n".join(t)
    t=[r"\begin{longtable}{llrrrr}",r"\toprule",r"System & Mode & $C$ & Throughput (kmsg/s) & Cycle p99 (ms) & Drain p99 (ms)\\",r"\midrule\endhead"]
    for p in PROFILES:
        for c in (1,2,4,8,16):
            a=ma[f"{p}:{c}"];e,m=p.split("-")
            t.append(f"{'Redis' if e=='redis' else 'JetStream'} & {m} & {c} & {interval(a['drain_mps'],1000,2)} & {a['cycle_ms.p99']['mean']:.3f} & {a['drain_delivery_ms.p99']['mean']:.1f}\\\\")
    t += [r"\bottomrule",r"\end{longtable}"];tables["full-matrix.tex"]="\n".join(t)
    t=[r"\begin{tabular}{llrr}",r"\toprule",r"System & Mode & Throughput (msg/s) & Publish p99 (ms)\\",r"\midrule"]
    for p in PROFILES:
        a=sa[p];e,m=p.split("-")
        t.append(f"{'Redis' if e=='redis' else 'JetStream'} & {m} & {interval(a['publish_mps'])} & {interval(a['publish_ms.p99'],1,3)}\\\\")
    t += [r"\bottomrule",r"\end{tabular}"];tables["serial-table.tex"]="\n".join(t)
    for file,body in tables.items():(OUT/file).write_text(body+"\n")
    # Print-ready vector figures.
    plt.rcParams.update({"font.family":"serif","font.size":10,"axes.spines.top":False,"axes.spines.right":False,"axes.grid":True,"grid.alpha":.2,"pdf.fonttype":42,"ps.fonttype":42})
    fig,axes=plt.subplots(1,2,figsize=(7.2,3.2))
    cs=np.array([1,2,4,8,16])
    for p in PROFILES:
        e,m=p.split("-");style="-" if e=="redis" else "--";mark="o" if e=="redis" else "s"
        for ax,metric_name,scale in ((axes[0],"drain_mps",1000),(axes[1],"cycle_ms.p99",1)):
            values=[ma[f"{p}:{c}"][metric_name] for c in cs];y=np.array([v["mean"] for v in values])/scale;lo=np.array([v["low"] for v in values])/scale;hi=np.array([v["high"] for v in values])/scale
            ax.plot(cs,y,linestyle=style,marker=mark,color=COLOR[m],label=LABEL[p],markersize=3);ax.fill_between(cs,lo,hi,color=COLOR[m],alpha=.10)
            ax.set_xscale("log",base=2);ax.set_xticks(cs,labels=[str(c) for c in cs]);ax.set_xlabel("Concurrent consumers")
    axes[0].set_ylabel("Acknowledged throughput (kmsg/s)");axes[1].set_ylabel("Mean within-run cycle p99 (ms)");axes[1].set_yscale("log")
    handles,labels=axes[0].get_legend_handles_labels();fig.legend(handles,labels,loc="lower center",ncol=3,fontsize=8,frameon=False,bbox_to_anchor=(.5,-.08));fig.tight_layout();fig.savefig(FIG/"concurrency.pdf",bbox_inches="tight",metadata={"CreationDate":None,"ModDate":None});plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(7.2,3.1))
    for i,p in enumerate(PROFILES):
        m=p.split("-")[1]
        for ax,k in ((axes[0],"publish_mps"),(axes[1],"publish_ms.p99")):
            v=da[p][k];scale=1000 if k=="publish_mps" else 1
            ax.bar(i,v["mean"]/scale,color=COLOR[m],alpha=1 if p.startswith("redis") else .55)
            ax.errorbar(i,v["mean"]/scale,yerr=[[max(0,v["mean"]-v["low"])/scale],[max(0,v["high"]-v["mean"])/scale]],color="black",capsize=2,linewidth=.8)
    for ax in axes:ax.set_xticks(range(6),labels=["R-M","R-P","R-S","J-M","J-P","J-S"]);ax.set_yscale("log")
    axes[0].set_ylabel("Confirmed appends (kmsg/s)");axes[1].set_ylabel("Mean within-run publish p99 (ms)");fig.tight_layout();fig.savefig(FIG/"durability.pdf",bbox_inches="tight",metadata={"CreationDate":None,"ModDate":None});plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(7.2,3.2));rng=np.random.default_rng(20260923)
    for ax,delta in zip(axes,(250,1000)):
        for i,(p,poll,label,col) in enumerate((("redis-periodic",10,"Redis: 10 ms","#236493"),("redis-periodic",100,"Redis: 100 ms","#b77916"),("nats-periodic",0,"JetStream","#9b3956"))):
            for j,age in enumerate((.1,.75)):
                x=j+(i-1)*.18;vals=[r["failure_to_redelivery_ms"] for r in rg[delta,age,p,poll]]
                ax.scatter(x+rng.uniform(-.035,.035,len(vals)),vals,color=col,s=16,alpha=.55,label=label if j==0 else None);ax.plot([x-.06,x+.06],[np.median(vals)]*2,color=col,lw=2)
        for j,age in enumerate((.1,.75)):ax.plot([j-.32,j+.32],[delta*(1-age)]*2,color="black",ls=":",lw=1)
        ax.set_title(f"Configured timeout: {delta} ms");ax.set_xticks([0,1],labels=["Kill at 10% age","Kill at 75% age"]);ax.set_ylabel("Failure-to-redelivery (ms)")
    h,l=axes[0].get_legend_handles_labels();fig.legend(h,l,loc="lower center",ncol=3,frameon=False,bbox_to_anchor=(.5,-.05),fontsize=9);fig.tight_layout();fig.savefig(FIG/"recovery.pdf",bbox_inches="tight",metadata={"CreationDate":None,"ModDate":None});plt.close(fig)
    # Descriptive run-order diagnostic; one observed trial per treatment/block.
    fig,axes=plt.subplots(1,2,figsize=(7.2,3.1),sharey=True)
    for ax,engine,title in zip(axes,("redis","nats"),("Redis Streams","NATS JetStream")):
        for mode in ("memory","periodic","always"):
            d=diagnostic[f"{engine}-{mode}"]
            by_block=dict(zip(d['blocks'],d['publish_mps_by_block']))
            y=np.array([by_block.get(b,float('nan')) for b in range(10)])/1000
            ax.plot(range(1,11),y,marker="o",markersize=3,color=COLOR[mode],label=mode)
            for b in sorted(set(range(10))-set(by_block)):
                ax.text(b+1,.025,"timeout",transform=ax.get_xaxis_transform(),color=COLOR[mode],ha="center",fontsize=7)
        ax.set_title(title);ax.set_xlabel("Randomized block");ax.set_yscale("log");ax.set_xticks(range(1,11))
    axes[0].set_ylabel("Confirmed appends (kmsg/s)")
    h,l=axes[0].get_legend_handles_labels();fig.legend(h,l,loc="lower center",ncol=3,frameon=False,bbox_to_anchor=(.5,-.04),fontsize=9)
    fig.tight_layout();fig.savefig(FIG/"durability-blocks.pdf",bbox_inches="tight",metadata={"CreationDate":None,"ModDate":None});plt.close(fig)
    # Stable macros separate data from prose.
    macros={"MainMessages":f"{checks['main']['messages']:,}","TimedMessages":f"{checks['durability']['messages']:,}","SerialMessages":f"{checks['serial']['messages']:,}","KillBracket":f"{checks['recovery']['max_kill_bracket_ms']:.3f}"}
    for e,short in (("redis","Redis"),("nats","Nats")):
        for mode,mshort in (("memory","Memory"),("periodic","Periodic"),("always","Always")):
            p=f"{e}-{mode}";q=effects[f"{p}:C16/C1"]
            macros[short+mshort+"Speedup"]=f"{q['ratio']:.2f}"
            macros[short+mshort+"PubRate"]=f"{da[p]['publish_mps']['mean']/1000:.2f}"
            macros[short+mshort+"PubPnn"]=f"{da[p]['publish_ms.p99']['mean']:.2f}"
        q=effects[f"{e}:always/memory:publish"];macros[short+"SyncSlowdown"]=f"{1/q['ratio']:.1f}"
    (OUT/"values.tex").write_text("\n".join("\\newcommand{\\"+k+"}{"+v+"}" for k,v in macros.items())+"\n")
    print(json.dumps({"checks":checks,"effects":effects},indent=2))

if __name__ == "__main__":main()
