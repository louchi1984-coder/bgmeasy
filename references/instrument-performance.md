# 演奏资料与实际音源能力

证据索引：[theory-evidence.md](theory-evidence.md) I01–I03。以下查询/记录步骤为**项目工作法**；后台支持为**本机实现**；外部演奏知识须逐字段看证据，不能把两者混为已核实的自然感。

用于原创、改编、换配器与选择主奏。先查本页流程，再按拟用的乐器/预设检索；不要一次把整个JSON载入上下文。

## 写谱前：从乐器动作落实到当前后端

1. 按音乐需求提出候选，查询演奏资料卡。核对发声方式、音区、连断、重音、收音、呼吸/换弓/拨弦等动作。资料中的奏法是乐器可能的演奏方式，不表示当前音源已经实现。
2. 查询具体preset的能力卡，核对实际身份、采样映射、力度区域、循环、当前后端读哪些参数。需要特殊奏法时进一步阅读卡内来源和该音源手册；身份不明的预设保留原名。
3. 确定各声部怎样演奏这一句，再写作品音符。用用户指定的写法、普通奏法、可用预设或明确说明的近似来实现；不要以“真实乐器能做到”为由声称简单SF2已实现。
4. 对关键主奏先制作独奏短句，检查起音、连接、重复、力度和释放；在可实际核听时核听。无法核听就保留“未核听”，照常交付有数值检查的草稿，不能把状态改成听感合格。用户明确要合成/非写实效果时按其目标，不强制模拟原声。

例：笛类要说明连吐、气息和收音；铜管要说明重音、连断与音区；弦乐要区分弓法；弹拨要组织起音、余音和止音。这些是检查问题，不是禁止某件乐器主奏或跨风格使用的规则。没有适用于全部乐器的固定最快速度、最大句长或“主角音区”。

## 音域资料的型号条件

原音域表21个low条目已作[逐项来源核查](instrument-range-evidence.md)：15项有附带条件的数值实例，5项需分类/定弦，越南十六弦筝绝对端点仍待核。旧舒适区和统一极限不因此获认证。写谱前可用 `python3 -I scripts/check_ranges.py --list-variants dizi` 查询；确认适用后在声部写如 `"range_variant": "dizi.hkco-qudi-c"`。这是作者声明的演奏音域参照，渲染器忽略该字段，不会让GM Flute变成竹笛。实际预设身份与采样映射仍按本页原查询检查。未指定型号、定弦或找不到匹配证据时保留条件提示，不用旧猜测数值判定不合常理。

## 查询命令

```bash
python3 -I scripts/instruments.py search "笛"
python3 -I scripts/instruments.py instrument flute
python3 -I scripts/instruments.py preset generaluser-gs:0:73
python3 -I scripts/instruments.py preset dsk-asian-dreamz:0:0 --zones
```

- `search` 同时查中文/英文资料卡与实际预设。变体逐一关联；合成器和拟音预设有独立类别，不套原声乐器限制。
- `instrument` 返回乐器发声、奏法、写作提示、附条件的实音参考范围、来源和证据层级。
- `preset` 现场读取实际SF2头部，返回对应资料、后端支持、结构统计及匹配的技术测试。`--zones` 展开每个区域的键位、力度、根音、循环与样本长度。
- 基础合成器的 `inst` 与SF2预设是两件事：例如 `inst=dizi` 不会把GeneralUser Flute变成真实中国竹笛。能力卡显示的是给定inst上下文，谱面检查按实际声部配置核对。

## 覆盖与证据

- `instruments.json`：演奏资料、家族共性、逐program及实际变体关联、基础合成类型和鼓件别名。`claim_review` 才是逐字段核查：`source_supported_scoped`只支持所列字段与条件，`project_synthesis`是项目归纳，`pending_direct_evidence`为待核。`evidence_level=partial_field_review`只表示部分字段有证据，`pending_direct_evidence`表示缺直接字段证据，`project_or_local_category`为项目/本机分类；均须看逐字段条件。`identity_unverified`仍表示身份待核实；旧关联类型另存`source_association_type`，不作为认证。
- `instrument-sources.json`：一手资料入口、日期、`review.status/sections/limitations`。日期不证明内容已读，抓取成功不证明主张成立；已读小节、仅目录与未读取分别标明。资料以简要摘要和链接保存，没有整本复制教材。卡片的写作建议是项目应用判断，允许根据演奏者、型号、传统、风格修正。
- `soundfonts/capabilities.json`：所有已安装预设的结构快照及文件哈希。键盘映射范围不等于真实乐器音域；同一力度区也可能有滤波/音量调制，不能一概说力度只改变音量。
- `soundfonts/capability-probes.json`：技术出声测试。标记`rendered`只代表指定键位的有限数值检查成功，不代表全音域、全部奏法、真实感或主奏适合性已验证。所有听感状态初始为`not_listened`。
- 新增音源需要登记资料关联，再重建能力快照；不允许悄悄落到泛化“民族乐器”类别。某些型号/定弦依赖的音域没有可靠数值时保留空值并按需查来源，不能编造上下界。

来源包含[VSL Academy](https://www.vsl.co.at/academy/)、[Philharmonia](https://philharmonia.co.uk/resources/instruments/)、[Yamaha](https://www.yamaha.com/en/musical_instrument_guide/)、[香港中乐团](https://www.hkco.org/en/Instrument-Rd/Chinese-Instruments/Wind-Instruments.html)和[TOR](https://timbreandorchestration.org/instruments)。每张卡标出直接来源与仅作背景的入口；未读专项段落的字段保持待核，不用总目录或相邻乐器资料替代证据。

## 当前后端的重要区别

| 项目 | 内置合成器 | SF2 / VCSL后端 |
|---|---|---|
| 乐器身份 | `inst`控制基础合成近似 | 实际`preset/sf2/gm/engine`决定声音 |
| `params.attack/release/decay`等 | 仅该合成函数读取的参数生效 | SF2不读取这些参数，不会因此换成短弓/不同拨弦 |
| 滑音与揉弦 | 仅部分合成音色有近似 | 只有`inst=erhu`显式`bend/vibrato`的单声部弯音；不是连奏/换弓采样 |
| 延音踏板、任意CC曲线、keyswitch | 无通用实现 | 当前乐谱API没有发送这些控制 |
| 和弦分解 | `params.strum`错开各音起点 | 同样支持起点错开；不等于录制的真实扫弦奏法 |
| 音量/表情 | 合成信号增益 | SF2使用MIDI CC7及乐器补偿，段落dynamics使用CC11；VCSL将dynamics乘到传入velocity，其幅度响应依分支；不能一律当线性音频gain |
| 声部混响/延迟 | 有声部混响总线与delay | SF2发CC91并有固定母带混响，不读取delay/delay_beats/global reverb_level |

SF2内部有其自身包络、调制和录制奏法；不能因乐谱API没提供某个控制，便断言音源内部一定没有该声音。也不能因样本名、预设名含Legato/Tremolo/RR便宣称当前播放方式已正确调用。

VCSL当前实现也有边界：Dan Tranh是越南筝，移调被夹在最近样本±5半音，过远请求不能保证目标音高；它不按短note精确止音。大鼓按力度选文件但不再乘同一力度缩放；锣当前只选mf/f，目录中的p未被选择。文件名中的rr1不代表选择器会轮替。VCSL声部不发MIDI CC，声部reverb未被读取，声音仍经过固定母带混响。

## 在设计里留演奏记录

每个拟用声部记录乐器身份、目标奏法/乐句、具体实现与限制。可用：

```json
"performance": {
  "flute_theme": {
    "instrument": "flute",
    "technique": "以连句为主，句末释放，短音用清楚吐音",
    "phrase": "两小节一问一答，呼吸留在句尾",
    "implementation": "generaluser-gs:0:73；MIDI时值/力度近似，没有真实吐音切换",
    "limitations": "不声称支持真实连奏与气息曲线",
    "audition": "not_listened"
  }
}
```

已有乐谱仍兼容；这些字段是设计记录，不会自动控制渲染。新作在完整写谱前查资料、记录演奏意图，写完再检查：

```bash
python3 -I scripts/instruments.py score score.json --backend sf2
```

检查实际预设与目标身份、缺失演奏记录、当前后端忽略的参数、未映射键位/力度以及采样器移调夹限。提示供人工修谱，不依据音色名字判定情绪、风格或好听。最后仍按原装渲染和验收流程执行。

## 技术短句与维护

```bash
python3 -I scripts/instruments.py audition generaluser-gs:0:73 --out work/flute-check.wav
python3 -I scripts/instruments.py build
python3 -I scripts/instruments.py probe-all
```

`audition`只生成中性技术探针（连接、短音、重复、力度），并调用未修改的标准采样渲染器，不冒充真实演奏示范。作品主奏的独奏试句仍应按实际乐句设计。`build`更新结构快照；`probe-all`测试全部预设及基础合成/鼓件的有限出声能力，保存测试文件哈希。音源或后端改变后重新检查；不能继承旧音源的听感结论。
