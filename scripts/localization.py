"""Four-language display strings and instrument aliases; no audio processing."""
from functools import lru_cache
import json
from pathlib import Path
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
LANGUAGES = ('zh', 'en', 'ja', 'ko')
CURRENT_LANGUAGE = 'zh'


@lru_cache(maxsize=None)
def resource(name):
    return json.loads((ROOT/'references'/name).read_text(encoding='utf-8'))


def add_argument(parser):
    parser.add_argument('--lang', choices=LANGUAGES, default='zh',
                        help='报告语言 / report language / 表示言語 / 보고서 언어 (zh, en, ja, ko)')


def use_language(language):
    global CURRENT_LANGUAGE
    CURRENT_LANGUAGE = language


def translate(message, language=None, **values):
    language = language or CURRENT_LANGUAGE
    text = resource('report-languages.json').get(message, {}).get(language, message)
    return text.format(**values) if values else text


def normalize(text):
    return ' '.join(unicodedata.normalize('NFKC', text).casefold().split())


@lru_cache(maxsize=1)
def aliases():
    data = resource('instrument-languages.json')
    result = {}
    # Categories take precedence for broad words such as bass/strings/drums.
    for group in ('instruments', 'categories'):
        for ident, entry in data[group].items():
            for name in [ident, *entry['names'].values(), *entry['aliases']]:
                result[normalize(name)] = ident
    return result


def search_words(query):
    query = normalize(query)
    known = aliases()
    if query in known:
        return [known[query]]
    return [known.get(word, word) for word in query.split()]


def instrument_name(ident, language='zh'):
    entry = resource('instrument-languages.json')['instruments'].get(ident)
    return entry['names'][language] if entry else ident


def profile_for(entry):
    data = resource('instruments.json')
    if entry['id'] in data['preset_overrides']:
        return data['preset_overrides'][entry['id']]
    if entry['source'] == 'generaluser-gs':
        return 'drum-kit' if entry.get('bank') in (120, 128) else data['gm_profiles'][entry['program']]
    return None


def search_text(entry):
    return normalize(' '.join([entry['id'], entry['name'], entry['family'], *entry['tags'], profile_for(entry) or '']))


def plot_language(language, labels):
    """Use a local font with all required glyphs; otherwise keep readable English axes."""
    if language == 'en':
        return 'en', None
    from matplotlib import font_manager, ft2font
    families = {'zh': ['Microsoft YaHei', 'PingFang SC', 'Noto Sans CJK SC', 'SimHei'],
                'ja': ['Yu Gothic', 'MS Gothic', 'Hiragino Sans', 'Noto Sans CJK JP', 'IPAexGothic'],
                'ko': ['Malgun Gothic', 'AppleGothic', 'Noto Sans CJK KR']}
    needed = {ord(c) for label in labels for c in translate(label, language) if ord(c) > 127} | {0x2212}
    for family in families[language]:
        for font in font_manager.fontManager.ttflist:
            if font.name == family:
                if needed <= ft2font.FT2Font(font.fname).get_charmap().keys():
                    return language, font.fname
    return 'en', None
