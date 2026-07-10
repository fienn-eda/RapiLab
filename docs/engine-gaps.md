# 엔진 갭 인벤토리 (Engine Gap Inventory)

현재 시뮬레이션 엔진이 **표현하지 못해서 인코딩을 defer 중인 스킬 메커니즘**을
한곳에 모아, "어떤 엔진 기능을 만들면 몇 명이 풀리나"를 데이터로 보고 우선순위를
정하기 위한 문서. `special-mechanics.md`(패턴 카탈로그)와
`encoded-nikkes.md`(유닛별 보류 내역)의 상위 집계판이다.

- 마지막 갱신: 2026-07-10
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
| 1 | **per-shot 트리거 + 발사 카운터** (노멀공격 N회 / 풀차지 N회 / "마지막 탄" / N shot마다) | ~30 (합집합) | 큼 (~100–180 loc + 테스트) | 신규 트리거 |
| 2 | **자원/스택 트래킹** (배터리·탄약주머니·N스택 누적) | 16 | 중 (~60–100 loc) — 대개 #1에 의존 | 신규 상태 |
| 3 | **narrow subset scope** (무기종별 / 티어+선버스트 대상) | 9 | 무기종: 소(~20 loc) / 티어부분집합: 중(~60 loc) | 신규 스코프 |
| ~~4~~ | ~~sustained / distributed / true / projectile-explosion damage 배선~~ | 5 / 4 / 4 / — | **완료 (2026-07-10, 데미지 타입 모델링)** | 스탯 배선 |
| 5 | **enemy-element 조건** (룰에서 boss_element 접근) | 1 (+기존 Brid, Helm:Aqua) | 소 (~30 loc) | 컨텍스트 확장 |
| 6 | **periodic-during-Full-Burst 넉** (풀버스트 창 안에서만 N초마다) | 1 (Ada) | 소 (~30 loc, periodic_nukes 변형) | 타이밍 변형 |
| — | ~~버스트 외 트리거 즉발 넉~~ / ~~자체 쿨다운 주기 넉~~ | — | **완료** (instant_nuke / periodic_nukes) | 참고 |
| — | attack/charge speed·hit rate (딜 아님) | 15 | **구현 안 함** (딜 개념 아님, defer 유지) | 범위 밖 |

> **핵심 결론:** #1 하나가 압도적이다. 노멀공격 카운터(20명)와 풀차지 카운터(19명)는
> **같은 기반 메커니즘**(유닛의 발사를 세면서 임계치마다 룰 발동)으로 묶을 수 있어,
> 하나만 만들면 두 그룹의 합집합(~30 유닛)이 풀린다. #2 자원 트래킹도 대부분
> "part 파괴 / 풀차지 발사"로 채워지므로 #1이 선행 조건이다. **#1이 첫 번째 확장으로
> 가장 높은 ROI.**

---

## 갭 상세

### 1. per-shot 트리거 + 발사 카운터 — **최우선**

- **무엇:** "노멀 공격 N회 후", "풀차지 공격 N회 후 / 시", "마지막 탄 발사 시",
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

### 2. 자원 / 스택 트래킹

- **무엇:** 유닛 개인 자원(배터리·탄약주머니)이나 N스택 누적을 채웠다 소모하며
  자버프·변신·넉을 켠다. 예: Ark Ranger Black 배터리, Velvet ammo pouch,
  Anti A.T. Field 30스택.
- **왜 막힘:** 수량 기반 자원 트래킹 프리미티브가 없다(현재는 boolean status flag뿐).
- **막힌 유닛 (16):** ark-ranger-black, asuka-shikinami-langley-wille, cinderella,
  guillotine-winter-slayer, helm-aquamarine, julia, laplace, maiden-ice-rose,
  mihara-bonding-chain, modernia, quency-escape-queen, raven, red-hood,
  sakura-bloom-in-summer, soda-twinkling-bunny, velvet
- **필요한 확장:** `SquadContext`에 유닛별 정수 자원(fill/drain) + 임계치 조건.
- **의존성:** 채우고/쓰는 트리거가 대개 #1(part 파괴, 풀차지 발사, 노멀 카운터)이라
  **#1 선행 필요.** 단독으로 만들면 채울 방법이 없어 무의미한 경우가 많음.
- 참고: `special-mechanics.md`의 "Ammo pouch / stored-resource mechanics".

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
- 참고: `special-mechanics.md`의 "Weapon-type-scoped buffs", "Targeting a per-member
  subset by tier + element + prior-burst".

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

## 만들지 않는 것 (딜 개념 아님 — defer 유지)

- **attack speed / charge speed / hit rate** (15 유닛이 언급): 엔진의 딜 공식에
  들어가는 개념이 아니라 배선해도 inert. 이런 게 유닛 가치의 대부분이면 얇은
  인코딩이 정직한 답. (`engine-capabilities.md`의 "Stats the engine does NOT consume".)

---

## 권장 착수 순서

- ~~#4 데미지 타입 배선~~ — ✅ 완료 (2026-07-10, 데미지 타입 모델링).
1. **#1 per-shot 트리거 + 카운터** — 단일 최대 ROI(~30 유닛), #2의 선행.
2. **#2 자원 트래킹** — #1 위에서.
3. **#3 무기종 스코프**(소) → 티어부분집합(중), **#5 boss_element**, **#6 FB창 periodic**
   — 수요 적고 소규모, 필요할 때.

각 확장은 TDD로, 인벤토리가 증명한 최소 범위만. 착수 시 이 문서의 해당 유닛 목록으로
"진짜 풀리는지"를 검증하고, 풀린 유닛은 배치 인코딩한다.
