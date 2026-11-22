# bgmeasy

[English](README.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md) · **한국어**

### 장면을 설명하고, 에이전트와 배경음악을 만들어 보세요.

장면이나 원하는 분위기를 알려주세요. 에이전트가 만든 15초짜리 시안 세 개를 듣고 하나를 고르면, 그 시안을 바탕으로 완성곡을 만듭니다. 악보와 오디오가 함께 남아 선율, 리듬, 악기 편성을 다시 손볼 수 있습니다.

짧은 영상, 내레이션, 게임, 애니메이션의 배경음악 제작에 사용할 수 있습니다. 파일 작업과 명령 실행이 가능한 코딩 에이전트와 함께 사용하며, 렌더링과 참고 음원 분석에 별도 음악 생성 서비스를 연결할 필요는 없습니다.

[시작하기](#시작하기) · [v0.2.0 음원 팩](https://github.com/louchi1984-coder/bgmeasy/releases/tag/v0.2.0) · [작곡 절차(중국어)](SKILL.md) · [악보 형식(중국어)](references/score-format.md)

## 장면과 자료에 맞는 모드 고르기

한 문장이면 시작할 수 있습니다. 음악이 화면의 특정 순간과 맞아야 한다면 그 시점도 알려주세요.

> 결혼식 입장 장면에 쓸 행진곡을 써 주세요. 첫걸음부터 박자가 들리고, 두 사람이 12초쯤 눈을 마주칠 때 선율이 살짝 고조되면 좋겠어요.

| 모드 | 언제 쓰나요? | 에이전트가 하는 일 |
|---|---|---|
| **직접 작곡** | 장면이나 분위기만 정해져 있을 때 | 설명을 바탕으로 박자감, 화성, 선율이 서로 다른 시안을 씁니다. |
| **참고** | 비슷한 느낌의 곡을 찾아보고 싶거나 참고할 곡의 제목만 알 때 | 에이전트가 직접 작품을 찾아 악보의 특정 구절을 읽고, 그곳에서 쓰인 작곡 기법을 새 곡에 활용합니다. |
| **분석** | 재생 가능한 오디오·영상 파일이나 직접 녹음한 허밍이 있을 때 | 참고 음원에서는 리듬과 화성 등의 단서를 찾아 새 곡에 활용합니다. 직접 부른 허밍은 음높이와 리듬을 살리고 시안마다 반주와 편성을 달리합니다. |

파일을 첨부하면 바로 분석 모드로 들어갑니다. 모드를 지정했다면 그대로 진행하고, 그 밖의 경우에는 세 모드를 소개한 뒤 선택을 기다립니다.

어느 모드에서든 **각각 15초인 시안 세 개**를 재생해 볼 수 있습니다. 에이전트는 들을 때 무엇이 다른지 한 문장씩 짚어 줍니다. 번호만 골라도 되고 수정할 점을 함께 말해도 됩니다. 셋 다 마음에 들지 않으면 피드백을 바탕으로 세 개를 다시 만듭니다.

> 2번으로 해 주세요. 완성곡은 60초로 하고, 입장 박자는 살리면서 뒤로 갈수록 현악기를 더해 주세요.

시안을 고른 뒤에는 완성곡의 길이와 편성을 얼마나 풍성하게 할지 정합니다. 처음에 알려준 조건은 그대로 반영합니다.

## 작곡·수정·영상 믹싱

| 하려는 작업 | bgmeasy의 활용 방식 |
|---|---|
| 장면에 맞는 오리지널 BGM 제작 | 선택한 시안의 선율·화성·리듬·편성을 살려 전체 곡으로 발전 |
| 청취 후 수정 | 구성과 설정을 남기고 같은 악보의 필요한 부분을 조정 |
| 직접 부른 선율 편곡 | 허밍을 채보하고 원래 선율에 어울리는 반주와 악기 편성을 시안으로 비교 |
| 내레이션이나 대사를 받쳐주는 음악 | 편곡에서 목소리의 공간을 확보하고 믹싱 시 전경 오디오에 따라 더킹 |
| 영상과 함께 납품 | WAV를 출력하거나, 영상 스트림을 복사하면서 오디오 믹싱과 라우드니스 조정 |

오리지널 완성곡은 보통 감상용 WAV, 편집용 MIDI, 렌더링에 사용한 JSON 악보로 제공합니다. 별도 샘플러로 재생한 파트와 오디오 효과는 WAV에 담깁니다. 필요하면 영상과 믹싱할 수 있습니다.

## 시작하기

### 1. 프로젝트 받기

```text
git clone https://github.com/louchi1984-coder/bgmeasy.git
cd bgmeasy
```

GitHub에서 소스 ZIP을 다운로드해도 됩니다.

### 2. 실행 환경 준비하기

**Python 3.10 이상, FFmpeg/FFprobe, FluidSynth**가 필요합니다. 전체 샘플 음원 경로는 약 **179 MB**의 음원 팩도 사용합니다. 설치 명령은 아래 펼침 항목에서 확인할 수 있습니다. Windows에서는 네이티브 Python과 PowerShell로 실행하며 Git Bash나 WSL은 필요하지 않습니다.

### 3. 에이전트에게 스킬 읽히기

코딩 에이전트에게 프로젝트 위치를 알려준 뒤 다음과 같이 요청하세요.

> 이 프로젝트의 SKILL.md를 읽고 실행 환경을 확인해 주세요. 두 사람이 다시 만나는 장면에 따뜻한 기악곡을 쓰고 싶어요. 대사는 없습니다. 직접 작곡 모드로 시안 세 개를 들려주고 각각의 차이를 한국어로 설명해 주세요.

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

음원 팩 설치기는 SHA-256을 검증합니다. 직접 다운로드가 어려우면 [Release](https://github.com/louchi1984-coder/bgmeasy/releases/tag/v0.2.0)에서 ZIP을 받은 뒤 `--archive path/to/bgmeasy-soundfonts.zip`으로 설치할 수 있습니다.

</details>

## 문서 안내

- **악기 선택과 연주 능력 확인**: [연주·백엔드 자료](references/instrument-performance.md), [음원 카탈로그](references/soundfonts.md). 96개 항목의 악기 자료를 제공하며 공개 음원 팩은 17개 SF2와 변형 음색·샘플 타악기를 포함한 319개 항목을 제공합니다.
- **참고곡과 허밍**. 참고할 악보를 찾는 법과 음원 분석 결과를 읽는 법은 [참고곡 가이드](references/reference-analysis.md)에, 직접 부른 선율을 채보하고 편곡하는 방법은 [허밍 가이드](references/hum-workflow.md)에 담겨 있습니다.
- **영상 믹싱**: `scripts/mix.py`를 사용합니다. `--vo`는 내레이션을 추가하고 `--keep-audio`는 원본 오디오를 유지합니다. 기본값은 2패스 정규화, −14 LUFS, −2 dBTP입니다.
- **보고서 언어 선택**: [중국어·영어·일본어·한국어 지원](references/languages.md). `--lang zh|en|ja|ko`로 지정합니다. 메인 스킬과 상세 자료는 현재 주로 중국어입니다.

## 실행 환경과 라이선스

v0.2.0은 macOS, Python 3.14.2, 표준 음원 팩으로 DSK 관련 테스트를 포함한 128개 테스트를 모두 통과했습니다. 건너뛴 테스트는 없습니다. 이 버전은 Windows 실기기에서 아직 다시 검증하지 않았습니다.

커밋 `124d698`은 macOS와 Python 3.14.2에서 v0.1.0 음원 팩으로 127개 테스트를 실행했습니다. 124개가 통과했고 당시 팩에 DSK 음원이 없어 3개는 건너뛰었습니다.

공개판 v0.1.0은 macOS와 네이티브 Windows 10 x64에서 각각 121개 테스트를 실행해 118개가 통과했습니다. 별도로 설치해야 하는 DSK 음원 관련 테스트 3개는 건너뛰었습니다. Linux는 실기기에서 아직 검증하지 않았습니다.

소스는 [MIT 라이선스](LICENSE)입니다. 음원은 각자의 라이선스를 따르며 [THIRD_PARTY.md](THIRD_PARTY.md)에서 확인할 수 있습니다. v0.2.0 표준 음원 팩에는 DSK Asian DreamZ 원본 SF2와 제작자의 README가 들어 있습니다. [제작자가 배포한 원본 ZIP 전체](https://github.com/louchi1984-coder/bgmeasy/releases/download/v0.2.0/DSK_Asian_DreamZ_sf2.zip)도 따로 받을 수 있습니다. 복제·배포 조건은 [DSK Music 라이선스](https://www.dskmusic.com/license-info/)에서, 음원의 출처는 [출시 공지](https://rekkerd.org/dsk-music-releases-dsk-asian-dreamz-vol-1/)에서 확인할 수 있습니다.

최종 음악은 실제로 들어 확인해야 합니다. 음원의 주법 지원과 참고 분석의 신뢰도 역시 자료 및 실제 소리와 대조해 판단하세요.
