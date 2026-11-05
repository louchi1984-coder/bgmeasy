# bgmeasy

[English](README.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md) · [한국어](README.ko.md)

**让 AI agent 在本地设计、渲染和检查背景音乐的 skill。**

由 LLM agent 先规划全曲、写出乐谱，再用 Python 合成器或 SoundFont 渲染 WAV；也可将音乐混入视频、给旁白自动闪避，并用纯算法分析参考曲。

不需要音乐生成模型、模型权重下载、云端音乐 API 或商业乐器插件。创作推理由你使用的编程 agent 完成。

## 包含什么

- `SKILL.md` 与 `references/` 中的全曲规划、乐句发展、和声、节奏和配器资料。
- 内置合成，以及 MIDI → FluidSynth/SF2 → 母带的渲染路径。
- 原生 Python 视频混音：旁白/原声触发闪避、两遍响度归一、视频流直接复制。**Windows 无需 Git Bash 或 WSL。**
- 参考曲音高、节奏、和声和结构的纯算法**候选分析**，保留不确定性，不使用学习模型。
- 中英日韩乐器检索与标准报告：`--lang zh|en|ja|ko`。
- 96 个乐器资料 profile；可选音源包包含 16 个 SF2、312 个目录条目，含变体和采样打击。资料项不等于独立音源库，也不保证音色真实感。

## 安装

建议 Python 3.10+，另安装原生 **FFmpeg、FFprobe、FluidSynth** 并加入 PATH。Windows 的 FluidSynth 可执行文件旁须保留同包 DLL。macOS 可运行 `brew install ffmpeg fluid-synth`。

下载项目，或克隆：

```text
git clone https://github.com/louchi1984-coder/bgmeasy.git
cd bgmeasy
```

创建虚拟环境并安装依赖：

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

下方命令中的 `python` 请替换为该环境的解释器；无需激活环境也能运行。

完整采样流程需要单独下载约 **169 MB** 的音源包，各组件保留原许可：

```text
python -I scripts/download_soundfonts.py
python -I scripts/check_deps.py --lang zh
```

安装脚本校验 SHA-256，拒绝不安全路径，不覆盖内容不同的已有文件。离线安装可先下载 [`bgmeasy-soundfonts.zip`](https://github.com/louchi1984-coder/bgmeasy/releases/download/v0.1.0/bgmeasy-soundfonts.zip)，再加 `--archive path/to/bgmeasy-soundfonts.zip`。音源二进制放在 Release，不进入 Git 历史。**不分发 DSK Asian DreamZ。** 详见[第三方许可](THIRD_PARTY.md)。

## 交给 agent 使用

让有文件读写及命令执行能力的 agent 读取 [`SKILL.md`](SKILL.md)，例如：

> 用这个 skill 做一段 30 秒温暖、安静的 BGM，无对白。先规划全曲，写出有逻辑的主题，再按标准流程渲染，报告用中文。

主 skill 和详细参考资料目前仍以中文为主；README、乐器别名与标准报告界面支持四语。原始引文和用户注释保留原文。

## 命令示例

```text
python -c "from pathlib import Path; Path('outputs').mkdir(exist_ok=True)"
python -I scripts/render_score_sf2.py examples/western-15s.score.json outputs/western.wav --duration 15 --lang zh
python -I scripts/verify.py outputs/western.wav --lang zh
python -I scripts/soundfonts.py search "ピアノ" --lang ja
python -I scripts/instruments.py search "얼후" --lang ko
```

原始 WAV 的响度检查可能出现 CHECK；视频混音步骤才执行最终的两遍响度归一。

使用自己的参考音频或视频：

```text
python -I scripts/analyze_reference.py reference.wav outputs/reference --seconds 30 --lang zh
python -I scripts/mix.py --video input.mp4 --bgm outputs/western.wav --out outputs/mixed.mp4 --lang zh
```

加 `--vo narration.wav` 或 `--keep-audio`，可让前景声触发 BGM 闪避。混音保持原有默认值：−14 LUFS、−2 dBTP、两遍 `loudnorm`；没有要求时不额外淡出。渲染时加 `--report-levels` 可检查采样声部贡献。

报告语言只影响展示，不改变乐谱或音频处理。JSON/CSV 字段、技术枚举、时间戳与分析数值保持兼容。图表使用本地字体，缺少字形时仅图表标签回退英文，HTML 正文仍为所选语言。[多语种说明](references/languages.md)。

## 测试与边界

```text
python -I -B -m unittest discover -s tests -v
```

完整测试前请安装音源包和外部工具。依赖未分发 DSK 音源的三项测试会明确跳过，不应为了消除跳过而另行下载该音源。

开发流程已在 macOS、原生 Windows 10 x64 / Python 3.10 测试，包括默认 CP936 编码与 PowerShell；Linux 尚未实机验证。测试覆盖谱面解析、路由、DSP 夹具、语言一致性和混音行为，不认证音乐好听程度，仍需实际核听。参考分析不是已确认的原谱或乐器分轨；部分乐器资料有条件或待核，小采样库也不能保证真实连奏与自然的完整音域。

## 许可

项目代码与文档使用 [MIT](LICENSE)，有单独许可声明的文件除外。音源及依赖保留各自许可，包括 CC0 与 GeneralUser GS 自定义许可。再分发前请阅读 [THIRD_PARTY.md](THIRD_PARTY.md)。
