# bgmeasy

[English](README.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md) · [한국어](README.ko.md)

**An agent skill for composing, rendering and checking background music locally.**

An LLM agent plans the whole piece and writes a symbolic score. Python renders it to WAV using synthesis or SoundFonts. The same project can mix music into video, duck it around narration, and analyze reference audio with classical signal processing.

No music-generation model, model-weight download, cloud music API or commercial instrument plugin is required. Your coding agent supplies the composition reasoning.

## What is included

- Whole-piece planning, phrase development, harmony, rhythm and orchestration guidance in `SKILL.md` and `references/`.
- Built-in synthesis and a MIDI → FluidSynth/SF2 → mastering path.
- Native Python video mixing: narration/original-audio ducking, two-pass loudness normalization and video stream copy. **Windows does not need Git Bash or WSL.**
- Reference-audio pitch, rhythm, harmony and structure **candidates**, with uncertainty retained; no learned models.
- Chinese, English, Japanese and Korean instrument search and standard reports: `--lang zh|en|ja|ko`.
- 96 instrument knowledge profiles. The optional sound pack contains 16 SF2 files and 312 catalog entries, including variants and sampled percussion. A profile is not a separate sound library or a guarantee of realism.

## Setup

Use Python 3.10+ and install native **FFmpeg + FFprobe** and **FluidSynth** on your PATH. Keep the DLLs distributed with Windows FluidSynth beside its executable. macOS users can use `brew install ffmpeg fluid-synth`.

Download this repository, or clone it:

```text
git clone https://github.com/louchi1984-coder/bgmeasy.git
cd bgmeasy
```

Create a virtual environment and install the Python dependencies:

```powershell
# Windows PowerShell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

```sh
# macOS / Linux
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

In the commands below, use that environment's interpreter in place of `python`. Activation is optional.

For the complete sampled workflow, download the **169 MB** separately licensed sound pack:

```text
python -I scripts/download_soundfonts.py
python -I scripts/check_deps.py --lang en
```

The installer verifies SHA-256, rejects unsafe paths and refuses to overwrite different existing files. For offline setup, download [`bgmeasy-soundfonts.zip`](https://github.com/louchi1984-coder/bgmeasy/releases/download/v0.1.0/bgmeasy-soundfonts.zip) and pass `--archive path/to/bgmeasy-soundfonts.zip`. Sound binaries are Release assets, not part of Git history. **DSK Asian DreamZ is excluded.** See [third-party licenses](THIRD_PARTY.md).

## Use with an agent

Point an agent with file and command execution access at [`SKILL.md`](SKILL.md). For example:

> Use this skill to make 30 seconds of warm, calm background music. No dialogue. Plan the complete piece first, write a coherent theme, and render with the standard workflow. Give me an English report.

The main skill and detailed reference material are currently written primarily in Chinese. The README, instrument aliases and standard report UI support the four languages above; original quotations and user-authored text are preserved.

## CLI examples

```text
python -c "from pathlib import Path; Path('outputs').mkdir(exist_ok=True)"
python -I scripts/render_score_sf2.py examples/western-15s.score.json outputs/western.wav --duration 15 --lang en
python -I scripts/verify.py outputs/western.wav --lang en
python -I scripts/soundfonts.py search "ピアノ" --lang ja
python -I scripts/instruments.py search "얼후" --lang ko
```

The raw WAV check may flag loudness; video mixing performs the final two-pass normalization.

With your own reference audio or video:

```text
python -I scripts/analyze_reference.py reference.wav outputs/reference --seconds 30 --lang en
python -I scripts/mix.py --video input.mp4 --bgm outputs/western.wav --out outputs/mixed.mp4 --lang en
```

Add `--vo narration.wav` or `--keep-audio` to make foreground audio trigger BGM ducking. Mixing keeps the established defaults: −14 LUFS, −2 dBTP, two-pass `loudnorm`, and no extra fade unless requested. For sampled-layer contributions, render with `--report-levels`.

Report language changes presentation, not the score or audio processing. JSON/CSV keys, technical enums, timestamps and numeric analysis remain stable. Charts use local fonts; if required glyphs are unavailable, chart labels fall back to English while HTML text keeps the requested language. [Language details](references/languages.md).

## Tests and limits

```text
python -I -B -m unittest discover -s tests -v
```

Install the sound pack and external tools before running the full suite. Three tests requiring the excluded, locally licensed DSK font are explicitly skipped. Do not download that font merely to remove the skips.

The development workflow has been tested on macOS and native Windows 10 x64 / Python 3.10, including default CP936 encoding and PowerShell. Linux is not yet validated on a real machine. Tests check score parsing, routing, DSP fixtures, language consistency and mixing behavior; they do not certify musical quality. Listening is still required. Reference-analysis results are not a verified transcription or instrument separation. Some instrument evidence is conditional or unverified; small sample sets do not provide true legato or a natural full range.

## License

Project code and documentation: [MIT](LICENSE), except explicitly licensed files. Sound assets and dependencies retain their own licenses, including CC0 and the custom GeneralUser GS license. Read [THIRD_PARTY.md](THIRD_PARTY.md) before redistribution.
