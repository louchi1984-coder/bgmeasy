#!/usr/bin/env python3
"""只读谱面关系描述：拍位和声、素材匹配、乐句末音、休止与跳进。

用法: check_melody.py score.json [--tracks lead,erhu]

旋律声部: 默认取 inst 为 lead/whistle/dizi/xiao/erhu/bell 的声部，或 design.melody 列出的声部，或 --tracks。
和弦来源（按优先级）:
  1. design.chords: 段落名 -> 每小节和弦（不够则循环）；小节可为字符串或
     [{"beat": 0, "chord": "C/G"}, {"beat": 2, "chord": "Am7"}]。
  2. 没写则从和声声部（pad/strings/organ/keys/pluck/bass/sub 等非旋律、非鼓声部）每小节的音推断
写了 design.chords 最准；推断只是近似，报告会注明来源。
不以首拍比例、原样重复、末音主音或休止比例判定质量。格式错误仍报错。
design.phrases 可指定全曲1起算的小节范围；未指定时只描述段落边界，不假定乐句。
素材匹配保留起音/休止并跨小节搜索，仍不证明辨识度、发展或听感合格。
"""
import argparse, os, re, sys

from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import localization as I18N
from localization import translate as translate_text

if __name__ == "__main__" and sys.platform == "win32":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import render_score as R

NOTE = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]
MELODY_INST = {"lead", "whistle", "dizi", "xiao", "erhu", "bell"}
HARMONY_INST = {"pad", "strings", "organ", "keys", "pluck", "bass", "sub", "marimba", "guzheng", "pipa"}
QUAL = {"": (0, 4, 7), "m": (0, 3, 7), "dim": (0, 3, 6), "7": (0, 4, 7, 10), "maj7": (0, 4, 7, 11), "m7": (0, 3, 7, 10),
        "sus4": (0, 5, 7), "sus2": (0, 2, 7), "5": (0, 7), "aug": (0, 4, 8),
        "6": (0, 4, 7, 9), "m6": (0, 3, 7, 9), "dim7": (0, 3, 6, 9), "m7b5": (0, 3, 6, 10),
        "add9": (0, 4, 7, 14), "madd9": (0, 3, 7, 14), "9": (0, 4, 7, 10, 14),
        "maj9": (0, 4, 7, 11, 14), "m9": (0, 3, 7, 10, 14),
        "11": (0, 4, 7, 10, 14, 17), "m11": (0, 3, 7, 10, 14, 17),
        "13": (0, 4, 7, 10, 14, 17, 21), "maj13": (0, 4, 7, 11, 14, 17, 21), "m13": (0, 3, 7, 10, 14, 17, 21)}


def pc_of(name):
    m = re.fullmatch(r"([A-G])([#b]?)", name)
    return (R.PC[m.group(1)] + {"#": 1, "b": -1, "": 0}[m.group(2)]) % 12


def chord_set(name):
    m = re.fullmatch(r"([A-G][#b]?)([^/]*)(?:/([A-G][#b]?))?", name.strip())
    if not m or m.group(2) not in QUAL: return None, None
    r = pc_of(m.group(1)); cs = {(r + i) % 12 for i in QUAL[m.group(2)]}
    if m.group(3): cs.add(pc_of(m.group(3)))
    return cs, r


def chord_events(value, bpb, where):
    if isinstance(value, str): return [(0, *chord_set(value), value)]
    if not isinstance(value, list) or not value: raise R.ScoreError(f"{where}: 需要和弦名或非空和弦时间列表")
    out = []
    for item in value:
        if not isinstance(item, dict): raise R.ScoreError(f"{where}: 和弦时间项需要 beat/chord")
        pos, name = item.get("beat"), item.get("chord")
        if (not isinstance(pos, (int, float)) or isinstance(pos, bool) or not 0 <= pos < bpb
                or (not out and pos != 0) or (out and pos <= out[-1][0]) or not isinstance(name, str)):
            raise R.ScoreError(f"{where}: beat须从0开始严格递增且小于{bpb}，chord须为字符串")
        out.append((pos, *chord_set(name), name))
    return out


def chord_at(events, pos):
    return next((e[1:] for e in reversed(events) if e[0] <= pos + 1e-9), (None, None, "未知"))


def motif_events(text):
    text = R.expand(text.replace("|", " ")); tokens = text.split()
    if not tokens or any(not R.TOKEN.fullmatch(t) for t in tokens): return [], 0
    span = sum(R.num(R.TOKEN.fullmatch(t).group(2)) for t in tokens)
    return R.parse_bar(text, span, "design.motif"), span


def motif_matches(seed, span, stream, bpb, total_beats):
    """匹配完整素材窗口；保留休止/拍位，不用短音程巧合作为关联证明。"""
    if len(seed) < 2: return []
    signature = lambda evs, base: [(round(p - base, 6), round(d, 6)) for p, d, ms, v in evs]
    pitches = lambda evs: [max(ms) for p, d, ms, v in evs]
    intervals = lambda pv: [b - a for a, b in zip(pv, pv[1:])]
    sp = pitches(seed); si = intervals(sp); matches = []
    for pos, _, _, _ in stream:
        base = pos - seed[0][0]
        if base < -1e-6 or base + span > total_beats + 1e-6: continue
        window = [e for e in stream if base - 1e-6 <= e[0] < base + span - 1e-6]
        if signature(window, base) != signature(seed, 0): continue
        pv = pitches(window); iv = intervals(pv)
        if pv == sp: tag = "原样" if abs(base / bpb - round(base / bpb)) < 1e-6 else "节奏位移"
        elif iv == si: tag = "移调（同起音/时值关系）"
        elif iv == [-v for v in si]: tag = "倒影线索（同起音/时值关系）"
        else: continue
        matches.append((round(base, 6), tag))
    return matches


def infer(events_by_track):
    w = {}
    low = None
    for evs in events_by_track:
        for pos, d, ms, vel in evs:
            for m in ms:
                w[m % 12] = w.get(m % 12, 0) + d
                if low is None or m < low: low = m
    if not w: return None, None
    top = max(w.values())
    return {p for p, v in w.items() if v >= 0.25 * top}, (low % 12 if low is not None else None)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("score"); ap.add_argument("--tracks", default="")
    I18N.add_argument(ap)
    a = ap.parse_args()
    I18N.use_language(a.lang)
    try: sc, bpb, tracks, arr, secs = R.load(a.score)
    except R.ScoreError as e: print(translate_text('乐谱错误: {v0}', v0=e), file=sys.stderr); sys.exit(2)
    design = sc.get("design") or {}
    mel = [t for t in a.tracks.split(",") if t] or list(design.get("melody") or []) or \
        [t for t, c in tracks.items() if c["inst"] in MELODY_INST]
    for t in mel:
        if t not in tracks: sys.exit(translate_text('没有声部 {v0}', v0=t))
    harm = [t for t, c in tracks.items() if c["inst"] in HARMONY_INST and t not in mel]
    if not mel: sys.exit(translate_text('没有找到旋律声部，用 --tracks 或 design.melody 指定'))
    mk = re.fullmatch(r"\s*([A-G][#b]?)\s*(major|minor)\s*", sc.get("key", "") or "")
    tonic = pc_of(mk.group(1)) if mk else None
    dch = design.get("chords") or {}
    if not isinstance(dch, dict): raise R.ScoreError("design.chords: 需要段落名到小节列表的映射")
    phr = design.get("phrases") or {}
    if not isinstance(phr, dict): raise R.ScoreError("design.phrases: 需要声部名到乐句列表的映射")

    # 展开成全曲小节序列
    seq = []  # (section, bar_in_section, bar_index_global)
    for s in arr:
        for b in range(secs[s][0]): seq.append((s, b, len(seq)))
    src = "design.chords" if dch else "由和声声部推断（近似）"
    chords = []
    for s, b, i in seq:
        if s in dch:
            if not isinstance(dch[s], list) or not dch[s]: raise R.ScoreError(f"design.chords.{s}: 需要非空小节列表")
            events = chord_events(dch[s][b % len(dch[s])], bpb, f"design.chords.{s}第{b + 1}小节")
        else:
            cs, root = infer([secs[s][1].get(t, [None] * secs[s][0])[b] or [] for t in harm])
            events = [(0, cs, root, "推断")]
        chords.append(events)

    print(translate_text('和弦来源: {v0} | 旋律声部: {v1} | 共 {v2} 小节\n', v0=translate_text(src), v1=', '.join(mel), v2=len(seq)))
    unknown = sorted({name for events in chords for p, cs, root, name in events if cs is None and name != "推断"})
    if unknown: print(translate_text('[INFO] 未识别和弦标签 {v0}，跳过相关音级判断；不表示和声错误。', v0=unknown))
    changes = [(i + 1, [(p, name) for p, cs, root, name in events]) for i, events in enumerate(chords) if len(events) > 1]
    if changes: print(translate_text('[INFO] 小节内和声时间（0起算拍位）: {v0}', v0=changes))
    print(translate_text('[REVIEW] 以下是谱面现象，不自动评审素材、乐句、节奏协作或听感质量。'))
    for key, label in (("rhythm", "共同节奏"), ("harmony", "和声与声部连接"), ("ending", "结束意图")):
        if design.get(key): print(translate_text('[INFO] {v0}（作者记录，须对照音符）: {v1}', v0=translate_text(label), v1=design[key]))
    review = design.get("motif_review")
    if not isinstance(review, dict):
        print(translate_text('[REVIEW] 缺少 design.motif_review：新作须记录职能、具体辨识点及声部/小节发展依据；旧谱仍可检查。'))
    else:
        for key, label in (("role", "素材职能"), ("identity", "辨识点"), ("phrase_plan", "乐句发展依据")):
            value = review.get(key)
            if isinstance(value, str) and value.strip():
                print(translate_text('[INFO] {v0}（作者记录，非自动验收）: {v1}', v0=translate_text(label), v1=value.strip()))
            else:
                print(translate_text('[REVIEW] design.motif_review.{v0} 未记录，请补充{v1}并复核实际音符。', v0=key, v1=translate_text(label)))
    print()
    for tr in mel:
        bars = [(secs[s][1].get(tr, [None] * secs[s][0])[b] or []) for s, b, i in seq]
        bars = [sorted(e, key=lambda x: x[0]) for e in bars]
        print(translate_text('=== 声部 {v0} ({v1}) ===', v0=tr, v1=tracks[tr]['inst']))
        if not any(bars):
            print(translate_text('[INFO] 此声部在展开编排中没有记谱音符。\n')); continue

        # 1 首拍
        hit = tot = 0; nonchord = []; free = 0
        for i, evs in enumerate(bars):
            cs, _, _ = chord_at(chords[i], 0)
            at0 = [e for e in evs if e[1] and abs(e[0]) < 1e-6]
            if not evs: continue
            if not at0: free += 1; continue
            if cs is None: continue
            tot += 1
            ok = any(m % 12 in cs for m in at0[0][2])
            if ok: hit += 1
            else: nonchord.append(i + 1)
        if tot:
            print(translate_text('[INFO] 首拍起音含和弦音: {v0}/{v1} 个可判断小节', v0=hit, v1=tot) + (translate_text('；首拍非和弦音小节: {v0}，按倚音/延留等实际去向复核，不按比例判差。', v0=nonchord) if nonchord else '') + (translate_text('；另有 {v0} 小节首拍无起音。', v0=free) if free else ''))
        else:
            print(translate_text('[INFO] 无可判断和声的首拍起音；有 {v0} 个有音小节首拍无起音。', v0=free))
        strong = [0, 0]
        for i, evs in enumerate(bars):
            for pos, d, ms, vel in evs:
                cs, _, _ = chord_at(chords[i], pos)
                if cs is None: continue
                if abs(pos - 2) < 1e-6 and bpb == 4: strong[1] += 1; strong[0] += any(m % 12 in cs for m in ms)
        if strong[1]: print(translate_text('[INFO] 第三拍落和弦音: {v0}/{v1}', v0=strong[0], v1=strong[1]))

        # 2 动机
        sig = lambda evs: tuple((round(p, 3), round(d, 3)) for p, d, ms, v in evs)
        piv = lambda evs: tuple(max(ms) for p, d, ms, v in evs)
        itv = lambda evs: tuple(b - a for a, b in zip(piv(evs), piv(evs)[1:]))
        ne = [(i, e) for i, e in enumerate(bars) if len(e) >= 2]
        seed, span = motif_events(str(design.get("motif") or ""))
        if len(seed) >= 2:
            stream = [(i * bpb + p, d, ms, v) for i, evs in enumerate(bars) for p, d, ms, v in evs]
            matches = motif_matches(seed, span, stream, bpb, len(bars) * bpb)
            print(translate_text('[INFO] 素材窗口 {v0:g} 拍（保留起音与休止，跨小节搜索）；匹配 {v1} 处。', v0=span, v1=len(matches)))
            for pos, tag in matches:
                print(translate_text('      第{v0}小节，0起算拍位{v1:g}: {v2}', v0=int(pos // bpb) + 1, v1=pos % bpb, v2=translate_text(tag)))
            if any(len(ms) > 1 for p, d, ms, v in seed + stream):
                print(translate_text('      多音事件仅比较最高音投影，不代表真实独立声部。'))
            print(translate_text('      原样重复可用于呈示/确认；未匹配不代表无关，匹配也不证明发展充分。'))
        elif not ne:
            print(translate_text('[INFO] 无可作逐小节比较的多起音材料；长音、纹理或跨小节关系另查整句。'))
        else:
            i0, m0 = ne[0]; cnt = dict(原样=0, 移调=0, 同节奏=0, 同音程开头=0, 其他=0)
            for i, e in ne[1:]:
                if sig(e) == sig(m0) and piv(e) == piv(m0): cnt["原样"] += 1
                elif sig(e) == sig(m0) and itv(e) == itv(m0): cnt["移调"] += 1
                elif sig(e) == sig(m0): cnt["同节奏"] += 1
                elif itv(e)[:3] == itv(m0)[:3] and len(itv(m0)) >= 3: cnt["同音程开头"] += 1
                else: cnt["其他"] += 1
            n = len(ne) - 1
            desc = "、".join(f"{translate_text(k)}{v}" for k, v in cnt.items() if v)
            if n == 0: print(translate_text('[INFO] 只有 1 个有旋律的小节（第 {v0} 小节）', v0=i0 + 1))
            else:
                print(translate_text('[INFO] 逐小节素材线索（第 {v0} 小节参考，非整句分析）: {v1}', v0=i0 + 1, v1=desc or translate_text('无')))
                print(translate_text('      重复、变化或未匹配均不自动判定质量；优先用实际素材与整句范围复核。'))

        # 3 句尾
        phrases = phr.get(tr)
        ranges = []
        if phrases is not None:
            if not isinstance(phrases, list): raise R.ScoreError(f"design.phrases.{tr}: 需要乐句列表")
            for phrase in phrases:
                if not isinstance(phrase, dict): raise R.ScoreError(f"design.phrases.{tr}: 乐句需要小节范围")
                start, end = phrase.get("start_bar"), phrase.get("end_bar")
                if type(start) is not int or type(end) is not int or not 1 <= start <= end <= len(bars):
                    raise R.ScoreError(f"design.phrases.{tr}: 范围须为1~{len(bars)}内的起止小节")
                ranges.append((start - 1, end - 1, translate_text('乐句{v0}–{v1}（作者功能: {v2}；目标: {v3}）', v0=start, v1=end, v2=phrase.get('function', translate_text('未注明')), v3=phrase.get('target', translate_text('未注明')))))
        else:
            start = 0
            for s in arr:
                end = start + secs[s][0] - 1
                ranges.append((start, end, translate_text('段落边界{v0}，非乐句判定', v0=s))); start = end + 1
        for start, end, label in ranges:
            sounding = [j for j in range(start, end + 1) if bars[j]]
            if not sounding:
                print(translate_text('[INFO] {v0}: 范围内无记谱音符。', v0=label)); continue
            j = sounding[-1]; e = bars[j][-1]; m = max(e[2])
            cs, root, name = chord_at(chords[j], min(e[0] + e[1], bpb) - 1e-6)
            tone = "和声未知" if cs is None else ("和弦音" if m % 12 in cs else "非和弦音")
            extra = translate_text('；距主音音级 {v0} 半音', v0=(m % 12 - tonic) % 12) if tonic is not None else ''
            print(translate_text('[INFO] {v0}: 第{v1}小节末个记谱音 {v2}{v3}，{v4}上的{v5}{v6}。', v0=label, v1=j + 1, v2=NOTE[m % 12], v3=m // 12 - 1, v4=translate_text(name) if name == "推断" else name, v5=translate_text(tone), v6=extra))
        print(translate_text('      末音位置不自动证明终止；结合低音、和声、节奏与结束意图复核。'))

        # 4 休止
        total = len(seq) * bpb; sound = 0.0
        for evs in bars:
            for p, d, ms, v in evs: sound += min(d, bpb - p)
        rest = 1 - sound / total
        print(translate_text('[INFO] 记谱休止比例 {v0:.0%}；按乐器、句法与用途判断，不设固定合格区间。', v0=rest))
        run = best = 0
        for evs in bars:
            full = bool(evs) and sum(min(d, bpb - p) for p, d, ms, v in evs) >= bpb - 1e-6
            run = run + 1 if full else 0; best = max(best, run)
        print(translate_text('[INFO] 最长连续无记谱休止 {v0} 小节；连断、音长、重心与演奏呼吸仍须另查。', v0=best))
        allm = [m for evs in bars for p, d, ms, v in evs for m in ms]
        if allm:
            top = [max(ms) for evs in bars for p, d, ms, v in evs]
            leaps = max((abs(b - a_) for a_, b in zip(top, top[1:])), default=0)
            print(translate_text('[INFO] 音域 {v0}~{v1}，相邻事件最高音最大跳进 {v2} 半音；按乐器和线条判断。', v0=min(allm), v1=max(allm), v2=leaps))
        print()
    print(translate_text('[REVIEW] 请对照共同节奏、完整乐句与声部连接复核；以上数值/匹配不判定创作合格。听感仍须实际核听。'))


if __name__ == "__main__":
    try: main()
    except R.ScoreError as e:
        print(translate_text('乐谱/检查注释错误: {v0}', v0=e), file=sys.stderr); sys.exit(2)
