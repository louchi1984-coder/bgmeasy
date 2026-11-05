"""Known-signal and CLI regressions for the model-free reference frontend."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import soundfile as sf

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('reference_analysis', ROOT/'scripts/analyze_reference.py')
A = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(A)


def tone(note, seconds):
    t = np.arange(round(seconds*A.SR))/A.SR
    frequency = 440*2**((note-69)/12)
    return .25*np.sin(2*np.pi*frequency*t)*np.minimum(t/.01, 1)*np.minimum((seconds-t)/.02, 1)


class ReferenceAnalysisTests(unittest.TestCase):
    def test_silence_does_not_invent_music(self):
        r, _ = A.analyze(np.zeros(8*A.SR, dtype=np.float32))
        self.assertEqual(r['melody']['notes'], [])
        self.assertEqual(r['rhythm']['tempo_candidates'], [])
        self.assertEqual(r['rhythm']['pulse_times_seconds'], [])
        self.assertEqual(r['harmony']['key_candidates'], [])
        self.assertTrue(all(not x['candidates'] for x in r['harmony']['chord_windows']))
        self.assertEqual(r['structure']['boundaries'], [])
        json.dumps(r, allow_nan=False)

    def test_known_notes_and_global_time_offset(self):
        notes = [60, 64, 67, 65, 62]
        y = np.concatenate([np.concatenate([tone(n, .55), np.zeros(round(.15*A.SR))]) for n in notes])
        result, _ = A.pitch_features(y, isolated=True, offset=12)
        for i, n in enumerate(notes):
            middle = 12+i*.7+.3
            covering = [e for e in result['notes'] if e['start_seconds'] <= middle <= e['end_seconds']]
            self.assertTrue(covering, (i, result['notes']))
            self.assertAlmostEqual(covering[0]['midi'], n, delta=0)
        self.assertTrue(all(e['melody_identity']=='unverified' for e in result['notes']))
        self.assertEqual(result['source_mode'], 'provided_solo_not_verified')

    def test_repeated_pitch_is_not_one_sustained_note(self):
        y = np.concatenate([np.concatenate([tone(69, .4), np.zeros(round(.12*A.SR))]) for _ in range(4)])
        result, _ = A.pitch_features(y)
        self.assertGreaterEqual(sum(e['midi']==69 for e in result['notes']), 4)
        self.assertEqual(result['source_mode'], 'mixed_audio')

    def test_noise_is_not_a_verified_pitch_line(self):
        y = np.random.default_rng(2).normal(0, .05, 4*A.SR)
        result, _ = A.pitch_features(y)
        self.assertEqual(result['notes'], [])

    def test_mixed_audio_keeps_upper_pitch_evidence_and_alternatives(self):
        pitches = [72, 76, 74, 71, 67]
        lead = np.concatenate([np.concatenate([tone(n, .55), np.zeros(round(.15*A.SR))]) for n in pitches])
        t = np.arange(len(lead))/A.SR
        bass = .30*np.sin(2*np.pi*82.4069*t)+.15*np.sin(2*np.pi*164.8138*t)
        result, _ = A.pitch_features(lead+bass)
        recovered=0
        for i,pitch in enumerate(pitches):
            middle=i*.7+.3
            for event in result['notes']:
                if event['start_seconds'] <= middle <= event['end_seconds']:
                    options=[event['midi']]+[c['midi'] for c in event['alternate_pitch_candidates']]
                    recovered+=pitch in options
                    break
        self.assertGreaterEqual(recovered,4,result['notes'])
        self.assertTrue(all(e['melody_identity']=='unverified' for e in result['notes']))

    def test_tempo_candidates_and_compound_meter_are_not_four_four(self):
        y = np.zeros(9*A.SR)
        for t in np.arange(.25, 8.75, .5):
            start = round(t*A.SR)
            y[start:start+220] = np.random.default_rng(start).normal(0, .2, 220)*np.exp(-np.arange(220)/40)
        env, onsets = A.onset_features(y)
        r = A.rhythm_features(env, onsets, 9, meter='6/8', offset=10)
        self.assertTrue(any(abs(c['pulse_bpm']-120)<3 for c in r['tempo_candidates']), r)
        self.assertEqual(r['meter'], {'value':'6/8', 'source':'user'})
        self.assertIsNone(r['barlines'])
        self.assertTrue(all(t>=10 for t in r['onsets_seconds']))
        provided = A.rhythm_features(env, onsets, 9, bpm=60, meter='6/8')
        self.assertEqual(provided['pulse_bpm_used_for_grid'], 60)
        self.assertEqual(provided['tempo_source'], 'user')

    def test_triads_are_candidates_and_short_audio_has_no_forced_sections(self):
        y = sum(tone(n, 4) for n in [48, 52, 55])
        r, _ = A.analyze(y)
        stable = [w for w in r['harmony']['chord_windows'] if .5<w['start_seconds']<2]
        self.assertTrue(stable)
        self.assertTrue(any('C' in [c['label'] for c in w['candidates']] for w in stable), stable)
        self.assertTrue(all(w['status'] in ['candidate','ambiguous','unknown'] for w in stable))
        self.assertEqual(r['structure']['boundaries'], [])
        self.assertFalse(r['uses_learned_models'])

    def test_a_known_spectral_change_can_be_located(self):
        first = sum(tone(n, 6) for n in [60, 64, 67])
        second = sum(tone(n, 6) for n in [66, 70, 73])
        r, _ = A.analyze(np.concatenate([first, second]))
        times = [b['time_seconds'] for b in r['structure']['boundaries']]
        self.assertTrue(any(abs(t-6)<1.5 for t in times), times)

    def test_analysis_does_not_open_network_connections(self):
        with patch('socket.socket',side_effect=AssertionError('network access is not permitted')):
            r,_=A.analyze(tone(69,1))
        self.assertFalse(r['uses_learned_models'])

    def test_cli_outputs_are_readable_and_source_is_untouched(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp);source=tmp/'tone & source.wav';out=tmp/'report'
            sf.write(source, tone(69, 3), A.SR)
            digest=hashlib.sha256(source.read_bytes()).hexdigest()
            cmd=[sys.executable,'-I','-B',str(ROOT/'scripts/analyze_reference.py'),str(source),str(out),
                 '--seconds','2','--start','.5','--meter','6/8']
            result=subprocess.run(cmd,capture_output=True,text=True, encoding="utf-8", errors="replace")
            self.assertEqual(result.returncode,0,result.stderr)
            r=json.loads((out/'reference.json').read_text(encoding="utf-8"))
            self.assertEqual(r['source']['audio_channels'],1)
            self.assertEqual(r['spatial']['input_channels'],1)
            self.assertTrue(all(e['stereo_balance'] is None for e in r['voices']['notes']))
            self.assertEqual(r['analysis_range']['start_seconds'],.5)
            self.assertEqual(r['analysis_range']['duration_seconds'],2)
            self.assertAlmostEqual(r['analysis_range']['unanalysed_tail_seconds'],.5,places=3)
            self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(),digest)
            self.assertTrue(all((out/f).is_file() for f in A.FILES))
            self.assertTrue((out/'analysis.png').read_bytes().startswith(b'\x89PNG'))
            self.assertIn('tone &amp; source.wav', (out/'report.html').read_text(encoding="utf-8"))
            saved=(out/'reference.json').read_bytes()
            again=subprocess.run(cmd,capture_output=True,text=True, encoding="utf-8", errors="replace")
            self.assertNotEqual(again.returncode,0)
            self.assertEqual((out/'reference.json').read_bytes(),saved)

    def test_cli_rejects_invalid_ranges_and_unsynchronised_solo(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp=Path(tmp);source=tmp/'source.wav';solo=tmp/'short-solo.wav'
            sf.write(source,tone(69,2),A.SR);sf.write(solo,tone(69,1),A.SR)
            for extra in [['--seconds','nan'],['--start','-1'],
                          ['--seconds','2','--melody-source',str(solo)]]:
                out=tmp/'must-not-exist'
                r=subprocess.run([sys.executable,'-I','-B',str(ROOT/'scripts/analyze_reference.py'),
                                  str(source),str(out)]+extra,capture_output=True,text=True, encoding="utf-8", errors="replace")
                self.assertNotEqual(r.returncode,0)
                self.assertFalse((out/'reference.json').exists())


if __name__=='__main__':
    unittest.main()
