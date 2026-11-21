import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from numba import config

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'


class ReferenceRuntimeTests(unittest.TestCase):
    @unittest.skipUnless(hasattr(config, 'CACHE_LOCATOR_CLASSES'), 'requires selectable Numba cache locators')
    def test_private_cache_after_failed_import_and_explicit_cache_in_a_new_process(self):
        # Limit Numba to the configured locator so read-only defaults are reproducible on any host.
        probe = """
import json, os, sys
from numba import config
import librosa, numpy as np
try:
    librosa.stft
except RuntimeError as error:
    assert 'no locator available' in str(error), error
else:
    raise AssertionError('expected the default JIT cache to be unavailable')
if sys.argv[2]:
    os.environ['NUMBA_CACHE_DIR'] = sys.argv[2]
sys.path.insert(0, sys.argv[1])
import analyze_reference as analysis
result = analysis.librosa.stft(np.ones(128, dtype=np.float32), n_fft=64)
assert result.shape == (33, 9) and np.isfinite(result).all()
print(json.dumps([config.CACHE_DIR, os.environ.get('NUMBA_CACHE_DIR')]))
"""
        env = dict(os.environ, NUMBA_CACHE_LOCATOR_CLASSES='UserProvidedCacheLocator')
        env.pop('NUMBA_CACHE_DIR', None)
        with tempfile.TemporaryDirectory() as directory:
            configured = str(Path(directory) / 'my cache')
            for cache in ('', configured):
                with self.subTest(cache=cache):
                    child = subprocess.run([sys.executable, '-I', '-B', '-c', probe, str(SCRIPTS), cache],
                                           env=env, capture_output=True, text=True, encoding='utf-8')
                    self.assertEqual(child.returncode, 0, child.stderr)
                    actual, exported = json.loads(child.stdout)
                    self.assertEqual(exported, cache or None)
                    if cache:
                        self.assertEqual(actual, configured)
                        self.assertTrue(any(Path(actual).rglob('*.nbi')))
                    else:
                        self.assertTrue(Path(actual).name.startswith('bgmeasy-numba-'))
                        self.assertFalse(Path(actual).exists())

    def test_invalid_cache_fails_only_the_reference_probe(self):
        with tempfile.TemporaryDirectory() as directory:
            cache = Path(directory) / 'not a directory'
            cache.touch()
            child = subprocess.run([sys.executable, '-I', '-B', str(SCRIPTS/'check_deps.py')],
                                   env=dict(os.environ, NUMBA_CACHE_DIR=str(cache)),
                                   capture_output=True, text=True, encoding='utf-8')
            self.assertEqual(child.returncode, 0, child.stderr)
            self.assertIn('[OPTIONAL-MISSING] python: librosa (STFT)', child.stdout)
            self.assertIn('Set NUMBA_CACHE_DIR to a writable directory', child.stdout)
            self.assertIn(str(cache), child.stdout)


if __name__ == '__main__':
    unittest.main()
