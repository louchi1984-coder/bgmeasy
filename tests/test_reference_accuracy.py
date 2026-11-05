"""Accuracy checks on known mixtures, not claims about arbitrary recordings."""
import importlib.util
import json
from pathlib import Path
import tempfile
import subprocess
import sys
import unittest

import soundfile as sf

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('accuracy_reference', ROOT/'scripts/analyze_reference.py')
A = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(A)
import numpy as np
SR=22050

def note(midi, seconds, harmonics=(1,.5,.25,.125), detune=0):
 t=np.arange(round(seconds*SR))/SR
 f=440*2**((midi-69+detune/100)/12)
 y=sum(a*np.sin(2*np.pi*f*(i+1)*t) for i,a in enumerate(harmonics))
 env=np.minimum(t/.015,1)*np.minimum((seconds-t)/.025,1)
 return .15*y*env

def phrase(pitches, step=.7, duration=.55, harmonics=(1,.5,.25,.125)):
 y=np.zeros(round(len(pitches)*step*SR));events=[]
 for i,p in enumerate(pitches):
  x=note(p,duration,harmonics);st=round(i*step*SR);y[st:st+len(x)]+=x
  events.append({'midi':p,'start':i*step,'end':i*step+duration})
 return y,events

def cases():
 out=[]
 for name,pitches,h in [('clean',[60,64,67,65,62],(1,)),('harmonic_lead',[60,64,67,65,62],(1,.8,.65,.45,.3,.2)),('upper_lead',[72,76,74,71,67],(1,.5,.25,.125))]:
  y,e=phrase(pitches,harmonics=h)
  if name!='clean':
   n=note(40,len(y)/SR,(1,.65,.4,.25,.15));y=y+1.7*n[:len(y)]
  out.append((name,y,e))
 # A quiet low melody under a brighter sustained chord. This is intentionally difficult.
 y,e=phrase([60,62,64,67,65],harmonics=(1,.65,.4,.2))
 pad=sum(note(p,len(y)/SR,(1,.4,.2)) for p in [72,76,79])*.7
 out.append(('low_lead_under_pad',y+pad,e))
 return out

def frame_accuracy(notes,truth):
 ok=total=0
 for e in truth:
  for t in np.arange(e['start']+.15,e['end']-.10,.05):
   active=[n for n in notes if n['start_seconds']<=t<n['end_seconds']]
   total+=1;ok+=bool(active and abs(active[0]['midi']-e['midi'])<.5)
 return {'correct':ok,'total':total,'accuracy':ok/total if total else None}


def f1_events_at(notes, truth, t):
    predicted={n['midi'] for n in notes if n['start_seconds']<=t<n['end_seconds']}
    correct=len(predicted & set(truth))
    precision=correct/len(predicted) if predicted else 0
    recall=correct/len(truth)
    return 2*precision*recall/(precision+recall) if precision+recall else 0


def beat_f1(predicted, truth, tolerance=.08):
    # One-to-one greedy nearest matching, including false-positive beats.
    options=sorted((abs(p-t),i,j) for i,p in enumerate(predicted) for j,t in enumerate(truth) if abs(p-t)<=tolerance)
    ps=set();ts=set()
    for _,i,j in options:
        if i not in ps and j not in ts:ps.add(i);ts.add(j)
    return 2*len(ps)/(len(predicted)+len(truth)) if len(predicted)+len(truth) else 0


def changing_clicks():
    times=np.r_[np.arange(.5,8.5,.5),np.arange(8.5,15,.4)]
    y=np.zeros(16*SR)
    for t in times:
        st=round(t*SR)
        y[st:st+300]+=np.random.default_rng(st).normal(0,.2,300)*np.exp(-np.arange(300)/45)
    return y,times


class ReferenceAccuracyTests(unittest.TestCase):
    def test_melody_frame_accuracy_on_four_known_mixtures(self):
        for name,y,truth in cases():
            with self.subTest(case=name):
                result,_=A.pitch_features(y)
                self.assertGreaterEqual(frame_accuracy(result['notes'],truth)['accuracy'],.90)

    def test_held_foreground_is_not_discarded_for_being_stationary(self):
        lead=note(76,3.5,(1,.4,.2))
        accompaniment,_=phrase([60,64,67,60,64])
        result,_=A.pitch_features(lead+accompaniment*.8)
        truth=[{'midi':76,'start':0,'end':3.5}]
        # Mixed-audio regression floor; this is not perfect transcription.
        # The original over-broad stationary-tone penalty scored only 23%.
        self.assertGreaterEqual(frame_accuracy(result['notes'],truth)['accuracy'],.80)

    def test_simultaneous_pitch_precision_and_recall(self):
        signals=[sum(note(p,1.4) for p in notes) for notes in [[48,52,55,72],[45,52,57,74]]]
        activation,_=A.DSP.note_activations(np.concatenate(signals))
        r=A.DSP.polyphonic_events(activation,2.8)
        self.assertGreaterEqual(f1_events_at(r['notes'],[48,52,55,72],.7),.85)
        self.assertGreaterEqual(f1_events_at(r['notes'],[45,52,57,74],2.1),.85)
        self.assertTrue(all(n['instrument_identity']=='unverified' for n in r['notes']))

    def test_rich_harmonics_do_not_turn_minor_chords_into_major(self):
        for label,pitches in [('C',[48,52,55]),('Am',[45,48,52])]:
            y=sum(note(p,3,(1,.9,.75,.6,.45,.35)) for p in pitches)
            r,_=A.analyze(y)
            windows=[w for w in r['harmony']['chord_windows'] if .5<=w['start_seconds']<2]
            self.assertTrue(windows)
            self.assertTrue(all(w['candidates'][0]['label']==label for w in windows),windows)

    def test_repeated_polyphonic_onsets_are_separate(self):
        y,truth=phrase([72]*4,step=.6,duration=.42)
        y+=note(48,len(y)/SR)*1.5
        activation,_=A.DSP.note_activations(y)
        result=A.DSP.polyphonic_events(activation,len(y)/SR)
        events=[e for e in result['notes'] if e['midi']==72]
        self.assertEqual(len(events),4,events)
        for predicted,expected in zip(events,truth):
            self.assertLess(abs(predicted['start_seconds']-expected['start']),.10)

    def test_stereo_balance_and_offset_follow_known_sources(self):
        left=note(60,3);right=note(76,3)
        stereo=np.stack([left+.08*right,.08*left+right],axis=1)
        r,_=A.analyze(stereo,offset=12)
        mid=[e for e in r['voices']['notes'] if e['start_seconds']<13.5<e['end_seconds']]
        self.assertTrue(any(e['midi']==60 and e['stereo_balance']<-.5 for e in mid),mid)
        self.assertTrue(any(e['midi']==76 and e['stereo_balance']>.5 for e in mid),mid)
        self.assertTrue(all(e['start_seconds']>=12 for e in r['voices']['notes']))
        self.assertEqual(r['spatial']['input_channels'],2)
        json.dumps(r,allow_nan=False)

    def test_opposite_phase_stereo_does_not_become_silence(self):
        y=note(69,2)
        r,_=A.analyze(np.stack([y,-y],axis=1))
        self.assertEqual(r['spatial']['analysis_view'],'stronger_channel_due_to_mono_cancellation')
        self.assertTrue(any(e['midi']==69 for e in r['voices']['notes']))

    def test_noise_does_not_invent_polyphonic_lines(self):
        y=np.random.default_rng(7).normal(0,.05,3*SR)
        activation,_=A.DSP.note_activations(y)
        self.assertEqual(A.DSP.polyphonic_events(activation,3)['notes'],[])

    def test_pyin_retains_detuning_without_key_snapping(self):
        result,_=A.pitch_features(note(60,3,detune=28),isolated=True)
        stable=[e for e in result['notes'] if e['start_seconds']<1.5<e['end_seconds']]
        self.assertTrue(stable,result)
        cents=1200*np.log2(stable[0]['median_frequency_hz']/A.librosa.midi_to_hz(60))
        self.assertAlmostEqual(cents,28,delta=7)
        self.assertEqual(result['algorithm'],'pYIN')
        self.assertEqual(stable[0]['midi'],60)

    def test_local_pulse_tracks_a_known_tempo_change(self):
        y,times=changing_clicks();env,_=A.DSP.multiband_onsets(y)
        r=A.rhythm_features(env,A.librosa.onset.onset_detect(onset_envelope=env,sr=SR,hop_length=A.HOP),16)
        local=r['local_pulse']
        self.assertGreaterEqual(beat_f1(local['pulse_times_seconds'],times),.85)
        tempos=local['local_tempo_candidates']
        self.assertTrue(any(t['start_seconds']<=2 and abs(t['pulse_bpm']-120)<5 for t in tempos))
        self.assertTrue(any(10<=t['start_seconds']<=12 and abs(t['pulse_bpm']-150)<5 for t in tempos))
        json.dumps(r,allow_nan=False)
        self.assertIsNone(r['barlines'])

    def test_stereo_cli_exports_voice_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp=Path(tmp);source=tmp/'source.wav';out=tmp/'out'
            sf.write(source,np.stack([note(60,3),note(76,3)],axis=1),SR)
            p=subprocess.run([sys.executable,'-I','-B',str(ROOT/'scripts/analyze_reference.py'),str(source),str(out),'--seconds','3'],capture_output=True,text=True, encoding="utf-8", errors="replace")
            self.assertEqual(p.returncode,0,p.stderr)
            r=json.loads((out/'reference.json').read_text(encoding="utf-8"))
            self.assertEqual(r['source']['audio_channels'],2)
            self.assertEqual(r['schema_version'],2)
            self.assertTrue((out/'voice-notes.csv').is_file())
            self.assertIn('voice-notes.csv',(out/'report.html').read_text(encoding="utf-8"))


if __name__=='__main__':
    unittest.main()
