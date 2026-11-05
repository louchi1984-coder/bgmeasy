#!/usr/bin/env python3
"""频段能量占比对比：参考曲 vs 成品（可多个）。用来判断“薄/闷/糊”是不是频段失衡。
用法: compare_bands.py REF.(m4a|wav|mp3|mp4) OUT1.wav [OUT2.wav ...]
输出: 谱心，<150Hz、150-500Hz、500-2kHz、2-6kHz、>6kHz 的能量占比，以及与参考的差（百分点）。
常见读法: 低频占比远高于参考 -> 贝斯/底鼓太重，挤掉中频，听起来反而薄；中频(500-2k)偏低 -> 缺主奏/和声的存在感。
数值接近不等于好听，仍要听。依赖 numpy、ffmpeg。"""
import subprocess, sys

if __name__ == "__main__" and sys.platform == "win32":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
import numpy as np

EDGES = [(0, 150), (150, 500), (500, 2000), (2000, 6000), (6000, 11025)]
NAMES = ["<150", "150-500", "500-2k", "2k-6k", ">6k"]


def load(path):
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vn", "-ac", "1", "-ar", "22050", "-f", "f32le", "-"],
                         capture_output=True).stdout
    if not pcm: sys.exit(f"无法读取 {path}")
    return np.frombuffer(pcm, dtype=np.float32)


def bands(x, sr=22050):
    P = np.abs(np.fft.rfft(x)) ** 2; f = np.fft.rfftfreq(len(x), 1 / sr); t = P.sum()
    return (f * P).sum() / t, [P[(f >= a) & (f < b)].sum() / t for a, b in EDGES]


if len(sys.argv) < 3: sys.exit(__doc__)
rc, rb = bands(load(sys.argv[1]))
print(f"{'':<14}{'谱心Hz':>7} " + " ".join(f"{n:>8}" for n in NAMES))
print(f"{'参考':<12}{rc:7.0f} " + " ".join(f"{v:8.1%}" for v in rb))
for p in sys.argv[2:]:
    c, b = bands(load(p)); name = p.split("/")[-1][:14]
    print(f"{name:<14}{c:7.0f} " + " ".join(f"{v:8.1%}" for v in b))
    print(f"{'  与参考差':<12}{c - rc:+7.0f} " + " ".join(f"{(v - r) * 100:+7.1f}p" for v, r in zip(b, rb)))
    notes = []
    if b[0] - rb[0] > 0.12: notes.append("低频明显偏多：降贝斯/底鼓，否则会挤掉中频")
    if rb[2] - b[2] > 0.08: notes.append("500Hz-2kHz 偏少：缺中频存在感，检查主奏和中间声部的音区与音量")
    if rb[3] - b[3] > 0.03: notes.append("高频偏少：可能偏闷")
    if notes: print("  提示: " + "；".join(notes))
