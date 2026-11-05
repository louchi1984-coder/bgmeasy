from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import mido

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import render_score_sf2 as R


class ReportFailureTests(unittest.TestCase):
    def check_failure(self, returncode):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            score = root / 'score.json'
            score.write_text(json.dumps({'tracks': {}, 'sections': {}}), encoding='utf-8')
            scratch = root / 'report'
            scratch.mkdir()
            args = SimpleNamespace(score=str(score), mute='', comp_ratio=2, tail=.8,
                                   soundfont='unused.sf2', duration=1, calibrate=False, seed=7)
            result = subprocess.CompletedProcess([], returncode, '', 'child failed')
            with patch.object(R.tempfile, 'mkdtemp', return_value=str(scratch)), \
                    patch.object(R.subprocess, 'run', return_value=result):
                with self.assertRaisesRegex(R.R.ScoreError, 'full 子渲染失败'):
                    R.report_levels(args, {}, {}, [])
            self.assertFalse(scratch.exists())

    def test_child_failure_is_reported_and_temporary_files_are_removed(self):
        self.check_failure(1)

    def test_child_success_without_audio_is_not_reported_as_success(self):
        self.check_failure(0)


@unittest.skipUnless(shutil.which('fluidsynth'), 'requires fluidsynth')
class ReportLevelsTests(unittest.TestCase):
    def test_zero_gain_is_zero_and_other_note_times_survive_counterfactual(self):
        score = {'bpm': 120, 'seed': 7, 'humanize_ms': 6, 'tracks': {
            'silent': {'inst': 'keys', 'gain': 0, 'reverb': 0},
            'backing': {'inst': 'keys', 'gain': .4, 'reverb': 0},
            'audible': {'inst': 'pluck', 'gain': .8, 'reverb': 0}},
            'sections': {'A': {'bars': 2,
                'silent': ['(C4:.25)*16'] * 2,
                'backing': ['(C3:.25)*16'] * 2,
                'audible': ['(E4:.25@.8)*16'] * 2}}, 'arrangement': ['A']}
        run = subprocess.run
        rendered = {}

        def capture(command, **kwargs):
            result = run(command + ['--keep-mid'], **kwargs)
            self.assertEqual(result.returncode, 0, result.stderr)
            output = Path(command[4])
            events = []
            controls = []
            for track in mido.MidiFile(output.with_suffix('.mid')).tracks:
                tick = 0
                for event in track:
                    tick += event.time
                    if event.type == 'note_on' and event.channel == 2:
                        events.append((tick, event.note, event.velocity))
                    if event.type == 'control_change' and event.control == 7 and event.channel == 0:
                        controls.append(event.value)
            rendered[output.stem] = (events, controls)
            return result

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'score.json'
            path.write_text(json.dumps(score), encoding="utf-8")
            sc, bpb, tracks, arr, sections = R.R.load(str(path))
            args = SimpleNamespace(score=str(path), soundfont=str(ROOT / 'soundfonts/GeneralUser-GS.sf2'),
                                   comp_ratio=2, tail=.8, duration=5, calibrate=False, seed=91, mute='')
            output = io.StringIO()
            with patch.object(R.subprocess, 'run', side_effect=capture), redirect_stdout(output):
                R.report_levels(args, tracks, sections, arr)
        # Compare actual MIDI emitted by the real child renderer, not recreated timings.
        self.assertEqual(len(rendered['full'][0]), 32)
        self.assertEqual(rendered['full'][0], rendered['m_backing'][0])
        self.assertEqual(rendered['full'][1], [0])
        self.assertRegex(output.getvalue(), r'(?m)^silent\s+-inf\s')


if __name__ == '__main__':
    unittest.main(verbosity=2)
