import ast
import copy
import hashlib
import json
from pathlib import Path
import re
import shutil
import string
import subprocess
import sys
import tempfile
import unicodedata
import unittest
from unittest.mock import patch

import numpy as np
import soundfile as sf

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT/'scripts'
sys.path.insert(0, str(SCRIPTS))
import localization as L
import soundfonts as F
import analyze_reference as A


def cli(script, *args):
    return subprocess.run([sys.executable, '-I', '-B', str(SCRIPTS/script), *map(str, args)],
                          capture_output=True, text=True, encoding='utf-8')


class LocalizationDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = F.build_catalog()

    def test_all_instrument_profiles_have_four_names(self):
        names = L.resource('instrument-languages.json')['instruments']
        self.assertEqual(set(names), set(L.resource('instruments.json')['profiles']))
        for ident, entry in names.items():
            with self.subTest(instrument=ident):
                self.assertEqual(set(entry['names']), set(L.LANGUAGES))
                self.assertTrue(all(v.strip() for v in entry['names'].values()))

    def test_four_language_search_returns_identical_presets(self):
        groups = [('钢琴', 'piano', 'ピアノ', '피아노'), ('吉他', 'guitar', 'ギター', '기타'),
                  ('小提琴', 'violin', 'バイオリン', '바이올린'), ('二胡', 'erhu', '二胡', '얼후'),
                  ('鼓组', 'drums', 'ドラム', '드럼'), ('竖琴', 'harp', 'ハープ', '하프'),
                  ('单簧管', 'clarinet', 'クラリネット', '클라리넷'),
                  ('电吉他', 'electric guitar', 'エレキギター', '일렉 기타')]
        for queries in groups:
            with self.subTest(queries=queries):
                ids = [{e['id'] for e in F.search(self.catalog, query)} for query in queries]
                self.assertTrue(ids[0])
                self.assertTrue(all(result == ids[0] for result in ids[1:]))

    def test_normalization_and_mixed_language_filters(self):
        ids = lambda query: {e['id'] for e in F.search(self.catalog, query)}
        self.assertEqual(ids('piano'), ids('ＰＩＡＮＯ'))
        self.assertEqual(ids('ピアノ'), ids('ﾋﾟｱﾉ'))
        self.assertEqual(ids('피아노'), ids(unicodedata.normalize('NFD', '피아노')))
        self.assertEqual(ids('变体 吉他'), ids('バリエーション 기타'))
        self.assertTrue(ids('バリエーション 기타'))

    def test_distinct_and_unverified_identities_are_not_merged(self):
        self.assertEqual(L.aliases()['luan'], 'unverified-lute')
        self.assertNotEqual(L.aliases()['ruan'], L.aliases()['luan'])
        erhu = {e['id'] for e in F.search(self.catalog, '얼후')}
        self.assertIn('ethnic-light/erhu-practice:0:0', erhu)
        for query in ('guzheng', 'koto'):
            self.assertNotIn('vcsl:dantranh', {e['id'] for e in F.search(self.catalog, query)})
        self.assertNotIn('dsk-asian-dreamz:0:5', {e['id'] for e in F.search(self.catalog, 'dizi')})

    def test_message_catalog_languages_and_formatting_are_complete(self):
        formatter = string.Formatter()
        fields = lambda text: sorted((name, spec, conversion) for _, name, spec, conversion in formatter.parse(text) if name is not None)
        catalog = L.resource('report-languages.json')
        for source, translations in catalog.items():
            for lang in ('en', 'ja', 'ko'):
                with self.subTest(message=source, language=lang):
                    self.assertTrue(translations[lang].strip())
                    self.assertEqual(fields(source), fields(translations[lang]))
        for filename in ['verify.py', 'check_deps.py', 'mix.py', 'check_melody.py',
                         'check_ranges.py', 'render_score.py', 'render_score_sf2.py', 'analyze_reference.py']:
            for call in ast.walk(ast.parse((SCRIPTS/filename).read_text(encoding='utf-8'))):
                if isinstance(call, ast.Call) and isinstance(call.func, ast.Name) and call.func.id == 'translate_text':
                    for value in ast.walk(call.args[0]):
                        if isinstance(value, ast.Constant) and isinstance(value.value, str) and re.search('[\u3400-\u9fff]', value.value):
                            self.assertIn(value.value, catalog, filename)

    def test_user_text_is_not_translated_or_reformatted(self):
        value = '综合响度 {v0} 日本 피아노'
        result = L.translate('乐谱错误: {v0}', 'en', v0=value)
        self.assertEqual(result, 'Score error: '+value)

    def test_cli_names_and_preset_configuration(self):
        configs = []
        for lang, query, name in [('zh', '钢琴', '钢琴'), ('en', 'piano', 'piano'),
                                  ('ja', 'ピアノ', 'ピアノ'), ('ko', '피아노', '피아노')]:
            with self.subTest(language=lang):
                search = cli('soundfonts.py', 'search', query, '--json', '--lang', lang)
                self.assertEqual(search.returncode, 0, search.stderr)
                self.assertTrue(any(e['instrument_name'] == name for e in json.loads(search.stdout)))
                show = cli('soundfonts.py', '--lang', lang, 'show', 'generaluser-gs:0:0')
                self.assertEqual(show.returncode, 0, show.stderr)
                configs.append(json.loads(show.stdout)['track'])
                knowledge = cli('instruments.py', 'search', query, '--lang', lang)
                self.assertEqual(knowledge.returncode, 0, knowledge.stderr)
                self.assertIn('piano', {e['id'] for e in json.loads(knowledge.stdout)['instruments']})
        self.assertTrue(all(cfg == configs[0] for cfg in configs))

    def test_missing_plot_fonts_fall_back_explicitly(self):
        from matplotlib import font_manager
        with patch.object(font_manager.fontManager, 'ttflist', []):
            self.assertEqual(L.plot_language('ja', ['MIDI pitch']), ('en', None))


@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'requires FFmpeg/FFprobe')
class LocalizedReportTests(unittest.TestCase):
    def test_reference_views_change_language_without_changing_analysis(self):
        y = .2*np.sin(2*np.pi*440*np.arange(A.SR*2)/A.SR)
        report, data = A.analyze(y)
        report['source'] = {'path': '原曲 & 日本 피아노.wav'}
        original = copy.deepcopy(report)
        digests = []
        markers = ['参考曲分析 · 候选证据', 'Reference analysis · candidate evidence',
                   '参照音源分析・候補の根拠', '참고 음원 분석 · 후보 근거']
        with tempfile.TemporaryDirectory() as directory:
            for lang, marker in zip(L.LANGUAGES, markers):
                with self.subTest(language=lang):
                    out = Path(directory)/lang; out.mkdir()
                    A.write_outputs(out, report, data, lang)
                    self.assertEqual(report, original)
                    digests.append([(out/name).read_bytes() for name in A.FILES if name.endswith(('.json', '.csv'))])
                    page = (out/'report.html').read_text(encoding='utf-8')
                    self.assertIn(f'<html lang="{lang}">', page)
                    self.assertIn(marker, page)
                    self.assertIn('原曲 &amp; 日本 피아노.wav', page)
                    self.assertIn('data-chart-language=', page)
                    if lang == 'en':
                        self.assertNotIn('未核听', page)
                        self.assertNotIn('和弦是固定时间窗', page)
            self.assertTrue(all(result == digests[0] for result in digests))

    def test_verification_numbers_do_not_depend_on_language(self):
        with tempfile.TemporaryDirectory() as directory:
            audio = Path(directory)/'音楽 음악.wav'
            t = np.arange(44100*3)/44100
            sf.write(audio, np.column_stack([.2*np.sin(2*np.pi*440*t)]*2), 44100)
            values = []
            for lang, marker in zip(L.LANGUAGES, ['综合响度', 'Integrated loudness', '統合ラウドネス', '통합 라우드니스']):
                result = cli('verify.py', audio, '--lang', lang)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn(marker, result.stdout)
                values.append([re.findall(r'[-+]?\d+(?:\.\d+)?', line.split(':', 1)[1])
                               for line in result.stdout.splitlines() if line.startswith('[')])
            self.assertTrue(all(value == values[0] for value in values))

    def test_score_reports_accept_all_four_languages(self):
        score = {'bpm': 120, 'tracks': {'melody': {'inst': 'keys'}},
                 'sections': {'A': {'melody': ['C4:1 E4:1 G4:1 C5:1']}}, 'arrangement': ['A'],
                 'design': {'melody': ['melody'], 'chords': {'A': ['C']}, 'motif': 'C4:1 E4:1 G4:1 C5:1'}}
        with tempfile.TemporaryDirectory() as directory:
            fixture = Path(directory)/'谱面.json';fixture.write_text(json.dumps(score), encoding='utf-8')
            for lang in L.LANGUAGES:
                for script in ['check_melody.py', 'check_ranges.py', 'check_deps.py']:
                    with self.subTest(language=lang, script=script):
                        result = cli(script, *([] if script == 'check_deps.py' else [fixture]), '--lang', lang)
                        self.assertEqual(result.returncode, 0, result.stderr)

    def test_invalid_language_is_rejected_before_writing(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)/'not-created'
            result = cli('analyze_reference.py', 'missing.wav', out, '--lang', 'fr')
            self.assertEqual(result.returncode, 2)
            self.assertFalse(out.exists())

    @unittest.skipUnless(shutil.which('fluidsynth'), 'requires FluidSynth')
    def test_render_language_does_not_change_wav_or_score_metadata(self):
        score = {'bpm': 120, 'seed': 7, 'humanize_ms': 0,
                 'tracks': {'主题 주제': {'inst': 'keys', 'preset': 'generaluser-gs:0:0'}},
                 'sections': {'主題': {'主题 주제': ['C4:1 E4:1 G4:1 C5:1']}}, 'arrangement': ['主題']}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory);fixture=root/'日本 & 한국.json'
            fixture.write_text(json.dumps(score, ensure_ascii=False), encoding='utf-8')
            before = fixture.read_bytes()
            for engine in ['render_score.py', 'render_score_sf2.py']:
                hashes = []
                for lang in L.LANGUAGES:
                    output = root/(engine+'-'+lang+'.wav')
                    result = cli(engine, fixture, output, '--duration', '3.2', '--seed', '7', '--lang', lang)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertIn('主题 주제', result.stdout)
                    hashes.append(hashlib.sha256(output.read_bytes()).hexdigest())
                self.assertEqual(len(set(hashes)), 1, engine)
            self.assertEqual(fixture.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
