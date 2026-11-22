# 脚本一览

所有脚本在 `scripts/`，用 `python3 -I` 运行。依赖见 [dependencies.md](dependencies.md)。

| 脚本 | 作用 | 额外依赖 |
|---|---|---|
| `check_deps.py` | 原生 Python 检查依赖；旧 check-deps.sh 保留兼容 | 标准库 |
| `soundfonts.py` | 扫描实际 SF2、检索、显示乐谱配置、生成 catalog.json | 标准库 |
| `instruments.py` / `sf2_capabilities.py` | 查询演奏资料、逐预设能力、谱面适配、独奏技术探针、结构快照与出声测试 | 查询/扫描仅标准库；探针使用现有音频依赖 |
| `render_score.py` | 乐谱 → WAV（内置合成音色）+ 自检报告 | numpy scipy soundfile |
| `render_score_sf2.py` | 同一份乐谱 → MIDI → FluidSynth + SF2 采样音色 → pedalboard 母带 | fluidsynth mido pedalboard + `soundfonts/*.sf2` |
| `analyze_reference.py` | 纯算法参考前端 → 音符/节奏/和声/结构候选、图与本地报告；不使用学习模型 | librosa, matplotlib（及 numpy/scipy） |
| `hum2score.py` | 哼唱转写成 `motif` 段落 | librosa |
| `analyze.py` | 旧粗略风格 profile，保留给 `imitate.sh` 兼容；不输出完整旋律 | librosa |
| `compare.py` | 对比两份 profile | numpy |
| `mix.py` | 原生 Python 混进视频，闪避，响度归一；旧 mix.sh 保留兼容 | ffmpeg ffprobe |
| `check_melody.py` | 谱面关系描述（拍位和声、素材、乐句、休止；不自动评审质量） | render_score 同依赖 |
| `check_ranges.py` | 音区参照检索与检查；21 项有条件证据、型号/定弦及待核项见 [instrument-range-evidence.md](instrument-range-evidence.md) | 同 render_score |
| `verify.py` | 数值验收 | numpy ffmpeg |
| `compare_bands.py` | 参考曲与成品的频段能量占比对比，判断“薄/闷/糊” | numpy ffmpeg |
| `compose.py` / `imitate.sh` | 旧的预设快速草稿（无设计，仅作兜底对照） | numpy scipy soundfile / librosa |

## 检查脚本补充

- `check_melody.py score.json [--tracks 声部名,声部名]`：必须让脚本知道哪个声部是旋律，否则报“没有找到旋律声部”并退出。三种办法任选其一：命令行 `--tracks`；乐谱顶层写 `design.melody`，如 `"melody": ["theme"]`；或声部的 `inst` 是 `lead`、`whistle`、`dizi`、`xiao`、`erhu`、`bell`。钢琴、大提琴、长笛等做主旋律时要用前两种。中性描述拍位与和声关系、素材起音/休止及跨小节匹配、显式乐句末音、休止与跳进。原样重复、强拍非和弦音、非主音结束、连续长句不自动判差；不按固定百分比验收创作。乐谱顶层写 `design.chords`（段落名 → 每小节和弦，如 `"A": ["Cm","Fm"]`）结果最准，不写则从和声声部推断。输出是提示，有意为之的设计可以说明理由后保留。
- `check_ranges.py`：先按[音域资料与型号条件](instrument-range-evidence.md)核对实音、型号和定弦；用 `--list-variants dizi` 等查询参照 ID，在适用声部写可选 `range_variant`。原 21 个 low 条目未指定型号时只给条件提示；选择后按对应资料范围检查，明确物理边界或缺音才作相应 CHECK，图示/实用范围外仅待复核。其余旧表行保留原数值提示，未在本次逐条核查。音区不认证预设身份、气口、技法、舒适度或自然感。
- `compare_bands.py ref.m4a out.wav`：模仿参考曲时对比频段占比。新的 `analyze_reference.py` 不输出 `level_range_db`（只有旧 `analyze.py` 有）；电平范围请用每秒电平或自行测量，它只反映所测电平范围，需另查和声、节奏、织体与画面，不能用 3 dB 阈值判定有无高潮。
