#!/usr/bin/env bash
# 把 BGM 混进视频：旁白/原声触发闪避，两遍 loudnorm，视频流直接复制。
# 用法: mix.sh --video in.mp4 --bgm bgm.wav --out out.mp4
#         [--vo vo.wav] [--keep-audio] [--bgm-db -16] [--duck-ratio 6]
#         [--fade-out 0] [--lufs -14] [--tp -2.0]
# --keep-audio  保留 in.mp4 自带声音（对白/演示声），与 --vo 一起作为前景触发闪避
# --bgm-db      BGM 相对前景的基础增益（无前景时作用于整体，之后仍归一到 --lufs）
# --fade-out    视频末尾额外淡出秒数；BGM 已按 compose 落定时保持 0
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
VIDEO=; BGM=; OUT=; VO=; KEEP=0; BGMDB=-16; RATIO=6; FADE=0; LUFS=-14; TP=-2.0
while [ $# -gt 0 ]; do case $1 in
  --video) VIDEO=$2; shift 2;; --bgm) BGM=$2; shift 2;; --out) OUT=$2; shift 2;;
  --vo) VO=$2; shift 2;; --keep-audio) KEEP=1; shift;; --bgm-db) BGMDB=$2; shift 2;;
  --duck-ratio) RATIO=$2; shift 2;; --fade-out) FADE=$2; shift 2;;
  --lufs) LUFS=$2; shift 2;; --tp) TP=$2; shift 2;; *) echo "unknown arg $1"; exit 2;; esac; done
[ -n "$VIDEO" ] && [ -n "$BGM" ] && [ -n "$OUT" ] || { sed -n '2,9p' "$0"; exit 2; }
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$VIDEO")
HASA=$(ffprobe -v error -select_streams a -show_entries stream=index -of csv=p=0 "$VIDEO" | head -1)
[ "$KEEP" = 1 ] && [ -z "$HASA" ] && { echo "WARN: 视频没有音轨，忽略 --keep-audio" >&2; KEEP=0; }

IN=(-i "$BGM"); FG=()
if [ -n "$VO" ]; then IN+=(-i "$VO"); FG+=("[$(( ${#IN[@]}/2 - 0 - 0 ))]"); fi
# 输入索引: 0=bgm, (1=vo), 末位=video(用于原声)
BG="[0:a]aresample=48000,aformat=channel_layouts=stereo,volume=${BGMDB}dB,apad,atrim=0:${DUR},asetpts=N/SR/TB"
[ "$FADE" != 0 ] && BG="$BG,afade=t=out:st=$("$PYTHON" -X utf8 -c "print(max(0,$DUR-$FADE))"):d=$FADE"
FC="$BG[bgm]"
FGL=()
if [ -n "$VO" ]; then FC="$FC;[1:a]aresample=48000,aformat=channel_layouts=stereo[vo]"; FGL+=("[vo]"); fi
if [ "$KEEP" = 1 ]; then
  VI=$(( ${#IN[@]} / 2 )); IN+=(-i "$VIDEO")
  FC="$FC;[${VI}:a]aresample=48000,aformat=channel_layouts=stereo[orig]"; FGL+=("[orig]")
fi
if [ ${#FGL[@]} -eq 0 ]; then
  FC="$FC;[bgm]anull[m]"
else
  if [ ${#FGL[@]} -eq 1 ]; then FC="$FC;${FGL[0]}anull[fg]"
  else FC="$FC;${FGL[0]}${FGL[1]}amix=inputs=2:normalize=0:duration=longest[fg]"; fi
  FC="$FC;[fg]asplit=2[fgk][fgm];[bgm][fgk]sidechaincompress=threshold=0.03:ratio=${RATIO}:attack=20:release=500:makeup=1[bgmd];[bgmd][fgm]amix=inputs=2:normalize=0:duration=longest[m]"
fi
ffmpeg -v error -y "${IN[@]}" -filter_complex "$FC" -map "[m]" -t "$DUR" "$TMP/mix.wav"

M=$(ffmpeg -hide_banner -i "$TMP/mix.wav" -af loudnorm=I=$LUFS:TP=$TP:LRA=11:print_format=json -f null - 2>&1 | sed -n '/^{/,/^}/p')
g() { echo "$M" | "$PYTHON" -X utf8 -c "import json,sys;print(json.load(sys.stdin)['$1'])"; }
ffmpeg -v error -y -i "$VIDEO" -i "$TMP/mix.wav" -map 0:v -map 1:a -c:v copy -c:a aac -b:a 192k -shortest \
  -af "loudnorm=I=$LUFS:TP=$TP:LRA=11:measured_I=$(g input_i):measured_TP=$(g input_tp):measured_LRA=$(g input_lra):measured_thresh=$(g input_thresh):offset=$(g target_offset):linear=true,aresample=48000" "$OUT"
echo "-> $OUT"
