# bgmeasy

[English](README.md) · [简体中文](README.zh-CN.md) · **日本語** · [한국어](README.ko.md)

### AIエージェントと、映像に合うBGMをつくる。

どんな場面に音楽を付けたいか伝えると、手元の環境で作った15秒の試作を3つ聴き比べられます。気に入った案を選ぶと、エージェントがその案をもとに全曲を作り、編集できる楽譜と完成音源を渡します。

短い動画、ナレーション、ゲーム、アニメーションの背景音楽に。ファイル操作とコマンド実行ができるコーディングエージェントと組み合わせて使います。レンダリングと参考音源の分析に、別の音楽生成サービスを接続する必要はありません。

[使い始める](#使い始める) · [v0.2.0 音源パック](https://github.com/louchi1984-coder/bgmeasy/releases/tag/v0.2.0) · [制作フロー（中国語）](SKILL.md) · [楽譜形式（中国語）](references/score-format.md)

## まず、場面を伝える

たとえば「結婚式で二人が入場する場面に、歩幅に合う温かな曲を」と一言伝えるだけで始められます。扉が開く瞬間など、音楽を映像に合わせたい箇所があれば、その秒数も添えてください。

| モード | 制作の進め方 |
|---|---|
| **直接作曲** | 場面や雰囲気をもとに、旋律やリズム、楽器の掛け合いを考えます。 |
| **参考モード** | エージェントが雰囲気の近い曲をいくつか探し、楽譜の具体的な箇所を読み比べて、拍の出し方や和声の動かし方を新しい曲に生かします。参考曲のタイトルだけを伝えた場合もこのモードで進めます。 |
| **分析モード** | 読み込める音声・動画ファイルや鼻歌の録音を渡すと、自動でこのモードに入ります。参考音源ならテンポや編成の変化を分析して新しい曲に生かします。自分で歌った旋律なら、その音程とリズムを保ち、演奏する楽器や伴奏を変えた案を作ります。 |

モードを指定済みなら、そのまま制作に入ります。場面や雰囲気だけを伝えた場合は、エージェントが3つのモードを紹介し、選んだ方法で進めます。

どのモードでも、まず**各15秒の試作が3つ**届きます。拍の取り方や和音の進み方など、聴きどころを一言ずつ添えます。1案を選んで番号を返し、希望の変更点も伝えられます。3案とも合わなければ、感想をもとに3案を作り直します。

選んだ後で、完成版の長さと、試作に比べて編成をどれだけ厚くするかを決めます。先に伝えた条件は引き継ぎます。

> 2番で、完成版は60秒に。入場の足取りが伝わるように低音を残して、後半から弦を加えてください。

## 作曲、修正、動画へのミックス

| 作りたいもの・作業 | bgmeasyの使い方 |
|---|---|
| 場面に合わせたオリジナルBGM | 試聴で選んだ案の旋律・和声・リズム・編成を生かして全曲を制作 |
| 試聴後の修正 | 構成と設定を残し、同じ楽譜の必要な部分を調整 |
| 自分の鼻歌をBGMにする | 録音から旋律を採譜し、気に入った伴奏で仕上げる |
| ナレーションや台詞を支える音楽 | 編曲で声のための余地を作り、ミックス時は前景音声に合わせてダッキング |
| 動画へ組み込む | WAVを出力するか、映像ストリームをコピーして音声をミックス・ラウドネス調整 |

オリジナル曲では通常、試聴用のWAV、編集用のMIDI、レンダリングに使ったJSON楽譜をお渡しします。別途サンプラーで鳴らしたパートや音声エフェクトはWAVに含まれます。必要に応じて動画にもミックスできます。

## 使い始める

### 1. プロジェクトを取得

```text
git clone https://github.com/louchi1984-coder/bgmeasy.git
cd bgmeasy
```

GitHubからソースZIPをダウンロードすることもできます。

### 2. 実行環境を用意

**Python 3.10以上、FFmpeg/FFprobe、FluidSynth**が必要です。サンプル音源を使う完全な手順では、約**179 MB**の音源パックも利用します。具体的なコマンドは下の折りたたみ欄にあります。WindowsはネイティブPythonとPowerShellで実行でき、Git BashやWSLは不要です。

### 3. エージェントにスキルを読ませる

コーディングエージェントにプロジェクトの場所を伝え、次のように依頼します。

> このプロジェクトのSKILL.mdを読み、実行環境を確認してください。二人が再会する場面に温かな器楽曲を付けたいです。台詞はありません。直接作曲モードで3つの案を音にして、違いを日本語で説明してください。

音声を聴いたら、具体的な修正点を伝えてください。長さ、用途、雰囲気、台詞の有無、使いたい楽器、参考音源を指定でき、編曲の全パラメーターを自分で入力する必要はありません。

<details>
<summary><strong>インストールコマンドと最初のレンダリング例</strong></summary>

FFmpeg、FFprobe、FluidSynthを先にインストールし、実行ファイルをPATHに追加します。Windows版FluidSynthの同梱DLLは実行ファイルの隣に残してください。macOSでは `brew install ffmpeg fluid-synth` を利用できます。

**Windows PowerShell**

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -I scripts/download_soundfonts.py
.\.venv\Scripts\python.exe -I scripts/check_deps.py --lang ja
```

**macOS / Linux**

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -I scripts/download_soundfonts.py
.venv/bin/python -I scripts/check_deps.py --lang ja
```

以下の `python` は上の仮想環境のインタープリターに読み替えてください。付属の15秒の例をレンダリングします。

```text
python -c "from pathlib import Path; Path('outputs').mkdir(exist_ok=True)"
python -I scripts/render_score_sf2.py examples/western-15s.score.json outputs/western.wav --duration 15 --lang ja
python -I scripts/verify.py outputs/western.wav --lang ja
```

未ミックスWAVのラウドネス検査にCHECKが出る場合があります。最終的な2パス正規化は動画ミックス時に行います。

音源パックのインストーラーはSHA-256を検証します。直接取得しにくい場合は、[Release](https://github.com/louchi1984-coder/bgmeasy/releases/tag/v0.2.0)からZIPをダウンロードし、`--archive path/to/bgmeasy-soundfonts.zip` を指定できます。

</details>

## ドキュメント

- **楽器選びと演奏能力の確認**：[演奏・バックエンド資料](references/instrument-performance.md)、[音源カタログ](references/soundfonts.md)。96項目の楽器資料を収録し、公開音源パックは17個のSF2、バリエーションやサンプル打楽器を含む319件の項目を提供します。
- 参考曲の探し方、楽譜の読み比べ方、音源から得た音高・和音・構造の手掛かりは[参考曲の分析ガイド](references/reference-analysis.md)を参照してください。自分で歌った旋律を採譜して編曲する手順は[鼻歌から作曲するガイド](references/hum-workflow.md)にあります。
- **動画へのミックス**：`scripts/mix.py` を使います。`--vo` はナレーション、`--keep-audio` は元音声の保持に対応。既定値は2パス正規化、−14 LUFS、−2 dBTPです。
- **レポート言語の選択**：[中国語・英語・日本語・韓国語の対応](references/languages.md)。`--lang zh|en|ja|ko` で指定します。主スキルと詳細資料は現在も主に中国語です。

## 動作環境とライセンス

v0.2.0はmacOS、Python 3.14.2、標準音源パックで、DSK関連を含む全128件のテストに合格しました。スキップは0件です。このバージョンはWindows実機での再検証を待っています。

コミット `124d698` では、macOS、Python 3.14.2、v0.1.0音源パックで127件のテストを実行しました。124件が成功し、当時のパックにDSKが含まれていなかったため3件をスキップしました。

公開版v0.1.0では、macOSとネイティブWindows 10 x64でそれぞれ121件のテストを実行し、118件が成功しました。別途インストールが必要なDSK音源を使う3件はスキップしています。Linuxは実機で未検証です。

ソースは[MITライセンス](LICENSE)。音源はそれぞれのライセンスに従います。[THIRD_PARTY.md](THIRD_PARTY.md)を参照してください。v0.2.0の標準音源パックには、DSK Asian DreamZのオリジナルSF2と作者のREADMEが含まれます。[配布元のZIP一式](https://github.com/louchi1984-coder/bgmeasy/releases/download/v0.2.0/DSK_Asian_DreamZ_sf2.zip)も別途ダウンロードできます。複製・配布の条件は[DSK Musicのライセンス](https://www.dskmusic.com/license-info/)、音源の出典は[リリース告知](https://rekkerd.org/dsk-music-releases-dsk-asian-dreamz-vol-1/)をご覧ください。

音楽の仕上がりは実際の試聴で確認してください。音源の奏法対応や参考分析の確かさも、資料と実際の音に照らして判断する必要があります。
