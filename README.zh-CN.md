# bgmeasy

[English](README.md) · **简体中文** · [日本語](README.ja.md) · [한국어](README.ko.md)

### 让 AI agent 为你的画面写配乐。

告诉它场景、情绪和时长，bgmeasy 会引导 agent 规划整首音乐、编写乐谱，再在本地渲染成音频。旋律、节奏、配器和段落都保留在可编辑的乐谱里，方便试听后继续调整。

适合短视频、解说、游戏和动画中的背景音乐制作。搭配具备文件操作与命令执行能力的编程 agent 使用，渲染和参考曲分析无需另接音乐生成服务。

[开始使用](#开始使用) · [音源下载](https://github.com/louchi1984-coder/bgmeasy/releases/latest) · [创作流程](SKILL.md) · [乐谱格式](references/score-format.md)

## 先描述你的场景

你可以这样描述一段音乐：

> 做一段 30 秒温暖、安静的配乐，给两个人重逢的画面用。没有对白，旋律可以突出，结尾自然落下。

也可以在试听后继续修改：

> 主旋律保留，前半段少一点伴奏；后半段逐渐加厚，但不要提前把情绪推满。

bgmeasy 的工作方式是先确定全曲的去向，再安排乐句、和声、共同节奏和声部职能。Agent 负责创作与修改，本地程序负责把乐谱变成声音。

```text
场景与需求 → 全曲设计 → 可编辑乐谱 → 本地渲染 → 试听与修改
```

## 创作、修改与视频混音

| 你要完成的事 | bgmeasy 提供的工作方式 |
|---|---|
| 为一个画面写原创 BGM | 先设计整段音乐，再展开旋律、和声、节奏与配器 |
| 根据试听意见修改 | 回到同一份乐谱调整，保留结构、参数和修改依据 |
| 借鉴参考曲 | 分析音高、节奏、和声与结构线索，辅助重新创作 |
| 给解说或对白配乐 | 在编配中为人声留空间，混音时由前景声触发自动闪避 |
| 把音乐交付到视频 | 输出 WAV，或混入视频并完成响度归一；视频画面直接复制 |

产物包括 agent 编写的 JSON 乐谱和渲染后的 WAV。需要视频时，再进入混音流程。保留乐谱与参数，后续修改、比较和复现都有依据。

## 开始使用

### 1. 下载项目

```text
git clone https://github.com/louchi1984-coder/bgmeasy.git
cd bgmeasy
```

也可以从 GitHub 下载源码 ZIP。

### 2. 准备运行环境

需要 **Python 3.10+、FFmpeg/FFprobe、FluidSynth**。完整采样流程另需约 **169 MB** 的音源包；安装命令见下方展开内容。Windows 使用原生 Python 和 PowerShell 即可，无需 Git Bash 或 WSL。

### 3. 让 agent 读取 skill

向你的编程 agent 提供项目目录，然后发送：

> 读取这个项目的 SKILL.md，检查运行环境。用 bgmeasy 制作一段 30 秒温暖治愈的 BGM，纯音乐、无对白。先规划全曲，再写谱和渲染；保留乐谱，并用中文说明编配思路和输出文件。

拿到音频后，先试听，再把具体修改意见交给 agent。你可以指定时长、用途、情绪、人声需求、乐器偏好和参考音频，不需要自己填写全部编曲参数。

<details>
<summary><strong>展开安装命令与首次运行示例</strong></summary>

先安装 FFmpeg、FFprobe 和 FluidSynth，并将可执行文件加入 PATH。Windows 版 FluidSynth 须保留随包提供的 DLL；macOS 可使用 `brew install ffmpeg fluid-synth`。

**Windows PowerShell**

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -I scripts/download_soundfonts.py
.\.venv\Scripts\python.exe -I scripts/check_deps.py --lang zh
```

**macOS / Linux**

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -I scripts/download_soundfonts.py
.venv/bin/python -I scripts/check_deps.py --lang zh
```

以下命令中的 `python` 请使用上述虚拟环境的解释器。先渲染项目自带的 15 秒示例：

```text
python -c "from pathlib import Path; Path('outputs').mkdir(exist_ok=True)"
python -I scripts/render_score_sf2.py examples/western-15s.score.json outputs/western.wav --duration 15 --lang zh
python -I scripts/verify.py outputs/western.wav --lang zh
```

原始 WAV 的响度检查可能出现 CHECK；视频混音步骤才执行最终的两遍响度归一。

音源包安装器会校验 SHA-256。下载不便时，可从 [Release](https://github.com/louchi1984-coder/bgmeasy/releases/latest) 手动下载音源 ZIP，再使用 `--archive path/to/bgmeasy-soundfonts.zip` 安装。

</details>

## 使用文档

- **选乐器、查演奏能力**：[乐器资料与后端能力](references/instrument-performance.md)、[音源目录](references/soundfonts.md)。现有资料覆盖 96 项乐器演奏资料；发布音源包提供 16 个 SF2 和 312 个目录条目，包含音色变体与采样打击。
- **分析参考曲**：[分析方法与输出](references/reference-analysis.md)。音高、和弦和结构均作为待复核线索，不把估计值当作原谱。
- **混入视频**：使用 `scripts/mix.py`；`--vo` 接入旁白，`--keep-audio` 保留原声。默认两遍响度归一到 −14 LUFS、−2 dBTP。
- **切换语言**：[中英日韩检索与报告](references/languages.md)。使用 `--lang zh|en|ja|ko`；主 skill 和详细参考资料目前仍以中文为主。

## 运行与许可

已在 macOS 和原生 Windows 10 x64 验证，Linux 尚未实机验证。公开版测试共 121 项：118 项通过，3 项因未分发的 DSK 音源而明确跳过。

源码采用 [MIT](LICENSE)，音源遵循各自许可，详见 [THIRD_PARTY.md](THIRD_PARTY.md)。DSK Asian DreamZ 不随项目分发。

音乐效果仍需实际试听。音源是否支持某种奏法、参考分析是否可信，都要结合具体资料和声音判断。
