#!/usr/bin/env python3
"""Offline reference-audio evidence: classical DSP only, no learned models.

python3 -I scripts/analyze_reference.py INPUT OUTPUT_DIR [--start 0 --seconds 120]
    [--melody-source ALIGNED_SOLO.wav] [--bpm PULSE_BPM] [--meter 6/8]
"""
import argparse
import csv
import hashlib
import html
import json
from pathlib import Path
import re
import subprocess
import sys

if __name__ == "__main__" and sys.platform == "win32":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")

import librosa
import numpy as np
from scipy.ndimage import median_filter
from scipy.signal import correlate, find_peaks

sys.path.insert(0, str(Path(__file__).resolve().parent))
import reference_dsp as DSP
import localization as I18N

SR, HOP, FRAME = 22050, 256, 4096
BLOCK = round(.5 * SR / HOP) * HOP / SR
NAMES = ['C', 'C#', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B']
MAJOR = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
MINOR = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
QUALITIES = [('', [0, 4, 7]), ('m', [0, 3, 7]), ('dim', [0, 3, 6]),
             ('sus2', [0, 2, 7]), ('sus4', [0, 5, 7]), ('7', [0, 4, 7, 10]),
             ('maj7', [0, 4, 7, 11]), ('m7', [0, 3, 7, 10]), ('m7b5', [0, 3, 6, 10])]
FILES = ['reference.json', 'melody-notes.csv', 'pitch-contour.csv', 'analysis.png', 'report.html', 'voice-notes.csv']


def rounded(value):
    return round(float(value), 5)


def unit_columns(x):
    return x / np.maximum(np.linalg.norm(x, axis=0, keepdims=True), 1e-12)


def decode(path, start=0, seconds=120, stereo=False):
    path = Path(path).expanduser().resolve()
    if not path.is_file():
        raise ValueError(f'不是本地音频文件: {path}')
    cmd = ['ffmpeg', '-v', 'error', '-protocol_whitelist', 'file,pipe',
           '-ss', str(start), '-i', str(path), '-t', str(seconds),
           '-vn', '-ac', '2' if stereo else '1', '-ar', str(SR), '-f', 'f32le', '-']
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode:
        raise ValueError('解码失败: ' + r.stderr.decode(errors='replace')[-800:])
    y = np.frombuffer(r.stdout, dtype='<f4').copy()
    if stereo:
        y = y.reshape(-1, 2)
    if len(y) < SR / 4 or not np.isfinite(y).all():
        raise ValueError('选定范围不足0.25秒，或包含非有限音频值')
    return y


def source_info(path):
    path = Path(path).expanduser().resolve()
    r = subprocess.run(['ffprobe', '-v', 'error', '-protocol_whitelist', 'file,pipe',
                        '-show_entries', 'format=duration:stream=codec_type,channels',
                        '-of', 'json', str(path)], capture_output=True, text=True, check=True, encoding="utf-8", errors="replace")
    metadata = json.loads(r.stdout)
    duration = metadata.get('format', {}).get('duration')
    channels = next((v.get('channels') for v in metadata.get('streams', []) if v.get('codec_type') == 'audio'), None)
    digest = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024*1024), b''):
            digest.update(chunk)
    return {'path': str(path), 'sha256': digest.hexdigest(),
            'duration_seconds': float(duration) if duration not in (None, 'N/A') else None,
            'audio_channels': channels}


def onset_features(y):
    env = librosa.onset.onset_strength(y=y, sr=SR, hop_length=HOP, n_fft=FRAME)
    if np.max(np.abs(y)) < 1e-6 or np.max(env) < 1e-6:
        return np.zeros_like(env), np.array([], dtype=int)
    peaks = librosa.onset.onset_detect(onset_envelope=env, sr=SR, hop_length=HOP)
    return env, peaks


def rhythm_features(env, onsets, duration, bpm=None, meter=None, offset=0):
    candidates = []
    enough = len(onsets) >= 3 and duration >= 2.5 and np.std(env) > 1e-6
    if enough:
        ac = correlate(env, env, mode='full', method='fft')[len(env)-1:]
        ac /= max(float(ac[0]), 1e-12)
        peaks, _ = find_peaks(ac)
        peaks = [p for p in peaks if p and ac[p] >= .12 and 40 <= 60 * SR / (HOP * p) <= 240]
        for p in sorted(peaks, key=lambda p: ac[p], reverse=True)[:4]:
            candidates.append({'pulse_bpm': rounded(60 * SR / (HOP * p)),
                               'autocorrelation_score': rounded(ac[p])})
    chosen = bpm if bpm is not None else (candidates[0]['pulse_bpm'] if candidates else None)
    beats = []
    if enough and chosen is not None:
        _, frames = librosa.beat.beat_track(onset_envelope=env, sr=SR, hop_length=HOP,
                                          bpm=chosen, trim=True)
        beats = [rounded(offset + f * HOP / SR) for f in frames if f * HOP / SR < duration]
    return {'status': 'candidate' if enough and chosen else 'insufficient_evidence',
            'tempo_candidates': candidates, 'pulse_bpm_used_for_grid': chosen,
            'tempo_source': 'user' if bpm is not None else 'autocorrelation_candidate',
            'pulse_times_seconds': beats,
            'onsets_seconds': [rounded(offset + f * HOP / SR) for f in onsets if f * HOP / SR < duration],
            'meter': {'value': meter, 'source': 'user' if meter else 'not_estimated'},
            'barlines': None,
            'local_pulse': DSP.local_pulse(env, duration, offset),
            'uncertainty': ['速度可能有半速/倍速及复合拍细分歧义；未自动推断拍号或小节起点。',
                            '--bpm表示分析脉冲BPM；6/8可指定附点四分脉冲，不自动当成四分音符。',
                            '脉冲网格是估计，不能证明实际重音或节奏质量。']}


def periodicity(frames, f0):
    """Normalized autocorrelation at each YIN period; not a trained confidence model."""
    out = np.zeros(len(f0))
    rows = np.arange(FRAME)[:, None]
    for start in range(0, len(f0), 256):
        x = frames[:, start:start+256].astype(np.float64)
        x = x - x.mean(axis=0)
        lag = np.rint(SR / np.maximum(f0[start:start+x.shape[1]], 1)).astype(int)
        indices = rows + lag[None, :]
        valid = indices < FRAME
        shifted = np.take_along_axis(x, np.clip(indices, 0, FRAME-1), axis=0)
        a, b = x * valid, shifted * valid
        denominator = np.sqrt(np.sum(a*a, axis=0) * np.sum(b*b, axis=0))
        out[start:start+x.shape[1]] = np.sum(a*b, axis=0) / np.maximum(denominator, 1e-12)
    return np.clip(out, 0, 1)


def mixed_pitch_candidates(y, evidence=None):
    """Fixed-dictionary simultaneous pitches, followed by a continuity path."""
    activation = DSP.note_activations(y)[0] if evidence is None else evidence
    f0, support, relative = DSP.predominant_path(activation)
    tonal = activation.max(axis=0) > 1e-6
    return f0, support, tonal, relative


def pitch_features(y, isolated=False, offset=0, evidence=None):
    duration = len(y) / SR
    rms = librosa.feature.rms(y=y, frame_length=FRAME, hop_length=HOP)[0]
    count = len(rms)
    f0 = np.zeros(count)
    quality = np.zeros(count)
    support = np.zeros(count)
    alternatives = None
    valid = np.zeros(count, dtype=bool)
    if np.max(np.abs(y)) >= 1e-6:
        if isolated:
            f0, voiced, _ = librosa.pyin(y, fmin=librosa.note_to_hz('C2'), fmax=librosa.note_to_hz('C7'),
                                        sr=SR, frame_length=FRAME, hop_length=HOP, fill_na=0)
            f0 = np.nan_to_num(f0)
        else:
            f0, support, tonal, alternatives = mixed_pitch_candidates(y, evidence)
        frames = librosa.util.frame(np.pad(y, (FRAME//2, FRAME//2)),
                                   frame_length=FRAME, hop_length=HOP)
        quality = periodicity(frames, f0)
        gate = max(5e-5, float(np.max(rms)) * .004)
        accepted = (voiced & (quality >= .55)) if isolated else (tonal & (support >= .55))
        valid = (rms > gate) & accepted & np.isfinite(f0)
    midi = np.zeros(count)
    midi[valid] = librosa.hz_to_midi(f0[valid])
    quantized = median_filter(np.rint(midi).astype(int), size=3)
    _, attacks = onset_features(y)
    attack_set = set(int(f) for f in attacks)
    notes = []
    first = 0
    while first < count:
        if not valid[first]:
            first += 1
            continue
        last = first + 1
        while last < count and valid[last] and quantized[last] == quantized[first]:
            if last in attack_set and (last-first) * HOP / SR >= .12:
                break
            last += 1
        start_t, end_t = first*HOP/SR, min(last*HOP/SR, duration)
        if end_t-start_t >= .06:
            pitch = int(quantized[first])
            other = []
            margin = None
            if alternatives is not None:
                mean = alternatives[:, first:last].mean(axis=1)
                order = np.argsort(mean)[::-1][:3]
                margin = float(mean[order[0]]-mean[order[1]])
                for i in order:
                    p = int(i+48)
                    other.append({'midi': p, 'note': NAMES[p % 12]+str(p//12-1),
                                  'relative_salience': rounded(mean[i])})
            notes.append({'start_seconds': rounded(offset+start_t), 'end_seconds': rounded(offset+end_t),
                          'midi': pitch, 'note': NAMES[pitch % 12] + str(pitch//12-1),
                          'median_frequency_hz': rounded(np.median(f0[first:last])),
                          'periodicity_score': rounded(np.median(quality[first:last])),
                          'spectral_support_score': rounded(np.median(support[first:last])) if not isolated else None,
                          'pitch_spread_cents': rounded(np.std(midi[first:last])*100) if isolated else None,
                          'alternative_margin': rounded(margin) if margin is not None else None,
                          'alternate_pitch_candidates': other,
                          'status': 'ambiguous' if margin is not None and margin < .10 else 'candidate',
                          'melody_identity': 'unverified'})
        first = last
    result = {'status': 'candidate' if notes else 'insufficient_evidence',
              'source_mode': 'provided_solo_not_verified' if isolated else 'mixed_audio',
              'algorithm': 'pYIN' if isolated else 'fixed_harmonic_nnls_and_continuity',
              'frequency_resolution': 'continuous_estimate' if isolated else 'semitone_grid_not_vibrato_measurement',
              'pitch_range': ['C2' if isolated else 'C3', 'C7'], 'notes': notes,
              'accepted_frame_fraction': rounded(np.mean(valid)),
              'uncertainty': ['独奏路径用pYIN；混音路径用固定谐波字典NNLS与连续性，仍可能跟随伴奏或泛音，不自动认定主旋律。',
                              '混音主旋律路径仍只搜索C3–C7；多音高候选覆盖C2–C7。不按高音优先认定旋律，弱主奏仍可能被伴奏盖住；多条稳定音并存时的变化软权重也可能压低持续主奏。',
                              '混音路径用半音格，不据其轨迹报告揉弦深度、音分抖动或自然感。',
                              '周期性、相对显著度及spectral_support_score都不是正确率或旋律身份概率。',
                              '短于60ms的稳定段不生成音符；装饰音、重复音、滑音及起止点可能漏检或拆错。',
                              '独奏搜索C2–C7；混音主线搜索C3–C7；区外旋律不会可靠转写。独奏文件也未被认证为单声部。']}
    return result, (f0, quality, valid)


def chord_templates():
    templates, labels = [], []
    for root in range(12):
        for suffix, intervals in QUALITIES:
            t = np.zeros(12)
            t[[(root+i) % 12 for i in intervals]] = 1
            templates.append(t / np.linalg.norm(t))
            labels.append(NAMES[root] + suffix)
    return np.asarray(templates), labels


def harmonic_features(chroma, harmonic_rms, duration, offset=0):
    templates, labels = chord_templates()
    frames_per_window = max(1, round(BLOCK * SR / HOP))
    sequence, observed = [], []
    for first in range(0, chroma.shape[1], frames_per_window):
        last = min(first+frames_per_window, chroma.shape[1])
        start_t, end_t = first*HOP/SR, min(last*HOP/SR, duration)
        if end_t <= start_t:
            continue
        v = chroma[:, first:last].mean(axis=1)
        signal = float(harmonic_rms[first:last].mean())
        active = signal > 1e-5 and np.linalg.norm(v) > 1e-5 and np.std(v) > .015
        candidates = []
        if active:
            fit = templates @ (v / np.linalg.norm(v))
            order = np.argsort(fit)[::-1][:3]
            candidates = [{'label': labels[i], 'template_cosine_score': rounded(fit[i])} for i in order]
            margin = float(fit[order[0]] - fit[order[1]])
            observed.append(v)
        else:
            margin = None
        sequence.append({'start_seconds': rounded(offset+start_t), 'end_seconds': rounded(offset+end_t),
                         'status': 'ambiguous' if active and margin < .08 else 'candidate' if active else 'unknown',
                         'candidates': candidates, 'top_two_margin': rounded(margin) if margin is not None else None})
    key_candidates = []
    if observed:
        mean = np.mean(observed, axis=0)
        if np.std(mean) > 1e-5:
            for root in range(12):
                for mode, profile in [('major', MAJOR), ('minor', MINOR)]:
                    key_candidates.append({'key': NAMES[root]+' '+mode,
                                           'profile_correlation': rounded(np.corrcoef(mean, np.roll(profile, root))[0, 1])})
            key_candidates.sort(key=lambda x: x['profile_correlation'], reverse=True)
    return {'status': 'candidate' if observed else 'insufficient_evidence',
            'window_seconds_approx': BLOCK, 'chord_windows': sequence,
            'key_candidates': key_candidates[:3],
            'uncertainty': ['和弦是固定时间窗色度与人工音程模板的匹配候选，不假设四拍小节。',
                            '余音、旋律、泛音及多声部会改变色度；转位、低音和扩展和弦未被可靠识别。',
                            '相似度、相关系数与候选间距未经正确率校准；单和弦或短片段不足以唯一确定调性。']}


def smooth_chord_candidates(harmony):
    """Fixed transition penalty; unknown windows break the path, never fill them."""
    windows = harmony['chord_windows']
    _, labels = chord_templates()
    first = 0
    while first < len(windows):
        if not windows[first]['candidates']:
            windows[first]['smoothed_label_candidate'] = None
            first += 1
            continue
        last = first+1
        while last < len(windows) and windows[last]['candidates']:
            last += 1
        score = np.full((last-first, len(labels)), -2.)
        for t, window in enumerate(windows[first:last]):
            for candidate in window['candidates']:
                score[t, labels.index(candidate['label'])] = candidate['template_cosine_score']
        transition = .12*(1-np.eye(len(labels)))
        previous = score[0];back = []
        for row in score[1:]:
            paths = previous[:, None]-transition
            which = paths.argmax(axis=0);back.append(which)
            previous = paths[which, np.arange(len(labels))]+row
        selected = [int(previous.argmax())]
        for which in reversed(back):
            selected.append(int(which[selected[-1]]))
        selected.reverse()
        for window, index in zip(windows[first:last], selected):
            window['smoothed_label_candidate'] = labels[index]
        first = last


def analysis_view(y):
    """Preserve stereo evidence and avoid losing anti-phase audio in the mean."""
    y = np.asarray(y)
    if y.ndim == 1:
        return y, None, 'mono_input'
    if y.ndim != 2 or y.shape[1] != 2:
        raise ValueError('分析输入应为单声道数组或(samples, 2)立体声数组')
    mono = y.mean(axis=1)
    energies = np.mean(y*y, axis=0)
    if np.mean(mono*mono) < max(energies.max()*.01, 1e-15) and energies.max() > 1e-12:
        selected = int(energies.argmax())
        return y[:, selected], y, 'stronger_channel_due_to_mono_cancellation'
    return mono, y, 'stereo_mean_with_original_channels_retained'


def block_means(x):
    step = max(1, round(BLOCK * SR / HOP))
    return np.stack([x[:, i:i+step].mean(axis=1) for i in range(0, x.shape[1], step)], axis=1)


def structural_features(chroma, mfcc, duration, offset=0):
    c, m = block_means(chroma), block_means(mfcc)
    m = (m - np.mean(m, axis=1, keepdims=True)) / np.maximum(np.std(m, axis=1, keepdims=True), 1)
    features = unit_columns(np.vstack([.7*unit_columns(c), .3*unit_columns(m)]))
    similarity = np.clip(features.T @ features, 0, 1)
    novelty = np.zeros(features.shape[1])
    width = 3  # Compare 1.5 seconds on each side; an analysis scale, not a phrase-length rule.
    for i in range(width, len(novelty)-width):
        ll = similarity[i-width:i, i-width:i].mean()
        rr = similarity[i:i+width, i:i+width].mean()
        lr = similarity[i-width:i, i:i+width].mean()
        novelty[i] = max(0, float((ll+rr)/2-lr))
    peaks, _ = find_peaks(novelty, distance=4, prominence=max(.08, float(np.std(novelty))*.5))
    if duration < 6 or np.linalg.norm(chroma) < 1e-6:
        peaks = np.array([], dtype=int)
    bounds = [int(p) for p in peaks if p*BLOCK < duration-1]
    cuts = [0.0] + [p*BLOCK for p in bounds] + [duration]
    segments = [{'start_seconds': rounded(offset+a), 'end_seconds': rounded(offset+b),
                 'status': 'candidate_extent'} for a, b in zip(cuts, cuts[1:])]
    repeated = []
    for a in range(len(segments)):
        for b in range(a+1, len(segments)):
            aa, ab = cuts[a:a+2]
            ba, bb = cuts[b:b+2]
            if min(ab-aa, bb-ba) < 1 or not .8 <= (ab-aa)/(bb-ba) <= 1.25:
                continue
            pieces = []
            for start, end in [(aa, ab), (ba, bb)]:
                piece = features[:, int(start/BLOCK):max(int(start/BLOCK)+1, int(end/BLOCK))]
                pieces.append(unit_columns(np.stack([np.interp(np.linspace(0, 1, 32), np.linspace(0, 1, piece.shape[1]), row) for row in piece])))
            value = float(np.sum(pieces[0]*pieces[1], axis=0).mean())
            if value >= .90:
                repeated.append({'segment_indices': [a, b], 'feature_similarity': rounded(value),
                                 'status': 'possible_recurrence_not_confirmed_theme'})
    repeated.sort(key=lambda x: x['feature_similarity'], reverse=True)
    result = {'status': 'candidate' if bounds else 'no_strong_boundary_found',
              'boundaries': [{'time_seconds': rounded(offset+p*BLOCK), 'contrast_score': rounded(novelty[p]),
                              'status': 'candidate'} for p in bounds],
              'segments': segments, 'similar_segment_candidates': repeated[:12],
              'resolution_seconds_approx': BLOCK,
              'uncertainty': ['边界来自色度/音色自相似的局部变化；不是已确认乐句、主歌、副歌或高潮。',
                              '未检出边界不等于没有结构；相似片段可能只共享和弦或音色，不保证同一主题。',
                              '0.5秒分辨率、对比窗口和阈值是项目分析参数，不是乐理质量门槛。']}
    return result, (similarity, novelty)


def analyze(y, melody=None, bpm=None, meter=None, offset=0):
    y, stereo, view = analysis_view(y)
    if melody is not None:
        melody = analysis_view(melody)[0]
    duration = len(y) / SR
    S = np.abs(librosa.stft(y, n_fft=FRAME, hop_length=HOP))
    H, _ = librosa.decompose.hpss(S)
    harmonic_rms = np.sqrt(np.mean(H*H, axis=0))
    activation, tuning = DSP.note_activations(y)
    chroma, bass_chroma = DSP.activation_chroma(activation)
    mel = librosa.feature.melspectrogram(S=S*S, sr=SR, n_fft=FRAME, n_mels=40)
    mfcc = librosa.feature.mfcc(S=librosa.power_to_db(mel, ref=np.max), n_mfcc=9)[1:]
    env, bands = DSP.multiband_onsets(y)
    onsets = librosa.onset.onset_detect(onset_envelope=env, sr=SR, hop_length=HOP) if env.max() > 1e-6 else np.array([], dtype=int)
    pitches, contour = pitch_features(y if melody is None else melody, melody is not None, offset, activation)
    harmony = harmonic_features(chroma, harmonic_rms, duration, offset)
    smooth_chord_candidates(harmony)
    harmony['front_end'] = 'fixed_harmonic_dictionary_nnls'
    harmony['tuning_offset_semitones_candidate'] = rounded(tuning)
    harmony['bass_chroma_windows'] = [
        {'time_seconds': rounded(offset+i*BLOCK), 'pitch_class_energy': [rounded(v) for v in row]}
        for i, row in enumerate(block_means(bass_chroma).T)]
    harmony['uncertainty'].append('NNLS字典假设谐和泛音，音色不匹配与同音叠奏可误识别；平滑标签仍是候选，低音色度不认证转位。')
    rhythm = rhythm_features(env, onsets, duration, bpm, meter, offset)
    rhythm['onset_bands'] = {
        name: [rounded(offset+i*HOP/SR) for i in librosa.onset.onset_detect(onset_envelope=curve, sr=SR, hop_length=HOP) if i*HOP/SR < duration]
        if curve.max() > 1e-6 else [] for name, curve in bands.items()}
    rhythm['uncertainty'].append('PLP局部脉冲与全局动态规划是并列候选，变速、弱拍和半速歧义仍须复核。')
    structure, matrices = structural_features(chroma, mfcc, duration, offset)
    voices = DSP.polyphonic_events(activation, duration, stereo, offset)
    report = {'schema_version': 2, 'method': 'classical_signal_processing',
              'uses_learned_models': False, 'listening_status': 'not_listened',
              'analysis_range': {'start_seconds': offset, 'end_seconds': rounded(offset+duration),
                                 'duration_seconds': rounded(duration), 'sample_rate': SR},
              'spatial': {'input_channels': 1 if stereo is None else 2, 'analysis_view': view,
                          'scope': '保留左右谐波能量作为分组线索，不是源分离或乐器身份识别。'},
              'rhythm': rhythm, 'melody': pitches, 'harmony': harmony, 'structure': structure,
              'voices': voices,
              'limitations': ['所有识别结果是候选；未识别乐器身份、情绪、音色自然感或好听程度。',
                              '没有训练模型、权重下载或API调用；多音高分组不是原始分轨或原谱。',
                              '没有按推测的调性吸附音符；不确定处保留候选或unknown。']}
    return report, {'wave': y, 'onset_envelope': env, 'pitch': contour, 'chroma': chroma,
                    'similarity': matrices[0], 'novelty': matrices[1]}


def write_outputs(out, report, data, lang='zh'):
    translate_text = lambda message: I18N.translate(message, lang)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.collections import LineCollection
    offset = report['analysis_range']['start_seconds']
    duration = report['analysis_range']['duration_seconds']
    (out/'reference.json').write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding="utf-8")
    fields = ['start_seconds', 'end_seconds', 'midi', 'note', 'median_frequency_hz',
              'periodicity_score', 'spectral_support_score', 'pitch_spread_cents', 'alternative_margin',
              'status', 'melody_identity', 'alternate_pitch_candidates']
    with (out/'melody-notes.csv').open('w', newline='', encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(report['melody']['notes'])
    voice_fields = ['voice_id', 'start_seconds', 'end_seconds', 'midi', 'activation_relative', 'stereo_balance', 'status', 'instrument_identity']
    with (out/'voice-notes.csv').open('w', newline='', encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=voice_fields)
        writer.writeheader()
        writer.writerows(report['voices']['notes'])
    f0, quality, valid = data['pitch']
    with (out/'pitch-contour.csv').open('w', newline='', encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(['time_seconds', 'f0_hz', 'periodicity_score', 'accepted_pitch_candidate'])
        for i in range(len(f0)):
            if i*HOP/SR > duration:
                break
            writer.writerow([rounded(offset+i*HOP/SR), rounded(f0[i]) if valid[i] else '', rounded(quality[i]), int(valid[i])])
    chart_lang, chart_font = I18N.plot_language(lang, ['Waveform and estimated onsets', 'Amplitude', 'Candidate', 'Close alternatives / ambiguous', 'Pitch / note candidates (mixed audio is NOT a verified melody)', 'MIDI pitch', 'Simultaneous pitch candidates / provisional lines (NOT instrument stems)', 'Harmonic pitch-class energy', 'Local feature contrast and candidate boundaries', 'Contrast', 'Feature self-similarity (not proof of thematic identity)', 'Source time (s)'])
    chart = lambda message: I18N.translate(message, chart_lang)
    fig, axes = plt.subplots(6, 1, figsize=(12, 14), constrained_layout=True,
                             gridspec_kw={'height_ratios': [1, 1.2, 1.4, 1.1, 1, 2]})
    wave = data['wave']; stride = max(1, len(wave)//6000)
    axes[0].plot(offset+np.arange(0, len(wave), stride)/SR, wave[::stride], linewidth=.6)
    for t in report['rhythm']['onsets_seconds']:
        axes[0].axvline(t, alpha=.22, color='tab:orange', linewidth=.7)
    axes[0].set(title=chart('Waveform and estimated onsets'), ylabel=chart('Amplitude'))
    for note in report['melody']['notes']:
        axes[1].plot([note['start_seconds'], note['end_seconds']], [note['midi']]*2,
                     color='tab:orange' if note['status']=='ambiguous' else 'tab:blue', linewidth=2)
    axes[1].plot([], [], color='tab:blue', label=chart('Candidate'))
    axes[1].plot([], [], color='tab:orange', label=chart('Close alternatives / ambiguous'))
    axes[1].legend(loc='upper right', fontsize=8)
    axes[1].set(title=chart('Pitch / note candidates (mixed audio is NOT a verified melody)'), ylabel=chart('MIDI pitch'))
    voice_notes = report['voices']['notes']
    if voice_notes:
        segments = [[(n['start_seconds'], n['midi']), (n['end_seconds'], n['midi'])] for n in voice_notes]
        colors = [plt.get_cmap('tab20')(int(n['voice_id'].split('_')[-1]) % 20) for n in voice_notes]
        axes[2].add_collection(LineCollection(segments, colors=colors, linewidths=1.5, alpha=.7))
        axes[2].autoscale_view()
    axes[2].set(title=chart('Simultaneous pitch candidates / provisional lines (NOT instrument stems)'), ylabel=chart('MIDI pitch'))
    axes[3].imshow(data['chroma'], origin='lower', aspect='auto', extent=[offset, offset+duration, -.5, 11.5])
    axes[3].set(yticks=range(12), yticklabels=NAMES, title=chart('Harmonic pitch-class energy'))
    novelty = data['novelty']
    axes[4].plot(offset+np.arange(len(novelty))*BLOCK, novelty, color='tab:purple')
    for boundary in report['structure']['boundaries']:
        for ax in axes[:5]:ax.axvline(boundary['time_seconds'], color='tab:red', alpha=.4, linestyle='--')
    axes[4].set(title=chart('Local feature contrast and candidate boundaries'), ylabel=chart('Contrast'))
    axes[5].imshow(data['similarity'], origin='lower', aspect='equal',
                   extent=[offset, offset+duration, offset, offset+duration], vmin=0, vmax=1)
    axes[5].set(title=chart('Feature self-similarity (not proof of thematic identity)'), ylabel=chart('Source time (s)'))
    for ax in axes:
        ax.set_xlabel(chart('Source time (s)'))
        ax.set_xlim(offset, offset+duration)
    if chart_font:
        from matplotlib.text import Text
        for text in fig.findobj(Text):
            properties = text.get_fontproperties().copy()
            properties.set_file(chart_font)
            text.set_fontproperties(properties)
    fig.savefig(out/'analysis.png', dpi=140)
    plt.close(fig)
    esc = lambda value: html.escape(str(value))
    def display(value):
        # Only generated analysis sections go through this view; user paths stay literal.
        if isinstance(value, dict): return {k: display(v) for k, v in value.items()}
        if isinstance(value, list): return [display(v) for v in value]
        return translate_text(value) if isinstance(value, str) else value
    rows = ''.join('<tr>'+''.join('<td>'+esc(display(n[k]))+'</td>' for k in fields)+'</tr>' for n in report['melody']['notes'][:200])
    chords = ''.join('<tr><td>'+esc(w['start_seconds'])+'–'+esc(w['end_seconds'])+'</td><td>'+esc(translate_text(w['status']))+'</td><td>'+esc(', '.join(c['label']+' '+str(c['template_cosine_score']) for c in w['candidates']))+'</td></tr>' for w in report['harmony']['chord_windows'])
    warnings = ''.join('<li>'+esc(translate_text(t))+'</li>' for t in report['limitations'] + [t for section in ['melody', 'rhythm', 'harmony', 'structure', 'voices'] for t in report[section]['uncertainty']])
    page = f'''<!doctype html><html lang="{lang}"><meta charset="utf-8"><title>{translate_text('参考曲纯算法分析')}</title>
<style>body{{font:16px/1.6 system-ui;margin:32px auto;max-width:1200px;padding:0 20px;color:#243047}}img{{width:100%}}table{{border-collapse:collapse;font-size:13px}}td,th{{border:1px solid #ccd4df;padding:5px}}.scroll{{overflow:auto}}</style>
<h1>{translate_text('参考曲分析 · 候选证据')}</h1><p>{translate_text('来源')}：{esc(report['source']['path'])}<br>{translate_text('分析范围')}：{offset}–{offset+duration:.3f} s。{translate_text('纯算法、无学习模型；未核听。')}</p>
<p>{translate_text('这份报告提供待复核的音高、节奏、和声和结构线索，不是原谱、乐器识别或审美评分。')}</p>
<p><a href="reference.json">{translate_text('完整 JSON')}</a> · <a href="melody-notes.csv">{translate_text('音符候选 CSV')}</a> · <a href="pitch-contour.csv">{translate_text('音高轨迹 CSV')}</a> · <a href="voice-notes.csv">{translate_text('多音高声部候选 CSV')}</a></p>
<p data-chart-language="{chart_lang}">{translate_text('图中文字使用本地字体；缺少所需字体时，图表回退为英文，正文保留所选语言。')}</p>
<img src="analysis.png" alt="{translate_text('音频、主线/多音高候选、色度、自相似和结构变化图')}">
<h2>{translate_text('节奏')}</h2><pre>{esc(json.dumps(display(report['rhythm']),ensure_ascii=False,indent=2))}</pre>
<h2>{translate_text('立体声与声部候选（不是乐器分轨）')}</h2><pre>{esc(json.dumps(display({"spatial": report["spatial"], "lines": report["voices"]["lines"]}),ensure_ascii=False,indent=2))}</pre>
<h2>{translate_text('调性候选')}</h2><pre>{esc(json.dumps(display(report['harmony']['key_candidates']),ensure_ascii=False,indent=2))}</pre>
<h2>{translate_text('结构候选')}</h2><pre>{esc(json.dumps(display(report['structure']),ensure_ascii=False,indent=2))}</pre>
<h2>{translate_text('音符候选（页面最多显示200条，CSV/JSON包含全部）')}</h2><div class="scroll"><table><tr>{''.join('<th>'+esc(translate_text(k))+'</th>' for k in fields)}</tr>{rows}</table></div>
<h2>{translate_text('和弦窗口 · 余音和扩展和弦可能歧义')}</h2><table><tr><th>{translate_text('原曲秒数')}</th><th>{translate_text('状态')}</th><th>{translate_text('前三候选及非校准匹配分')}</th></tr>{chords}</table>
<h2>{translate_text('不确定性与限制')}</h2><ul>{warnings}</ul></html>'''
    (out/'report.html').write_text(page, encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('input')
    ap.add_argument('output_dir')
    ap.add_argument('--start', type=float, default=0)
    ap.add_argument('--seconds', type=float, default=120)
    ap.add_argument('--melody-source', help='可选、与原曲从0秒同步的主奏/独奏文件；不执行模型分离')
    ap.add_argument('--bpm', type=float, help='已知分析脉冲BPM；不自动等同四分音符')
    ap.add_argument('--meter', help='已知拍号，如6/8；不自动估计小节起点')
    I18N.add_argument(ap)
    a = ap.parse_args()
    I18N.use_language(a.lang)
    if not np.isfinite(a.start) or a.start < 0 or not np.isfinite(a.seconds) or a.seconds < .25:
        ap.error('--start须为非负有限数，--seconds须为至少0.25的有限数')
    if a.bpm is not None and (not np.isfinite(a.bpm) or not 20 <= a.bpm <= 400):
        ap.error('--bpm须在20–400之间')
    if a.meter and not re.fullmatch(r'[1-9][0-9]*/(?:2|4|8|16)', a.meter):
        ap.error('--meter格式如4/4、3/4、6/8')
    out = Path(a.output_dir).expanduser().resolve()
    if any((out/name).exists() for name in FILES):
        ap.error('报告文件已存在，请使用新的输出目录，避免覆盖')
    try:
        source = source_info(a.input)
        y = decode(a.input, a.start, a.seconds, stereo=source['audio_channels'] != 1)
        solo = decode(a.melody_source, a.start, a.seconds, stereo=True) if a.melody_source else None
        if solo is not None and abs(len(y)-len(solo))/SR > .05:
            raise ValueError('主奏文件选定范围与原曲时长不一致；需要同起点、同步的文件')
        if solo is not None:
            solo = np.pad(solo[:len(y)], ((0, max(0, len(y)-len(solo))), (0, 0)))
        report, data = analyze(y, solo, a.bpm, a.meter, a.start)
        report['source'] = source
        report['melody_source'] = source_info(a.melody_source) if a.melody_source else None
        report['software'] = {'librosa': librosa.__version__, 'numpy': np.__version__}
        total = report['source']['duration_seconds']
        report['analysis_range']['unanalysed_tail_seconds'] = rounded(max(0, total-a.start-len(y)/SR)) if total is not None else None
        out.mkdir(parents=True, exist_ok=True)
        write_outputs(out, report, data, a.lang)
    except (ValueError, OSError, subprocess.CalledProcessError) as e:
        ap.exit(2, f'参考曲分析失败: {e}\n')
    print(json.dumps({'report': str(out/'report.html'), 'report_language': a.lang, 'range': report['analysis_range'],
                      'note_candidates': len(report['melody']['notes']),
                      'boundary_candidates': len(report['structure']['boundaries']),
                      'status': 'candidates_only_not_listened'}, ensure_ascii=False))


if __name__ == '__main__':
    main()
