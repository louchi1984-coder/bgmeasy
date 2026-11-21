# bgmeasy

**English** · [简体中文](README.zh-CN.md) · [日本語](README.ja.md) · [한국어](README.ko.md)

### Compose background music with your coding agent.

Describe the scene or mood. Your agent writes an editable score and renders the audio locally, so you can change the melody, rhythm or arrangement after listening.

Built for background music in short videos, narrated content, games and animation. Use it with a coding agent that can read files and run commands. Rendering and reference analysis need no separate music-generation service.

[Get started](#get-started) · [v0.1.0 sound pack](https://github.com/louchi1984-coder/bgmeasy/releases/tag/v0.1.0) · [Composition workflow (中文)](SKILL.md) · [Score format (中文)](references/score-format.md)

## Start with the scene

A brief can be as simple as:

> Write 30 seconds of warm, quiet music for two people meeting again. There is no dialogue, so the melody can stand out. Give it a settled ending.

After listening, keep shaping the same piece:

> Keep the main theme. Thin out the accompaniment in the first half, then gradually build the second half without reaching full intensity too early.

In reference mode the agent studies passages from existing scores before composing. In direct mode it writes from your brief. In both modes you hear three original sketches and choose one. The agent then asks for the final duration and how full the arrangement should sound, using any details you have already given.

```text
Describe the scene → Choose a mode → Hear three sketches and pick one → Set duration and arrangement → Develop the full cue
```

## Compose, revise, and mix with video

| Your task | How bgmeasy helps |
|---|---|
| Score a scene | Choose a sketch, then develop its melody, harmony, rhythm and orchestration into a complete cue |
| Revise after listening | Adjust the same score while keeping the structure, settings and reasons for changes |
| Work from a reference | Examine pitch, rhythm, harmony and structural clues to inform a new composition |
| Support narration or dialogue | Leave room in the arrangement, then use foreground-driven ducking during mixing |
| Deliver music with a video | Render a WAV, or mix it into video with loudness normalization and video stream copy |

An original cue normally comes with a WAV for listening, a MIDI file for editing, and the JSON score used to render it. Separate sampler parts and audio effects are preserved in the WAV. You can mix the cue into a video when needed.

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

> Read this project’s SKILL.md and check the environment. Write some warm instrumental music for a reunion scene with no dialogue. Use direct mode and give me three sketches to listen to. Explain the differences in English.

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

The sound pack installer verifies SHA-256. If direct downloading is inconvenient, get the ZIP from [Releases](https://github.com/louchi1984-coder/bgmeasy/releases/tag/v0.1.0) and install it with `--archive path/to/bgmeasy-soundfonts.zip`.

</details>

## Documentation

- **Choose instruments and check their capabilities:** [performance and backend guide](references/instrument-performance.md), [sound catalog](references/soundfonts.md). The knowledge base covers 96 instrument profiles; the release sound pack provides 16 SF2 files and 312 catalog entries, including variants and sampled percussion.
- **Study a reference:** [analysis methods and outputs](references/reference-analysis.md). Pitch, chord and structure estimates remain clues to review, rather than a verified score.
- **Mix with video:** use `scripts/mix.py`; `--vo` adds narration and `--keep-audio` retains the original audio. Mixing defaults to two-pass normalization at −14 LUFS and −2 dBTP.
- **Choose a report language:** [Chinese, English, Japanese and Korean support](references/languages.md), via `--lang zh|en|ja|ko`. The main skill and detailed reference material are currently written primarily in Chinese.

## Compatibility and licensing

This revision ran 127 tests on macOS with Python 3.14.2 and the v0.1.0 sound pack. 124 passed, and three were skipped because they require the optional DSK soundfont. A native Windows run for this revision is pending.

The v0.1.0 public release was tested on macOS and native Windows 10 x64. Each ran 121 tests with 118 passes and three skips for the separately installed DSK soundfont. Linux has not yet been tested on a native host.

Project source is [MIT licensed](LICENSE). Sound assets retain their own licenses; see [THIRD_PARTY.md](THIRD_PARTY.md). DSK Asian DreamZ is not distributed with the project.

The final musical result still needs listening. Instrument techniques and reference-analysis estimates should be checked against the actual sources and sound.
