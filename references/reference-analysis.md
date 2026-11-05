# 参考曲：纯算法分析前端

用户约定 G07：实际读取参考音频，用传统信号处理提取可复核证据，不接音频大模型、神经转谱、神经分离、权重下载或外部API。分析用于之后的全曲规划，不改变标准创作渲染流程。

## 入口与输出

```bash
python3 -I scripts/analyze_reference.py reference.wav work/reference-study \
  --start 0 --seconds 60
```

输入须是已取得的本地音频/视频。只给曲名、描述或不可读取链接时，不能声称已分析原曲。默认分析从0秒起最多120秒，可用`--seconds`选择其他长度；JSON记录原文件路径、哈希、总时长、实际分析范围及未分析尾部。没有分析到的部分不能当作全曲结论。输出目录中已有报告会拒绝覆盖。

可选参数只补充已知信息：

```bash
python3 -I scripts/analyze_reference.py reference.wav work/reference-study-2 \
  --seconds 30 --melody-source aligned-solo.wav --bpm 50 --meter 6/8
```

- `--melody-source`：已有主奏/独奏文件，须与原曲从0秒同步；同样应用`--start`选区。不执行模型分离，不自动验证它是否真是单声部。
- `--bpm`：分析脉冲BPM，不默认为四分音符。6/8可以指定附点四分脉冲；缺失时输出速度候选及半速/倍速歧义。
- `--meter`：已知拍号，只记录用户提供的信息。不自动推断拍号或小节第一拍，不据此强制生成四拍和弦窗。

输出为同一证据包：

| 文件 | 用途 |
|---|---|
| `reference.json` | 全量候选、时间位置、来源、方法与不确定性，供agent读取 |
| `melody-notes.csv` | 音符候选的起止时间、音高、周期性与稳定度 |
| `pitch-contour.csv` | 分帧基频候选；未通过信号门限的帧留空 |
| `voice-notes.csv` | 同时发声的音符与暂定单音线ID、左右能量线索；不是乐器分轨 |
| `analysis.png` | 波形/起音、主线与多音高候选、色度、局部变化和自相似图 |
| `report.html` | 本地可读报告，链接图和数据，无外部资源或服务 |

时间戳均对应原文件时间，含`--start`偏移；分离文件的时间基准须由提供者保证。

## 各类结果怎么读

**旋律候选**：已有主奏文件用librosa的pYIN（YIN候选与Viterbi序列解码）；混音先在C2–C7上用固定谐波字典NNLS估计同时发声的音高，再在C3–C7内用连续性路径选择一条主线候选。不下载预训练参数；pYIN的概率分布与路径代价是算法设置，不是训练好的音频模型。独奏连续频率不按推测调性吸附。短于60ms的稳定段不生成主线音符。

当至少两个较强且稳定的音高候选并存时，混音路径对较少变化的持续和弦音施加软权重，以降低被静态伴奏占据的机会；这是**项目启发式**，也可能压低真正的持续主奏。强伴奏、同音齐奏与声部交叉仍可能选错；`melody_identity`始终为`unverified`。保留其他音高候选，不能把单一路径当原谱。混音轨迹仍是半音格，`pitch_spread_cents`留空，不能据此测揉弦或精细音准。

**多音高与声部候选**：字典由C2–C7的数学谐波模板构造，使用现有SciPy的`nnls`解非负最小二乘。统一加权数据和字典，约23ms求解一次并插值回原时间格；估计整体调音偏移。门限用于排除低能量和宽带噪声，短于90ms的音符不进入此列表。没有神经转谱、学习乐器字典或外部插件。

`voices.notes`保留同时发声的音符、相对活跃程度和`stereo_balance`（左负、右正；单声道为null）。按音高距离、时间衔接和可用左右能量线索贪心连接成`candidate_01`等暂定单音线；这些ID可能断裂、串线，不等于乐器身份或乐器数量，不生成分离后的音频。弱音、非谐和音、快速装饰音、重复起音、同音叠奏和交叉都可能遗漏或混淆。

CLI解码为立体声工作信号，保留左右通道用于谐波频带能量比较；同时在`source.audio_channels`记录原文件通道数。通常用左右平均分析，显著反相抵消时改用较强通道并在`spatial.analysis_view`注明。此回退防止误报静音，不是完整的相位恢复或声源分离；多声道文件转为立体声工作信号，未保留所有环绕通道。

**节奏候选**：按低频20–200Hz、中频200–2000Hz、高频2000Hz以上提取正向频谱变化，输出各频带起音及合成起音证据。全局自相关速度候选和动态规划脉冲网格继续保留；增加PLP局部脉冲及约4秒窗口的脉冲速度摘要，供变速片段交叉复核。`--bpm`仍指定全局网格所用脉冲；PLP是独立候选，不会偷偷覆盖已知BPM。半速/倍速歧义、重音、拍号与小节第一拍均不自动认证；静音/弱周期可返回`insufficient_evidence`。

**和声候选**：由NNLS音高活跃程度汇总十二音色度与独立低音色度，约0.5秒窗匹配人工和弦模板；HPSS的谐波成分提供能量门限。模板包含大小三和弦、减三、sus2/sus4、属七、大小七与半减七。每窗保留原始前三候选及间距，额外输出固定转换代价下的`smoothed_label_candidate`；未知窗口中断平滑，不将未知填成和弦。`bass_chroma_windows`是低区音级证据，不认证低音线、转位或复杂扩展和弦；调性仍是固定大小调分布相关候选。不假定每小节一和弦。

**结构候选**：色度与MFCC音色特征的自相似、局部对比变化点，以及时间形状相似的片段。段数由观测决定，不强制切五段。变化可能来自换和弦、换音色、余音或编配；相似可能只代表相同和弦/质地。边界不是已确认乐句，重复片段不是已确认主题再现；不自动命名主歌、副歌或高潮。

## 不确定性与创作衔接

`periodicity_score`、`spectral_support_score`、谐波相对显著度、模板余弦相似度、调性相关系数、变化对比与片段相似度都是**未经正确率校准的信号线索**，不能读成“识别正确的概率”。各部分保留候选、歧义、未知和限制，整份报告为`not_listened`。JSON的`schema_version`为2，旧主线CSV字段保留，增加声部候选CSV及JSON字段。高分不认证主旋律身份、情绪、乐器音色或作品质量。数值阈值属于本机分析参数，不是乐理质量门槛。

读报告后，结合原片段的已知资料整理时间轴：哪些材料可能重复、节奏怎样组织、和声怎样变动、哪些位置值得复核。每项判断对应具体时间与数据，把观测、算法推测和agent归纳分开；无法确定的部分保留待核。然后进入SKILL的2a，借鉴参考的组织关系设计原创作品，不复制受保护的具体旋律，也不把候选转谱直接拿来交付。

这是感知证据前端，不是自动“听懂”或“好听”判断器。`analyze.py`继续为旧`imitate.sh`提供粗略profile兼容；其四拍和弦窗、强制速度范围和预设草稿不是此新入口的默认创作路径。

## 依赖、算法依据与验证

使用已有ffmpeg/ffprobe、NumPy、SciPy、librosa和Matplotlib，全部离线运行，新增Python包为0。自编DSP在`scripts/reference_dsp.py`。新增调用来自librosa的ISC授权实现和SciPy的BSD授权实现；不集成MELODIA、Essentia、Chordino或外部NMF工具箱。分发既有库时保留各自版权与许可声明，无需为本次新增调用购买或单独申请授权。HPSS按时间/频率中值滤波分出谐波与打击成分，不是按具体乐器进行神经分离。只写分析输出，不修改原音频、乐谱或渲染结果。

字典的谐波衰减、加权频谱、活跃门限、变化软权重、路径代价与声部贪心连接均为项目固定启发式；不是经过识别正确率校准的参数，也不构成通用主旋律或乐器识别保证。ffmpeg/ffprobe仅允许本地文件与管道协议，避免分析本地播放列表时隐式访问网络。

- [librosa pYIN](https://librosa.org/doc/0.11.0/generated/librosa.pyin.html)：独奏基频候选及序列解码，不认证混音主旋律。
- [SciPy NNLS](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.nnls.html)：非负最小二乘求解；具体音频字典与启发式为项目自编。
- [librosa PLP](https://librosa.org/doc/0.11.0/generated/librosa.beat.plp.html)：局部脉冲估计，可辅助速度变化分析。
- [librosa ISC许可](https://github.com/librosa/librosa/blob/main/LICENSE.md)、[SciPy BSD许可](https://github.com/scipy/scipy/blob/main/LICENSE.txt)：本次使用的既有库，未加入外部受限插件实现。
- [librosa YIN](https://librosa.org/doc/0.11.0/generated/librosa.yin.html)：基于自相关差分的基频估计；不是多乐器转谱或主旋律识别保证。
- [起音检测](https://librosa.org/doc/0.11.0/generated/librosa.onset.onset_detect.html)：起音强度包络的峰值位置估计。
- [色度](https://librosa.org/doc/0.11.0/generated/librosa.feature.chroma_stft.html)：频谱的音高类别能量表示；和弦模板匹配及歧义阈值为本项目实现。
- [HPSS](https://librosa.org/doc/0.11.0/generated/librosa.decompose.hpss.html)：谐波/打击成分分解。
- [自相似](https://librosa.org/doc/0.11.0/generated/librosa.segment.recurrence_matrix.html)：特征相似关系的解释；本脚本的局部对比、重复片段筛选和权重为项目启发式，不冒充乐句识别标准。

运行已知信号与CLI回归：

```bash
python3 -I -B tests/test_reference_analysis.py
python3 -I -B tests/test_reference_accuracy.py
```

测试覆盖已知混音主线帧准确度、同时音高精确率/召回率、重复音起始误差、左右声像方向、反相抵消、pYIN音准误差、PLP变速节拍F1，以及原有的和弦候选、结构变化、静音/噪声、时间偏移、CLI导出及源文件不变。指标阈值仅用于这些已知合成回归场景，不是任意参考音乐的正确率或创作硬规则。通过测试只说明这些已知场景与工程路径有效，不代表对所有混音、民族乐器或复杂和声具有已知准确率。

报告可用 `--lang zh|en|ja|ko` 切换标题、说明、表头和不确定性提示。JSON/CSV协议与算法保持不变；字体回退及原文保留范围见 [languages.md](languages.md)。
