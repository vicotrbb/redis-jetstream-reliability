"""Render descriptive follow-up tables and figures from verified observations."""
import argparse
import hashlib
import json
import os
from pathlib import Path

os.environ.setdefault('MPLCONFIGDIR', str(Path(__file__).resolve().parents[2]/'tmp/matplotlib'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
ENGINES = [('redis', '7.4.2'), ('redis', '8.10.2'), ('nats', '2.10.24'), ('nats', '2.15.0')]
POLICIES = [('redis', '7.4.2', 'autoclaim'), ('redis', '8.10.2', 'autoclaim'),
            ('redis', '8.10.2', 'claim'), ('nats', '2.10.24', 'jetstream'), ('nats', '2.15.0', 'jetstream')]
NAMES = {'redis': 'Redis', 'nats': 'JetStream'}
PROFILES = {'memory': 'M', 'periodic': 'P', 'always': 'S'}
COLORS = ['#176B87', '#B54B22']


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def select(frame, **conditions):
    result = frame
    for field, value in conditions.items():
        result = result[result[field] == value]
    return result


def measure(frame, value):
    """Equal weight for each campaign mean having at least one completed trial."""
    completed = frame[(frame.status == 'complete') & frame[value].notna()]
    means = completed.groupby('campaign')[value].mean()
    return {'planned': len(frame), 'completed': len(completed), 'campaigns': len(means),
            'campaign_means': {k: float(v) for k, v in means.items()},
            'mean': float(means.mean()) if len(means) else None,
            'min': float(means.min()) if len(means) else None,
            'max': float(means.max()) if len(means) else None}


def fmt(value, decimals=2, scale=1):
    return '--' if value is None or pd.isna(value) else f'{value/scale:.{decimals}f}'


def span(m, decimals=2, scale=1):
    if not m['campaigns']:
        return '--'
    return f"{fmt(m['mean'],decimals,scale)} [{fmt(m['min'],decimals,scale)}, {fmt(m['max'],decimals,scale)}]"


def tex_table(headers, rows, alignment=None, long=False):
    environment = 'longtable' if long else 'tabular'
    alignment = alignment or ('l' + 'r'*(len(headers)-1))
    header = ' & '.join(headers) + r'\\'
    lines = [r'\begin{' + environment + '}{' + alignment + '}', r'\toprule', header, r'\midrule']
    if long:
        lines += [r'\endfirsthead', r'\toprule', header, r'\midrule', r'\endhead']
    lines += [' & '.join(map(str, row)) + r'\\' for row in rows]
    lines += [r'\bottomrule', r'\end{' + environment + '}']
    return '\n'.join(lines) + '\n'


def contrast_summary(stats, name, **conditions):
    rows = stats['paired_contrasts'][name]['per_campaign']
    matched = [r for r in rows if all(r[k] == v for k, v in conditions.items())]
    values = [r['estimate'] for r in matched if r['estimate'] is not None]
    return {'campaigns': len(values), 'mean': float(np.mean(values)) if values else None,
            'min': min(values) if values else None, 'max': max(values) if values else None,
            'planned_pairs': sum(r['planned_pairs'] for r in matched),
            'complete_pairs': sum(r['complete_pairs'] for r in matched),
            'campaign_estimates': {r['campaign']: r['estimate'] for r in matched}}


def render(frame, stats, texdir, figdir):
    generated = []
    report = {'scope': 'Equal-weight campaign means and observed ranges; no confidence intervals.',
              'publication': [], 'drain': [], 'recovery': [], 'trace': [], 'compression': []}
    def write(name, headers, rows, **kwargs):
        path = texdir / ('followup-' + name + '.tex')
        path.write_text(tex_table(headers, rows, **kwargs)); generated.append(path)
    def figure(name, fig):
        path = figdir / ('followup-' + name + '.pdf')
        fig.savefig(path, bbox_inches='tight', metadata={'CreationDate': None, 'ModDate': None})
        plt.close(fig); generated.append(path)
    plt.rcParams.update({'font.family': 'serif', 'font.size': 9,
                         'axes.spines.top': False, 'axes.spines.right': False,
                         'axes.grid': True, 'grid.alpha': .2, 'pdf.fonttype': 42, 'ps.fonttype': 42})

    outcome_rows = []
    for kind in ('publication', 'drain', 'recovery', 'trace', 'compression'):
        part = select(frame, kind=kind)
        outcome_rows.append([kind.capitalize(), len(part), int((part.status == 'complete').sum()),
                             int((part.status != 'complete').sum())])
    write('outcomes', ['Family', 'Planned', 'Complete', 'Failed'], outcome_rows)
    failedrows = []
    for _, row in frame[frame.status != 'complete'].iterrows():
        failedrows.append([row.campaign.removeprefix('main')+'/'+row.id,
                           ('R' if row.engine == 'redis' else 'J')+row.version,
                           PROFILES[row.profile], row.publishers, row.stage,
                           fmt(row.confirmed_records, 0), fmt(row.unknown_records, 0),
                           fmt(row.seconds_until_workers_joined), fmt(row.retained_count_at_reconciliation, 0)])
    write('failures', ['Trial', 'System', 'Mode', '$P$', 'Stage', 'Conf.', 'Unknown', 'Join, s', 'Stored'], failedrows,
          alignment='llrrlrrrr', long=True)

    pub = select(frame, kind='publication')
    pubrows, fullpub = [], []
    fig, axes = plt.subplots(2, 2, figsize=(6.6, 4.2), sharey=True)
    for ax, (engine, version) in zip(axes.flat, ENGINES):
        for pi, profile in enumerate(PROFILES):
            for j, publishers in enumerate((1, 16)):
                sub = select(pub, engine=engine, version=version, profile=profile, publishers=publishers)
                rate = measure(sub, 'throughput_mps'); tail = measure(sub, 'p99_ms')
                complete = sub[sub.status == 'complete']
                entry = {'engine': engine, 'version': version, 'profile': profile, 'publishers': publishers,
                         'throughput_mps': rate, 'mean_trial_p99_ms': tail,
                         'sample_count_range': [int(complete.sample_count.min()), int(complete.sample_count.max())] if len(complete) else None,
                         'positions_above_p99_range': [int(complete.positions_above_p99.min()), int(complete.positions_above_p99.max())] if len(complete) else None}
                report['publication'].append(entry)
                pubrows.append([f'{NAMES[engine]} {version}', PROFILES[profile], publishers,
                                f"{rate['completed']}/{rate['planned']}", span(rate, 2, 1000), span(tail)])
                for campaign, cell in sub.groupby('campaign'):
                    r = measure(cell, 'throughput_mps'); p = measure(cell, 'p99_ms')
                    n = cell[cell.status == 'complete'].sample_count
                    fullpub.append([campaign.removeprefix('main'), f'{NAMES[engine]} {version}', PROFILES[profile], publishers,
                                    f"{r['completed']}/{r['planned']}", fmt(r['mean'], 2, 1000), fmt(p['mean']),
                                    '--' if not len(n) else f'{int(n.min())}--{int(n.max())}'])
                for ci, (campaign, value) in enumerate(rate['campaign_means'].items()):
                    ax.scatter(pi + (j-.5)*.27 + (ci-1)*.045, value/1000, color=COLORS[j],
                               marker=('o', 's')[j], s=22, alpha=.8,
                               label=f'{publishers} publisher' + ('s' if publishers > 1 else '') if pi == ci == 0 else None)
        ax.set(title=f'{NAMES[engine]} {version}', xticks=[0, 1, 2], xticklabels=['Memory', 'Periodic', 'Always'], yscale='log')
    for ax in axes[:, 0]: ax.set_ylabel('Confirmed rate (kmsg/s)')
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc='lower center', ncol=2, frameon=False, bbox_to_anchor=(.5, -.015))
    fig.tight_layout(rect=(0, .04, 1, 1)); figure('publication', fig)
    write('publication', ['System', 'Mode', '$P$', '$n$', 'Rate, kmsg/s', 'Trial p99, ms'], pubrows, alignment='llrrll', long=True)
    write('publication-campaigns', ['Run', 'System', 'Mode', '$P$', '$n$', 'kmsg/s', 'p99, ms', 'Count range'], fullpub, alignment='llrrrrrl', long=True)

    drainrows, fulldrain = [], []
    for engine, version in (ENGINES[1], ENGINES[3]):
        for profile in ('memory', 'periodic'):
            for cpus in (2, 4):
                condition = dict(engine=engine, version=version, profile=profile, cpus=cpus)
                low = select(frame, kind='drain', consumers=1, **condition)
                high = select(frame, kind='drain', consumers=16, **condition)
                rates = [measure(s, 'throughput_mps') for s in (low, high)]
                gain = contrast_summary(stats, 'consumers_16_1', **condition)
                cpu = {who: measure(high, who+'_mean_cores') for who in ('driver', 'broker')}
                entry = {**condition, 'c1_throughput_mps': rates[0], 'c16_throughput_mps': rates[1],
                         'paired_speedup': gain, 'c16_cpu': cpu,
                         'c1_p99_ms': measure(low, 'p99_ms'), 'c16_p99_ms': measure(high, 'p99_ms')}
                report['drain'].append(entry)
                drainrows.append([NAMES[engine], PROFILES[profile], cpus, fmt(rates[0]['mean'], 2, 1000),
                                  fmt(rates[1]['mean'], 2, 1000), span(gain), fmt(cpu['driver']['mean']), fmt(cpu['broker']['mean'])])
                for consumers, sub in ((1, low), (16, high)):
                    for campaign, cell in sub.groupby('campaign'):
                        r = measure(cell, 'throughput_mps'); p = measure(cell, 'p99_ms')
                        fulldrain.append([campaign.removeprefix('main'), NAMES[engine], PROFILES[profile], consumers, cpus,
                                          f"{r['completed']}/{r['planned']}", fmt(r['mean'], 2, 1000), fmt(p['mean']),
                                          fmt(measure(cell, 'driver_mean_cores')['mean']), fmt(measure(cell, 'broker_mean_cores')['mean'])])
    write('drain', ['System', 'Mode', 'CPU', '$X_1$', '$X_{16}$', '$X_{16}/X_1$', 'Driver', 'Broker'], drainrows, alignment='llrrrlrr')
    write('drain-campaigns', ['Run', 'System', 'Mode', '$C$', 'CPU', '$n$', 'kmsg/s', 'p99, ms', 'Driver', 'Broker'], fulldrain, long=True, alignment='llrrrrrrrr')

    recovery = select(frame, kind='recovery')
    # Policy strings are the exact names in the prospective plan.
    policies = POLICIES
    labels = ['R7 auto', 'R8 auto', 'R8 CLAIM', 'J2.10', 'J2.15']
    recoveryrows = []
    fig, axes = plt.subplots(2, 2, figsize=(6.6, 4.6), sharex=True)
    for di, delta in enumerate((250, 1000)):
        for ai, age in enumerate((.1, .75)):
            ax = axes[di, ai]
            for i, (engine, version, policy) in enumerate(policies):
                condition = dict(engine=engine, version=version, recovery=policy, delta_ms=delta, age=age)
                measures = []
                for j, killed in enumerate((False, True)):
                    cell = select(recovery, kill=killed, **condition)
                    m = measure(cell, 'receipt_excess_ms'); measures.append(m)
                    for ci, (campaign, group) in enumerate(cell.groupby('campaign')):
                        values = group.loc[group.status == 'complete', 'receipt_excess_ms'].to_numpy()
                        x = np.full(len(values), i+(j-.5)*.27+(ci-1)*.045)
                        ax.scatter(x, values, color=COLORS[j], marker=('o', 's')[j], s=15, alpha=.65,
                                   label=('Live, unacknowledging', 'Killed')[j] if i == ci == 0 else None)
                contrast = contrast_summary(stats, 'kill_live_receipt_excess_ms', **condition)
                report['recovery'].append({**condition, 'live_excess_ms': measures[0], 'killed_excess_ms': measures[1],
                                           'paired_kill_minus_live_ms': contrast})
                recoveryrows.append([labels[i], delta, int(age*100), span(measures[0]), span(measures[1]), span(contrast)])
            ax.axhline(0, color='black', linewidth=.7, linestyle=':')
            ax.set(title=f'Threshold {delta} ms; receipt age {int(age*100)}%', xticks=range(5), xticklabels=labels)
            ax.tick_params(axis='x', labelrotation=25)
    for ax in axes[:, 0]: ax.set_ylabel('Receipt-to-receipt excess (ms)')
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc='lower center', ncol=2, frameon=False, bbox_to_anchor=(.5, -.035))
    fig.tight_layout(); figure('recovery', fig)
    write('recovery', ['Policy', r'$\Delta$', r'Age, \%', 'Live excess, ms', 'Killed excess, ms', 'Killed $-$ live, ms'], recoveryrows, alignment='lrrlll', long=True)
    controlrows = []
    for _, row in select(recovery, recovery='none').iterrows():
        controlrows.append([row.campaign.removeprefix('main')+'/'+row.id, row.version, row.delta_ms,
                            row.status, fmt(row.observation_seconds, 3)])
    write('controls', ['Trial', 'Redis', r'$\Delta$, ms', 'Outcome', 'Observation, s'], controlrows, long=True)

    tracerows, compressionrows = [], []
    for engine, version in (ENGINES[1], ENGINES[3]):
        for publishers in (1, 16):
            condition = dict(engine=engine, version=version, profile='always', publishers=publishers)
            cell = select(frame, kind='trace', trace=True, **condition)
            gain = contrast_summary(stats, 'trace_untraced', **condition)
            entry = {**condition, 'traced_untraced_ratio': gain}
            for key in ('sync_complete_calls', 'sync_calls_per_confirmed_message', 'sync_p50_ms', 'sync_p99_ms', 'sync_sum_call_seconds', 'sync_errors'):
                entry[key] = measure(cell, key)
            report['trace'].append(entry)
            tracerows.append([NAMES[engine], publishers, span(entry['sync_complete_calls'], 0),
                              span(entry['sync_calls_per_confirmed_message'], 3), span(entry['sync_p99_ms']), span(gain),
                              f"{entry['sync_complete_calls']['completed']}/{gain['complete_pairs']}"])
        for payload in ('compressible', 'random'):
            condition = dict(engine=engine, version=version, profile='always', payload=payload)
            gain = contrast_summary(stats, 'compression_off_inherited', **condition)
            entry = {**condition, 'off_inherited_ratio': gain}
            for comp in ('inherited', 'off'):
                entry[comp] = measure(select(frame, kind='compression', compression=comp, **condition), 'throughput_mps')
            report['compression'].append(entry)
            compressionrows.append([NAMES[engine], 'Template' if payload == 'random' else 'Filler',
                                    span(entry['inherited'], 2, 1000), span(entry['off'], 2, 1000), span(gain),
                                    f"{entry['inherited']['completed']}/{entry['off']['completed']}/{gain['complete_pairs']}"])
    write('trace', ['System', '$P$', 'Sync calls', 'Calls/msg', 'Call p99, ms', 'Traced/plain', '$n_t/n_p$'], tracerows, alignment='lrllllr')
    write('compression', ['System', 'Payload', 'Inherited, kmsg/s', 'Off, kmsg/s', 'Off/inherited', '$n_i/n_o/n_p$'], compressionrows, alignment='lllllr')
    return report, generated


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', default='followup/derived')
    parser.add_argument('--tables', default='data/derived')
    parser.add_argument('--figures', default='paper/figures')
    args = parser.parse_args()
    folder = ROOT / args.input
    stats = json.loads((folder/'statistics.json').read_text())
    assert digest(folder/'trials.csv') == stats['trials_csv_sha256']
    frame = pd.read_csv(folder/'trials.csv', keep_default_na=False)
    numeric = ['throughput_mps', 'p99_ms', 'sample_count', 'positions_above_p99', 'receipt_excess_ms',
               'driver_mean_cores', 'broker_mean_cores', 'sync_complete_calls', 'sync_calls_per_confirmed_message',
               'sync_p50_ms', 'sync_p99_ms', 'sync_sum_call_seconds', 'sync_errors',
               'confirmed_records', 'unknown_records', 'seconds_until_workers_joined',
               'retained_count_at_reconciliation', 'observation_seconds']
    for key in numeric:
        frame[key] = pd.to_numeric(frame[key] if key in frame else pd.Series(np.nan, index=frame.index), errors='coerce')
    texdir, figdir = ROOT/args.tables, ROOT/args.figures
    texdir.mkdir(exist_ok=True, parents=True); figdir.mkdir(exist_ok=True, parents=True)
    report, generated = render(frame, stats, texdir, figdir)
    report.update(generator_sha256=digest(Path(__file__).resolve()),
                  statistics_sha256=digest(folder/'statistics.json'), trials_sha256=digest(folder/'trials.csv'),
                  generated_sha256={str(p.relative_to(ROOT)): digest(p) for p in generated})
    (folder/'report.json').write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
    print(json.dumps({'generated_files': len(generated), 'campaigns': len(stats['campaigns'])}))


if __name__ == '__main__':
    main()
