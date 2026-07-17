# Phase B — blablalink/ShiftyPad 정확 스탯 수집기 설계

- 날짜: 2026-07-18
- 상태: 설계 승인 대기 → (승인 후) writing-plans
- 브랜치: `wip/roster-import`
- 상위 맥락: Phase 7 / Phase A(`2026-07-18-exia-roster-importer-design.md`)의 후속.
  Phase A가 미룬 "ATK 자동화"를 재정의.

---

## 1. 목표

사용자가 **간단한 조작만으로 본인 계정의 정확한 육성 상태**를 얻고, 그 데이터로 덱 추천을
받는다(Fienn 2026-07-18). Phase A는 오버로드·스킬·돌파를 ExiaInvasion export 파일로
임포트했지만 **ATK/HP/DEF는 수동으로 남겼다**. Phase B는 그 스탯을 **정확히 자동 수집**한다.

**핵심 통찰 (조사로 확정, 2026-07-18):**
- **솔로레이드는 전원 레벨 400 고정**(Fienn). 유니온레이드는 400 보정 없이 **실제 육성 레벨**로
  전투. → 두 컨텐츠를 위해 **스탯을 두 버전(실제레벨 + 400레벨)으로 수집**한다.
- ShiftyPad의 개별 니케 정보 페이지가 방어구 포함 **정확한 스탯을 클라이언트에서 계산해
  표시**하고, 레벨 슬라이더로 임의 레벨(=400) 값도 준다. 같은 페이지가 **합산 오버로드**도 보여준다.
- 따라서 **스탯 공식을 재구현할 필요가 없다** — ShiftyPad이 이미 계산한 값을 읽는다.

**정확도 교정 (중요):** 현재 덱빌더는 사용자가 수동 입력한 값(ShiftyPad 메인 표시 = **실제레벨
663** 값)을 쓴다. 그러나 솔로레이드는 400레벨이다. Rapi 실측: **실제 418,862 vs 400레벨
143,543 (2.9배 차이)**. 즉 현재 솔로레이드 추천은 부풀려진 ATK를 쓰고 있을 가능성이 크다.
Phase B는 이걸 함께 바로잡는다(솔로레이드 = 400레벨 스탯 사용).

---

## 2. 조사로 증명된 사실 (추측 아님)

전부 2026-07-18 Fienn 로그인 세션에 CDP로 붙어 실측.

- **개별 니케 페이지 URL:** `https://www.blablalink.com/shiftyspad/nikke?from=list&nikke=<resource_id>`.
  `resource_id`는 우리 캐릭터 디렉토리(blablalink CDN `yl-57/...` EN, `name_code`/`id`로 조인)와
  export 양쪽에 있다.
- **메인 스탯 패널:** `POWER/HP/ATK/DEF` 각각 `실제레벨 값 + (레벨 슬라이더가 400일 때의) 델타`.
  실측 Rapi(슬라이더 400): ATK 실제 418862 / 델타 −275319 → **400레벨 = 143543**. HP 9727100 →
  3532402. DEF 55537 → 20986. **한 페이지 상태에서 두 버전이 다 나온다**(실제=메인, 400=메인+델타).
- **합산 오버로드:** 같은 페이지 "Equipment Effects"에 **4장비 합산 + 영문 라벨**로. 실측 Rapi:
  Increase ATK 42.32%(=export StatAtk 11.11+10.4+9.7+11.11), Increase Element Damage 87.21%,
  Increase Max Ammunition 173.93%, Increase Critical Rate 4.69% — **export 합산과 정확히 일치**.
- **레벨 400 설정:** 커스텀 버튼(`-263/-10/-1/+1/+10`). synchro 663에서 `-263` 한 번이 정확히 400.
  (표준 `input[type=range]` 아님 → 버튼 조작 필요.)
- **같은 페이지 탭 (Equipment | Skill | Collection | Cube):** 유닛 정보를 탭으로 분리.
  - **Cube 탭: 스크랩 확인.** 장착 큐브 이름·레벨·스탯("Resilience Cube, LV.15, ATK 2780…").
    → **`pve_cube`(이름+레벨) 자동 채우기 가능** — Phase A가 수동으로 남긴 필드를 자동화.
  - **Collection 탭: 스크랩 확인.** 소장품 이름·등급·레벨·스탯("Shopping Commander Doll Ltd.,
    Phase 15, SR, ATK 9688…").
  - **Skill 탭: 클릭 미해결.** 탭 `div`가 "not visible"로 잡혀 전환 실패 — 견고한 셀렉터 필요
    (구현 첫 스파이크). 스킬레벨은 raw API로 대체 가능(아래).
- **인증 raw API(스킬/보유목록 폴백):** `POST api.blablalink.com/.../GetUserCharacterDetails`
  (body `{intl_open_id, nikke_area_id, name_codes:[...]}`, `credentials:include`, intl_open_id=
  `game_openid` 쿠키값)가 `skill1_lv/skill2_lv/ulti_skill_lv` 등을 준다.
  `GetUserCharacters`가 보유 유닛 목록(name_code/lv/grade/core)을 준다. **Skill 탭·ShiftyPad
  리스트가 여의치 않을 때의 신뢰 폴백.**
- **base 스탯 테이블(이미 수집, `data/blablalink-cdn/`):** 클래스 3종(Attacker/Supporter/Defender)
  레벨 1~1200 배열, 클래스-균일. base@400 = `list[399]`(Attacker 90318 등). 스크랩값 교차검증용.

**목표는 순수 ShiftyPad 스크랩**(스탯·오버로드·스킬·소장품·큐브 전부 ShiftyPad 탭에서, Fienn
2026-07-18). raw API는 Skill 탭·보유목록이 스크랩 곤란할 때의 폴백으로만 둔다.
**미확정(구현 중 해소):** Skill 탭 견고 셀렉터 · ShiftyPad 리스트 뷰 보유목록.

---

## 3. 아키텍처

**라이브 수집기(Playwright/CDP 헬퍼)** — 이 프로젝트는 Fienn 개인 도구이므로, "간단한 조작"의
현실적 기준은 "Fienn이 로그인된 브라우저에 대고 헬퍼 1회 실행"이다(오늘 검증한 흐름).

```
[Fienn] Chrome(원격 디버깅) 실행 + blablalink 로그인
   → [수집기] CDP 접속
       → 보유 유닛 목록 취득 (raw API GetUserCharacters)
       → 유닛마다: /shiftyspad/nikke?nikke=<resource_id> 이동
            → 레벨 400 설정 (버튼)
            → 메인패널 스크랩: ATK/HP/DEF (실제 + 400)
            → Equipment Effects 스크랩: 합산 오버로드(영문→우리 이름)
            → Skill 탭: 스킬레벨 (실패 시 raw API 폴백)
            → Cube 탭: 큐브 이름·레벨 → pve_cube 자동
            → Collection 탭: 소장품 이름·등급·레벨
   → roster.json 출력 (유닛별: slug · 두 스탯버전 · 오버로드 · 스킬 · 큐브 · 소장품)
[앱] roster.json 임포트 (Phase A 병합 setter 재사용)
```

- **수집기 위치:** Node/Playwright 스크립트(예: `tools/collect-blablalink/`). 백엔드(Python)·
  프론트(TS)와 분리된 사용자-실행 도구. 자격증명 저장 없음(세션은 Fienn 브라우저).
- **폴백은 언제나 수동/Phase A 파일임포트**(서드파티는 죽는다 — Phase 7 원칙2). ShiftyPad이 바뀌면
  수집기는 실패하되 앱은 수동 폼으로 degrade.

---

## 4. 유닛별 수집 데이터 → 매핑

| 필드 | 소스 | 비고 |
|---|---|---|
| `character_slug` | `resource_id`→디렉토리→`name_en`→Phase A `resolveSlug` | 별칭표 재사용 |
| **솔로레이드 스탯** hp/atk/def | ShiftyPad 메인패널 실제+델타 = **400레벨** | 덱빌더(솔로) 사용 |
| **실제레벨 스탯** actual_hp/atk/def | ShiftyPad 메인패널 실제값 | 유니온레이드(후속)용 |
| `overload_options` | Equipment Effects 합산(영문→한글 7종) | 이미 합산됨 |
| `skill_levels` | ShiftyPad **Skill 탭** (폴백: raw API `skill1_lv/skill2_lv/ulti_skill_lv`) | 엔진 소비 |
| `pve_cube` | ShiftyPad **Cube 탭** 이름·레벨 | **자동**(Phase A는 수동) — 큐브 효과 배선 |
| 소장품(item) | ShiftyPad **Collection 탭** 이름·등급·레벨 | 스탯은 이미 메인패널 반영; 기록/후속용 |
| `core_level` | (inert) 생략 또는 raw API core | 엔진 미소비 |

**오버로드 영문→우리 매핑(백엔드 `overload_effects.py` 한글 7종):**
Increase ATK→공격력 증가 · Increase Element Damage Dealt→우월코드 대미지 증가 ·
Increase Critical Damage→크리티컬 대미지 증가 · Increase Critical Rate→크리티컬 확률 증가 ·
Increase Charge Damage→차지 대미지 증가 · Increase Charge Speed→차지 속도 증가 ·
Increase Max Ammunition Capacity→최대 장탄 수 증가. (미매핑 라벨은 드롭+경고 — Phase A 정책.)
**주의: 실제 영문 라벨 문자열은 구현 시 페이지에서 확정**(위는 관측된 4종 + 예상 3종).

---

## 5. 데이터 모델 변경

현 `UserNikkeState`의 hp/atk/def는 사용자 수동값(실제레벨 663)이었다. 변경:

- **`hp/atk/def` = 솔로레이드(400레벨) 값**으로 의미 재정의. 엔진은 base_stats.hp/atk/def를 그대로
  읽으므로 **엔진 변경 없이** 솔로레이드 추천이 올바른 400레벨 스탯을 쓰게 된다(정확도 교정).
- **신규 옵셔널 `actual_hp/actual_atk/actual_def`** 추가 — 유니온레이드(후속 기능)용. 지금은 저장만.
- 프론트 `NikkeDraft`·`UserNikkeState`(및 TS 미러)에 반영. Phase A 병합 setter가 import 필드로
  이 스탯들을 덮되, 여전히 수동 편집 가능(폴백).

**YAGNI:** 유니온레이드 추천 로직·모드 스위치는 이번 범위 밖(스탯만 수집·저장). 솔로레이드
경로만 배선.

---

## 6. 컴포넌트

1. **수집기(Node/Playwright)** — §3 흐름. CDP 접속·유닛 순회·스크랩·JSON 출력. 재실행 안전,
   진행/에러 리포팅, `--dry-run`.
2. **앱 임포트** — roster.json(신규 포맷)을 읽어 `NikkeDraft[]`로 매핑 + Phase A `importDrafts`
   슬러그별 병합. Phase A의 ExiaInvasion 임포트 경로와 공존(둘 다 draft로 수렴).
3. **모델/타입 변경** — §5.

---

## 7. 검증

- **수집기:** 캡처된 픽스처(정제 — 자격증명 없음)에 대한 파싱 단위테스트. 라이브 호출/토큰
  불요(테스트 pristine). 메인패널 파싱(실제/델타/400) · 오버로드 영문→한글 · resource_id→slug.
- **교차검증:** 스크랩한 400레벨 ATK가 `base@400[class] + 합리적 초과분` 범위인지 대조
  (`data/blablalink-cdn/` base 테이블). Rapi 143543 = base@400 90318 + 53225(gear+item+cube+LB).
- **임포트:** 니케 1명 수집→임포트 결과 `UserNikkeState`가 유효하고 hp/atk/def가 400값인지.
- **E2E:** `/verify`로 백엔드 기동 → 수집 로스터로 `POST /api/recommend` → 추천 반환.
- **정확도 회귀:** 동일 로스터에서 솔로레이드 추천이 400레벨 스탯 기준으로 달라지는지 확인
  (663 대비 순위 변화 관측).

---

## 8. 결정 로그 (Fienn, 2026-07-18)

1. **완전 자동화 목표, 정확한 데이터 우선** — 사용자는 간단한 조작만, 정확도는 타협 안 함.
2. **스탯 두 버전 수집** — 실제레벨(유니온레이드) + 400레벨(솔로레이드). 유니온레이드 도우미는 후속.
3. **ShiftyPad 계산값을 읽는다(공식 재구현 안 함)** — ShiftyPad은 공식 커뮤니티(blablalink)
   하위라 안정적(Fienn). 방어구 스탯 테이블·돌파%공식 유도 회피.
4. **오버로드도 같은 페이지에서 수집**(Fienn 제안) — 합산·영문 라벨 그대로. cost 절감, raw API의
   option-id 해석 불필요.
5. **솔로레이드 = 400레벨 스탯**으로 hp/atk/def 의미 재정의(정확도 교정). 실제레벨은 별도 저장.
6. **스킬·소장품·큐브도 ShiftyPad 탭에서 수집**(Fienn 2026-07-18) → **순수 ShiftyPad 스크랩**
   지향(raw API는 폴백). **큐브가 Cube 탭에서 자동 채워짐**(Phase A는 수동이었음). Cube·Collection
   탭 스크랩 확인됨, Skill 탭은 셀렉터 스파이크 필요.
7. **폴백은 수동/Phase A 파일임포트** — 서드파티 의존 리스크 방어.

---

## 9. 리스크 / 미해결

- **ShiftyPad SPA 취약성:** DOM/구조가 바뀌면 스크랩 붕괴. 완화 = 파싱을 라벨 기반으로 견고화,
  실패 시 명확한 에러 + 수동 폴백. (공식 사이트라 빈도 낮음, Fienn.)
- **레벨 400 설정 견고성:** 커스텀 버튼 조작. synchro≠663이면 `-263`이 400이 아님 → 목표 레벨까지
  정확히 도달하는 로직 필요(구현 첫 스파이크).
- **스킬/큐브 탭 스크랩 불확실** → 스킬은 raw API로 대체(신뢰). 큐브는 필요 시 API tid/lv.
- **보유 유닛 목록:** raw API `GetUserCharacters`(신뢰) 우선, ShiftyPad 리스트는 선택.
- **사용자 조작 간소화:** 현재는 "디버깅 Chrome 실행 + 로그인 + 헬퍼 실행". 개인 도구엔 OK.
  향후 북마클릿/패키징은 별도 개선(YAGNI).
- **영문 오버로드 라벨 전체 목록** 미확정(4종 관측) → 구현 시 크리댐/차지 보유 유닛으로 확정.

---

## 10. 손대는 파일(예상)

| 파일 | 무엇을 |
|---|---|
| `tools/collect-blablalink/` (신규) | Playwright/CDP 수집기 + 파서 + 픽스처 테스트 |
| `backend/app/models.py` | `actual_hp/atk/def` 옵셔널 필드; hp/atk/def=400레벨 의미 |
| `frontend/src/types/userNikkeState.ts`·`nikkeDraft.ts` | TS 미러 + draft 필드 |
| `frontend/src/lib/` (신규 임포터) | roster.json → NikkeDraft 매핑(+Phase A 병합 재사용) |
| 임포트 UI | roster.json 업로드 경로 |
| `docs/roadmap.md` | Phase 7/B 상태 갱신 |
| `docs/decisions.md` | 이 설계의 결정 기록(`/document`) |
