# Third-party assets and dependencies

The MIT license at the repository root covers project code and documentation except where a file states otherwise. It does not replace the licenses of audio assets, upstream conversion material, Python packages or external programs.

The optional `bgmeasy-soundfonts.zip` release asset preserves the original license files, attribution, source URLs, conversion information and SHA-256 records under `soundfonts/`.

| Component | License / distribution notes | Included notices |
|---|---|---|
| GeneralUser GS 2.0.3 | GeneralUser GS License v2.0, **not MIT/CC0**. The author's license permits software-project use and packaging changes, and explicitly describes uncertainty in some historical sample provenance. Read the complete license before reuse. | `soundfonts/LICENSE-GeneralUser-GS.txt` |
| FreePats lightweight instruments | CC0-1.0; individual sources, sizes and hashes are recorded in the manifest. | `soundfonts/freepats-light/manifest.json`, `soundfonts/freepats-light/licenses/` |
| VCSL excerpts | CC0-1.0. The installed WAV set contains Dan Tranh, bass drums and gongs. Dan Tranh is a Vietnamese instrument, not a verified Chinese guzheng recording. | `soundfonts/vcsl/LICENSE-VCSL.txt` |
| AliExpress Erhu conversion | CC0-1.0; pinned upstream commit and per-sample provenance. It remains an evaluated candidate, not a certified natural-sounding replacement. | `soundfonts/ethnic-light/LICENSE-erhu.txt`, `UPSTREAM-erhu.txt`, `manifest.json` |
| Erhu practice excerpts by irzirgpznj | CC0-1.0. Lossy-source excerpts mapped only to A4/C5; no full-range or legato claim. | `soundfonts/ethnic-light/ATTRIBUTION-erhu-practice.txt`, `erhu-practice-provenance.json` and the license URL recorded there |
| DSK Asian DreamZ | **Excluded.** No redistribution grant was established. Historical optional references and tests remain; the binary is never part of this repository or release bundle. | `soundfonts/LICENSE-DSK-NOTE.txt` |

External Python packages are installed separately through pip and retain their own licenses. FFmpeg/FFprobe and FluidSynth are external programs installed by the user and are not bundled. The reference-analysis path uses classical DSP; no model weights, commercial music plugins or third-party audio APIs are installed by this project.

The verified release ZIP SHA-256, file list and pinned download URL are in [`references/soundfont-bundle.json`](references/soundfont-bundle.json). The installer verifies the archive and every file, refuses path traversal, and does not overwrite a conflicting existing file.
