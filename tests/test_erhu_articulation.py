from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import render_score_sf2 as R


def make_midi(params, notes=None, inst='erhu'):
    track = {'inst': inst, 'params': params}
    notes = notes if notes is not None else [(0, 2, [62], .8), (2, 2, [69], .8)]
    return R.build_midi({'humanize_ms': 0}, 4, {'voice': track}, ['A'],
                        {'A': (1, {'voice': [notes]})}, 120, 4, .4, 7)[0]


def absolute_events(mid):
    result = []
    for track in mid.tracks:
        tick = 0
        for event in track:
            tick += event.time
            result.append((tick, event))
    return result


class ErhuArticulationTests(unittest.TestCase):
    def test_slide_vibrato_and_reset_reach_midi(self):
        events = absolute_events(make_midi({'bend': .6, 'vibrato': .009}))
        bends = [(t, e.pitch) for t, e in events if e.type == 'pitchwheel']
        # 下方0.6半音滑入；长音随后有双向揉弦，每个音结束回到零。
        self.assertEqual(bends[0], (0, round(-.6 / 2 * 8192)))
        self.assertGreater(max(p for t, p in bends if 240 < t < 930), 200)
        self.assertLess(min(p for t, p in bends if 240 < t < 930), -200)
        self.assertEqual([t for t, p in bends if p == 0 and t in (931, 1891)], [931, 1891])
        cc = [(e.control, e.value) for t, e in events if e.type == 'control_change' and e.control in (101, 100, 6, 38)]
        self.assertEqual(cc, [(101, 0), (100, 0), (6, 2), (38, 0), (101, 127), (100, 127)])
        self.assertEqual(sum(e.type == 'note_on' for t, e in events), 2)

    def test_zero_and_unset_leave_legacy_midi_unchanged(self):
        for params in ({}, {'bend': 0, 'vibrato': 0}):
            self.assertFalse(any(e.type == 'pitchwheel' for t, e in absolute_events(make_midi(params))))
        self.assertFalse(any(e.type == 'pitchwheel' for t, e in absolute_events(make_midi({'bend': .6}, inst='pipa'))))

    def test_channel_wide_bend_rejects_chords(self):
        with self.assertRaisesRegex(R.R.ScoreError, '单音旋律'):
            make_midi({'bend': .6}, [(0, 4, [62, 69], .8)])

    def test_invalid_pitch_range_is_not_silently_clipped(self):
        with self.assertRaisesRegex(R.R.ScoreError, '2个半音'):
            make_midi({'bend': 3})

    def test_close_notes_stop_old_controls_before_new_onset(self):
        events = R.erhu_pitch_events([(0, 500), (480, 950)], {'bend': .6}, 0, 960)
        self.assertIn((479, 0), [(t, e.pitch) for t, order, e in events if e.type == 'pitchwheel'])
        self.assertFalse(any(t == 500 and e.pitch == 0 for t, order, e in events if e.type == 'pitchwheel'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
