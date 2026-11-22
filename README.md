# bgmeasy

**English** · [简体中文](README.zh-CN.md) · [日本語](README.ja.md) · [한국어](README.ko.md)

### Compose background music with your coding agent.

Describe a scene, share a reference recording or video, or send a recording of yourself humming. You hear three 15-second sketches first. Pick one and your agent develops it into a full cue with an editable score and locally rendered audio.

Built for background music in short videos, narrated content, games and animation. Use it with a coding agent that can read files and run commands. Rendering and reference analysis need no separate music-generation service.

[Get started](#get-started) · [v0.2.0 sound pack](https://github.com/louchi1984-coder/bgmeasy/releases/tag/v0.2.0) · [Composition workflow (中文)](SKILL.md) · [Score format (中文)](references/score-format.md)

## Choose a starting point

> Write a warm, stately march for a wedding entrance. The couple meet 12 seconds in. Let the music brighten as they reach each other.

A scene or a mood is enough to start. Include a time cue if the music should land on a particular action. With a written brief, you can name a mode or let the agent explain the three options and wait for your choice.

| Mode | What you bring | What the agent does |
|---|---|---|
| **Direct composition** | A purpose, scene or mood | Writes from the brief, exploring different grooves, harmonies or melodic shapes. |
| **Reference** | A sound you have in mind, optionally a piece by name | Finds relevant works and studies passages in their scores. It might borrow how the bass builds momentum or how one part answers another, then write an original theme. |
| **Analysis** | An audio or video file, or a recording of you humming | Starts analysis as soon as you supply a readable file. With a reference recording it looks for rhythmic, harmonic and structural clues. With your own tune it keeps the pitches and rhythm and varies the arrangement. |

A title alone or a link the agent cannot open leads to reference mode. In all three modes you get **three playable 15-second sketches**, each with a sentence on what to listen for. Listen for the pulse, how the chords change, and who takes over when the lead pauses. If none fits, tell the agent why and it will make three new sketches.

Once you pick a sketch, the agent asks how long the finished cue should run and how full you want the arrangement. It carries forward any details you already gave. One reply can cover all three decisions.

> Sketch 2, 60 seconds. Keep that walking pace and add a cello answering the melody in the second half.

## Compose, revise, and mix with video

| Your task | How bgmeasy helps |
|---|---|
| Score a scene | Choose a sketch, then develop its melody, harmony, rhythm and orchestration into a complete cue |
| Revise after listening | Adjust the same score while keeping the structure, settings and reasons for changes |
| Develop a hummed tune | Keep your melody, hear it with different accompaniments, and develop the arrangement you choose |
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

You need **Python 3.10+, FFmpeg/FFprobe and FluidSynth**. The full sampled workflow also uses a **179 MB** sound pack. Expand the commands below for setup. Windows runs with native Python and PowerShell; Git Bash and WSL are not required.

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

The sound pack installer verifies SHA-256. If direct downloading is inconvenient, get the ZIP from [Releases](https://github.com/louchi1984-coder/bgmeasy/releases/tag/v0.2.0) and install it with `--archive path/to/bgmeasy-soundfonts.zip`.

</details>

## Documentation

- **Choose instruments and check their capabilities:** [performance and backend guide](references/instrument-performance.md), [sound catalog](references/soundfonts.md). The knowledge base covers 96 instrument profiles; the release sound pack provides 17 SF2 files and 319 catalog entries, including variants and sampled percussion.
- **Find a score or analyze a recording.** Pitch, chord and structure estimates are clues to review. [Reference study and audio analysis](references/reference-analysis.md)
- **Develop a hummed tune.** [Transcription and arrangement workflow](references/hum-workflow.md)
- **Mix with video:** use `scripts/mix.py`; `--vo` adds narration and `--keep-audio` retains the original audio. Mixing defaults to two-pass normalization at −14 LUFS and −2 dBTP.
- **Choose a report language:** [Chinese, English, Japanese and Korean support](references/languages.md), via `--lang zh|en|ja|ko`. The main skill and detailed reference material are currently written primarily in Chinese.

## Compatibility and licensing

On macOS with Python 3.14.2 and the v0.2.0 standard sound pack, all 128 tests passed with no skips, including the DSK tests. A native Windows run for v0.2.0 is pending.

Commit `124d698` was tested on macOS with Python 3.14.2 and the v0.1.0 sound pack. Of 127 tests, 124 passed and three skipped because that pack omitted DSK.

The v0.1.0 public release was tested on macOS and native Windows 10 x64. Each ran 121 tests with 118 passes and three skips for the separately installed DSK soundfont. Linux has not yet been tested on a native host.

Project source is [MIT licensed](LICENSE). Sound assets retain their own licenses; see [THIRD_PARTY.md](THIRD_PARTY.md). The v0.2.0 standard sound pack includes the original DSK Asian DreamZ SF2 and the author’s README. The [complete upstream ZIP](https://github.com/louchi1984-coder/bgmeasy/releases/download/v0.2.0/DSK_Asian_DreamZ_sf2.zip) is also available. See [DSK Music’s license terms](https://www.dskmusic.com/license-info/) and [the release announcement](https://rekkerd.org/dsk-music-releases-dsk-asian-dreamz-vol-1/).

The final musical result still needs listening. Instrument techniques and reference-analysis estimates should be checked against the actual sources and sound.
