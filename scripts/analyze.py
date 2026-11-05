#!/usr/bin/env python3
"""分析参考曲，提取「风格参数」（不提取旋律），供 compose.py --profile 模仿。

用法: analyze.py REF.(mp3|wav|m4a|mp4...) OUT.profile.json [--max-seconds 240]
依赖: librosa（可选依赖，仅分析/模仿需要）。ffmpeg 用于解码视频或少见格式。
输出字段: bpm, key/mode(+置信度), chord_loop(罗马数字和弦循环), energy_curve(16点),
brightness, percussive_ratio, onset_per_beat, sections, compose_hints。
局限: 拍点/调性/和弦均为估计，对无明显节拍、变速、复杂和声的曲子可能不准，
看 key_confidence 与 bpm 是否合理，不合理就手动覆盖 compose.py 的参数。
"""
import json, sys, argparse, subprocess, tempfile, os

if __name__ == "__main__" and sys.platform == "win32":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
from collections import Counter
import numpy as np
import librosa

KS_MAJ = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
KS_MIN = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
NAMES = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]
ROMAN = {0: "I", 1: "bII", 2: "II", 3: "bIII", 4: "III", 5: "IV", 6: "#IV", 7: "V", 8: "bVI", 9: "VI", 10: "bVII", 11: "VII"}


def load(path, max_s):
    try:
        return librosa.load(path, sr=22050, mono=True, duration=max_s)
    except Exception:
        tmp = tempfile.mkdtemp(); w = os.path.join(tmp, "x.wav")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", path, "-vn", "-ac", "1", "-ar", "22050", w], check=True)
        return librosa.load(w, sr=22050, mono=True, duration=max_s)


def detect_key(chroma, bass=None):
    """全频色度 KS 相关 + 低频（贝斯）色度相关；后者抑制泛音造成的误判。"""
    m = chroma.mean(axis=1)
    b = bass.mean(axis=1) if bass is not None else None
    best = []
    for tonic in range(12):
        for mode, prof in (("major", KS_MAJ), ("minor", KS_MIN)):
            sc = np.corrcoef(m, np.roll(prof, tonic))[0, 1]
            if b is not None and b.std() > 0:
                sc += 0.6 * np.corrcoef(b, np.roll(prof, tonic))[0, 1]
            best.append((sc, tonic, mode))
    best.sort(reverse=True)
    return best[0][1], best[0][2], float(best[0][0] - best[1][0])


def triad_templates():
    T, labels = [], []
    for r in range(12):
        for q, third in (("maj", 4), ("min", 3)):
            v = np.zeros(12); v[[r, (r + third) % 12, (r + 7) % 12]] = 1; T.append(v / np.linalg.norm(v)); labels.append((r, q))
    return np.array(T), labels


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("ref"); ap.add_argument("out")
    ap.add_argument("--max-seconds", type=float, default=240)
    a = ap.parse_args()
    y, sr = load(a.ref, a.max_seconds); dur = len(y) / sr
    if dur < 8: sys.exit("参考曲过短（<8s），无法可靠分析")

    tempo, beats = librosa.beat.beat_track(y=y, sr=sr, units="time")
    bpm = float(np.atleast_1d(tempo)[0])
    while bpm > 150: bpm /= 2
    while bpm < 60: bpm *= 2

    yh, yp = librosa.effects.hpss(y)
    chroma = librosa.feature.chroma_cqt(y=yh, sr=sr)
    bass = librosa.feature.chroma_cqt(y=yh, sr=sr, fmin=librosa.note_to_hz("C1"), n_octaves=3)
    tonic, mode, conf = detect_key(chroma, bass)

    # 以 4 拍为一小节估计和弦（小节线位置为假设）
    T, labels = triad_templates()
    bar_s = 240.0 / bpm

    def bar_chords(start):
        res, score = [], []
        for t0 in np.arange(start, dur - bar_s * 1.5, bar_s):
            f0, f1 = librosa.time_to_frames([t0 + 0.2 * bar_s, t0 + bar_s - 0.1 * bar_s], sr=sr)
            if f1 - f0 < 2: continue
            v = chroma[:, f0:f1].mean(axis=1); n = np.linalg.norm(v)
            if n == 0: continue
            sc = T @ (v / n); r, q = labels[int(np.argmax(sc))]
            name = ROMAN[(r - tonic) % 12]
            res.append(name if q == "maj" else name.lower()); score.append(float(sc.max()))
        return res, (float(np.mean(score)) if score else 0.0)

    # 节拍追踪相位常有偏差：在一小节内搜索使和弦模板拟合最好的网格相位（小节线位置仍是假设）
    base = float(beats[0]) % bar_s if len(beats) else 0.0
    cands = [bar_chords((base + k * bar_s / 16) % bar_s) for k in range(16)]
    chords, _ = max(cands, key=lambda c: c[1])
    loop = None
    if len(chords) >= 4:
        grams = Counter(tuple(chords[i:i + 4]) for i in range(len(chords) - 3))
        loop = list(grams.most_common(1)[0][0])
        tonic_names = ("I", "i")
        if any(c in tonic_names for c in loop):  # 循环旋转到以主和弦开头
            k = next(i for i, c in enumerate(loop) if c in tonic_names); loop = loop[k:] + loop[:k]

    rms = librosa.feature.rms(y=y)[0]
    seg = np.array_split(rms, 16)
    e = np.array([s.mean() for s in seg]); e = (e - e.min()) / max(e.max() - e.min(), 1e-9)
    energy = [round(float(0.1 + 0.9 * x), 3) for x in e]

    cent = float(librosa.feature.spectral_centroid(y=y, sr=sr)[0].mean())
    brightness = float(np.clip((cent - 800) / 3200, 0.15, 0.95))
    perc = float(np.sum(yp ** 2) / max(np.sum(y ** 2), 1e-12))
    onsets = len(librosa.onset.onset_detect(y=y, sr=sr)) / dur
    opb = float(onsets / (bpm / 60))

    try:
        bounds = librosa.segment.agglomerative(chroma, k=5)
        sections = [round(float(t), 1) for t in librosa.frames_to_time(bounds, sr=sr)]
    except Exception:
        sections = []

    mode_prog = {"major": "I V vi IV", "minor": "i bVI bIII bVII"}[mode]
    hints = dict(
        bpm=round(bpm, 1), key=NAMES[tonic], mode=mode,
        prog=" ".join(loop) if loop else mode_prog,
        brightness=round(brightness, 2),
        drums=round(float(np.clip(perc * 1.6, 0, 0.9)), 2),
        arp=0.6, arp_rate=1 if opb < 0.8 else (2 if opb < 2.0 else 4),
        density=0.9, bass_level=1 if opb < 1.0 else 2, energy=energy,
    )
    prof = dict(source=os.path.basename(a.ref), analyzed_seconds=round(dur, 1), bpm=round(bpm, 1),
                key=NAMES[tonic], mode=mode, key_confidence=round(conf, 3), chord_loop=loop,
                chord_sequence=chords[:32], energy_curve=energy, spectral_centroid_hz=round(cent),
                brightness=round(brightness, 2), percussive_ratio=round(perc, 3),
                onset_per_beat=round(opb, 2), sections_sec=sections, compose_hints=hints,
                note="只含风格统计参数，不含旋律/音符；估计值，key_confidence<0.05 时调性不可靠。")
    sec_db = [20 * np.log10(float(np.sqrt(np.mean(y[i * sr:(i + 1) * sr] ** 2))) + 1e-9) for i in range(int(dur))]
    prof["level_db_per_sec"] = [round(v, 1) for v in sec_db]
    prof["level_range_db"] = round(float(max(sec_db) - min(sec_db)), 1)
    prof["level_std_db"] = round(float(np.std(sec_db)), 1)
    prof["energy_note"] = "level_range_db 只描述所测电平范围；不能据3 dB阈值判定音乐有无高潮。energy_curve 经min-max归一化，会放大微小波动；需结合和声、节奏、音区、织体和实际试听判断结构。"
    json.dump(prof, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({k: prof[k] for k in ("bpm", "key", "mode", "key_confidence", "chord_loop", "brightness", "percussive_ratio", "onset_per_beat", "level_range_db")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
