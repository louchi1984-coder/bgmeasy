#!/usr/bin/env python3
"""合成原创 BGM（纯 numpy/scipy，无采样、无网络）。

用法:
  compose.py OUT.wav --duration 30 [--style calm|tech|upbeat|cinematic]
             [--profile ref.profile.json]      # 模仿：用 analyze.py 的结果
             [--bpm N --key A --mode minor --prog "i VI III VII"]
             [--energy 0.2,0.5,0.9,0.3] [--brightness 0-1] [--drums 0-1] [--arp 0-1]
             [--arp-rate 1|2|4] [--tail 2.0] [--seed 7]

优先级: 风格默认值 < --profile < 命令行显式参数。
--duration 是成品总长（含 --tail 尾音）。节拍会被微调，使正文恰为整数小节，
最后一小节落在主和弦并自然衰减，不会截断乐句。输出 OUT.plan.json 记录实际参数。
这是简单的和弦垫底 + 低音 + 琶音 + 轻鼓组，音质有限，必须人工核听。
"""
import argparse, json, math, re, sys

if __name__ == "__main__" and sys.platform == "win32":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
import numpy as np
import soundfile as sf
from scipy import signal

SR = 44100
NUMERAL = {"I": 0, "II": 2, "III": 4, "IV": 5, "V": 7, "VI": 9, "VII": 11}
NOTE_PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}

STYLES = {
    "calm":      dict(bpm=76,  mode="major", prog="I V vi IV",      brightness=0.35, arp=0.35, arp_rate=1, density=0.8, drums=0.0, bass_level=1),
    "tech":      dict(bpm=100, mode="minor", prog="i bVI bIII bVII",   brightness=0.60, arp=0.70, arp_rate=2, density=0.9, drums=0.35, bass_level=2),
    "upbeat":    dict(bpm=118, mode="major", prog="I V vi IV",      brightness=0.75, arp=0.60, arp_rate=2, density=1.0, drums=0.70, bass_level=2),
    "western":   dict(bpm=112, mode="minor", prog="i bVII i V",      brightness=0.45, arp=0.0, arp_rate=1, density=1.0, drums=0.0, bass_level=3,
                      lead=1, gallop=1, hoof=0.9, pad_level=0.45, key="E", energy=[0.45, 0.6, 0.85, 0.9, 0.85, 0.3]),
    "cinematic": dict(bpm=68,  mode="minor", prog="i bVI bIII bVII", brightness=0.40, arp=0.20, arp_rate=1, density=0.7, drums=0.0, bass_level=1),
}
DEFAULT_ENERGY = [(0.0, 0.25), (0.15, 0.40), (0.55, 0.80), (0.85, 0.85), (1.0, 0.30)]


def parse_key(s):
    m = re.fullmatch(r"([A-Ga-g])([#b]?)", s.strip())
    if not m: sys.exit(f"bad key: {s}")
    pc = NOTE_PC[m.group(1).upper()] + {"#": 1, "b": -1, "": 0}[m.group(2)]
    return pc % 12


def parse_chord(sym, tonic):
    m = re.fullmatch(r"([b#]?)([ivIV]+)(?:°|dim)?", sym)
    if not m or m.group(2).upper() not in NUMERAL: sys.exit(f"bad chord symbol: {sym}")
    off = NUMERAL[m.group(2).upper()] + {"b": -1, "#": 1, "": 0}[m.group(1)]
    return (tonic + off) % 12, ("maj" if m.group(2).isupper() else "min")


def mtof(m): return 440.0 * 2 ** ((m - 69) / 12)
def smooth(x, a, b): return float(np.clip((x - a) / (b - a), 0, 1))


def osc(freq, t, nh, rolloff, cents=0.0):
    f = freq * 2 ** (cents / 1200)
    out = np.zeros_like(t)
    for h in range(1, nh + 1):
        if f * h > 9000: break
        out += np.sin(2 * np.pi * f * h * t) / h ** rolloff
    return out


def add(buf, seg, start):
    """buf: (2,N) 或 (N,)；把 seg 叠加到 start，越界截断。"""
    if start >= buf.shape[-1] or start < 0: return
    n = min(seg.shape[-1], buf.shape[-1] - start)
    buf[..., start:start + n] += seg[..., :n]


def render_pad(chords, gains, bar_n, total_n, bright):
    buf = np.zeros((2, total_n))
    for i, (root, q) in enumerate(chords):
        last = i == len(chords) - 1
        rel = 1.1 if last else 0.35
        seg_n = min(bar_n + int(5 * rel * SR), total_n - i * bar_n)
        t = np.arange(seg_n) / SR
        bar_s = bar_n / SR
        env = np.minimum(t / 0.45, 1.0) * np.where(t < bar_s, 1.0, np.exp(-(t - bar_s) / rel))
        r = 48 + root
        notes = [r, r + (3 if q == "min" else 4), r + 7, r + 12]
        seg = np.zeros((2, seg_n))
        for k, m in enumerate(notes):
            w = 1.0 if k < 3 else 0.5
            seg[0] += w * osc(mtof(m), t, 6, 1.0, -6)
            seg[1] += w * osc(mtof(m), t, 6, 1.0, +6)
        add(buf, seg * env * 0.12 * gains["pad"][i], i * bar_n)
    sos = signal.butter(2, 500 + 4500 * bright ** 1.5, fs=SR, output="sos")
    return signal.sosfilt(sos, buf, axis=-1)


def render_bass(chords, gains, bar_n, beat_n, total_n, level):
    buf = np.zeros(total_n)
    for i, (root, q) in enumerate(chords):
        g = gains["bass"][i]
        if g < 0.03: continue
        last = i == len(chords) - 1
        if last: pat = [(0.0, 0)]
        elif level == 3: pat = [(b + o, off) for b in range(4) for o, off in ((0, 0), (0.5, 0), (0.75, 7))]  # 驰骋型
        else: pat = [(b, 0) for b in ([0.0, 2.0] if level == 1 else [0.0, 1.5, 2.0, 3.5])]
        for b, off in pat:
            f = mtof(36 + root + off)
            gal = level == 3 and not last
            dur = (3.5 if last else (0.5 if gal else 1.4)) * beat_n / SR
            t = np.arange(int(dur * SR)) / SR
            env = np.minimum(t / 0.006, 1) * np.exp(-t / (1.2 if last else (0.16 if gal else 0.4)))
            s = (np.sin(2 * np.pi * f * t) + 0.3 * np.sin(4 * np.pi * f * t)) * env
            add(buf, s * 0.5 * g, i * bar_n + int(b * beat_n))
    return buf


def render_arp(chords, gains, bar_n, beat_n, total_n, rate, density, rng):
    buf = np.zeros((2, total_n))
    step = beat_n / rate
    seq = [0, 1, 2, 3, 2, 1]
    for i, (root, q) in enumerate(chords[:-1]):
        g = gains["arp"][i]
        if g < 0.03: continue
        tones = [60 + root, 60 + root + (3 if q == "min" else 4), 60 + root + 7, 72 + root]
        for k in range(int(4 * rate)):
            if k > 0 and rng.random() > density: continue
            t = np.arange(int(0.9 * SR)) / SR
            f = mtof(tones[seq[k % 6]])
            s = (np.sin(2 * np.pi * f * t) + 0.4 * np.sin(4 * np.pi * f * t) + 0.15 * np.sin(6 * np.pi * f * t))
            s *= np.minimum(t / 0.003, 1) * np.exp(-t / 0.22)
            amp = 0.16 * g * (1.0 if k % rate == 0 else 0.7)
            pan = 0.35 if k % 2 else 0.65
            add(buf, np.stack([s * (1 - pan), s * pan]) * amp * 1.4, i * bar_n + int(k * step))
    d = int(0.75 * beat_n)  # 附点八分回声，左右交叉
    echo = buf.copy()
    for n, gg in ((1, 0.33), (2, 0.12)):
        sh = np.zeros_like(buf)
        if d * n < total_n: sh[:, d * n:] = buf[::-1, :total_n - d * n]
        echo += gg * sh
    return echo


def render_guitar(chords, gains, bar_n, beat_n, total_n, bright):
    """扭音吉他：驰骋节奏拨弦；末小节为轻扫的空五度和弦并长衰减。"""
    buf = np.zeros((2, total_n))
    for i, (root, q) in enumerate(chords):
        g = gains["guitar"][i]
        if g < 0.03: continue
        last = i == len(chords) - 1
        r = 48 + root
        if last:
            for k, m in enumerate([r, r + 7, r + 12]):
                t = np.arange(int(2.2 * SR)) / SR
                x = osc(mtof(m), t, 8, 0.8) * np.minimum(t / 0.004, 1) * np.exp(-t / 0.9)
                add(buf, np.stack([x, x]) * 0.16 * g, i * bar_n + int(k * 0.035 * SR))
            continue
        tones = [r, r + 7, r + 12, r + 7]
        n = 0
        for b in range(4):
            for o in (0, 0.5, 0.75):
                t = np.arange(int(0.45 * SR)) / SR
                x = osc(mtof(tones[n % 4]), t, 8, 0.8) * np.minimum(t / 0.003, 1) * np.exp(-t / 0.15)
                amp = 0.2 * g * (1.0 if o == 0 else 0.7)
                pan = 0.4 if n % 2 else 0.6
                add(buf, np.stack([x * (1 - pan), x * pan]) * amp * 1.4, i * bar_n + int((b + o) * beat_n))
                n += 1
    sos = signal.butter(2, 1500 + 3500 * bright, fs=SR, output="sos")
    return signal.sosfilt(sos, buf, axis=-1)


def render_lead(chords, gains, bar_n, beat_n, total_n, tonic, rng):
    """口哨主旋律：小调五声音阶，一问一答；末小节落在主音长音。"""
    buf = np.zeros(total_n)
    pent = [0, 3, 5, 7, 10, 12, 15, 17]
    base = 72 + tonic if tonic < 6 else 60 + tonic
    idx = 0
    phrases = [[(0, 1.5), (1.5, 0.5), (2, 1.0), (3, 1.0)], [(0, 1.0), (1, 1.0)], [(0, 0.5), (0.5, 0.5), (1, 1.0), (2, 2.0)], [(0, 2.0)]]
    for i, (root, q) in enumerate(chords):
        g = gains["lead"][i]
        last = i == len(chords) - 1
        if g < 0.03 and not last: continue
        notes = [(0.0, 3.5)] if last else phrases[i % len(phrases)]
        for k, (pos, ln) in enumerate(notes):
            if last: idx = 0
            elif k == 0:  # 每小节首音取和弦音（根/三/五音）附近
                ct = [(root + x) % 12 for x in (0, 3 if q == "min" else 4, 7)]
                cands = [j for j, x in enumerate(pent) if (tonic + x) % 12 in ct] or [idx]
                idx = min(cands, key=lambda j: abs(j - idx))
            else:
                idx = int(np.clip(idx + rng.choice([-2, -1, -1, 1, 1, 2]), 0, len(pent) - 1))
            f = mtof(base + pent[idx])
            d = ln * beat_n / SR * (1.0 if last else 0.92)
            n = int(d * SR) + int(0.1 * SR); t = np.arange(n) / SR
            vib = 0.006 * np.sin(2 * np.pi * 5.5 * t) * np.minimum(t / 0.3, 1)
            ph = 2 * np.pi * np.cumsum(f * (1 + vib)) / SR
            x = np.sin(ph) + 0.12 * np.sin(2 * ph)
            x += 0.02 * np.diff(rng.standard_normal(n + 1))  # 气声
            env = np.minimum(t / 0.04, 1) * np.where(t < d, 1.0, np.exp(-(t - d) / 0.05))
            if last: env = np.minimum(t / 0.04, 1) * np.exp(-t / 1.3)
            add(buf, x * env * 0.22 * (g if not last else 1.0), i * bar_n + int(pos * beat_n))
    return np.stack([buf * 0.55, buf * 0.45])


def render_hoof(gains, bar_n, beat_n, total_n, nbars, rng):
    """马蹄声：驰骋节奏的木质敲击，两个音高交替。"""
    buf = np.zeros(total_n)
    t = np.arange(int(0.07 * SR)) / SR
    sos = signal.butter(2, [600, 3500], btype="band", fs=SR, output="sos")
    click = signal.sosfilt(sos, rng.standard_normal(len(t)))
    for i in range(nbars - 1):
        g = gains["hoof"][i]
        if g < 0.03: continue
        n = 0
        for b in range(4):
            for o in (0, 0.5, 0.75):
                f = 780 if n % 2 == 0 else 1020
                x = (np.sin(2 * np.pi * f * t) * 0.6 + click * 0.5) * np.exp(-t / 0.018)
                add(buf, x * 0.3 * g * (1.0 if o == 0 else 0.7), i * bar_n + int((b + o) * beat_n))
                n += 1
    return buf


def render_drums(gains, bar_n, beat_n, total_n, nbars, drums_style, rng):
    buf = np.zeros(total_n)
    tk = np.arange(int(0.3 * SR)) / SR
    kick = np.sin(2 * np.pi * np.cumsum(45 + 90 * np.exp(-tk / 0.03)) / SR) * np.exp(-tk / 0.12)
    th = np.arange(int(0.06 * SR)) / SR
    hat = np.diff(rng.standard_normal(len(th) + 1)) * np.exp(-th / 0.015)
    ts = np.arange(int(0.15 * SR)) / SR
    sos = signal.butter(2, [1200, 5000], btype="band", fs=SR, output="sos")
    clap = signal.sosfilt(sos, rng.standard_normal(len(ts))) * np.exp(-ts / 0.05)
    four = drums_style >= 0.5
    for i in range(nbars - 1):
        g = gains["drums"][i]
        if g < 0.03: continue
        base = i * bar_n
        for b in ([0, 1, 2, 3] if four else [0, 2]):
            add(buf, kick * 0.9 * g, base + int(b * beat_n))
        for b in (0.5, 1.5, 2.5, 3.5):
            add(buf, hat * 0.22 * g, base + int(b * beat_n))
        if four:
            for b in (1, 3): add(buf, clap * 0.22 * g, base + int(b * beat_n))
    return buf


def reverb(x, wet, rng, sec=1.2):
    n = int(sec * SR)
    ir = rng.standard_normal(n) * np.exp(-np.arange(n) / (0.28 * SR))
    ir[0] = 0
    ir /= np.sqrt(np.sum(ir ** 2))
    y = np.stack([signal.fftconvolve(x[c], ir)[:x.shape[1]] for c in range(2)])
    return x * (1 - wet) + y * wet


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out"); ap.add_argument("--duration", type=float, required=True)
    ap.add_argument("--style", default="tech", choices=list(STYLES))
    ap.add_argument("--profile"); ap.add_argument("--bpm", type=float)
    ap.add_argument("--key"); ap.add_argument("--mode", choices=["major", "minor"])
    ap.add_argument("--prog"); ap.add_argument("--energy")
    ap.add_argument("--brightness", type=float); ap.add_argument("--drums", type=float)
    ap.add_argument("--arp", type=float); ap.add_argument("--arp-rate", type=int, choices=[1, 2, 4])
    ap.add_argument("--tail", type=float, default=2.0); ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args()

    p = dict(key="C", energy=None, lead=0, gallop=0, hoof=0, pad_level=1.0); p.update(STYLES[a.style])
    if a.profile:
        pr = json.load(open(a.profile, encoding="utf-8"))["compose_hints"]
        p.update({k: v for k, v in pr.items() if v is not None})
    for k, v in (("bpm", a.bpm), ("key", a.key), ("mode", a.mode), ("prog", a.prog),
                 ("brightness", a.brightness), ("drums", a.drums), ("arp", a.arp), ("arp_rate", a.arp_rate)):
        if v is not None: p[k] = v
    if a.energy: p["energy"] = [float(x) for x in a.energy.split(",")]

    body = a.duration - a.tail
    if body < 4: sys.exit("duration 太短（正文需 ≥4s，可减小 --tail）")
    bpm = float(p["bpm"])
    bars = max(2, round(body / (240 / bpm)))
    bpm_used = 240 * bars / body
    if abs(bpm_used / bpm - 1) > 0.12:
        print(f"WARN: 为凑整数小节，bpm {bpm:.0f} -> {bpm_used:.1f}（偏离>12%）", file=sys.stderr)
    beat_n = int(round(60 / bpm_used * SR)); bar_n = 4 * beat_n
    total_n = int(round(a.duration * SR))

    tonic = parse_key(p["key"])
    prog = p["prog"].split()
    chords = [parse_chord(prog[i % len(prog)], tonic) for i in range(bars)]
    chords[-1] = (tonic, "min" if p["mode"] == "minor" else "maj")

    if p["energy"]:
        e = np.interp(np.linspace(0, 1, bars), np.linspace(0, 1, len(p["energy"])), p["energy"])
    else:
        xs, ys = zip(*DEFAULT_ENERGY); e = np.interp(np.linspace(0, 1, bars), xs, ys)
    e[-1] = min(e[-1], 0.3)

    gains = dict(
        pad=[0.55 + 0.45 * x for x in e],
        bass=[smooth(x, 0.18, 0.32) for x in e],
        arp=[p["arp"] * smooth(x, 0.30, 0.45) for x in e],
        drums=[p["drums"] * smooth(x, 0.50, 0.65) for x in e],
        guitar=[smooth(x, 0.25, 0.4) for x in e],
        lead=[smooth(x, 0.5, 0.65) for x in e],
        hoof=[p["hoof"] * smooth(x, 0.3, 0.45) for x in e],
    )
    gains["pad"] = [v * p["pad_level"] for v in gains["pad"]]
    rng = np.random.default_rng(a.seed)
    pad = render_pad(chords, gains, bar_n, total_n, p["brightness"])
    arp = render_arp(chords, gains, bar_n, beat_n, total_n, int(p["arp_rate"]), p["density"], rng)
    bass = render_bass(chords, gains, bar_n, beat_n, total_n, int(p["bass_level"]))
    drums = render_drums(gains, bar_n, beat_n, total_n, bars, p["drums"], rng)

    music = pad + arp
    extra = 0.0
    if p["gallop"]:
        music = music + render_guitar(chords, gains, bar_n, beat_n, total_n, p["brightness"])
        extra = extra + render_hoof(gains, bar_n, beat_n, total_n, bars, rng) * 0.9
    if p["lead"]:
        music = music + render_lead(chords, gains, bar_n, beat_n, total_n, tonic, rng)
    music = reverb(music, 0.2, rng)
    mix = music + bass * 0.55 + drums * 0.6 + extra
    mix = np.tanh(mix * 1.1)
    mix[:, :int(0.015 * SR)] *= np.linspace(0, 1, int(0.015 * SR))
    mix *= 0.7 / max(np.abs(mix).max(), 1e-9)  # 峰值约 -3 dBFS
    sf.write(a.out, mix.T.astype(np.float32), SR, subtype="PCM_16")

    plan = dict(duration=a.duration, tail=a.tail, bars=bars, bpm=round(bpm_used, 2), key=p["key"], mode=p["mode"],
                progression=prog, energy_per_bar=[round(float(x), 2) for x in e], brightness=p["brightness"],
                drums=p["drums"], arp=p["arp"], arp_rate=p["arp_rate"], seed=a.seed, style=a.style, profile=a.profile)
    json.dump(plan, open(re.sub(r"\.\w+$", "", a.out) + ".plan.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(plan, ensure_ascii=False))


if __name__ == "__main__":
    main()
