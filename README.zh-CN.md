# bgmeasy

[English](README.md) · **简体中文** · [日本語](README.ja.md) · [한국어](README.ko.md)

### 让 AI agent 为你的画面写配乐。

描述画面，或交给 agent 一段参考音频、视频或自己的哼唱。你先听三个 15 秒小样，选中一个，再由 agent 写成完整配乐，在本地渲染。

适合短视频、解说、游戏和动画中的背景音乐制作。搭配具备文件操作与命令执行能力的编程 agent 使用，渲染和参考曲分析无需另接音乐生成服务。

[开始使用](#开始使用) · [v0.2.0 音源包](https://github.com/louchi1984-coder/bgmeasy/releases/tag/v0.2.0) · [创作流程](SKILL.md) · [乐谱格式](references/score-format.md)

## 从哪里开始

> 给婚礼入场写一段温暖、庄重的进行曲。第 12 秒两个人会合，希望音乐在那一刻明亮起来。

一句画面或听感就够了。有需要对齐的动作，可以像上面这样给出时间点。用文字描述时，可以直接指定模式，也可以听 agent 介绍三种模式后再选。

| 模式 | 你提供什么 | agent 怎么写 |
|---|---|---|
| **直接创作** | 一句用途、画面或情绪 | 从描述出发，用不同的拍感、和声或旋律写出几个方向。 |
| **参考模式** | 想要的感觉，也可以点一首曲名 | 主动找几首相关作品，读具体谱段，借鉴低音怎样推进、乐句怎样应答等手法，再写原创主题。 |
| **分析模式** | 可读取的音频、视频或哼唱录音 | 给了文件就直接进入分析。参考录音用于提取节奏、和声和结构线索；如果是你哼的旋律，就保留它的音高和节奏，试听不同编配。 |

只有曲名或链接打不开时，agent 会按参考模式查找作品。三种模式都会交付 **3 个各 15 秒的可播放小样**，每段配一句能听出来的区别。试听时可以比较谁在带拍、和弦怎样推进、主奏留白时谁来接。三个都不合适，可以说出原因，再听三个新小样。

选好方向后，agent 才补问**成品时长和配器丰富程度**，之前给过的要求会沿用。你可以像这样一次答完。

> 选 2，做成 60 秒。保留这个步速，后半段加一条能听清的大提琴答句。

## 创作、修改与视频混音

| 你要完成的事 | bgmeasy 提供的工作方式 |
|---|---|
| 为一个画面写原创 BGM | 试听选样后，围绕选定的旋律、和声、节奏与配器展开全曲 |
| 根据试听意见修改 | 回到同一份乐谱调整，保留结构、参数和修改依据 |
| 从自己的哼唱发展成曲 | 保留哼唱的旋律，先试听几种伴奏，再把选定的编配展开 |
| 给解说或对白配乐 | 在编配中为人声留空间，混音时由前景声触发自动闪避 |
| 把音乐交付到视频 | 输出 WAV，或混入视频并完成响度归一；视频画面直接复制 |

原创成品默认交付供试听的 WAV、可编辑的 MIDI 和用于渲染的 JSON 乐谱。独立采样声部和音频效果保存在 WAV 中。需要视频时，可把成品混入视频。

## 开始使用

### 1. 下载项目

```text
git clone https://github.com/louchi1984-coder/bgmeasy.git
cd bgmeasy
```

也可以从 GitHub 下载源码 ZIP。

### 2. 准备运行环境

需要 **Python 3.10+、FFmpeg/FFprobe、FluidSynth**。完整采样流程另需约 **179 MB** 的音源包；安装命令见下方展开内容。Windows 使用原生 Python 和 PowerShell 即可，无需 Git Bash 或 WSL。

### 3. 让 agent 读取 skill

向你的编程 agent 提供项目目录，然后发送：

> 读取这个项目的 SKILL.md，检查运行环境。给两个人重逢的画面写一段温暖的纯音乐，没有对白。选直接创作，先给我听三个小样，用中文说说各自的区别。

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

音源包安装器会校验 SHA-256。下载不便时，可从 [Release](https://github.com/louchi1984-coder/bgmeasy/releases/tag/v0.2.0) 手动下载音源 ZIP，再使用 `--archive path/to/bgmeasy-soundfonts.zip` 安装。

</details>

## 使用文档

- **选乐器、查演奏能力**：[乐器资料与后端能力](references/instrument-performance.md)、[音源目录](references/soundfonts.md)。现有资料覆盖 96 项乐器演奏资料；发布音源包提供 17 个 SF2 和 319 个目录条目，包含音色变体与采样打击。
- **找谱或分析录音**：[参考作品检索与音频分析](references/reference-analysis.md)。报告中的音高、和弦与结构是供复核的线索。
- **从哼唱写配乐**：[哼唱转谱与编配](references/hum-workflow.md)。
- **混入视频**：使用 `scripts/mix.py`；`--vo` 接入旁白，`--keep-audio` 保留原声。默认两遍响度归一到 −14 LUFS、−2 dBTP。
- **切换语言**：[中英日韩检索与报告](references/languages.md)。使用 `--lang zh|en|ja|ko`；主 skill 和详细参考资料目前仍以中文为主。

## 运行与许可

v0.2.0 在 macOS 和 Python 3.14.2 上使用标准音源包运行了全部 128 项测试，含 DSK 相关测试，全部通过，零跳过。此版本尚待 Windows 实机复测。

提交 `124d698` 在 macOS、Python 3.14.2 下使用 v0.1.0 音源包运行了 127 项测试，124 项通过，3 项因当时的音源包未含 DSK 而跳过。

v0.1.0 公开版在 macOS 和原生 Windows 10 x64 上各运行了 121 项测试，118 项通过，3 项因需单独安装 DSK 音源而跳过。Linux 尚未实机验证。

源码采用 [MIT](LICENSE)，音源遵循各自许可，详见 [THIRD_PARTY.md](THIRD_PARTY.md)。v0.2.0 标准音源包内含 DSK Asian DreamZ 原版 SF2 和作者 README。也可单独下载[上游完整 ZIP](https://github.com/louchi1984-coder/bgmeasy/releases/download/v0.2.0/DSK_Asian_DreamZ_sf2.zip)。复制与分发条件见 [DSK Music 许可](https://www.dskmusic.com/license-info/)，音源出处见[发布公告](https://rekkerd.org/dsk-music-releases-dsk-asian-dreamz-vol-1/)。

音乐效果仍需实际试听。音源是否支持某种奏法、参考分析是否可信，都要结合具体资料和声音判断。
