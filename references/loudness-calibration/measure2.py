#!/usr/bin/env python3
"""重测：每个预设先全音域扫描，按"实际有声的音"确定自己的音域，再在音域内取中位数。只读，不改 skill。
扫描：音符 24..96 步长 3，每音 1.2s + 余响，力度 90，CC7=127，CC11=127。
音域：峰值 >= 该预设最大峰值 - 18 dB 的音。
指标(取音域内中位数)：peak、rms1(音头起 1.0s 的 RMS，对应约一拍的音)、sus(0.5~1.0s RMS)。
鼓组(bank128)：底鼓36/军鼓38/踩镲42 各一次，取 peak 与 rms0.5。
"""
import json, os, subprocess, sys, tempfile, csv, collections
import numpy as np, soundfile as sf, mido
S = os.path.expanduser('~/.claude/skills/bgmeasy/soundfonts')
cat = json.load(open(S + '/catalog.json'))['entries']
SR = 22050; SLOT = 1.8; HOLD = 1.2; SPT = 1/960  # 120bpm: 960 tick/s
NOTES = list(range(24, 97, 3)); DR = [36, 38, 42]
db = lambda z: 20*np.log10(np.sqrt(np.mean(z**2)) + 1e-9)
pk = lambda z: 20*np.log10(np.abs(z).max() + 1e-9)
by = collections.defaultdict(list)
for e in cat:
    if e.get('file', '').endswith('.sf2') and e.get('kind') in ('melodic', 'drums'): by[e['file']].append(e)
rows = []
def run(f, batch):
    m = mido.MidiFile(type=1, ticks_per_beat=480); tr = mido.MidiTrack(); m.tracks.append(tr); ev = []; plan = []; t = 0.0
    for e in batch:
        d128 = e['kind'] == 'drums' and e['bank'] >= 128
        ch = 9 if d128 else 0; notes = DR if d128 else NOTES
        ev.append((int(t/SPT), mido.Message('control_change', channel=ch, control=0, value=min(e['bank'], 127) if not d128 else 0)))
        ev.append((int(t/SPT), mido.Message('program_change', channel=ch, program=e['program'])))
        for c in (7, 11): ev.append((int(t/SPT), mido.Message('control_change', channel=ch, control=c, value=127)))
        t += 0.2
        for n in notes:
            ev.append((int(t/SPT), mido.Message('note_on', channel=ch, note=n, velocity=90)))
            ev.append((int((t + (HOLD if not d128 else 0.6))/SPT), mido.Message('note_off', channel=ch, note=n, velocity=0)))
            plan.append((e, n, t, d128)); t += SLOT
    last = 0
    for tick, msg in sorted(ev, key=lambda x: x[0]): tr.append(msg.copy(time=tick-last)); last = tick
    d = tempfile.mkdtemp(); m.save(d+'/a.mid')
    subprocess.run(['fluidsynth','-ni','-q','-g','1.0','-r',str(SR),'-F',d+'/a.wav',os.path.join(S,f),d+'/a.mid'], capture_output=True)
    x, sr = sf.read(d+'/a.wav', dtype='float32'); x = x.mean(axis=1) if x.ndim > 1 else x
    res = collections.defaultdict(list)
    for e, n, t0, d128 in plan:
        a = int(t0*sr); seg = x[a:a+int(1.5*sr)]
        if len(seg) < sr//2: continue
        if d128: res[e['id']].append((n, pk(seg), db(seg[:sr//2]), db(seg[:sr//2])))
        else: res[e['id']].append((n, pk(seg), db(seg[:sr]), db(seg[sr//2:sr])))
    os.remove(d+'/a.wav')
    return res
for f, es in by.items():
    for i in range(0, len(es), 25):
        batch = es[i:i+25]; res = run(f, batch)
        for e in batch:
            r = res.get(e['id'], [])
            if not r: continue
            if e['kind'] == 'drums' and e['bank'] >= 128:
                rows.append(dict(id=e['id'], name=e['name'], kind='drums128', lo='', hi='', n_in=len(r), peak=round(np.median([a[1] for a in r]),1), rms1=round(np.median([a[2] for a in r]),1), sus=''))
                continue
            mx = max(a[1] for a in r); ok = [a for a in r if a[1] >= mx - 18 and a[1] > -100]
            if not ok: rows.append(dict(id=e['id'], name=e['name'], kind=e['kind'], lo='', hi='', n_in=0, peak=-180, rms1=-180, sus=-180)); continue
            rows.append(dict(id=e['id'], name=e['name'], kind=e['kind'], lo=min(a[0] for a in ok), hi=max(a[0] for a in ok), n_in=len(ok),
                             peak=round(np.median([a[1] for a in ok]),1), rms1=round(np.median([a[2] for a in ok]),1), sus=round(np.median([a[3] for a in ok]),1)))
    print(f, 'ok', flush=True)
ref = next(r for r in rows if r['id'] == 'generaluser-gs:0:0')
for r in rows:
    r['rel_rms1_vs_piano'] = round(r['rms1'] - ref['rms1'], 1) if r['n_in'] else ''
    r['rel_peak_vs_piano'] = round(r['peak'] - ref['peak'], 1) if r['n_in'] else ''
with open('preset_loudness_v2.csv', 'w', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
print('rows', len(rows))
