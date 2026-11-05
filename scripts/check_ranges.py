#!/usr/bin/env python3
"""乐器音区检查：每个声部的音是否落在这件乐器的常用音域内。只读乐谱，提示不是判决。
用法: check_ranges.py score.json
查询: check_ranges.py --list-variants dizi
表: references/instrument-ranges.json 与 instrument-range-evidence.json。
原21个low条目须指定型号/定弦参照；图示范围外待复核，不等于不可演奏。
识别顺序: 声部指定的预设/GM program -> DSK 预设号 -> 内置 inst 名。识别不了的（合成器、pad、lead、鼓）跳过并说明。
"""
import argparse, json, os, sys

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
import render_score_sf2 as RS
import soundfonts as SF

NOTE = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]
nm = lambda m: f"{NOTE[m % 12]}{m // 12 - 1}"
ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("score", nargs="?")
ap.add_argument("--list-variants", metavar="INSTRUMENT_ID", help="查询已核查条目的型号/定弦与来源")
I18N.add_argument(ap)
a = ap.parse_args()
I18N.use_language(a.lang)
if a.lang != "zh": print(translate_text("原始引用资料保留原文。"))
T = json.load(open(os.path.join(HERE, "..", "references", "instrument-ranges.json"), encoding="utf-8"))
INS = T["instruments"]
E = json.load(open(os.path.join(HERE, "..", "references", T["range_evidence_file"]), encoding="utf-8"))
REVIEWS = {r["id"]: r for r in E["instruments"]}
VARIANTS = {v["id"]: (r["id"], v) for r in E["instruments"] for v in r["verified_variants"]}
if a.list_variants:
    if a.list_variants not in REVIEWS: ap.error(translate_text('此ID没有本次核查资料，请查instrument-performance.md与实际预设'))
    r = REVIEWS[a.list_variants]
    print(f"{r['name']} ({r['review_status']})\n{r['finding']}")
    for v in r["verified_variants"]:
        print(f"  {v['id']}: {v['name']} | {v['range'][0]}~{v['range'][1]} | {v['range_kind']}")
        print(translate_text('    条件: {v0}', v0=v['scope']))
        for k in ("additional_notes", "extra_extreme_notes", "missing_in_extension"):
            if v.get(k): print(f"    {k}: {', '.join(v[k])}")
    for sid in r["sources"]:
        s = E["sources"][sid]; print(translate_text('  来源: {v0} {v1}\n    限制: {v2}', v0=s['title'], v1=s['url'], v2=s['limits']))
    print(translate_text('参照不认证预设身份；未核实的舒适区及统一极限仍待核。'))
    sys.exit(0)
if not a.score: ap.error(translate_text('请提供乐谱路径，或使用--list-variants INSTRUMENT_ID'))
def gm_lookup(p):
    for k, v in T["gm_program_to_instrument"].items():
        lo, _, hi = k.partition("-")
        if int(lo) <= p <= int(hi or lo): return v
try: sc, bpb, tracks, arr, secs = R.load(a.score)
except R.ScoreError as e: sys.exit(translate_text('乐谱错误: {v0}', v0=e))
try:
    default_sf = os.path.join(HERE, "..", "soundfonts", "GeneralUser-GS.sf2")
    tracks = SF.resolve_tracks(tracks, default_sf, default_programs={k: v[0] for k, v in RS.GM.items()})
except Exception as e:
    print(translate_text('[注意] 预设解析失败，改用 inst 名识别: {v0}', v0=e))
def identify(cfg):
    if cfg.get("engine") == "sampler:dantranh": return "dan-tranh", "VCSL Dan Tranh采样器"
    if cfg["inst"] == "drums" or str(cfg.get("engine", "")).startswith("sampler:"): return None, "鼓/采样器，不检查"
    sf2 = os.path.splitext(os.path.basename(cfg.get("sf2") or ""))[0].lower(); prog = (cfg.get("gm") or {}).get("program")
    if sf2 in T["preset_stem_to_instrument"]:
        v = T["preset_stem_to_instrument"][sf2]
        return (v, sf2) if v else (None, "合成器/打击/pad，音区不检查")
    if sf2.startswith("dsk") and str(prog) in T["dsk_program_to_instrument"]: return T["dsk_program_to_instrument"][str(prog)], f"DSK program {prog}"
    if not sf2 or sf2.startswith("generaluser") :
        if prog is not None and gm_lookup(int(prog)): return gm_lookup(int(prog)), f"GM {prog}"
    if cfg["inst"] in T["inst_name_to_instrument"] and not cfg.get("preset") and not sf2: return T["inst_name_to_instrument"][cfg["inst"]], f"内置 {cfg['inst']}"
    return None, "合成器、音效或未收录音色"
seq = [(s, b) for s in arr for b in range(secs[s][0])]
print(translate_text('共 {v0} 小节\n', v0=len(seq)))
issues = 0; unchecked = []; conditional = []; review = []
for tr, cfg in tracks.items():
    key, why = identify(cfg)
    selection = cfg.get("range_variant")
    if selection is not None:
        if not isinstance(selection, str) or selection not in VARIANTS:
            issues += 1; print(translate_text('[CHECK] {v0}: 未知range_variant {v1!r}；用--list-variants查询，不会静默套用通用音域。', v0=tr, v1=selection)); continue
        if cfg["inst"] == "drums" or cfg.get("engine", "").startswith("sampler:") and cfg.get("engine") != "sampler:dantranh":
            issues += 1; print(translate_text('[CHECK] {v0}: 未对该鼓/采样器建立有音高的演奏参照。', v0=tr)); continue
    if not key and selection is None: unchecked.append(tr); print(translate_text('[未检查] {v0}: {v1}（没有检查不等于没问题）', v0=tr, v1=translate_text(why))); continue
    notes = []
    for i, (s, b) in enumerate(seq):
        evs = secs[s][1].get(tr); evs = evs[b] if evs else []
        for pos, d, ms, vel in evs or []:
            for m in ms: notes.append((i + 1, m))
    if not notes: continue
    if selection is not None:
        v = VARIANTS[selection][1]
        lo = min(m for _, m in notes); hi = max(m for _, m in notes)
        low, high = v["midi_range"]
        extra = set(v.get("additional_notes_midi", []) + v.get("extra_extreme_notes_midi", []))
        missing = set(v.get("missing_in_extension_midi", []))
        outside = [(b, m) for b, m in notes if not low <= m <= high and m not in extra]
        absent = [(b, m) for b, m in notes if m in missing]
        hard = absent or v["range_kind"] == "physical_bounds" and outside
        tag = "CHECK" if hard else "REVIEW" if outside else "范围内"
        if hard: issues += 1
        elif outside: review.append(tr)
        print(translate_text('[{v0}] {v1}: 实际 {v2}~{v3}；作者选择参照 {v4}（{v5}），资料范围 {v6}~{v7}', v0=translate_text(tag), v1=tr, v2=nm(lo), v3=nm(hi), v4=selection, v5=v['name'], v6=v['range'][0], v7=v['range'][1]))
        print(translate_text('      条件: {v0}；当前预设检索: {v1}。这是演奏参照，不认证音源身份。', v0=v['scope'], v1=translate_text(why)))
        if absent: print(translate_text('      该参照明确缺音: {v0}，小节 {v1}。', v0=', '.join(sorted({nm(m) for _, m in absent})), v1=sorted({b for b, _ in absent})[:10]))
        if outside:
            if v["range_kind"] == "physical_bounds": print(translate_text('      超出所选型号的物理键盘边界。'))
            else: print(translate_text('      {v0}个音在资料所示范围外，小节 {v1}；需另查，不等于不可演奏。', v0=len(outside), v1=sorted({b for b, _ in outside})[:10]))
        for k in ("additional_notes", "extra_extreme_notes"):
            if v.get(k): print(translate_text('      图示附加音: {v0}；未由端点推定额外半音或技法能力。', v0=', '.join(v[k])))
        source = E["sources"][v["source"]]
        print(translate_text('      来源: {v0} {v1}', v0=source['title'], v1=source['url']))
        print(translate_text('      范围内不保证舒适度、全部半音、快速技法或自然感。'))
        continue
    if INS[key].get("range_review"):
        r = REVIEWS[key]; conditional.append(tr)
        tag = "待核" if r["review_status"] == "absolute_endpoints_pending" else "条件"
        lo = min(m for _, m in notes); hi = max(m for _, m in notes)
        print(translate_text('[{v0}] {v1} ({v2}，来源 {v3}): 实际 {v4}~{v5}；未指定型号/定弦参照。', v0=translate_text(tag), v1=tr, v2=r['name'] if a.lang == 'zh' else I18N.instrument_name(key,a.lang), v3=why, v4=nm(lo), v5=nm(hi)))
        print(f"      {r['finding']}")
        if r["verified_variants"]: print(translate_text('      用--list-variants {v0}查询，再在适用声部写range_variant。', v0=key))
        print(translate_text('      旧通用common/extreme未核值不参与硬判定；没有判定不等于已验证可演奏。'))
        continue
    row = INS[key]; c0, c1 = row["common"]; e0, e1 = row["extreme"]
    lo = min(m for _, m in notes); hi = max(m for _, m in notes)
    out_c = [(b, m) for b, m in notes if not c0 <= m <= c1]; out_e = [(b, m) for b, m in notes if not e0 <= m <= e1]
    tag = "OK"
    if out_e: tag = "CHECK"; issues += 1
    elif out_c: tag = "注意"
    print(translate_text('[{v0}] {v1} ({v2}，来源 {v3}，把握 {v4}): 实际 {v5}~{v6}，常用 {v7}~{v8}，极端 {v9}~{v10}', v0=translate_text(tag), v1=tr, v2=row['name'] if a.lang == 'zh' else I18N.instrument_name(key,a.lang), v3=why, v4=row['confidence'], v5=nm(lo), v6=nm(hi), v7=nm(c0), v8=nm(c1), v9=nm(e0), v10=nm(e1)))
    if out_e: print(translate_text('      超出极端音域 {v0}/{v1} 个音，小节 {v2}：这件乐器几乎不会这样用，改音区或换乐器。', v0=len(out_e), v1=len(notes), v2=sorted({b for b, _ in out_e})[:10]))
    elif out_c: print(translate_text('      超出常用音域 {v0}/{v1} 个音，小节 {v2}：属于极端音区，确认是有意为之。', v0=len(out_c), v1=len(notes), v2=sorted({b for b, _ in out_c})[:10]))
    med = sorted(m for _, m in notes)[len(notes) // 2]; pos = (med - c0) / max(c1 - c0, 1)
    if tag != "CHECK" and pos < 0.25: print(translate_text('      [音区位置] 中位音 {v0} 落在常用音域的最低四分之一：这件乐器在此处音色较暗/较虚，若它承担主旋律请确认。', v0=nm(med)))
    if tag != "CHECK" and pos > 0.85: print(translate_text('      [音区位置] 中位音 {v0} 落在常用音域的最高处：音色会很尖，持续使用请确认。', v0=nm(med)))
    if row["confidence"] == "low": print(translate_text('      （把握低：民族乐器因型号定弦而异，数值仅作粗略提示，需核对具体型号。）'))
print(translate_text('\n共 {v0} 个声部需CHECK，{v1}个所选资料范围外待复核，{v2}个型号/端点有条件或待核，{v3}个未检查。未纳入21项核查的旧表行仍只是原有数值提示；范围内不认证技法、预设身份或听感。', v0=issues, v1=len(review), v2=len(conditional), v3=len(unchecked)))
