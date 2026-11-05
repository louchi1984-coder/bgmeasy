"""Read SF2 preset/instrument/sample zones; never infer playing quality from headers."""
import struct
from pathlib import Path


def read_tables(path):
    wanted = {b'phdr', b'pbag', b'pgen', b'inst', b'ibag', b'igen', b'shdr'}
    tables = {}
    with Path(path).open('rb') as f:
        head = f.read(12)
        if len(head) != 12 or head[:4] != b'RIFF' or head[8:] != b'sfbk':
            raise ValueError(f'不是SF2: {path}')
        def scan(start, stop):
            while start + 8 <= stop:
                f.seek(start)
                tag, size = struct.unpack('<4sI', f.read(8))
                body = start + 8
                if body + size > stop:
                    raise ValueError(f'SF2区块越界: {path}')
                if tag == b'LIST':
                    scan(body + 4, body + size)
                elif tag in wanted:
                    tables[tag] = f.read(size)
                start = body + size + size % 2
        scan(12, min(Path(path).stat().st_size, struct.unpack_from('<I', head, 4)[0] + 8))
    if wanted - tables.keys():
        raise ValueError(f'SF2缺少pdta表: {path}')
    formats = {b'phdr': '<20sHHHIII', b'pbag': '<HH', b'pgen': '<HH',
               b'inst': '<20sH', b'ibag': '<HH', b'igen': '<HH', b'shdr': '<20sIIIIIBbHH'}
    return {tag.decode(): list(struct.iter_unpack(formats[tag], data)) for tag, data in tables.items()}


def _name(raw):
    return raw.split(b'\0')[0].decode('latin1').strip()


def _zones(bags, gens, start, stop, terminal):
    global_zone = {}
    for b in range(start, stop):
        local = dict(gens[bags[b][0]:bags[b + 1][0]])
        if terminal not in local:
            global_zone = local
        else:
            yield {**global_zone, **local}


def _range(gens, op):
    raw = gens.get(op, 127 << 8)
    return raw & 255, raw >> 8


def _intersection(a, b):
    return max(a[0], b[0]), min(a[1], b[1])


def _signed(value):
    return value if value < 32768 else value - 65536


def inspect(path):
    tables = read_tables(path)
    ph, pb, pg = (tables[k] for k in ('phdr', 'pbag', 'pgen'))
    instruments, ib, ig, samples = (tables[k] for k in ('inst', 'ibag', 'igen', 'shdr'))
    result = {}
    for i, preset in enumerate(ph[:-1]):
        zones = []
        for pz in _zones(pb, pg, preset[3], ph[i + 1][3], 41):
            instrument = pz[41]
            if instrument >= len(instruments) - 1:
                raise ValueError('SF2 instrument索引越界')
            for iz in _zones(ib, ig, instruments[instrument][1], instruments[instrument + 1][1], 53):
                sample_id = iz[53]
                if sample_id >= len(samples) - 1:
                    raise ValueError('SF2 sample索引越界')
                sample = samples[sample_id]
                keys = _intersection(_range(pz, 43), _range(iz, 43))
                velocities = _intersection(_range(pz, 44), _range(iz, 44))
                if keys[0] > keys[1] or velocities[0] > velocities[1]:
                    continue
                root = iz.get(58, sample[6])
                scale = iz.get(56, 100) + pz.get(56, 0)
                zones.append({'sample_id': sample_id, 'sample': _name(sample[0]),
                              'keys': list(keys), 'velocities': list(velocities),
                              'root_midi': root if 0 <= root <= 127 else None,
                              'scale_tuning_cents_per_key': scale,
                              'coarse_tune_semitones': _signed(iz.get(51,0))+_signed(pz.get(51,0)),
                              'fine_tune_cents': _signed(iz.get(52,0))+_signed(pz.get(52,0)),
                              'sample_pitch_correction_cents': sample[7],
                              'fixed_key': iz.get(46), 'fixed_velocity': iz.get(47),
                              'duration_seconds': round((sample[2] - sample[1]) / sample[5], 4) if sample[5] else None,
                              'sample_rate': sample[5], 'sample_type': sample[9],
                              'loop_mode': iz.get(54, 0),
                              'loop_seconds': round((sample[4] - sample[3]) / sample[5], 4) if sample[5] else None})
        coverage = sorted({key for z in zones for key in range(z['keys'][0], z['keys'][1] + 1)})
        result[(preset[2], preset[1])] = {
            'preset_name': _name(preset[0]), 'zone_count': len(zones),
            'unique_sample_headers': len({z['sample_id'] for z in zones}),
            'covered_midi_keys': coverage,
            'root_midi_notes': sorted({z['root_midi'] for z in zones if z['root_midi'] is not None}),
            'velocity_ranges': sorted({tuple(z['velocities']) for z in zones}),
            'loop_modes': sorted({z['loop_mode'] for z in zones}), 'zones': zones,
            'interpretation': '采样头/区域统计；立体声链接、叠层不能算作独立奏法或轮替采样。音域是映射范围，不是真实乐器音域。',
        }
    return result
