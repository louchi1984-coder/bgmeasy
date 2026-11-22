# 采样音色版渲染（SF2、VCSL、外部音色库）

```bash
python3 -I scripts/render_score_sf2.py score.json bgm-sf2.wav --duration 30 --keep-mid
```

先渲染合成版和采样版，对比后选更合适的；两者用同一份乐谱，时长与小节数一致。预设检索、稳定 ID 和各音源能力见 [soundfonts.md](soundfonts.md)。

## 指定音色

- 乐器→GM 音色是近似映射，打印在输出里；声部里写 `"gm": {"program": 40}` 可覆盖。通用 GM 中二胡、琵琶用 Fiddle / Shamisen 近似。
- 优先从 `soundfonts.py` 检索实际预设，再在声部写 `"preset": "generaluser-gs:8:27"` 等稳定 ID；它会解析为对应 SF2、bank 和 program。13 个轻量 CC0 音源已接入。直接写 `sf2`、`gm.bank/program` 仍支持；不存在的预设会报错，不静默回退。鼓组也可通过 preset 选择，外部鼓库及 bank 0 鼓组均可用。
- 二胡：`ethnic-light/erhu-practice:0:0` 的 CC0 演奏切片已获用户试听认可，但仅映射 A4/C5，样本分别约 1.015/2.05 秒，不是全音域二胡库。旧 `ethnic-light/erhu` 未通过用户试听，保留评估。BISA 两种录音音色获认可，许可版本待核，未安装。

## 电平与各层贡献

- 当前后端含乐器音量补偿；具体持续/衰减预设的平衡仍取决于音区、奏法、力度和织体，不能按名称概括谁一定更响（O02）。**换音色库后要重新检查各小节电平**，层次被抹平就用 `--mute` 逐个静音声部排查。
- 加 `--report-levels` 渲染，会逐层静音相减，打印每层的实际贡献，比最响层低 12 dB 以上的层标出“可能听不清”。SF2 默认按响度校准表折算 gain，可用 `--no-calibrate` 改用固定补偿。数值不替代听感。详见 [loudness-calibration.md](loudness-calibration.md)。

## 音区与技法

写谱后跑 `check_ranges.py`。二胡的揉弦、滑入是真实弯音但同一声部共用参数，竹笛等技法只能用音符模拟，见 [technique-notes.md](technique-notes.md)。

## VCSL 采样器

`scripts/sampler.py`（CC0）：声部里写 `"engine": "sampler:dantranh"`，该声部改用 Dan Tranh（越南十六弦筝，接近古筝）真实采样，按音高选最近采样并变调（±5 半音）、按力度选层。鼓组里的 `taiko` 自动改用 Bass Drum 采样、`gong` 改用 Gong 采样（声部加 `"gm_drums": true` 可改回 GM 音色）。范例：`examples/wuxia-15s-vcsl.score.json`。

## 外部 SF2 音色库

安装 v0.2.0 标准音源包后即可使用 DSK Asian DreamZ。声部写 `"sf2": "DSK-Asian-DreamZ.sf2", "gm": {"program": 4}`，改用指定音色库预设（DSK 原名：0 PIPA、1 PIPA TREM、2 LUAN、3 GUZHEN、4 ERHU、5 BAN-DI、6 Chinese Percussion）。LUAN 与 BAN-DI 的具体乐器身份待核实，不能沿用旧目录“柳琴/竹笛”的翻译作事实。按音色库分开渲染再混合；换库后用 `--mute` 逐个核对贡献。范例：`examples/wuxia-15s-dsk.score.json`。

## 结尾

采样长于乐谱总长时会在结尾淡出，避免硬切；换采样后仍要看有效时长。
