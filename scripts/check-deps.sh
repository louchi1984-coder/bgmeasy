#!/usr/bin/env bash
# 检查 bgm skill 的工具依赖。用法: check-deps.sh
# 必需项缺失时退出码为 1；可选项缺失只给出提示。
set -u
PYTHON=${BGMEASY_PYTHON:-}
if [ -z "$PYTHON" ]; then
  for candidate in python3 python; do
    if command -v "$candidate" >/dev/null && "$candidate" -c "import sys" >/dev/null 2>&1; then
      PYTHON=$candidate; break
    fi
  done
fi
[ -n "$PYTHON" ] || { echo "缺少可用 Python；可用 BGMEASY_PYTHON 指定解释器" >&2; exit 1; }
fail=0
ok()   { printf '  [OK]      %s\n' "$1"; }
miss() { printf '  [MISSING] %s\n    -> %s\n' "$1" "$2"; }
opt()  { printf '  [OPTIONAL-MISSING] %s\n    -> %s\n' "$1" "$2"; }

echo "必需（合成 / 混音 / 验收）"
for c in ffmpeg ffprobe; do
  if command -v "$c" >/dev/null; then ok "$c  $(command -v $c)"; else miss "$c" "brew install ffmpeg python"; fail=1; fi
done
if command -v ffmpeg >/dev/null; then
  for f in loudnorm sidechaincompress apad afade ebur128; do
    if ffmpeg -hide_banner -filters 2>/dev/null | grep -qE " $f "; then ok "ffmpeg filter: $f"; else miss "ffmpeg filter: $f" "换用带完整滤镜的 ffmpeg 构建（brew install ffmpeg）"; fail=1; fi
  done
fi
if [ -n "$PYTHON" ]; then
  "$PYTHON" -X utf8 - <<'PY' || fail=1
import sys
v = sys.version_info
print(f"  [{'OK' if v >= (3,9) else 'MISSING'}]      python >= 3.9  (当前 {v.major}.{v.minor}.{v.micro})")
bad = 0
for m in ("numpy", "scipy", "soundfile"):
    try:
        mod = __import__(m); print(f"  [OK]      python: {m} {getattr(mod,'__version__','')}")
    except Exception:
        print(f"  [MISSING] python: {m}\n    -> python3 -m pip install {m}"); bad = 1
sys.exit(1 if (bad or v < (3,9)) else 0)
PY
fi

echo "可选（仅「分析参考曲 / 模仿」需要）"
if [ -n "$PYTHON" ] && "$PYTHON" -X utf8 -c "import librosa" 2>/dev/null; then
  ok "python: librosa $("$PYTHON" -X utf8 -c 'import librosa;print(librosa.__version__)')"
else
  opt "python: librosa" "python3 -m pip install librosa   （没有它仍可 compose / mix / verify，但不能 analyze / imitate）"
fi
command -v fluidsynth >/dev/null && ok "fluidsynth $(fluidsynth --version 2>/dev/null | head -1)" || opt "fluidsynth" "brew install fluid-synth   （采样音色渲染）"
"$PYTHON" -X utf8 -c "import pedalboard" 2>/dev/null && ok "python: pedalboard" || opt "python: pedalboard" "python3 -m pip install pedalboard   （效果器链）"
"$PYTHON" -X utf8 -c "import mido" 2>/dev/null && ok "python: mido" || opt "python: mido" "python3 -m pip install mido   （MIDI 读写）"
[ -f "$(dirname "$0")/../soundfonts/GeneralUser-GS.sf2" ] && ok "音色库 GeneralUser-GS.sf2" || opt "音色库 soundfonts/GeneralUser-GS.sf2" "见 references/dependencies.md「已下载的音色库」"
light_manifest="$(dirname "$0")/../soundfonts/freepats-light/manifest.json"
if [ -f "$light_manifest" ]; then
  "$PYTHON" -X utf8 -I - "$light_manifest" <<'PY' || fail=1
import json, pathlib, sys
p = pathlib.Path(sys.argv[1]); data = json.loads(p.read_text(encoding='utf-8')); root = p.parent.parent
missing = [a['file'] for a in data['assets'] if not (root / a['file']).is_file()]
if missing:
    print(f"  [MISSING] 轻量音源文件: {missing}"); sys.exit(1)
print(f"  [OK]      轻量音色库 {len(data['assets'])} 个 SF2；下载 {data['download_bytes'] / 1e6:.1f} MB")
PY
else
  opt "FreePats 轻量扩充" "见 references/soundfonts.md；现有音色仍可用"
fi
command -v afplay >/dev/null && ok "afplay（macOS 试听）" || opt "afplay / 任意播放器" "用于人工核听；缺失不影响生成"

echo
if [ $fail -eq 0 ]; then echo "必需依赖齐全。"; else echo "必需依赖不全，先补齐再用。"; fi
exit $fail
