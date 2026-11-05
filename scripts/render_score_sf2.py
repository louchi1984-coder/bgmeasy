#!/usr/bin/env python3
"""采样后端：同一份 score.json -> MIDI -> FluidSynth(SF2 音色库) -> pedalboard 母带 -> WAV。

用法: render_score_sf2.py score.json OUT.wav [--duration 15] [--tail 0.8] [--soundfont X.sf2] [--keep-mid]
依赖: fluidsynth, mido, pedalboard, numpy, soundfile，以及 SF2 音色库（默认 soundfonts/GeneralUser-GS.sf2）。

乐器 -> GM 音色是近似映射（见 GM 表），没有二胡/古筝/琵琶/竹笛的真实对应：
  - 可在 score 的声部里用 "gm": {"program": 40} 覆盖该声部的 GM 音色号（0 起算）。
鼓组在 MIDI 通道 10；大鼓(taiko)与锣(gong)用旋律通道的 Taiko Drum / Tubular Bells 近似。
"""
import argparse, json, math, os, shutil, subprocess, sys, tempfile

from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import localization as I18N
from localization import translate as translate_text

if __name__ == "__main__" and sys.platform == "win32":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import numpy as np
import soundfile as sf
import mido
import render_score as R
import sampler as SMP
import soundfonts as SF

# 乐谱乐器 -> (GM 程序号 0 起算, 说明)
GM = dict(
    pad=(89, "Warm Pad"), strings=(48, "String Ensemble 1"), pluck=(25, "Acoustic Guitar (steel)"),
    bass=(33, "Electric Bass (finger)"), sub=(38, "Synth Bass 1"), lead=(80, "Lead 1 (square)"),
    whistle=(78, "Whistle"), organ=(19, "Church Organ"), keys=(4, "Electric Piano 1"), bell=(9, "Glockenspiel"),
    marimba=(12, "Marimba"), guzheng=(107, "Koto"), pipa=(106, "Shamisen"), erhu=(110, "Fiddle"),
    dizi=(73, "Flute"), xiao=(77, "Shakuhachi"),
)
DRUM_NOTE = dict(kick=36, snare=38, hat=42, openhat=46, clap=39, rim=37, tom=45, hoof=76, shaker=70, cowbell=56, bangzi=77, crash=49, ride=51)
MELODIC_DRUMS = dict(taiko=(116, 43, "Taiko Drum"), gong=(14, 48, "Tubular Bells"))
# GM 音色库里持续音色（弦乐/垫音/管风琴）普遍比拨弦响得多，按乐器补偿音量，避免盖住旋律与层次
GAIN_COMP = dict(dantranh=2.6, gong=0.55, bassdrum=1.0, pad=0.5, strings=0.5, organ=0.6, sub=0.8, whistle=0.4, dizi=0.6, erhu=0.7, lead=0.6)
TPB = 480
CALIBRATE = False  # 实验功能：按 soundfonts/loudness.json 折算 gain；默认关闭（实测未优于手填补偿系数），--calibrate 打开
CAL_FLOOR_DB = -3.0  # 比钢琴轻于此值的预设不再提升（避免 CC7 超上限），其 gain 按原值
def _load_loudness():
    try: return json.load(open(os.path.join(HERE, "..", "soundfonts", "loudness.json"), encoding="utf-8"))["presets"]
    except Exception: return {}
LOUD = _load_loudness()
def cal_factor(sf2, bank, prog):
    """返回 (系数, 预设id或None)。FluidSynth 的 CC7 衰减约为 40*log10(cc/127) dB，故系数=10^(-(rel-floor)/40)，且不大于 1。"""
    stem = os.path.splitext(os.path.basename(sf2 or "GeneralUser-GS.sf2"))[0].lower()
    pid = f"{stem}:{bank}:{prog}"
    if not CALIBRATE or pid not in LOUD: return 1.0, None
    return min(1.0, 10 ** (-(LOUD[pid] - CAL_FLOOR_DB) / 40)), pid
COMP_RATIO = 2.0  # 母带压缩比；--comp-ratio 1.0 即几乎不压，保留段落动态
CH_SF = {}  # MIDI 通道 -> 外部音色库文件名（声部写 "sf2" 时使用）


def erhu_pitch_events(notes, params, channel, ticks_per_second):
    """把合成后端的 bend（半音）和 vibrato（频率比例）转换为单声部 MIDI 弯音。"""
    bend, vib = float(params.get("bend", 0)), float(params.get("vibrato", 0))
    if not (bend or vib): return []
    if abs(bend) + 12 * math.log2(1 + abs(vib)) > 2:
        raise R.ScoreError("二胡 bend 与 vibrato 的总幅度不能超过2个半音")
    # 明确设置弯音范围 ±2 半音，再关闭 RPN 选择，避免依赖音源的默认范围。
    events = [(0, -1, mido.Message("control_change", channel=channel, control=cc, value=value))
              for cc, value in ((101, 0), (100, 0), (6, 2), (38, 0), (101, 127), (100, 127))]
    notes = sorted(notes)
    step = max(1, round(ticks_per_second / 100))
    for i, (start, stop) in enumerate(notes):
        # 人性化时差可能使相邻音符轻微重叠；新音开始前停止旧音的控制曲线。
        stop = min(stop, notes[i + 1][0] - 1) if i + 1 < len(notes) else stop
        for tick in range(start, stop, step):
            t = (tick - start) / ticks_per_second
            depth = vib * min(max((t - .2) / .3, 0), 1)
            semitones = -bend * math.exp(-t / .07)
            semitones += 12 * math.log2(1 + depth * math.sin(2 * math.pi * 5.8 * t))
            pitch = int(np.clip(round(semitones / 2 * 8192), -8192, 8191))
            events.append((tick, 0, mido.Message("pitchwheel", channel=channel, pitch=pitch)))
        if stop >= start:
            events.append((stop, 0, mido.Message("pitchwheel", channel=channel, pitch=0)))
    return events


def build_midi(sc, bpb, tracks, arr, secs, bpm, total_beats, tail_beats, seed):
    CH_SF.clear()
    rng = np.random.default_rng(seed); hum = float(sc.get("humanize_ms", 6)) / 1000
    tps = TPB * bpm / 60  # ticks per second
    chans, pitched = {}, [c for c in range(16) if c != 9]
    ev = {}  # channel -> [(tick, order, msg)]
    info = []
    sev = []  # 采样器事件: (track, sampler_inst, time_beats, dur_beats, midi, vel, gain, pan)
    erhu_notes = {}
    use_smp = SMP.available()

    def chan_for(key, prog, bank=0):
        if key not in chans:
            c = chans[key] = pitched.pop(0)
            ev[c] = [(0, -2, mido.Message("control_change", channel=c, control=0, value=bank >> 7)),
                     (0, -2, mido.Message("control_change", channel=c, control=32, value=bank & 127)),
                     (0, -1, mido.Message("program_change", channel=c, program=prog))]
        return chans[key]

    ev[9] = []
    for tr, cfg in tracks.items():
        gain, pan = float(cfg.get("gain", 0.8)), float(cfg.get("pan", 0)); rev = float(cfg.get("reverb", 0.15))
        if cfg["inst"] == "drums":
            for lane in ("__drums",):
                gain *= cal_factor(cfg.get("sf2"), int(cfg.get("gm", {}).get("bank", 128)), int(cfg.get("gm", {}).get("program", 0)))[0]
                ev[9].append((0, -1, mido.Message("control_change", channel=9, control=7, value=int(min(127, gain * 127)))))
                ev[9].append((0, -1, mido.Message("control_change", channel=9, control=10, value=int(64 + pan * 63))))
            kit = int(cfg.get("gm", {}).get("program", 0))  # 鼓组：GM 0 标准、8 房间、16 力量、24 电子、25 TR-808（GeneralUser GS）
            bank = int(cfg.get("gm", {}).get("bank", 128))
            ev[9].append((0, -2, mido.Message("control_change", channel=9, control=0, value=bank >> 7)))
            ev[9].append((0, -2, mido.Message("control_change", channel=9, control=32, value=bank & 127)))
            ev[9].append((0, -1, mido.Message("program_change", channel=9, program=kit)))
            if cfg.get("sf2"): CH_SF[9] = cfg["sf2"]
            info.append((tr, "drums", f"{cfg.get('sf2', '默认音色库')} bank {bank} / program {kit}: {cfg.get('_preset_name', '鼓组')}"))
        elif cfg.get("engine", "").startswith("sampler:"):
            info.append((tr, cfg["inst"], f"VCSL 采样器 {cfg['engine'][8:]}（CC0）"))
        else:
            prog = int(cfg.get("gm", {}).get("program", GM[cfg["inst"]][0]))
            bank = int(cfg.get("gm", {}).get("bank", 0))
            ch = chan_for(("t", tr), prog, bank)
            if cfg.get("sf2"): CH_SF[ch] = cfg["sf2"]
            cf, pid = cal_factor(cfg.get("sf2"), bank, prog)
            gain *= cf if pid else GAIN_COMP.get(cfg["inst"], 1.0)
            for cc, v in ((7, int(min(127, gain * 127))), (10, int(64 + pan * 63)), (91, int(min(127, rev * 127 * 1.3)))):
                ev[ch].append((0, -1, mido.Message("control_change", channel=ch, control=cc, value=v)))
            desc = cfg.get('_preset_name', GM[cfg['inst']][1] if 'gm' not in cfg else '自定义')
            info.append((tr, cfg["inst"], f"{cfg.get('sf2', '默认音色库')} bank {bank} / program {prog}: {desc}"))

    swing = float(sc.get("swing", 0)); bar_i = 0
    for sname in arr:
        nb, bars = secs[sname]
        lvl = float((sc.get("dynamics") or {}).get(sname, 1.0))  # 段落整体力度 0~1：对所有通道发 CC11
        for chn in list(ev):
            ev[chn].append((int(bar_i * bpb * TPB), -1, mido.Message("control_change", channel=chn, control=11, value=int(np.clip(lvl * 127, 1, 127)))))
        for b in range(nb):
            for tr, cfg in tracks.items():
                evs = bars.get(tr, [None] * nb)[b]
                if not evs: continue
                if cfg["inst"] == "drums":
                    for pos, name, vel in evs:
                        t0 = int((bar_i * bpb + pos) * TPB); v = int(np.clip(vel * 127, 1, 127))
                        custom_notes = cfg.get("drum_notes", {})
                        if custom_notes and name not in custom_notes:
                            raise R.ScoreError(f"{tr}: 所选鼓库未映射鼓件 {name}，可用 {list(custom_notes)}")
                        if name in ("taiko", "gong") and name not in custom_notes and use_smp and not cfg.get("gm_drums"):
                            sev.append((tr, "bassdrum" if name == "taiko" else "gong", bar_i * bpb + pos, 4.0, 0, vel * lvl, float(cfg.get("gain", .8)), float(cfg.get("pan", 0))))
                            continue
                        if name in custom_notes:
                            ch, note = 9, custom_notes[name]
                        elif name in MELODIC_DRUMS:
                            prog, note, desc = MELODIC_DRUMS[name]; ch = chan_for(("m", name), prog)
                            if not any(m.type == "control_change" and m.control == 7 for _, _, m in ev[ch]):
                                ev[ch].append((0, -1, mido.Message("control_change", channel=ch, control=7, value=int(min(127, float(cfg.get("gain", .8)) * 127)))))
                                ev[ch].append((0, -1, mido.Message("control_change", channel=ch, control=91, value=int(min(127, float(cfg.get("reverb", .2)) * 127 * 1.3)))))
                        else:
                            ch, note = 9, DRUM_NOTE[name]
                        ev[ch].append((t0, 1, mido.Message("note_on", channel=ch, note=note, velocity=v)))
                        ev[ch].append((t0 + int(0.25 * TPB), 0, mido.Message("note_off", channel=ch, note=note, velocity=0)))
                elif cfg.get("engine", "").startswith("sampler:"):
                    P = cfg.get("params", {})
                    for pos, d, ms, vel in evs:
                        base = (bar_i * bpb + pos) + (rng.uniform(-hum, hum) * tps / TPB if hum else 0)
                        for k, m in enumerate(ms):
                            sev.append((tr, cfg["engine"][8:], max(base + k * P.get("strum", 0) * tps / TPB, 0), d, m, vel * lvl, float(cfg.get("gain", .8)), float(cfg.get("pan", 0))))
                else:
                    ch = chans[("t", tr)]; P = cfg.get("params", {})
                    for pos, d, ms, vel in evs:
                        expressive_erhu = cfg["inst"] == "erhu" and (P.get("bend") or P.get("vibrato"))
                        if expressive_erhu and len(ms) != 1:
                            raise R.ScoreError(f"{tr}: 二胡弯音控制仅支持单音旋律，不能用于和弦")
                        base = (bar_i * bpb + pos) * TPB
                        if swing and abs((pos % 1) - 0.5) < 1e-6: base += swing * TPB / 3
                        base += rng.uniform(-hum, hum) * tps if hum else 0
                        for k, m in enumerate(ms):
                            t0 = max(int(base + k * P.get("strum", 0) * tps), 0); t1 = t0 + max(int(d * TPB * 0.97), 1)
                            ev[ch].append((t0, 1, mido.Message("note_on", channel=ch, note=m, velocity=int(np.clip(vel * 115, 1, 127)))))
                            ev[ch].append((t1, 0, mido.Message("note_off", channel=ch, note=m, velocity=0)))
                            if expressive_erhu: erhu_notes.setdefault(ch, (P, []))[1].append((t0, t1))
            bar_i += 1
    for ch, (params, notes) in erhu_notes.items():
        ev[ch].extend(erhu_pitch_events(notes, params, ch, tps))
    end_tick = int((total_beats + tail_beats) * TPB)
    ev.setdefault(15, []).append((end_tick, 2, mido.Message("control_change", channel=15, control=7, value=100)))

    mid = mido.MidiFile(type=1, ticks_per_beat=TPB)
    meta = mido.MidiTrack(); meta.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(bpm), time=0)); mid.tracks.append(meta)
    for ch, lst in ev.items():
        trk = mido.MidiTrack(); last = 0
        for tick, _, msg in sorted(lst, key=lambda x: (x[0], x[1])):
            trk.append(msg.copy(time=tick - last)); last = tick
        mid.tracks.append(trk)
    return mid, info, sev


def _chan_of(trk):
    for m in trk:
        if hasattr(m, "channel"): return m.channel
    return None


def sub_midi(mid, chans):
    """只保留指定通道的音轨（含速度轨）。"""
    out = mido.MidiFile(type=1, ticks_per_beat=mid.ticks_per_beat)
    for i, trk in enumerate(mid.tracks):
        if i == 0 or _chan_of(trk) in chans: out.tracks.append(trk)
    return out


def fluid(sfs, midi_obj, tmp, tag, sr=44100):
    midp = os.path.join(tmp, tag + ".mid"); raw = os.path.join(tmp, tag + ".wav"); midi_obj.save(midp)
    r = subprocess.run(["fluidsynth", "-ni", "-q", "-o", "synth.midi-bank-select=mma", "-g", "1.0", "-r", str(sr), "-F", raw, *sfs, midp], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode or not os.path.exists(raw): sys.exit(translate_text('fluidsynth 渲染失败:\n') + r.stderr[-800:])
    x, _ = sf.read(raw, dtype="float32"); return x.T if x.ndim > 1 else np.stack([x, x])


def master(x, sr):
    from pedalboard import Pedalboard, HighpassFilter, Compressor, Reverb, Limiter
    board = Pedalboard([HighpassFilter(30), Compressor(threshold_db=-20, ratio=COMP_RATIO, attack_ms=25, release_ms=250),
                        Reverb(room_size=0.3, damping=0.6, wet_level=0.1, dry_level=0.9), Limiter(threshold_db=-2.0)])
    return board(x.astype(np.float32), sr)


def report_levels(a, tracks, secs, arr):
    """保留音符与随机时序，逐层将gain置零，取未归一化的差信号RMS。"""
    td = tempfile.mkdtemp()
    with open(a.score, encoding="utf-8") as f: original = json.load(f)
    # 先保留父命令已有的静音状态；新增的逐层对照只改gain，不删事件。
    for mt in a.mute.split(","):
        if mt:
            for section in original["sections"].values(): section.pop(mt, None)
    common = ["--lang", I18N.CURRENT_LANGUAGE, "--raw-level", "--comp-ratio", str(a.comp_ratio), "--tail", str(a.tail), "--soundfont", a.soundfont] + (["--duration", str(a.duration)] if a.duration else []) + (["--calibrate"] if a.calibrate else []) + (["--seed", str(a.seed)] if a.seed is not None else [])
    def run(name, mute=None):
        out = os.path.join(td, name + ".wav")
        score = dict(original); score["tracks"] = {t: dict(cfg) for t, cfg in original["tracks"].items()}
        if mute: score["tracks"][mute]["gain"] = 0
        score_path = os.path.join(td, name + ".json")
        with open(score_path, "w", encoding="utf-8") as f: json.dump(score, f)
        result = subprocess.run([sys.executable, "-I", os.path.abspath(__file__), score_path, out] + common, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if result.returncode or not os.path.isfile(out):
            raise R.ScoreError(f"{name} 子渲染失败（exit={result.returncode}）: {result.stderr[-800:]}")
        return sf.read(out, dtype="float32")[0]
    def db(z):
        rms = float(np.sqrt(np.mean(z ** 2)))
        return 20 * np.log10(rms) if rms else float("-inf")
    try:
        full = run("full")
        rows = []
        for t in tracks:
            if not any(secs[s][1].get(t) for s in arr): continue
            # gain已经为零时两份乐谱完全相同，复用同一次渲染，零能量为-inf dB。
            b = full if float(tracks[t].get("gain", .8)) == 0 else run("m_" + t, t)
            n = min(len(full), len(b)); rows.append((t, db(full[:n] - b[:n])))
    finally:
        shutil.rmtree(td, ignore_errors=True)
    if not rows: return
    top = max(v for _, v in rows)
    print(translate_text('\n各层实际贡献（未归一化，整体 {v0:.1f} dB；差信号 RMS，越接近 0 越响）', v0=db(full)))
    print(f"{translate_text('声部'):<12}{translate_text('贡献dB'):>8}{translate_text('比最响层'):>10}")
    weak = []
    for t, v in sorted(rows, key=lambda x: -x[1]):
        d = 0.0 if v == top else v - top; flag = ""
        if d < -12: flag = translate_text("   <-- 比最响层低 12 dB 以上，可能听不清"); weak.append(t)
        print(f"{t:<12}{v:8.1f}{d:+10.1f}{flag}")
    print(translate_text('说明：-inf dB表示零能量。这是整段差信号平均能量，包含共享母带处理的响应变化，不是独立分轨电平；稀疏/短音/鼓的贡献天然偏低。数值不替代听感。') + (translate_text(' 偏低的层: {v0}。', v0=', '.join(weak)) if weak else ''))

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("score"); ap.add_argument("out")
    ap.add_argument("--duration", type=float); ap.add_argument("--tail", type=float, default=0.8)
    ap.add_argument("--soundfont", default=os.path.join(HERE, "..", "soundfonts", "GeneralUser-GS.sf2"))
    ap.add_argument("--mute", default="", help="逗号分隔的声部名，渲染时静音（调试/分轨检查）")
    ap.add_argument("--comp-ratio", type=float, default=2.0)
    ap.add_argument("--report-levels", action="store_true", help="渲染后逐层静音相减，报告各层对整体的实际贡献（约多渲染 N 次）")
    ap.add_argument("--raw-level", action="store_true", help="不做最终峰值归一化（报告各层贡献时内部使用；不要用于交付）")
    ap.add_argument("--calibrate", action="store_true", help="实验：按响度校准表折算 gain，替代手填补偿系数")
    I18N.add_argument(ap)
    ap.add_argument("--seed", type=int); ap.add_argument("--keep-mid", action="store_true"); a = ap.parse_args()
    I18N.use_language(a.lang)
    global CALIBRATE; CALIBRATE = a.calibrate
    global COMP_RATIO; COMP_RATIO = max(a.comp_ratio, 1.0)
    if not os.path.exists(a.soundfont): sys.exit(translate_text('找不到音色库 {v0}（见 references/dependencies.md）', v0=a.soundfont))
    if not shutil.which("fluidsynth"): sys.exit(translate_text('缺少 fluidsynth：请安装并加入 PATH（见 references/dependencies.md）'))
    try: sc, bpb, tracks, arr, secs = R.load(a.score)
    except R.ScoreError as e: print(translate_text('乐谱错误: {v0}', v0=e), file=sys.stderr); sys.exit(2)
    try: tracks = SF.resolve_tracks(tracks, a.soundfont, default_programs={k: v[0] for k, v in GM.items()})
    except ValueError as e: print(translate_text('音色错误: {v0}', v0=e), file=sys.stderr); sys.exit(2)
    seed = a.seed if a.seed is not None else int(sc.get("seed", 7))
    nbars = sum(secs[s][0] for s in arr); beats = nbars * bpb; bpm = float(sc.get("bpm", 100))
    if a.duration:
        used = 60 * beats / (a.duration - a.tail)
        if abs(used / bpm - 1) > 0.08: print(translate_text('WARN: bpm {v0:g} -> {v1:.1f}（偏离>8%）', v0=bpm, v1=used), file=sys.stderr)
        bpm = used
    tail_beats = a.tail * bpm / 60
    for mt in [x for x in a.mute.split(",") if x]:
        if mt not in sc["tracks"]: sys.exit(translate_text('--mute: 没有声部 {v0}', v0=mt))
        for sec in sc["sections"].values(): sec.pop(mt, None)
    R_secs = secs
    for _, bars in R_secs.values():
        for mt in a.mute.split(","):
            bars.pop(mt, None)
    try: mid, info, sev = build_midi(sc, bpb, tracks, arr, secs, bpm, beats, tail_beats, seed)
    except R.ScoreError as e: print(translate_text('乐谱错误: {v0}', v0=e), file=sys.stderr); sys.exit(2)
    tmp = tempfile.mkdtemp(); sr = 44100
    ext = {}
    for ch, name in CH_SF.items(): ext.setdefault(name, set()).add(ch)
    main_chans = {c for c in range(16)} - set(CH_SF)
    x = fluid([a.soundfont], sub_midi(mid, main_chans), tmp, "main")
    total = int(round((beats * 60 / bpm + a.tail) * sr))
    x = x[:, :total] if x.shape[1] >= total else np.pad(x, ((0, 0), (0, total - x.shape[1])))
    for font_i, (name, chans) in enumerate(ext.items()):
        path = os.path.join(HERE, "..", "soundfonts", name)
        if not os.path.exists(path): sys.exit(translate_text('找不到声部指定的音色库 {v0}', v0=path))
        e = fluid([path], sub_midi(mid, chans), tmp, f"ext_{font_i}")
        e = e[:, :total] if e.shape[1] >= total else np.pad(e, ((0, 0), (0, total - e.shape[1])))
        x = x + e
    if sev:  # 把 VCSL 采样器声部叠加到 FluidSynth 渲染结果上
        smp = SMP.Sampler(); spb = 60.0 / bpm
        for tr, inst, tb, db, midi, vel, g, pan in sev:
            n = smp.note(inst, midi, vel, db * spb)
            th = (pan + 1) * np.pi / 4
            n = n * g * np.array([[np.cos(th)], [np.sin(th)]]) * np.sqrt(2) * GAIN_COMP.get(inst, 1.0)
            st = int(tb * spb * sr)
            if st < total:
                e = min(st + n.shape[1], total); seg = n[:, :e - st].copy()
                if st + n.shape[1] > total:  # 采样比乐谱总长还长：在结尾前淡出，避免硬切尾音
                    f = min(int(1.5 * sr), seg.shape[1]); seg[:, -f:] *= np.linspace(1, 0, f) ** 2
                x[:, st:e] += seg
    y = master(x, sr)[:, :total]
    nf = int(0.01 * sr); y[:, :nf] *= np.linspace(0, 1, nf); 
    if not a.raw_level: y *= 0.7 / max(float(np.abs(y).max()), 1e-9)
    sf.write(a.out, y.T, sr, subtype="PCM_16")
    if a.keep_mid: mid.save(os.path.splitext(a.out)[0] + ".mid")
    print(translate_text('[sf2] bpm {v0:.1f} | {v1} 小节 | 总长 {v2:.2f}s | 音色库 {v3}', v0=bpm, v1=nbars, v2=total / sr, v3=os.path.basename(a.soundfont)))
    for tr, inst, desc in info: print(f"  {tr:<9}{inst:<9}-> {desc}")
    if a.report_levels and not a.raw_level:
        try: report_levels(a, tracks, secs, arr)
        except R.ScoreError as e: sys.exit(translate_text('逐层报告失败: {v0}', v0=e))


if __name__ == "__main__":
    main()
