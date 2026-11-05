#!/usr/bin/env python3
"""Inspect installed SF2 presets, search the catalog, and resolve score preset IDs."""
import argparse
import copy
import json
from pathlib import Path
import struct

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import localization as I18N
if __name__ == "__main__" and sys.platform == "win32":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")

ROOT = Path(__file__).resolve().parents[1] / 'soundfonts'
FAMILIES = [
    ('piano', '钢琴 键盘'), ('chromatic', '钟琴 木琴 有音打击'),
    ('organ', '风琴 手风琴'), ('guitar', '吉他 拨弦'), ('bass', '贝斯 低音'),
    ('strings', '弦乐 竖琴'), ('ensemble', '合奏 合唱 人声'), ('brass', '铜管 小号 圆号'),
    ('woodwinds', '木管 萨克斯 单簧管'), ('flutes', '长笛 箫 管乐'),
    ('synth-lead', '合成 主音 电子'), ('synth-pad', '合成 氛围 铺底'),
    ('synth-fx', '合成 特效'), ('ethnic', '民族 弹拨'),
    ('percussion', '打击 定音鼓'), ('sfx', '声音特效'),
]
ALIASES = {'piano': '钢琴 键盘', 'guitar': '吉他 电吉他 拨弦', 'bass': '贝斯 低音',
           'strings': '弦乐 竖琴', 'woodwinds': '木管 单簧管', 'synth': '合成 氛围 电子',
           'percussion': '打击', 'drums': '鼓组 打击 电子', 'bowed': '弓弦 民族'}


def read_presets(path):
    """Read phdr headers without loading the (potentially large) sample payload."""
    path = Path(path)
    with path.open('rb') as f:
        header = f.read(12)
        if len(header) != 12 or header[:4] != b'RIFF' or header[8:] != b'sfbk':
            raise ValueError(f'不是 SF2 SoundFont: {path}')
        end = min(path.stat().st_size, struct.unpack_from('<I', header, 4)[0] + 8)
        pos = 12
        while pos + 8 <= end:
            f.seek(pos)
            tag, size = struct.unpack('<4sI', f.read(8))
            if tag == b'LIST' and f.read(4) == b'pdta':
                sub, stop = pos + 12, min(pos + 8 + size, end)
                while sub + 8 <= stop:
                    f.seek(sub)
                    name, length = struct.unpack('<4sI', f.read(8))
                    if name == b'phdr':
                        data = f.read(length)
                        if len(data) != length or length % 38:
                            raise ValueError(f'损坏的 phdr: {path}')
                        presets = []
                        for offset in range(0, length, 38):
                            raw, program, bank, *_ = struct.unpack_from('<20sHHHIII', data, offset)
                            label = raw.split(b'\0')[0].decode('latin1').strip()
                            if label != 'EOP':
                                presets.append({'bank': bank, 'program': program, 'name': label})
                        return sorted(presets, key=lambda p: (p['bank'], p['program']))
                    sub += 8 + length + length % 2
            pos += 8 + size + size % 2
    raise ValueError(f'没有找到 phdr: {path}')


def build_catalog(root=ROOT):
    root = Path(root)
    metadata = {}
    for relative in ['freepats-light/manifest.json', 'ethnic-light/manifest.json']:
        manifest = root / relative
        if manifest.exists():
            metadata.update({a['file']: a for a in json.loads(manifest.read_text(encoding="utf-8"))['assets']})
    entries = []
    for path in sorted(root.rglob('*.sf2')):
        relative = path.relative_to(root).as_posix()
        source = path.relative_to(root).with_suffix('').as_posix().lower()
        meta = metadata.get(relative, {})
        for preset in read_presets(path):
            preset_name, bank, program = preset['name'], preset['bank'], preset['program']
            preset_meta = next((p for p in meta.get('presets', [])
                                if (p['bank'], p['program']) == (bank, program)), {})
            name = preset_meta.get('display_name', meta.get('name', preset_name))
            if relative == 'DSK-Asian-DreamZ.sf2' and name.startswith('DSK Music'):
                continue  # This is a credits preset, not a musical instrument.
            kind = meta.get('kind', 'drums' if bank == 128 else 'melodic')
            family, chinese = FAMILIES[min(program // 8, 15)]
            family = meta.get('family', family)
            chinese = ALIASES.get(family, chinese)
            if kind == 'drums':
                family, chinese = 'drums', '鼓组 打击'
            elif bank == 120 and 'kit' in name.lower():
                family, chinese = 'percussion', '打击 鼓 有音通道'
            elif program == 47 and not meta:
                family, chinese = 'percussion', '打击 定音鼓'
            if relative == 'DSK-Asian-DreamZ.sf2':
                labels = {0: '琵琶', 1: '琵琶 轮指', 2: 'LUAN 弹拨 身份待核实', 3: '古筝',
                          4: '二胡', 5: 'BAN-DI 吹管 身份待核实', 6: '中国打击'}
                family, chinese = 'ethnic', '民族 ' + labels.get(program, '')
            inst = ('drums' if kind == 'drums' else
                    'pluck' if family in {'guitar', 'ethnic'} or 'harp' in name.lower() else
                    'bass' if family == 'bass' else 'strings' if family in {'strings', 'ensemble'} else
                    'pad' if family in {'synth', 'synth-pad'} else 'keys' if family == 'piano' else 'lead')
            tags = f'{chinese} {family} {meta.get("name", "")} {" ".join(meta.get("tags", []))} {"变体 variant" if bank not in (0, 128) else ""}'
            tags += ' ' + ' '.join(preset_meta.get('tags', []))
            if family == 'drums':
                tags += ' ' + {0: '标准', 8: '房间', 16: '力量 摇滚', 24: '电子', 25: '电子 808 909',
                               32: '爵士', 40: '刷子 爵士', 48: '管弦', 56: '特效'}.get(program, '')
            if 'generaluser' in source:
                license_name = 'GeneralUser GS license (see LICENSE-GeneralUser-GS.txt)'
            elif 'dsk' in source:
                license_name = 'Local use; see LICENSE-DSK-NOTE.txt; do not redistribute font'
            else:
                license_name = meta.get('license', 'Check source license')
            track = {'inst': meta.get('inst', inst), 'sf2': relative, 'gm': {'bank': bank, 'program': program}}
            if meta.get('drum_notes'):
                track['drum_notes'] = meta['drum_notes']
            entries.append({
                'id': f'{source}:{bank}:{program}', 'name': name, 'kind': kind,
                'preset_name': preset_name,
                'source': source, 'file': relative, 'bank': bank, 'program': program,
                'family': family, 'tags': tags.split(), 'license': license_name,
                'source_url': meta.get('source_url', ''),
                'track': track,
            })
    if (root / 'vcsl').is_dir():
        for key, label, inst in [('dantranh', 'Dan Tranh 筝', 'guzheng'),
                                  ('bassdrum', 'Low Drum 低音大鼓', 'pluck'), ('gong', 'Gong 锣', 'bell')]:
            entries.append({'id': f'vcsl:{key}', 'name': label, 'kind': 'sample',
                            'source': 'vcsl', 'family': 'ethnic' if key == 'dantranh' else 'percussion',
                            'tags': ['VCSL', 'CC0', label], 'license': 'CC0-1.0',
                            'source_url': 'https://github.com/sgossner/VCSL',
                            'track': {'inst': inst, 'engine': f'sampler:{key}'}})
    return {'schema_version': 1, 'entries': entries, 'counts': {
        'soundfonts': len(list(root.rglob('*.sf2'))), 'presets': len(entries),
        'melodic': sum(e['kind'] == 'melodic' for e in entries),
        'drums': sum(e['kind'] == 'drums' for e in entries),
        'variants': sum(e.get('bank', 0) not in (0, 128) for e in entries),
        'samples': sum(e['kind'] == 'sample' for e in entries),
    }}


def search(catalog, query='', kind=None, source=None):
    words = I18N.search_words(query)
    return [e for e in catalog['entries']
            if (kind is None or e['kind'] == kind)
            and (source is None or source.casefold() in e['source'].casefold())
            and all(w in I18N.search_text(e) for w in words)]


def resolve_tracks(tracks, default_soundfont, root=ROOT, default_programs=None):
    """Resolve stable IDs, validate actual presets, and reject conflicting drum kits."""
    resolved = copy.deepcopy(tracks)
    indexed = None
    inventories = {}
    drum_selection = None
    for name, cfg in resolved.items():
        if cfg.get('preset'):
            if indexed is None:
                indexed = {e['id']: e for e in build_catalog(root)['entries']}
            if cfg['preset'] not in indexed:
                raise ValueError(f'{name}: 找不到 preset {cfg["preset"]}，先运行 soundfonts.py search')
            entry = indexed[cfg['preset']]
            if (cfg['inst'] == 'drums') != (entry['kind'] == 'drums'):
                raise ValueError(f'{name}: preset 类型与 inst 不一致；建议 {entry["track"]}')
            for key, value in entry['track'].items():
                if key == 'inst':
                    continue
                if key in cfg and cfg[key] != value:
                    raise ValueError(f'{name}: {key} 与 preset 指定值冲突')
                cfg[key] = copy.deepcopy(value)
        if cfg.get('engine', '').startswith('sampler:'):
            continue
        gm = cfg.get('gm', {})
        bank = gm.get('bank', 128 if cfg['inst'] == 'drums' else 0)
        program = gm.get('program', (default_programs or {}).get(cfg['inst']))
        if not isinstance(bank, int) or not 0 <= bank <= 16383:
            raise ValueError(f'{name}: bank 必须为 0–16383 的整数')
        if program is not None and (not isinstance(program, int) or not 0 <= program <= 127):
            raise ValueError(f'{name}: program 必须为 0–127 的整数')
        path = Path(root) / cfg['sf2'] if cfg.get('sf2') else Path(default_soundfont)
        if not path.is_file():
            raise ValueError(f'{name}: 找不到音色库 {path}')
        if path not in inventories:
            inventories[path] = {(p['bank'], p['program']): p['name'] for p in read_presets(path)}
        if cfg['inst'] == 'drums':
            program = 0 if program is None else program
            for lane, note in cfg.get('drum_notes', {}).items():
                if not isinstance(note, int) or not 0 <= note <= 127:
                    raise ValueError(f'{name}: drum_notes.{lane} 必须为 0–127 的 MIDI 音高')
            selection = (path.resolve(), bank, program)
            if drum_selection is not None and selection != drum_selection:
                raise ValueError('所有 drums 声部共用通道10，必须选择同一音色库、bank 和鼓组 program')
            drum_selection = selection
        if program is not None:
            if (bank, program) not in inventories[path]:
                raise ValueError(f'{name}: {path.name} 不存在 bank {bank} / program {program}；不会静默回退')
            cfg['_preset_name'] = inventories[path][bank, program]
    return resolved


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    find = commands.add_parser('search', help='按中英文名称、类别或来源检索')
    find.add_argument('query', nargs='?', default='')
    find.add_argument('--kind', choices=['melodic', 'drums', 'sample'])
    find.add_argument('--source')
    find.add_argument('--json', action='store_true')
    show = commands.add_parser('show', help='输出可复制到乐谱的声部配置')
    show.add_argument('id')
    rebuild = commands.add_parser('build', help='重建安装目录与机器可读索引')
    rebuild.add_argument('--out', type=Path, default=ROOT / 'catalog.json')
    I18N.add_argument(parser)
    for command in (find, show, rebuild):
        command.add_argument('--lang', choices=I18N.LANGUAGES, default=argparse.SUPPRESS)
    args = parser.parse_args()
    I18N.use_language(args.lang)
    catalog = build_catalog()
    if args.command == 'build':
        args.out.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + '\n', encoding="utf-8")
        print(json.dumps(catalog['counts'], ensure_ascii=False, indent=2))
    elif args.command == 'show':
        matches = [e for e in catalog['entries'] if e['id'] == args.id]
        if not matches:
            parser.error(f'找不到 {args.id}')
        entry = matches[0]
        print(json.dumps({'name': entry['name'], 'instrument_name': I18N.instrument_name(I18N.profile_for(entry), args.lang), 'license': entry['license'],
                         'track': {'preset': entry['id'], **entry['track']},
                         'performance_lookup': f'python3 -I scripts/instruments.py preset {entry["id"]}'}, ensure_ascii=False, indent=2))
    else:
        matches = search(catalog, args.query, args.kind, args.source)
        if args.json:
            print(json.dumps([{**entry, 'instrument_name': I18N.instrument_name(I18N.profile_for(entry), args.lang)} for entry in matches], ensure_ascii=False, indent=2))
        else:
            for entry in matches:
                label = I18N.instrument_name(I18N.profile_for(entry), args.lang)
                print(f'{entry["id"]:<56} {label} | {entry["name"]}')
            print(f'{len(matches)} matches')


if __name__ == '__main__':
    main()
