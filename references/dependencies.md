# 依赖

运行 `python3 -I scripts/check_deps.py` 自动检查；退出码 1 表示必需项缺失。以下版本是本机已验证组合，不是下限保证。

## 必需

| 依赖 | 用途 | 安装（macOS） | 验证过的版本 |
|---|---|---|---|
| ffmpeg + ffprobe | 解码、混音、闪避、响度、封装 | `brew install ffmpeg` | 需含滤镜 `loudnorm` `sidechaincompress` `apad` `afade` `ebur128` |
| python3 ≥ 3.9 | 全部 .py 脚本 | `brew install python` | 3.14.2 |
| numpy | 合成、分析、验收 | `python3 -m pip install numpy` | 2.3.5 |
| scipy | 滤波、混响卷积 | `python3 -m pip install scipy` | 1.17.0 |
| soundfile | 写 WAV | `python3 -m pip install soundfile` | 0.12.1 |

## 可选

| 依赖 | 用途 | 缺失时 |
|---|---|---|
| librosa | `analyze_reference.py`纯算法参考前端；旧`analyze.py` / `imitate.sh`兼容 | 缺少音频参考分析，原创写谱与渲染仍可用；已验证0.11.0 |
| matplotlib | `analyze_reference.py`的静态分析图与本地报告 | 此参考前端需补齐依赖，其他渲染不受影响；已验证3.11.0 |
| FluidSynth | 把 MIDI 用 SF2 音色库渲染成真实采样的音频（`brew install fluid-synth`，已验证 2.6.1） | 只能用内置合成器音色 |
| pedalboard | 专业效果器链：混响、压缩、EQ、限幅，也能加载 VST3（`pip install pedalboard`，已验证 0.9.26） | 用内置简易混响 |
| mido | 读写 MIDI（乐谱转 MIDI 用，`pip install mido`，已验证 1.3.3） | 不能走 FluidSynth 后端 |
| 播放器（afplay 等） | 人工核听 | 不影响生成，但验收必须有人听 |

## 不需要

不需要网络、API key、GPU、采样库、Node/Remotion（Remotion 只在你用 `<Audio>` 内嵌时才相关）。`sox`、`madmom`、`pydub` 都不被使用。

## 每个脚本实际用到什么

- `render_score.py`（主力）与 `compose.py`（旧预设草稿）：numpy, scipy, soundfile
- `analyze.py`：librosa（及其依赖 numpy/scipy/soundfile）；输入是视频或少见格式时调用 ffmpeg 转码
- `analyze_reference.py`：librosa, numpy, scipy, matplotlib, ffmpeg/ffprobe；本地纯算法；pYIN/PLP使用已有librosa，NNLS使用已有SciPy，无新增包、受限插件、模型权重、GPU或API；详见 [reference-analysis.md](reference-analysis.md)
- `compare.py`：numpy
- `mix.py`：Python 标准库、ffmpeg、ffprobe；参数、滤镜和两遍 loudnorm 沿用 mix.sh。旧 mix.sh 保留兼容。
- `check_deps.py`：Python 标准库；检查当前解释器与 PATH 中的工具。旧 check-deps.sh 保留兼容。
- `verify.py`：numpy, ffmpeg
- 所有脚本离线运行；输出只写到你指定的路径（混音入口用系统临时目录并自动清理）。

## Windows 运行条件

已在 Windows 10 x64、Python 3.10.10 的原生环境通过完整测试；采样渲染使用 FluidSynth 2.6.2，混音使用 FFmpeg 7.1（FFprobe 5.1.0）。其他 Windows 版本和 ARM 架构尚未实测。

使用原生 Windows Python 和虚拟环境；把 FFmpeg/FFprobe、FluidSynth 的可执行文件目录加入当前终端 PATH。Python 命令可能是 `python`，文档中的 `python3 -I` 在这种环境下改用 `python -I`，或指定虚拟环境解释器的完整路径。脚本的文本文件与命令行输出使用 UTF-8，不依赖 Windows 默认代码页，也不要求全局切换 UTF-8。

标准流程直接使用原生 Python，不需要 Git Bash、WSL、sed、grep 或 shell 管道：

```text
python -I scripts/check_deps.py
python -I scripts/mix.py --video in.mp4 --bgm bgm.wav --out out.mp4
python -I scripts/verify.py out.mp4
```

Windows agent 选择已装依赖的 Python 解释器；路径含空格时由当前终端正确引用，程序内部使用参数数组调用 FFmpeg，不启动 shell。`mix.py` 支持原 `mix.sh` 的全部参数，滤镜、默认响度和两遍 loudnorm 不变。旧 `mix.sh`、`check-deps.sh` 和兜底用 `imitate.sh` 保留给 Bash 用户；原有 `BGMEASY_PYTHON` 只用于这些旧脚本，Python 入口使用当前解释器。

FluidSynth 官方 Windows 包需保留同目录依赖 DLL；能力探测先查系统库，再查 CLI 旁的 `libfluidsynth-3.dll` 等库文件。无需 `which.exe`。不要只复制 fluidsynth.exe 而遗漏包内 DLL。

## 常见问题

- `sidechaincompress` 缺失：ffmpeg 构建过于精简，换完整构建。
- `pip install` 报 externally-managed-environment：用虚拟环境 `python3 -m venv ~/.venvs/bgm && source ~/.venvs/bgm/bin/activate` 后再装，并用该环境的 python3 运行脚本。
- 分析很慢：新参考前端用`--start/--seconds`选片段，并核对报告实际覆盖范围；旧`analyze.py --max-seconds 120`只取前120秒。

## 已下载的音色库

`soundfonts/GeneralUser-GS.sf2`（32,319,396 字节，读取本机 SF2 头部：274 个非鼓组预设、13 套鼓组；含银行变体）。许可证全文见 `soundfonts/LICENSE-GeneralUser-GS.txt`：个人或商用音乐创作无限制、不要求署名，作者提示无法完全保证每个采样的来源。

下载注意：本机 `raw.githubusercontent.com` 会被重置连接，改用 GitHub API：
`curl -L -H "Accept: application/vnd.github.raw" -o X.sf2 https://api.github.com/repos/<owner>/<repo>/contents/<path>`

未安装的其他音色库（如 Sonatina、Salamander）使用前逐个核对许可证。现有 VCSL 和轻量 FreePats 已安装，见下文。

## FreePats 轻量扩充（CC0）

`soundfonts/freepats-light/` 含13个新增 SF2，覆盖钢琴、干净与爵士电吉他、两种贝斯、竖琴、单簧管、三种氛围音色、定音鼓、世界打击和电子鼓。压缩下载 78,188,905 字节，SF2 文件共127,974,818字节。来源、许可和 SHA-256 见该目录的 manifest.json，原始许可在 licenses/。

索引见 `soundfonts/catalog.json`；用 `python3 -I scripts/soundfonts.py search` 查询、`show <id>` 取配置、`build` 更新索引。银行、外部鼓库和映射规则见 [soundfonts.md](soundfonts.md)。不需要安装额外运行依赖。

## VCSL 采样（CC0）

位置：`soundfonts/vcsl/`（41 个文件，约 44 MB），来源 github.com/sgossner/VCSL，许可证 CC0 1.0（`LICENSE-VCSL.txt`）。内容：Gong 1 的 3 个力度层、Dan Tranh 的 mf/f 两个力度层（32 个单音）、Bass Drum 1/2 的几个单击。由 `scripts/sampler.py` 读取；`map.json` 是自动生成的音高缓存。
注意：VCSL 文件名的八度比标准 MIDI 低一个八度，采样器以自相关估计的音高为准。
没有的：二胡、琵琶、竹笛（VCSL 无这些乐器）。Dizi 的 SF2 来源（Musical Artifacts / Freesound）许可证无法核实，未采用。

## DSK Asian DreamZ（SF2）

位置 `soundfonts/DSK-Asian-DreamZ.sf2`（11.5 MB，2008），来自 rekkerd.org 镜像。预设：PIPA、PIPA TREM、LUAN、GUZHEN、ERHU、BAN-DI、Chinese Percussion；LUAN与BAN-DI的具体身份待核，不沿用旧“柳琴/竹笛”翻译作为事实。DSK 官网声明其虚拟乐器可免费用于私人和商业用途，但没有再分发条款，所以只在本机使用，不要打包分发。rekkerd 下载需带 Referer 头：`curl -e https://rekkerd.org/dsk-soundfonts/ -A 'Mozilla/5.0' -o x.zip https://rekkerd.org/samples/DSK_Asian_DreamZ_sf2.zip`。

中英日韩检索及报告语言仅使用 Python 标准库新增的 Unicode 归一化与本地 JSON 资源，无新增第三方包、模型或下载。图表需要相应本地字体，缺字时回退英文坐标；见 [languages.md](languages.md)。
