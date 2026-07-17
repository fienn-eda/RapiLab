# Phase A — ExiaInvasion 로스터 JSON 임포터 설계

- 날짜: 2026-07-18
- 상태: 설계 승인 대기 → (승인 후) writing-plans
- 브랜치: `wip/roster-import`
- 상위 맥락: `C:\Users\fienn\.claude\plans\phase-7-sprightly-manatee.md` (Phase 7 재정의) 의
  **"Phase A — ExiaInvasion JSON 임포터"**

---

## 1. 목표와 배경

Fienn의 고통은 **초기 입력 분량(로더블 56명 × 약 35필드 ≈ 2,000값)과 스펙업마다의 재입력**이다.
Phase 7 정찰 결과 진짜 데이터 소스는 blablalink이고, 오픈소스 확장 **ExiaInvasion**이
blablalink 데이터를 JSON으로 export한다. 이 export 파일 하나를 우리 로스터로 **임포트**하는
것이 Phase A다.

**핵심 결정 (Path 1, Fienn 2026-07-18):** ATK 자동 계산은 하지 않고, export가 담은 필드
(오버로드·스킬·돌파·레벨)만 임포트한다. ATK/HP/DEF/큐브는 **수동 입력으로 남긴다**. ATK 자동화는
CDN 기초스탯 테이블 발견으로 디리스크된 **Phase B**로 분리한다(§10).

**임포터 위치 (Fienn 2026-07-18):** **프론트엔드 TypeScript**. Phase A는 네트워크 호출이 없는
순수 로컬 파일 파싱이고, 결과가 편집 가능한 draft로 떨어져 사용자가 ATK를 손으로 채우는 흐름을
유지해야 하므로 프론트가 맞다. 대가는 오버로드/슬러그 매핑을 TS에 두는 것(§6, §7).

---

## 2. 범위

**포함 (In):**
- ExiaInvasion export JSON 1개를 읽어 `NikkeDraft[]`로 매핑.
- `useRoster`에 **슬러그별 병합** setter 추가 + 파일 임포트 UI.
- 임포트 요약(임포트 N·신규 M·드롭된 오버로드 줄·미매칭 슬러그) 표시.

**제외 (Out):**
- ATK/HP/DEF 계산(→ Phase B). 임포트 후에도 수동 필드로 공란.
- 큐브(`pve_cube`): export가 캐릭터별 장착 큐브를 담지 않음(§4) → 수동.
- 애장품(소장품) 스탯: 표시 ATK에 이미 포함되어 수동 ATK에 반영됨. draft 필드로 만들지 않음(§9-근거).
- blablalink 라이브 API 호출·토큰·세션 자동화(폐기된 경로).
- 스킬레벨 >10(애장품 스킬강화): 엔진이 애초에 표현 못 함(`CONSTRAINTS.skill` max 10) — 기존 갭.

---

## 3. 소스 포맷 (실제 `FIENN.json`, 2026-07-18 실증)

최상위 오브젝트:

| 키 | 내용 | 사용 |
|---|---|---|
| `name` | 계정 이름 | 무시 |
| `game_uid` | 계정 식별자 | **읽지 않음(민감)** |
| `synchroLevel` | 계정 전역 싱크로 레벨 (예 663) | `level`의 소스 |
| `outpostLevel` | 전초기지 레벨 | 무시 |
| `cubes` | **계정 큐브 인벤토리**(장착 정보 아님) | 무시 |
| `elements` | 원소별(`Electronic/Fire/Wind/Water/Iron/Utility`) 캐릭터 배열 | **캐릭터 소스** |
| `cookie` | 게임 로그인 쿠키 | **절대 읽지 않음(자격증명)** |

`elements[<원소>]`는 캐릭터 배열. 캐릭터 객체 필드(합집합):
`id`, `name_cn`, `name_code`, `name_en`, `priority`, `resource_id`, `showStats`,
`skill1_level`, `skill2_level`, `skill_burst_level`, `item_level`, `item_rare`,
`limit_break{grade,core}`, `equipments{"0".."3"}`, `AtkElemLbScore`.

`equipments["0".."3"]` = 4개 장비 슬롯, 각 슬롯은 오버로드 줄 배열:
`{function_type, function_value, level}`.

**계획서(ExiaInvasion api.js 기반)와 다른 실측 4건:**
1. 캐릭터에 **장착 큐브 정보 없음** — `cubes`는 계정 인벤토리일 뿐. → 큐브 수동.
2. 최상위 `cookie`에 자격증명 → 픽스처·코드에서 절대 취급 안 함.
3. 오버로드에 `StatDef`(24건)·`StatAccuracyCircle`(31건) 흔함 → 미매핑=에러는 불가(§7).
4. 캐릭터 식별이 짧은 인게임 `name_en`("Ada"/"Jill"…) → 별칭표 필요(§6).

---

## 4. 필드 매핑 (`NikkeDraft` ← export 캐릭터)

`NikkeDraft`의 숫자 필드는 문자열 보관이므로 임포터도 문자열로 채운다.

| draft 필드 | 소스 | 비고 |
|---|---|---|
| `id` | `crypto.randomUUID()` (신규) 또는 병합 시 기존 유지 | §8 |
| `character_slug` | `name_en` → kebab + 별칭표(§6) | 미매칭은 그대로 통과 |
| `level` | 최상위 `synchroLevel` (전원 동일) | **inert**(딜 미반영), 개별 레벨 없음 |
| `core_level` | `limit_break.core` (없으면 0) | **inert**, grade는 별도 필드 없음(Phase B가 export에서 직접 읽음) |
| `skill_levels.skill1/2/burst` | `skill1_level`/`skill2_level`/`skill_burst_level` | 1–10 |
| `overload_options` | `equipments{0-3}`를 `function_type`별 합산 → 한글 7종(§7) | def/accuracy 드롭+warning |
| `hp`/`atk`/`def_` | (없음) → `''` | 수동, Phase A 기지의 갭 |
| `hasCube`/`pve_cube` | (없음) → `false`/공란 | 수동 |

**inert 확인:** `level`·`core_level`은 `models.py`의 필드 정의와 테스트에만 존재하고 어떤
`skill_rules`/스탯 조립에서도 소비되지 않는다. base_stats는 사용자가 입력한 hp/atk/def에서
직접 온다(`user_roster.py:74`). 따라서 두 값의 정확한 변환은 Phase A 딜 계산에 영향이 없고,
`ge` 제약을 만족하는 합리값이면 충분하다.

---

## 5. 예외/엣지

- `elements`가 없거나 오브젝트가 아니면 → 사용자향 에러("ExiaInvasion export 형식이 아님"), 크래시 없음.
- `equipments`가 없는 캐릭터(1건 관측) → 오버로드 빈 배열로 처리.
- `limit_break`가 `{grade:null,core:null}`(미보유 추정, 1건) → `core_level` 0.
- `name_en`이 비었거나 없으면 → 그 캐릭터 스킵 + warning.

---

## 6. 슬러그 해석

**전략:** `name_en`을 kebab으로 변환(소문자·`:`·`()` 제거·공백→`-`) → **별칭표**로 교정 →
레지스트리에 없어도 **그대로 통과**(하류 `excluded_slugs`가 미인코딩/미로더블을 보고).
백엔드 `dotgg_slug` 별칭 선례와 동일 패턴이나, 프론트 TS에 둔다(이 매핑은 export-이름→우리-슬러그로
`dotgg_slug`(우리-슬러그→dotgg-슬러그)와는 별개의 신규 매핑).

**별칭표(파생슬러그 → 교정슬러그), 9건 — export 75명 대조로 도출:**

```
rei                 → rei-ayanami
rei-tentative-name  → rei-ayanami-tentative-name
ada                 → ada-wong
jill                → jill-valentine
asuka-wille         → asuka-shikinami-langley-wille
soline              → soline-frost-ticket
marciana            → marciana-marine-study
takina              → takina-inoue
chisato             → chisato-nishikigi
```

**별칭 걸지 않음(다른 유닛이므로):** "Red Hood"(→`red-hood`, 미인코딩 — `rapi-red-hood`와 별개) ·
"Cinderella: Crystal Wave"(→`cinderella-crystal-wave`, 미인코딩 — `cinderella`와 별개).
이들은 통과 후 하류에서 제외된다.

자동변환 매치 51/75 + 별칭 9 → 인코딩 유닛 손실 없음. 나머지 15명은 미인코딩(정상적으로 제외).

**주의:** 별칭표·오버로드 매핑은 export 표본에서 도출된 것이라, 새 유닛이 추가되면 갱신이 필요할
수 있다. 미매칭 슬러그를 요약에 **시끄럽게 보고**해 이를 조기에 드러낸다.

---

## 7. 오버로드 매핑

각 캐릭터의 `equipments["0".."3"]`를 순회하며 `function_type`별로 `function_value`를 **합산**한 뒤,
영문 stat키를 백엔드 `overload_effects.py`의 **한글 7종**으로 매핑한다(draft의 overload row `name`은
백엔드 `NAME_TO_STAT`이 조회하는 값이므로 정확히 일치해야 함):

```
StatAtk            → 공격력 증가
IncElementDmg      → 우월코드 대미지 증가
StatCriticalDamage → 크리티컬 대미지 증가
StatCritical       → 크리티컬 확률 증가
StatChargeDamage   → 차지 대미지 증가
StatChargeTime     → 차지 속도 증가
StatAmmoLoad       → 최대 장탄 수 증가
```

합산값은 draft overload row의 `value`(문자열)로. (백엔드 `overload_effects`가 `value/100`을
적용하므로, ShiftyPad 표시 방식과 동일하게 `function_value` 그대로 합산해 넣는다.)

**미매핑 `function_type`(`StatDef`·`StatAccuracyCircle`) 처리 = 드롭 + warning.** 이 둘은 엔진에
소비처가 없고 실제 로스터에 빈번(합 55건)해 에러로 처리하면 임포트가 거의 항상 실패한다. 조용히
버리지 않고 요약에 "N개 오버로드 줄이 모델 미지원으로 제외됨(StatDef·StatAccuracyCircle)"로 보고한다.
(백엔드 `overload_effects`의 미지 이름=`ValueError`는 유지 — 그건 draft가 이미 7종만 담는다는 전제의
방어선이고, 임포터가 그 전제를 지킨다.)

---

## 8. 병합 의미론 — 슬러그별 병합

**근거:** Phase A에서 ATK·큐브가 수동으로 남고, 로스터는 localStorage로 영속화된다. 전체 교체를
하면 재임포트마다 손입력 ATK가 증발해 "스펙업마다 재입력"이라는 원래 고통이 재발한다. 스펙업에서
바뀌는 건 export가 담은 필드(오버로드·스킬·돌파)이므로 그것만 덮어쓰고 수동 필드는 보존한다.
(Phase B가 ATK를 자동화해도 병합은 안전 — 그때는 ATK도 import 필드로 덮일 뿐.)

`importDrafts(incoming: NikkeDraft[])`:
- 각 `incoming`에 대해 기존 draft 중 **같은 `character_slug`**가 있으면:
  - 덮어씀: `skill_levels`, `overload_options`, `core_level`, `level`.
  - 보존: `hp`, `atk`, `def_`, `hasCube`, `pve_cube`, 그리고 기존 `id`.
- 없으면 신규 추가(새 `id`).
- import에 없는 기존 draft는 **무변경**(사용자 손입력 유닛 보호).

---

## 9. 컴포넌트

**(a) 파서/매퍼 — 순수 함수, TDD 핵심.** (예: `frontend/src/lib/exiaImport.ts`)
```
parseExiaExport(raw: unknown): { drafts: NikkeDraft[]; warnings: ImportWarning[] }
```
React·I/O 없음. §3~§7을 구현. `warnings`는 드롭된 오버로드·스킵된 캐릭터·미매칭 슬러그를 담는다.

**(b) `useRoster` 병합 setter.** `frontend/src/hooks/useRoster.ts`에 `importDrafts` 추가(§8).
기존 공개 인터페이스(`drafts/addNikke/updateNikke/removeNikke`)는 불변 → 소비 컴포넌트 무영향.

**(c) 임포트 UI.** 폼 영역에 파일 입력(또는 붙여넣기) → `FileReader`/`JSON.parse` →
`parseExiaExport` → `importDrafts` → 요약 표시. 잘못된 JSON/형식은 사용자향 에러로.

**애장품 필드 미생성 근거:** 표시 ATK가 애장품 스탯을 **포함**(Fienn 확인 2026-07-18)하므로 수동
ATK에 이미 반영된다. `item_level`/`item_rare`를 draft 계약에 추가하면 아무도 안 읽는 필드가 되어
YAGNI 위반이고, Phase B는 어차피 export를 재임포트하며 직접 읽는다(§10).

---

## 10. 지연 / Phase B 입력 (의식적 보류, 기록)

Phase B(ATK 자동 계산)에 필요한 원재료가 blablalink CDN에서 제공됨을 2026-07-18 확인. **URL은
해시라 회전 가능 → 구조/필드로 기록**(URL 의존 금지).

- **캐릭터 기초 스탯표** (예: Rapi CDN): `character_level_attack_list`·`_hp_list`·`_defence_list`
  = 레벨 1–1200 기초값 배열 + `stat_enhance_detail{grade_*, core_*}`(돌파/코어 가산 계수) +
  `critical_ratio`/`critical_damage`/`class`.
- **큐브** CDN: `atk`/`hp`/`def` = 큐브 레벨 1–15 배열 + `harmonycube_skill_group`. → 큐브는 평면
  atk/hp/def에 기여(표시 ATK에 이미 포함 — 밑바닥 계산 시 **이중 계산 주의**).
- **소장품(애장품)** CDN: `atk`/`hp`/`def` = 아이템 레벨 0–15 배열 + `collection_skill_group_data`.

**Phase B 필수 입력 (export에서 재임포트 시 읽음):** `item_level`/`item_rare`(소장품 스탯),
`limit_break.grade`(돌파, Phase A `core_level`엔 안 담김), `synchroLevel`.

**Phase B 남은 발견거리(미해결):**
1. `name_code`(캐릭)·큐브·소장품 → **CDN 해시 매니페스트** 매핑(Fienn DevTools 추가 정찰 필요).
   Fienn 도메인 사실("기초 스탯은 클래스별 동일")이 맞다면 클래스 3종 표로 축소 가능 — 2번째
   캐릭 파일로 검증 필요.
2. 정확한 조립 공식(기초표[레벨] + grade + core + 소장품 + 큐브 + 오버로드%)을 ShiftyPad 표시
   ATK 1명치와 **1회 대조 검증**.
3. **export가 캐릭터별 장착 큐브를 담지 않음** — 큐브 자동화는 별도 소스(라이브 페이지가 아는
   장착 큐브)나 수동 유지 필요.

---

## 11. 에러 처리 요약

- 잘못된 JSON / `elements` 부재 → 사용자향 에러, 크래시 없음.
- 미매핑 오버로드(def/accuracy) → warning(에러 아님).
- 미매칭 슬러그 → 통과 + 요약 보고(하류 `excluded_slugs`가 제외).
- `cookie`·`game_uid` → 아예 읽지 않음.

---

## 12. 보안

- **`cookie`/`game_uid`는 코드가 읽지도, 저장하지도 않는다.** 파서는 매핑에 필요한 필드만 접근.
- **테스트 픽스처는 정제본:** 실제 `FIENN.json`에서 `cookie`·`game_uid`를 제거(또는 더미
  `"REDACTED"`)하고, 대표 4–5명으로 축소해 `frontend/src` 하위에 커밋. 원본 `data/FIENN.json`은
  gitignore된 `data/`에 남기고 커밋하지 않는다.

---

## 13. 테스트 (TDD, Vitest)

**픽스처(정제·축소):** 다음 케이스를 덮는 대표 캐릭터 구성 —
- 4슬롯 오버로드 + def/accuracy 줄 포함(합산·드롭+warning 검증).
- 오버로드 빈 캐릭터.
- 별칭 캐릭터("Ada" → `ada-wong`).
- 미인코딩 캐릭터("Naga") → 통과(하류 제외).
- `limit_break` null 엣지.
- 더미 `cookie`/`game_uid`(파서가 무시하는지 확인).

**케이스:**
- 최상위 형식 검증(정상 / `elements` 부재 / 비객체 / 깨진 JSON).
- 슬러그: 자동변환 · 별칭 9종 · 미매칭 통과.
- 오버로드: `function_type`별 4슬롯 합산 · 영문→한글 7종 · def/accuracy 드롭+warning.
- `synchroLevel` → 전원 `level`.
- 스킬 3필드 매핑 · `limit_break.core` → `core_level`.
- `hp/atk/def_` 공란 · 큐브 미설정.
- **병합**: 수동필드(atk/hp/def/cube) 보존 · import필드 덮어쓰기 · 신규 추가 · 미포함 기존 무변경 · `id` 유지.
- 보안: `cookie`/`game_uid`가 결과·저장 어디에도 안 나타남.

테스트는 네트워크·토큰 불요, 출력 pristine(CLAUDE.md).

---

## 14. 손대는 파일

| 파일 | 무엇을 |
|---|---|
| `frontend/src/lib/exiaImport.ts` (신규) | `parseExiaExport` 순수 파서/매퍼 + 슬러그·오버로드 매핑 |
| `frontend/src/lib/exiaImport.test.ts` (신규) | 위 테스트 |
| `frontend/src/hooks/useRoster.ts` | `importDrafts` 슬러그별 병합 setter |
| `frontend/src/hooks/useRoster.test.ts` | 병합 케이스 |
| 임포트 UI 컴포넌트 (신규 또는 기존 폼에 배치) | 파일 입력 → 파싱 → 병합 → 요약 |
| `frontend/src/**/__fixtures__/exia-sample.json` (신규) | 정제·축소 픽스처 |
| `docs/roadmap.md` | Phase A 착수/완료 반영(구현 후) |

---

## 15. 결정 로그 (Fienn과 확정, 2026-07-18)

1. **임포터 위치 = 프론트 TS** (네트워크 없는 로컬 파싱, 편집 가능 draft 산출, 수동 ATK 흐름 유지).
2. **Path 1 = Phase A 먼저**, ATK 자동화는 Phase B로 분리(CDN 기초스탯표 발견으로 디리스크).
3. **병합 = 슬러그별 병합**(수동 필드 보존) — 계획서의 "전체 교체·merge 없음"을 뒤집음. 전제
   변경 때문: export가 ATK/큐브를 안 담고 로스터가 영속화됨.
4. **애장품 = draft 필드로 만들지 않음**(표시 ATK에 포함 → 수동 ATK에 반영). Phase B 입력으로 기록.
5. **미매핑 오버로드(def/accuracy) = 드롭 + warning**(에러 아님).
