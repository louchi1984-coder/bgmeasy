#!/usr/bin/env python3
"""对比参考曲与生成曲的 analyze 结果，量化「像不像」。
用法: compare.py ref.profile.json out.profile.json
只比较风格参数；相似度高不代表听感好，仍需人工核听。"""
import json, sys

if __name__ == "__main__" and sys.platform == "win32":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
import numpy as np
r, o = (json.load(open(p, encoding="utf-8")) for p in sys.argv[1:3])
def row(n, a, b, ok): print(f"{n:<16}{str(a):<22}{str(b):<22}{'OK' if ok else 'DIFF'}")
print(f"{'项目':<16}{'参考':<22}{'生成':<22}结论")
row("bpm", r["bpm"], o["bpm"], abs(o["bpm"] / r["bpm"] - 1) < 0.08 or abs(o["bpm"] / r["bpm"] - 2) < 0.15 or abs(o["bpm"] / r["bpm"] - .5) < 0.08)
NM = ["C","C#","D","Eb","E","F","F#","G","Ab","A","Bb","B"]
def rel(p):  # 统一到大调等价主音，相对大小调视为同一音级集合
    k = NM.index(p["key"]); return k if p["mode"] == "major" else (k + 3) % 12
same = r["key"] == o["key"] and r["mode"] == o["mode"]
row("调式", f'{r["key"]} {r["mode"]}', f'{o["key"]} {o["mode"]}', same or rel(r) == rel(o))
if not same and rel(r) == rel(o): print("                  （相对大小调，音级集合相同，视为一致；和弦循环仍需对照）")
row("和弦循环", " ".join(r["chord_loop"] or []), " ".join(o["chord_loop"] or []), r["chord_loop"] == o["chord_loop"])
row("亮度", r["brightness"], o["brightness"], abs(r["brightness"] - o["brightness"]) < 0.2)
row("打击比例", r["percussive_ratio"], o["percussive_ratio"], abs(r["percussive_ratio"] - o["percussive_ratio"]) < 0.15)
a, b = np.array(r["energy_curve"]), np.array(o["energy_curve"])
c = float(np.corrcoef(a, b)[0, 1]) if a.std() > 0 and b.std() > 0 else float("nan")
row("能量曲线相关", "-", f"{c:.2f}", c > 0.6)
