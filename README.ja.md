# bgmeasy

[English](README.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md) · [한국어](README.ko.md)

**AIエージェントがローカルでBGMを設計・レンダリング・検証するためのスキルです。**

LLMエージェントが曲全体を計画して記号形式の楽譜を書き、Pythonが合成音源またはSoundFontでWAVを生成します。動画へのミックス、ナレーションに合わせたダッキング、古典的な信号処理による参考音源の分析にも対応します。

音楽生成モデル、モデル重みのダウンロード、クラウド音楽API、商用音源プラグインは不要です。作曲上の判断は、利用するコーディングエージェントが担当します。

## 機能

- `SKILL.md` と `references/` に、全曲構成、楽句展開、和声、リズム、配器の資料を収録。
- 内蔵合成と、MIDI → FluidSynth/SF2 → マスタリングのレンダリング経路。
- Pythonから直接動画をミックス。ナレーション・元音声によるダッキング、2パスのラウドネス正規化、映像ストリームのコピー。**WindowsでもGit BashやWSLは不要です。**
- 音高・リズム・和声・構造の**候補**を、学習モデルを使わず分析。不確実性を保持します。
- 中国語・英語・日本語・韓国語の楽器検索と標準レポート：`--lang zh|en|ja|ko`。
- 96件の楽器資料profile。任意の音源パックには16個のSF2と312件のカタログ項目があり、バリエーションとサンプル打楽器を含みます。資料の件数は独立音源の数やリアルさの保証ではありません。

## セットアップ

Python 3.10以上を推奨します。ネイティブの **FFmpeg、FFprobe、FluidSynth** をインストールしてPATHに追加してください。Windows版FluidSynthは同梱DLLを実行ファイルの隣に残します。macOSでは `brew install ffmpeg fluid-synth` を利用できます。

リポジトリをダウンロードするか、クローンします。

```text
git clone https://github.com/louchi1984-coder/bgmeasy.git
cd bgmeasy
```

仮想環境とPython依存パッケージを準備します。

```powershell
# Windows PowerShell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

```sh
# macOS / Linux
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

以降の `python` は、この仮想環境のインタープリターに読み替えてください。有効化操作は必須ではありません。

サンプル音源を使う完全な手順には、別ライセンスの音源パック（約 **169 MB**）を追加します。

```text
python -I scripts/download_soundfonts.py
python -I scripts/check_deps.py --lang ja
```

インストーラーはSHA-256を検証し、危険なパスと内容が異なる既存ファイルへの上書きを拒否します。オフラインでは [`bgmeasy-soundfonts.zip`](https://github.com/louchi1984-coder/bgmeasy/releases/download/v0.1.0/bgmeasy-soundfonts.zip) を取得し、`--archive path/to/bgmeasy-soundfonts.zip` を指定できます。音源バイナリはReleaseで配布し、Git履歴には入れません。**DSK Asian DreamZは含みません。** [第三者ライセンス](THIRD_PARTY.md)を確認してください。

## エージェントで使う

ファイル操作とコマンド実行ができるエージェントに [`SKILL.md`](SKILL.md) を読ませます。依頼例：

> このスキルで、温かく静かな30秒のBGMを作ってください。台詞はありません。全曲を先に計画し、一貫した主題を書いて標準手順でレンダリングしてください。レポートは日本語にしてください。

主スキルと詳細資料は現在も主に中国語です。README・楽器別名・標準レポートUIは上記の4言語に対応します。引用とユーザーが書いた文章は原文を保ちます。

## CLIの例

```text
python -c "from pathlib import Path; Path('outputs').mkdir(exist_ok=True)"
python -I scripts/render_score_sf2.py examples/western-15s.score.json outputs/western.wav --duration 15 --lang ja
python -I scripts/verify.py outputs/western.wav --lang ja
python -I scripts/soundfonts.py search "ピアノ" --lang ja
python -I scripts/instruments.py search "얼후" --lang ko
```

未ミックスWAVのラウドネス検査にCHECKが出る場合があります。最終的な2パス正規化は動画ミックス時に行います。

自分の参考音源や動画を使う場合：

```text
python -I scripts/analyze_reference.py reference.wav outputs/reference --seconds 30 --lang ja
python -I scripts/mix.py --video input.mp4 --bgm outputs/western.wav --out outputs/mixed.mp4 --lang ja
```

`--vo narration.wav` または `--keep-audio` を加えると、前景音声に応じてBGMがダッキングされます。既存の既定値は−14 LUFS、−2 dBTP、2パスの `loudnorm` です。明示しない限り追加フェードは行いません。音源声部の寄与はレンダリング時の `--report-levels` で確認できます。

言語指定は表示のみを変え、楽譜や音声処理は変えません。JSON/CSVのキー、技術的な列挙値、時刻、分析数値は維持します。図はローカルフォントを使い、必要な文字がない場合は図のラベルだけ英語に戻ります。HTML本文は選択した言語のままです。[言語対応の詳細](references/languages.md)。

## テストと制約

```text
python -I -B -m unittest discover -s tests -v
```

全テストの前に音源パックと外部ツールを準備してください。再配布しないDSK音源に依存する3テストは明示的にスキップします。スキップをなくす目的でDSKを追加取得しないでください。

開発手順はmacOSとネイティブWindows 10 x64 / Python 3.10で確認し、CP936の既定文字コードとPowerShellも検証しています。Linuxはまだ実機未検証です。テストは楽譜解析・ルーティング・DSPテスト信号・言語整合性・ミックス動作を対象とし、音楽の良さを保証しません。実際の試聴が必要です。参考分析は確認済みの原譜や楽器別ステムではありません。楽器資料には条件付き・未検証の項目があり、小規模サンプルでは本物のレガートや自然な全音域を保証できません。

## ライセンス

個別指定を除くコード・文書は [MIT](LICENSE) です。音源と依存ソフトはCC0やGeneralUser GS独自ライセンスなど、それぞれの条件を維持します。再配布前に [THIRD_PARTY.md](THIRD_PARTY.md) を確認してください。
