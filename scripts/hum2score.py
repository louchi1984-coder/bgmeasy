#!/usr/bin/env python3
"""哼唱 -> 动机。把一段哼唱/口哨/清唱录音转写成音符，作为整首曲子的“动机”素材（不是成品旋律）。
输出 score.json 骨架：motif 段落（原样转写，供试听核对）+ design.motif + 自动和弦/低音垫底 + 收尾。
之后由 agent 按 references/melody-patterns.md 把动机发展成完整乐曲（重复、换尾、模进、倒影、增值、升八度…），再编配。

用法: hum2score.py hum.(wav|m4a|mp3|mp4) OUT.score.json [--bpm 100] [--key "D major"] [--inst whistle]
        [--grid 0.25] [--no-snap] [--no-end] [--octave auto|N] [--max-seconds 60] [--title X]
依赖: librosa（pyin 音高追踪）、numpy、soundfile；非 wav 格式或视频会调用 ffmpeg 转码。
流程: 音高追踪 -> 校准音准偏差 -> 切成音符 -> 按 bpm 量化到格子 -> 调性检测并把出调音吸附到音阶 -> 逐小节配和弦。
局限: 单声部、干声最准；节拍靠 --bpm（不给则估计，哼唱常不稳，估计不准就手动给）；
      默认格子 0.25 拍（16 分音符），三连音会被扭成直拍；跨小节的长音会拆成两个同音（没有连音线）；
      吸附音阶会改掉你哼错或有意的出调音，用 --no-snap 保留原音。输出只是起点，仍需听和改。
"""
import argparse, json, os, re, subprocess, sys, tempfile

if __name__ == "__main__" and sys.platform == "win32":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import numpy as np
import librosa
import render_score as R

NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
KS_MAJ = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
KS_MIN = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
DEG = {"major": [0, 2, 4, 5, 7, 9, 11], "minor": [0, 2, 3, 5, 7, 8, 10]}


def nm(m): return f"{NAMES[m % 12]}{m // 12 - 1}"


def load(path, max_s):
    try:
        return librosa.load(path, sr=22050, mono=True, duration=max_s)
    except Exception:
        w = os.path.join(tempfile.mkdtemp(), "h.wav")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", path, "-vn", "-ac", "1", "-ar", "22050", w], check=True)
        return librosa.load(w, sr=22050, mono=True, duration=max_s)


def track_notes(y, sr, min_dur=0.07):
    hop = 256
    f0, voiced, _ = librosa.pyin(y, fmin=65, fmax=1100, sr=sr, frame_length=2048, hop_length=hop)
    ok = voiced & ~np.isnan(f0)
    if ok.sum() < 8: sys.exit("没有检测到稳定的音高：请用干净、无伴奏的哼唱/口哨，靠近麦克风，音量别太小。")
    midi = np.full(len(f0), np.nan); midi[ok] = librosa.hz_to_midi(f0[ok])
    off = float(np.median(midi[ok] - np.round(midi[ok])))  # 整体音准偏差（半音），校准到标准音高
    midi[ok] -= off
    lab = np.where(ok, np.round(midi), np.nan)
    # 3 帧中值滤波去抖
    sm = lab.copy()
    for i in range(1, len(lab) - 1):
        if ok[i]:
            w = [v for v in lab[i - 1:i + 2] if not np.isnan(v)]
            sm[i] = float(np.median(w))
    fs = hop / sr; notes = []; cur = None
    for i, v in enumerate(sm):
        if np.isnan(v):
            if cur: notes.append(cur); cur = None
        elif cur and cur[0] == v: cur[2] = i + 1
        else:
            if cur: notes.append(cur)
            cur = [v, i, i + 1]
    if cur: notes.append(cur)
    notes = [(int(p), s * fs, e * fs) for p, s, e in notes if (e - s) * fs >= min_dur]
    merged = []
    for p, s, e in notes:  # 同音且间隙极短：视为同一个音
        if merged and merged[-1][0] == p and s - merged[-1][2] < 0.04: merged[-1] = (p, merged[-1][1], e)
        else: merged.append((p, s, e))
    return merged, off, float(len(y) / sr)


def detect_key(notes):
    h = np.zeros(12)
    for p, s, e in notes: h[p % 12] += e - s
    best = []
    for t in range(12):
        for mode, prof in (("major", KS_MAJ), ("minor", KS_MIN)):
            best.append((float(np.corrcoef(h, np.roll(prof, t))[0, 1]), t, mode))
    best.sort(reverse=True)
    return best[0][1], best[0][2], best[0][0] - best[1][0]


def snap(m, scale_pcs):
    if m % 12 in scale_pcs: return m
    for d in (1, -1, 2, -2):
        if (m + d) % 12 in scale_pcs: return m + d
    return m


def chord_for_bar(bar_notes, tonic, mode):
    sc = [(tonic + d) % 12 for d in DEG[mode]]
    best = None
    for i in range(7):
        tri = [sc[i], sc[(i + 2) % 7], sc[(i + 4) % 7]]
        score = sum(d * (1.0 if p % 12 in tri else 0) for p, d in bar_notes)
        if bar_notes and bar_notes[0][0] % 12 in tri: score += 0.3
        if i == 0: score += 0.05
        if best is None or score > best[0]: best = (score, i, tri)
    return best[1], best[2]


def bar_text(events, bpb):
    out, pos = [], 0.0
    for st, d, m in sorted(events):
        if st > pos + 1e-6: out.append(f"r:{st - pos:g}")
        out.append(f"{nm(m)}:{d:g}"); pos = st + d
    if pos < bpb - 1e-6: out.append(f"r:{bpb - pos:g}")
    return " ".join(out)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("audio"); ap.add_argument("out")
    ap.add_argument("--bpm", type=float); ap.add_argument("--key"); ap.add_argument("--inst", default="whistle")
    ap.add_argument("--grid", type=float, default=0.25); ap.add_argument("--no-snap", action="store_true")
    ap.add_argument("--no-end", action="store_true"); ap.add_argument("--octave", default="auto")
    ap.add_argument("--max-seconds", type=float, default=60); ap.add_argument("--title", default="哼唱创作"); a = ap.parse_args()
    if a.inst not in R.INST: sys.exit(f"未知乐器 {a.inst}，可用 {list(R.INST)}")
    y, sr = load(a.audio, a.max_seconds)
    notes, off, total = track_notes(y, sr)
    t0 = notes[0][1]; notes = [(p, s - t0, e - t0) for p, s, e in notes]  # 去掉开头静音

    if a.bpm: bpm = a.bpm; src = "用户指定"
    else:
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr); bpm = float(np.atleast_1d(tempo)[0])
        while bpm > 140: bpm /= 2
        while bpm < 70: bpm *= 2
        bpm = round(bpm); src = "估计（哼唱常不稳，不准请用 --bpm）"
    beat = 60.0 / bpm; g = a.grid

    # 八度：让旋律中位音落在 64~79 之间（适合口哨/主音乐器）
    med = float(np.median([p for p, s, e in notes]))
    if a.octave == "auto": shift = 12 * round((72 - med) / 12)
    else: shift = 12 * int(a.octave)
    notes = [(p + shift, s, e) for p, s, e in notes]

    if a.key:
        mk = re.fullmatch(r"\s*([A-G][#b]?)\s*(major|minor)\s*", a.key)
        if not mk: sys.exit("--key 格式如 \"D major\" / \"A minor\"")
        tonic = (R.PC[mk.group(1)[0]] + {"#": 1, "b": -1, "": 0}[mk.group(1)[1:]]) % 12; mode = mk.group(2); conf = None
    else: tonic, mode, conf = detect_key(notes)
    scale_pcs = {(tonic + d) % 12 for d in DEG[mode]}
    snapped = 0
    if not a.no_snap:
        n2 = []
        for p, s, e in notes:
            q = snap(p, scale_pcs); snapped += q != p; n2.append((q, s, e))
        notes = n2

    # 量化到格子，保证不重叠、最短一格
    q = []; prev_end = 0.0
    for p, s, e in notes:
        qs = max(round(s / beat / g) * g, prev_end); qe = max(round(e / beat / g) * g, qs + g)
        if qs >= qe: continue
        q.append((p, qs, qe)); prev_end = qe
    bpb = 4; nbars = int(np.ceil(q[-1][2] / bpb - 1e-9))
    bars = [[] for _ in range(nbars)]
    for p, s, e in q:
        while s < e - 1e-9:
            b = int(s // bpb + 1e-9); end = min(e, (b + 1) * bpb)
            bars[b].append((s - b * bpb, end - s, p)); s = end

    mel, pad, bas, chord_names = [], [], [], []
    for b in range(nbars):
        bn = [(m, d) for st, d, m in sorted(bars[b])]
        deg, tri = chord_for_bar(bn, tonic, mode)
        if b == nbars - 1 and a.no_end: pass
        r = tri[0]; base = 48 + r
        ints = [(t - r) % 12 for t in tri]
        pad.append("+".join(nm(base + i) for i in ints) + f":{bpb}")
        bas.append(f"{nm(36 + r)}:{bpb}")
        suffix = "" if (tri[1] - tri[0]) % 12 == 4 else "m"
        if (tri[2] - tri[1]) % 12 == 3 and (tri[1] - tri[0]) % 12 == 3: suffix = "dim"
        chord_names.append(NAMES[r] + suffix)
        mel.append(bar_text(bars[b], bpb))

    tn = NAMES[tonic]; tri0 = [tonic, (tonic + DEG[mode][2]) % 12, (tonic + 7) % 12]
    sec = {"motif": {"melody": mel, "pad": pad, "bass": bas}}; arrangement = ["motif"]
    chords = {"motif": chord_names}
    if not a.no_end:
        sec["END"] = {"melody": [f"{nm(72 + (tonic - 0) % 12 - (12 if tonic > 5 else 0))}:4@0.7"],
                      "pad": ["+".join(nm(48 + tonic + (t - tonic) % 12) for t in tri0) + ":4"], "bass": [f"{nm(36 + tonic)}:4"]}
        arrangement.append("END"); chords["END"] = [tn + ("m" if mode == "minor" else "")]
    score = {
        "title": a.title, "bpm": round(bpm, 2), "beats_per_bar": bpb, "key": f"{tn} {mode}", "humanize_ms": 0,
        "design": {"mood": "（待填：根据用途补充情绪）", "source": "哼唱转写，需人工听校",
                   "motif": " | ".join(mel), "variations": ["（待填：换尾/模进/倒影/增值/升八度…）"], "structure": "（待填：如 A A' B A'）",
                   "melody": ["melody"], "chords": chords},
        "tracks": {
            "melody": {"inst": a.inst, "gain": 1.0, "pan": 0.1, "reverb": 0.3},
            "pad": {"inst": "strings", "gain": 0.4, "pan": 0.0, "reverb": 0.4, "params": {"attack": 0.4, "release": 1.0}},
            "bass": {"inst": "bass", "gain": 0.7, "pan": 0.0, "reverb": 0.03}},
        "sections": sec, "arrangement": arrangement}
    json.dump(score, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    print(f"哼唱 {total:.1f}s（去开头静音 {t0:.2f}s） | 转写 {len(q)} 个音，{nbars} 小节")
    print(f"音准整体偏差 {off * 100:+.0f} cents（已校准） | 八度移位 {shift:+d} 半音 | 旋律音域 {nm(min(p for p, _, _ in q))}~{nm(max(p for p, _, _ in q))}")
    print(f"bpm {bpm:g}（{src}） | 调性 {tn} {mode}" + (f"（可信度 {conf:.2f}，<0.05 不可靠，用 --key 指定）" if conf is not None else "（用户指定）"))
    print(f"吸附到音阶的音: {snapped}" + ("" if not a.no_snap else "（已关闭吸附）") + f" | 格子 {g} 拍")
    print("逐小节和弦（自动推断，近似）: " + " | ".join(chord_names))
    print(f"-> {a.out}\n注意: 这只是动机（motif 段落）。下一步: 试听核对转写，再按 melody-patterns.md 把它发展成完整乐曲，不要直接当成品。")


if __name__ == "__main__":
    main()
