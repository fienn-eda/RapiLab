# 엔진 갭 인벤토리 (Engine Gap Inventory)

현재 시뮬레이션 엔진이 **표현하지 못해서 인코딩을 defer 중인 스킬 메커니즘**을
한곳에 모아, "어떤 엔진 기능을 만들면 몇 명이 풀리나"를 데이터로 보고 우선순위를
정하기 위한 문서. `special-mechanics.md`(패턴 카탈로그)와
`encoded-nikkes.md`(유닛별 보류 내역)의 상위 집계판이다.

- 마지막 갱신: 2026-07-12 (count-스케일 넉 + multi-hit burst + periodic 자원 fill 완료 반영)
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
| ~~1~~ | **per-shot 트리거 + 발사 카운터** (노멀공격 N회 / 풀차지 N회 / N shot마다) | ~30 (합집합) | **완료 (2026-07-11, per_shot_rules)** — "마지막 탄"만 잔여 | 신규 트리거 |
| 2 | **자원/스택 트래킹** (배터리·탄약주머니·N스택 누적) | 16 | **Pattern A 완료 (2026-07-12, named-resource)** — Pattern B(시간감쇠 게이지·변신) 잔여 | 신규 상태 |
| 3 | **narrow subset scope** (무기종별 / 티어+선버스트 대상) | 9 | 무기종: 소(~20 loc) / 티어부분집합: 중(~60 loc) | 신규 스코프 |
| ~~4~~ | ~~sustained / distributed / true / projectile-explosion damage 배선~~ | 5 / 4 / 4 / — | **완료 (2026-07-10, 데미지 타입 모델링)** | 스탯 배선 |
| 5 | **enemy-element 조건** (룰에서 boss_element 접근) | 1 (+기존 Brid, Helm:Aqua) | 소 (~30 loc) | 컨텍스트 확장 |
| 6 | **periodic-during-Full-Burst 넉** (풀버스트 창 안에서만 N초마다) | 1 (Ada) | 소 (~30 loc, periodic_nukes 변형) | 타이밍 변형 |
| — | ~~버스트 외 트리거 즉발 넉~~ / ~~자체 쿨다운 주기 넉~~ | — | **완료** (instant_nuke / periodic_nukes) | 참고 |
| — | ~~교차 유닛 트리거 (타 유닛 버스트에 반응)~~ | 1 (Prika→Mint) | **완료 (2026-07-11, `ally_burst_activate`)** | 신규 트리거 |
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
  넉까지 반영됨. 첫 소비자 Brid: Journey Ahead(5발마다 675% 넉). "마지막 탄"(매거진
  경계)만 잔여. `engine-capabilities.md`/`special-mechanics.md` 참고.
- **다음(후속 배치):** 아래 막힌 유닛들을 이 능력으로 재인코딩. 각 유닛 데이터 수집 후
  per-shot 룰 추가.
- **잔여 변형:** (a) "마지막 탄"(매거진 경계) — attack_rate 마커 필요. (b) **아군 총탄
  카운터**(스쿼드 전체 발사 누적, per-caster 아님) — 예: Little Mermaid의 Bubble
  Barrage(아군 총탄 500마다 850%). `per_shot_rules`는 시전자 본인 발사만 세므로 미커버.
  스쿼드 합산 카운터는 별도 확장 필요. (c) **크리티컬 히트 카운터 — 영구 defer, "만들
  능력"이 아님(2026-07-12, Julia 시그니처 인코딩 중 발견):** "N회 크리티컬 히트 후" 트리거는
  엔진의 기대값 기반 크리 모델(각 히트가 `crit_rate` 확률로 스케일되는 연속값 — 실제
  per-hit RNG 안 굴림)과 구조적으로 안 맞는다. "이 샷이 실제 크리였는가"라는 이벤트
  자체가 없어서 셀 수 없다. per-shot 카운터 확장으로도 못 푼다 — Julia(시그니처)의
  Crescendo/Marcato가 이 사유로 영구 defer.
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
  DoT), modernia ✅, cinderella ✅(Beautiful periodic fill + mirror 넉). 남은
  soda-twinkling-bunny, quency-escape-queen, maiden-ice-rose, asuka-shikinami-langley-wille
  등은 다중소스 채우기·burst-consume·스테이지 게이팅 등 잔주름이 있어 후속 인코딩
  배치(roadmap To-Do).
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
1. **막힌 ~30명 재인코딩 배치** — #1이 풀렸으니 이제 실제 유닛들에 per-shot 룰 추가
   (데이터 수집 → 인코딩). 가장 큰 실질 가치. Pattern A 자원 유닛(Soda·Quency·Maiden·
   Asuka…)도 이제 이 배치에 포함.
2. **#2 Pattern B (시간감쇠 게이지·변신)** + **#3 무기종/티어부분집합 스코프** + **#5
   boss_element** + **#6 FB창 periodic** — 수요 적고, 필요할 때.

각 확장은 TDD로, 인벤토리가 증명한 최소 범위만. 착수 시 이 문서의 해당 유닛 목록으로
"진짜 풀리는지"를 검증하고, 풀린 유닛은 배치 인코딩한다.
