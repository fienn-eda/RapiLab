# 신규 니케 출시 자동 탐지 — 운영 가이드

신규 니케가 출시되면 로스터 파이프라인이 **조용히 그 유닛을 버린다**(디렉토리 스냅샷에
없어 `roster_assembly.py`가 건너뛴다). 이 자동화는 매일 공개 디렉토리를 확인해 새 유닛을
알아채고, 온보딩할 때가 됐음을 Windows 토스트로 알린다.

- **설계 배경·근거:** `docs/superpowers/specs/2026-07-21-new-nikke-release-detection-design.md`
- **각 스크립트 상세 사용법:** 스크립트 최상단 help text가 권위 있는 출처다. 이 문서는
  운영 흐름과 문제 대응을 묶는다.

---

## 신호 모델 — 한 문장

**토스트가 뜨면 뭔가 일어난 것이고, 조용하면 아무 일도 없는 것이다.** 그게 전부다.
상태 파일이 없으므로 신규 유닛을 온보딩할 때까지 매일 같은 토스트가 반복된다 — 이는
미완료 작업에 대한 알림이며 의도된 동작이다. 스냅샷을 갱신하면 즉시 멈춘다.

토스트 종류는 둘뿐이다:

| 토스트 제목 | 뜻 | 해야 할 일 |
|---|---|---|
| **신규 니케 감지** | 새 SSR이 디렉토리에 나타남 | 아래 "온보딩" |
| **신규 니케 점검 실패** | 점검 자체가 실패함 | 아래 "점검 실패 대응" |

종료 코드(수동 실행 시): `0` 신규 없음 · `1` 신규 SSR 있음 · `2` 점검 실패.

---

## 설치 (1회, 메인 체크아웃에서)

작업 스케줄러에 등록하면 매일 19:00(KST)에 무인 실행된다.

```
powershell -ExecutionPolicy Bypass -File scripts/schedule_new_nikke_check.ps1 -Action register
powershell -ExecutionPolicy Bypass -File scripts/schedule_new_nikke_check.ps1 -Action status
```

- **반드시 메인 체크아웃에서 등록한다.** 작업은 실행된 디렉토리 경로에 고정되는데,
  워크트리(`.claude/worktrees/…`)는 일시적이라 삭제되면 작업이 깨진다.
- `status`는 등록 상태·마지막 실행 결과·다음 실행 시각을 보여준다. `LastTaskResult`는
  위 종료 코드와 같다(`0` 정상·무소식, `1` 신규 있음, `2` 실패).
- 해제: `-Action unregister`.

왜 목요일이 아니라 매일인가: 패치는 2~3주 간격 목요일이지만 지연·연장될 수 있어, 목요일
한정 실행은 최대 7일의 사각지대를 만든다. 매일 실행은 탐지 지연을 최대 하루로 줄이고,
무소식인 날의 비용은 페이지 한 번 로드다.

---

## 평상시

**아무것도 할 필요 없다.** 신규가 없으면 토스트가 안 뜨고 점검은 조용히 끝난다.

---

## "신규 니케 감지" 토스트가 떴을 때 — 온보딩

토스트 본문에 새 SSR 이름이 실린다(3명 초과 시 앞 3명 + `외 N명`). 수동으로 점검을
한 번 돌리면(`python3 scripts/check_new_nikkes.py`) 콘솔에 온보딩 안내가 그대로 출력된다.

절차 (🔴만 사람이 직접, 나머지는 위임 가능):

1. **스냅샷 갱신** — `cd tools/collect-blablalink && node collect.js --directory --headless --deep`.
   `--deep`은 서브타입이 아직 없는 신규 유닛만 방문한다.
2. **데이터 수집** — `/collect-nikke <이름>`. 무기 스텁까지 생성된다.
3. 🔴 **무기 스탯 수동 입력** — dotgg가 2026-05에 멈춰 신규 유닛은 API에 없다. 생성된
   스텁의 `_todo`를 인게임/나무위키 값으로 채운다(MG·SMG·AR·SG 3개, RL·SR 5개).
   채우지 않으면 로더가 유닛을 **안전하게 제외**한다(틀린 값이 들어가지 않는다).
4. 🔴 **인코딩 판단 승인 1회** — `nikke-skill-encoding` 스킬이 애매한 항목을 한 번에
   모아 제시한다.
5. **슬러그 맵 등록** — 손댈 필요 없다. 인코딩 시작과 동시에
   `test_resource_id_slug_map.py`가 실패하므로 건너뛸 수 없다.
6. 🔴 **커밋·병합**.

온보딩을 마치고 갱신된 스냅샷을 커밋하면 그 유닛에 대한 토스트가 멈춘다.

> 스냅샷 갱신·수집·인코딩의 상세는 각각 `collect.js`의 help, `/collect-nikke` 명령,
> `nikke-skill-encoding` 스킬이 권위다. 위 목록은 순서와 사람이 개입하는 지점만 정리한 것이다.

---

## "신규 니케 점검 실패" 토스트가 떴을 때 — 점검 실패 대응

실패는 일부러 시끄럽게 만들었다. 조용히 죽으면 커버되고 있다고 믿는데 실제로는 아무 일도
안 일어나는, 자동화가 없는 것보다 나쁜 상태가 되기 때문이다.

**1. 원인을 읽는다.** 토스트 본문 첫 줄에 오류 요약이 실린다. 전체 메시지는:

```
data/cache/new-nikke-check/last-run.log
```

이 파일은 **마지막 실행분만** 담고 매번 덮어쓴다. 신호가 아니라 원인을 읽기 위한
디버깅 보조물이다.

**2. 흔한 원인별 대응:**

- **`no Chrome/Edge executable found; set CHROME_PATH. Tried: …`**
  헤드리스로 띄울 브라우저를 못 찾았다. Chrome을 설치하거나, 환경변수 `CHROME_PATH`를
  실제 `chrome.exe`(또는 `msedge.exe`) 경로로 지정한다.
  **주의:** `CHROME_PATH`는 *가장 먼저 시도*할 뿐이며, 그 경로에 파일이 없으면 알려진
  기본 경로 목록으로 폴백한다(덮어쓰기가 아니다). 즉 오타 난 경로는 오류를 내지 않고
  조용히 무시되니, 지정할 때 **존재하는 파일**을 가리키는지 확인한다.

- **디렉토리를 네트워크 트래픽에서 못 봄 / blablalink 접속 실패**
  일시적 네트워크 문제일 수 있으니 먼저 수동 재실행으로 재현되는지 본다(아래 3). blablalink
  CDN 응답 구조가 바뀌었다면 `collect.js`의 `collectDirectory`(응답을 엿봐 디렉토리 JSON을
  식별하는 로직)가 갱신되어야 한다.

- **작업은 도는데 python3를 못 찾음**
  스케줄 작업은 `python3.exe`(anaconda)를 절대 경로로 등록한다. 그 인터프리터가 옮겨졌다면
  `-Action unregister` 후 다시 `-Action register`로 재등록한다.

**3. 수동으로 재현·확인:**

```
python3 scripts/check_new_nikkes.py            # 실제 점검 (토스트까지)
python3 scripts/check_new_nikkes.py --dry-run  # 토스트 없이 결과만 출력
```

`--dry-run`은 성공·실패 어느 경로에서도 토스트를 띄우지 않으므로 원인 조사에 안전하다.

---

## 참고: 오프라인 비교

이미 받아둔 디렉토리 덤프 파일을 네트워크 없이 커밋된 스냅샷과 비교한다. 네트워크 단계를
건너뛰므로 비교 로직만 확인하고 싶을 때 쓴다.

```
python3 scripts/check_new_nikkes.py --offline <path-to-directory.json>
```

---

## 불변식 — 이것들은 항상 참이다

- **점검은 리포지토리를 절대 수정하지 않는다.** 신선한 덤프는 `data/cache/new-nikke-check/`
  (gitignore됨)에만 쓴다. 커밋된 `tools/collect-blablalink/nikke-directory.json` 갱신은
  온보딩 때 사람이 의도적으로 하는 단계다 — 자동으로 하지 않는 이유는 병렬 세션·
  워크트리와 충돌하기 때문이다.
- **디렉토리 조회는 계정이 필요 없다.** 공개 게임 데이터라 헤드리스로 로그인 없이 받는다.
- 인터프리터는 `python3`(anaconda)다. 이 머신의 맨 `python`은 pytest도 없는 다른 설치본이다.

---

## 참조

| 무엇 | 어디 |
|---|---|
| 설계 근거·의사결정 | `docs/superpowers/specs/2026-07-21-new-nikke-release-detection-design.md` |
| 구현 계획·태스크 | `docs/superpowers/plans/2026-07-21-new-nikke-release-detection.md` |
| 점검 본체 사용법·종료 코드 | `scripts/check_new_nikkes.py` (docstring) |
| 스케줄 등록/해제/상태 | `scripts/schedule_new_nikke_check.ps1` (help) |
| 토스트 헬퍼 | `scripts/notify_toast.ps1` (help) |
| 온보딩 상세 (수집·인코딩) | `/collect-nikke` 명령 · `nikke-skill-encoding` 스킬 |
