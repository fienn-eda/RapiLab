# 신규 니케 출시 대응 — 자동 탐지 루틴

- 날짜: 2026-07-21
- 상태: 설계 확정 (구현 대기)
- 관련: `docs/roadmap.md` To-Do "디렉토리 스냅샷 갱신 루틴"

신규 니케가 출시되면 동기화와 시뮬레이션에 포함되기까지의 과정을 성립시킨다.
조사 결과 **온보딩 체인의 거의 전부가 이미 갖춰져 있고, 비어 있는 것은 탐지 하나**였다.
이 스펙은 탐지만 다룬다.

---

## 왜 탐지만인가 — 기존 커버리지 실측

| 단계 | 담당 | 상태 |
|---|---|---|
| 신규 출시 인지 | — | **없음** |
| 스킬 데이터 수집 | `/collect-nikke` (nikke-data-collector) | 있음 |
| 무기 스탯 (dotgg 중단분) | `collect_dotgg_weapons.py --stub` | 있음 |
| 스킬 인코딩 | `nikke-skill-encoding` 스킬 | 있음 |
| `resourceIdSlugMap` 등록 | `test_resource_id_slug_map.py` | **테스트가 강제** |
| resource_id 정합성 | `test_resource_id_directory.py` | 있음 |
| 밸런스 패치 드리프트 | `check_skill_value_drift.py` | 있음 |

인코딩을 시작하는 순간 슬러그 맵 테스트가 빨개지므로 등록 단계는 건너뛸 수 없다.
따라서 **온보딩 절차 문서를 새로 쓰지 않는다** — 기존 스킬·스크립트와 두 벌이 되어
갈라진다. 탐지 스크립트의 출력이 다음 단계를 가리키는 역할을 한다.

## 지금의 실패 모드

신규 니케는 `roster_assembly.py:138`의 `continue`에서 **완전히 조용히** 버려진다.
디렉토리 스냅샷에 없으므로 `rosterImport.ts:71`의 "미지원 유닛" 경고에 이름이 오를
기회조차 없다. 유일한 신호는 `api.py:192`의 `unknown_name_codes` 로그 카운터인데,
로컬 실행이라 **아무도 보지 않는다.** 신호가 없는 것이 아니라 닿지 않는 곳에 있다.

또한 이 탐지는 **보유 여부와 무관해야 한다**(Fienn). 로그 카운터는 소유한 유닛만
세므로 그 요구를 원리적으로 만족하지 못한다.

---

## 검증한 사실 (2026-07-21, 실측)

설계의 하중을 받는 가정 두 개를 추정하지 않고 직접 확인했다.

**① 디렉토리는 로그인 없이, 자체 헤드리스 Chrome으로 받을 수 있다.**
`collect.js`는 CDN 파일명이 해시라 회전하기 때문에 네트워크 응답을 엿보는데,
이는 인증이 아니라 URL 발견 때문이다(코드 주석: "this mode needs no account at all").
시스템 Chrome을 `playwright-core`로 직접 띄워 `https://www.blablalink.com/shiftyspad/nikke?nikke=16`
을 열고 **194개 엔트리를 그대로 캡처**했다. 로그인 세션도 CDP 부착도 필요 없었다.

**② WinRT 토스트가 이 머신에서 실제로 화면에 뜬다.**
`BurntToast` 모듈은 미설치이나 `Windows.UI.Notifications.ToastNotificationManager`가
로드되고, PowerShell AUMID로 발사한 프로브 토스트를 Fienn이 육안 확인했다.
추가 의존성이 필요 없다.

부수 확인: 커밋된 스냅샷도 194개 → **현재 미탐지 신규 니케 없음.** 스냅샷은 최신이다.
머신 시간대는 KST이므로 로컬 시각이 곧 한국 시각이다.

---

## 구성 요소

### ① `collect.js --headless`

`--directory` 모드에 한해 CDP 부착 대신 자체 Chrome을 띄운다. 로스터 수집 모드는
로그인 세션이 필요하므로 **`connectOverCDP`를 그대로 유지**한다. `--headless`를
`--directory` 없이 준 경우는 오류로 거부한다.

Chrome 실행 파일은 알려진 경로 목록을 순서대로 시도하고, 환경변수 `CHROME_PATH`가
있으면 그것을 우선한다. 어디서도 찾지 못하면 **찾아본 경로를 모두 나열하며 실패**한다
(조용한 실패 금지).

### ①-b `corporation_sub_type` 유실 수정 — 갱신 경로의 선결 조건

`trimDirectory`는 필드 6개짜리 객체를 새로 만들며 `corporation_sub_type`을 포함하지
않는다. 이 필드는 돌파 코어당 flat ATK를 결정해 스탯 계산기가 사용하고, 현재 스냅샷의
**27/194 엔트리**에 들어 있다. 따라서 `--deep` 없이 `--directory`를 돌리면 **27개 유닛의
값이 조용히 사라지고 ATK가 틀어진다.**

`collect.js:219`의 주석은 "the field is otherwise carried over from the previous one"
이라고 주장하지만 **그런 코드는 존재하지 않는다** — `collect.js`는 이전 스냅샷을 읽지
않는다(`readFileSync`/`existsSync` 없음). 주석이 사실과 다르다.

이 루틴이 반드시 지나가는 길목이므로 함께 고친다:

- 순수 함수를 `tools/collect-blablalink/directory.js`로 분리해 export한다
  (`parse.js` / `parse.test.js` 쌍의 기존 관례). `collect.js`는 이를 require하는
  오케스트레이터로 남는다.
  - `trimDirectory(raw)` — 현재 로직 그대로.
  - `carryOverSubTypes(entries, previous)` — 이전 스냅샷을 `resource_id`로 색인해
    `corporation_sub_type`을 승계. 이전 스냅샷이 없으면 그대로 통과.
- `--directory`는 기존 스냅샷이 있으면 읽어 승계한 뒤 기록한다.
- `--deep`은 **승계로 값이 채워지지 않은 `resource_id`에만** 페이지를 연다. 신규 유닛만
  방문하므로 갱신이 194페이지에서 신규 몇 건으로 줄어든다.
- 사실과 다른 주석을 실제 동작에 맞게 고친다.

테스트(`tools/collect-blablalink/directory.test.js`, `node --test`):
승계됨 / 이전 스냅샷 없음 / 이전에 없던 신규 `resource_id`는 값이 비어 `--deep` 대상이
됨 / 이전 값이 `null`인 엔트리도 결정된 값으로 승계되어 `--deep` 대상에서 빠짐(`null`은
"방문했고 sub type이 없다"는 확정 답이지, 미확인이 아니다 — 두 헬퍼 모두 값의 참/거짓이
아니라 필드의 존재 여부로 판단한다).

### ② `scripts/check_new_nikkes.py` — 본체

`collect.js --directory --headless`를 스크래치 경로에 실행시킨 뒤, 커밋된
`tools/collect-blablalink/nikke-directory.json`과 `resource_id` 기준으로 비교한다.

- 스크래치 경로: `data/cache/new-nikke-check/` (`.gitignore`에 `data/cache/` 존재)
- **리포지토리를 수정하지 않는다.** 커밋된 스냅샷 자동 갱신은 하지 않는다 — 병렬
  세션·워크트리와 충돌하고, 갱신은 온보딩 시 diff를 보며 의도적으로 해야 한다.
- 신규 항목마다 `resource_id` / `name_en` / `class` / `corporation` / `original_rare`
  출력. (`element`는 스냅샷에 없다 — `trimDirectory`가 남기는 필드는 `resource_id` ·
  `name_code` · `name_en` · `original_rare` · `class` · `corporation`뿐이며, 원소는
  RAW 페이로드에만 있다.)
- **토스트는 신규 SSR이 있을 때만** 띄운다. 레이드는 SSR 전용이며
  (`roster_assembly.py`가 같은 기준으로 필터) 신규 R/SR은 오탐이 된다. 비SSR 신규는
  로그에만 남긴다.

종료 코드: `0` 신규 없음 · `1` 신규 SSR 있음 · `2` 실패.

작업 스케줄러의 실행 기록은 0이 아닌 종료 코드를 실패처럼 표시하지만, 이 작업의
신호는 토스트이지 스케줄러 UI가 아니므로 그대로 둔다. 코드를 구분해 두면 사람이
수동 실행했을 때 "신규 있음"과 "점검 실패"를 즉시 가를 수 있고, 그쪽 가치가 더 크다.

플래그:
- `--offline <path>` — 네트워크 단계를 건너뛰고 주어진 파일을 커밋된 스냅샷과 비교.
  비교 로직을 테스트 가능하게 만드는 경로이며 `check_skill_value_drift.py`의 동명
  플래그와 같은 관례다.
- `--dry-run` — 토스트를 띄우지 않고 띄웠을 내용을 출력.

### ③ `scripts/notify_toast.ps1` — 토스트 헬퍼

제목과 본문을 인자로 받아 WinRT로 토스트를 발사한다. 발견 시와 **실패 시** 모두 호출.

토스트 본문 규칙: 신규 SSR의 `name_en`을 쉼표로 나열하되 3명을 넘으면 앞 3명과
`외 N명`으로 줄인다(토스트는 긴 본문을 잘라내므로). 실패 시에는 오류 메시지의 첫 줄을
싣는다 — 무엇이 실패했는지 로그를 열지 않고도 알 수 있어야 한다.

### ④ 작업 스케줄러 등록 스크립트

등록·해제·상태 확인과 help text를 갖춘 스크립트로 제공한다(한 번 하는 일이라도
스크립트로 — CLAUDE.md). 작업은 **메인 체크아웃 경로**를 대상으로 등록한다(워크트리는
일시적이다).

---

## 실행 주기: 매일 19:00 (KST)

패치는 2~3주 간격 목요일 15시 또는 18시 완료(Fienn). 목요일 19시로 한정하면 점검이
지연·연장될 때 **다음 실행까지 7일의 사각지대**가 생긴다. 매일 19시로 두면 그 사각지대가
사라지고 탐지 지연은 최대 하루이며, 패치가 없는 날의 비용은 페이지 한 번 로드다.
무소식이면 토스트가 없으므로 알림 피로가 쌓이지 않는다.

## 신규가 온보딩될 때까지 매일 토스트가 뜬다 — 의도된 동작

상태 파일을 두지 않으므로, 신규 SSR이 남아 있는 한 매일 토스트가 반복된다. 이는
**미완료 작업에 대한 지속적 알림**이며, 온보딩을 마치고 스냅샷을 갱신하면 즉시 멈춘다.
"이미 알린 것은 침묵" 방식은 상태 파일이 필요하고, 그 한 번의 토스트를 놓치면 신호가
영구히 사라진다. 패치 간격이 2~3주라 반복 기간은 온보딩까지의 며칠로 한정된다.

## 실패는 반드시 시끄럽게

네트워크 장애, Chrome 부재, CDN 응답 구조 변경 등 어떤 실패든 토스트를 띄우고 종료
코드 `2`로 끝낸다. 조용히 죽으면 **Fienn은 커버되고 있다고 믿는데 실제로는 아무 일도
일어나지 않는 상태**가 되며, 이는 자동화가 없는 것보다 나쁘다.

진단을 위해 마지막 실행의 로그만 `data/cache/new-nikke-check/last-run.log`에 덮어쓴다.
이것은 신호가 아니라 실패 원인을 읽기 위한 디버깅 보조물이다(신호는 토스트다).

---

## 탐지 이후 — 사람이 하는 일

이 스펙은 탐지까지만 자동화한다. 토스트가 뜬 뒤의 경로는 다음과 같으며, 🔴만 Fienn이
직접 해야 하고 나머지는 위임 가능하다.

1. **스냅샷 갱신** — `node collect.js --directory --headless --deep`. ①-b 수정 후
   `--deep`은 신규 유닛만 방문한다.
2. **데이터 수집** — `/collect-nikke <이름>`. 무기 스텁까지 생성된다.
3. 🔴 **무기 스탯 수동 입력** — dotgg가 2026-05에 멈춰 신규 유닛은 API에 없다. 스텁의
   `_todo`를 인게임/나무위키 값으로 채운다. MG·SMG·AR·SG는 `maxAmmo`/`damage`/
   `reloadTime` 3개, RL·SR은 여기에 `chargeTime`/`chargeDamage`를 더한 5개.
   채우지 않으면 로더가 유닛을 **안전하게 제외**한다(틀린 값이 들어가지 않는다).
4. 🔴 **인코딩 판단 승인 1회** — `nikke-skill-encoding` 4단계가 애매한 항목을 한 번에
   모아 제시한다. 시그니처 무기(`dollskills`) 사용 여부도 같은 검토에 포함된다.
5. **슬러그 맵 등록** — 손댈 필요 없다. 인코딩 시작과 동시에
   `test_resource_id_slug_map.py`가 실패하므로 건너뛸 수 없다.
6. 🔴 **트렁크 머지** — 리모트가 없어 ff는 Fienn이 실행한다.

## 테스트

- **비교 로직**: 두 엔트리 목록에 대한 순수 함수. 픽스처로 신규 있음 / 없음 /
  신규가 비SSR뿐 / 동일 `resource_id`에 이름만 바뀐 경우를 각각 단언.
- **위치·관례**: `backend/tests/test_check_new_nikkes.py`에서
  `sys.path.insert(0, <repo>/scripts)` — `test_check_skill_value_drift.py`와
  `test_collect_dotgg_weapons.py`가 쓰는 기존 관례.
- **종료 코드**: 신규 SSR 있음 → `1`, 없음 → `0`을 `--offline`으로 단언.
- **토스트 억제**: `--dry-run`에서 토스트가 발사되지 않는지.
- 네트워크 수집 단계는 단위 테스트하지 않는다(외부 사이트 의존). `--offline`으로
  분리하는 이유가 이것이다.

## 범위 밖

- 커밋된 디렉토리 스냅샷의 자동 갱신 — 온보딩 시 수동, 의도적으로.
- 데이터 자동 수집·자동 인코딩 — 판단이 필요하며 `/collect-nikke`와
  `nikke-skill-encoding`이 이미 담당한다.
- 디렉토리에서 **사라진** 엔트리 탐지 — 실제로 일어나지 않으며 대응 절차도 없다.
- 밸런스 패치 드리프트 — `check_skill_value_drift.py`가 담당한다. 패치일에 함께
  일어나는 일이지만 전 유닛의 lootandwaifus 페이지를 재수집하므로 매일 돌리기엔 비싸다.
- **무기 스탯의 ShiftyPad 전환 — 별도 스펙(바로 다음).** 아래 참조.

## 후속: 무기 스탯을 ShiftyPad에서 얻을 수 있다 (실측 확인)

이 스펙을 논의하던 중 확인한 사실이며, 다음 스펙의 근거로 여기 기록한다.

ShiftyPad의 캐릭터 상세 페이로드에는 `shot_detail` 블록이 있고, 엔진이 쓰는 무기 필드
다섯 개가 **모두** 고정소수점으로 들어 있다(÷100이 dotgg 값):
`max_ammo` · `damage` · `reload_time` · `charge_time` · `full_charge_damage`.

**6개 무기 타입(SG·MG·RL·SMG·SR·AR) 각 1유닛, 30개 필드 전수 대조에서 불일치 0건.**
탄창형 무기의 `chargeTime 0` / `chargeDamage 100%` 관례까지 그대로 재현된다.
로그인 없이 헤드리스로, 이 루틴이 어차피 여는 페이지에서 얻어진다.

의미: dotgg가 2026-05에 멈춰 **신규 니케마다 영구히 발생하던 수동 입력(위 3번)이
제거 가능**하며, 출처가 스크랩에서 1차 게임 데이터로 바뀐다.

이번 스펙에 넣지 않는 이유: 이는 탐지 도구가 아니라 **엔진 무기 로딩 경로의 데이터
소스 마이그레이션**이다(`skill_values`의 dotgg 경로, 기존 유닛 백필 여부). 섞으면 양쪽
모두 리뷰가 어려워진다.

다음 스펙이 반드시 확인해야 할 미검증 항목:
- 전체 유닛 전수 대조(현재 6유닛만).
- **시그니처 무기(`dollskills`) 유닛에서 `shot_detail`이 기본 무기 기준인지 시그니처
  반영인지.** dotgg 파일이 기본 무기 기준이라 동등할 가능성이 높으나 확인하지 않았다.

부수로 `shot_detail`은 엔진이 현재 쓰지 않는 `shot_count` / `rate_of_fire` /
`core_damage_rate` / `burst_energy_pershot`도 담고 있다.

### 스킬 데이터도 같은 페이로드에 있다 (실측 확인)

같은 캐릭터 상세 페이로드의 `skill1_detail` / `skill2_detail` / `ulti_skill_detail`이
담고 있는 것:

- **영문** 스킬명(`name_localkey`)과 설명(`description_localkey`) — Fienn의 브라우저
  언어가 한국어인데도 영문으로 내려온다.
- `{description_value_NN}` 플레이스홀더와 `<word_group=...>` 마크업 — dotgg와 같은
  템플릿 구조.
- **전 레벨 값 사다리**: `description_value_list[슬롯].description_value`가 레벨 1~10의
  값 배열. 레코드의 `skill_level`은 1이지만 사다리는 전 레벨을 담는다(하모니 큐브
  테이블과 같은 인코딩).

**Rapi: Red Hood 3개 스킬 × 전 슬롯 × 전 10레벨 = 230개 값 대조, 불일치 0건.**
dotgg는 `levels[레벨][슬롯]`, ShiftyPad는 `슬롯[레벨]`로 **전치 관계**다.

즉 ShiftyPad는 무기뿐 아니라 **스킬까지 포함해 dotgg와 lootandwaifus 양쪽을 대체할 수
있는 1차 소스**다. 다음 스펙의 범위는 이에 맞춰 정한다.

**`dollskills`는 ShiftyPad에 없다 (실측 확인).** dollskills를 가진 9유닛 중
Julia(`resource_id` 150)로 확인했다: 캐릭터 상세 페이로드의 키 집합이 dollskills가 없는
Ada와 **61개로 완전히 동일**하고, 페이지가 싣는 **16개 페이로드 전문을 검색해도**
dollskill 설명 텍스트가 없다. 탭 클릭으로도 새 페이로드가 발생하지 않았다(16 → 16).

이것이 중요한 이유는 dollskills가 확장 레벨이 아니라 **효과가 다른 별개 스킬**이기
때문이다. Julia 기준 세 스킬 모두 설명과 슬롯 의미가 다르다(스킬2 "마지막 탄 명중 시"
→ "크리티컬 N회 후", 스킬3 "DEF 최고 적" → "무작위 적"). 값 사다리로 유도할 수 없다.

따라서 ShiftyPad로 전환하더라도 **dollskills를 쓰는 9유닛
(drake · helm · julia · laplace · miranda · moran · privaty · tove · zwei)에는
기존 소스가 계속 필요하다.** 다음 스펙은 전면 대체가 아니라 이 예외를 남기는 전환으로
설계해야 한다.

참고: 애장품 스탯 테이블 자체는 blablalink CDN에 있고 `data/blablalink-cdn/NOTES.md`에
URL이 기록돼 있으나, 이는 `atk`/`hp`/`level1`/`level2` 사다리이지 dollskill 설명이
아니며 **한국어**다(캐릭터 스킬이 영문인 것과 대조적).

추가 미검증 항목:
- 스킬 대조는 1유닛(Rapi: Red Hood)만. 전수 대조 필요.
- `skill_cooltime`(예: 4000)과 dotgg `cooldown`의 단위 대응 미확인.
- 설명의 `<word_group=...>` 마크업과 선두 아이콘 문자 파싱 필요.
- 애장품(favorite item) 탭은 조사하지 않았다. 엔진이 현재 모델링하지 않는다.
