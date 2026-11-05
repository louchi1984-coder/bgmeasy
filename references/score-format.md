# 乐谱格式（score.json）

证据类别：本页为**本机实现**（G05、R05、I01、A01、A03），依据当前脚本，不是乐理定律；设计草图与字段用法为**项目归纳** G01/G02。详见 [theory-evidence.md](theory-evidence.md)。

渲染命令：`python3 -I scripts/render_score.py score.json out.wav --duration 15`
范例：`examples/western-15s.score.json`。出错时渲染器会指出 段落 / 声部 / 第几小节。

## 顶层字段

| 字段 | 含义 |
|---|---|
| `bpm` | 速度。传 `--duration` 时会微调以凑准时长 |
| `beats_per_bar` | 每小节四分音符时值单位数，默认 4；没有独立拍单位/分组字段，6/8 可用 3 个单位表达时长并另注明两组八分重音，不能直接写 6 当作 6/8 |
| `key` | 如 `"E minor"`。只用于出调检查，不影响发声 |
| `swing` | 0~0.5，普通音符中半拍位置的起音后推；SF2鼓格与VCSL分支未读取，见节奏文档 R05 |
| `humanize_ms` | 音符时间随机抖动，默认 6ms；鼓不抖 |
| `reverb_level` | 全局混响量，默认 1.0 |
| `tracks` | 声部表，见下 |
| `sections` | 段落表：段落名 → 声部名 → 小节列表 |
| `arrangement` | 段落顺序，`"A*2"` 表示重复 2 次 |
| `design.performance` | 各声部的乐器身份、演奏意图、音源实现、限制与核听状态；只作设计记录，不自动触发奏法 |
| `design.motif` | 素材音高/时值与休止；允许直接陈述/重复，可用 `|` 分隔小节，供跨小节关系描述 |
| `design.motif_review` | 素材与整句复核记录：`role`职能、`identity`身份、`phrase_plan`呈示/保持/延续与结束；不自动判质量 |
| `design.rhythm` | `pulse/subdivision/accents/roles`：共同节奏参照与声部配合，作者记录，不自动生成鼓点 |
| `design.harmony` | 和声节奏、低音与内声部连接意图，作者记录，不触发声音控制 |
| `design.phrases` | 声部名 → 乐句列表；`start_bar/end_bar` 为展开 arrangement 后全曲从 1 开始的闭区间，附 `function/target`，供整句核对 |
| `design.ending` | 闭合、开放、循环连接或强击结尾及理由，不触发自动收尾 |

写作品音符前按 [instrument-performance.md](instrument-performance.md) 查询拟用乐器与实际预设。写完用 `python3 -I scripts/instruments.py score score.json --backend sf2` 检查适配。不能把SF2未读取的 `params.attack/decay/breath` 等当作已生效，也不能把设计文字当作已经实现的演奏。
`design.performance.<声部>.instrument` 要填库内乐器 ID（如 `guzheng`、`erhu`、`flute`、`electric-bass`、`drum-kit`），可用 `python3 -I scripts/instruments.py search 关键词` 查；写中文名或自造名会被报“不在资料库”。

创作先按 [music-design.md 第0节](music-design.md#0-确定时长后先规划全曲) 建立全曲方案（用户约定 G06），复用现有 `design` 字段简记。主题、和声、节奏或音色短素材可用于试探方案（G01）；正式写谱应贯通覆盖全长的核心草图，再细化声部。此流程不新增字段验证或改变渲染格式；设计记录须能在谱面核对，旧谱缺少记录仍可渲染，字段齐全不等于音乐或听感合格。

### 检查注释：节奏、乐句与和声时间

下面字段只供 `check_melody.py` 和人工检查，原装渲染器忽略它们，实际音符仍须写入 sections：

```json
"design": {
  "melody": ["theme"],
  "rhythm": {"pulse": "4/4 四分主拍", "subdivision": "直八分",
             "accents": "1拍支点，句末释放", "roles": {"bass": "与和弦共同落点", "theme": "弱起长句"}},
  "harmony": {"rhythm": "A第一小节C保持，第二小节两拍换和弦", "bass": "C3—B2—A2", "inner_voices": "保留共同音并就近连接"},
  "chords": {"A": ["C", [{"beat": 0, "chord": "G/B"}, {"beat": 2, "chord": "Am7"}]]},
  "phrases": {"theme": [{"start_bar": 1, "end_bar": 2, "function": "呈示", "target": "Am上的E，继续而非完结"}]},
  "ending": "开放衔接，按后续画面继续"
}
```

`design.chords` 保留原来的“每小节一个字符串”及不足循环用法；小节内多和弦可用上述列表，`beat` 从 0 开始，以同一四分时值单位计，首项为 0、其后严格递增且小于每小节总长。持续跨小节的和弦可重复标注；这不代表音符应重新起音。检查器识别常见转位和扩展和弦，未知标签中性提示并跳过相关判断，不把它当错误和声。标签音级集合只作参考，实际扩展和弦可省略部分音；注释与音符是否一致仍须核对。

乐句范围跨小节/段落有效，但当前端点以整小节描述；弱起、重叠、连线和具体拍位仍须看实际事件。未标 `phrases` 时只描述段落边界的末个记谱音，不假定每个段落都是一个乐句。

6/8 换算示例：若两主拍每分钟 60，当前格式用 `bpm: 90`、`beats_per_bar: 3`，六个八分音符各写 `.5`，将主拍重音落实在单位 0 与 1.5 的音符/鼓件力度上。3/4 也占三个四分单位，但通常分为三主拍；这一区别需要实际重音和 `design.rhythm` 共同说明，字段本身不会自动生成。

## tracks

可选检查注释 `range_variant` 选择有条件的演奏音域参照，例如 `"range_variant": "dizi.hkco-qudi-c"`。先用 `python3 -I scripts/check_ranges.py --list-variants dizi` 查询并核对型号/定弦。此字段只被音区检查器读取，不改变渲染、音高或音色，不证明实际预设就是该乐器；来源与适用条件见 [instrument-range-evidence.md](instrument-range-evidence.md)。旧谱不填仍可渲染，原21个low条目会显示需要确认型号。

```json
"gtr": {"inst": "pluck", "gain": 0.9, "pan": -0.25, "reverb": 0.2,
        "delay": 0.25, "delay_beats": 0.75, "params": {"decay": 0.35}}
```
`gain` 音量；`pan` -1 左 ~ 1 右；`reverb` 送混响量；`delay` 回声量；`params` 见下表。

采样后端还支持 `preset` 稳定 ID（如 `generaluser-gs:8:27`），以及直接指定 `sf2` 和 `gm.bank/program`。先用 `python3 -I scripts/soundfonts.py search` 检索，用 `show <id>` 取得配置；完整目录与规则见 [soundfonts.md](soundfonts.md)。`inst` 仍须填写，用于基础合成近似和声部职能。

## 乐器

| inst | 音色 | params |
|---|---|---|
| `pad` | 柔和持续的和声垫 | attack, release, bright(0~1) |
| `strings` | 弦乐群，起音慢 | attack, release |
| `pluck` | 拨弦（吉他、班卓感） | decay, bright, release, sustain(true=忽略时值) , strum(秒，和弦分解) |
| `bass` | 低音 | decay, sustain_level, release |
| `sub` | 纯低频正弦 | - |
| `lead` | 合成主音（锯齿） | vibrato, roll |
| `whistle` | 口哨/笛感主音，带气声 | vibrato |
| `organ` | 管风琴 | - |
| `keys` | 电钢琴 | decay |
| `bell` | 钟琴，余音长 | decay |
| `marimba` | 合成马林巴近似，短促 | - |
| `guzheng` | 古筝，明亮拨弦，余音长，起音略上滑 | decay, bend, strum |
| `pipa` | 琵琶，颗粒感强，衰减快；快速重复同音可模拟轮指 | decay |
| `erhu` | 二胡，弓弦，滑入起音，较深颤音 | bend, vibrato, rosin |
| `dizi` | 竹笛，亮、气声明显 | bend, vibrato, breath |
| `xiao` | 洞箫，柔暗、起音慢 | bend, vibrato, breath |
| `drums` | 鼓组，用格子记谱 | - |

没有的音色就用最接近的，并如实告诉用户。

采样后端的 `erhu` 支持显式填写 `params.bend`（从下方滑入的半音数）和 `params.vibrato`（揉弦的频率变化比例，如 `.009`）。它们通过 MIDI 弯音控制实现，范围固定为 ±2 半音，只能用于单音旋律，不能同时写和弦；不填写则保持原有音源表现。该控制不等于真实连奏、换弓或滑音采样，也不会改善采样本身的音色。其余乐器的这些参数目前仍只在内置合成后端生效。

## 音符记号（旋律/和声声部，每个小节一个字符串）

- `E4:1.5` 音名+八度（C4=中央 C，`F#3`、`Bb2`），冒号后是拍数，支持 `.5`、`1/3`。
- `E3+G3+B3:4` 和弦（同时发声）。
- `r:1` 休止。
- `E4:1@0.6` 力度 0~1，默认 0.8。
- `(E3:.5 B3:.25 E4:.25)*4` 重复组，不能嵌套。
- **每小节总拍数必须等于 `beats_per_bar`**，否则报错。
- 小节列表比段落小节数短时会循环使用。
- 当前没有延音线语义，跨小节同音写成两项会重新起音；无通用延音踏板或真实连奏控制。需要这些效果时按实际后端能力改写或说明限制，不能只写在 design 里声称实现。

## 鼓记号（`inst: "drums"` 的声部）

每小节一个字符串，分号分隔鼓件，每个鼓件 `beats_per_bar × 4` 格；默认4/4为16格，前述6/8换算为12格。以下为4/4示例：
`"kick: x...x...x...x...; hat: ..x...x...x...x."`
`x` 普通 `X` 重音 `o` 轻 `.` 空。鼓件：kick snare hat openhat clap rim tom hoof shaker cowbell taiko（大鼓）gong（锣）bangzi（梆子）crash（强音镲）ride（叮叮镲）。

## 段落

```json
"A": {"bars": 2, "pad": ["Am:..."], "bass": ["..."], "perc": ["..."]}
```
`bars` 可省略，取各声部小节数最大值。不写的声部在该段静音，用来做编配层次。

## 段落力度 dynamics（仅采样后端 render_score_sf2.py 生效）

顶层字段 `"dynamics": {"A": 0.55, "B": 1.0}`：段落名 → 0~1。SF2声部发送CC11；VCSL声部将该值乘到传入velocity，响应取决于选层和幅度实现，尤其大鼓不保证连续缩放响度。没写的段落为1.0。实现细节见 [instrument-performance.md](instrument-performance.md)。
音符力度影响多大取决于预设的力度响应；母带处理可能改变动态，但不能断言一定抹平差距。CC11是现有表情控制选项，不自动形成高潮；需结合节奏、音区、和声、奏法与织体检查（A03/G04）。内置合成器 render_score.py 不读这个字段。
渲染采样版时可加 `--comp-ratio 1.3` 放宽母带压缩（默认 2.0，1.0 为几乎不压）。

## 采样后端的音色与鼓组选择（render_score_sf2.py）

- 旋律声部：`"gm": {"program": 59, "bank": 8}` 指定实际 SF2 bank/program（均 0 起算）；使用 MMA 模式，以 CC0=`bank >> 7`、CC32=`bank & 127` 编码。省略 bank 为 0；不存在的预设会报错。
- 鼓组：drums 声部写 `"gm": {"program": 40}` 选择刷子鼓组，省略 bank 为 128、program 为 0。GeneralUser 共13套鼓组；可写 `"preset": "generaluser-gs:128:16"` 选择 Power。不同 drums 声部若选择不同来源、bank 或 program 会报错，因为它们共用通道10。
- 外部鼓库：支持 drums 声部的 `sf2`，或直接选 `freepats-light/electronic-drums:0:0`、`freepats-light/world-percussion:0:0`；它们实际在 bank 0。世界打击 preset 会附带 `drum_notes` 映射，也可手动用该字典覆盖鼓件的 MIDI 音高。
- taiko/gong 默认仍使用已有 VCSL；指定 `drum_notes` 时优先使用映射。crash/ride 的 GM 音高分别为49/51，基础合成版只作噪声近似。
- 渲染输出打印音色文件、bank、program 和实际预设名，注意核对。不要将检索类别当作必须使用的风格配器。
