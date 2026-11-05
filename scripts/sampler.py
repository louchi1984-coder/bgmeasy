"""小型采样器：用 VCSL(CC0) 的 WAV 单音采样演奏 Dan Tranh（越南十六弦筝，当作古筝近似）、Gong、Bass Drum（当作大鼓近似）。

按音高选最近采样并重采样变调（限 ±5 半音），按力度选层。音高由自相关估计，不依赖文件名里的音名。
首次使用会分析采样根音并写入 soundfonts/vcsl/map.json 缓存。
"""
import glob, json, os, re
import numpy as np
import soundfile as sf
from scipy import signal

SR = 44100
HERE = os.path.dirname(os.path.abspath(__file__))
DIR = os.path.normpath(os.path.join(HERE, "..", "soundfonts", "vcsl"))
NAMES = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def available():
    return os.path.isdir(DIR) and bool(glob.glob(os.path.join(DIR, "*.wav")))


def _load(path):
    x, sr = sf.read(path, dtype="float32", always_2d=True)
    x = x.T if x.shape[0] > 2 else x.T
    x = np.stack([x[0], x[1] if x.shape[0] > 1 else x[0]])
    if sr != SR: x = signal.resample_poly(x, SR, sr, axis=1).astype(np.float32)
    return x


def _f0_midi(mono, lo=60.0, hi=1200.0):
    seg = mono[int(0.05 * SR):int(0.45 * SR)].astype(np.float64)
    if len(seg) < 2000 or np.abs(seg).max() < 1e-4: return None
    seg = seg - seg.mean()
    ac = np.correlate(seg, seg, mode="full")[len(seg) - 1:]
    lag_lo, lag_hi = int(SR / hi), int(SR / lo)
    k = lag_lo + int(np.argmax(ac[lag_lo:lag_hi]))
    return 69 + 12 * np.log2((SR / k) / 440.0)


def _catalog():
    cache = os.path.join(DIR, "map.json")
    files = sorted(glob.glob(os.path.join(DIR, "*.wav")))
    if os.path.exists(cache):
        c = json.load(open(cache, encoding="utf-8"))
        if set(c) == {os.path.basename(f) for f in files}: return c
    c = {}
    for f in files:
        b = os.path.basename(f)
        if b.startswith("Dan Tranh__"):
            m = re.search(r"__([A-Ga-g][#b]?)(\d)_(mf|f)_", b)
            nm = m.group(1).upper() + m.group(1)[1:]
            guess = 12 * (int(m.group(2)) + 1) + NAMES[nm[0]] + (1 if "#" in nm else 0)
            est = _f0_midi(_load(f).mean(axis=0))
            # VCSL 的八度命名比标准 MIDI 低一个八度；以自相关估计为准，估计缺失时用文件名 +12
            c[b] = dict(root=float(round(est)) if est is not None and abs(est - (guess + 12)) < 1.6 else float(guess + 12),
                        est=None if est is None else round(float(est), 2), name_guess=guess, layer=m.group(3), label=f"{nm}{m.group(2)}_{m.group(3)}")
        else:
            c[b] = {}
    json.dump(c, open(cache, "w", encoding="utf-8"), indent=1)
    return c


class Sampler:
    def __init__(self):
        self.cat = _catalog(); self.cache = {}

    def _get(self, base):
        if base not in self.cache: self.cache[base] = _load(os.path.join(DIR, base))
        return self.cache[base]

    def _pick(self, prefix, note, vel):
        fs = [(b, v) for b, v in self.cat.items() if b.startswith(prefix) and v.get("root") is not None and "root" in v]
        layer = "f" if vel >= 0.75 else "mf"
        pool = [x for x in fs if x[1]["layer"] == layer] or fs
        return min(pool, key=lambda x: abs(x[1]["root"] - note))

    def note(self, inst, note, vel, dur):
        """返回 (2,n) 数组。inst: dantranh|gong|bassdrum"""
        if inst == "dantranh":
            b, v = self._pick("Dan Tranh__", note, vel)
            sh = float(np.clip(note - v["root"], -5, 5))
            x = self._get(b)
            if abs(sh) > 1e-6:
                r = 2 ** (-sh / 12); n = int(x.shape[1] * r)
                x = np.stack([np.interp(np.linspace(0, x.shape[1] - 1, n), np.arange(x.shape[1]), c) for c in x])
            keep = int((max(dur, 1.4) + 0.6) * SR)
            x = x[:, :keep].copy(); fade = int(0.5 * SR)
            if x.shape[1] > fade: x[:, -fade:] *= np.linspace(1, 0, fade)
            return x * 0.9 * (0.55 + 0.45 * vel)
        if inst == "gong":
            names = sorted(b for b in self.cat if b.startswith("Gong 1__"))
            pick = [b for b in names if ("_f." in b)] if vel >= 0.85 else [b for b in names if "_mf." in b] or names
            x = self._get(pick[0])[:, :int(7.0 * SR)].copy(); fade = int(1.5 * SR)
            x[:, -fade:] *= np.linspace(1, 0, fade); return x * 0.8 * (0.5 + 0.5 * vel)
        if inst == "bassdrum":
            names = sorted(b for b in self.cat if b.startswith("Bass Drum 1__"))
            pick = names[min(int(vel * len(names)), len(names) - 1)]
            x = self._get(pick)[:, :int(2.5 * SR)].copy(); fade = int(0.4 * SR)
            x[:, -fade:] *= np.linspace(1, 0, fade); return x * 1.0
        raise ValueError(inst)
