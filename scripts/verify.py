#!/usr/bin/env python3
"""数值验收（不替代人耳）。用法: verify.py FILE(.mp4/.wav) [--lufs -14] [--tp -1.0]
检查: 综合响度/真峰值/LRA、开头静音、尾 1s 相对正文的电平差、削波、声道。"""
import argparse, json, re, subprocess
import numpy as np

import sys

from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import localization as I18N
from localization import translate as translate_text
if __name__ == "__main__" and sys.platform == "win32":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
ap = argparse.ArgumentParser(); ap.add_argument("f"); ap.add_argument("--lufs", type=float, default=-14)
I18N.add_argument(ap)
ap.add_argument("--tp", type=float, default=-1.0); a = ap.parse_args()
I18N.use_language(a.lang)
r = subprocess.run(["ffmpeg", "-hide_banner", "-i", a.f, "-vn", "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True, encoding="utf-8", errors="replace").stderr
tail = r[r.rfind("Summary:"):]
g = lambda k: float(re.search(k + r":\s+(-?[\d.]+)", tail).group(1))
I, LRA, TP = g("I"), g("LRA"), g("Peak")
pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", a.f, "-vn", "-ac", "1", "-ar", "22050", "-f", "f32le", "-"], capture_output=True).stdout
x = np.frombuffer(pcm, dtype=np.float32); sr = 22050
sec = len(x) // sr
rms = np.array([np.sqrt(np.mean(x[i*sr:(i+1)*sr] ** 2) + 1e-12) for i in range(sec)])
db = 20 * np.log10(rms)
lead = next((i for i, v in enumerate(db) if v > -50), sec)
body = np.median(db[:-1]) if sec > 3 else db.mean()
end = db[-1] - body
native_pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", a.f, "-vn", "-f", "f32le", "-"], capture_output=True).stdout
native = np.frombuffer(native_pcm, dtype=np.float32)
clip = int(np.sum(np.abs(native) >= 0.999))  # 原始声道/采样率；不下混或重采样
w = sr // 4; nw = len(x) // w
wdb = np.array([20 * np.log10(np.sqrt(np.mean(x[i*w:(i+1)*w] ** 2)) + 1e-9) for i in range(nw)])
ref = np.percentile(wdb[wdb > -60], 60) if (wdb > -60).any() else -20
alive = [i for i, v in enumerate(wdb) if v > ref - 10]
eff = (alive[-1] + 1) * w / sr if alive else 0.0; total = len(x) / sr
def line(n, v, ok, extra=""): print(f"[{'OK' if ok else 'CHECK'}] {n}: {v} {extra}")
line(translate_text('综合响度'), f"{I:.1f} LUFS", abs(I - a.lufs) <= 1.5, translate_text('(目标 {v0})', v0=a.lufs))
line(translate_text('真峰值'), f"{TP:.1f} dBTP", TP <= a.tp, translate_text('(上限 {v0})', v0=a.tp))
line(translate_text('响度范围 LRA'), f"{LRA:.1f} LU", LRA <= 14)
line(translate_text('开头静音'), f"{lead}s", lead <= 1)
line(translate_text('结尾最后 1s 相对正文'), f"{end:+.1f} dB", True, translate_text('(仅描述电平差；约 0 dB 表示末秒与正文电平接近，不能据此判断截断、高潮或是否落定；结合闭合、循环或开放结尾的设计核查)'))
line(translate_text('有效时长（电平在正文 -10 dB 内的最后时刻）'), translate_text('{v0:.1f}s / 总长 {v1:.1f}s', v0=eff, v1=total), total - eff <= 1.2, translate_text('(排查阈值为差值 ≤1.2s；超过时结合设计核查弱收、停顿或自然释放，不直接判断早停或终止质量)'))
line(translate_text('削波采样数'), clip, clip == 0)
print(translate_text('提示: 以上只是数值。是否好听、对白是否清晰、结尾是否真正落定，必须实际播放核听。'))
