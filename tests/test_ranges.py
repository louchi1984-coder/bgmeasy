"""Model-specific range references must not become generic instrument prohibitions."""
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'scripts'
sys.path.insert(0, str(SCRIPTS))
import render_score_sf2 as RS
import soundfonts as SF


class RangeTests(unittest.TestCase):
    def run_score(self, track, notes):
        score = {'bpm': 100, 'tracks': {'voice': track},
                 'sections': {'A': {'bars': 1, 'voice': [notes]}}, 'arrangement': ['A']}
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / 'score.json'
            p.write_text(json.dumps(score), encoding="utf-8")
            before = hashlib.sha256(p.read_bytes()).hexdigest()
            result = subprocess.run([sys.executable, '-I', '-B', str(SCRIPTS / 'check_ranges.py'), str(p)],
                                    capture_output=True, text=True, encoding="utf-8", errors="replace")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(), before)
        return result.stdout

    def test_unselected_model_does_not_use_old_generic_limits(self):
        text = self.run_score({'inst': 'pluck', 'preset': 'generaluser-gs:0:106'}, 'C2:4')
        self.assertIn('[条件]', text)
        self.assertNotIn('[CHECK]', text)
        self.assertIn('未指定型号', text)

    def test_qudi_a4_is_inside_declared_sounding_range(self):
        text = self.run_score({'inst': 'dizi', 'range_variant': 'dizi.hkco-qudi-c'}, 'A4:4')
        self.assertIn('[范围内]', text)
        self.assertNotIn('暗/较虚', text)
        self.assertIn('不认证音源身份', text)

    def test_same_note_outside_bangdi_reference_is_not_impossible(self):
        text = self.run_score({'inst': 'dizi', 'range_variant': 'dizi.hkco-bangdi-g'}, 'A4:4')
        self.assertIn('[REVIEW]', text)
        self.assertNotIn('[CHECK]', text)
        self.assertIn('不等于不可演奏', text)

    def test_documented_extra_qudi_note_is_not_rejected(self):
        text = self.run_score({'inst': 'dizi', 'range_variant': 'dizi.hkco-qudi-c'}, 'B6:4')
        self.assertIn('[范围内]', text)
        self.assertIn('图示附加音', text)

    def test_bandoneon_keeps_high_b_but_reports_missing_b_flat(self):
        track = {'inst': 'keys', 'preset': 'generaluser-gs:0:23', 'range_variant': 'bandoneon.rheinische-142'}
        self.assertIn('[范围内]', self.run_score(track, 'B6:4'))
        missing = self.run_score(track, 'Bb6:4')
        self.assertIn('[CHECK]', missing)
        self.assertIn('明确缺音: Bb6', missing)

    def test_clavinet_physical_keyboard_endpoints(self):
        track = {'inst': 'keys', 'preset': 'generaluser-gs:0:7', 'range_variant': 'clavinet.hohner-d6'}
        self.assertIn('[范围内]', self.run_score(track, 'F1:2 E6:2'))
        self.assertIn('物理键盘边界', self.run_score(track, 'F6:4'))
        self.assertIn('[CHECK]', self.run_score(track, 'F6:4'))

    def test_sampler_tranh_stays_pending_instead_of_using_sample_keys(self):
        text = self.run_score({'inst': 'guzheng', 'engine': 'sampler:dantranh'}, 'C3:4')
        self.assertIn('[待核]', text)
        self.assertNotIn('[范围内]', text)

    def test_invalid_reference_never_silently_falls_back(self):
        text = self.run_score({'inst': 'keys', 'range_variant': 'dizi.not-a-model'}, 'C4:4')
        self.assertIn('[CHECK]', text)
        self.assertIn('未知range_variant', text)
        self.assertNotIn('[OK]', text)

    def test_unreviewed_violin_still_has_its_existing_range_check(self):
        text = self.run_score({'inst': 'strings', 'preset': 'generaluser-gs:0:40'}, 'C2:4')
        self.assertIn('[CHECK]', text)
        self.assertIn('小提琴', text)

    def test_query_exposes_conditions_and_sources(self):
        p = subprocess.run([sys.executable, '-I', '-B', str(SCRIPTS / 'check_ranges.py'),
                            '--list-variants', 'dizi'], capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn('dizi.hkco-qudi-c', p.stdout)
        self.assertIn('G4~G6', p.stdout)
        self.assertIn('hkco.org', p.stdout)

    def test_evidence_covers_all_21_without_promoting_old_limits(self):
        table = json.loads((ROOT / 'references/instrument-ranges.json').read_text(encoding="utf-8"))
        evidence = json.loads((ROOT / 'references/instrument-range-evidence.json').read_text(encoding="utf-8"))
        self.assertEqual(len(evidence['instruments']), 21)
        ids = []
        for r in evidence['instruments']:
            row = table['instruments'][r['id']]
            self.assertIsNone(row['common'])
            self.assertIsNone(row['extreme'])
            self.assertEqual(row['legacy_unverified']['common'], r['legacy_common_midi'])
            for v in r['verified_variants']:
                ids.append(v['id'])
                self.assertIn(v['source'], evidence['sources'])
                self.assertLessEqual(*v['midi_range'])
        self.assertEqual(len(ids), len(set(ids)))

    def test_reference_annotation_does_not_change_rendered_midi(self):
        tracks = {'voice': {'inst': 'dizi', 'preset': 'generaluser-gs:0:73'}}
        default = ROOT / 'soundfonts/GeneralUser-GS.sf2'
        before = SF.resolve_tracks(tracks, default, default_programs={k: v[0] for k, v in RS.GM.items()})
        after = deepcopy(before)
        after['voice']['range_variant'] = 'dizi.hkco-qudi-c'
        secs = {'A': (1, {'voice': [[(0, 4, [69], .65)]]})}
        def midi_bytes(t):
            mid = RS.build_midi({}, 4, t, ['A'], secs, 100, 4, .8, 7)[0]
            out = io.BytesIO(); mid.save(file=out)
            return out.getvalue()
        self.assertEqual(midi_bytes(before), midi_bytes(after))


if __name__ == '__main__':
    unittest.main()
