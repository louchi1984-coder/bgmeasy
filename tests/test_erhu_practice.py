import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import numpy as np
import soundfile as sf

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
import instruments as K
import soundfonts as F
import sf2_capabilities as SF

IDENT = 'ethnic-light/erhu-practice:0:0'
FOLDER = F.ROOT / 'ethnic-light'


class PracticeErhuTests(unittest.TestCase):
    def test_exact_approved_asset_and_separate_user_audition_scope(self):
        raw = (FOLDER / 'erhu-practice.sf2').read_bytes()
        self.assertEqual(len(raw), 541724)
        self.assertEqual(hashlib.sha256(raw).hexdigest(),
                         '0f3c2c5d971e29b6d89c6820dbdfc20aee54a247039e0d1bb6cf42dd119456bd')
        asset = next(a for a in json.loads((FOLDER / 'manifest.json').read_text(encoding="utf-8"))['assets']
                     if a['id'] == 'erhu-practice')
        self.assertEqual(asset['license'], 'CC0-1.0')
        self.assertEqual(asset['sha256'], hashlib.sha256(raw).hexdigest())
        self.assertLessEqual(sum(p.stat().st_size for p in FOLDER.rglob('*') if p.is_file()), 30_000_000)
        found = F.search(F.build_catalog(), '二胡 试听通过')
        self.assertEqual([e['id'] for e in found], [IDENT])
        cap = K.lookup(IDENT)['capability']
        self.assertEqual(cap['user_audition']['status'], 'user_accepted_timbre_trial')
        self.assertEqual(cap['listening_status'], 'not_listened')
        cfg = F.resolve_tracks({'v': {'inst': 'erhu', 'preset': IDENT}}, F.ROOT / 'GeneralUser-GS.sf2')['v']
        self.assertEqual((cfg['sf2'], cfg['gm']), ('ethnic-light/erhu-practice.sf2', {'bank': 0, 'program': 0}))

    def test_actual_key_coverage_stereo_links_and_finite_recording_lengths(self):
        font = FOLDER / 'erhu-practice.sf2'
        cap = SF.inspect(font)[(0, 0)]
        self.assertEqual(cap['covered_midi_keys'], [69, 72])
        self.assertEqual(cap['root_midi_notes'], [69, 72])
        self.assertEqual(cap['loop_modes'], [0])
        headers = SF.read_tables(font)['shdr'][:-1]
        self.assertEqual(len(headers), 4)
        for i, h in enumerate(headers):
            self.assertEqual(h[-1], 4 if i % 2 == 0 else 2)
            self.assertEqual(h[-2], i + 1 if i % 2 == 0 else i - 1)
            self.assertEqual(h[5], 44100)
            self.assertAlmostEqual((h[2] - h[1]) / h[5], 1.015 if i < 2 else 2.05, places=3)

    def audit(self, bar, bpm=80):
        score = {'bpm': bpm, 'tracks': {'v': {'inst': 'erhu', 'preset': IDENT}},
                 'sections': {'A': {'v': [bar]}}, 'arrangement': ['A'],
                 'design': {'performance': {'v': {'instrument': 'erhu', 'implementation': 'Recorded single notes'}}}}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'score.json'; path.write_text(json.dumps(score), encoding="utf-8")
            return K.audit_score(path)['issues']

    def test_score_check_reports_missing_keys_and_overlong_sustains_using_seconds(self):
        self.assertEqual(self.audit('A4:1 C5:2 r:1'), [])
        self.assertTrue(any('没有映射音高' in s and '67' in s for s in self.audit('G4:4')))
        self.assertTrue(any('原样本长度' in s for s in self.audit('A4:4')))
        self.assertTrue(any('原样本长度' in s for s in self.audit('C5:4')))
        self.assertEqual(self.audit('A4:2 r:2', bpm=160), [])

    def test_stable_preset_renders_the_approved_example(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'audio.wav'
            result = subprocess.run([sys.executable, '-I', '-B', str(SCRIPTS / 'render_score_sf2.py'),
                                     str(SCRIPTS.parent / 'examples/erhu-practice-audition.score.json'),
                                     str(output), '--duration', '9.8', '--tail', '.8'],
                                    capture_output=True, text=True, encoding="utf-8", errors="replace")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            y, rate = sf.read(output, always_2d=True)
            self.assertEqual(y.shape, (round(9.8 * rate), 2))
            self.assertTrue(np.isfinite(y).all())
            self.assertGreater(float(np.mean(y * y)), 1e-7)


if __name__ == '__main__':
    unittest.main(verbosity=2)
