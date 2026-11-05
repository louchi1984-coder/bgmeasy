# CC0 二胡轻量候选

上游：[sfzinstruments/aliexpress-erhu](https://github.com/sfzinstruments/aliexpress-erhu/tree/6615047b2fd06126877483e97b8bb4af9d00b080)，固定版本 `6615047b2fd06126877483e97b8bb4af9d00b080`。
许可为 CC0-1.0，允许随开源项目再分发和转换；随附 `LICENSE-erhu.txt` 与原作者说明 `UPSTREAM-erhu.txt`。本目录转换脚本同样按 CC0-1.0 提供。

170 条录音转换成单声道 32 kHz PCM16 SF2，音源 22,458,028 字节；本目录所有文件合计小于 30,000,000 字节。原始下载包约 81.6 MB，仅用于准备，不安装到 skill。

在 skill 根目录查询：

```bash
python3 -I scripts/soundfonts.py search "二胡" --source ethnic-light
python3 -I scripts/instruments.py preset ethnic-light/erhu:0:0
```

预设 0–1：长音两次录音；2–5：短音四次录音；6–7：sul tasto 两次录音。所有 bank 为 0。前六个预设仅映射实际录制的 D4–A5，后两个为 D4–D6。Take 必须显式选择，当前后端不会自动轮替；无真实力度层、无限循环延音或真实连奏转接。

转换只做立体声均值、重采样、PCM16 量化与键位映射；没有音量归一、降噪、循环、自动调音或添加音效。原录音的音准、起音及长度差异保留。原文件八度标签高一组（`a5` 实际约 A4），不是直接使用上游 SFZ 的音高/控制配置。逐样本来源哈希、PCM 哈希、根音及转换说明见 `manifest.json`。

重新构建（使用上述固定版本解压后的源目录，以及现有 numpy/scipy/soundfile）：

```bash
python3 -I soundfonts/ethnic-light/build_erhu.py /path/to/aliexpress-erhu /path/to/new-output
```

SF2 使用现有 FluidSynth 后端，不需要商业插件；已在本机 macOS 测试，Windows/Linux 未实测。**未核听**；采样数量和出声测试不能证明自然感优于旧 DSK。旧 DSK 文件和 ID 保留，历史乐谱不自动换声；其他民族乐器尚未替换。

用户试听记录（2026-11-05）：预设 0 的持续音被反馈为刺耳摩擦声过长，预设 7 仍被反馈为偏乌、发闷、不够清亮。本库尚未通过替代验收，取消升级推荐，仅保留评估用途；其他预设没有据此被判定合格或具有同样问题。代理未核听状态与用户实际试听反馈分别记录。

另已安装 `erhu-practice.sf2`（541,724字节），稳定ID `ethnic-light/erhu-practice:0:0`。它来自irzirgpznj的CC0练习录音，用户对其9.8秒技术试听回复“都可以”。只映射A4和C5，原素材分别约1.015秒、2.05秒，无循环延长或真实连奏，不能当作全音域二胡库。代理仍未核听，用户认可范围只限该试听片段的音色。原公开MP3试听为有损源；来源、固定哈希、切片位置、署名及完整能力限制见 `erhu-practice-provenance.json`、`ATTRIBUTION-erhu-practice.txt`。可用 `python3 -I build_erhu_practice.py /path/to/pinned-preview.mp3 /path/to/new-output` 离线重建；输出目录必须是新位置。整个民族轻量目录仍不超过30MB。

BISA两种试听录音的音色也获用户认可，但许可版本尚待核实，本目录没有安装BISA文件。
