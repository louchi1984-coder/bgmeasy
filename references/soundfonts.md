# 已安装音色、检索与选择

证据边界：本页目录、映射、键位和控制说明是**本机实现** I01；音色名称不证明传统奏法、风格或适合主奏。外部演奏主张按 [theory-evidence.md](theory-evidence.md) 与卡内 `claim_review` 判断。

音色目录用于查找**实际可用的音源和编号**，不把风格固定绑定到乐器。先根据质感、音区、起音和声部职能提出候选，再检索并选音，理由写入 `design.timbre_reason`。

写谱前还须按 [instrument-performance.md](instrument-performance.md) 查询乐器演奏资料与逐预设能力：`python3 -I scripts/instruments.py preset <id>`。所有实际目录入口都有资料关联；基础合成器和鼓件别名另行覆盖。结构扫描及出声测试不证明自然感或主奏适合性。DSK的LUAN、BAN-DI保留原名，具体身份待核实，不按旧中文别名断言为柳琴、竹笛。

## 轻量扩充

`soundfonts/freepats-light/manifest.json` 记录来源、许可、下载 URL、SHA-256、下载大小及 SF2 文件大小。原始许可和说明保存在其 `licenses/` 目录。

本批新增 13 个 CC0 音源包：共下载 **78,188,905 字节（78.2 MB / 74.57 MiB）**，新增 SF2 文件 **127,974,818 字节（128.0 MB / 122.05 MiB）**。这是压缩下载预算；解压后的采样文件体积较大。没有另装采样器或付费插件。

| 稳定来源 ID | 内容 | 上游 |
|---|---|---|
| `freepats-light/piano-kw` | 精简版 Kawai 立式钢琴 | [FreePats Piano](https://freepats.zenvoid.org/Piano/acoustic-grand-piano.html) |
| `freepats-light/guitar-clean` | 精简版干净电吉他 | [FreePats Guitar](https://freepats.zenvoid.org/ElectricGuitar/clean-electric-guitar.html) |
| `freepats-light/guitar-jazz` | 精简版爵士电吉他 | 同上 |
| `freepats-light/bass-picked` | 拨片贝斯 | [FreePats Bass](https://freepats.zenvoid.org/ElectricGuitar/clean-electric-bass.html) |
| `freepats-light/bass-finger` | 指弹贝斯 | 同上 |
| `freepats-light/harp` | 音乐会竖琴 | [FreePats Harp](https://freepats.zenvoid.org/OrchestralStrings/harp.html) |
| `freepats-light/clarinet` | 单簧管 | [FreePats Clarinet](https://freepats.zenvoid.org/Reed/clarinet.html) |
| `freepats-light/pad-choir` | 合成人声 Pad | [FreePats Pad](https://freepats.zenvoid.org/Synthesizer/synth-pad.html) |
| `freepats-light/pad-sweep` | 扫频 Pad | 同上 |
| `freepats-light/pad-new-age` | 新世纪 Pad | 同上 |
| `freepats-light/timpani` | 定音鼓 | [FreePats Orchestral Percussion](https://freepats.zenvoid.org/Percussion/orchestral-percussion.html) |
| `freepats-light/world-percussion` | 卡洪、邦戈、铃鼓、康加、沙锤、达布卡等 | [FreePats World Percussion](https://freepats.zenvoid.org/Percussion/world-and-rare-percussion.html) |
| `freepats-light/electronic-drums` | 模拟合成电子鼓组 | [FreePats Electronic Percussion](https://freepats.zenvoid.org/Percussion/electric-percussion.html) |

原有 GeneralUser GS、DSK 和 VCSL 保留。GeneralUser 的钢琴、弦乐、铜管、木管、电子等音色及其变体全部进入目录；DSK 的署名预设不计作乐器。DSK 音色文件仍按本机许可说明处理，不随作品或 skill 分发。

## 民族轻量替换候选（2026-11-05）

新增 `ethnic-light/erhu.sf2`，由 [AliExpress Erhu](https://github.com/sfzinstruments/aliexpress-erhu/tree/6615047b2fd06126877483e97b8bb4af9d00b080) 的 CC0 录音转换，SF2 **22,458,028 字节（22.46 MB）**。许可、上游版本、逐样本哈希、转换脚本及限制随库保存在 `soundfonts/ethnic-light/`；整个新增目录不超过 30 MB。无需注册、商业插件或新增播放后端。

| preset | 内容 | 实际映射范围（不是乐器物理音域） |
|---|---|---|
| `ethnic-light/erhu:0:0`、`:0:1` | 长音 Take 1 / 2，各 20 个录音音高 | D4–A5 |
| `ethnic-light/erhu:0:2` 至 `:0:5` | 短音 Take 1–4，各 20 个录音音高 | D4–A5 |
| `ethnic-light/erhu:0:6`、`:0:7` | sul tasto（指板附近运弓）Take 1 / 2，各 25 个录音音高 | D4–D6 |

共 170 条原录音，转为单声道 32 kHz / PCM16；不额外添加效果、降噪、循环延长或音准校正。原录音的起音、音准和长度差异保留。上游文件名的八度编号高于科学音高记法一组，本库按实际 A4≈440 Hz 映射，不能直接照抄文件名或原 SFZ 的控制映射。

`Take` 是**显式可选预设**，当前后端不自动轮替；无真实力度分层、真实连奏转接、自动换弓或奏法切换。长音只播放到原录音结束，不能当作无限延音。来源本身是低价二胡录音，技术兼容通过不代表自然度优于 DSK；状态仍为**未核听**。可先比较长音/短音的独奏试句，再决定具体作品使用哪个预设。

**用户试听记录（2026-11-05）**：`ethnic-light/erhu:0:0` 的持续拉奏被反馈为一直有刺耳摩擦声；改用 `:0:7` 后，用户确认琴音本身仍偏乌、发闷、不够清亮。当前替代评估未通过，取消该库的升级推荐地位，仅保留候选和比较用途。其余预设未获用户听感验收，不能推定都具有相同缺陷或已经合格。这是本次用户评价，不是通用乐理或对所有二胡音色的判断。

候选复查配置：`"inst": "erhu", "preset": "ethnic-light/erhu:0:0"`。不需要为使用此库额外设置通用 `bend/vibrato`。

旧 DSK ID 与文件保留，已有作品不自动换声；本批仅接入二胡替代候选。古筝、琵琶、LUAN、BAN-DI 与中国打击未完成替换，不能把 Dan Tranh、GM Flute 或合成拨弦改名声称是相应中国乐器。历史 DSK 范例仍是旧音源范例。

### 已通过试听：CC0演奏切片

`ethnic-light/erhu-practice:0:0` 来自 [irzirgpznj的二胡练习录音](https://freesound.org/people/irzirgpznj/sounds/477169/)，原作者标明 [CC0-1.0](https://creativecommons.org/publicdomain/zero/1.0/)。采用无需注册可取得的公开HQ MP3试听版，原条目本身为有损Ogg，不能称为无损原件。SF2 **541,724字节**，与用户2026-11-05回复“都可以”认可的试听A使用的文件逐字节相同；没有在认可后换音、扩展音区或另加处理。

| 实际映射 | 素材时长 | 当前能力 |
|---|---|---|
| A4 / MIDI 69 | 约1.015秒 | 原立体声演奏切片，保留录制的表情 |
| C5 / MIDI 72 | 约2.05秒 | 原立体声演奏切片，保留录制的表情 |

只映射两个实际取出的音高，不将它们大幅移调成全键盘；没有循环延长、真实连奏转接、多力度或自动轮替。持续音超过上述素材长度会提前失声。`instruments.py score` 会报告缺少的键位及超出原样本长度的谱面持续音。用户认可的是该技术片段的音色，不能扩张成完整二胡音源或所有写法均已验收。

配置：`"inst": "erhu", "preset": "ethnic-light/erhu-practice:0:0"`。源录音已有表情，不需要为使用此预设额外加通用揉弦。可复用 [原试听乐谱](../examples/erhu-practice-audition.score.json)检查，参数与已认可的试听保持一致。来源、哈希、切片位置、3毫秒采样边缘窗、署名和用户反馈在 `soundfonts/ethnic-light/erhu-practice-provenance.json` 与 `ATTRIBUTION-erhu-practice.txt`；离线重建脚本为 `build_erhu_practice.py`，输入须匹配固定MP3哈希，输出到新目录。仅增加音源和查询信息，标准渲染/母带/混音不变。

同次试听B/C的Berklee BISA普通揉弦、延迟揉弦音色也获用户认可；[发布页](https://remix.berklee.edu/bisa-chinese-erhu/)仅写CC BY，未列版本号，原始WAV未取得。本次未将其作为已完成许可核查的音源安装，也不自行标成CC BY 4.0。

## 检索

在 skill 根目录执行：

```bash
python3 -I scripts/soundfonts.py search "吉他"
python3 -I scripts/soundfonts.py search "变体 吉他"
python3 -I scripts/soundfonts.py search --kind drums
python3 -I scripts/soundfonts.py search --source freepats-light
python3 -I scripts/soundfonts.py search "二胡" --source ethnic-light
python3 -I scripts/soundfonts.py show ethnic-light/erhu:0:0
python3 -I scripts/soundfonts.py search "二胡 试听通过"
python3 -I scripts/soundfonts.py show ethnic-light/erhu-practice:0:0
python3 -I scripts/soundfonts.py show generaluser-gs:8:27
python3 -I scripts/soundfonts.py show freepats-light/world-percussion:0:0
python3 -I scripts/soundfonts.py build
```

`search` 支持中英日韩乐器别名与名称、类别、来源和标签（见 [languages.md](languages.md)），`--json` 输出完整记录。`show` 输出可直接复制的声部配置。`build` 重建 `soundfonts/catalog.json`。检索与渲染时解析实际 SF2 头部，不依赖可能过期的缓存。

SF2 稳定 ID 为 `相对音色文件名（去扩展名、小写）:bank:program`，均为 **0 起算**。例如 `generaluser-gs:8:27` 是 Chorused Clean Guitar。目录中 `name` 是展示名，`preset_name` 是 SF2 内原名，`family` 和 `tags` 用于检索，不是强制配器规则。

## 乐谱中使用

旋律乐器：

```json
"guitar": {
  "inst": "pluck",
  "preset": "generaluser-gs:8:27",
  "gain": 0.7,
  "pan": -0.2
}
```

新竖琴：`"inst": "pluck", "preset": "freepats-light/harp:0:0"`。

力度鼓组：`"inst": "drums", "preset": "generaluser-gs:128:16"`。

新电子鼓组：`"inst": "drums", "preset": "freepats-light/electronic-drums:0:0"`。

`inst` 是基础合成后端的近似类型；`preset` 决定采样后端的实际音色。仍可直接写 `sf2` 和 `gm.bank/program`，与原有乐谱兼容。若同时指定的字段与 preset 冲突，会明确报错。

## 银行和鼓组

- `gm.bank` 是 SF2 中的实际 bank 编号。渲染器使用 FluidSynth 的 MMA 模式，按 `bank = CC0 × 128 + CC32` 解释；普通 bank 8 编码为 CC0=0、CC32=8。不要再混用 GS 的 MSB-only 编码。
- GeneralUser 有 13 套鼓组，位于 bank 128；包括 Standard、Room、Power、Electronic、808/909、Dance、Jazz、Brush、Orchestral 等。用 `search --kind drums` 查完整目录。
- 本批 FreePats 电子鼓和世界打击库位于 **bank 0**，外部鼓库也按其实际 bank 和 program 选择，音频通道会送入指定音色库。
- 一首曲子的全部 `drums` 声部共用 MIDI 通道10，必须选择同一音色库、bank、program；不同设置会报错，不再被最后一个设置悄悄覆盖。需要混合多个库时，分别渲染后混音。
- `drum_notes` 可覆盖鼓件到 MIDI 音高的映射。世界打击 preset 会自动附带上游键位映射：kick→卡洪、snare/tom→邦戈、hat/openhat→铃鼓、clap→手拍、rim→响棒、shaker→蛋沙锤、cowbell→响板、taiko/gong→达布卡。名称在这里表示节奏声部角色，具体乐器以映射为准。
- 新电子鼓的键位也非 GM：kick=48、snare=50、hat=52、openhat=54、crash=55、ride=56、tom=57、clap=63、shaker=64、rim=66，preset 会自动附带。指定 `drum_notes` 后只能使用其中列出的鼓件；未映射的鼓件会报错，避免播放错误的采样。
- `taiko/gong` 默认仍使用已有 VCSL 采样；明确提供 `drum_notes` 时优先使用该映射。`crash` 与 `ride` 分别使用 GM 音符49、51；基础合成后端仅提供噪声近似。
- 不存在的 bank/program、未知 preset、缺失音色文件会报错，避免以为换了音色却听到默认声音。

VCSL 也可检索：`vcsl:dantranh`、`vcsl:bassdrum`、`vcsl:gong`。后两种使用旋律记谱来触发单击，适合独立编排与分轨混音。

## 核验

```bash
python3 -I tests/test_soundfonts.py
```

测试包含实际 SF2 清单、下载预算、检索、缺失预设报错、鼓组一致性、外部音源映射及 FluidSynth 实际银行／鼓组选择。声音质量与搭配仍需试听；数值通过不等于已经核听。
