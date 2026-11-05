#!/usr/bin/env python3
"""把 LLM 写的乐谱（score.json）渲染成 WAV，并打印自检报告。

用法: render_score.py score.json OUT.wav [--duration 15] [--tail 0.8] [--seed 7] [--no-report]

乐谱格式见 references/score-format.md。要点:
  tracks       每个声部用哪种乐器、音量、声像、混响/回声
  sections     段落；每个声部按“小节”写一串音符（迷你记谱）
  arrangement  段落顺序，如 ["intro","A*2","B","END"]
--duration 给出时，会微调速度使「正文 + 尾音」恰为该时长（偏离 >8% 时警告）。
乐谱有错会报出具体的 段落/声部/小节，退出码 2。合成器简单，音质有限，必须人耳核听。
"""
import argparse, json, math, re, sys

from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import localization as I18N
from localization import translate as translate_text

if __name__ == "__main__" and sys.platform == "win32":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
import numpy as np
import soundfile as sf
from scipy import signal

SR = 44100
PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
SCALES = {"major": [0, 2, 4, 5, 7, 9, 11], "minor": [0, 2, 3, 5, 7, 8, 10, 11]}  # 小调含导音（和声小调）
DRUMS = ["kick", "snare", "hat", "openhat", "clap", "rim", "tom", "hoof", "shaker", "cowbell", "taiko", "gong", "bangzi", "crash", "ride"]


class ScoreError(Exception): pass


# ---------------------------------------------------------------- 记谱解析
TOKEN = re.compile(r"^(r|(?:[A-Ga-g][#b]?-?\d|\d{1,3})(?:\+(?:[A-Ga-g][#b]?-?\d|\d{1,3}))*):([\d./]+)(?:@([\d.]+))?$")


def midi_of(s):
    if s.isdigit(): return int(s)
    m = re.fullmatch(r"([A-Ga-g])([#b]?)(-?\d)", s)
    v = PC[m.group(1).upper()] + {"#": 1, "b": -1, "": 0}[m.group(2)]
    return 12 * (int(m.group(3)) + 1) + v


def num(x):
    a, _, b = x.partition("/")
    return float(a) / float(b) if b else float(a)


def expand(s):
    pat = re.compile(r"\(([^()]*)\)\*(\d+)")
    while pat.search(s): s = pat.sub(lambda m: " ".join([m.group(1).strip()] * int(m.group(2))), s)
    return s


def parse_bar(text, bpb, where):
    """-> [(start_beat, dur_beats, [midi...], vel)]，并校验小节总拍数。"""
    out, pos = [], 0.0
    for tok in expand(text).split():
        m = TOKEN.match(tok)
        if not m: raise ScoreError(f"{where}: 无法解析记号 '{tok}'（格式 E4:1.5 / E3+G3+B3:4@0.8 / r:1）")
        d = num(m.group(2))
        if d <= 0: raise ScoreError(f"{where}: 时值必须>0: '{tok}'")
        if m.group(1) != "r":
            vel = float(m.group(3)) if m.group(3) else 0.8
            out.append((pos, d, [midi_of(p) for p in m.group(1).split("+")], vel))
        pos += d
    if abs(pos - bpb) > 1e-6: raise ScoreError(f"{where}: 本小节共 {pos:g} 拍，应为 {bpb} 拍")
    return out


def parse_drum_bar(text, bpb, where):
    steps = int(bpb * 4); out = []
    for lane in [x.strip() for x in text.split(";") if x.strip()]:
        name, _, pat = lane.partition(":"); name, pat = name.strip(), pat.strip().replace(" ", "")
        if name not in DRUMS: raise ScoreError(f"{where}: 未知鼓件 '{name}'，可用 {DRUMS}")
        if len(pat) != steps: raise ScoreError(f"{where}: 鼓件 {name} 需要 {steps} 个格子（16 分音符），现有 {len(pat)}")
        for i, ch in enumerate(pat):
            if ch in ".-": continue
            if ch not in "xXo": raise ScoreError(f"{where}: 鼓格只能是 x X o .，出现 '{ch}'")
            out.append((i / 4, name, {"x": 0.8, "X": 1.0, "o": 0.45}[ch]))
    return out


# ---------------------------------------------------------------- 乐器
def L(dur, rel): return max(int((dur + 4 * rel) * SR), 64)
def tt(n): return np.arange(n) / SR
def mtof(m): return 440.0 * 2 ** ((m - 69) / 12)


def adsr(n, dur, a, d, s, r):
    t = tt(n)
    e = np.minimum(t / max(a, 1e-3), 1.0) * (s + (1 - s) * np.exp(-np.maximum(t - a, 0) / max(d, 1e-3)))
    return e * np.where(t < dur, 1.0, np.exp(-(t - dur) / max(r, 1e-3)))


def harm(f, t, amps, cents=0.0):
    f = f * 2 ** (cents / 1200); x = np.zeros_like(t)
    for h, a in enumerate(amps, 1):
        if f * h > SR * 0.45: break
        x += a * np.sin(2 * np.pi * f * h * t)
    return x


def saw_amps(n, roll=1.0): return [h ** -roll for h in range(1, n + 1)]


def i_pad(m, dur, vel, P, rng):
    r = P.get("release", 0.6); n = L(dur, r); t = tt(n); roll = 1.0 + (1 - P.get("bright", 0.5)) * 1.5
    e = adsr(n, dur, P.get("attack", 0.4), 0.1, 0.9, r); a = saw_amps(8, roll)
    return np.stack([harm(mtof(m), t, a, -7) * e, harm(mtof(m), t, a, +7) * e]) * 0.2


def i_strings(m, dur, vel, P, rng):
    r = P.get("release", 0.7); n = L(dur, r); t = tt(n); e = adsr(n, dur, P.get("attack", 0.5), 0.1, 0.9, r); a = saw_amps(10, 1.0)
    f = mtof(m)
    return np.stack([(harm(f, t, a, -9) + harm(f, t, a, 0)) * e, (harm(f, t, a, 0) + harm(f, t, a, 9)) * e]) * 0.12


def i_pluck(m, dur, vel, P, rng):
    tau = P.get("decay", 0.5); rel = P.get("release", 0.12)
    if P.get("sustain"): dur = max(dur, tau * 5)
    n = L(min(dur, tau * 6), rel); t = tt(n); f = mtof(m); x = np.zeros(n)
    for h in range(1, 13):
        if f * h > SR * 0.45: break
        x += h ** -0.9 * np.sin(2 * np.pi * f * h * t) * np.exp(-t * (1 + P.get("bright", 0.4) * h) / tau)
    return x * np.minimum(t / 0.002, 1) * np.where(t < dur, 1.0, np.exp(-(t - dur) / rel)) * 0.3


def i_bass(m, dur, vel, P, rng):
    rel = P.get("release", 0.08); n = L(dur, rel); t = tt(n); f = mtof(m)
    x = np.sin(2 * np.pi * f * t) + 0.3 * np.sin(4 * np.pi * f * t) + 0.1 * np.sin(6 * np.pi * f * t)
    return x * adsr(n, dur, 0.006, P.get("decay", 0.3), P.get("sustain_level", 0.25), rel) * 0.55


def i_sub(m, dur, vel, P, rng):
    n = L(dur, 0.15); return np.sin(2 * np.pi * mtof(m) * tt(n)) * adsr(n, dur, 0.02, 0.1, 0.9, 0.15) * 0.6


def _voice(m, dur, P, rng, amps, a, d, s, r, vib, noise):
    n = L(dur, r); t = tt(n); f = mtof(m)
    ph = 2 * np.pi * np.cumsum(f * (1 + vib * np.sin(2 * np.pi * 5.5 * t) * np.minimum(t / 0.3, 1))) / SR
    x = sum(a_ * np.sin((h + 1) * ph) for h, a_ in enumerate(amps))
    if noise: x = x + noise * np.diff(rng.standard_normal(n + 1))
    return x * adsr(n, dur, a, d, s, r)


def i_lead(m, dur, vel, P, rng):
    return _voice(m, dur, P, rng, saw_amps(10, P.get("roll", 1.0)), 0.03, 0.1, 0.8, 0.15, P.get("vibrato", 0.006), 0) * 0.14


def i_whistle(m, dur, vel, P, rng):
    return _voice(m, dur, P, rng, [1.0, 0.12], 0.04, 0.1, 0.9, 0.08, P.get("vibrato", 0.006), 0.02) * 0.22


def i_organ(m, dur, vel, P, rng):
    n = L(dur, 0.08); t = tt(n); f = mtof(m)
    x = sum(a * np.sin(2 * np.pi * f * h * t) for h, a in ((1, 1), (2, .8), (3, .5), (4, .35), (6, .2)))
    return x * adsr(n, dur, 0.01, 0.1, 1.0, 0.08) * 0.12


def i_keys(m, dur, vel, P, rng):
    tau = P.get("decay", 1.0); n = L(min(dur, tau * 5), 0.15); t = tt(n); f = mtof(m)
    x = sum(a * np.sin(2 * np.pi * f * h * t) * np.exp(-t * h ** 0.5 / tau) for h, a in ((1, 1), (2, .35), (3, .15), (4, .06)))
    x += 0.1 * np.sin(2 * np.pi * f * 6 * t) * np.exp(-t / 0.06)
    return x * np.minimum(t / 0.003, 1) * np.where(t < dur, 1.0, np.exp(-(t - dur) / 0.15)) * 0.28


def i_bell(m, dur, vel, P, rng):
    k = P.get("decay", 1.0); n = L(min(2.5 * k, 3.0), 0.1); t = tt(n); f = mtof(m)
    x = sum(a * np.sin(2 * np.pi * f * r * t) * np.exp(-t / (tau * k)) for r, a, tau in ((1, 1, 1.2), (2.76, .5, .7), (5.4, .25, .4), (8.93, .12, .25)))
    return x * np.minimum(t / 0.002, 1) * 0.25


def i_marimba(m, dur, vel, P, rng):
    n = L(0.6, 0.05); t = tt(n); f = mtof(m)
    x = sum(a * np.sin(2 * np.pi * f * r * t) * np.exp(-t / tau) for r, a, tau in ((1, 1, .35), (4, .45, .08), (10, .15, .03)))
    return x * np.minimum(t / 0.002, 1) * 0.35


def _bent(m, dur, rel, amps, a, d, s, vib, noise, rng, bend=0.0, bend_t=0.08, vib_rate=5.5, vib_delay=0.25):
    """带起音滑音（bend 半音，从下方滑入）的持续音，用于二胡/笛等。"""
    n = L(dur, rel); t = tt(n); f = mtof(m)
    sl = 2 ** (-bend * np.exp(-t / bend_t) / 12) if bend else 1.0
    ph = 2 * np.pi * np.cumsum(f * sl * (1 + vib * np.sin(2 * np.pi * vib_rate * t) * np.clip((t - vib_delay) / 0.3, 0, 1))) / SR
    x = sum(a_ * np.sin((h + 1) * ph) for h, a_ in enumerate(amps))
    if noise: x = x + noise * np.diff(rng.standard_normal(n + 1))
    return x * adsr(n, dur, a, d, s, rel)


def i_dizi(m, dur, vel, P, rng):
    """竹笛：偏亮、气声明显、轻颤音，起音带微小滑入。"""
    return _bent(m, dur, 0.1, [1.0, 0.25, 0.1, 0.05], 0.03, 0.1, 0.85, P.get("vibrato", 0.004), P.get("breath", 0.05), rng,
                 bend=P.get("bend", 0.3), bend_t=0.05) * 0.2


def i_xiao(m, dur, vel, P, rng):
    """洞箫：更柔更暗，气声多，起音慢。"""
    return _bent(m, dur, 0.18, [1.0, 0.12, 0.04], 0.09, 0.15, 0.9, P.get("vibrato", 0.005), P.get("breath", 0.09), rng,
                 bend=P.get("bend", 0.5), bend_t=0.09, vib_delay=0.4) * 0.24


def i_erhu(m, dur, vel, P, rng):
    """二胡：泛音丰富的弓弦声，明显滑入和较深颤音。"""
    n_amps = [h ** -0.8 for h in range(1, 12)]
    return _bent(m, dur, 0.12, n_amps, 0.06, 0.2, 0.85, P.get("vibrato", 0.009), P.get("rosin", 0.012), rng,
                 bend=P.get("bend", 0.6), bend_t=0.07, vib_rate=5.8, vib_delay=0.2) * 0.12


def i_guzheng(m, dur, vel, P, rng):
    """古筝：明亮拨弦，余音长，起音略带上滑（按弦）。"""
    tau = P.get("decay", 1.4); n = L(min(tau * 4, 4.0), 0.2); t = tt(n); f = mtof(m)
    sl = 2 ** (P.get("bend", 0.25) * np.exp(-t / 0.05) / 12)
    x = np.zeros(n)
    for h in range(1, 12):
        if f * h > SR * 0.45: break
        x += h ** -0.85 * np.sin(2 * np.pi * f * h * sl * t) * np.exp(-t * (1 + 0.25 * h) / tau)
    x += 0.15 * np.diff(rng.standard_normal(n + 1)) * np.exp(-t / 0.01)  # 拨弦瞬态
    return x * np.minimum(t / 0.0015, 1) * 0.3


def i_pipa(m, dur, vel, P, rng):
    """琵琶：颗粒感强、衰减快的弹拨。"""
    tau = P.get("decay", 0.55); n = L(min(tau * 5, 2.5), 0.1); t = tt(n); f = mtof(m); x = np.zeros(n)
    for h in range(1, 14):
        if f * h > SR * 0.45: break
        x += h ** -0.7 * np.sin(2 * np.pi * f * h * t) * np.exp(-t * (1.5 + 0.5 * h) / tau)
    x += 0.25 * np.diff(rng.standard_normal(n + 1)) * np.exp(-t / 0.006)
    return x * np.minimum(t / 0.001, 1) * 0.26


INST = dict(dizi=i_dizi, xiao=i_xiao, erhu=i_erhu, guzheng=i_guzheng, pipa=i_pipa, pad=i_pad, strings=i_strings, pluck=i_pluck, bass=i_bass, sub=i_sub, lead=i_lead, whistle=i_whistle,
            organ=i_organ, keys=i_keys, bell=i_bell, marimba=i_marimba)


def drum_shot(name, rng, k=0):
    if name == "kick":
        t = tt(int(0.32 * SR)); return np.sin(2 * np.pi * np.cumsum(48 + 110 * np.exp(-t / 0.03)) / SR) * np.exp(-t / 0.12) * 0.9
    if name in ("snare", "clap", "rim", "shaker", "hat", "openhat", "hoof", "crash", "ride"):  # noqa
        if name == "snare":
            t = tt(int(0.25 * SR)); sos = signal.butter(2, [1500, 8000], "band", fs=SR, output="sos")
            return signal.sosfilt(sos, rng.standard_normal(len(t))) * np.exp(-t / 0.09) * 0.45 + np.sin(2 * np.pi * 190 * t) * np.exp(-t / 0.06) * 0.35
        if name == "clap":
            t = tt(int(0.2 * SR)); sos = signal.butter(2, [1000, 6000], "band", fs=SR, output="sos")
            nz = signal.sosfilt(sos, rng.standard_normal(len(t)))
            env = sum(np.exp(-np.maximum(t - d, 0) / 0.04) * (t >= d) for d in (0, .012, .024)); return nz * env * 0.2
        if name == "rim":
            t = tt(int(0.05 * SR)); return np.sin(2 * np.pi * 1700 * t) * np.exp(-t / 0.01) * 0.5
        if name == "shaker":
            t = tt(int(0.1 * SR)); sos = signal.butter(2, [5000, 9500], "band", fs=SR, output="sos")
            return signal.sosfilt(sos, rng.standard_normal(len(t))) * np.minimum(t / 0.008, 1) * np.exp(-t / 0.04) * 0.4
        if name in ("hat", "openhat", "crash", "ride"):
            tau = {"hat": .03, "openhat": .25, "crash": 1.1, "ride": .6}[name]; t = tt(int(min(tau * 6, 1.5 if name in ("crash", "ride") else .5) * SR))
            return np.diff(rng.standard_normal(len(t) + 1)) * np.exp(-t / tau) * 0.3
        t = tt(int(0.07 * SR)); sos = signal.butter(2, [600, 3500], "band", fs=SR, output="sos")  # hoof
        f = 780 if k % 2 == 0 else 1020
        return (np.sin(2 * np.pi * f * t) * .6 + signal.sosfilt(sos, rng.standard_normal(len(t))) * .5) * np.exp(-t / 0.018) * 0.4
    if name == "tom":
        t = tt(int(0.4 * SR)); return np.sin(2 * np.pi * np.cumsum(90 + 80 * np.exp(-t / 0.05)) / SR) * np.exp(-t / 0.18) * 0.7
    if name == "taiko":  # 大鼓：低沉、鼓皮余震
        t = tt(int(0.9 * SR)); f = 58 + 40 * np.exp(-t / 0.06)
        return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.3) + 0.25 * np.sin(2 * np.pi * 112 * t) * np.exp(-t / 0.12)) * 0.95
    if name == "gong":  # 锣：非谐泛音长衰减
        t = tt(int(2.5 * SR)); x = sum(a * np.sin(2 * np.pi * f * t) * np.exp(-t / tau) for f, a, tau in ((180, 1, 1.4), (273, .6, 1.0), (421, .4, .7), (587, .25, .5), (903, .12, .3)))
        return x * np.minimum(t / 0.004, 1) * 0.3
    if name == "bangzi":  # 梆子：清脆木击
        t = tt(int(0.1 * SR)); return (np.sin(2 * np.pi * 1250 * t) + 0.5 * np.sin(2 * np.pi * 1900 * t)) * np.exp(-t / 0.012) * 0.4
    if name == "cowbell":
        t = tt(int(0.3 * SR)); return (np.sin(2 * np.pi * 560 * t) + np.sin(2 * np.pi * 845 * t)) * np.exp(-t / 0.1) * 0.25
    raise ScoreError(f"unknown drum {name}")


# ---------------------------------------------------------------- 渲染
def add(buf, seg, start):
    if start >= buf.shape[-1] or start < 0: return
    n = min(seg.shape[-1], buf.shape[-1] - start); buf[..., start:start + n] += seg[..., :n]


def reverb(x, rng, sec=1.4):
    n = int(sec * SR); ir = rng.standard_normal(n) * np.exp(-np.arange(n) / (0.3 * SR)); ir[0] = 0; ir /= np.sqrt(np.sum(ir ** 2))
    return np.stack([signal.fftconvolve(x[c], ir)[:x.shape[1]] for c in range(2)])


def load(path):
    sc = json.load(open(path, encoding="utf-8"))
    bpb = int(sc.get("beats_per_bar", 4))
    tracks = sc.get("tracks") or {}
    if not tracks: raise ScoreError("缺少 tracks")
    for k, v in tracks.items():
        if v.get("inst") not in INST and v.get("inst") != "drums": raise ScoreError(f"声部 {k}: 未知乐器 '{v.get('inst')}'，可用 {list(INST)+['drums']}")
    arr = []
    for item in sc.get("arrangement") or []:
        name, _, rep = item.partition("*"); arr += [name.strip()] * int(rep or 1)
    if not arr: raise ScoreError("缺少 arrangement")
    secs = {}
    for name in set(arr):
        if name not in sc.get("sections", {}): raise ScoreError(f"arrangement 引用了不存在的段落 '{name}'")
    for name, sec in sc["sections"].items():
        lens = [len(v) if isinstance(v, list) else 1 for k, v in sec.items() if k != "bars"]
        nb = int(sec.get("bars") or (max(lens) if lens else 1)); bars = {}
        for tr, val in sec.items():
            if tr == "bars": continue
            if tr not in tracks: raise ScoreError(f"段落 {name}: 声部 '{tr}' 未在 tracks 中定义")
            lst = val if isinstance(val, list) else [val]
            bars[tr] = []
            for b in range(nb):
                where = f"段落 {name} / 声部 {tr} / 第{b % len(lst) + 1}小节"
                txt = lst[b % len(lst)]
                bars[tr].append(parse_drum_bar(txt, bpb, where) if tracks[tr]["inst"] == "drums" else parse_bar(txt, bpb, where))
        secs[name] = (nb, bars)
    return sc, bpb, tracks, arr, secs


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("score"); ap.add_argument("out")
    ap.add_argument("--duration", type=float); ap.add_argument("--tail", type=float, default=0.8)
    I18N.add_argument(ap)
    ap.add_argument("--seed", type=int); ap.add_argument("--no-report", action="store_true"); a = ap.parse_args()
    I18N.use_language(a.lang)
    try: sc, bpb, tracks, arr, secs = load(a.score)
    except ScoreError as e: print(translate_text('乐谱错误: {v0}', v0=e), file=sys.stderr); sys.exit(2)
    except json.JSONDecodeError as e: print(translate_text('JSON 语法错误: {v0}', v0=e), file=sys.stderr); sys.exit(2)

    seed = a.seed if a.seed is not None else int(sc.get("seed", 7)); rng = np.random.default_rng(seed)
    bpm = float(sc.get("bpm", 100)); nbars = sum(secs[s][0] for s in arr); beats = nbars * bpb
    if a.duration:
        body = a.duration - a.tail
        if body < 2: sys.exit(translate_text('duration 太短'))
        used = 60 * beats / body
        if abs(used / bpm - 1) > 0.08: print(translate_text('WARN: 为凑 {v0}s，bpm {v1:g} -> {v2:.1f}（偏离>8%，建议增减小节数）', v0=a.duration, v1=bpm, v2=used), file=sys.stderr)
        bpm = used
    beat_s = 60 / bpm; total_n = int(round((beats * beat_s + a.tail) * SR))
    swing = float(sc.get("swing", 0)); hum = float(sc.get("humanize_ms", 6)) / 1000

    bufs = {k: np.zeros((2, total_n)) for k in tracks}; rev_bus = np.zeros((2, total_n)); drum_k = 0
    timeline, counts = [], {k: [] for k in tracks}; notes_by_track = {k: [] for k in tracks}
    bar_i = 0
    for sname in arr:
        nb, bars = secs[sname]
        for b in range(nb):
            timeline.append(sname)
            for tr, spec in tracks.items():
                ev = bars.get(tr, [None] * nb)[b]; cnt = 0
                if ev:
                    for e in ev:
                        base = (bar_i * bpb + e[0]) * beat_s
                        if tr and tracks[tr]["inst"] == "drums":
                            pos, name, vel = e; jit = 0.0
                            if abs((pos * 2) % 1) < 1e-6 and (pos * 2) % 2 == 1 and swing: base += swing * beat_s / 3
                            drum_k += 1
                            add(bufs[tr], np.stack([drum_shot(name, rng, drum_k)] * 2) * vel, int((base) * SR)); cnt += 1
                        else:
                            pos, d, ms, vel = e
                            if swing and abs((pos % 1) - 0.5) < 1e-6: base += swing * beat_s / 3
                            jit = rng.uniform(-hum, hum) if hum else 0.0
                            P = tracks[tr].get("params", {})
                            for mi, m in enumerate(ms):
                                x = INST[tracks[tr]["inst"]](m, d * beat_s, vel, P, rng) * vel
                                x = np.stack([x, x]) if x.ndim == 1 else x
                                add(bufs[tr], x, max(int((base + jit + mi * P.get("strum", 0)) * SR), 0)); notes_by_track[tr].append(m)
                            cnt += 1
                counts[tr].append(cnt)
            bar_i += 1

    mix = np.zeros((2, total_n))
    for tr, buf in bufs.items():
        cfg = tracks[tr]; g = float(cfg.get("gain", 0.8)); pan = float(cfg.get("pan", 0)); th = (pan + 1) * math.pi / 4
        x = buf * g * np.array([[math.cos(th)], [math.sin(th)]]) * math.sqrt(2)
        dl = float(cfg.get("delay", 0))
        if dl > 0:
            d = int(float(cfg.get("delay_beats", 0.75)) * beat_s * SR); echo = np.zeros_like(x)
            for n_, gg in ((1, dl), (2, dl * 0.4)):
                if d * n_ < total_n: echo[:, d * n_:] += gg * x[::-1, :total_n - d * n_]
            x = x + echo
        mix += x; rev_bus += x * float(cfg.get("reverb", 0.15))
    mix += reverb(rev_bus, rng) * float(sc.get("reverb_level", 1.0))
    mix = np.tanh(mix * 1.1)
    nfade = int(0.01 * SR); mix[:, :nfade] *= np.linspace(0, 1, nfade); mix *= 0.7 / max(np.abs(mix).max(), 1e-9)
    sf.write(a.out, mix.T.astype(np.float32), SR, subtype="PCM_16")

    info = dict(bpm=round(bpm, 2), bars=nbars, beats_per_bar=bpb, body_sec=round(beats * beat_s, 2), tail_sec=a.tail,
                total_sec=round(total_n / SR, 2), seed=seed, timeline=timeline)
    json.dump(info, open(re.sub(r"\.\w+$", "", a.out) + ".render.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(translate_text('bpm {v0:.1f} | {v1} 小节 | 正文 {v2:.2f}s + 尾音 {v3}s = {v4:.2f}s | seed {v5}', v0=bpm, v1=nbars, v2=beats * beat_s, v3=a.tail, v4=total_n / SR, v5=seed))
    if a.no_report: return

    # ------- 自检报告
    key = sc.get("key", "")
    mk = re.fullmatch(r"\s*([A-Ga-g][#b]?)\s*(major|minor)\s*", key or "")
    allowed = None
    if mk:
        tonic = (PC[mk.group(1)[0].upper()] + {"#": 1, "b": -1, "": 0}[mk.group(1)[1:]]) % 12
        allowed = {(tonic + s) % 12 for s in SCALES[mk.group(2)]}
    mono = mix.mean(axis=0); spb = int(bpb * beat_s * SR)
    print(translate_text('\n小节 段落        ') + ' '.join((f'{k[:7]:>7}' for k in tracks)) + translate_text('   电平dB'))
    for i in range(nbars):
        seg = mono[i * spb:(i + 1) * spb]; db = 20 * math.log10(math.sqrt(np.mean(seg ** 2)) + 1e-9)
        print(f"{i + 1:>3}  {timeline[i]:<10} " + " ".join(f"{counts[k][i]:>7}" for k in tracks) + f"   {db:6.1f}")
    print(translate_text('\n声部    音域                出调音占比'))
    for k, ns in notes_by_track.items():
        if not ns: continue
        out = (sum(1 for m in ns if m % 12 not in allowed) / len(ns)) if allowed else None
        print(translate_text('{v0:<8}{v1:>3}~{v2:<3}({v3}音)   ', v0=k, v1=min(ns), v2=max(ns), v3=len(ns)) + (f'{out:5.0%}' if out is not None else translate_text('-（未声明 key）')))
    last = mono[-SR:]; body_db = 20 * math.log10(np.sqrt(np.mean(mono[:-int(a.tail * SR)] ** 2)) + 1e-9) if a.tail > 0 else 0
    print(translate_text('\n结尾最后1s相对正文: {v0:+.1f} dB', v0=20 * math.log10(math.sqrt(np.mean(last ** 2)) + 1e-09) - body_db))


if __name__ == "__main__":
    main()
