# bgmeasy

[English](README.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md) · **한국어**

### 장면을 설명하고, 에이전트와 배경음악을 만들어 보세요.

장면, 분위기, 필요한 길이를 알려주면 bgmeasy가 에이전트의 곡 전체 설계, 편집 가능한 악보 작성, 로컬 오디오 렌더링을 안내합니다. 선율·리듬·악기 편성·구성이 악보에 남으므로, 들어본 뒤 같은 곡을 계속 다듬을 수 있습니다.

짧은 영상, 내레이션, 게임, 애니메이션의 배경음악 제작에 사용할 수 있습니다. 파일 작업과 명령 실행이 가능한 코딩 에이전트와 함께 사용하며, 렌더링과 참고 음원 분석에 별도 음악 생성 서비스를 연결할 필요는 없습니다.

[시작하기](#시작하기) · [음원 팩](https://github.com/louchi1984-coder/bgmeasy/releases/latest) · [작곡 절차(중국어)](SKILL.md) · [악보 형식(중국어)](references/score-format.md)

## 먼저 장면을 설명하세요

이런 요청으로 시작할 수 있습니다.

> 두 사람이 다시 만나는 장면에 쓸 따뜻하고 조용한 30초 BGM을 만들어 주세요. 대사는 없으니 선율이 잘 들렸으면 합니다. 끝은 차분하게 마무리해 주세요.

들어본 다음에는 같은 곡을 수정합니다.

> 주제 선율은 유지하고 전반부 반주를 줄여 주세요. 후반부는 점차 풍성하게 만들되, 너무 일찍 감정이 최고조에 이르지 않게 해주세요.

먼저 곡 전체의 도착점을 정하고, 그곳으로 이어지는 악구·화성·공통 리듬·악기별 역할을 구성합니다. 에이전트가 작곡과 수정을 맡고, 로컬 프로그램이 악보를 소리로 만듭니다.

```text
장면과 요청 → 곡 전체 설계 → 편집 가능한 악보 → 로컬 렌더링 → 청취와 수정
```

## 작곡·수정·영상 믹싱

| 하려는 작업 | bgmeasy의 활용 방식 |
|---|---|
| 장면에 맞는 오리지널 BGM 제작 | 전체 구성을 먼저 설계하고 선율·화성·리듬·편성을 구체화 |
| 청취 후 수정 | 구성과 설정을 남기고 같은 악보의 필요한 부분을 조정 |
| 참고곡에서 아이디어 얻기 | 음고·리듬·화성·구조의 단서를 살펴 새로운 곡의 설계에 활용 |
| 내레이션이나 대사를 받쳐주는 음악 | 편곡에서 목소리의 공간을 확보하고 믹싱 시 전경 오디오에 따라 더킹 |
| 영상과 함께 납품 | WAV를 출력하거나, 영상 스트림을 복사하면서 오디오 믹싱과 라우드니스 조정 |

작업 결과는 에이전트가 작성한 JSON 악보와 렌더링된 WAV입니다. 영상이 필요할 때 믹싱 단계로 진행합니다. 악보와 설정을 보관하면 이후 수정·비교·재현이 쉬워집니다.

## 시작하기

### 1. 프로젝트 받기

```text
git clone https://github.com/louchi1984-coder/bgmeasy.git
cd bgmeasy
```

GitHub에서 소스 ZIP을 다운로드해도 됩니다.

### 2. 실행 환경 준비하기

**Python 3.10 이상, FFmpeg/FFprobe, FluidSynth**가 필요합니다. 전체 샘플 음원 경로는 약 **169 MB**의 음원 팩도 사용합니다. 설치 명령은 아래 펼침 항목에서 확인할 수 있습니다. Windows에서는 네이티브 Python과 PowerShell로 실행하며 Git Bash나 WSL은 필요하지 않습니다.

### 3. 에이전트에게 스킬 읽히기

코딩 에이전트에게 프로젝트 위치를 알려준 뒤 다음과 같이 요청하세요.

> 이 프로젝트의 SKILL.md를 읽고 실행 환경을 확인해 주세요. bgmeasy로 따뜻하고 차분한 30초 기악 BGM을 만들어 주세요. 대사는 없습니다. 곡 전체를 먼저 계획하고 악보를 작성한 다음 렌더링해 주세요. 악보를 남기고 곡의 구성과 결과 파일을 한국어로 설명해 주세요.

오디오를 들어본 뒤 구체적인 수정 사항을 전달하세요. 길이, 용도, 분위기, 대사 유무, 악기 선호, 참고 음원을 지정할 수 있으며 모든 편곡 파라미터를 직접 입력할 필요는 없습니다.

<details>
<summary><strong>설치 명령과 첫 렌더링 예시 펼치기</strong></summary>

먼저 FFmpeg, FFprobe, FluidSynth를 설치하고 실행 파일을 PATH에 추가하세요. Windows FluidSynth의 동봉 DLL은 실행 파일 옆에 유지합니다. macOS에서는 `brew install ffmpeg fluid-synth`를 사용할 수 있습니다.

**Windows PowerShell**

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -I scripts/download_soundfonts.py
.\.venv\Scripts\python.exe -I scripts/check_deps.py --lang ko
```

**macOS / Linux**

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -I scripts/download_soundfonts.py
.venv/bin/python -I scripts/check_deps.py --lang ko
```

아래의 `python`은 위 가상 환경의 인터프리터로 바꿔 사용하세요. 프로젝트에 포함된 15초 예시를 렌더링합니다.

```text
python -c "from pathlib import Path; Path('outputs').mkdir(exist_ok=True)"
python -I scripts/render_score_sf2.py examples/western-15s.score.json outputs/western.wav --duration 15 --lang ko
python -I scripts/verify.py outputs/western.wav --lang ko
```

원본 WAV 라우드니스 검사에 CHECK가 표시될 수 있습니다. 최종 2패스 정규화는 영상 믹싱 단계에서 수행합니다.

음원 팩 설치기는 SHA-256을 검증합니다. 직접 다운로드가 어려우면 [Release](https://github.com/louchi1984-coder/bgmeasy/releases/latest)에서 ZIP을 받은 뒤 `--archive path/to/bgmeasy-soundfonts.zip`으로 설치할 수 있습니다.

</details>

## 문서 안내

- **악기 선택과 연주 능력 확인**: [연주·백엔드 자료](references/instrument-performance.md), [음원 카탈로그](references/soundfonts.md). 96개 항목의 악기 자료를 제공하며 공개 음원 팩은 16개 SF2와 변형 음색·샘플 타악기를 포함한 312개 항목을 제공합니다.
- **참고 음원 분석**: [분석 방법과 출력](references/reference-analysis.md). 음고·화음·구조는 검토할 단서이며 검증된 원보로 취급하지 않습니다.
- **영상 믹싱**: `scripts/mix.py`를 사용합니다. `--vo`는 내레이션을 추가하고 `--keep-audio`는 원본 오디오를 유지합니다. 기본값은 2패스 정규화, −14 LUFS, −2 dBTP입니다.
- **보고서 언어 선택**: [중국어·영어·일본어·한국어 지원](references/languages.md). `--lang zh|en|ja|ko`로 지정합니다. 메인 스킬과 상세 자료는 현재 주로 중국어입니다.

## 실행 환경과 라이선스

macOS와 네이티브 Windows 10 x64에서 검증했습니다. Linux는 아직 실기기 미검증입니다. 공개판 테스트는 총 121개로, 118개가 통과하고 재배포하지 않는 DSK 음원에 의존하는 3개는 명시적으로 건너뜁니다.

소스는 [MIT 라이선스](LICENSE)입니다. 음원은 각자의 라이선스를 따르며 [THIRD_PARTY.md](THIRD_PARTY.md)에서 확인할 수 있습니다. DSK Asian DreamZ는 배포하지 않습니다.

최종 음악은 실제로 들어 확인해야 합니다. 음원의 주법 지원과 참고 분석의 신뢰도 역시 자료 및 실제 소리와 대조해 판단하세요.
