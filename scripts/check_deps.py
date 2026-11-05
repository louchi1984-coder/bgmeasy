#!/usr/bin/env python3
"""原生 Python 依赖检查；必需项缺失退出 1，可选项缺失仅提示。"""
import argparse
import importlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import localization as I18N
from localization import translate as translate_text

ROOT = Path(__file__).resolve().parents[1]


def line(ok, name, optional=False):
    status = 'OK' if ok else 'OPTIONAL-MISSING' if optional else 'MISSING'
    print(f'  [{status}] {name}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    I18N.add_argument(parser)
    a = parser.parse_args()
    I18N.use_language(a.lang)
    failed = False
    print(translate_text('必需（合成 / 混音 / 验收）'))
    for name in ('ffmpeg', 'ffprobe'):
        path = shutil.which(name)
        line(bool(path), f"{name} {path or translate_text('：请加入 PATH')}")
        failed |= not bool(path)
    if shutil.which('ffmpeg'):
        result = subprocess.run(['ffmpeg', '-hide_banner', '-filters'], capture_output=True,
                                text=True, encoding='utf-8', errors='replace')
        for name in ('loudnorm', 'sidechaincompress', 'apad', 'afade', 'ebur128'):
            found = result.returncode == 0 and bool(re.search(r'\s'+name+r'\s', result.stdout))
            line(found, f'ffmpeg filter: {name}')
            failed |= not found
    supported = sys.version_info >= (3, 9)
    line(supported, translate_text('python >= 3.9（当前 {v0}，{v1}）', v0=sys.version.split()[0], v1=sys.executable))
    failed |= not supported
    for name in ('numpy', 'scipy', 'soundfile', 'librosa', 'pedalboard', 'mido'):
        optional = name in ('librosa', 'pedalboard', 'mido')
        try:
            module = importlib.import_module(name)
            line(True, f'python: {name} {getattr(module, "__version__", "")}')
        except Exception:
            line(False, translate_text('python: {v0}；用当前解释器 -m pip install {v1}', v0=name, v1=name), optional)
            failed |= not optional
    line(bool(shutil.which('fluidsynth')), translate_text('fluidsynth（采样音色渲染）'), optional=True)
    line((ROOT/'soundfonts/GeneralUser-GS.sf2').is_file(), translate_text('音色库 GeneralUser-GS.sf2'), optional=True)
    manifest = ROOT/'soundfonts/freepats-light/manifest.json'
    if manifest.is_file():
        data = json.loads(manifest.read_text(encoding='utf-8'))
        missing = [a['file'] for a in data['assets'] if not (manifest.parent.parent/a['file']).is_file()]
        line(not missing, translate_text('轻量音色库 {v0} 个 SF2', v0=len(data['assets'])) + (translate_text('；缺失 {v0}', v0=missing) if missing else ''))
        failed |= bool(missing)
    else:
        line(False, translate_text('FreePats 轻量扩充'), optional=True)
    line(bool(shutil.which('afplay')), translate_text('afplay / 任意播放器（人工核听）'), optional=True)
    print(translate_text('必需依赖不全，先补齐再用。') if failed else translate_text('必需依赖齐全。'))
    return int(failed)


if __name__ == '__main__':
    if sys.platform == 'win32':
        for stream in (sys.stdout, sys.stderr):
            if hasattr(stream, 'reconfigure'):
                stream.reconfigure(encoding='utf-8', errors='backslashreplace')
    sys.exit(main())
