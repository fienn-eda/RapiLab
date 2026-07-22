# 무기 + 기본스킬 데이터 ShiftyPad 전환

- 날짜: 2026-07-21
- 상태: 설계 확정 (구현 대기)
- 관련: `docs/superpowers/specs/2026-07-21-new-nikke-release-detection-design.md`
  (후속 절 "무기 스탯을 ShiftyPad에서 얻을 수 있다"에서 근거 실측)

신규 니케 온보딩에서 사람이 직접 하는 가장 큰 수작업 — dotgg 사망(2026-05) 이후 유닛마다
발생하는 **무기 스탯 5개 손입력** — 을 없앤다. ShiftyPad는 무기와 기본 스킬을 한 번의
페이지 fetch로 1차 데이터로 제공한다(탐지 작업에서 실측: 무기 30/30, 스킬 230/230 일치).

## 범위 — go-forward

**앞으로 온보딩하는 신규 유닛만** ShiftyPad에서 무기+스킬을 받는다. 기존 71유닛은 현재
데이터(dotgg/lootandwaifus)를 그대로 유지한다. 전수 백필은 하지 않는다 — 핵심 고통은
신규 유닛의 수동 입력이고, 백필은 처리량·churn 대비 이득이 작다.

---

## 핵심 아키텍처 — ShiftyPad를 "dotgg 모양"으로 정규화

각 유닛의 skill_rules 모듈은 `SKILL_VALUE_MANIFESTS`에 `source`·`keys`를 선언하는데,
`keys`가 `("skills", 0)`처럼 **소스 데이터의 모양에 묶여** 있다. 그리고 dotgg 파일 하나가
무기 6필드·`element`·`burst`·스킬 레벨 사다리를 모두 담는다(실측: Rapi dotgg 파일에
`weapon`/`maxAmmo`/`damage`="5.57%"/`reloadTime`/`chargeTime`/`chargeDamage`,
`element`="Fire", `burst`=3, `skills[2].cooldown`=40).

따라서 **ShiftyPad 페이로드를 dotgg와 같은 모양의 파일로 변환**하면 그 아래 파싱 —
스킬 슬롯 추출(`dotgg_slots`), 무기 스탯(`_weapon_stats`), 메타(element/burst/weapon/
cooldown) — 이 **전부 기존 코드 그대로 재사용**된다. 새 코드는 변환기와 얇은 배선뿐이며,
`source: "shiftypad"` 유닛의 manifest는 dotgg 유닛과 **동일한 모양**을 갖는다.

---

## 구성 요소

### ① 수집 — `collect.js` 유닛 상세 모드 (JS, 원시 덤프만)

한 유닛의 ShiftyPad 캐릭터 상세 페이로드를 헤드리스로 받아 **원시 그대로** 저장한다.
탐지 작업에서 검증한 경로를 쓴다: 상세 페이로드의 `shot_detail`(무기)과
`skill1_detail`/`skill2_detail`/`ulti_skill_detail`(스킬), 그리고 디렉토리 항목의
`shot_id.weapon_type`·`element_id.element.element`·`use_burst_skill`(메타).

- 입력: 유닛의 `resource_id`(또는 디렉토리로 해소되는 이름). `collect.js`는 이미 헤드리스
  기동과 디렉토리 해소를 갖고 있어(`--headless`, 탐지 작업), 이를 재사용한다.
- 출력: `data/shiftypad/raw/<resource_id>.json` — 원시 페이로드. 네트워크 단계라 변환은
  하지 않고 단위 테스트도 하지 않는다.
- 로그인 불필요(공개 게임 데이터, 탐지 작업에서 확인).

### ② 정규화기 — Python 순수 함수 (변환의 유일한 리스크 표면)

원시 ShiftyPad 페이로드 → dotgg 모양 JSON. **커밋된 픽스처로 단위 테스트**한다.

변환 규칙:
- **무기 6필드** ← `shot_detail`, dotgg의 고정소수점 관례로: `damage`(`6130`→`"61.3%"`),
  `max_ammo`(정수 그대로), `reload_time`/`charge_time`(÷100), `full_charge_damage`
  (`25000`→`"250%"`). `weapon`(타입)은 디렉토리 `shot_id.weapon_type`.
- **스킬 레벨 사다리** ← `description_value_list`. ShiftyPad는 `슬롯[레벨]`, dotgg는
  `levels[레벨][슬롯]` — **전치**하여 `levels: [{description_value_01: …, …}, …]` 생성.
  스킬 순서는 skill1 → skill2 → ulti로 dotgg의 `skills[0..2]`에 대응.
- **버스트 쿨다운** ← `ulti_skill_detail.skill_cooltime` ÷ 100(실측: Rapi 4000→40,
  dotgg `skills[2].cooldown`=40과 일치). `skills[2].cooldown`에 기록.
- **메타** ← 디렉토리: `element`, `burst`(=`use_burst_skill`의 Step 번호), `weapon`.
- 출력: `data/shiftypad/<slug>.json`. `resource_id`→slug는 `resourceIdSlugMap.ts`를
  파싱해 해소한다(`test_resource_id_slug_map.py`가 이미 Python에서 이 파일을 파싱하는
  관례를 쓴다).

정규화기가 이 전환의 **유일한 정확성 리스크**다. 수집(JS)은 dumb하게 원시만 덤프하고,
정규화(Python 순수 함수)는 픽스처로 검증한다 — `check_new_nikkes`의 순수로직/`--offline`,
`check_skill_value_drift`의 분리와 같은 관례.

### ③ 로더 배선 (작음)

- `load_character_data`: `source == "shiftypad"` → `data/shiftypad/<slug>.json` 경로 추가.
- `assemble_skill_values`: shiftypad를 dotgg와 같은 native-slot 경로로 처리
  (`source in ("dotgg", "shiftypad")`).
- 무기 스탯은 `user_roster.load_nikke_spec`이 현재 dotgg에서 읽는 것을, shiftypad
  소스 유닛에 한해 shiftypad 파일에서 읽도록 분기. `_weapon_stats`·메타 로직·
  `get_weapon_profile_override` 경로는 **변경 없이 그대로** 통과한다.

### ④ 패리티 하니스 — 백필 없이 파서를 넓게 증명

dotgg 정답지를 가진 기존 유닛들에 대해, 그들의 ShiftyPad 원시 페이로드를 정규화기에
돌려 **커밋된 dotgg 파일과 필드 단위로 일치**하는지 단언한다.

- **hermetic pytest + 커밋된 원시 픽스처.** 정규화기가 순수 함수라 네트워크 없이 돈다.
- **픽스처 범위: 구조 커버리지 중심 선별.** 파서 로직은 유닛마다 같고(같은 전치·÷100),
  변형은 **구조**에서 온다 — 충전 무기(RL·SR) vs 탄창 무기, 슬롯 수, 빈 슬롯. 6개 무기
  타입 각 최소 1유닛 + 스킬 슬롯 구조 다양성을 덮는 ~10–15유닛을 픽스처로 커밋한다.
  이것이 파서를 구조적으로 증명하고, 미검증이던 쿨다운 단위·전 무기타입·전치를 한 번에
  검증한다.
- **선택적 라이브 전수 스윕:** `check_skill_value_drift`처럼 라이브로 전 유닛을 재수집해
  대조하는 스크립트를 별도로 두어, 커밋 픽스처 밖의 유닛에서 예기치 못한 편차가 없는지
  가끔 확인한다(hermetic 테스트가 아니라 유지보수 도구).

---

## 받아들이는 한계 — dollskills / 시그니처 무기

ShiftyPad는 dollskills(시그니처 무기 스킬)를 노출하지 않는다(탐지 작업에서 실측: Julia의
상세 페이로드에 없고, 페이지의 16개 페이로드 어디에도 텍스트 없음). dollskills는 확장
레벨이 아니라 효과가 다른 별개 스킬이라 유도도 불가능하다.

따라서 **신규 유닛이 시그니처 무기를 갖고 그 버전으로 인코딩하는 경우**엔 ShiftyPad만으론
부족하다. 그 부분은 기존 9유닛(drake·helm·julia·laplace·miranda·moran·privaty·tove·
zwei)과 같은 취급 — 기존 소스/수동 입력. **기본 무기 + 기본 스킬은 ShiftyPad가 담당**하고,
시그니처 부분만 예외다. 인코딩 워크플로가 이미 시그니처 무기 사용 여부를 Fienn에게 묻는다.
이 한계는 문서로 남긴다(자동화 시도 안 함 — YAGNI).

---

## 온보딩 통합

`docs/new-nikke-detection.md`의 온보딩 절차와 `/collect-nikke` 경로를 갱신한다:

- 신규 유닛(비-시그니처): ShiftyPad 수집 → 정규화 → `source: "shiftypad"` manifest.
  **무기 스텁 수동 입력(🔴 #3)이 사라진다.**
- dotgg/lootandwaifus 수집은 dollskills(시그니처) 유닛에만 남는다.

---

## 테스트

- **정규화기(단위):** 커밋된 원시 픽스처에 대해 무기 6필드·스킬 전치·쿨다운·메타 각각을
  단언. 충전/탄창 무기, 빈 슬롯을 포함.
- **패리티(hermetic pytest):** 선별 픽스처에서 정규화기 출력이 커밋된 dotgg 파일과
  필드 단위로 동일. 이것이 파서의 구조적 정확성을 증명하는 핵심 게이트.
- **로더 통합:** `source: "shiftypad"` 유닛이 `load_nikke_spec`을 통과해 무기 스탯·스킬
  값·메타를 올바르게 산출. 값 없음/필드 부족 시 유닛이 안전하게 제외되는지(현행 계약 유지).
- **회귀:** 기존 dotgg/lootandwaifus 소스 유닛의 로딩·시뮬 결과 불변(백엔드 전체 스위트).
- 라이브 수집·전수 스윕은 단위 테스트하지 않는다(외부 사이트 의존).

---

## 범위 밖

- 기존 71유닛의 ShiftyPad 백필 — go-forward 결정에 따라 제외.
- dollskills/시그니처 무기 자동화 — 구조적으로 불가(위 한계).
- lootandwaifus/dotgg 수집 경로 제거 — dollskills 유닛에 아직 필요하므로 남긴다.
- 애장품(favorite item) 데이터 — 엔진이 현재 모델링하지 않음.
