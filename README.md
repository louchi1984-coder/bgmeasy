# bgmeasy

**English** · [简体中文](README.zh-CN.md) · [日本語](README.ja.md) · [한국어](README.ko.md)

### Compose background music with your coding agent.

Describe the scene, mood and duration. bgmeasy guides your agent through planning the piece, writing an editable score and rendering the audio locally. Melody, rhythm, instrumentation and structure stay in the score, ready for the next round of changes.

Built for background music in short videos, narrated content, games and animation. Use it with a coding agent that can read files and run commands. Rendering and reference analysis need no separate music-generation service.

[Get started](#get-started) · [Sound pack](https://github.com/louchi1984-coder/bgmeasy/releases/latest) · [Composition workflow (中文)](SKILL.md) · [Score format (中文)](references/score-format.md)

## Start with the scene

A brief can be as simple as:

> Write 30 seconds of warm, quiet music for two people meeting again. There is no dialogue, so the melody can stand out. Give it a settled ending.

After listening, keep shaping the same piece:

> Keep the main theme. Thin out the accompaniment in the first half, then gradually build the second half without reaching full intensity too early.

The workflow starts with a destination for the whole piece, then develops its phrases, harmony, shared rhythm and instrumental roles. The agent composes and revises; local programs turn the score into sound.

```text
Scene and brief → Whole-piece plan → Editable score → Local render → Listen and revise
```

## Compose, revise, and mix with video

| Your task | How bgmeasy helps |
|---|---|
| Score a scene | Plan the complete cue before developing melody, harmony, rhythm and orchestration |
| Revise after listening | Adjust the same score while keeping the structure, settings and reasons for changes |
| Work from a reference | Examine pitch, rhythm, harmony and structural clues to inform a new composition |
| Support narration or dialogue | Leave room in the arrangement, then use foreground-driven ducking during mixing |
| Deliver music with a video | Render a WAV, or mix it into video with loudness normalization and video stream copy |

The working files are an agent-authored JSON score and a rendered WAV. Video mixing is a separate step when needed. Keeping the score and settings makes later revisions, comparisons and reproduction easier.

## Get started

### 1. Download the project

```text
git clone https://github.com/louchi1984-coder/bgmeasy.git
cd bgmeasy
```

You can also download the source ZIP from GitHub.

### 2. Prepare the environment

You need **Python 3.10+, FFmpeg/FFprobe and FluidSynth**. The full sampled workflow also uses a **169 MB** sound pack. Expand the commands below for setup. Windows runs with native Python and PowerShell; Git Bash and WSL are not required.

### 3. Give the skill to your agent

Point your coding agent at the project directory and ask:

> Read this project's SKILL.md and check the environment. Use bgmeasy to make 30 seconds of warm, calming instrumental background music, with no dialogue. Plan the whole piece before writing and rendering the score. Keep the score and explain the arrangement and output files in English.

Listen to the result, then give the agent specific changes. You can describe duration, purpose, mood, dialogue, instrument preferences and reference audio without filling in every arrangement parameter yourself.

<details>
<summary><strong>Installation commands and a first render</strong></summary>

Install FFmpeg, FFprobe and FluidSynth on PATH first. Keep the DLLs supplied with Windows FluidSynth beside its executable. On macOS, `brew install ffmpeg fluid-synth` is available.

**Windows PowerShell**

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -I scripts/download_soundfonts.py
.\.venv\Scripts\python.exe -I scripts/check_deps.py --lang en
```

**macOS / Linux**

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -I scripts/download_soundfonts.py
.venv/bin/python -I scripts/check_deps.py --lang en
```

For the following commands, use that virtual environment's interpreter in place of `python`. Try the included 15-second example:

```text
python -c "from pathlib import Path; Path('outputs').mkdir(exist_ok=True)"
python -I scripts/render_score_sf2.py examples/western-15s.score.json outputs/western.wav --duration 15 --lang en
python -I scripts/verify.py outputs/western.wav --lang en
```

The raw WAV check may flag loudness. Final two-pass loudness normalization happens during video mixing.

The sound pack installer verifies SHA-256. If direct downloading is inconvenient, get the ZIP from [Releases](https://github.com/louchi1984-coder/bgmeasy/releases/latest) and install it with `--archive path/to/bgmeasy-soundfonts.zip`.

</details>

## Documentation

- **Choose instruments and check their capabilities:** [performance and backend guide](references/instrument-performance.md), [sound catalog](references/soundfonts.md). The knowledge base covers 96 instrument profiles; the release sound pack provides 16 SF2 files and 312 catalog entries, including variants and sampled percussion.
- **Study a reference:** [analysis methods and outputs](references/reference-analysis.md). Pitch, chord and structure estimates remain clues to review, rather than a verified score.
- **Mix with video:** use `scripts/mix.py`; `--vo` adds narration and `--keep-audio` retains the original audio. Mixing defaults to two-pass normalization at −14 LUFS and −2 dBTP.
- **Choose a report language:** [Chinese, English, Japanese and Korean support](references/languages.md), via `--lang zh|en|ja|ko`. The main skill and detailed reference material are currently written primarily in Chinese.

## Compatibility and licensing

Validated on macOS and native Windows 10 x64; Linux has not yet been tested on a real machine. The public package has 121 tests: 118 pass and 3 explicitly skip the DSK font, which is not redistributed.

Project source is [MIT licensed](LICENSE). Sound assets retain their own licenses; see [THIRD_PARTY.md](THIRD_PARTY.md). DSK Asian DreamZ is not distributed with the project.

The final musical result still needs listening. Instrument techniques and reference-analysis estimates should be checked against the actual sources and sound.
