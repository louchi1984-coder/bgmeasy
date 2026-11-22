---
name: bgmeasy
description: 为视频、动画、演示设计并制作背景音乐（BGM）。由 agent 先设计一份乐谱（速度、调式、和弦、旋律、配器、编配层次），再用渲染器合成 WAV，自检、混入视频（旁白自动闪避）、响度归一与验收；也能分析参考曲，借鉴其风格参数后重新设计。适用于“配个 BGM”“做一段××风格的音乐”“模仿这首的感觉”“把 BGM 混进视频”“检查音量/结尾”。不负责下载版权音乐，也不能代替人耳核听。
---

# BGM：由 agent 设计乐谱，脚本负责渲染与检查

原创先让用户听小样、选写法。写完整版时，先规划全曲，再展开写谱：以“这句为什么接下一句、最终要到哪里”组织整段音乐，让旋律、和声、节奏和各声部共同实现去向。脚本负责渲染与检查，不能代替创作判断。写法建议的依据和适用范围见 [theory-evidence.md](references/theory-evidence.md)，建议不自动成为硬规则。

## 按任务进入流程

| 用户要做什么 | 从哪里开始 |
|---|---|
| 写原创 BGM，或修改已有乐谱 | 写谱前查[典型失误](references/common-failures.md)。新作从步骤 1 开始。改稿从用户已选的小样或成品继续，按反馈调整有关乐句与声部。 |
| 给了参考音频或哼唱 | 直接进入分析模式（步骤 2）。 |
| 把现成音乐混入视频，或只检查音量与结尾 | 已有获准使用的素材时，混入视频从步骤 5 开始。只验收，直接用步骤 6 检查用户给的文件。 |

## 参考资料（按需读，分支注明必读的先读）

- [music-design.md](references/music-design.md)：怎么设计（共同节奏、乐句、和声与声部连接、配器、结构和自检）
- [chord-progressions.md](references/chord-progressions.md)、[melody-patterns.md](references/melody-patterns.md)、[rhythm-patterns.md](references/rhythm-patterns.md)：和弦、旋律、节奏的候选写法，仅作候选
- [score-format.md](references/score-format.md)：乐谱格式、乐器、记号、MIDI 与 WAV 交付
- [soundfonts.md](references/soundfonts.md)、[sampled-rendering.md](references/sampled-rendering.md)：音色库检索与采样音色版渲染
- [instrument-performance.md](references/instrument-performance.md)：写谱前查乐器演奏资料、实际音源能力和后端限制
- [vocal-space.md](references/vocal-space.md)：说唱伴奏或配旁白/对白时为人声让位；这类需求先读
- [reference-analysis.md](references/reference-analysis.md)：参考作品检索、读谱与音频分析；[hum-workflow.md](references/hum-workflow.md)：哼唱创作
- [scripts.md](references/scripts.md)：脚本一览与检查脚本说明；[dependencies.md](references/dependencies.md)：依赖；[languages.md](references/languages.md)：中英日韩检索与 `--lang zh|en|ja|ko` 报告选项
- 范例（用于理解格式和思路，原创曲的音符、和弦与配器需自行设计）：[western-15s](examples/western-15s.score.json)、[wuxia-15s](examples/wuxia-15s.score.json)、[witty-adult-15s](examples/witty-adult-15s.score.json)（含 timbre_reason、鼓组切换）

所有脚本在 `scripts/`，用 `python3 -I` 运行，路径以本 skill 目录为准。Windows 用已装依赖的 `python -I` 或解释器完整路径替代，不需要 Git Bash。

## 流程

**0. 检查依赖**：`python3 -I scripts/check_deps.py`，必需项缺失先补齐。分析参考音频还要确认 librosa (STFT) 和 matplotlib (Agg) 均为 `[OK]`。音色候选从实际安装目录检索：`python3 -I scripts/soundfonts.py search "吉他"`、`search --kind drums`。

**1. 用户流程**

1. **收需求。** 用户可以只给一句用途、画面或想要的感觉。缺方向时先请用户说一句想做什么音乐。保留用户主动给出的时长、配器、旁白、高潮等约束。
2. **确定模式。**
   - 用户已给出音频、视频或哼唱文件：直接进入分析模式，不再问模式。
   - 用户已明确指定模式：直接执行。
   - 其余情况，用一句话介绍三种模式，等用户选择：
     - **直接创作**：我根据你的描述构思不同的旋律、节奏或声部关系，写原创小样。
     - **参考模式**：我先找几首感觉相近的作品，读具体谱段，借鉴不同手法写原创小样。
     - **分析模式**：你给我一段音频或哼唱，我先分析或转写，再据此创作。
3. **交付 3 个可播放的原创小样，等用户选择。** 三种模式都用实际音源渲染，按 1、2、3 提供试听，每段配一句能听出来的区别。三个小样要让人一句话说得出区别：下列三类中，至少有两类在三个小样之间明显不同，只换音色或乐器不算。① 速度或拍感（如慢而疏、中速流动）；② 调式或和声进行（如大调明亮、小调内敛、换一条和弦走向）；③ 旋律走向与主奏角色（如旋律主导、琶音主导、对话式）。描述不出区别就重做。制作和发出前按下面的“小样阶段最低要求”检查。停在选样：用户可以回编号，也可以带修改意见；三个都不合适就按反馈重做三个。受委托制作小样时，把音频交回主对话，由用户决定。
4. **选定后，一次补问成品时长和配器丰富程度**（例如「成品想做多长？配器想跟小样差不多、再丰满一点，还是做成大编制？」），只问尚未给出的项。拿到后（或用户明确交给创作者决定），进入 2a。

**小样阶段最低要求**（完整规划和全套检查留到选定之后）：
- 必读：[common-failures.md](references/common-failures.md)、[music-design.md 的小样试听](references/music-design.md#0a-代表性小样与试听)与[共同节奏](references/music-design.md#1a-全曲方案中的共同节奏)两节、[score-format.md](references/score-format.md)。
- 必做：每个小样先做一两小节的节奏草图，确定从什么声音开始跟拍；写完用 `instruments.py score score.json --backend sf2` 查能力适配（只处理它报的能力错误，缺 `design.performance` 等字段的提示小样阶段可忽略）；渲染后用 `verify.py` 看时长、削波和响度；发出前核对主奏、关键伴奏和拍感，没听过就写“未核听”。
- 可以留到选定之后：`check_melody.py`、`check_ranges.py`、完整的 `design` 字段和 3b 复核。

制作完整版时，简记速度、调式、配器、段落和结尾的设计理由。需要为人声让位时按 vocal-space.md 处理；没有指定高潮且画面没有明显高潮点时，沿用平稳型设计。

**2. 按模式准备材料**

- **直接创作**：按用户方向试写，按步骤 1 第 3 条做出三个小样。
- **参考模式**：按[从听感找谱与提出写法](references/reference-analysis.md#从听感找谱与提出写法)找谱、读具体小节、借鉴手法。只读了谱时，结论限定为记谱事实。然后回到三段试听。
- **分析模式**：先确认文件可读。只有曲名或打不开的链接，不算进入分析模式，回到参考模式并说明没有分析原曲。
  - **参考音频（借鉴）**：借鉴速度、调式、层次、节奏组织，写新的原创曲，不复制受版权保护的旋律。
    ```bash
    python3 -I scripts/analyze_reference.py ref.mp3 work/reference-study --seconds 60
    ```
    纯算法，不接模型、不下载权重、不调用音频 API。输出全是待复核候选：读 `reference.json`、CSV 和分析图，按时间整理“观测 / 算法推测 / 采纳理由”，再把可借鉴的手法用到三个小样。只给曲名或未取得音频时不能声称已分析；候选转谱不当作原谱。
  - **哼唱（保留）**：保留用户自己的旋律，音高和节奏不擅改。
    ```bash
    python3 -I scripts/hum2score.py hum.m4a score.json --bpm 100
    ```
    调性可信度低或 bpm 是估计值时，先与用户确认再用 `--key`、`--bpm` 重跑。三个小样里主旋律保持一致，变的是编配、节奏和声部关系。完整步骤与局限见 [hum-workflow.md](references/hum-workflow.md)。
- 用户指定直接使用已有授权曲目：按要求剪辑、混音或验收。
- 要真实乐器、人声、成熟编曲：本脚本做不到，如实告知。

**2a. 确定时长后，先规划全曲**：按 [music-design.md 第 0 节](references/music-design.md#0-确定时长后先规划全曲)建立覆盖正文与结尾的方案（起点和终点、各部分职能与长度、核心材料如何贯穿、乐句为何相接，以及和声/低音、共同节奏、声部职能怎样配合），用 `design.arc/structure/ending/phrases/chords/rhythm/harmony/layers` 简记。用速度、拍号与小节数核对总长。允许重复、停留、悬置、循环和开放结尾。设计合奏时，在 `design.layers` 里按段写清听众除了主旋律，还应能跟住哪条节奏、低音、和声变化或答句。若设有高潮，默认在高潮合奏处安排至少 5 层（见[配器层次](references/music-design.md#8b-多层先设计再写谱不是越多越好)）。

BGM 默认要有能跟住的基本拍感。先做一到两小节合在一起的节奏草图，确定听众从什么声音开始跟拍、怎样辨认每组重心，以及旋律切分或停顿时拍感靠什么延续，并带入每个乐句。旋律与伴奏共同强调一个落点时，优先一起起音。改动任一声部后，合起来复听受影响的乐句及其再现处，检查同一个重音有没有意外响成两下。采用自由节奏或刻意模糊拍点时，在全曲方案里交代用途和时间组织。详见[共同节奏](references/music-design.md#1a-全曲方案中的共同节奏)。

**2b. 核心材料与乐器相互校验**：在全曲方案内，从主题、律动、纹理或乐器动作切入，按需往返试写。结合声部职能，用 `python3 -I scripts/instruments.py instrument <乐器ID>` 查典型写法，用 `preset <实际preset ID>` 查实际音源和后端能力，把演奏构想落实到音符、节奏、音区、连断与声部配合。主旋律默认优先考虑钢琴等起音清楚、自然衰减的乐器；中国风作品默认将中国民族乐器与其他乐器搭配；用户指定编制时按其要求。用 `design.performance` 和 `design.timbre_reason` 简记依据。详见[配器与主奏偏好](references/music-design.md#8-配器材料乐器和奏法相互校验)和 [instrument-performance.md](references/instrument-performance.md)。

**3. 展开乐谱**：写 `score.json`（格式见 [score-format.md](references/score-format.md)）。把核心材料、配器和共同节奏贯通全长，和弦、旋律和鼓型围绕同一去向调整，不套模板拼接。按 [melody-patterns.md](references/melody-patterns.md) 简记 `design.motif/motif_review/phrases`；局部改动影响句长、落点或衔接时，同时更新全曲方案与有关声部。把重音、乐句走向和演奏语气落实到音符的 `@力度` 与鼓格强弱中，按[力度设计](references/music-design.md#力度设计)处理，优先使用所选音源的原生力度响应。主奏、律动或整体听感明显改变时，用成品音源渲染受影响的乐句，按小样试听标准核对后再请用户听。

**3b. 用实际乐谱复核全曲关系**：逐个主要连接检查“前句留下什么、此句为何承接、下一步和全曲末端去哪里”，再核对旋律、低音、和声、重音与声部进出是否落实；把合奏的实际起音、重音与留白对照节奏草图，尤其检查拍感初次建立处、切分和句末。关系缺失时调整音符或全曲方案；字段齐全与技术检查通过都不能证明好听。运行 `python3 -I scripts/instruments.py score score.json --backend sf2` 检查能力适配；内置合成版用 `--backend synth`。

**4. 渲染并读报告**
```bash
python3 -I scripts/render_score.py score.json bgm.wav --duration 30
```
- `--duration` 为成品总长（含尾音）；速度会微调凑准，偏离 >8% 时警告，应改小节数。默认 `--tail 0.8`，需要更长自然释放时用 `--tail` 并重算正文。
- 报错会指出段落 / 声部 / 第几小节。先修错。
- 按约定时长组织音乐，不无意提前结束；按需求选闭合、开放、循环或强击结尾。
- **成品发出前重新审核拍感**：按[拍感审核](references/music-design.md#1a-全曲方案中的共同节奏)检查开头、切分、换段、声部进出与结尾。发现意外丢拍或重心跳移时先改谱再渲染。无法核听时注明“未核听”。
- 读报告核对设计意图：声部进出是否对应 `design.layers`、调外音是否有音乐作用、结尾是否按设计完成。电平只作技术描述，不据此判高潮。
- 旋律与音区检查：`python3 -I scripts/check_melody.py score.json --tracks 旋律声部名`（或在乐谱写 `design.melody`）、`python3 -I scripts/check_ranges.py score.json`。输出是提示，有意为之的设计可以说明理由后保留。说明见 [scripts.md](references/scripts.md)。
- 模仿参考曲时用 `python3 -I scripts/compare_bands.py ref.m4a out.wav` 对比频段占比。
- 不满意就定位问题、改乐谱再渲染；每轮可先聚焦一两处，不以固定轮数宣称合格。

**4b. 采样音色版（可选，听感通常更真实）**
```bash
python3 -I scripts/render_score_sf2.py score.json bgm-sf2.wav --duration 30 --keep-mid
```
同一份乐谱渲染合成版和采样版，对比后选更合适的。**换音色库后要重新检查各小节电平**，层次被抹平就用 `--mute` 或 `--report-levels` 排查。预设 ID、DSK/VCSL 写法和二胡切片的限制见 [sampled-rendering.md](references/sampled-rendering.md)。

**5. 按需混入视频**
```bash
python3 -I scripts/mix.py --video in.mp4 --bgm bgm.wav --out out.mp4
# 可选：--vo narration.wav --keep-audio --bgm-db -16 --duck-ratio 6
```
- 旁白永远在前：有 `--vo` 或 `--keep-audio` 时，BGM 由前景声侧链压缩自动闪避。
- 默认归一到 -14 LUFS、真峰值 -2.0 dBTP，视频流直接复制。交付规格不同用 `--lufs --tp`。
- `--keep-audio` 保留视频自带声音；不加则替换为 BGM（+旁白）。
- 混音的 `--fade-out` 默认保持 0，除非用户明确要求；谱面力度和渐强渐弱由音乐需要决定。

**6. 验收**
```bash
python3 -I scripts/verify.py bgm.wav
python3 -I scripts/verify.py out.mp4 --lufs -14 --tp -2
```
- 独立 WAV：两个标准渲染器默认将采样峰值归一到满幅的 0.7（约 −3.1 dBFS）。验收默认比较值为 −14 LUFS（±1.5 LU）、真峰值上限 −1 dBTP。无指定交付规格时报告实测值；有约定时用相应的 `--lufs`、`--tp` 核对，超出时说明偏差。
- 视频成片：对最终编码的文件，用与 `mix.py` 一致的响度目标和真峰值上限验收。
- 同时查看响度范围（LRA）、开头静音、有效时长和削波采样数。**听感必须实际播放核听**；做不到就在交付说明里写“未核听”。

**7. 交付原创成品**

默认把同一版的 `曲名.wav`、`曲名.mid` 和 `曲名.score.json` 一起输出。`--keep-mid` 生成与采样版 WAV 同名的标准 MIDI。核对三个文件可打开，且 MIDI 的速度和演奏事件对应最终版本。选内置合成版交付时，通过采样后端保留配套 MIDI，并说明它是供编辑的近似；缺少采样后端或含 VCSL 等独立采样声部时，如实说明 MIDI 缺失的内容。详见 [MIDI 与 WAV 交付](references/score-format.md#midi-与-wav-交付)。

## 诚实边界

- 合成器只有一组基础音色，不是成品级录音。别把它说成专业配乐。
- 模仿 = 借鉴风格参数（速度、调式、循环、层次），不复制旋律或音频片段；不要重建受版权保护的具体旋律。
- 参考曲纯算法分析全部是待复核候选：混音基频不保证主旋律，暂定声部 ID 不认证乐器身份或数量，和弦/调性与结构可能歧义，信号分数不是正确率，未核听状态不变。旧 `analyze.py` 的四拍和弦窗等假设不能当作完整参考理解。
- 本 skill 不处理音效；需要音效另行处理，并避免音效触发 BGM 降音。
