"""Build the CC0 erhu SF2 from the pinned, extracted upstream repository.

Usage: python3 -I build_erhu.py /path/to/aliexpress-erhu /path/to/output
Requires the project's existing numpy, scipy and soundfile dependencies.
This asset preparation script is separate from the standard music renderer.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import struct

import numpy as np
from scipy.signal import resample_poly
import soundfile as sf

COMMIT = '6615047b2fd06126877483e97b8bb4af9d00b080'
SOURCE = 'https://github.com/sfzinstruments/aliexpress-erhu'
RATE = 32000
PRESETS = [('sus', i, f'Erhu Long Take {i}') for i in (1, 2)]
PRESETS += [('stac', i, f'Erhu Short Take {i}') for i in (1, 2, 3, 4)]
PRESETS += [('st', i, f'Erhu Tasto Take {i}') for i in (1, 2)]
PITCH = {'c': 0, 'db': 1, 'd': 2, 'eb': 3, 'e': 4, 'f': 5,
         'gb': 6, 'g': 7, 'ab': 8, 'a': 9, 'bb': 10, 'b': 11}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def chunk(tag, data):
    return tag + struct.pack('<I', len(data)) + data + b'\0' * (len(data) % 2)


def name(text):
    return text.encode('ascii')[:19].ljust(20, b'\0')


def root_note(path):
    pitch, octave = re.match(r'erhu_([a-g]b?)(\d)_', path.name).groups()
    # Upstream filename octave numbers are one above scientific pitch notation:
    # erhu_a5 is approximately 440 Hz (MIDI 69), not 880 Hz.
    return 12 * int(octave) + PITCH[pitch]


def build(source, output):
    output.mkdir(parents=True, exist_ok=True)
    files = sorted((source / 'Samples').rglob('*.wav'))
    if len(files) != 170:
        raise ValueError('Expected the 170 WAVs in the pinned upstream release')
    samples, headers, records = bytearray(), [], []
    sample_ids = {}
    cursor = 0
    for path in files:
        audio, rate = sf.read(path, always_2d=True)
        if rate != 44100 or audio.shape[1] != 2 or not np.isfinite(audio).all():
            raise ValueError(f'Unexpected source format: {path}')
        mono = resample_poly(audio.mean(axis=1), 320, 441)
        pcm = np.clip(np.rint(mono * 32768), -32768, 32767).astype('<i2')
        root = root_note(path)
        sample_ids[path.relative_to(source).as_posix()] = len(headers)
        headers.append(struct.pack('<20sIIIIIBbHH', name(path.stem), cursor,
                                   cursor + len(pcm), cursor, cursor + len(pcm) - 1,
                                   RATE, root, 0, 0, 1))
        records.append({'source_file': path.relative_to(source).as_posix(),
                        'source_sha256': digest(path), 'root_midi': root,
                        'frames': len(pcm), 'sample_rate': RATE,
                        'pcm_sha256': hashlib.sha256(pcm.tobytes()).hexdigest()})
        samples.extend(pcm.tobytes() + b'\0' * 92)
        cursor += len(pcm) + 46
    headers.append(struct.pack('<20sIIIIIBbHH', name('EOS'), cursor, cursor,
                               cursor, cursor, RATE, 0, 0, 0, 1))
    phdr, pbag, pgen, inst, ibag, igen = [], [], [], [], [], []
    preset_records = []
    for program, (art, take, label) in enumerate(PRESETS):
        phdr.append(struct.pack('<20sHHHIII', name(label), program, 0, len(pbag), 0, 0, 0))
        pbag.append(struct.pack('<HH', len(pgen), 0))
        pgen.append(struct.pack('<HH', 41, len(inst)))
        inst.append(struct.pack('<20sH', name(label), len(ibag)))
        selected = sorted((p for p in files if p.parent.name == art
                           and p.name.endswith(f'_rr{take}.wav')), key=root_note)
        roots = [root_note(p) for p in selected]
        for path, root in zip(selected, roots):
            ibag.append(struct.pack('<HH', len(igen), 0))
            # Exact recorded pitch only: do not silently stretch beyond coverage.
            for op, value in [(43, root | (root << 8)), (54, 0), (58, root),
                              (38, -2400), (53, sample_ids[path.relative_to(source).as_posix()])]:
                igen.append(struct.pack('<HH', op, value & 65535))
        chinese = {'sus': '二胡 长音', 'stac': '二胡 短音', 'st': '二胡 sul-tasto 指板附近运弓'}[art]
        preset_records.append({'program': program, 'bank': 0, 'name': label,
                               'display_name': f'{chinese} Take {take}', 'tags': chinese.split(),
                               'articulation': art, 'take': take, 'recorded_roots': roots,
                               'selection': 'Explicit preset; no automatic round robin'})
    phdr.append(struct.pack('<20sHHHIII', name('EOP'), 0, 0, len(pbag), 0, 0, 0))
    pbag.append(struct.pack('<HH', len(pgen), 0))
    pgen.append(b'\0' * 4)
    inst.append(struct.pack('<20sH', name('EOI'), len(ibag)))
    ibag.append(struct.pack('<HH', len(igen), 0))
    igen.append(b'\0' * 4)
    info = chunk(b'LIST', b'INFO' + chunk(b'ifil', struct.pack('<HH', 2, 1))
                 + chunk(b'isng', b'EMU8000\0') + chunk(b'INAM', b'CC0 Erhu Light\0\0'))
    tables = [(b'phdr', phdr), (b'pbag', pbag), (b'pmod', [b'\0' * 10]),
              (b'pgen', pgen), (b'inst', inst), (b'ibag', ibag),
              (b'imod', [b'\0' * 10]), (b'igen', igen), (b'shdr', headers)]
    pdta = chunk(b'LIST', b'pdta' + b''.join(chunk(tag, b''.join(rows)) for tag, rows in tables))
    font = output / 'erhu.sf2'
    font.write_bytes(chunk(b'RIFF', b'sfbk' + info
                           + chunk(b'LIST', b'sdta' + chunk(b'smpl', bytes(samples))) + pdta))
    shutil.copyfile(source / 'LICENSE', output / 'LICENSE-erhu.txt')
    shutil.copyfile(source / 'readme.txt', output / 'UPSTREAM-erhu.txt')
    asset = {'id': 'erhu', 'file': 'ethnic-light/erhu.sf2', 'inst': 'erhu',
             'kind': 'melodic', 'family': 'bowed', 'tags': ['二胡', '民族', '弓弦', 'CC0'],
             'license': 'CC0-1.0', 'source_url': SOURCE, 'source_commit': COMMIT,
             'installed_bytes': font.stat().st_size, 'sha256': digest(font),
             'presets': preset_records}
    manifest = {'schema_version': 1, 'budget_bytes': 30_000_000,
                'upstream_archive_url': f'https://codeload.github.com/sfzinstruments/aliexpress-erhu/zip/{COMMIT}',
                'source_wav_bytes': sum(p.stat().st_size for p in files),
                'preparation': 'Stereo mean, scipy resample_poly 44100->32000 Hz, mono PCM16; no normalization, denoise, added effects, looping or pitch correction. 0.25s SF2 note-off release.',
                'pitch_mapping': 'Scientific MIDI convention, A4=69; filenames are one octave higher. Original performance intonation retained, not auto-tuned.',
                'limitations': ['No recorded legato transitions or recorded articulation switching.',
                                'Takes require explicit presets; no automatic round robin or velocity layers.',
                                'One-shot notes stop at sample end; long samples are not indefinite sustains.',
                                'Some attacks/intonation vary; no naturalness or quality improvement certified.'],
                'listening_status': 'not_listened', 'assets': [asset], 'samples': records}
    (output / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    if sum(p.stat().st_size for p in output.iterdir() if p.is_file()) > manifest['budget_bytes']:
        raise ValueError('Installed ethnic-light directory exceeds 30 MB')
    return asset


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    print(json.dumps(build(args.source, args.output), ensure_ascii=False, indent=2))
