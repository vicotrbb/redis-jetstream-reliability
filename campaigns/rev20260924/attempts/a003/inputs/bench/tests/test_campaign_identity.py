import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import campaign_identity as ci
import run_homelab as runner


class CampaignIsolationTests(unittest.TestCase):
    def test_wrong_campaign_failure_ledger_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/'failed-trials.jsonl').write_text(json.dumps({**ci.identity('other','a1'),'key':'D038'})+'\n')
            with self.assertRaisesRegex(ValueError,'Mismatched campaign_id'):
                ci.seal(root,ci.identity('study','a1'))

    def test_wrong_attempt_in_execution_log_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/'run.log').write_text(json.dumps({**ci.identity('study','old'),'key':'D038'})+'\n')
            with self.assertRaisesRegex(ValueError,'Mismatched attempt_id'):
                ci.seal(root,ci.identity('study','new'))

    def test_seal_detects_modified_or_added_evidence(self):
        for modification in ('modify','add'):
            with self.subTest(modification=modification), tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);record=ci.identity('study','a1')
                (root/'raw.csv').write_text('id\n1\n')
                ci.seal(root,record)
                ci.verify_seal(root,record)
                if modification=='modify':(root/'raw.csv').write_text('id\n2\n')
                else:(root/'stale-ledger.json').write_text('{}')
                with self.assertRaises(ValueError):ci.verify_seal(root,record)

    def test_collection_and_seal_are_exclusive(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);record=ci.identity('study','a1')
            ci.seal(root,record)
            with self.assertRaises(FileExistsError):ci.seal(root,record)
            with self.assertRaises(FileExistsError):ci.write_new(root/'manifest.json',{})

    def test_existing_attempt_is_rejected_before_external_actions(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(runner,'ROOT',Path(tmp)):
            target=runner.location('study','a1');target.mkdir(parents=True)
            with patch.object(runner.subprocess,'run') as call:
                with self.assertRaises(FileExistsError):runner.prepare('study','a1','validation')
                call.assert_not_called()

    def test_namespace_ownership_is_required(self):
        record={**ci.identity('study','a1'),'owner_token':'expected'}
        reply=type('Reply',(),{'stdout':json.dumps({'metadata':{'labels':{'evidence-owner':'other'}}})})()
        with patch.object(runner,'run',return_value=reply):
            with self.assertRaisesRegex(ValueError,'ownership'):runner.owned_namespace(record)

    def test_invalid_path_ids_are_rejected(self):
        for bad in ('../other','UPPER','x/y','', 'x'*21):
            with self.assertRaises(ValueError):ci.identity(bad,'a1')

    def test_symlink_cannot_import_mutable_external_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'collection';root.mkdir()
            outside=Path(tmp)/'outside';outside.write_text('old')
            (root/'alias').symlink_to(outside)
            with self.assertRaisesRegex(ValueError,'Symlink'):ci.seal(root,ci.identity('study','a1'))


if __name__=='__main__':unittest.main()
