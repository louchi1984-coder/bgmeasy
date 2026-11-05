from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

import numpy as np
import soundfile as sf

VERIFY = Path(__file__).resolve().parents[1] / 'scripts/verify.py'


@unittest.skipUnless(shutil.which('ffmpeg'), 'requires ffmpeg')
class VerifyTests(unittest.TestCase):
    def check_clip_count(self, signal, expected):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'stereo.wav'
            sf.write(path, signal, 44100, subtype='PCM_16')
            result = subprocess.run([sys.executable, '-I', '-B', str(VERIFY), str(path)],
                                    capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(result.returncode, 0, result.stderr)
        count = re.search(r'削波采样数:\s*(\d+)', result.stdout)
        self.assertIsNotNone(count, result.stdout)
        self.assertEqual(int(count.group(1)), expected, result.stdout)

    def test_correlated_stereo_below_full_scale_has_no_clips(self):
        wave = .8 * np.sin(2 * np.pi * 440 * np.arange(44100 * 3) / 44100)
        self.check_clip_count(np.column_stack([wave, wave]), 0)

    def test_opposite_full_scale_samples_do_not_cancel_before_counting(self):
        wave = .1 * np.sin(2 * np.pi * 440 * np.arange(44100 * 3) / 44100)
        stereo = np.column_stack([wave, wave])
        stereo[5000:5010, 0] = 1
        stereo[5000:5010, 1] = -1
        self.check_clip_count(stereo, 20)


if __name__ == '__main__':
    unittest.main(verbosity=2)
