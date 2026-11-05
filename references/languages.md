# 检索与报告语言

支持 `zh`（中文）、`en`（English）、`ja`（日本語）、`ko`（한국어）。标准入口的 `--lang` 默认 `zh`，不依赖系统区域设置。Agent 按用户指定的语言生成交付说明并选择报告参数；没有明确指定时可按对话语言选这四种之一，其他语言的脚本报告暂用用户可接受的已支持语言。此选项不改变乐谱、音频算法或渲染参数。

## 乐器检索

```text
python3 -I scripts/soundfonts.py search "ピアノ" --lang ja
python3 -I scripts/soundfonts.py search "피아노" --json --lang ko
python3 -I scripts/instruments.py search "violin" --lang en
python3 -I scripts/soundfonts.py show generaluser-gs:0:0 --lang en
```

查询语言与输出语言可以不同；命令有子命令时 `--lang` 可放在子命令前或后。`instrument-languages.json` 为现有96个演奏资料 profile 提供四种显示名和检索别名；也包括吉他、鼓组、弦乐等类别词。NFKC处理全角、半角片假名和分解韩文，再做大小写折叠。复合查询保持各词同时匹配，保留 `--kind` / `--source` 过滤。

稳定 preset ID、bank、program、原始 name 与 track 配置不翻译；JSON另提供 `instrument_name`。显示名是现有资料卡的译名，不认证音源真实身份或自然感。阮与身份未核实的 LUAN、中国古筝与日本箏、越南 Đàn tranh 保持独立映射；没有相应音源时不会凭译名生成新预设。宽泛类别词可以覆盖多种相关预设，需要精确定位时使用 profile 或 preset ID。

## 标准报告入口

以下 Python 入口支持 `--lang zh|en|ja|ko`（Windows 使用已装依赖的 `python -I` 或解释器完整路径替代 python3）：

- `analyze_reference.py`：HTML报告标题、说明、表头、状态与不确定性提示；图表标签优先使用本地相应字体，缺少所需字形时图表回退英文并在HTML说明，正文保留所选语言。不下载字体。
- `verify.py`：响度、真峰值、有效时长、结尾电平、削波等数值报告的标签与解释。
- `render_score.py` / `render_score_sf2.py`：渲染摘要、自检及 `--report-levels` 贡献报告。逐层子渲染继承报告语言。
- `check_melody.py` / `check_ranges.py`：谱面关系和音域检查的生成标签、提示；不增加或修改检查规则。
- `check_deps.py` / `mix.py`：依赖检查及混音提示。
- `soundfonts.py` / `instruments.py`：四语检索和 `instrument_name` 展示；资料卡保留原始字段。

```text
python3 -I scripts/analyze_reference.py ref.wav work/report-ja --seconds 30 --lang ja
python3 -I scripts/render_score_sf2.py score.json bgm.wav --duration 30 --report-levels --lang ko
python3 -I scripts/verify.py bgm.wav --lang en
```

JSON/CSV字段名、技术枚举、音名、数值、时间戳、置信状态维持机器协议；参考分析JSON/CSV不因显示语言而变。HTML提供翻译视图，不回写分析数据。曲名、路径、声部名、用户注释、音源原名、原始演奏资料与引文保留原文，不能因为换语言删除“候选”“未核实”“未核听”等限制。第三方程序的原始错误信息也保留原文。

现阶段没有把整套SKILL.md、演奏资料正文、全部命令帮助或旧 `analyze.py` / `compose.py` / `imitate.sh` 的输出翻译成四语。旧 Bash 入口保留原行为；标准流程使用上面的原生 Python 入口。
