#!/usr/bin/env bash
# 模仿参考曲的风格，合成一首原创 BGM，并回读对比。
# 用法: imitate.sh REF.(mp3|wav|mp4) OUT.wav DURATION_SEC [compose.py 的额外参数...]
# 例:   imitate.sh ref.mp3 bgm.wav 32 --tail 2.5 --drums 0
# 只复制风格参数（速度/调式/和弦循环/能量走向/亮度/鼓组密度），不复制旋律或音频片段。
set -euo pipefail
PYTHON=${BGMEASY_PYTHON:-}
if [ -z "$PYTHON" ]; then
  for candidate in python3 python; do
    if command -v "$candidate" >/dev/null && "$candidate" -c "import sys" >/dev/null 2>&1; then
      PYTHON=$candidate; break
    fi
  done
fi
[ -n "$PYTHON" ] || { echo "缺少可用 Python；可用 BGMEASY_PYTHON 指定解释器" >&2; exit 1; }
[ $# -ge 3 ] || { sed -n '2,6p' "$0"; exit 2; }
REF=$1; OUT=$2; DUR=$3; shift 3
D=$(cd "$(dirname "$0")" && pwd); B="${OUT%.*}"
"$PYTHON" -X utf8 -I "$D/analyze.py" "$REF" "$B.ref.profile.json"
"$PYTHON" -X utf8 -I "$D/compose.py" "$OUT" --duration "$DUR" --profile "$B.ref.profile.json" "$@" >/dev/null
"$PYTHON" -X utf8 -I "$D/analyze.py" "$OUT" "$B.out.profile.json" >/dev/null
echo "--- 参考 vs 生成 ---"
"$PYTHON" -X utf8 -I "$D/compare.py" "$B.ref.profile.json" "$B.out.profile.json"
echo "-> $OUT （计划见 $B.plan.json；务必试听）"
