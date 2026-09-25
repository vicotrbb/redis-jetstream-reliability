"""Integrity tests on synthetic package fixtures, not broker experiments."""
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

from checksums import sha256, write_manifest
from verify_release import parse_manifest, verify_archive, verify_directory


class ReleaseIntegrity(unittest.TestCase):
    def setUp(self):
        self.scratch=tempfile.TemporaryDirectory()
        self.root=Path(self.scratch.name)/'fixture'
        self.root.mkdir()
        files={'CITATION.cff':'version: 1.1.0\n',
               'release/metadata.json':'{"version":"1.1.0"}',
               'output/pdf/redis-jetstream-reliability.pdf':'synthetic identity fixture',
               'LICENSE.md':'synthetic scope fixture',
               'LICENSES/CC-BY-4.0.txt':'synthetic license fixture',
               'LICENSES/MIT.txt':'synthetic license fixture',
               'paper/main.log':'synthetic log fixture',
               'paper/main.bbl':'synthetic bibliography fixture',
               'data/derived/visual-review.json':'{}'}
        for name,value in files.items():
            path=self.root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(value)
        manifest={'version':'1.1.0','core_sha256':{
            name:sha256(self.root/name) for name in files if name.endswith('.pdf')}}
        (self.root/'release/manifest.json').write_text(json.dumps(manifest))
        self.entries=write_manifest(self.root)

    def tearDown(self):
        self.scratch.cleanup()

    def archive(self,extra=None):
        path=Path(self.scratch.name)/'fixture.tar.gz'
        with tarfile.open(path,'w:gz') as tf:
            for name in [*self.entries,'SHA256SUMS']:
                tf.add(self.root/name,arcname=f'redis-jetstream-reliability-v1.1.0/{name}')
            if extra:
                info=tarfile.TarInfo('redis-jetstream-reliability-v1.1.0/'+extra)
                content=b'unlisted';info.size=len(content);tf.addfile(info,io.BytesIO(content))
        return path

    def test_roundtrip_directory_and_archive(self):
        self.assertEqual(verify_directory(self.root)['version'],'1.1.0')
        self.assertEqual(verify_archive(self.archive())['files_verified'],len(self.entries))

    def test_changed_content_rejected_in_both_forms(self):
        (self.root/'LICENSE.md').write_text('changed fixture')
        with self.assertRaisesRegex(ValueError,'Content changed'):verify_directory(self.root)
        with self.assertRaisesRegex(ValueError,'Archive content changed'):verify_archive(self.archive())

    def test_missing_file_rejected(self):
        (self.root/'LICENSE.md').unlink()
        with self.assertRaisesRegex(ValueError,'file set mismatch'):verify_directory(self.root)

    def test_unlisted_content_rejected_in_both_forms(self):
        (self.root/'unexpected.txt').write_text('unlisted')
        with self.assertRaisesRegex(ValueError,'file set mismatch'):verify_directory(self.root)
        with self.assertRaisesRegex(ValueError,'unlisted members'):verify_archive(self.archive('unexpected.txt'))

    def test_duplicate_archive_member_rejected(self):
        with self.assertRaisesRegex(ValueError,'Duplicate'):verify_archive(self.archive('LICENSE.md'))

    def test_version_mismatch_rejected_after_rehash(self):
        (self.root/'CITATION.cff').write_text('version: 9.0.0\n')
        write_manifest(self.root)
        with self.assertRaisesRegex(ValueError,'Citation version mismatch'):verify_directory(self.root)

    def test_path_escape_and_duplicate_manifest_rejected(self):
        for path in ('../outside','/outside','a/../outside','a\\outside'):
            with self.subTest(path=path),self.assertRaises(ValueError):
                parse_manifest(('0'*64+'  '+path+'\n').encode())
        line='0'*64+'  repeated\n'
        with self.assertRaises(ValueError):parse_manifest((line+line).encode())

    def test_symbolic_link_rejected(self):
        (self.root/'linked').symlink_to(self.root/'LICENSE.md')
        with self.assertRaisesRegex(ValueError,'symbolic link'):verify_directory(self.root)

    def test_existing_release_refused_before_any_write(self):
        import package_release
        destination=self.root/'releases/v1.1.0'
        destination.mkdir(parents=True)
        sentinel=destination/'keep';sentinel.write_text('original release')
        before=(self.root/'SHA256SUMS').read_bytes()
        with patch.object(package_release,'ROOT',self.root):
            with self.assertRaisesRegex(FileExistsError,'already exists'):package_release.main()
        self.assertEqual(sentinel.read_text(),'original release')
        self.assertEqual((self.root/'SHA256SUMS').read_bytes(),before)


if __name__=='__main__':unittest.main()
