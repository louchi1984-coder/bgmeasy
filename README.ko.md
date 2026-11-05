# bgmeasy

[English](README.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md) · [한국어](README.ko.md)

**AI 에이전트가 로컬에서 배경음악을 설계·렌더링·검증하는 스킬입니다.**

LLM 에이전트가 곡 전체를 계획하고 기호 악보를 작성하면 Python이 합성 음원 또는 SoundFont로 WAV를 만듭니다. 영상 믹싱, 내레이션에 따른 자동 더킹, 전통적인 신호 처리 기반 참고 음원 분석도 지원합니다.

음악 생성 모델, 모델 가중치 다운로드, 클라우드 음악 API, 상용 악기 플러그인은 필요하지 않습니다. 작곡 판단은 사용 중인 코딩 에이전트가 담당합니다.

## 기능

- `SKILL.md`와 `references/`에 전체 구성, 악구 발전, 화성, 리듬, 편성 자료를 제공합니다.
- 내장 합성 및 MIDI → FluidSynth/SF2 → 마스터링 렌더링 경로.
- 네이티브 Python 영상 믹싱: 내레이션·원본 오디오에 따른 더킹, 2패스 라우드니스 정규화, 영상 스트림 복사. **Windows에서 Git Bash나 WSL이 필요하지 않습니다.**
- 학습 모델 없이 음고·리듬·화성·구조의 **후보**를 분석하고 불확실성을 유지합니다.
- 중국어·영어·일본어·한국어 악기 검색과 표준 보고서: `--lang zh|en|ja|ko`.
- 96개 악기 자료 profile. 선택 음원 팩은 16개 SF2와 312개 카탈로그 항목을 포함하며 변형 음색과 샘플 타악기도 제공합니다. 자료 수는 독립 음원 라이브러리 수나 사실성 보장이 아닙니다.

## 설치

Python 3.10 이상을 권장합니다. 네이티브 **FFmpeg, FFprobe, FluidSynth**를 설치하고 PATH에 추가하세요. Windows FluidSynth의 동봉 DLL은 실행 파일 옆에 유지해야 합니다. macOS에서는 `brew install ffmpeg fluid-synth`를 사용할 수 있습니다.

저장소를 다운로드하거나 복제합니다.

```text
git clone https://github.com/louchi1984-coder/bgmeasy.git
cd bgmeasy
```

가상 환경과 Python 의존성을 준비합니다.

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

이후 명령의 `python`은 해당 가상 환경의 인터프리터로 바꿔 사용하세요. 가상 환경 활성화는 필수가 아닙니다.

전체 샘플 음원 경로를 사용하려면 별도 라이선스 음원 팩(약 **169 MB**)을 설치합니다.

```text
python -I scripts/download_soundfonts.py
python -I scripts/check_deps.py --lang ko
```

설치기는 SHA-256을 검증하고 위험한 경로와 기존 파일의 다른 내용 덮어쓰기를 거부합니다. 오프라인에서는 [`bgmeasy-soundfonts.zip`](https://github.com/louchi1984-coder/bgmeasy/releases/download/v0.1.0/bgmeasy-soundfonts.zip)을 받아 `--archive path/to/bgmeasy-soundfonts.zip`을 지정할 수 있습니다. 음원 바이너리는 Release로 제공하며 Git 기록에 넣지 않습니다. **DSK Asian DreamZ는 제외합니다.** [서드파티 라이선스](THIRD_PARTY.md)를 확인하세요.

## 에이전트로 사용하기

파일 작업과 명령 실행이 가능한 에이전트에게 [`SKILL.md`](SKILL.md)를 읽도록 요청합니다. 예시:

> 이 스킬로 따뜻하고 차분한 30초 BGM을 만들어 주세요. 대사는 없습니다. 곡 전체를 먼저 계획하고 일관된 주제를 작성한 다음 표준 절차로 렌더링해 주세요. 보고서는 한국어로 작성해 주세요.

메인 스킬과 상세 참고 자료는 현재 주로 중국어로 작성되어 있습니다. README·악기 별칭·표준 보고서 UI는 위의 4개 언어를 지원합니다. 인용문과 사용자 작성 문장은 원문을 유지합니다.

## CLI 예시

```text
python -c "from pathlib import Path; Path('outputs').mkdir(exist_ok=True)"
python -I scripts/render_score_sf2.py examples/western-15s.score.json outputs/western.wav --duration 15 --lang ko
python -I scripts/verify.py outputs/western.wav --lang ko
python -I scripts/soundfonts.py search "ピアノ" --lang ja
python -I scripts/instruments.py search "얼후" --lang ko
```

원본 WAV 라우드니스 검사에 CHECK가 표시될 수 있습니다. 최종 2패스 정규화는 영상 믹싱 단계에서 수행합니다.

자신의 참고 음원이나 영상을 사용할 때:

```text
python -I scripts/analyze_reference.py reference.wav outputs/reference --seconds 30 --lang ko
python -I scripts/mix.py --video input.mp4 --bgm outputs/western.wav --out outputs/mixed.mp4 --lang ko
```

`--vo narration.wav` 또는 `--keep-audio`를 추가하면 전경 오디오에 따라 BGM을 더킹합니다. 기존 기본값은 −14 LUFS, −2 dBTP, 2패스 `loudnorm`입니다. 별도 요청이 없으면 추가 페이드하지 않습니다. 샘플 성부의 기여도는 렌더링 시 `--report-levels`로 확인할 수 있습니다.

언어 설정은 표시만 바꾸며 악보나 오디오 처리를 바꾸지 않습니다. JSON/CSV 키, 기술 열거값, 시간과 분석 수치는 유지됩니다. 차트는 로컬 글꼴을 사용하며 필요한 글리프가 없으면 차트 라벨만 영어로 표시합니다. HTML 본문은 선택 언어를 유지합니다. [언어 지원 상세](references/languages.md).

## 테스트와 한계

```text
python -I -B -m unittest discover -s tests -v
```

전체 테스트 전에 음원 팩과 외부 도구를 설치하세요. 재배포하지 않는 DSK 음원에 의존하는 3개 테스트는 명시적으로 건너뜁니다. 건너뛰기를 없애기 위해 DSK를 추가로 다운로드하지 마세요.

개발 절차는 macOS와 네이티브 Windows 10 x64 / Python 3.10에서 검증했으며 기본 CP936 인코딩과 PowerShell도 확인했습니다. Linux는 아직 실기기 미검증입니다. 테스트는 악보 파싱·라우팅·DSP 테스트 신호·언어 일관성·믹싱 동작을 확인할 뿐 음악의 질을 보장하지 않습니다. 실제 청취가 필요합니다. 참고 분석은 검증된 원보나 악기별 스템이 아닙니다. 악기 자료에는 조건부·미검증 항목이 있으며 작은 샘플 세트는 실제 레가토나 자연스러운 전 음역을 보장하지 않습니다.

## 라이선스

별도 표기가 없는 코드와 문서는 [MIT](LICENSE)입니다. 음원과 의존 소프트웨어는 CC0와 GeneralUser GS 자체 라이선스 등 각자의 조건을 유지합니다. 재배포 전 [THIRD_PARTY.md](THIRD_PARTY.md)를 확인하세요.
