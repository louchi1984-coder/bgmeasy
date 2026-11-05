---
name: bgmeasy
description: 为视频、动画、演示设计并制作背景音乐（BGM）。由 agent 先设计一份乐谱（速度、调式、和弦、旋律、配器、编配层次），再用渲染器合成 WAV，自检、混入视频（旁白自动闪避）、响度归一与验收；也能分析参考曲，借鉴其风格参数后重新设计。适用于“配个 BGM”“做一段××风格的音乐”“模仿这首的感觉”“把 BGM 混进视频”“检查音量/结尾”。不负责下载版权音乐，也不能代替人耳核听。
---

# BGM：由 agent 设计乐谱，脚本负责渲染与检查

核心是**先规划全曲，再展开写谱**。确定用途与时长后，以“**这句为什么接下一句、最终要到哪里**”组织整段音乐，让旋律、和声、节奏和各声部共同实现去向。先形成覆盖全曲的方案与草图，再细化音符、配器和演奏；试写中可以调整，但须回看全曲关系，不能逐小节独立填音后再补结构说明。这是用户明确的项目工作法（G06），不是所有音乐的唯一作曲次序。脚本负责渲染与检查，不能代替这些创作判断。

证据优先：[references/theory-evidence.md](references/theory-evidence.md) 区分资料定义/有范围指导、项目归纳、用户偏好、本机实现和待核。写法建议不自动成为硬规则；新增判断须标依据及适用范围，未验证的联想只能作候选。

**写谱前先读这两页，交付前自问五个问题：**
- [references/common-failures.md](references/common-failures.md)：用户反馈整理出的典型失误，写谱前先看。
- [references/reasoning-case-night-cruise.md](references/reasoning-case-night-cruise.md)：模仿参考曲的推理范例（观测 → 采纳/舍弃）；学推理，不要抄乐谱。

交付前自问：
1. 我复现的每个特征，在参考曲或需求里有证据吗？
2. 有没有把联想（曲名、风格词）当成事实？
3. 有没有把分析候选（音符、和弦、结构）当成结论？
4. 有没有沿用上一首的层、套路或模板？
5. 没听过的部分，有没有写“未核听”？

参考（按需读，不必全读；范例只看格式与推理，不要照抄音符、和弦、层配置）：
- [references/music-design.md](references/music-design.md)：怎么设计（共同节奏、完整乐句、和声与声部连接、配器、结构和自检）
- [references/chord-progressions.md](references/chord-progressions.md)：和弦进行候选、和声节奏、转位与声部连接；和弦编号不是情绪或质量保证
- [references/melody-patterns.md](references/melody-patterns.md)：素材身份、完整乐句的呈示/确认/延续、变化手法及谱面复核
- [references/rhythm-patterns.md](references/rhythm-patterns.md)：共同脉冲、重音与细分、声部节奏配合；鼓型和节奏格仅作候选
- [references/score-format.md](references/score-format.md)：乐谱格式、乐器、记号
- [references/soundfonts.md](references/soundfonts.md)：已安装音源、中英文检索、preset ID、音色银行变体与鼓组选择
- [references/vocal-space.md](references/vocal-space.md)：说唱伴奏或配旁白/对白时怎么为人声让位（频率、时间、动态、声场、纹理、结构）；这类需求先读
- [references/instrument-performance.md](references/instrument-performance.md)：写谱前查乐器演奏资料、实际音源能力和后端限制；用查询命令按需读取相关资料卡
- [examples/western-15s.score.json](examples/western-15s.score.json)：完整范例（15 秒西部风格）
- [examples/wuxia-15s.score.json](examples/wuxia-15s.score.json)：完整范例（15 秒中国古风侠客，用古筝/二胡/竹笛/琵琶/大鼓/锣）
- [examples/witty-adult-15s.score.json](examples/witty-adult-15s.score.json)：选音理由范例（成人向轻松诙谐，含 timbre_reason、鼓组切换）
- [references/dependencies.md](references/dependencies.md)：依赖

所有脚本在 `scripts/`，用 `python3 -I` 运行。路径以本 skill 目录为准。Windows 用已装依赖的 `python -I` 或解释器完整路径替代 `python3 -I`；标准流程全部直接调用 Python，不需要 Git Bash。依赖与 DLL 条件见 [dependencies.md](references/dependencies.md)。

中英日韩乐器检索与 `--lang zh|en|ja|ko` 报告选项见 [languages.md](references/languages.md)。按用户语言选择报告参数；稳定 ID、乐谱字段与音频处理不随语言变化。

## 流程

创作按“全曲方案 → 全长草图 → 配器细化 → 全曲复核”组织（G06）。可用主题、节奏、和声、音色或纹理短素材试探方案；这不替代正式展开前的全曲规划（G01）。设计记录简明复用，具体方法见 [music-design.md](references/music-design.md) 第0节；后面的渲染、混音与验收命令保持原标准流程。

**0. 检查依赖**：`python3 -I scripts/check_deps.py`。必需项缺失先补齐。

音色候选从实际安装目录检索：`python3 -I scripts/soundfonts.py search "吉他"`、`search "变体"`、`search --kind drums`。目录确认可用预设；写谱前还须按2b查询相关演奏资料与实际能力，不把类别当成固定风格搭配。

**1. 先分析需求，不清楚就反问，确认后再创作。** 正式写谱前，先逐项核对下面 7 项，每项标为“已知 / 可合理推定 / 不清楚”：
1. 用途与画面：配什么内容（短剧、产品介绍、游戏、vlog），画面讲什么，观众该感到什么。
2. 情绪与风格：用两个词说清楚；“趾高气昂”“武侠”这类词有多种理解时要确认（例如“趾高气昂”可能是得意滑稽，也可能是反派的拽）。
3. 总时长与重点时刻：整段多长，**有没有高潮**（见 music-design.md 1b）、哪里是转折、结尾。需求没说且画面没有明显高潮点时，默认按“平稳型”做，不要自己加高潮。
4. 有无旁白、对白、原声：有就要给人声让位。
5. 是否有参考曲、必须用或必须避开的乐器与风格。
6. 交付要求：格式、响度规格、是否直接混进视频。
7. 是否已有成品曲目：有就直接用，不重新创作。

处理方式：
- 影响方向的项（2、3、4）不清楚时，**先问用户，一次最多问 3 个问题**，每个问题给 2~3 个具体选项和你的推荐，不要问开放式问题；用户没回答前不创作。
- **无法提问时**（例如被子 agent 或自动流程调用）：不要停下来等回答。按需求自行推定，把每条假设和理由写进 `design.need` 或交付说明，让用户可以事后修改。
- 次要项（速度、调式、配器）不要问，按需求自行推定，并在设计说明里写明假设。
- 需求已经清楚就不要多问，直接进入设计。
- 确认后写**设计说明**（几句话，给用户看）：用途与情绪、有无旁白/原声、总时长与重点时刻、速度/调式/循环/配器/能量走向各自的理由、结尾怎么落定。用户已给定曲目、风格或参考时，直接采用，不替换。

**2. 选来源**
- 用户提供授权曲目：直接用，只做剪辑、混音、响度。
- 用户给参考曲：先读取 [reference-analysis.md](references/reference-analysis.md)，取得实际可分析的本地音频，再运行 `python3 -I scripts/analyze_reference.py ref.mp3 work/reference-study --seconds 60`。用纯算法输出带时间戳的旋律、多音高/暂定声部线、分频段节奏与局部脉冲、和声和结构候选；不接模型、下载权重或调用音频API（G07）。读取 `reference.json`、音符/声部候选CSV与分析图，按时间整理观测和不确定判断，再进入2a规划原创作品。只给曲名或未取得音频时不能声称已分析参考；候选转谱不当作原谱。旧`analyze.py`保留供旧命令兼容，不作为此新流程的默认入口。
- 用户哼唱了一段旋律（录音、口哨、清唱，音频或视频文件）：走**哼唱创作**。先辨认哼唱提供的是短动机、完整主题还是较完整的曲段，不预设素材一定不完整。按用户目标保留核心、转写或扩展为BGM；完整材料不为执行“发展”步骤而强行改写（G01/M06）。
  1. 先问清（缺就问）：整首的用途、时长与情绪；速度（能报 bpm 最好，哼唱节拍不稳）；调性有没有要求；哼唱里哪一小段是想保留的核心动机；主音色。
  2. `python3 -I scripts/hum2score.py hum.m4a score.json --bpm 100 [--key "D major"] [--inst whistle|erhu|dizi|lead|bell]`，把哼唱转写成 `motif` 段落，并写入 `design.motif`。终端会打印音准偏差、八度移位、bpm 来源、调性可信度、被吸附的音数和逐小节和弦。
  3. 先核对转写：调性可信度 <0.05 或 bpm 是估计的，就和用户确认后用 `--key`、`--bpm` 重跑；出调音被吸附时告诉用户，需要保留就加 `--no-snap`。动机的音高和节奏不要擅改，这是用户的创意内核。成品先组织完整乐句（见 melody-patterns.md），可原样呈示和重复，不强制先变形；`motif` 段落用于核对转写，用户明确要求原样保留的内容优先遵循。
  4. **把哼唱纳入全曲方案**：进入2a，先规划已有材料在全长中的位置、前后连接和最终去向，再按2b与3落实和声、节奏及配器。按 melody-patterns.md 选择必要的保持、回应或延续；完整材料可原样保留，不以变法数量证明发展，也不要求每条旋律都从同一动机派生（M06）。自动推断的和弦只作候选。
  5. 渲染后对照用户的哼唱试听：动机每次出现是否听得出来，是否被编配盖住。
  6. 局限：单声部干声最准，有伴奏或混响大会出错；格子默认 16 分音符，三连音和自由节奏会被扭成直拍；跨小节长音被拆成两个同音；自动和弦只是近似。需要 librosa。
- 其他：直接进入2a，按 music-design.md 规划全曲。
- 要真实乐器、人声、成熟编曲：本脚本做不到，如实告知，请用户提供素材。

**2a. 确定时长后，先规划全曲**：按 [music-design.md 第0节](references/music-design.md#0-确定时长后先规划全曲) 建立覆盖正文与结尾的方案：整体起点和终点、各部分的职能与长度、主题或核心材料如何贯穿、乐句为何相接，以及和声/低音、共同节奏、声部职能怎样配合。复用 `design.arc/structure/ending/phrases/chords/rhythm/harmony/layers` 简记，不新增必填表格。用速度、拍号与小节数核对总长，避免按秒数均分后填音。允许重复、停留、悬置、循环和开放结尾；不固定套提问—回答—收束，也不要求每句落主音。

**2b. 按全曲职能核对音源能力**：提出音色候选后，阅读 [instrument-performance.md](references/instrument-performance.md)，运行 `python3 -I scripts/instruments.py instrument <乐器ID>` 和 `preset <实际preset ID>`，核对发声、音区、奏法与当前后端实现；不要一次加载整库。在 `design.performance` 记录演奏意图、实现和限制，在 `design.timbre_reason` 说明具体音源如何承担职能。需要而未实现的奏法须改写、换源或明确近似；资料不固定绑定风格，也不禁止实验性用法。关键主奏先做独奏试句，无法核听则标“未核听”，不把技术出声测试称作自然感验收。

**3. 在全曲方案内写谱，再细化配器**：写 `score.json`（格式见 [score-format.md](references/score-format.md)）。先贯通覆盖全长的核心材料与关键和声、节奏和落点草图；主题型以完整旋律为核心，律动/纹理型按其核心组织全长，不强塞歌曲式主题。再展开各声部与演奏细节。和弦、旋律和鼓型围绕同一去向调整，不独立套模板拼接。按 [melody-patterns.md](references/melody-patterns.md) 简记 `design.motif/motif_review/phrases`；局部改动影响句长、落点或衔接时，同时更新全曲方案与有关声部。

**3b. 用实际乐谱复核全曲关系**：逐个主要连接检查“前句留下什么—此句为何承接—下一步和全曲末端去哪里”，再核对旋律、低音、和声、重音与声部进出是否落实。保持或重复也可有作用，但须符合整体用途；不能只列结构名称或补写解释。关系缺失时调整音符或全曲方案，字段齐全与技术检查通过都不能证明好听。运行 `python3 -I scripts/instruments.py score score.json --backend sf2` 检查能力适配；内置合成版用 `--backend synth`。随后进入原标准渲染流程。

**4. 渲染并读报告**
```bash
python3 -I scripts/render_score.py score.json bgm.wav --duration 30 [--tail 0.8]
```
- `--duration` 为成品总长（含尾音）；速度会微调凑准，偏离 >8% 时警告，应改小节数。
- 报错会指出 段落 / 声部 / 第几小节（拍数不对、鼓格数不对、乐器名错误）。先修错。
- **时长要铺满**：`--duration` 是成品总长，按约定时长组织音乐，不无意提前结束；按需求选闭合、开放、循环连接或强击结尾，不要求全员重击、末音主音或恒定力度。默认 `--tail 0.8` 保持原渲染行为；需要更长自然释放时用已有 `--tail` 并重算正文，不把该默认值当乐理规定。
- 报告含：每小节各声部音符数、每小节电平、各声部音域与出调音占比、有效时长（verify.py）。**用它们核对你设计的意图**：声部进出是否对应 design.layers、电平走势是否符合设计意图（电平只作技术描述，不据此判高潮）、调外音是否有音乐作用、结尾是否按设计完成。有效时长阈值不等于终止质量。
- **旋律检查**：`python3 -I scripts/check_melody.py score.json`。中性描述拍位与和声关系、素材起音/休止及跨小节匹配、显式乐句末音、休止与跳进；显示设计记录供谱面复核。原样重复、强拍非和弦音、非主音结束、连续长句不自动判差；不按固定百分比验收创作。乐谱顶层写 `design.chords`（段落名 → 每小节和弦，如 `"A": ["Cm","Fm"]`）结果最准，不写则从和声声部推断。输出是提示，有意为之的设计可以说明理由后保留。
- **乐器音区检查**：`python3 -I scripts/check_ranges.py score.json`。先按[音域资料与型号条件](references/instrument-range-evidence.md)核对实音、型号和定弦；用 `--list-variants dizi` 等查询参照ID，在适用声部写可选 `range_variant`。原21个low条目未指定型号时只给条件提示；选择后按对应资料范围检查，明确物理边界或缺音才作相应CHECK，图示/实用范围外仅待复核。其余旧表行保留原数值提示，未在本次逐条核查。音区不认证预设身份、气口、技法、舒适度或自然感。
- **模仿参考曲时**：渲染后用 `python3 -I scripts/compare_bands.py ref.m4a out.wav` 对比频段占比；新的 `analyze_reference.py` 不输出 `level_range_db`（只有旧 `scripts/analyze.py` 有）；电平范围请用每秒电平或自行测量，它只反映所测电平范围，需另查和声、节奏、织体与画面，不能用 3 dB 阈值判定有无高潮。
- 不满意就定位问题、改乐谱再渲染；每轮可先聚焦一两处，不以固定轮数宣称合格（A02）。

**4b. 采样音色版（可选，听感通常更真实）**
```bash
python3 -I scripts/render_score_sf2.py score.json bgm-sf2.wav --duration 30 [--mute 声部1,声部2] [--soundfont X.sf2]
```
- 乐器→GM 音色是近似映射，打印在输出里；声部里写 `"gm": {"program": 40}` 可覆盖。通用 GM 中二胡、琵琶用 Fiddle / Shamisen 近似。`ethnic-light/erhu-practice:0:0` 的CC0演奏切片已获用户试听认可，但仅映射A4/C5，样本分别约1.015/2.05秒，不是全音域二胡库。旧 `ethnic-light/erhu` 未通过用户试听，保留评估；BISA两种录音音色获认可，许可版本待核，未安装。具体能力与配置见 references/soundfonts.md。
- 优先从 `soundfonts.py` 检索实际预设，再在声部写 `"preset": "generaluser-gs:8:27"` 等稳定 ID；它会解析为对应 SF2、bank 和 program。13 个轻量 CC0 音源已接入，详见 references/soundfonts.md。直接写 `sf2`、`gm.bank/program` 仍支持；不存在的预设会报错，不静默回退。鼓组也可通过 preset 选择，外部鼓库及 bank 0 鼓组均可用。
- 当前后端含乐器音量补偿；具体持续/衰减预设的平衡仍取决于音区、奏法、力度和织体，不能按名称概括谁一定更响（O02）。**换音色库后要重新检查各小节电平**，层次被抹平就用 `--mute` 逐个静音声部排查。
- **各层实际贡献**：加 `--report-levels` 渲染，会逐层静音相减，打印每层的实际贡献，比最响层低 12 dB 以上的层标出“可能听不清”。数值不替代听感，详见 [loudness-calibration.md](references/loudness-calibration.md)。`--calibrate`（响度校准表折算 gain）是实验功能，默认关闭。
- **乐器音区与技法**：写谱后跑 `check_ranges.py`；二胡的揉弦、滑入是真实弯音但同一声部共用参数，竹笛等技法只能用音符模拟，见 [technique-notes.md](references/technique-notes.md)。
- 先渲染合成版和采样版，对比后选更合适的；两者用同一份乐谱，时长与小节数一致。
- **VCSL 采样器**（`scripts/sampler.py`，CC0）：声部里写 `"engine": "sampler:dantranh"`，该声部改用 Dan Tranh（越南十六弦筝，接近古筝）真实采样，按音高选最近采样并变调（±5 半音）、按力度选层。鼓组里的 `taiko` 自动改用 Bass Drum 采样、`gong` 改用 Gong 采样（声部加 `"gm_drums": true` 可改回 GM 音色）。范例：`examples/wuxia-15s-vcsl.score.json`。
- **外部 SF2 音色库**：声部写 `"sf2": "DSK-Asian-DreamZ.sf2", "gm": {"program": 4}`，改用指定音色库预设（DSK原名：0 PIPA、1 PIPA TREM、2 LUAN、3 GUZHEN、4 ERHU、5 BAN-DI、6 Chinese Percussion）。LUAN与BAN-DI的具体乐器身份待核实，不能沿用旧目录“柳琴/竹笛”的翻译作事实。按音色库分开渲染再混合；换库后用 `--mute` 逐个核对贡献。范例：`examples/wuxia-15s-dsk.score.json`。
- 采样长于乐谱总长时会在结尾淡出，避免硬切；换采样后仍要看有效时长。

**5. 混音**
```bash
python3 -I scripts/mix.py --video in.mp4 --bgm bgm.wav --out out.mp4
# 可选：--vo narration.wav --keep-audio --bgm-db -16 --duck-ratio 6
```
- 旁白永远在前：有 `--vo` 或 `--keep-audio` 时，BGM 由前景声侧链压缩自动闪避。
- 默认归一到 -14 LUFS、真峰值 -2.0 dBTP（两遍 loudnorm），视频流直接复制。交付规格不同用 `--lufs --tp`。
- `--keep-audio` 保留视频自带声音；不加则替换为 BGM（+旁白）。
- **分清音乐表情与音频淡入淡出**：谱面力度、重音与乐句渐强渐弱由音乐需要决定，并核对后端实际支持；混音的 `--fade-out` 默认保持 0，除非用户明确要求。遵循标准渲染流程，不自行添加额外处理。

**6. 验收**
```bash
python3 -I scripts/verify.py out.mp4 [--lufs -14] [--tp -1.0]
```
只给数值（响度、真峰值、LRA、开头静音、有效时长、削波）。**听感必须实际播放核听**；做不到就在交付说明里写“未核听”。

## 诚实边界

- 合成器只有一组基础音色，不是成品级录音。别把它说成专业配乐。
- 模仿 = 借鉴风格参数（速度、调式、循环、层次），不复制旋律或音频片段；不要重建受版权保护的具体旋律。
- 参考曲纯算法分析全部是待复核候选：混音基频不保证主旋律，暂定声部ID不认证乐器身份或数量，和弦/调性与结构可能歧义，信号分数不是正确率，未核听状态不变。旧`analyze.py`另有四拍和弦窗等假设，不能将其profile当作完整参考理解。
- 本 skill 不处理音效；需要音效另行处理，并避免音效触发 BGM 降音。

## 脚本一览

| 脚本 | 作用 | 额外依赖 |
|---|---|---|
| `check_deps.py` | 原生 Python 检查依赖；旧 check-deps.sh 保留兼容 | 标准库 |
| `soundfonts.py` | 扫描实际 SF2、检索、显示乐谱配置、生成 catalog.json | 标准库 |
| `instruments.py` / `sf2_capabilities.py` | 查询演奏资料、逐预设能力、谱面适配、独奏技术探针、结构快照与出声测试 | 查询/扫描仅标准库；探针使用现有音频依赖 |
| `render_score.py` | 乐谱 → WAV（内置合成音色）+ 自检报告 | numpy scipy soundfile |
| `render_score_sf2.py` | 同一份乐谱 → MIDI → FluidSynth + SF2 采样音色 → pedalboard 母带 | fluidsynth mido pedalboard + `soundfonts/*.sf2` |
| `analyze_reference.py` | 纯算法参考前端 → 音符/节奏/和声/结构候选、图与本地报告；不使用学习模型 | librosa, matplotlib（及numpy/scipy） |
| `analyze.py` | 旧粗略风格profile，保留给`imitate.sh`兼容；不输出完整旋律 | librosa |
| `compare.py` | 对比两份 profile | numpy |
| `mix.py` | 原生 Python 混进视频，闪避，响度归一；旧 mix.sh 保留兼容 | ffmpeg ffprobe |
| `check_melody.py` | 谱面关系描述（拍位和声、素材、乐句、休止；不自动评审质量） | render_score 同依赖 |
| `check_ranges.py` | 音区参照检索与检查；21项有条件证据、型号/定弦及待核项见references/instrument-range-evidence.md | 同 render_score |
| `verify.py` | 数值验收 | numpy ffmpeg |
| `compare_bands.py` | 参考曲与成品的频段能量占比对比，判断“薄/闷/糊” | numpy ffmpeg |
| `compose.py` / `imitate.sh` | 旧的预设快速草稿（无设计，仅作兜底对照） | numpy scipy soundfile / librosa |
