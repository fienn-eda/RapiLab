# RapiLab

승리의 여신: 니케 덱 추천기. 내 로스터로 **어떤 편성이 가장 세게 나오는지**를
전투 시뮬레이션으로 계산합니다.

스킬 배율만 더하는 것이 아니라 180초 전투를 발사 단위로 돌립니다 — 재장전과
탄창, 버스트 로테이션, 버프의 지속시간과 겹침, 풀버스트 창 안팎을 전부 시간
위에 놓고 계산합니다. 그래서 "이 서포터를 넣으면 총딜이 얼마나 오르는지" 같은,
표만 봐서는 안 나오는 질문에 답할 수 있습니다.

> **상태: 개발 중.** [릴리스](https://github.com/fienn-eda/RapiLab/releases)에서
> 받아 쓸 수 있고, 앱이 켜질 때 새 버전을 스스로 확인해 교체합니다. 소스에서
> 직접 빌드해도 됩니다(아래 [직접 빌드하기](#직접-빌드하기)).

## 무엇을 하나요

- **니케 풀** — 보유 니케와 투자 상태(레벨·돌파·오버로드·애장품·큐브)를 관리합니다.
  blablalink 계정에서 **한 번에 가져올 수 있습니다**.
- **솔로 레이드** — 보스 조건을 넣으면 가장 좋은 5인 편성을 찾아줍니다.
- **유니온 레이드** — 5개 덱에 니케를 겹치지 않게 배분합니다. 일부 자리를
  직접 정해두고 나머지만 채우게 할 수도 있습니다.
- **계산기** — 차지 무기의 풀버스트 발수 계산기. 오버로드 차지속도가 한 발을
  더 넣는 문턱을 넘었는지 봅니다.

현재 **98기**의 니케가 시뮬레이션에 들어갑니다. 차지 계산기는 스칼렛: 블랙
섀도우 · 리베랄리오 · 네온: 비전 아이 세 명을 다룹니다.

## 얼마나 믿을 수 있나요

엔진은 Fienn의 실제 레이드 기록(5덱 25기)과 대조해 맞춰져 있습니다. 다만
**중요한 전제가 하나** 있습니다.

**추천은 "모든 평타가 코어에 명중한다"는 가정 위에서 계산됩니다.** 실제
전투에서는 조준과 부위 타격 때문에 100%가 나오지 않습니다. 그래서 이 앱의
숫자는 실제 딜이 아니라 **상한**이고, 평타 비중이 큰 니케가 실제보다 높게
평가될 수 있습니다. 덱끼리 비교할 때는 모두에게 같은 전제가 적용되므로
순위는 대체로 유효하지만, 절대값을 기대 딜로 읽지는 마세요.

같은 이유로 앱이 내는 총딜은 실제 기록보다 큽니다. 자세한 근거는
`docs/engine-gaps.md`의 21번 항목에 있습니다.

## 개인정보

**로스터는 이 PC를 떠나지 않습니다.** 서버가 없고, 계산은 전부 사용자
컴퓨터에서 돕니다. blablalink 조회도 사용자 브라우저에서 직접 나가며,
저장은 `%LOCALAPPDATA%\RapiLab` 아래 한 곳뿐입니다. 계정 비밀번호는
어디에도 입력하지 않고 요구하지도 않습니다.

앱이 스스로 보내는 요청은 **시작할 때 GitHub에 새 버전이 있는지 묻는 것
하나**뿐입니다. 전문은 앱 화면 맨 아래 "개인정보 처리방침"을 펼치면 읽을 수
있고, 거기 적힌 주장은 `backend/tests/test_privacy_claims.py`가 코드와 대조해
지킵니다.

## 직접 빌드하기

Windows · Python · Node.js가 필요합니다. 파이썬은 **3.14**에서
검증했습니다(다른 버전은 확인하지 않았습니다).

```bash
# 1) 의존성
cd frontend && npm install && cd ..
pip install -r backend/requirements-app.txt

# 2) 빌드 (프론트 → 엔진 버전 스탬프 → 실행 파일, 순서가 중요합니다)
python scripts/build_app.py

# 3) 실행
dist/RapiLab/RapiLab.exe
```

`RapiLab.exe`와 옆의 `_internal/` 폴더는 **항상 같이** 있어야 합니다.

정상 여부만 빠르게 확인하려면:

```bash
dist/RapiLab/RapiLab.exe --selftest   # 창 없이 번들 점검, 결과는 %LOCALAPPDATA%\RapiLab\selftest.log
dist/RapiLab/RapiLab.exe --debug      # 창에서 우클릭 → 개발자 도구
```

**코드 서명이 되어 있지 않습니다.** 실행하면 Windows SmartScreen이 경고를
띄웁니다. "추가 정보 → 실행"으로 넘길 수 있고, 마음이 놓이지 않으면 위처럼
소스에서 직접 빌드하시면 됩니다 — 그러라고 코드를 공개해 두었습니다.

## 개발

프론트(Vite)와 백엔드(FastAPI)를 **각각 다른 터미널에서** 띄웁니다. Vite가
`/api/*`를 8000번으로 넘겨주므로 둘 다 떠 있어야 합니다 — 백엔드를 안 띄우면
화면은 뜨지만 모든 요청이 실패합니다.

```bash
# 터미널 1
cd backend && uvicorn app.api:app --reload --port 8000

# 터미널 2
cd frontend && npm run dev            # http://localhost:5173
```

Windows에서는 스크립트 하나로 둘을 함께 띄울 수 있습니다. 창 두 개를 열고
포트가 비어 있는지 확인한 뒤 브라우저까지 엽니다.

```powershell
powershell -ExecutionPolicy Bypass -File scripts/dev.ps1
```

UI를 고칠 때는 설치된 앱(`dist\RapiLab\RapiLab.exe`)이 아니라 이 개발 서버로
확인하세요. 설치본은 빌드 시점의 프론트를 담고 있어서 변경을 보려면 매번 다시
빌드해야 하고, 실행 중인 앱은 자기 exe를 덮어쓸 수 없습니다.

테스트는 각자의 디렉터리에서 돌립니다. 백엔드는 리포 루트에서 실행하면
`No module named 'app'`으로 수집에 실패합니다.

```bash
cd backend && python -m pytest -q
cd frontend && npm test -- --run
```

## 문서

설계 판단과 엔진의 함정은 `docs/`에 정리되어 있습니다.

| 파일 | 내용 |
|---|---|
| `docs/roadmap.md` | 단계별 진행 상황과 남은 할 일 |
| `docs/decisions.md` | 실제로 선택지가 있었던 결정들과 그 이유 |
| `docs/insights.md` | 엔진 함정과 재사용 가능한 패턴 |
| `docs/engine-gaps.md` | 아직 표현하지 못하는 게임 메커니즘 목록 |
| `docs/measurements/` | 인게임 프레임 단위 실측값 (엔진 상수의 근거) |

## 감사

- 게임 데이터는 [blablalink](https://www.blablalink.com)의 ShiftyPad ·
  [lootandwaifus](https://lootandwaifus.com) · [dotgg](https://dotgg.gg)의
  공개 데이터를 사용합니다.
- 데미지 공식은 [nikke.gg](https://nikke.gg)의 정리를 따릅니다.

이 프로젝트는 SHIFT UP · Level Infinite과 무관한 팬 제작물입니다.
게임 내 명칭과 자산의 권리는 원저작자에게 있습니다.

## 라이선스

[MIT](LICENSE)
