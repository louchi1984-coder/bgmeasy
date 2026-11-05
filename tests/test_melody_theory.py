import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
import check_melody as C
import render_score as R
import render_score_sf2 as SF


def score(bars, chords=None):
    return {
        'bpm': 72, 'key': 'C major', 'humanize_ms': 0,
        'tracks': {'theme': {'inst': 'keys'}},
        'sections': {'A': {'theme': bars}}, 'arrangement': ['A'],
        'design': {'melody': ['theme'], 'chords': {'A': chords or ['C']}}
    }


def run_check(sc, *args):
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / 'score.json'; path.write_text(json.dumps(sc), encoding="utf-8")
        return subprocess.run([sys.executable, '-I', '-B', str(SCRIPTS / 'check_melody.py'),
                               str(path), *args], capture_output=True, text=True, encoding="utf-8", errors="replace")


def stream_of(text):
    return C.motif_events(text)


class MelodyTheoryTests(unittest.TestCase):
    def assert_neutral(self, result):
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn('[CHECK]', result.stdout)
        self.assertNotIn('[OK]', result.stdout)

    def test_original_chords_slash_bass_and_extensions(self):
        for name, expected, root in [
            ('Cm', {0, 3, 7}, 0), ('C/G', {0, 4, 7}, 0),
            ('Am7/G', {9, 0, 4, 7}, 9), ('Cadd9', {0, 4, 7, 2}, 0),
            ('F#maj9', {6, 10, 1, 5, 8}, 6), ('Dm11', {2, 5, 9, 0, 4, 7}, 2)
        ]:
            with self.subTest(chord=name): self.assertEqual(C.chord_set(name), (expected, root))

    def test_unknown_chord_skips_judgment_without_aborting(self):
        result = run_check(score(['D4:2 C4:2'], ['C7#9']))
        self.assert_neutral(result)
        self.assertIn('未识别和弦标签', result.stdout)
        self.assertIn('和声未知', result.stdout)

    def test_melody_third_and_fifth_may_end_on_tonic_harmony(self):
        for pitch in ('E4', 'G4'):
            with self.subTest(pitch=pitch):
                result = run_check(score([f'C4:2 {pitch}:2']))
                self.assert_neutral(result)
                self.assertIn(f'{pitch}，C上的和弦音', result.stdout)

    def test_accented_nonchord_tone_and_unbroken_phrase_are_not_quality_failures(self):
        result = run_check(score(['D4:1 C4:3'] * 4))
        self.assert_neutral(result)
        self.assertIn('首拍非和弦音小节', result.stdout)
        self.assertIn('记谱休止比例 0%', result.stdout)
        self.assertNotIn('旁白难进', result.stdout)
        self.assertNotIn('太满', result.stdout)

    def test_sparse_material_is_not_forced_to_add_notes(self):
        result = run_check(score(['C4:.25 r:3.75', 'r:4']))
        self.assert_neutral(result)
        self.assertNotIn('太空', result.stdout)

    def test_exact_repeat_can_present_material(self):
        sc = score(['E4:1 G4:1 A4:1 G4:1'] * 2)
        sc['design']['motif'] = sc['sections']['A']['theme'][0]
        result = run_check(sc)
        self.assert_neutral(result)
        self.assertIn('匹配 2 处', result.stdout)
        self.assertIn('拍位0: 原样', result.stdout)

    def test_rest_position_change_is_not_an_exact_copy(self):
        seed, span = stream_of('C4:1 D4:1 E4:1 r:1')
        stream, total = stream_of('C4:1 r:1 D4:1 E4:1')
        self.assertEqual(C.motif_matches(seed, span, stream, 4, total), [])

    def test_complete_motif_displaced_one_beat_is_reported_as_displacement(self):
        seed, span = stream_of('C4:1 D4:1 E4:1 r:1')
        stream, total = stream_of('r:1 C4:1 D4:1 E4:1 | r:1 G4:1 C5:2')
        self.assertEqual(C.motif_matches(seed, span, stream, 4, total), [(1, '节奏位移')])

    def test_cross_bar_material_and_internal_rest_are_preserved(self):
        motif = 'C4:3 D4:1 | E4:1 r:1'
        seed, span = stream_of(motif)
        stream, total = stream_of('C4:3 D4:1 | E4:1 r:3')
        self.assertEqual(C.motif_matches(seed, span, stream, 4, total), [(0, '原样')])
        sc = score(['C4:3 D4:1', 'E4:1 r:3']); sc['design']['motif'] = motif
        result = run_check(sc)
        self.assert_neutral(result)
        self.assertIn('素材窗口 6 拍', result.stdout)
        self.assertIn('匹配 1 处', result.stdout)

    def test_motif_window_cannot_extend_past_the_score(self):
        seed, span = stream_of('C4:1 D4:1 r:6')
        stream, total = stream_of('C4:1 D4:1 r:2')
        self.assertEqual(C.motif_matches(seed, span, stream, 4, total), [])

    def test_intra_bar_harmony_is_used_at_the_actual_onset(self):
        result = run_check(score(['C4:2 D4:2'], [[{'beat': 0, 'chord': 'C'}, {'beat': 2, 'chord': 'Dm'}]]))
        self.assert_neutral(result)
        self.assertIn('第三拍落和弦音: 1/1', result.stdout)
        self.assertIn('D4，Dm上的和弦音', result.stdout)

    def test_note_ending_at_harmony_boundary_uses_previous_harmony(self):
        result = run_check(score(['C4:1 E4:1 r:2'], [[{'beat': 0, 'chord': 'C'}, {'beat': 2, 'chord': 'Dm'}]]))
        self.assert_neutral(result)
        self.assertIn('E4，C上的和弦音', result.stdout)

    def test_explicit_phrase_range_survives_arrangement_expansion(self):
        sc = score(['C4:2 E4:2'])
        sc['sections']['B'] = {'theme': ['F4:2 G4:2']}
        sc['arrangement'] = ['A*2', 'B']
        sc['design']['phrases'] = {'theme': [{'start_bar': 1, 'end_bar': 2, 'function': '呈示'}]}
        result = run_check(sc)
        self.assert_neutral(result)
        self.assertIn('乐句1–2', result.stdout)
        self.assertIn('第2小节末个记谱音 E4', result.stdout)
        self.assertNotIn('第3小节末个记谱音', result.stdout)

    def test_silent_track_does_not_crash(self):
        result = run_check(score(['r:4']))
        self.assert_neutral(result)
        self.assertIn('没有记谱音符', result.stdout)

    def test_old_score_without_design_still_checks_via_tracks(self):
        sc = score(['C4:2 E4:2']); sc.pop('design')
        self.assert_neutral(run_check(sc, '--tracks', 'theme'))

    def test_invalid_note_duration_remains_a_format_error(self):
        result = run_check(score(['C4:3']))
        self.assertEqual(result.returncode, 2)
        self.assertIn('应为 4 拍', result.stderr)

    def test_invalid_harmony_times_and_phrase_ranges_are_annotation_errors(self):
        for entries in ([{'beat': 1, 'chord': 'C'}],
                        [{'beat': 0, 'chord': 'C'}, {'beat': 0, 'chord': 'G'}],
                        [{'beat': 0, 'chord': 'C'}, {'beat': 4, 'chord': 'G'}]):
            with self.subTest(entries=entries):
                result = run_check(score(['C4:4'], [entries]))
                self.assertEqual(result.returncode, 2)
                self.assertNotIn('Traceback', result.stderr)
        sc = score(['C4:4'])
        sc['design']['phrases'] = {'theme': [{'start_bar': 1, 'end_bar': 2}]}
        self.assertEqual(run_check(sc).returncode, 2)

    def test_design_annotations_do_not_change_standard_midi_or_parsed_notes(self):
        original = score(['C4:2 E4:2', 'D4:2 E4:2'])
        annotated = copy.deepcopy(original)
        annotated['design'].update({
            'rhythm': {'pulse': '4/4', 'accents': '1拍支点'},
            'harmony': {'bass': 'C—B'}, 'ending': '开放',
            'chords': {'A': ['C/G', [{'beat': 0, 'chord': 'G7'}, {'beat': 2, 'chord': 'Cmaj9'}]]},
            'phrases': {'theme': [{'start_bar': 1, 'end_bar': 2, 'function': '呈示'}]}
        })
        loaded, midi = [], []
        with tempfile.TemporaryDirectory() as d:
            for index, value in enumerate((original, annotated)):
                path = Path(d) / f'{index}.json'; path.write_text(json.dumps(value), encoding="utf-8")
                sc, bpb, tracks, arr, secs = R.load(path)
                loaded.append((bpb, tracks, arr, secs))
                mid = SF.build_midi(sc, bpb, tracks, arr, secs, 72, 8, .8, 7)[0]
                midi.append([list(track) for track in mid.tracks])
        self.assertEqual(loaded[0], loaded[1])
        self.assertEqual(midi[0], midi[1])


if __name__ == '__main__':
    unittest.main(verbosity=2)
