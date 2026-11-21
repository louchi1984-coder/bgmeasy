# 响度校准表与各层贡献报告

## 它们是什么
- `soundfonts/loudness.json`：307 个预设相对 GeneralUser GS 三角钢琴的响度偏差（dB）。公开音源包覆盖其中 300 个；另外 7 个对应可选的 DSK 音色。测量条件：CC7=127、力度 90、预设自身音域内单音、取 1 秒 RMS 的中位数。测量脚本和原始数据在 `references/loudness-calibration/`（`measure2.py`、`preset_loudness_v2.csv`），脚本只读、不改 skill。
- `render_score_sf2.py` **默认按响度校准表折算 gain**。`--calibrate` 可显式开启，`--no-calibrate` 使用固定补偿。逐层贡献报告的子渲染继承同一设置。
- `render_score_sf2.py --report-levels`：渲染后逐层静音相减，打印每层对整体的实际贡献（未做峰值归一化），比最响层低 12 dB 以上标“可能听不清”。

## 怎么用
```bash
python3 -I scripts/render_score_sf2.py score.json bgm.wav --duration 30 --report-levels
```
写谱后用它查哪一层实际偏小，再回头改 gain 或力度。

## 已知局限（务必读）
- 表只描述“单音 1 秒内”的响度。衰减快的音色（钢琴、吉他、古筝、竖琴、贝斯）在真实乐句里的贡献比表里低；一个数字覆盖不了。
- 此前用 6 个音色以相同 gain 弹同一段，校准表与固定补偿的最大层间差分别为 3.5 dB 和 2.8 dB。具体作品仍需检查声部平衡。
- 贡献用平均能量（RMS）算，音头强的层听感比数值突出，稀疏层和鼓的数值偏低。数值不替代听感。
- SF2 的 CC7 按**补偿后的有效 gain**换算：`CC7 = int(min(127, 有效gain * 127))`。有效 gain 为 1.0 时对应 CC7=127，0.5 对应 63，超过 1.0 才被截断。
  - 谱面 `gain` 会先乘补偿系数。根据实际使用的 SF2 在 `soundfonts/` 内的相对路径、bank 和 program 查表（例如 `freepats-light/piano-kw:0:0`）；命中时默认使用表中系数。关闭校准或缺少对应记录时，按固定补偿折算。是否触及上限取决于有效 gain。
  - 使用固定补偿时，keys 系数为 1，谱面 gain 0.5→CC7=63、1→127。pad 系数为 0.5，谱面 gain 1→63、1.5→95、2→127。
  - VCSL 采样器声部（古筝 Dan Tranh、大鼓、锣）不受 CC7 上限限制，实测大鼓需要 gain 约 3。
- 没有覆盖 VCSL 采样器与未登记的预设；没有测不同力度。
