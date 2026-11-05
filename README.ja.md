# bgmeasy

[English](README.md) · [简体中文](README.zh-CN.md) · **日本語** · [한국어](README.ko.md)

### AIエージェントと、映像に合うBGMをつくる。

場面、雰囲気、必要な長さを伝えると、bgmeasyが曲全体の設計、編集可能な楽譜の作成、ローカルでの音声レンダリングまでエージェントを案内します。旋律、リズム、楽器編成、構成が楽譜に残るため、試聴したあとも同じ曲を調整できます。

短い動画、ナレーション、ゲーム、アニメーションの背景音楽に。ファイル操作とコマンド実行ができるコーディングエージェントと組み合わせて使います。レンダリングと参考音源の分析に、別の音楽生成サービスを接続する必要はありません。

[使い始める](#使い始める) · [音源パック](https://github.com/louchi1984-coder/bgmeasy/releases/latest) · [制作フロー（中国語）](SKILL.md) · [楽譜形式（中国語）](references/score-format.md)

## まず、場面を伝える

たとえば、こんな依頼から始められます。

> 二人が再会する場面に、温かく静かな30秒のBGMを作ってください。台詞はないので旋律を聴かせたいです。最後は落ち着いて締めてください。

試聴したら、同じ曲に修正を加えます。

> 主題はそのままに、前半の伴奏を薄くしてください。後半は少しずつ厚くし、早い段階で盛り上がり切らないようにしてください。

最初に曲全体の到達点を決め、そこへ向かう楽句、和声、共通リズム、各楽器の役割を組み立てます。作曲と修正はエージェントが担当し、ローカルのプログラムが楽譜を音にします。

```text
場面と要望 → 全曲の設計 → 編集可能な楽譜 → ローカルで生成 → 試聴と修正
```

## 作曲、修正、動画へのミックス

| 作りたいもの・作業 | bgmeasyの使い方 |
|---|---|
| 場面に合わせたオリジナルBGM | 曲全体を設計してから、旋律・和声・リズム・配器を具体化 |
| 試聴後の修正 | 構成と設定を残し、同じ楽譜の必要な部分を調整 |
| 参考曲から発想を広げる | 音高・リズム・和声・構造の手掛かりを調べ、新しい曲の設計に利用 |
| ナレーションや台詞を支える音楽 | 編曲で声のための余地を作り、ミックス時は前景音声に合わせてダッキング |
| 動画へ組み込む | WAVを出力するか、映像ストリームをコピーして音声をミックス・ラウドネス調整 |

制作物は、エージェントが書いたJSON楽譜とレンダリングしたWAVです。動画が必要な場合にミックスへ進みます。楽譜と設定を保管しておけば、あとから修正・比較・再現しやすくなります。

## 使い始める

### 1. プロジェクトを取得

```text
git clone https://github.com/louchi1984-coder/bgmeasy.git
cd bgmeasy
```

GitHubからソースZIPをダウンロードすることもできます。

### 2. 実行環境を用意

**Python 3.10以上、FFmpeg/FFprobe、FluidSynth**が必要です。サンプル音源を使う完全な手順では、約**169 MB**の音源パックも利用します。具体的なコマンドは下の折りたたみ欄にあります。WindowsはネイティブPythonとPowerShellで実行でき、Git BashやWSLは不要です。

### 3. エージェントにスキルを読ませる

コーディングエージェントにプロジェクトの場所を伝え、次のように依頼します。

> このプロジェクトのSKILL.mdを読み、実行環境を確認してください。bgmeasyで温かく穏やかな30秒の器楽BGMを作ってください。台詞はありません。全曲を先に計画し、楽譜を書いてレンダリングしてください。楽譜を残し、編曲の内容と出力ファイルを日本語で説明してください。

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

音源パックのインストーラーはSHA-256を検証します。直接取得しにくい場合は、[Release](https://github.com/louchi1984-coder/bgmeasy/releases/latest)からZIPをダウンロードし、`--archive path/to/bgmeasy-soundfonts.zip` を指定できます。

</details>

## ドキュメント

- **楽器選びと演奏能力の確認**：[演奏・バックエンド資料](references/instrument-performance.md)、[音源カタログ](references/soundfonts.md)。96項目の楽器資料を収録し、公開音源パックは16個のSF2、バリエーションやサンプル打楽器を含む312件の項目を提供します。
- **参考音源の分析**：[手法と出力](references/reference-analysis.md)。音高・和音・構造は要確認の手掛かりであり、確認済みの原譜とは扱いません。
- **動画へのミックス**：`scripts/mix.py` を使います。`--vo` はナレーション、`--keep-audio` は元音声の保持に対応。既定値は2パス正規化、−14 LUFS、−2 dBTPです。
- **レポート言語の選択**：[中国語・英語・日本語・韓国語の対応](references/languages.md)。`--lang zh|en|ja|ko` で指定します。主スキルと詳細資料は現在も主に中国語です。

## 動作環境とライセンス

macOSとネイティブWindows 10 x64で検証済みです。Linuxはまだ実機未検証です。公開版は121テスト中118件が成功し、再配布しないDSK音源に依存する3件を明示的にスキップします。

ソースは[MITライセンス](LICENSE)。音源はそれぞれのライセンスに従います。[THIRD_PARTY.md](THIRD_PARTY.md)を参照してください。DSK Asian DreamZは配布しません。

音楽の仕上がりは実際の試聴で確認してください。音源の奏法対応や参考分析の確かさも、資料と実際の音に照らして判断する必要があります。
