"""Verifier regression tests using retained pilot evidence and synthetic summaries."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

import pandas as pd

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('followup_analysis',HERE/'analyze.py')
a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)


class AnalysisRejectionTests(unittest.TestCase):
    def test_completed_workload_requires_trace(self):
        for key,trial_id in [('trace','F0001'),('preload_trace','F0003')]:
            row=json.loads((a.ROOT/'followup/campaigns/pilot04/raw'/trial_id/'result.json').read_text())
            row.pop(key)
            with tempfile.TemporaryDirectory() as directory:
                folder=Path(directory);(folder/'result.json').write_text(json.dumps(row))
                with self.assertRaisesRegex(AssertionError,'missing'):
                    a.verify_trial(folder,row['trial'])

    def test_forged_invocation_is_rejected(self):
        folder=a.ROOT/'followup/campaigns/pilot04';trial=json.loads((folder/'plan.json').read_text())[0]
        with tempfile.TemporaryDirectory() as directory:
            target=Path(directory);(target/'invocations').mkdir();(target/'raw'/trial['id']).mkdir(parents=True)
            for suffix in ('-started.json','.json'):
                row=json.loads((folder/'invocations'/(trial['id']+suffix)).read_text())
                if suffix=='.json':row['stdout']='{}'
                (target/'invocations'/(trial['id']+suffix)).write_text(json.dumps(row))
            (target/'raw'/trial['id']/'result.json').write_bytes((folder/'raw'/trial['id']/'result.json').read_bytes())
            with self.assertRaises(AssertionError):a.verify_invocation(target,trial)

    def test_partial_pairs_are_not_silently_complete(self):
        frame=pd.DataFrame([
            dict(campaign='x',kind='publication',engine='redis',id='a',block=0,publishers=1,status='complete',throughput_mps=10.),
            dict(campaign='x',kind='publication',engine='redis',id='b',block=0,publishers=16,status='complete',throughput_mps=30.),
            dict(campaign='x',kind='publication',engine='redis',id='c',block=1,publishers=1,status='complete',throughput_mps=20.),
            dict(campaign='x',kind='publication',engine='redis',id='d',block=1,publishers=16,status='failed',throughput_mps=None)])
        row=a.paired(frame,'publication','publishers',16,1,['engine'])['per_campaign'][0]
        self.assertEqual((row['planned_pairs'],row['complete_pairs'],row['unavailable_pairs'],row['estimate']),(2,1,1,3.))

    def test_entirely_failed_condition_remains_visible(self):
        frame=pd.DataFrame([dict(campaign='x',engine='nats',status='failed')])
        summary=a.summary(frame,['engine'],'throughput_mps')
        self.assertEqual(summary['outcome_counts'][0]['failed'],1)
        self.assertEqual(summary['per_campaign'],[])

    def test_missing_thread_trace_is_rejected(self):
        source=a.ROOT/'followup/campaigns/pilot04/raw/F0004'
        row=json.loads((source/'result.json').read_text())
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(AssertionError,'Missing or extra'):
                a.syscall_summary(Path(directory),row)


if __name__=='__main__':unittest.main()
