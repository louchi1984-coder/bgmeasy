import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest
import zipfile

SCRIPT = Path(__file__).resolve().parents[1]/'scripts/download_soundfonts.py'
spec = importlib.util.spec_from_file_location('download_soundfonts', SCRIPT)
D = importlib.util.module_from_spec(spec);spec.loader.exec_module(D)


class SoundfontDownloadTests(unittest.TestCase):
    def make_bundle(self, root, name='soundfonts/test.sf2'):
        archive = root/'test.zip'
        with zipfile.ZipFile(archive, 'w') as z:
            z.writestr(name, b'fixture')
        return archive, {'sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
                         'files': {name: hashlib.sha256(b'fixture').hexdigest()}}

    def test_install_is_verified_and_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);archive,spec=self.make_bundle(root);out=root/'checkout'
            self.assertEqual(D.install(archive,out,spec),1)
            self.assertEqual(D.install(archive,out,spec),1)
            self.assertEqual((out/'soundfonts/test.sf2').read_bytes(),b'fixture')

    def test_bad_archive_hash_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);archive,spec=self.make_bundle(root);spec['sha256']='0'*64
            with self.assertRaisesRegex(ValueError,'SHA-256'):D.install(archive,root/'checkout',spec)
            self.assertFalse((root/'checkout').exists())

    def test_conflicting_file_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);archive,spec=self.make_bundle(root);out=root/'checkout';(out/'soundfonts').mkdir(parents=True)
            target=out/'soundfonts/test.sf2';target.write_bytes(b'own font')
            with self.assertRaisesRegex(ValueError,'Existing file'):D.install(archive,out,spec)
            self.assertEqual(target.read_bytes(),b'own font')

    def test_traversal_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);archive,spec=self.make_bundle(root,'soundfonts/../../escape')
            with self.assertRaisesRegex(ValueError,'Unsafe'):D.install(archive,root/'checkout',spec)
            self.assertFalse((root/'escape').exists())


if __name__ == '__main__':unittest.main()
