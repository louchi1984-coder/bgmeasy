# SPDX-License-Identifier: CC0-1.0
"""Rebuild the approved CC0 erhu single-note asset from a pinned public preview."""
import argparse
from pathlib import Path
import hashlib
import json
import struct

import numpy as np
import soundfile as sf

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('source', type=Path, help='Public MP3 preview matching the pinned SHA-256')
parser.add_argument('output', type=Path, help='New output directory')
args = parser.parse_args()
D = args.output
D.mkdir(parents=True, exist_ok=True)
source = args.source
if hashlib.sha256(source.read_bytes()).hexdigest() != 'd2826ba89e1c41df4cf0ea8ecb43e58a0e810e933fb30103b880f6f4e64c11eb':
    raise ValueError('Source differs from the approved audition recording')
audio, sr = sf.read(source, always_2d=True)
assert sr == 44100 and audio.shape[1] == 2 and np.isfinite(audio).all()
# Candidate note boundaries were located with untrained YIN. No melodic phrase
# is reused; each excerpt is a single recorded pitch. Pitch is not corrected.
cuts = [(69, 20.925, 21.94), (72, 31.14, 33.19)]


def chunk(tag, data):
    return tag + struct.pack('<I', len(data)) + data + b'\0' * (len(data) % 2)


def name(text):
    return text.encode('ascii')[:19].ljust(20, b'\0')


smpl = bytearray()
shdr, ibag, igen, records = [], [], [], []
cursor = 0
for root, start, end in cuts:
    x = audio[round(start * sr):round(end * sr)].copy()
    # A 3ms edge window prevents a cut waveform from clicking; this prepares
    # the sample asset and does not change the music renderer or add effects.
    edge = round(.003 * sr)
    x[:edge] *= np.linspace(0, 1, edge)[:, None]
    x[-edge:] *= np.linspace(1, 0, edge)[:, None]
    first = len(shdr)
    for ch, (pan, sample_type) in enumerate([(-500, 4), (500, 2)]):
        pcm = np.clip(np.rint(x[:, ch] * 32768), -32768, 32767).astype('<i2')
        sid = len(shdr)
        shdr.append(struct.pack('<20sIIIIIBbHH', name(f'CC0-{root}-{ch}'), cursor, cursor + len(pcm),
                                cursor, cursor + len(pcm) - 1, sr, root, 0, first + 1 - ch, sample_type))
        smpl.extend(pcm.tobytes() + b'\0' * 92); cursor += len(pcm) + 46
        ibag.append(struct.pack('<HH', len(igen), 0))
        for op, val in [(43, root | (root << 8)), (17, pan), (54, 0), (58, root), (38, -2400), (53, sid)]:
            igen.append(struct.pack('<HH', op, val & 65535))
    records.append({'midi_root_candidate': root, 'source_start_seconds': start,
                    'source_end_seconds': end, 'duration_seconds': len(x) / sr,
                    'edge_window_seconds': .003})
ibag.append(struct.pack('<HH', len(igen), 0)); igen.append(b'\0' * 4)
shdr.append(struct.pack('<20sIIIIIBbHH', name('EOS'), cursor, cursor, cursor, cursor, sr, 0, 0, 0, 1))
phdr = [struct.pack('<20sHHHIII', name(n), 0, 0, bag, 0, 0, 0) for n, bag in [('CC0 Practice Erhu', 0), ('EOP', 1)]]
inst = [struct.pack('<20sH', name(n), bag) for n, bag in [('CC0 Practice Erhu', 0), ('EOI', len(ibag) - 1)]]
info = chunk(b'LIST', b'INFO' + chunk(b'ifil', struct.pack('<HH', 2, 1))
             + chunk(b'isng', b'EMU8000\0') + chunk(b'INAM', b'CC0 Practice Erhu\0'))
tables = [(b'phdr', phdr), (b'pbag', [struct.pack('<HH', 0, 0), struct.pack('<HH', 1, 0)]),
          (b'pmod', [b'\0' * 10]), (b'pgen', [struct.pack('<HH', 41, 0), b'\0' * 4]),
          (b'inst', inst), (b'ibag', ibag), (b'imod', [b'\0' * 10]), (b'igen', igen), (b'shdr', shdr)]
pdta = chunk(b'LIST', b'pdta' + b''.join(chunk(tag, b''.join(rows)) for tag, rows in tables))
font = D / 'erhu-practice.sf2'
assert not font.exists()
font.write_bytes(chunk(b'RIFF', b'sfbk' + info + chunk(b'LIST', b'sdta' + chunk(b'smpl', bytes(smpl))) + pdta))
manifest = {'author': 'irzirgpznj', 'title': 'Erhu sample',
            'page': 'https://freesound.org/people/irzirgpznj/sounds/477169/',
            'license': 'CC0-1.0', 'license_url': 'https://creativecommons.org/publicdomain/zero/1.0/',
            'source_description': 'Author states recorded during an erhu practice session.',
            'download_url': 'https://cdn.freesound.org/previews/477/477169_10194539-hq.mp3',
            'download_requires_login': False, 'source_type': 'public HQ MP3 preview; original listed as lossy Ogg 96kbps, not lossless',
            'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
            'font': font.name, 'font_sha256': hashlib.sha256(font.read_bytes()).hexdigest(),
            'font_bytes': font.stat().st_size, 'cuts': records,
            'processing': 'Isolate single recorded pitches, 3ms edge windows, stereo PCM16 SF2; no denoise, EQ, looping, artificial vibrato or pitch correction.',
            'limitations': 'Two isolated performance excerpts only, not full multisamples or legato transitions; held notes cannot exceed recording length.',
            'installed': False, 'listening_status': 'not_listened'}
(D / 'erhu-practice-provenance.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
(D / 'ATTRIBUTION-erhu-practice.txt').write_text('Erhu sample by irzirgpznj, Freesound 477169 (2019). CC0-1.0.\n'
    'https://freesound.org/people/irzirgpznj/sounds/477169/\n'
    'https://creativecommons.org/publicdomain/zero/1.0/\n'
    'Trial derivative: two isolated single notes from the public MP3 preview, stereo PCM16 with 3ms edge windows.\n'
    'No learned model, noise reduction, EQ, looping or artificial vibrato. Not installed or listening-approved.\n')
print(json.dumps({'font': str(font), 'font_bytes': font.stat().st_size, 'recorded_roots': [69, 72]}))
