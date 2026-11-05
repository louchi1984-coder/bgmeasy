import ctypes as C
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
import soundfonts as F
import render_score_sf2 as R
from fluidsynth_library import find_library as find_fluidsynth_library

DEFAULT = F.ROOT / 'GeneralUser-GS.sf2'


def midi_for(track, bar=None):
    if bar is None:
        bar = [(0, 'kick', .8)] if track['inst'] == 'drums' else [(0, 1, [60], .8)]
    return R.build_midi({}, 4, {'voice': track}, ['A'], {'A': (1, {'voice': [bar]})}, 120, 4, .4, 7)[0]


class SoundFontTests(unittest.TestCase):
    def test_catalog_matches_installed_files(self):
        catalog = F.build_catalog()
        self.assertEqual(catalog['counts']['soundfonts'], 16 + int((F.ROOT/'DSK-Asian-DreamZ.sf2').is_file()))
        self.assertEqual(len(F.search(catalog, source='freepats-light')), 13)
        self.assertEqual(catalog['counts']['variants'], 146)
        self.assertEqual(len(F.search(catalog, kind='drums')), 15)
        self.assertEqual(len({e['id'] for e in catalog['entries']}), len(catalog['entries']))
        self.assertFalse(any('DSK Music' in e['name'] for e in catalog['entries']))

    def test_download_budget_and_licenses(self):
        manifest = json.loads((F.ROOT / 'freepats-light/manifest.json').read_text(encoding="utf-8"))
        self.assertTrue(50_000_000 <= manifest['download_bytes'] <= 100_000_000)
        self.assertEqual(manifest['download_bytes'], sum(a['download_bytes'] for a in manifest['assets']))
        for asset in manifest['assets']:
            self.assertEqual(asset['license'], 'CC0-1.0')
            self.assertEqual((F.ROOT / asset['file']).stat().st_size, asset['installed_bytes'])
            self.assertTrue(list((F.ROOT / 'freepats-light/licenses' / asset['id']).iterdir()))

    def test_search_chinese_and_variants(self):
        catalog = F.build_catalog()
        self.assertIn('generaluser-gs:8:27', {e['id'] for e in F.search(catalog, '变体 吉他')})
        self.assertNotIn('generaluser-gs:120:24', {e['id'] for e in F.search(catalog, '吉他')})
        self.assertEqual([e['id'] for e in F.search(catalog, '世界', kind='drums')], ['freepats-light/world-percussion:0:0'])

    def test_preset_resolution(self):
        original = {'voice': {'inst': 'pluck', 'preset': 'freepats-light/guitar-clean:0:0', 'gain': .7}}
        result = F.resolve_tracks(original, DEFAULT)
        self.assertEqual(result['voice']['gm'], {'bank': 0, 'program': 0})
        self.assertEqual(result['voice']['sf2'], 'freepats-light/guitar-clean.sf2')
        self.assertNotIn('gm', original['voice'])

    def test_invalid_selection_fails_instead_of_falling_back(self):
        with self.assertRaisesRegex(ValueError, '不会静默回退'):
            F.resolve_tracks({'voice': {'inst': 'lead', 'gm': {'bank': 119, 'program': 61}}}, DEFAULT)
        with self.assertRaisesRegex(ValueError, '找不到 preset'):
            F.resolve_tracks({'voice': {'inst': 'keys', 'preset': 'missing:0:0'}}, DEFAULT)
        with self.assertRaisesRegex(ValueError, '类型'):
            F.resolve_tracks({'voice': {'inst': 'keys', 'preset': 'generaluser-gs:128:16'}}, DEFAULT)
        with self.assertRaisesRegex(ValueError, 'program'):
            F.resolve_tracks({'voice': {'inst': 'lead', 'gm': {'program': 128}}}, DEFAULT)

    def test_conflicting_shared_drum_channel_is_rejected(self):
        with self.assertRaisesRegex(ValueError, '共用通道10'):
            F.resolve_tracks({'a': {'inst': 'drums', 'gm': {'program': 16}},
                              'b': {'inst': 'drums', 'gm': {'program': 40}}}, DEFAULT)

    def test_default_and_world_drum_mapping(self):
        legacy = F.resolve_tracks({'p': {'inst': 'drums'}}, DEFAULT)['p']
        mid = midi_for(legacy)
        programs = [e.program for t in mid.tracks for e in t if e.type == 'program_change' and e.channel == 9]
        self.assertEqual(programs, [0])
        world = F.resolve_tracks({'p': {'inst': 'drums', 'preset': 'freepats-light/world-percussion:0:0'}}, DEFAULT)['p']
        mid = midi_for(world, [(0, 'taiko', .8), (1, 'shaker', .6)])
        notes = [e.note for t in mid.tracks for e in t if e.type == 'note_on']
        self.assertEqual(notes, [69, 54])
        self.assertEqual(R.CH_SF, {9: 'freepats-light/world-percussion.sf2'})
        midi_for({'inst': 'keys'})
        self.assertEqual(R.CH_SF, {})

    def test_cymbals_parse_and_use_actual_gm_notes(self):
        events = R.R.parse_drum_bar('crash: X...............; ride: ....x...x...x...', 4, 'test')
        mid = midi_for({'inst': 'drums'}, events)
        self.assertEqual([e.note for t in mid.tracks for e in t if e.type == 'note_on'], [49, 51, 51, 51])

    def test_electronic_kit_uses_its_non_gm_keymap(self):
        cfg = F.resolve_tracks({'p': {'inst': 'drums', 'preset': 'freepats-light/electronic-drums:0:0'}}, DEFAULT)['p']
        mid = midi_for(cfg, [(0, 'kick', .8), (1, 'snare', .8), (2, 'hat', .6), (3, 'crash', .9)])
        self.assertEqual([e.note for t in mid.tracks for e in t if e.type == 'note_on'], [48, 50, 52, 55])
        with self.assertRaisesRegex(R.R.ScoreError, '未映射'):
            midi_for(cfg, [(0, 'cowbell', .8)])

    def test_external_font_in_subdirectory_renders_audio(self):
        import numpy as np
        import soundfile as sf
        score = {'bpm': 240, 'humanize_ms': 0,
                 'tracks': {'voice': {'inst': 'keys', 'preset': 'freepats-light/piano-kw:0:0'}},
                 'sections': {'A': {'voice': ['C4:1 E4:1 G4:1 C5:1']}}, 'arrangement': ['A']}
        with tempfile.TemporaryDirectory() as directory:
            fixture, out = Path(directory) / 'score.json', Path(directory) / 'audio.wav'
            fixture.write_text(json.dumps(score), encoding="utf-8")
            result = subprocess.run([sys.executable, '-I', str(SCRIPTS / 'render_score_sf2.py'), str(fixture), str(out),
                                     '--duration', '1.2', '--tail', '.2'], capture_output=True, text=True, encoding="utf-8", errors="replace")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            x, sr = sf.read(out, always_2d=True)
            self.assertEqual(x.shape, (round(1.2 * sr), 2))
            self.assertGreater(float(np.mean(x ** 2)), 1e-7)

    def test_real_fluidsynth_selects_requested_bank_and_kit(self):
        path = find_fluidsynth_library()
        if not path:
            self.skipTest('FluidSynth shared library unavailable')
        lib = C.CDLL(path)
        P, I = C.c_void_p, C.c_int
        def bind(name, result, arguments):
            fn = getattr(lib, name)
            fn.restype, fn.argtypes = result, arguments
            return fn
        make_settings = bind('new_fluid_settings', P, [])
        setting = bind('fluid_settings_setstr', I, [P, C.c_char_p, C.c_char_p])
        make_synth = bind('new_fluid_synth', P, [P])
        load = bind('fluid_synth_sfload', I, [P, C.c_char_p, I])
        cc = bind('fluid_synth_cc', I, [P, I, I, I])
        pc = bind('fluid_synth_program_change', I, [P, I, I])
        get = bind('fluid_synth_get_program', I, [P, I, C.POINTER(I), C.POINTER(I), C.POINTER(I)])
        preset = bind('fluid_synth_get_channel_preset', P, [P, I])
        preset_name = bind('fluid_preset_get_name', C.c_char_p, [P])
        delete_synth = bind('delete_fluid_synth', None, [P])
        delete_settings = bind('delete_fluid_settings', None, [P])
        for ident, inst in [('generaluser-gs:8:61', 'lead'), ('generaluser-gs:128:16', 'drums'),
                             ('generaluser-gs:128:40', 'drums'), ('freepats-light/electronic-drums:0:0', 'drums')]:
            with self.subTest(ident=ident):
                cfg = F.resolve_tracks({'voice': {'inst': inst, 'preset': ident}}, DEFAULT)['voice']
                mid = midi_for(cfg)
                settings = make_settings()
                setting(settings, b'synth.midi-bank-select', b'mma')
                synth = make_synth(settings)
                try:
                    sid = load(synth, str(F.ROOT / cfg['sf2']).encode(), 0)
                    channel = 9 if inst == 'drums' else 0
                    for track in mid.tracks:
                        for event in track:
                            if getattr(event, 'channel', -1) != channel:
                                continue
                            if event.type == 'control_change':
                                cc(synth, channel, event.control, event.value)
                            elif event.type == 'program_change':
                                pc(synth, channel, event.program)
                    a, b, c = I(), I(), I()
                    get(synth, channel, C.byref(a), C.byref(b), C.byref(c))
                    self.assertEqual((a.value, b.value, c.value), (sid, cfg['gm']['bank'], cfg['gm']['program']))
                    self.assertEqual(preset_name(preset(synth, channel)).decode('latin1'), cfg['_preset_name'])
                finally:
                    delete_synth(synth)
                    delete_settings(settings)


if __name__ == '__main__':
    unittest.main(verbosity=2)
