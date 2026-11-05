import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

import numpy as np
import soundfile as sf

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
import soundfonts as F
import instruments as K
import sf2_capabilities as SF

FOLDER = F.ROOT / 'ethnic-light'


class EthnicLightTests(unittest.TestCase):
    def test_redistribution_provenance_size_and_embedded_sample_integrity(self):
        manifest = json.loads((FOLDER / 'manifest.json').read_text(encoding="utf-8"))
        self.assertLessEqual(sum(p.stat().st_size for p in FOLDER.rglob('*') if p.is_file()), 30_000_000)
        self.assertIn('CC0', (FOLDER / 'LICENSE-erhu.txt').read_text(encoding="utf-8"))
        asset = manifest['assets'][0]
        self.assertEqual(asset['license'], 'CC0-1.0')
        self.assertEqual(asset['source_commit'], '6615047b2fd06126877483e97b8bb4af9d00b080')
        font = F.ROOT / asset['file']
        raw = font.read_bytes()
        self.assertEqual(len(raw), asset['installed_bytes'])
        self.assertEqual(hashlib.sha256(raw).hexdigest(), asset['sha256'])
        # Read actual RIFF chunks, then validate every embedded PCM sample, not
        # just the manifest's totals or the SF2 preset names.
        tables = {}
        pos = 12
        while pos < len(raw):
            tag, size = struct.unpack_from('<4sI', raw, pos)
            if tag == b'LIST':
                sub = pos + 12
                while sub < pos + 8 + size:
                    kind, length = struct.unpack_from('<4sI', raw, sub)
                    tables[kind] = raw[sub + 8:sub + 8 + length]
                    sub += 8 + length + length % 2
            pos += 8 + size + size % 2
        self.assertEqual(len(manifest['samples']), 170)
        self.assertEqual(len(tables[b'shdr']), 171 * 46)
        for i, sample in enumerate(manifest['samples']):
            _, start, end, _, _, rate, root, correction, _, sample_type = struct.unpack_from(
                '<20sIIIIIBbHH', tables[b'shdr'], 46 * i)
            pcm = tables[b'smpl'][start * 2:end * 2]
            self.assertEqual((end - start, rate, root, correction, sample_type),
                             (sample['frames'], 32000, sample['root_midi'], 0, 1))
            self.assertEqual(hashlib.sha256(pcm).hexdigest(), sample['pcm_sha256'])
            self.assertTrue(np.any(np.frombuffer(pcm, dtype='<i2')))

    def test_new_presets_resolve_to_erhu_and_only_recorded_keys(self):
        catalog = F.build_catalog()
        found = [e for e in F.search(catalog, '二胡', source='ethnic-light')
                 if e['source'] == 'ethnic-light/erhu']
        self.assertEqual(len(found), 8)
        self.assertEqual(len(F.search(catalog, '二胡 短音', source='ethnic-light')), 4)
        self.assertEqual(len(F.search(catalog, '二胡 长音', source='ethnic-light')), 2)
        caps = SF.inspect(FOLDER / 'erhu.sf2')
        for entry in found:
            program = entry['program']
            roots = list(range(62, 87 if program >= 6 else 82))
            cap = caps[(0, program)]
            self.assertEqual(cap['covered_midi_keys'], roots)
            self.assertEqual(cap['root_midi_notes'], roots)
            self.assertEqual(cap['unique_sample_headers'], len(roots))
            self.assertEqual(cap['loop_modes'], [0])
            self.assertEqual(entry['track']['inst'], 'erhu')
            self.assertEqual(K.profile_for(entry, K.knowledge()), 'erhu')
            self.assertNotIn('钢琴', entry['tags'])
            cfg = F.resolve_tracks({'v': {'inst': 'erhu', 'preset': entry['id']}},
                                   F.ROOT / 'GeneralUser-GS.sf2')['v']
            self.assertEqual(cfg['sf2'], 'ethnic-light/erhu.sf2')
            self.assertEqual(cfg['gm'], {'bank': 0, 'program': program})

    def test_every_take_renders_through_unchanged_standard_workflow(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            for program in range(8):
                with self.subTest(program=program):
                    score = {'bpm': 150, 'seed': 7, 'humanize_ms': 0,
                             'tracks': {'v': {'inst': 'erhu', 'preset': f'ethnic-light/erhu:0:{program}',
                                              'gain': .7, 'params': {'bend': 0, 'vibrato': 0}}},
                             'sections': {'A': {'v': ['A4:2@.8 r:2']}}, 'arrangement': ['A']}
                    fixture, output = directory / 'score.json', directory / f'{program}.wav'
                    fixture.write_text(json.dumps(score), encoding="utf-8")
                    result = subprocess.run([sys.executable, '-I', '-B', str(SCRIPTS / 'render_score_sf2.py'),
                                             str(fixture), str(output), '--duration', '2', '--tail', '.4'],
                                            capture_output=True, text=True, encoding="utf-8", errors="replace")
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    y, rate = sf.read(output, always_2d=True)
                    self.assertEqual(y.shape, (round(2 * rate), 2))
                    self.assertTrue(np.isfinite(y).all())
                    self.assertGreater(float(np.mean(y ** 2)), 1e-7)
                    self.assertLessEqual(float(abs(y).max()), 1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
