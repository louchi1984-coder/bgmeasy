#!/usr/bin/env python3
"""原生 Python 混音入口；沿用 mix.sh 的 FFmpeg 滤镜、参数和两遍 loudnorm。"""
import argparse
import json
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import localization as I18N
from localization import translate as translate_text
import tempfile


def probe(video, *options):
    return subprocess.check_output(['ffprobe', '-v', 'error', *options, video],
                                   text=True, encoding='utf-8', errors='replace').strip()


def mix(a):
    duration = probe(a.video, '-show_entries', 'format=duration', '-of', 'csv=p=0')
    has_audio = probe(a.video, '-select_streams', 'a', '-show_entries', 'stream=index', '-of', 'csv=p=0')
    keep = a.keep_audio and bool(has_audio)
    if a.keep_audio and not has_audio:
        print(translate_text('WARN: 视频没有音轨，忽略 --keep-audio'), file=sys.stderr)

    inputs = ['-i', a.bgm]
    if a.vo:
        inputs += ['-i', a.vo]
    bg = (f'[0:a]aresample=48000,aformat=channel_layouts=stereo,volume={a.bgm_db}dB,'
          f'apad,atrim=0:{duration},asetpts=N/SR/TB')
    if a.fade_out != 0:
        bg += f',afade=t=out:st={max(0, float(duration)-a.fade_out)}:d={a.fade_out}'
    graph = bg + '[bgm]'
    foreground = []
    if a.vo:
        graph += ';[1:a]aresample=48000,aformat=channel_layouts=stereo[vo]'
        foreground.append('[vo]')
    if keep:
        index = len(inputs) // 2
        inputs += ['-i', a.video]
        graph += f';[{index}:a]aresample=48000,aformat=channel_layouts=stereo[orig]'
        foreground.append('[orig]')
    if not foreground:
        graph += ';[bgm]anull[m]'
    else:
        if len(foreground) == 1:
            graph += f';{foreground[0]}anull[fg]'
        else:
            graph += ';[vo][orig]amix=inputs=2:normalize=0:duration=longest[fg]'
        graph += (f';[fg]asplit=2[fgk][fgm];[bgm][fgk]sidechaincompress=threshold=0.03:'
                  f'ratio={a.duck_ratio}:attack=20:release=500:makeup=1[bgmd];'
                  '[bgmd][fgm]amix=inputs=2:normalize=0:duration=longest[m]')

    with tempfile.TemporaryDirectory() as directory:
        intermediate = str(Path(directory) / 'mix.wav')
        subprocess.run(['ffmpeg', '-v', 'error', '-y', *inputs, '-filter_complex', graph,
                        '-map', '[m]', '-t', duration, intermediate], check=True)
        measured = subprocess.run(['ffmpeg', '-hide_banner', '-i', intermediate, '-af',
                                   f'loudnorm=I={a.lufs}:TP={a.tp}:LRA=11:print_format=json',
                                   '-f', 'null', '-'], check=True, capture_output=True,
                                  text=True, encoding='utf-8', errors='replace')
        text = measured.stderr
        levels = json.loads(text[text.index('{'):text.rindex('}')+1])
        normalization = (f'loudnorm=I={a.lufs}:TP={a.tp}:LRA=11:'
                         f'measured_I={levels["input_i"]}:measured_TP={levels["input_tp"]}:'
                         f'measured_LRA={levels["input_lra"]}:measured_thresh={levels["input_thresh"]}:'
                         f'offset={levels["target_offset"]}:linear=true,aresample=48000')
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', a.video, '-i', intermediate,
                        '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'aac',
                        '-b:a', '192k', '-shortest', '-af', normalization, a.out], check=True)
    print(f'-> {a.out}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('video', 'bgm', 'out'):
        parser.add_argument('--'+name, required=True)
    parser.add_argument('--vo')
    parser.add_argument('--keep-audio', action='store_true')
    for name, default in [('bgm-db', -16), ('duck-ratio', 6), ('fade-out', 0), ('lufs', -14), ('tp', -2.0)]:
        parser.add_argument('--'+name, type=float, default=default)
    I18N.add_argument(parser)
    args = parser.parse_args()
    I18N.use_language(args.lang)
    try:
        mix(args)
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        print(translate_text('混音失败: {v0}', v0=error), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    if sys.platform == 'win32':
        for stream in (sys.stdout, sys.stderr):
            if hasattr(stream, 'reconfigure'):
                stream.reconfigure(encoding='utf-8', errors='backslashreplace')
    sys.exit(main())
