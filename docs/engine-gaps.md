# 엔진 갭 인벤토리 (Engine Gap Inventory)

현재 시뮬레이션 엔진이 **표현하지 못해서 인코딩을 defer 중인 스킬 메커니즘**을
한곳에 모아, "어떤 엔진 기능을 만들면 몇 명이 풀리나"를 데이터로 보고 우선순위를
정하기 위한 문서. `special-mechanics.md`(패턴 카탈로그)와
`encoded-nikkes.md`(유닛별 보류 내역)의 상위 집계판이다.

- 마지막 갱신: 2026-07-15 (**gap #7 완료** — `per_shot_rules`에 창 한정 모드
  `"every_during_full_burst"`/`"every_during_own_status_window"` 추가. 첫 소비자
  Soda·Asuka 잔여 메커니즘 재인코딩. 같은 날 Phase A1 두 건(helm-aquamarine·
  anis-sparkling-summer)도 기존 per_shot 능력으로 인코딩, grave·velvet은 gap #7로
  언블록 가능하다고 재분류(다음 배치), jill-valentine은 신규 소규모 갭
  "reload 후 첫 발" 마커 필요로 식별(gap #9), rapi-red-hood는 프로젝타일-런치
  상태머신이라 복잡·보류 확인). **같은 날 후속 배치:** grave(Overheat II/III)·
  velvet(Bullets of Love)도 gap #7로 재인코딩 완료 — gap #7 소비자는 Soda·Asuka·
  Grave·Velvet 4명. 남은 gap #7 후보는 modernia 하나(검증 전).
- 이전 갱신: 2026-07-12 (gap #1 잔여 변형 "마지막 탄" 완료 — `magazine_last_bullet_times`/
  `charge_last_bullet_times`/`last_bullet_shot_times` + `per_shot_rules`의
  `"last_bullet"` 모드. eb4 배치: Asuka Shikinami Langley: Wille·Mana도 이 날 완료
  — `fire_delay`+`own_burst_delayed`·own-status-window fill·`full_burst_bonus_eligible`·
  `resource_scaled_nukes`의 `resource` 선택화. `cinderella-crystal-wave`는 Pattern-A가
  아니라 무기-모드 상태머신 유닛으로 재분류됨)
- 목적: **ROI 순 엔진 확장 우선순위 결정.** 인코딩을 하나씩 하다 갭에 부딪혀
  단발성 확장(instant nuke, periodic nuke)을 반복하던 방식 대신, 갭을 모아
  빈도순으로 최소한만 확장한다. (Fienn 방침, 2026-07-10)
- YAGNI: 아래 인벤토리가 *증명한* 트리거/스탯만 최소로 구현한다. 가상 요구를 위한
  프레임워크 금지.

## 집계 방법 (재현 가능)

`data/lootandwaifus/char_*.html`에 수집된 **44개 유닛**의 Lv10 스킬 텍스트를
시그니처 문구로 스캔한 결과다. 카운트는 **문구 매칭 근사치** — 실제로 엔진 확장을
착수하기 전엔 해당 유닛 텍스트를 직접 확인해서 오탐(예: 단순히 "charge weapon"을
언급만 한 경우)을 걸러야 한다. 스캔 스크립트는 일회성으로 돌렸고, 유닛 풀이
늘어나면 같은 패턴으로 다시 집계하면 된다.

---

## 우선순위 요약 (막힌 유닛 수 기준)

| # | 엔진 갭 | 막힌 유닛 (근사) | 확장 규모 | 성격 |
|---|---|---:|---|---|
| ~~1~~ | **per-shot 트리거 + 발사 카운터** (노멀공격 N회 / 풀차지 N회 / N shot마다 / 마지막 탄) | ~30 (합집합) | **완료 (2026-07-11 `per_shot_rules`, 2026-07-12 "마지막 탄" 잔여 변형까지 완료)** | 신규 트리거 |
| 2 | **자원/스택 트래킹** (배터리·탄약주머니·N스택 누적) | 16 | **Pattern A 완료 (2026-07-12, named-resource)** — Pattern B(시간감쇠 게이지·변신) 잔여 | 신규 상태 |
| 3 | **narrow subset scope** (무기종별 / 티어+선버스트 대상) | 9 | 무기종: 소(~20 loc) / 티어부분집합: 중(~60 loc) | 신규 스코프 |
| ~~4~~ | ~~sustained / distributed / true / projectile-explosion damage 배선~~ | 5 / 4 / 4 / — | **완료 (2026-07-10, 데미지 타입 모델링)** | 스탯 배선 |
| 5 | **enemy-element 조건** (룰에서 boss_element 접근) | 1 (+기존 Brid, Helm:Aqua) | 소 (~30 loc) | 컨텍스트 확장 |
| 6 | **periodic-during-Full-Burst 넉** (풀버스트 창 안에서만 N초마다) | 1 (Ada) | 소 (~30 loc, periodic_nukes 변형) | 타이밍 변형 |
| ~~7~~ | ~~풀버스트/자기상태창 한정 per-shot 트리거~~ (fill이 아니라 버프/넉 직접 발동) | 4 (Soda·Asuka·Grave·Velvet) | **완료 (2026-07-15, `per_shot_rules`의 `every_during_full_burst`/`every_during_own_status_window` 모드)** | 신규 트리거 변형 |
| 8 | **자원-fill-트리거 타 유닛 버프** (자원 소유자 아닌 아군에게 버프) | 1 (Maiden 잔여 버프) | 소~중 | 신규 트리거 |
| 9 | **reload 후 첫 발("first bullet after reload") per-shot 마커** (신규, 2026-07-15) | 1 (Jill Valentine) | 소 (~30 loc, "마지막 탄" 마커의 거울상) | 신규 트리거 변형 |
| — | ~~버스트 외 트리거 즉발 넉~~ / ~~자체 쿨다운 주기 넉~~ | — | **완료** (instant_nuke / periodic_nukes) | 참고 |
| — | ~~교차 유닛 트리거 (타 유닛 버스트에 반응)~~ | 1 (Prika→Mint) | **완료 (2026-07-11, `ally_burst_activate`)** | 신규 트리거 |
| — | ~~자원 reset / resource_gated_buffs / squad-burst-cycle-conditional fill / dynamic_hit_count_nukes~~ | — | **완료 (2026-07-12)** — Soda·Maiden 소비 | 신규 상태/트리거 |
| — | attack/charge speed·hit rate (딜 아님) | 15 | **구현 안 함** (딜 개념 아님, defer 유지) | 범위 밖 |

> **핵심 결론:** #1 하나가 압도적이다. 노멀공격 카운터(20명)와 풀차지 카운터(19명)는
> **같은 기반 메커니즘**(유닛의 발사를 세면서 임계치마다 룰 발동)으로 묶을 수 있어,
> 하나만 만들면 두 그룹의 합집합(~30 유닛)이 풀린다. #2 자원 트래킹도 대부분
> "part 파괴 / 풀차지 발사"로 채워지므로 #1이 선행 조건이다. **#1이 첫 번째 확장으로
> 가장 높은 ROI.**

---

## 갭 상세

### 1. per-shot 트리거 + 발사 카운터 — ✅ 완료 (2026-07-11, `per_shot_rules`)

- **해결:** `simulate_raid`의 `per_shot_rules` — 유닛 발사를 세어 `after N`/`every N`에
  버프/넉 발동. 함께 **record-then-compute 리팩터**로 per-shot 스쿼드 버프가 버스트
  넉까지 반영됨. 첫 소비자 Brid: Journey Ahead(5발마다 675% 넉). `engine-capabilities.md`/
  `special-mechanics.md` 참고.
- **"마지막 탄"(매거진 경계) — ✅ 완료 (2026-07-12):** `attack_rate.py`의
  `magazine_last_bullet_times`/`charge_last_bullet_times`/`last_bullet_shot_times`가
  `generate_{magazine,charge}_shot_times`/`generate_shot_times`와 동일한 3단 구조로
  각 매거진을 실제로 비우는 발사(= `magazine_size - 1`번째)만 골라낸다 — 매거진
  크기는 `max_ammo_percent_at`으로 라이브 재계산(기존 발사 생성과 동일 메커니즘)돼서
  유저의 [최대 장탄 수 증가] 오버로드/스킬 버프가 이미 정확히 반영됨. attack/charge
  speed는 별도 모델링 불필요 — 이 엔진 어디에도 발사 간격 수정자로 배선돼 있지 않고
  (`engine-capabilities.md`의 "엔진이 소비하지 않는 스탯" 참고), 설령 있었어도 매거진
  "간격"만 바꿀 뿐 "용량"은 안 바꾸므로 마지막 탄 위치엔 무관. `fight_duration`으로
  전투가 매거진 중간에 끊긴 마지막 발사는 (실제로 매거진을 비운 게 아니므로) 잘못
  마킹하지 않도록 처리됨. `per_shot_rules`에 새 모드 `(None, "last_bullet", rules)`로
  배선(threshold 미사용). `ResourceSpec`에도 `("on_last_bullet",)` fill kind 추가
  (Julia의 Crescendo — 라스트불릿마다 스택). 같은 배치에서 즉시 재인코딩: Julia(base)
  ✅(Crescendo 자원 + Climax 게이팅 추가딜, 이 갭의 원래 동기 유닛) · Helm(애장품)
  ⚠(Frontline Command, 죽은 `on_last_bullet_hit` 트리거 실배선으로 교체) · Privaty
  (애장품) ✅(LD Assault, Designated Target 조건부 중첩 넉).
- **다음(후속 배치):** 아래 막힌 유닛들을 이 능력으로 재인코딩. 각 유닛 데이터 수집 후
  per-shot 룰 추가.
- **잔여 변형:** (a) **아군 총탄 카운터**(스쿼드 전체 발사 누적, per-caster 아님) — 예:
  Little Mermaid의 Bubble Barrage(아군 총탄 500마다 850%). `per_shot_rules`는 시전자
  본인 발사만 세므로 미커버. 스쿼드 합산 카운터는 별도 확장 필요. (b) **크리티컬 히트
  카운터 — 영구 defer, "만들 능력"이 아님(2026-07-12, Julia 시그니처 인코딩 중 발견):**
  "N회 크리티컬 히트 후" 트리거는 엔진의 기대값 기반 크리 모델(각 히트가 `crit_rate`
  확률로 스케일되는 연속값 — 실제 per-hit RNG 안 굴림)과 구조적으로 안 맞는다. "이 샷이
  실제 크리였는가"라는 이벤트 자체가 없어서 셀 수 없다. per-shot 카운터 확장으로도 못
  푼다 — Julia(시그니처)의 Crescendo/Marcato가 이 사유로 영구 defer.
- **무엇(원문):** "노멀 공격 N회 후", "풀차지 공격 N회 후 / 시", "마지막 탄 발사 시",
  "N shot마다" 처럼 **유닛의 발사 행위를 세어** 임계치마다 효과/넉을 발동하는 트리거.
- **왜 막힘:** 노멀공격(차지샷 포함)은 `raid_simulator`의 별도 weapon-stats 패스에서
  생성되고 `fire_trigger`를 거치지 않는다. 그래서 SkillRule이 훅할 "발사했다" 트리거가
  없다. (`engine-capabilities.md`의 트리거 표 참고 — 4개 버스트 트리거만 존재.)
- **막힌 유닛 (노멀 카운터, 20):** anis-sparkling-summer, ark-ranger-black,
  asuka-shikinami-langley-wille, chisato-nishikigi, cinderella-crystal-wave, drake,
  eve, guillotine-winter-slayer, helm-aquamarine, julia, laplace, ludmilla-winter-owner,
  mana, marciana-marine-study, mihara-bonding-chain, quency-escape-queen, rei-ayanami,
  rei-ayanami-tentative-name, soda-twinkling-bunny, velvet
- **막힌 유닛 (풀차지 카운터/트리거, 19):** bready, cinderella, cinderella-crystal-wave,
  diesel-winter-sweets, ein, laplace, liberalio, maiden-ice-rose, maxwell,
  milk-blooming-bunny, mint, neon-vision-eye, prika, raven, red-hood,
  scarlet-black-shadow, snow-white, snow-white-heavy-arms, velvet
- **필요한 확장:** weapon-stats 패스가 유닛별 누적 발사수(및 풀차지 발사수)를
  추적하고, 임계치 도달 시 트리거를 발동해 SkillRule 룰을 실행 + `_damage_from_percent`로
  넉을 계산하도록 배선. 발사율은 이미 `attack_rate.py`에 있으니 시각 t까지의 발사수는
  결정적으로 계산 가능. **노멀/풀차지를 하나의 "shot fired(+charge 여부)" 트리거로
  통합**하는 게 요점.
- **규모:** 큼 (~100–180 loc + 테스트). 이 프로젝트에서 가장 큰 단일 확장이지만
  ROI 최고.
- 참고: `special-mechanics.md`의 "On [own] Full Charge attack", "'Deals X%' tied to
  a trigger other than own burst"(마지막 탄/노멀 카운터 부분).

### 2. 자원 / 스택 트래킹 — ⚠ Pattern A 완료 (2026-07-12), Pattern B 잔여

실제 16유닛 텍스트를 확인하니 단일 메커니즘이 아니라 **두 갈래**였다:

- **Pattern A — 누적/캡 스택 카운터 (✅ 완료):** 이벤트마다 스택이 쌓여 캡에서 멈추고
  버프/넉이 스택 수에 비례. 채우기는 기존 트리거(per-shot 카운터·버스트·battle_start)로
  커버. **`ResourceSpec`/`ResourceBuff`** + `SquadContext.resource_fills`/`resource_count`
  + `raid_simulator` resolution 패스(결정론적 fill 스케줄 → 캡 스텝-버프 방출) +
  `linear_resource_buff`/`leveled_resource_buff`. **선형·시한·티어(레벨 파생)·core-conditional
  fill** 지원. 첫 소비자 Modernia(시한 캡)/Guillotine: Winter Slayer(연속 누적 + Hero
  Level 파생). "이미 만든 것" 참고.
- **Pattern B — 시간감쇠 게이지 + 임계치 변신 (잔여):** Ark Ranger 배터리(부위파괴 +50%,
  100%에서 변신, 1%/0.2초 감쇠), Mihara 체인. **part-destruction 이벤트에 추가로 막힘**
  (엔진에 부위 개념 없음 → 가상 스케줄 발명하지 않고 defer, Fienn 2026-07-12).
- **Pattern A로 언블록(코어):** guillotine-winter-slayer ✅(EXP+Hero Level+Extermination
  DoT), modernia ✅, cinderella ✅(Beautiful periodic fill + mirror 넉),
  quency-escape-queen ✅(정상상태 스택체인, 신규 확장 불필요), soda-twinkling-bunny ⚠
  (자원 **reset** + `resource_gated_buffs` + FB창 한정 fill), maiden-ice-rose ⚠
  (squad-burst-cycle-conditional fill + `dynamic_hit_count_nukes`), asuka-shikinami-
  langley-wille ⚠(`fire_delay`+`own_burst_delayed` 지연 발동 넉/리셋 + own-status-window
  fill), mana ⚠(`resource_scaled_nukes`의 `resource` 필드 선택화 — 순수 반복틱 DoT,
  자원 확장 불필요) — **2026-07-12 전부 완료**. `cinderella-crystal-wave`는 Pattern-A가
  아니라 **무기-모드(MG/Snipe) 전환이 FB 넉을 게이팅하는 상태머신 유닛**으로 밝혀져
  제외·재분류됨(eb4 검증 중, Fienn 결정) — roadmap의 무기 변형 항목 참고. 남은 Pattern-A
  후보(rei-ayanami·rei-ayanami-tentative-name·neon-vision-eye)는 검증 전.
- **count-스케일 넉 — ✅ 완료 (2026-07-12):** 버스트 시점(또는 반복 tick 시점) resource
  count로 스케일/게이팅되는 넉. `raid_simulator`의 `resource_scaled_nukes` 파라미터 —
  `record()`가 `resource_gate`를 실어 두고 phase 2에서 `context.resource_count(...)`로
  퍼센트를 해석(버프와 동일한 지연 계산 패턴). 단일 게이팅 히트(Julia Climax 문턱),
  단일 스케일 히트(Cinderella mirror), 반복 tick DoT(Guillotine Extermination, 매 tick
  자신의 시각 기준 count 재조회) 모두 커버.
- **multi-hit 버스트 넉 — ✅ 완료 (2026-07-12):** "attacks sequentially N times"는
  N*percent 한 방이 아니라 **N개의 개별 히트**(디펜스가 히트당 flat 차감이라 다르게
  나옴). `raid_simulator`의 `burst_hit_counts` 파라미터. 첫 소비자 Cinderella(10회)/
  Julia-signature(5회).
- **periodic 자원 fill — ✅ 완료 (2026-07-12):** `("periodic", interval)` fill kind —
  샷과 무관하게 고정 타이머로 채워지는 자원(Cinderella의 Beautiful, decoy 상시 유지로
  3초마다 틱).
- **Pattern B로 잔여(16 중):** ark-ranger-black, mihara-bonding-chain, red-hood(charge
  speed·딜 아님), velvet(ammo pouch·풀차지 트리거), laplace(Hero Vision·풀차지),
  raven/sakura(sustained DoT 스택·별 갭) 등.
- 참고: `special-mechanics.md`의 "Named resource / capped stack counter",
  "Resource-scaled / gated burst nuke", "Multi-hit burst nuke",
  `engine-capabilities.md`의 ResourceSpec/resource_scaled_nukes/burst_hit_counts.

### 3. narrow subset scope

- **무엇:** self/squad/element:X로 표현 안 되는 대상 지정. 두 하위 종류:
  - **무기종별** ("어썰트라이플 아군", "샷건 아군 제외 자기") — 규모 소.
  - **티어+원소+선버스트 부분집합** ("이미 버스트한 버스트3 전기 아군") — 규모 중,
    동적 멤버 리스트 필요.
- **막힌 유닛 (9):** ada-wong, anis-sparkling-summer, ark-ranger-black,
  cinderella-crystal-wave, maiden-ice-rose, mana, maxwell, sakura-bloom-in-summer,
  soda-twinkling-bunny
- **필요한 확장:** `Effect.scope`에 `weapon:<type>` 추가(멤버 무기 데이터로 매칭,
  소규모) / 임의 멤버 부분집합 스코프(중규모).
- **부분 해결 (2026-07-12):** "N ally unit(s) with the highest final ATK" 하위 종류는
  **완료** — `SquadContext.top_atk_slugs`(적용 시점 실시간 final ATK 랭킹) + `slugs:`
  Effect 스코프 + `highest_atk_buff_rule`. Miranda가 첫 소비자. 무기종/티어부분집합
  스코프는 여전히 잔여.
- 참고: `special-mechanics.md`의 "Weapon-type-scoped buffs", "Targeting a per-member
  subset by tier + element + prior-burst", "Highest-final-ATK top-N targeting".

### 4. sustained / distributed / true / projectile-explosion damage 배선 — ✅ 완료 (2026-07-10)

- **무엇:** `sustained_damage_up`, `distributed_damage_up`, `true_damage_up`,
  `projectile_explosion_damage_up`가 `raid_simulator`에서 inert였던 문제.
- **해결:** "데미지 타입 모델링"으로 구현. 각 데미지 인스턴스에 타입을 부여하고
  타입-게이팅된 버킷만 적용(블랭킷 배선의 과대평가를 피함). 게이팅이 핵심이었던 게
  맞았음 — 단순 배선이 아니라 **타입 인스턴스 생성 기능과 묶여야** 유효했다.
  `engine-capabilities.md` "Damage typing" 참고.
- **막혔던 유닛 (참고):** sustained(5): ark-ranger-black, diesel-winter-sweets,
  mana, mihara-bonding-chain, sakura-bloom-in-summer · distributed(4): bready,
  milk-blooming-bunny, quency-escape-queen, scarlet-black-shadow · true(4):
  ada-wong, chisato-nishikigi, ein, jill-valentine · projectile-explosion:
  Mint(기존 emit 즉시 유효), Rapi(버스트 넉 태깅). — 엔진은 준비됐고, 각 유닛의
  헤드라인 버프가 실제 딜을 움직이려면 **같은 덱에 해당 타입 딜러가 있어야** 함
  (버프는 곱할 대상이 있어야 유효).
- **잔여:** 각 딜러의 타입 인스턴스(지속 넉 등)를 실제로 인코딩하는 건 개별 유닛
  인코딩 작업. Prika/Anis:Star의 projectile explosion 버프는 여전히 다른 갭(풀차지
  트리거/미인코딩)에 막힘.

### 5. enemy-element 조건 (룰에서 boss_element 접근)

- **무엇:** "적이 X Code일 때만" 발동하는 디버프/추가딜. SkillRule 액션이 boss_element에
  접근 불가(현재 `raid_simulator`만 앎).
- **막힌 유닛 (신규 1):** marciana-marine-study. (기존: brid-silent-track,
  helm-aquamarine.)
- **필요한 확장:** 트리거 dispatch 시 boss_element를 액션 컨텍스트로 전달. 규모 소.
- 참고: `special-mechanics.md`의 "Enemy-element-conditional debuffs".

### 6. periodic-during-Full-Burst 넉

- **무엇:** 풀버스트 창(10초) 안에서만 N초마다 발동하는 넉. 예: Ada Wong의 Flash
  Grenade(420% True dmg, 2초마다, 풀버스트 중). 기존 `periodic_nukes`는 **전투 내내**
  발동이라 창 한정이 안 됨.
- **막힌 유닛 (1):** ada-wong.
- **필요한 확장:** `periodic_nukes`에 "풀버스트 창 한정" 옵션, 또는 full_burst_enter~end
  사이만 틱. 규모 소. (수요 1명이라 후순위.)

### 7. 풀버스트/자기상태창 한정 per-shot **트리거** — ✅ 완료 (2026-07-15)

- **무엇이었나:** "풀버스트(또는 자기 상태창) 중 노멀 N회마다"가 버프/넉을 **직접 발동**하는
  경우 — Soda의 Lucky Golden Chip 공동발동 버프(최고ATK 아군 대상 Attack Damage,
  3발마다·FB 중에만), Asuka의 Anti A.T. Field 15.62% 상태게이팅 넉(노멀10회마다·
  Annihilation State 중에만). #2 Pattern A로 만든 **창 한정 resource fill**
  (`per_shot_every_during_full_burst` / `per_shot_every_during_own_status_window`,
  2026-07-12 확장)은 자원 채우기 한 종류만 처리하고, 일반 `per_shot_rules`엔 창 필터가
  없어 버프/넉을 직접 발동하는 트리거로는 못 썼다. 근사(창 무시 "매 N발") 시도 시 실제
  과대평가 위험이 컸다(Soda SG는 1.5발/초라 "매 3발"=2초 주기인데 버프 지속도 2초라,
  FB 밖에서도 적용하면 사실상 상시 버프로 읽혀버림).
- **해결:** `raid_simulator.py`의 `per_shot_rules`에 창 한정 모드 두 개 추가 —
  `"every_during_full_burst"`(threshold=N)와 `"every_during_own_status_window"`
  (threshold=`(N, window_duration)`, 후자는 자기 버스트 앵커 고정 길이 창). 매N번째
  스텝 전에 **창 안의 발사만** 세도록, `_resource_fill_times`의 창 필터 계산을 재사용.
  기존 `after`/`every`/`last_bullet` 모드와 나란한 순수 추가(회귀 없음).
- **소비자 (4, 전부 기존 ⚠ 유지 — 이 갭 외 잔여 메커니즘이 남아있어서):**
  - **soda-twinkling-bunny:** Lucky Golden Chip 공동발동 버프("풀버스트 중 노멀3회마다
    → 자신 + 최고ATK 아군에게 Attack Damage +10.51%/2초, refresh")를
    `every_during_full_burst`로 모델링(`top_atk_slugs`는 시전자 제외). 잔여: Beginner's
    Rewards(캐스터별 FB창 연장, 표현 불가), Hit Rate(inert).
  - **asuka-shikinami-langley-wille:** Anti A.T. Field의 15.62% 넉("Annihilation State
    중 노멀10회마다, as damage" — 스택버프와는 별개 탄환)을
    `every_during_own_status_window`(9초 자기-버스트-앵커 창, N=10)로 모델링. "as
    additional damage"가 아니라 "as damage"라 `full_burst_bonus_eligible` 미적용. 잔여:
    Normal Attack Damage 전용 디버프(노멀전용 스코프 없음), 재장전/힐.
  - **grave (2026-07-15 후속 배치):** Overheat II/III — 자기 버스트의 10초 상태창
    (Prediction) 한정 노멀30/60회마다 자ATK+20.66%/자AD+30.8%를
    `every_during_own_status_window`로 모델링. "continuously"를 **언락-후-영구**로
    해석(가정, Fienn 플래그 — "Overheat X 상태일 때" 절을 언락 게이트로 읽고, Prediction
    안에서 이미 충족되므로 활성-지속-창-한정이 아니라 영구 부여). 잔여: Overheat I(재장전
    게이팅 토글, gap #9 — II의 전제조건일 뿐이라 II/III는 이거 없이도 정확), 자힐, +3라운드
    탄약 불릿(caster 기본 탄약 불명).
  - **velvet (2026-07-15 후속 배치):** Bullets of Love — 풀버스트 중 풀차지샷마다(SR,
    N=1) 스쿼드 flat ATK(자ATK의 25.2%)+스쿼드 Charge Damage+100.8%(3초, refresh,
    Prika 선례 따라 스쿼드스코프)+풀버스트 중 노멀50회마다 자AD+15.03%/5초 + 400.92%
    넉("as additional damage"→`full_burst_bonus_eligible`)를 `every_during_full_burst`로
    모델링. ammo pouch(6000, 버스트 스테이지2마다 풀리필)는 소모량 대비 압도적으로 커서
    비제약으로 처리(자원 미모델링 — gap #2 대상 아님). 잔여: Sticky Fingers의 "풀버스트
    아닐 때" 풀차지 카운터(gap #7의 거울상인 not-in-FB 창 필터 필요, 미구현, 자기전용
    저가치), Perfect Execution 무기변형딜.
- **남은 후보:** modernia(Giant Leap 상태게이팅 200히트 ATK버프) — 검증 전.
- 참고: `special-mechanics.md`의 관련 항목, `soda_twinkling_bunny.py`/
  `asuka_shikinami_langley_wille.py`/`grave.py`/`velvet.py` docstring.

### 참고 — gap #7의 거울상: not-in-Full-Burst per-shot 창 필터 (미구현, 신규 발견)

Velvet의 Sticky Fingers는 "풀버스트 **아닐 때**" 풀차지마다 자ATK/자AD 버프(각
30.5%, 3초)를 준다 — gap #7의 `every_during_full_burst`의 정반대 필터. 현재
`per_shot_rules`엔 이 보수 필터가 없다. 유일하게 확인된 소비자가 velvet의 이
스킬(자기전용, 저가치)뿐이라 후순위. 착수 시엔 `every_during_full_burst`와
나란히 `"every_outside_full_burst"` 같은 모드로 최소 확장.

### 8. 자원-fill-트리거 타 유닛 버프 (resource_gated_buffs와 별개 갭)

- **무엇:** 한 유닛의 자원이 채워지는 사건에 반응해 **다른** 유닛에게 버프를 주는
  패턴 — Maiden의 Blessings Upon You "MP 회복 시" 아군(Electric 코드) 버프, Soda의
  것과 유사 소비자 없음(현재는 Maiden만). `resource_gated_buffs`(2026-07-12 완료)는
  "자원 소유자 자신의 버스트 시점 게이팅"만 처리 — fill 이벤트 자체에 반응해 스쿼드의
  **다른** 멤버에게 버프를 주는 경로는 없음.
- **막힌 유닛 (1, 확인분):** maiden-ice-rose (Blessings Upon You의 아군 버프만 잔여).
- **필요한 확장:** 자원 fill 이벤트를 트리거로 스쿼드(또는 조건부 서브셋) 버프를
  거는 새 파라미터. 규모 소~중, 수요 확인 후 착수.
- 참고: `maiden_ice_rose.py` docstring.

### 9. reload 후 첫 발("first bullet after reload") per-shot 마커 (신규, 2026-07-15 발견)

- **무엇:** Jill Valentine의 Magnum "최대 장탄으로 재장전 시" 노멀공격댐 +30%/9라운드
  버프 트리거 — "마지막 탄"(매거진을 실제로 비우는 발사) 마커의 **거울상**으로,
  "재장전 직후 첫 발"을 표시하는 마커가 필요한데 현재 없음. 같은 재장전 이벤트에
  Acid Ammo(30초 지속딜 DoT, 재장전마다 겹쳐 갱신)도 걸려 있어 함께 막힘.
- **막힌 유닛 (1, 확인분):** jill-valentine (Magnum 스택 버프 + Acid Ammo DoT). 둘 다
  jill의 기존 인코딩(eb2, ⚠)에서 보류 중이던 항목인데, 재확인 결과 필요한 건 "코어파괴"류
  트리거가 아니라 이 마커임이 밝혀짐.
- **필요한 확장:** `attack_rate.py`에 매거진 "시작" 발사 시각 계산(기존
  `magazine_last_bullet_times`/`charge_last_bullet_times`의 거울상) + `per_shot_rules`에
  대응 모드(`"first_bullet"` 등). 규모 소(~30 loc, gap #1 "마지막 탄" 확장과 동형).
- 참고: `jill_valentine.py` docstring.

### 참고 — gap #7로 안 풀리는 사례: rapi-red-hood

Rapi: Red Hood의 120-노멀 카운터는 버프/넉을 직접 발동하는 게 아니라 **프로젝타일을
발사해 두었다가 풀버스트 진입 시 그 프로젝타일이 폭발**하는 구조(2단계: 발사 이벤트 →
지연된 별도 트리거의 폭발). 거기에 버스트 자체도 2단계(1단계 서포트 / 3단계 2808%
projectile_explosion 넉, "as additional damage")로 나뉘어 있어 복잡하다. 이건 단순
per-shot 트리거가 아니라 **무기/프로젝타일-런치 상태머신** 갭(gap #2 Pattern B에 더
가까움) — gap #7·#9 어느 것으로도 안 풀림. 확인만 하고 보류(2026-07-15).

---

## 이미 만든 것 (참고)

- **instant_nuke** (`instant_damage_percent` Pulse): 자기 버스트가 아닌 트리거의 즉발 넉
  (Brid: Silent Track). 2026-07-10.
- **periodic_nukes**: 버스트와 무관한 자체 고정 쿨다운 반복 넉 (Helm: Aquamarine,
  4초). 2026-07-10.
- **데미지 타입 모델링 (gap #4)**: sustained/distributed/true/projectile_explosion
  버프를 인스턴스 타입에 게이팅. 2026-07-10.
- **periodic 스킬 트리거**: 자체 쿨다운 있는 Skill1/2가 t=cd,2cd…에 버프/디버프를
  반복 발동(범용 전투 규칙). `simulate_raid`의 `periodic_rules`. 첫 소비자 Takina
  Inoue(Battlefield Control, cd15s). 2026-07-11.
- **per-shot 트리거 + record-then-compute (gap #1)**: 발사 카운트 트리거
  (`per_shot_rules`, after/every N) + 모든 넉을 "버프 적용 후" 일괄 계산해 per-shot
  스쿼드 버프가 버스트 넉까지 반영. 첫 소비자 Brid: Journey Ahead. 2026-07-11.
- **탄수("N round") 지속시간 버프**: "for N round(s)"는 초가 아니라 **대상 아군의
  다음 N발**로 만료. `RoundGrant` + `round_buff_rule` → 샷 루프가 정확히 그 N발만
  덮는 timed Effect로 변환(squad는 아군별 개별 소모). 첫 소비자 Zwei/Miranda.
  2026-07-12.
- **최고 final ATK top-N 타겟팅**: "N ally unit(s) with the highest final ATK"를
  적용 시점 실시간 랭킹으로 정확 대상 지정. `SquadContext.base_atk`+`top_atk_slugs`,
  `slugs:` 스코프, `highest_atk_buff_rule`. 첫 소비자 Miranda. 2026-07-12.
- **이름있는 자원 / 캡 스택 카운터 (gap #2 Pattern A)**: 수량 기반 자원을 결정론적 fill
  스케줄로 정의 → count를 시각의 함수로 계산(`resource_count`, phase-order 안전). 각
  count-스케일 버프를 fill/만료 이벤트 위 **스텝 함수(델타 Effect)**로 방출 → `total_for`
  누적합 = value_fn(count). 연속 누적(캡에서 정지)·시한 만료·티어(레벨 파생)·core-conditional
  fill·**periodic fill**(고정 타이머, 샷 무관) 지원. `ResourceSpec`/`ResourceBuff`,
  `linear_resource_buff`/`leveled_resource_buff`, raid_simulator resolution 패스. 첫
  소비자 Modernia/Guillotine: Winter Slayer/Cinderella. 2026-07-12.
- **count-스케일/게이팅 넉 + multi-hit 버스트 넉**: 버스트(또는 반복 tick)에서 발동하는
  넉이 자원 count에 따라 스케일/게이팅되는 경우(`resource_scaled_nukes` — `record()`가
  `resource_gate`를 실어두고 phase 2에서 각 이벤트 자신의 시각으로 `resource_count`
  재조회 후 퍼센트 해석, 반복 tick은 매 tick이 독립적으로 최신 count 반영) + "N회
  연속 공격" 버스트가 N개 개별 히트로 기록되는 `burst_hit_counts`(디펜스가 히트당 flat
  차감이라 한 방으로 합치면 오차 발생). 첫 소비자 Cinderella(mirror 넉 + 10연타)/
  Julia-signature(5연타)/Guillotine(Extermination Hero-Level DoT). 2026-07-12.
- **자원 reset(pre/post value) + `resource_gated_buffs` + FB창 한정 fill + squad-burst-cycle-conditional
  fill + `dynamic_hit_count_nukes`**: eb3 Pattern-A 배치(Soda·Maiden)에서 자원
  primitive를 여섯 방향으로 확장.
  - `SquadContext.reset_resource`/`resource_count_before_reset`: 자원을 증분이 아니라
    **고정값으로 SET**(Soda의 Golden Chip이 버스트에서 17로 리셋). `resource_count`는
    조회 시각 이전 최신 reset을 베이스라인으로 씀; `resource_count_before_reset`은 reset
    직전 값을 노출(리셋 전 스택 수 게이팅용).
  - `("per_shot_every_during_full_burst", N)` fill: 풀버스트 창 안의 발사만 세는 자원
    채우기 — `simulate_burst_cycle`의 이벤트 로그(`full_burst_start`/`full_burst_end`
    페어)로 계산.
  - `ResourceSpec.resets` + 시간순 fill+reset 리플레이: resolution 패스가 flat fill
    스케줄과 reset 이벤트를 시각순으로 병합·재생(각 reset의 pre-value가 이전 fill/reset을
    정확히 반영). 기존 무-reset 자원(Modernia/Guillotine/Cinderella)엔 동일 출력 확인.
  - `resource_gated_buffs`: `resource_scaled_nukes`의 버프판 — 버스트 시점 자원 count로
    게이팅되는 버프. 넉과 달리 버프는 "phase 2" 지연계산이 없어서, **resolution 패스
    안에서** (`on_tier_fire` 아님) `context.burst_times[slug]`를 순회해 게이트 통과 시
    Effect를 직접 추가. 첫 소비자 Soda(ATK+65.25%/15s, 리셋前 count≥30 게이팅).
  - `_resolve_squad_burst_cycle_resource`: 자원 소유자 본인 발사가 아니라 **스쿼드
    전체 버스트-사이클 이벤트**(임의 유닛의 버스트1 발동, 풀버스트 진입 등)로 채워지고
    **자원 자신의 현재 값**에도 조건 거는 fill — `simulate_burst_cycle`의 이벤트 로그
    위에서 진짜 상태를 순회(flat 결정론 스케줄이 아님). 동시각 이벤트 순서(자기 버스트
    reset이 각 이벤트 처리 시 인라인으로 체크됨, 별도 정렬 단계 없음)가 burst1→2→3→FB진입의
    **엄격한 순서**(Fienn 확인, 2026-07-12)에 의존. 첫 소비자 Maiden(MP: 임의 유닛 버스트1
    발동 시 MP==0이면 +1, 풀버스트 진입 시 MP≥1이면 +1).
  - `dynamic_hit_count_nukes`: 버스트 넉의 **히트 수 자체**가 자원 값인 경우 —
    `resource_count_before_reset`으로 각 히트를 기록. `record()`/`_damage_instance`에
    `extra_flat_atk` 파라미터 추가(기존 `extra_charge_bonus`와 동일한 선례) — 특정 넉에만
    최대체력 비례 flat_atk를 붙여 다른 데미지 인스턴스로 새지 않게 함. 첫 소비자
    Maiden(Diamond Dust, 히트수=MP).
  - 2026-07-12. 상세: `engine-capabilities.md`, `special-mechanics.md`,
    `soda_twinkling_bunny.py`/`maiden_ice_rose.py` docstring.
- **`fire_delay`+`own_burst_delayed` + own-status-window fill + `full_burst_bonus_eligible`
  + `resource_scaled_nukes`의 `resource` 선택화**: eb4 배치(Asuka·Mana)에서 자원
  primitive를 추가로 네 방향 확장.
  - `dynamic_hit_count_nukes`의 `fire_delay`(초) + `ResourceSpec.resets`의
    `"own_burst_delayed"` 트리거(같은 delay): 버스트 자신의 시각이 아니라 **버스트 후
    delay초 뒤**에 넉이 발동하고 자원이 리셋됨 — 자기 상태(예: Annihilation State)가
    끝나는 시점에 발동하는 넉을 위함. 첫 소비자 Asuka(Annihilation, 6.62%, 9초 지연).
  - `("per_shot_every_during_own_status_window", n, duration)` fill:
    `per_shot_every_during_full_burst`와 같은 아이디어지만 창이 **스쿼드의 풀버스트
    창이 아니라 소유자 본인의 버스트 시각을 앵커로 한 고정 길이 창**(`context.burst_
    times`) — 자기 상태창이 풀버스트 창과 다른 시각/길이일 때 필요. 첫 소비자
    Asuka(Anti A.T. Field, 노멀10회마다·9초 Annihilation State 창 한정).
  - `full_burst_bonus_eligible`: `record()`/`_damage_instance`와 `Pulse`에 옵트인
    플래그 추가, 이미 있는 `full_burst_windows`로 인스턴스 자신의 시각을 체크 —
    Fienn의 "as additional damage" 텍스트 규칙(`docs/decisions.md` 참고)의 실제 배선.
    기본값 False라 기존 47명(신규 2명 포함) 중 옵트인 안 한 인스턴스는 전부 비활성.
    같은-순간 경계 주의: `full_burst_start`는 그걸 유발한 티어3 버스트와 **같은
    타임스탬프**에 발동하므로, delay=0인 옵트인 넉은 경계에서 "창 안"으로 읽힐 수
    있음(이번 배치엔 영향 없음 — Asuka의 옵트인 넉은 둘 다 지연되거나 버스트와 무관한
    타이밍). 첫 소비자 Asuka(두 "as additional damage" 넉 모두).
  - `resource_scaled_nukes`의 `resource` 필드 선택화: 자원 스케일링이 필요 없는 순수
    반복틱 DoT(`resource_gate=None`)도 같은 tick_count/tick_interval 루프를 재사용 —
    가짜 자원을 만들 필요 없음. 첫 소비자 Mana(Fatal Error!, 396%/초 10틱).
  - 2026-07-12. 상세: `engine-capabilities.md`, `special-mechanics.md`,
    `asuka_shikinami_langley_wille.py`/`mana.py` docstring.
- **FB창/자기상태창 한정 per-shot 트리거 (gap #7)**: `per_shot_rules`에 창 한정 모드
  두 개 추가 — `"every_during_full_burst"`(threshold=N)와
  `"every_during_own_status_window"`(threshold=`(N, window_duration)`) — 창 안의
  발사만 세어 임계치마다 버프/넉을 **직접** 발동(자원 fill 전용이던 기존 창 한정
  경로와는 별개). `_resource_fill_times`의 창 필터 계산 재사용, 기존 after/every/
  last_bullet 모드와 나란한 순수 추가. 첫 소비자 Soda(Lucky Golden Chip 공동발동
  버프)/Asuka(Anti A.T. Field 15.62% 상태게이팅 넉). 2026-07-15. **후속 소비 배치
  (같은 날):** Grave(Overheat II/III, 자기 버스트 상태창 한정 노멀30/60회마다
  자버프)/Velvet(Bullets of Love, 풀버스트 한정 풀차지/노멀50회 카운터).

## 만들지 않는 것 (딜 개념 아님 — defer 유지)

- **attack speed / charge speed / hit rate** (15 유닛이 언급): 엔진의 딜 공식에
  들어가는 개념이 아니라 배선해도 inert. 이런 게 유닛 가치의 대부분이면 얇은
  인코딩이 정직한 답. (`engine-capabilities.md`의 "Stats the engine does NOT consume".)

---

## 권장 착수 순서

- ~~#4 데미지 타입 배선~~ — ✅ 완료 (2026-07-10, 데미지 타입 모델링).
- ~~#1 per-shot 트리거 + 카운터~~ — ✅ 완료 (2026-07-11, `per_shot_rules` + record-then-compute).
- ~~#2 자원 트래킹 (Pattern A)~~ — ✅ 완료 (2026-07-12, named-resource).
- ~~count-스케일 넉 경로~~ — ✅ 완료 (2026-07-12, `resource_scaled_nukes` + `burst_hit_counts`
  + periodic fill; 첫 소비자 Julia/Julia-signature/Cinderella/Guillotine).
- ~~자원 reset + resource_gated_buffs + FB창 한정 fill + squad-burst-cycle-conditional
  fill + dynamic_hit_count_nukes~~ — ✅ 완료 (2026-07-12, eb3 Pattern-A 배치: Quency·
  Soda·Maiden).
- ~~fire_delay+own_burst_delayed + own-status-window fill + full_burst_bonus_eligible
  + resource_scaled_nukes의 resource 선택화~~ — ✅ 완료 (2026-07-12, eb4 배치: Asuka·
  Mana). Pattern A는 이제 (Ark Ranger류 Pattern B와 소수 미검증 후보를 제외하면)
  사실상 소진됨.
- ~~#7 FB창/자기상태창 한정 per-shot 트리거~~ — ✅ 완료 (2026-07-15,
  `per_shot_rules`의 `every_during_full_burst`/`every_during_own_status_window`
  모드; Soda·Asuka 잔여 소비). 같은 날 기존 per-shot 능력만으로 helm-aquamarine·
  anis-sparkling-summer도 신규 인코딩(Phase A1). **같은 날 후속 배치로 grave·velvet도
  gap #7 소비 완료** (Overheat II/III·Bullets of Love). jill-valentine 재검증 중
  신규 소규모 갭 **#9 reload 후 첫 발 마커** 발견(미착수). rapi-red-hood는 gap
  #7·#9 어느 것으로도 안 풀리는 프로젝타일-런치 상태머신으로 확인, 보류.
1. **막힌 나머지 per-shot 유닛 재인코딩 배치** — gap #7 소비자는 이제 Soda·Asuka·
   Grave·Velvet 4명, 남은 후보는 modernia(검증 전) 하나. 이 배치의 나머지 가치는
   gap #1/#2 잔여 per-shot 유닛(rei-ayanami류 등)에 있음 — 데이터 확인 → 인코딩.
2. **#2 Pattern B (시간감쇠 게이지·변신)** + **#3 무기종/티어부분집합 스코프** + **#5
   boss_element** + **#6 FB창 periodic** + **#8 자원-fill-트리거 타 유닛 버프**
   (Maiden 잔여) + **#9 reload 후 첫 발 마커**(Jill 잔여) + **not-in-Full-Burst
   per-shot 창 필터**(gap #7 거울상, Velvet Sticky Fingers 잔여) — 각 수요 1명,
   필요할 때.

각 확장은 TDD로, 인벤토리가 증명한 최소 범위만. 착수 시 이 문서의 해당 유닛 목록으로
"진짜 풀리는지"를 검증하고, 풀린 유닛은 배치 인코딩한다.
