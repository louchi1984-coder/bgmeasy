"""Fixed-dictionary DSP helpers; no trained weights or external analysis tools.

Project implementation using NumPy, SciPy (BSD) and librosa (ISC).
Thresholds are signal-processing heuristics, not music-quality rules.
"""
import numpy as np
import librosa
from scipy.ndimage import median_filter
from scipy.optimize import nnls
from scipy.signal import find_peaks

SR, HOP, FRAME = 22050, 256, 4096
PITCHES = np.arange(36, 97)


def note_activations(y):
    """Fit a fixed harmonic dictionary, retaining simultaneous pitch candidates."""
    S = np.abs(librosa.stft(y, n_fft=FRAME, hop_length=HOP))
    count = S.shape[1]
    if not np.any(S > 1e-6):
        return np.zeros((len(PITCHES), count)), 0.0
    tuning = float(librosa.estimate_tuning(S=S, sr=SR, n_fft=FRAME))
    freq = librosa.fft_frequencies(sr=SR, n_fft=FRAME)
    width = SR / FRAME * .75
    W = np.zeros((len(freq), len(PITCHES)))
    for k, pitch in enumerate(PITCHES):
        fundamental = librosa.midi_to_hz(pitch + tuning)
        for h in range(1, 9):
            if fundamental*h >= SR/2:
                break
            W[:, k] += np.exp(-.5*((freq-fundamental*h)/width)**2) / h
    # Weight data and dictionary identically, retaining the meaning of NNLS.
    weight = 1 / np.maximum(median_filter(S.mean(axis=1), size=31), S.max()*.002)**.35
    W *= weight[:, None]
    W /= np.maximum(np.linalg.norm(W, axis=0), 1e-12)
    used = np.any(W > .002, axis=1)
    basis = np.ascontiguousarray(W[used])
    # Two-hop solve (~23ms), interpolated to the frontend's existing time grid.
    positions = np.arange(0, count, 2)
    fitted = np.zeros((len(PITCHES), len(positions)))
    for j, t in enumerate(positions):
        v = S[:, t:min(t+2, count)].mean(axis=1)*weight
        fitted[:, j] = nnls(basis, v[used], maxiter=10*len(PITCHES))[0]
    activation = np.stack([np.interp(np.arange(count), positions, row) for row in fitted])
    tonal = librosa.feature.spectral_flatness(S=S)[0] < .15
    energy = np.sqrt(np.mean(S*S, axis=0))
    activation[:, ~tonal | (energy < max(1e-5, energy.max()*.004))] = 0
    return activation, tuning


def predominant_path(activation):
    """A candidate path; no fixed preference for the highest/strongest overtone."""
    notes = PITCHES[PITCHES >= 48]
    a = activation[PITCHES >= 48]
    # A soft articulation cue suppresses stationary chord tones, not a melody identity test.
    low, high = np.percentile(a, [25, 95], axis=1)
    variation = np.clip((high-low)/np.maximum(high, 1e-12), 0, 1)
    stationary = (low > high*.75) & (high > high.max()*.25)
    # A single held foreground tone must not be penalized merely for being held.
    weight = np.ones(len(a))
    if np.count_nonzero(stationary) >= 2:
        weight = .4+.6*variation
    weighted = a*weight[:, None]
    relative = weighted / np.maximum(weighted.max(axis=0, keepdims=True), 1e-12)
    score = np.log(np.maximum(relative, 1e-6))
    transition = np.minimum(np.abs(notes[:, None]-notes[None, :]), 12)*.12
    previous = score[:, 0]
    back = np.zeros(score.shape, dtype=np.int16)
    for t in range(1, score.shape[1]):
        paths = previous[:, None]-transition
        which = paths.argmax(axis=0)
        previous = paths[which, np.arange(len(notes))]+score[:, t]
        back[:, t] = which
    selected = np.zeros(score.shape[1], dtype=int)
    selected[-1] = previous.argmax()
    for t in range(len(selected)-1, 0, -1):
        selected[t-1] = back[selected[t], t]
    return librosa.midi_to_hz(notes[selected]), relative[selected, np.arange(len(selected))], relative


def multiband_onsets(y):
    """Three spectral-flux bands plus their shared onset evidence."""
    S = np.abs(librosa.stft(y, n_fft=FRAME, hop_length=HOP))
    freq = librosa.fft_frequencies(sr=SR, n_fft=FRAME)
    curves = {}
    for name, low, high in [('low', 20, 200), ('middle', 200, 2000), ('high', 2000, SR/2+1)]:
        band = np.log1p(10*S[(freq >= low) & (freq < high)])
        flux = np.maximum(np.diff(band, axis=1, prepend=band[:, :1]), 0).mean(axis=0)
        if flux.max() > 1e-6:
            flux /= flux.max()
        curves[name] = flux
    combined = np.mean(list(curves.values()), axis=0)
    return combined, curves


def local_pulse(env, duration, offset=0):
    """PLP is an alternate beat candidate, never a confirmed downbeat grid."""
    if duration < 2.5 or np.max(env) < 1e-6:
        return {'pulse_times_seconds': [], 'local_tempo_candidates': []}
    win = min(384, max(64, 2**int(np.floor(np.log2(len(env))))))
    pulse = librosa.beat.plp(onset_envelope=env, sr=SR, hop_length=HOP,
                            win_length=win, tempo_min=40, tempo_max=240)
    peaks, _ = find_peaks(pulse, distance=max(1, round(SR/HOP*.20)), prominence=.1)
    times = peaks*HOP/SR
    times = times[times < duration]
    # Local medians only summarize the pulse candidate; do not assert note values.
    candidates = []
    for start in np.arange(0, duration, 2):
        t = times[(times >= start) & (times < start+4)]
        if len(t) >= 3:
            candidates.append({'start_seconds': round(float(offset+start), 5),
                               'end_seconds': round(float(offset+min(start+4, duration)), 5),
                               'pulse_bpm': round(float(60/np.median(np.diff(t))), 3)})
    return {'pulse_times_seconds': [round(offset+float(t), 5) for t in times],
            'local_tempo_candidates': candidates}


def spatial_evidence(stereo, pitch, start, end):
    """Harmonic-band energy balance; not an isolated stem or instrument ID."""
    if stereo is None or stereo.shape[1] != 2:
        return None
    x = stereo[round(start*SR):round(end*SR)]
    if len(x) < 32:
        return None
    spectra = np.abs(np.fft.rfft(x*np.hanning(len(x))[:, None], axis=0))**2
    frequencies = np.fft.rfftfreq(len(x), 1/SR)
    f0 = librosa.midi_to_hz(pitch)
    mask = np.zeros(len(frequencies), dtype=bool)
    for h in range(1, 7):
        mask |= np.abs(frequencies-f0*h) < max(8, f0*h*.012)
    energy = spectra[mask].sum(axis=0)
    return round(float((energy[1]-energy[0])/max(energy.sum(), 1e-12)), 4)


def polyphonic_events(activation, duration, stereo=None, offset=0):
    """Pitch events and provisional monophonic lines, with unknown identities."""
    strongest = activation.max(axis=0)
    events = []
    for k, pitch in enumerate(PITCHES):
        curve = activation[k]
        # Absolute, per-note and per-frame gates; keep weak-but-supported tones.
        active = (curve > max(curve.max()*.12, activation.max()*.025, 1e-6)) & (curve >= strongest*.15)
        changes = np.diff(np.r_[False, active, False].astype(int))
        for first, last in zip(np.flatnonzero(changes == 1), np.flatnonzero(changes == -1)):
            start, end = first*HOP/SR, min(last*HOP/SR, duration)
            if end-start < .09:
                continue
            events.append({'start_seconds': round(float(offset+start), 5), 'end_seconds': round(offset+end, 5),
                           'midi': int(pitch), 'activation_relative': round(float(np.median(curve[first:last]/np.maximum(strongest[first:last], 1e-12))), 4),
                           'stereo_balance': spatial_evidence(stereo, pitch, start, end),
                           'status': 'candidate', 'instrument_identity': 'unverified'})
    events.sort(key=lambda e: (e['start_seconds'], e['midi']))
    lines = []
    for event in events:
        options = []
        for i, line in enumerate(lines):
            last = line[-1]
            gap = event['start_seconds']-last['end_seconds']
            distance = abs(event['midi']-last['midi'])
            pan = abs((event['stereo_balance'] or 0)-(last['stereo_balance'] or 0))
            if -.04 <= gap <= .75 and distance <= 12 and pan <= .65:
                options.append((distance/12+max(0, gap)*.3+pan, i))
        if options:
            line = lines[min(options)[1]]
        else:
            line = [];lines.append(line)
        line.append(event)
    tracks = []
    for i, line in enumerate(lines):
        voice = 'candidate_%02d' % (i+1)
        for e in line:
            e['voice_id'] = voice
        tracks.append({'voice_id': voice, 'median_midi': float(np.median([e['midi'] for e in line])),
                       'event_count': len(line), 'status': 'provisional_pitch_line',
                       'instrument_identity': 'unverified'})
    return {'status': 'candidate' if events else 'insufficient_evidence',
            'pitch_range': ['C2', 'C7'], 'notes': events, 'lines': tracks,
            'uncertainty': ['固定谐波字典NNLS近似多音高，不是训练模型或原始分轨。',
                            '声部ID按时间、音高距离及左右能量启发式连接；同音齐奏、交叉与混响可能串线。',
                            '左右能量来自谐波频带混合，非精确声源声像；没有识别乐器或主旋律身份。',
                            '短于90ms的音、弱内声、非谐和声与同音叠奏可能遗漏；分量数不是乐器数量。']}


def activation_chroma(activation):
    chroma = np.zeros((12, activation.shape[1]));bass = np.zeros_like(chroma)
    for i, pitch in enumerate(PITCHES):
        chroma[pitch % 12] += activation[i]
        if pitch < 55:
            bass[pitch % 12] += activation[i]
    chroma /= np.maximum(chroma.max(axis=0, keepdims=True), 1e-12)
    bass /= np.maximum(bass.max(axis=0, keepdims=True), 1e-12)
    return chroma, bass
