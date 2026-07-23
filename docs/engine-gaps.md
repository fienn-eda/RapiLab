# 엔진 갭 인벤토리 (Engine Gap Inventory)

현재 시뮬레이션 엔진이 **표현하지 못해서 인코딩을 defer 중인 스킬 메커니즘**을
한곳에 모아, "어떤 엔진 기능을 만들면 몇 명이 풀리나"를 데이터로 보고 우선순위를
정하기 위한 문서. `special-mechanics.md`(패턴 카탈로그)와
`encoded-nikkes.md`(유닛별 보류 내역)의 상위 집계판이다.

- 마지막 갱신: 2026-07-22 (**무기변형 defer 잔여 배치 종결.** 2026-07-19 세그먼트
  프리미티브 착지 후에도 "무기변형 미지원"으로 defer돼 있던 유닛들을 닫았다: nayuta·
  zwei·laplace(2026-07-21) + takina·moran(2026-07-22) 인코딩, modernia·velvet은
  **편성상 제외**(둘 다 버스트 미사용 운용이라 변형이 발동 안 함 — 엔진 한계가 아니라
  편성 결정). Takina는 실측 25발 `until_shots` + 변형샷 `damage_type="true"` 고정
  (같은 bullet의 진댐 변환이 곧 이 샷들), Moran은 무한탄창이라 발수 측정 불가 →
  엔진 표준 SMG 20/초 프록시(Fienn 승인, E2E +5.54%). 무기변형은 더 이상 열린 갭이
  아니며, 남은 것은 modernia/velvet의 **버스트 미사용을 엔진에서 강제**(`burst_delay`
  skip)하는 스윕 셸 재설계 후속뿐. 상세 `docs/decisions.md` 2건.
  이전 갱신: 2026-07-20 (**신규 스탯 `element_advantage_grant` — gap #12 원소 우위
  게이팅의 부산물 버그 정리.** gap #12에서 `other_elemental_bonus`("Superior Code
  Damage")를 원소 우위 게이팅한 게 이 스탯을 뭉뚱그려 쓰고 있던 **두 개의 서로 다른
  케이스**를 노출시켰다 — (a) "Elemental Advantage Attack Damage ▲ N%" 조건부 버프
  (이미 우위를 가진 유닛에게만 지급, 게이팅이 정확히 맞는 케이스, 71명 원문 스킬텍스트
  전수 스캔 결과 110건으로 압도적 다수), (b) "Applies Elemental Advantage damage to
  `<X>` Code enemies" 부여형 스킬(우위가 없는 유닛에게 우위 자체를 만들어줌 — 게이팅이
  정확히 거꾸로 작동해 자기상쇄됨, 같은 스캔에서 로스터 전체 중 유일하게 Rapi: Red Hood
  하나). Rapi는 (a)로 인코딩돼 있어서 게이트 도입 후 그녀의 보너스가 조용히 사라졌었다
  (버프 있으나 없으나 데미지 동일 — 효과가 레지스트리에 등록되는지만 검증한 유닛 테스트는
  그린이었음, 하모니 큐브와 같은 실패 형태). 해결: `raid_simulator.element_bonus_for`가
  이 스탯을 가진 유닛에 자연 배율 대신 `1 + ELEMENT_ADVANTAGE_BONUS`를 반환(가산이 아닌
  대체라 자연 우위와 중복 안 됨, 원소 정체성 자체는 안 바꿔서 다른 유닛의
  `element:<Name>` 스코프 버프엔 여전히 무자격). 같은 배치에서 딸려나온 사전 존재 버그:
  Rei Ayanami의 자기우위 버프가 `boss_is_element("Iron")`으로 게이팅돼 있었는데, 코멘트가
  "Fire > Iron"으로 정당화한 것과 달리 `elements.py`의 실제 사이클은 Water>Fire>Wind>
  Iron>Electric>Water — Fire는 Wind를 이기지 원문에 원소 명시도 없음. 게이트 도입 후 두
  조건이 상호배타가 돼 그녀의 버프가 어떤 보스에서도 발동 불가능해졌던 것을 게이트 제거로
  수정. 상세는 `docs/decisions.md`의 원소 우위 게이팅 ADR + amendment 참고, 스탯 카탈로그는
  `.claude/skills/nikke-skill-encoding/references/engine-capabilities.md`.
  이전 갱신: 2026-07-20 (**gap #12 완료 — 하모니 큐브 효과 배선.** 전원 Resilience
  큐브 Lv.15 착용을 가정(전역 1종, 유닛별 선택은 다음 확장으로 defer)하고 값을
  `tables.json`(`resilience_cube`)에서 유도해 배선 — 재장전 속도 29.69% / 우월 코드
  대미지 19.09%, 인게임 툴팁 대조 완료. 부수로 `other_elemental_bonus`(우월 코드
  대미지)를 원소 우위 게이팅. 상세는 아래 gap #12 참고.
  이전 갱신: 2026-07-19 (**무기변형 계획 2 착지 — v1이 이월한 잔여 3건 전부
  해소**: cinderella-crystal-wave가 `registry.MODE_VARIANTS`(소유 유닛 1개를 후보
  슬러그 여러 개로 로스터가 fan-out, 덱 탐색은 두 enumeration 경로 모두
  `_no_variant_clash`로 같은 base의 변형 동시 편성을 금지, pruning 휴리스틱의
  내부 참조덱도 정합하게 보강) 경유로 `-mg`/`-snipe` 두 정적 슬러그로 갈라짐 —
  전투 전 모드 고정이라 상태머신이 아니라 기존 평범한 무기 경로를 두 번 타는
  것뿐. rapi-red-hood의 120노멀 프로젝타일 발사기가 `SquadContext.
  full_burst_windows`(FB 창 [시작,종료) 목록 노출) + `boss_core_hittable()`
  조건 헬퍼로 완성(부착 누적 → 다음 FB 진입에서 일괄 폭발, `scheduled_nukes`
  두 개 — 부착/폭발 — 로 표현, 신규 `projectile_attachment` 데미지 타입이
  `projectile_explosion`과 나란히) + 신규 슬러그 `rapi-red-hood-b1`(Combat
  Assist B1 대역을 실제 B1 후보로 편성, `VARIANT_BURST_TIERS`로 base와 다른
  티어에 착석, `SOLE_TIER1_SLUGS`로 진짜 B1과 동시 편성 금지 — 원래 이번 배치
  범위엔 없었으나 착수 중 추가). snow-white-heavy-arms는 검증 패스 결과 **신규
  상태머신이 필요 없었음** — Auto Fire는 기존 per-shot 룰을 그대로 타고, Seven
  Dwarves Fully Active는 세그먼트(3.2초 차지 2발, +528% 차지댐을 프로필의
  `charge_damage_percent`에 접어 덱 차지댐 버프가 계속 곱해짐, 세그먼트 프로필은
  신규 `caster_weapon_stats` 스킬값 주입으로 자기 기본무기 스탯을 읽음)이며, 신규
  `every_during_segment`/`every_outside_segment` per-shot 모드(샷 시각이 아니라
  레코드 정체성으로 매칭 — 세그먼트 종료와 재개 매거진의 첫 샷이 같은 시각을 가질
  수 있어 시각 매칭은 둘 다 만족시켜버림, 구조적으로 상호 배타)가 강화/평시
  Auto Fire의 이중계상을 막는다. 4개 신규 엔진 확장 상세는 "이미 만든 것" 참고,
  velvet 변형딜·laplace base 5초 변형만 계속 보류 — 상세는
  `docs/superpowers/specs/2026-07-18-weapon-transform-design.md`(상태: 계획 2
  착지 완료).
  이전 갱신: 2026-07-19 (**weapon-mode segments v1 착지 — 무기변형 엔진
  프리미티브 완료**: `attack_rate.generate_segmented_shots()`(세그먼트 단위 ShotRecord
  타임라인 — 세그먼트 안에서 기본무기 침묵, 종료 시 새 매거진 즉시 재개,
  `until_shots`/`end` 두 창 형태, `charge_time` 프로필은 라이브 차지속도 버프 반영,
  명시적 `rate_of_fire` 프로필은 실측 앵커라 케이던스 버프 미적용, 프로필별 옵셔널
  `damage_type`) + `simulate_raid(..., weapon_mode_schedules=)` 옵트인 배선 — **전
  유닛이 세그먼트 생성기 경유**(빈 세그먼트 = 기존 출력과 비트 동일, SR_ODD 1.19초
  차지 동치 테스트로 검증), first/last-bullet 마커도 레코드 플래그 기반으로 전환.
  소비: snow-white·maxwell(신규, 버스트 단발 캐논 변형) · laplace-signature(신규
  슬러그, 10초 창 First+93틱) · red-hood(기존 `scheduled_nukes` 근사에서 마이그레이션
  — 정적 차감/상수 접기 제거, 덱 차지댐 버프가 변형샷에 곱해짐, 총딜 ~+1.6%). 남은
  무기변형은 계획 2 백로그로 이월(cinderella-crystal-wave-mg/-snipe 듀얼슬러그·
  rapi-red-hood FB창 노출·snow-white-heavy-arms 검증 패스, velvet/laplace base 변형은
  보류 확정) — 상세는 "이미 만든 것" 및
  `docs/superpowers/specs/2026-07-18-weapon-transform-design.md`(상태: v1 구현 완료)
  참고.
  이전 갱신: 2026-07-18 (**아군 총탄 카운터 해소 — 확장 불필요**: `scheduled_nukes`의
  `context.shot_times`가 전 유닛 타임라인을 담고 있어 모듈 병합으로 스쿼드 합산
  카운터 표현 가능 — Little Mermaid Bubble Barrage ⚠→✅. 같은 날: **red-hood
  재검증 — Pattern B 아님, 확장 없이 인코딩 완료**.
  "게이지=charge speed=딜 아님" 판정은 Phase S(charge_speed_percent 배선) 이전의
  낡은 것. 무기변형 창은 Fienn 실측(10초 33발·무한탄창) 앵커 `scheduled_nukes`.
  Pattern B 잔여 후보는 mihara·elegg 2명으로 감소 — gap #2 상세 참고.
  **→ gap #2 Pattern B 소진 (2026-07-19): 남은 2명 다 Pattern B가 아니었다.**
  착수 전 검증에서 mihara·elegg 모두 **시간감쇠 게이지도 임계치 변신도 없고**
  결정론적 fill을 가진 평범한 자원(Pattern A) 유닛임이 확인됨 — red-hood와
  같은 종류의 낡은 분류였다. 둘 다 인코딩 완료. 소비한 엔진 확장 4건:
  자원 reset의 `value_fn`(post = f(pre); delta·floor·임계분기를 한 필드로 포섭) ·
  `dynamic_hit_count_nukes`의 `hit_count_fn`(카운트→히트수 분기) ·
  **다중 소스 fill**(`ResourceSpec.fill`이 (fill spec, amount) 리스트를 받아 한
  자원을 서로 다른 비율/증가량으로 급유; 신규 fill kind `at_battle_start` /
  `on_full_burst_end_after_own_burst`) · `scheduled_nukes`의 `resource_gate`
  (전투 전체 스케줄 DoT를 스택수로 스케일 — 기존엔 버스트 앵커 `resource_scaled_nukes`뿐).
  **교훈: '동시각 fill은 reset에 먹힌다'** — `resource_count`가
  `fill_time <= baseline_time`인 fill을 버리므로, reset과 같은 순간에 놓인
  재충전은 사라진다. Mihara의 방출을 창 끝 +`AFTER_WINDOW_EPSILON`에 놓아 해결
  (스킬 텍스트도 '풀 버스트 타임 종료 **후**'라 의미상으로도 맞음).
  같은 날 이전 갱신: **gap #10 완료 — `per_shot_rules` `"sequence"` 모드,
  Scarlet: Black Shadow 인코딩**. 단일 풀차지 카운터가 단계별 요구치 테이블(3/6/9)을
  걷고, 자기 버스트 창(10초) 안에서는 테이블이 1/2/3으로 교체 — 카운트/스테이지는
  경계를 넘어 이어지고(Fienn 판정), 스테이지는 `count >= 활성 요구치`면 발동이라
  테이블 교체로 진행이 유실되지 않음. 같은 배치 부수 확장 2건: **`every_outside_
  full_burst` 모드**(gap #7 거울상 not-in-FB 창 필터 — Velvet Sticky Fingers 소비,
  아래 참고 섹션 해소) · **Pulse에 `damage_type`**("as Distributed Damage" per-shot
  넉이 이제 `distributed_damage_up` 버킷과 곱해짐 — Scarlet 6/9단계 소비, Neon
  문서의 펄스 경로 한계 해소). **modernia 검증 종결(Fienn 정정): Giant Leap은
  상태창 무관 전투시작 기준 200히트 카운터 — gap #7 아님, 기존 `every`로 인코딩
  완료. gap #7 후보 소진.** 이전 갱신: **Raven·Sakura 인코딩 — `scheduled_nukes`에 소유자 발사
  시각 노출**. schedule 함수가 `context.shot_times[slug]`로 자기 발사 타임라인을 읽을
  수 있게 됨(엔진이 이미 `shot_times_by_slug`를 갖고 있어 신규 계산 없음, Ein 무영향).
  소비: Raven(Shock Wave — 풀차지마다 68.46% 지속댐 5틱, 인스턴스 중첩). Sakura는 확장
  없이 인코딩(Full Glory가 배틀스타트 강제발동+cd30 → 스케줄이 컨텍스트 무관).
  **Raven 부위파괴는 Ark Ranger식 floor/ceiling 브래킷**(Single Point Attack, Fienn
  판정) — 부위파괴 이벤트 자체는 여전히 미모델. **정정: 검증 배치의 "raven 확장 불필요"
  판정은 틀렸음** — 스킬 텍스트만 보면 기존 프리미티브로 되는 듯했으나, 착수해보니
  per-shot DoT를 걸 경로가 없었다. 텍스트 검증과 실제 배선 사이에 이 정도 간극이 있음.
  이전 갱신: **미검증 5유닛 검증 배치 + `scheduled_nukes` 확장**.
  로드맵의 "미검증(풀차지/distributed)" 5유닛을 실제 텍스트로 검증한 결과:
  **ein 언블록→인코딩 완료**(아래 신규 확장) · **raven·sakura-bloom-in-summer는
  기존 프리미티브로 인코딩 가능**(부위파괴 연동만 defer, 다음 배치) ·
  **scarlet-black-shadow는 신규 소규모 갭**(gap #10, 창 한정 per-shot threshold
  오버라이드) · **milk-blooming-bunny는 강제재장전/탄약제거 상태머신 갭**(gap #11).
  **정정: "true의 DEF 무시 여부 Fienn 확인 대기"는 이미 해결됨** —
  `raid_simulator.py`가 `true` 타입을 `enemy_def=0`으로 계산 중이고
  `damage-formula-reference.md`도 확정. 이 낡은 메모가 ein을 불필요하게 막고 있었음.
  이전 갱신: 2026-07-16 (**Phase C 배치 — gap #3·#6·#8·#9 완료.**
  #3 member-subset scope: `SquadMember.weapon` + `member_subset_buff_rule`(트리거 시점
  라이브 필터 → `slugs:` 스코프 해석, 신규 Effect scope 없음). 소비: Ark Ranger Black
  (Wind-AR 아군 지속댐)·Arcana(Magician/Strength 선버스트 Electric B3)·Tove(SG 아군
  공속+flat ATK, 데이터 재수집)·Ada Wong(신규, Covert Support 선버스트 B3).
  #6 periodic-during-FB: `periodic_nukes`에 `during_full_burst`/`hit_count`/
  `own_burst_interval`. 소비: Ada Wong(Flash Grenade 420% 진댐, 자기버스트 창 1초 틱
  Fienn 판정)·Little Mermaid(Bubble Wave 63.36%×4). #8 자원-fill-트리거 아군 버프:
  `resource_fill_triggered_buffs` 파라미터+레지스트리 맵. 소비: Maiden ⚠→✅.
  #9 first-bullet 마커: `attack_rate` first-bullet 트리오 + `per_shot_rules`
  `"first_bullet"` 모드 + RoundGrant 2차 패스 리팩터 + `normal_attack_damage_multiplier`
  (노멀공격 전용 Final-ATK 항). 소비: Jill Valentine ⚠→✅(Magnum 9탄 배수·Acid refresh
  정상상태 DoT, Fienn 판정). 이전 갱신: **Ark Ranger Black (gap #2 Pattern B) 브래킷으로 우회
  완료** — 시간감쇠 게이지·변신을 일반 primitive로 풀지 않고, 신규 보스 플래그
  `BossProfile.part_destructible`로 floor(변신=버스트당 10초 창)/ceiling(변신=전투
  시작부터 영구) 두 갈래를 하드코딩. 부위파괴로 게이지가 차는 메커니즘 자체는 여전히
  미모델(엔진에 부위 개념 없음) — 이 유닛 한정 우회일 뿐, Pattern B 일반 프리미티브는
  아직 안 만들어짐. 상세는 `docs/superpowers/specs/2026-07-16-ark-ranger-black-transformation-design.md`
  및 아래 gap #2 참고. 이전 갱신: gap #5 완료 — `SquadContext.boss_element` +
  `boss_is_element` 조건 + `enemy_def_percent` 배선. 소비: brid-silent-track ⚠→✅
  (Wind Damage Taken 디버프)·helm-aquamarine(Electric Damage Taken + 추가딜 불릿)·
  marciana-marine-study(신규, Fienn의 rapture=1/Flagged=보스/High-Risk=Electric 가정).
  헬퍼 `buff_rule`/`refreshing_buff_rule`/`instant_nuke_pulse_rule`에 옵셔널 condition
  추가. 이전 갱신: gap #7 완료 — `per_shot_rules`에 창 한정 모드
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
| 2 | **자원/스택 트래킹** (배터리·탄약주머니·N스택 누적) | 16 | **Pattern A 완료 (2026-07-12, named-resource)** — Pattern B(시간감쇠 게이지·변신) 일반 프리미티브 잔여 (ark-ranger-black은 2026-07-16 `part_destructible` 브래킷으로 개별 우회) | 신규 상태 |
| ~~3~~ | ~~narrow subset scope~~ (무기종별 / 티어+선버스트 대상) | 9 | **완료 (2026-07-16 Phase C, `member_subset_buff_rule` — Ark·Arcana·Tove·Ada 소비)** | 신규 스코프 |
| ~~4~~ | ~~sustained / distributed / true / projectile-explosion damage 배선~~ | 5 / 4 / 4 / — | **완료 (2026-07-10, 데미지 타입 모델링)** | 스탯 배선 |
| ~~5~~ | ~~enemy-element 조건~~ (룰에서 boss_element 접근) | 3 (Brid·Helm:Aqua·Marciana) | **완료 (2026-07-16, `boss_is_element` + enemy_def_percent 배선)** | 컨텍스트 확장 |
| ~~6~~ | ~~periodic-during-Full-Burst 넉~~ (풀버스트 창 안에서만 N초마다) | 2 (Ada·Little Mermaid) | **완료 (2026-07-16 Phase C, `during_full_burst`+`hit_count`+`own_burst_interval`)** | 타이밍 변형 |
| ~~7~~ | ~~풀버스트/자기상태창 한정 per-shot 트리거~~ (fill이 아니라 버프/넉 직접 발동) | 4 (Soda·Asuka·Grave·Velvet) | **완료 (2026-07-15, `per_shot_rules`의 `every_during_full_burst`/`every_during_own_status_window` 모드)** | 신규 트리거 변형 |
| ~~8~~ | ~~자원-fill-트리거 타 유닛 버프~~ (자원 소유자 아닌 아군에게 버프) | 1 (Maiden) | **완료 (2026-07-16 Phase C, `resource_fill_triggered_buffs`)** | 신규 트리거 |
| ~~9~~ | ~~reload 후 첫 발("first bullet after reload") per-shot 마커~~ | 1 (Jill Valentine) | **완료 (2026-07-16 Phase C, `first_bullet` 모드 + `normal_attack_damage_multiplier`)** | 신규 트리거 변형 |
| — | ~~버스트 외 트리거 즉발 넉~~ / ~~자체 쿨다운 주기 넉~~ | — | **완료** (instant_nuke / periodic_nukes) | 참고 |
| — | ~~교차 유닛 트리거 (타 유닛 버스트에 반응)~~ | 1 (Prika→Mint) | **완료 (2026-07-11, `ally_burst_activate`)** | 신규 트리거 |
| — | ~~자원 reset / resource_gated_buffs / squad-burst-cycle-conditional fill / dynamic_hit_count_nukes~~ | — | **완료 (2026-07-12)** — Soda·Maiden 소비 | 신규 상태/트리거 |
| ~~—~~ | ~~attack/charge speed~~ (발사 간격 → 딜) | 2 (Dorothy·Tove) | **완료 (Phase S, 2026-07-16)** — `attack_speed_percent`/`charge_speed_percent` 배선 | 발사 타임라인 |
| ~~10~~ | ~~소환체 가변 케이던스 스케줄~~ (살아있는 개체 수가 공격 주기를 바꿈) | 1 (Ein) | **완료 (2026-07-17, `scheduled_nukes`)** | 신규 방출 경로 |
| ~~10~~ | ~~창 한정 per-shot threshold 오버라이드~~ (버스트가 요구 카운트를 3/6/9 → 1/2/3으로 변경) | 1 (Scarlet: Black Shadow) | **완료 (2026-07-18, `per_shot_rules` `"sequence"` 모드 — Scarlet 인코딩)** | 트리거 변형 |
| ~~11~~ | ~~**강제 재장전 / 탄약 제거 상태머신**~~ | 1 (Milk: Blooming Bunny) | **완료 (2026-07-20)** — 신규 타임라인 프리미티브 불필요(샷 0개 세그먼트 + `reload_time_with_speed` 음수 분기 + `burst_anchored_buffs`) | 재분류 |
| — | **부위파괴 이벤트** (gap #2 Pattern B와 동근) | 3+ (Raven·Sakura·Mihara) | 미착수 — ark-ranger는 `part_destructible` 브래킷으로 개별 우회 | 신규 이벤트 |
| 13 | **차지-카운트 트리거 무기 변환** (Warm Up 스택 → 변신 + 변환상태 카운터/단계 자원) | 1 (Laplace: Ultimate Hero) | 미착수 — 중간+ | 신규 트리거+상태 |
| — | hit rate · Burst Gauge fill speed (딜/타이밍 아님) | 15 | **구현 안 함** (defer 유지) | 범위 밖 |

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
- **잔여 변형:** (a) ~~**아군 총탄 카운터**(스쿼드 전체 발사 누적, per-caster 아님)~~ —
  **완료 (2026-07-18, 확장 불필요)**: Little Mermaid의 Bubble Barrage(아군 총탄
  500마다 85%×10연타)를 `scheduled_nukes`로 해결 — schedule 함수가 받는
  `context.shot_times`가 **전 유닛의 발사 타임라인**을 담고 있어(소유자 전용이
  아님), 모듈이 병합·정렬 후 매 500번째 발사 시각에 히트를 방출. 신규 스쿼드
  카운터 primitive는 만들지 않았고 필요하지도 않았음. (b) **크리티컬 히트
  카운터 — ✅ **해소 (2026-07-20, `every_n_critical_hits`)**. 2026-07-12 Julia 시그니처
  인코딩 중 '영구 defer'로 판정했던 항목이나, EVE 인코딩에서 뒤집혔다:**
  "N회 크리티컬 히트 후" 트리거는 엔진의 기대값 기반 크리 모델(각 히트가 `crit_rate`
  확률로 스케일되는 연속값 — 실제 per-hit RNG 안 굴림)과 안 맞아서 "이 샷이 실제
  크리였는가"라는 이벤트가 없다. 해법은 이벤트를 만드는 게 아니라 **딜 경로가 이미 하는
  기대값 환산을 카운터에도 적용**하는 것: 샷마다 그 시점의 라이브 크리율을 누적해 임계
  N을 넘을 때마다 발동(나머지 이월). **고정 발수로 접지 않는 게 핵심** — Fienn 수용
  조건(2026-07-20)이 '덱 크리 버프가 반영돼야 한다'였고, 빌드시점 `N / 자기크리율`은
  아군 크리버퍼를 통째로 무시한다. 한계: 샷 루프가 유닛별로 돌아 **나중에 처리되는
  아군의 per-shot 규칙이 거는 크리 버프는 미반영**(버스트/FB 트리거 크리 버프는 반영 —
  통상적인 크리 버퍼는 여기 해당). 소비: EVE(per-shot 모드) · **Julia 시그니처(2026-07-20 완료)**. 후자는 Crescendo가
  **캡 5 스택**이라 per-shot 모드로는 부족해 같은 누적기를 쓰는 자원 fill
  `("per_critical_hit_every", N)`를 함께 추가했다 — 두 경로는
  `_expected_crit_positions`를 공유한다.
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
  ~~diesel-winter-sweets~~(2026-07-19 인코딩 — RL은 charge 무기라 매 발사가 풀차지,
  `per_shot_every 1`로 해결됨), ein, laplace, liberalio, maiden-ice-rose, maxwell,
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
- **Pattern B — 시간감쇠 게이지 + 임계치 변신 (일반 프리미티브 잔여):** Ark Ranger
  배터리(부위파괴 +50%, 100%에서 변신, 1%/0.2초 감쇠), Mihara 체인. **part-destruction
  이벤트에 추가로 막힘**(엔진에 부위 개념 없음 → 가상 스케줄 발명하지 않고 defer,
  Fienn 2026-07-12).
  - **ark-ranger-black ⚠(2026-07-16, 브래킷 우회로 인코딩 완료):** 일반 Pattern B
    게이지 프리미티브를 만드는 대신, 배터리가 결국 "변신 ON/OFF"라는 이진 상태로만
    딜에 영향을 준다는 점을 이용해 신규 보스 플래그 `BossProfile.part_destructible`로
    **floor**(파츠파괴 없음 — 변신은 버스트당 10초 창만, `not_condition(boss_part_
    destructible())`)/**ceiling**(파츠파괴 있음 — 변신 영구, `battle_start`부터)
    두 브래킷을 하드코딩. 부위파괴 이벤트 자체(게이지가 실제로 어떻게 차는지)는
    여전히 미모델 — 이 유닛의 답을 "알려진 상한/하한 사이"로 좁혔을 뿐, 다른 Pattern B
    후보(Mihara 등)에 재사용 가능한 일반 게이지 primitive는 아니다. 상세는
    `docs/superpowers/specs/2026-07-16-ark-ranger-black-transformation-design.md`,
    `ark_ranger_black.py` docstring, `test_ark_ranger_bracket.py`(end-to-end
    floor<ceiling 검증) 참고.
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
- **Pattern B로 잔여(16 중):** mihara-bonding-chain, velvet(ammo pouch·풀차지 트리거),
  laplace(Hero Vision·풀차지), raven/sakura(sustained DoT 스택·별 갭) 등.
  **정정(2026-07-18): red-hood는 Pattern B가 아니었음** — "charge speed·딜 아님"은
  Phase S 배선 이전의 낡은 판정이고, 스택은 Raven식 카운터(정상상태 10스택 상시),
  버스트 Step 1/2/3은 상태머신이 아니라 버스트 슬롯 선택(B3 고정 → Step 3만),
  Step 3 무기변형은 Fienn 인게임 실측(10초 33발·무한탄창)을 앵커로 `scheduled_nukes`
  33발/창(이중계상 노멀샷 정적 차감)으로 모델. **엔진 확장 없이 인코딩 완료**
  (`red_hood.py` docstring 참고). (ark-ranger-black은 2026-07-16
  `part_destructible` 브래킷 우회로 인코딩 완료 — 위 참고, 일반 Pattern B 프리미티브
  소비는 아님.)
- 참고: `special-mechanics.md`의 "Named resource / capped stack counter",
  "Resource-scaled / gated burst nuke", "Multi-hit burst nuke",
  `engine-capabilities.md`의 ResourceSpec/resource_scaled_nukes/burst_hit_counts.

### 3. narrow subset scope — ✅ 완료 (2026-07-16, Phase C `member_subset_buff_rule`)

- **해결:** 신규 Effect scope를 만들지 않고, 트리거 시점에 라이브 필터
  `member_filter(member, context) -> bool`로 멤버를 골라 기존 `slugs:` 스코프로
  해석(`top_atk_slugs` 선례). `SquadMember`에 옵셔널 `weapon` 필드 추가(로스터가
  덱 dict에 스레딩, 기본 None이라 기존 컨텍스트 불변). 무기종·티어·선버스트
  (`burst_used_this_cycle`) 어떤 조합도 한 헬퍼로 커버.
- **소비 (4):** ark-ranger-black(Wind-AR 아군 Sustained+77.5%)·arcana ⚠→✅
  (Magician/Strength — 선버스트 Electric B3, Wheel of Fortune 게이팅)·tove
  (SG 아군 공속+42.24% 상시 + flat ATK 24.21%/스택×3 — char_tove.json 재수집)·
  ada-wong(신규 — Covert Support 선버스트 B3 flat ATK+진댐). drake-signature·
  arcana-fortune-mate의 SG squad-근사 정밀화는 **완료(2026-07-18)** — drake는
  `member_subset_buff_rule`, arcana는 라이브 필터 액션(except-self/스택 판독이
  섞여 커스텀 액션 유지). arcana 자신이 받던 except-self 과대적용도 제거됨.

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
- **막혔던 유닛 (참고):** sustained(5): ark-ranger-black, diesel-winter-sweets(2026-07-19 인코딩),
  mana, mihara-bonding-chain, sakura-bloom-in-summer · distributed(4): bready,
  milk-blooming-bunny, quency-escape-queen, scarlet-black-shadow · true(4):
  ada-wong, chisato-nishikigi, ein, jill-valentine · projectile-explosion:
  Mint(기존 emit 즉시 유효), Rapi(버스트 넉 태깅). — 엔진은 준비됐고, 각 유닛의
  헤드라인 버프가 실제 딜을 움직이려면 **같은 덱에 해당 타입 딜러가 있어야** 함
  (버프는 곱할 대상이 있어야 유효).
- **잔여:** 각 딜러의 타입 인스턴스(지속 넉 등)를 실제로 인코딩하는 건 개별 유닛
  인코딩 작업. Prika/Anis:Star의 projectile explosion 버프는 여전히 다른 갭(풀차지
  트리거/미인코딩)에 막힘.

### 5. enemy-element 조건 (룰에서 boss_element 접근) — ✅ 완료 (2026-07-16)

- **무엇이었나:** "적이 X Code일 때만" 발동하는 디버프/추가딜. SkillRule 액션이
  boss_element에 접근 불가(당시 `raid_simulator`만 앎).
- **해결:** `SquadContext.boss_element`(raid_simulator가 주입) + `boss_is_element(element)`
  조건 헬퍼. `buff_rule`/`refreshing_buff_rule`/`instant_nuke_pulse_rule`에 옵셔널
  `condition` 파라미터 추가(게이팅된 불릿이 비게이팅과 같은 빌더 재사용). 규모 소.
- **소비자 (3):**
  - **brid-silent-track ⚠→✅:** 두 Wind-Code Damage Taken 디버프(Ignition Sequence
    풀버스트 진입 시 +15.12%/10s, Journey Ahead 노멀10회마다 +12.12%/10s) 모두
    `boss_is_element("Wind")` 게이팅. 이제 잔여 없음.
  - **helm-aquamarine ⚠(부분 해소):** Suppression Fire의 Electric Damage Taken 디버프
    (정상상태 5스택=28.2% squad, battle_start, Electric 게이팅) + Aegis Cannon Overload의
    Electric 추가딜 불릿(164.83%, 자기 버스트 시, **FB 보너스 미적용** — Burst 2라 FB창
    직전 발동, Fienn 2026-07-16). Electric-Code 불릿 잔여 없음.
  - **marciana-marine-study ⚠(신규 인코딩):** Iron AR B3. Fienn 가정(rapture=1,
    Flagged Target=보스, High-Risk 불릿은 Electric 보스 게이팅) 하에 Elemental Advantage
    Attack Damage·High-Risk DEF 디버프·High-Risk 20노멀 넉을 `boss_is_element("Electric")`로
    게이팅. **enemy_def_percent 배선**(아래) 소비. 잔여: Flagged Target ATK 스코프 모호(defer),
    적 처치 트리거 넉 사본, 6+rapture 넉.
- **부산물 — enemy_def_percent 배선 (2026-07-16):** DEF ▼ 디버프(Marciana의 High-Risk
  Target DEF -10.56%)를 위해 `damage_formula`가 이미 지원하던 `enemy_def_percent`를
  `raid_simulator._damage_instance`에 한 줄 배선(`damage_taken_up`과 동형, squad 스코프
  적 디버프). 기존엔 inert였음. DEF=0 바닥(reference)엔 아직 도달하는 유닛 없어 클램프 미도입.
- 참고: `special-mechanics.md`의 "Enemy-element-conditional debuffs",
  `brid_silent_track.py`/`helm_aquamarine.py`/`marciana_marine_study.py` docstring.

### 6. periodic-during-Full-Burst 넉 — ✅ 완료 (2026-07-16, Phase C)

- **해결:** `periodic_nukes` 스펙에 옵셔널 필드 3개 — `"during_full_burst": True`
  (각 FB 창 시작 앵커로 창 안에서만 틱), `"hit_count": N`(틱당 N개 개별 히트,
  `burst_hit_counts`와 같은 사유), `"own_burst_interval": (interval, duration)`
  (소유자 본인 버스트로 열린 창은 interval로 틱 — Ada의 "activation time condition
  ▼1초/10초" Fienn 판정 2026-07-16). 기본값 부재 시 기존 스펙과 동일 출력.
- **소비 (2):** ada-wong(Flash Grenade 420% 진댐 2초마다, 자기 버스트 창은 1초)·
  little-mermaid(Bubble Wave 63.36%×4연타 1초마다).

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
  - **grave (2026-07-15 후속 배치, 2026-07-16 정정):** Overheat II/III — 자기
    버스트의 10초 상태창(Prediction) 한정 노멀30/60회마다 자ATK+20.66%/자AD+30.8%를
    `every_during_own_status_window`로 모델링. **Fienn 실측 확인(2026-07-16):
    "continuously"는 언락-후-영구가 아니라 Prediction 중에만 활성** → II/III를
    refreshing으로 현재 Prediction 창-끝까지 부여(창 끝에 소멸, 매 사이클 재획득). 이와
    별개로 **Overheat I(노멀15회 후 자ATK+15.48%)는 언락-후-영구**로 확인돼 이제
    `after` 모드로 모델링(전투 시작 기준 노멀 카운터, Prediction 무관, II의 전제조건).
    잔여: 자힐(Prediction), +3라운드 탄약 불릿(caster 기본 탄약 불명).
  - **velvet (2026-07-15 후속 배치):** Bullets of Love — 풀버스트 중 풀차지샷마다(SR,
    N=1) 스쿼드 flat ATK(자ATK의 25.2%)+스쿼드 Charge Damage+100.8%(3초, refresh,
    Prika 선례 따라 스쿼드스코프)+풀버스트 중 노멀50회마다 자AD+15.03%/5초 + 400.92%
    넉("as additional damage"→`full_burst_bonus_eligible`)를 `every_during_full_burst`로
    모델링. ammo pouch(6000, 버스트 스테이지2마다 풀리필)는 소모량 대비 압도적으로 커서
    비제약으로 처리(자원 미모델링 — gap #2 대상 아님). 잔여: Sticky Fingers의 "풀버스트
    아닐 때" 풀차지 카운터(gap #7의 거울상인 not-in-FB 창 필터 필요, 미구현, 자기전용
    저가치), Perfect Execution 무기변형딜.
- **남은 후보:** ~~modernia(Giant Leap 상태게이팅 200히트 ATK버프) — 검증 전.~~ →
  **검증 종결 (2026-07-18, Fienn 정정):** 인게임에서 상태창과 무관하게 전투 시작부터
  200히트마다 발동 — gap #7 아님, 기존 `every` 모드로 인코딩 완료. 후보 소진.
- 참고: `special-mechanics.md`의 관련 항목, `soda_twinkling_bunny.py`/
  `asuka_shikinami_langley_wille.py`/`grave.py`/`velvet.py` docstring.

### 참고 — gap #7의 거울상: not-in-Full-Burst per-shot 창 필터 — ✅ 완료 (2026-07-18)

Velvet의 Sticky Fingers는 "풀버스트 **아닐 때**" 풀차지마다 자ATK/자AD 버프(각
30.5%, 3초)를 준다 — gap #7의 `every_during_full_burst`의 정반대 필터.
**해결:** 예정대로 `"every_outside_full_burst"` 모드로 최소 확장(FB 창 밖 발사만
세고 every-N 스텝 적용, gap #10 배치에 동승). 소비: velvet(Sticky Fingers 재인코딩
— 잔여는 무기변형딜뿐).

### 8. 자원-fill-트리거 타 유닛 버프 — ✅ 완료 (2026-07-16, Phase C)

- **해결:** `simulate_raid(..., resource_fill_triggered_buffs={owner: [spec]})` —
  spec = `{"resource", "member_filter"(member, owner_slug), "buffs":
  [(stat, value, duration)], "condition"(옵션)}`. (owner, resource)의 **모든 fill
  이벤트마다** 필터된 멤버에 `slugs:` 스코프로 refreshing 적용(연속 fill은 refresh,
  NIKKE 관례). resource_specs 해석 루프 직후(모든 fill 기록 완료 시점)·
  resource_gated_buffs 직전 패스. 레지스트리 맵 `_RESOURCE_FILL_TRIGGERED_BUFF_
  BUILDERS` + `get_resource_fill_triggered_buffs` + assemble 키.
- **소비 (1):** maiden-ice-rose ⚠→✅ — Blessings Upon You "MP 회복 시" Electric
  아군(자신 제외) 상성공댐+40.9%(Water 보스 `boss_is_element` 게이팅)·flat ATK
  20.9%/10초 refresh.

- **무엇:** 한 유닛의 자원이 채워지는 사건에 반응해 **다른** 유닛에게 버프를 주는
  패턴 — Maiden의 Blessings Upon You "MP 회복 시" 아군(Electric 코드) 버프, Soda의
  것과 유사 소비자 없음(현재는 Maiden만). `resource_gated_buffs`(2026-07-12 완료)는
  "자원 소유자 자신의 버스트 시점 게이팅"만 처리 — fill 이벤트 자체에 반응해 스쿼드의
  **다른** 멤버에게 버프를 주는 경로는 없음.
- **막힌 유닛 (1, 확인분):** maiden-ice-rose (Blessings Upon You의 아군 버프만 잔여).
- **필요한 확장:** 자원 fill 이벤트를 트리거로 스쿼드(또는 조건부 서브셋) 버프를
  거는 새 파라미터. 규모 소~중, 수요 확인 후 착수.
- 참고: `maiden_ice_rose.py` docstring.

### 9. reload 후 첫 발("first bullet after reload") per-shot 마커 — ✅ 완료 (2026-07-16, Phase C)

- **해결:** `attack_rate.py`에 `magazine_first_bullet_times`/`charge_first_bullet_
  times`/`first_bullet_shot_times`(last-bullet 트리오의 거울상, t=0 전투 개시
  매거진 포함) + `per_shot_rules` `"first_bullet"` 모드. 함께 **RoundGrant 2차
  패스 리팩터**(그랜트→Effect 변환을 유닛별 샷 루프 밖 2차 루프로 이동 — per-shot
  룰이 기록한 라운드그랜트도 변환됨, 기존 Zwei/Miranda 출력 불변) +
  **`normal_attack_damage_multiplier`**(노멀공격 전용 Final-ATK 항, phase 2에서
  노멀 인스턴스의 coefficient만 스케일).
- **소비 (1):** jill-valentine ⚠→✅ — Magnum(전투시작+풀재장전마다 다음 9탄 +30%)·
  Acid(192%/1초/30초, refresh 판정[Fienn 2026-07-16]으로 전투 내내 정상상태 →
  전체전투 주기 지속넉).

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

### 참고 — gap #7로 안 풀리는 사례였던 rapi-red-hood — ✅ 완료 (2026-07-19, 별도의 소규모 확장)

Rapi: Red Hood의 120-노멀 카운터는 버프/넉을 직접 발동하는 게 아니라 **프로젝타일을
발사해 두었다가 풀버스트 진입 시 그 프로젝타일이 폭발**하는 구조(2단계: 발사 이벤트 →
지연된 별도 트리거의 폭발). 2026-07-15엔 이걸 단순 per-shot 트리거가 아니라
**무기/프로젝타일-런치 상태머신** 갭(gap #2 Pattern B에 더 가까움)으로 확인만 하고
보류했다 — gap #7·#9 어느 것으로도 안 풀렸음.

**실제로는 상태머신도 Pattern B도 필요 없었다:** 발사(부착) 스케줄은 이미
`scheduled_nukes`가 표현할 수 있는 형태(소유자의 발사 카운터가 임계치를 넘을 때마다
결정론적 시각을 방출)였고, 막혔던 건 오직 폭발 시각 — "다음 풀버스트 진입 시각" —
을 계산할 방법이 없었다는 것뿐이었다. `SquadContext.full_burst_windows`(FB 창
`[시작, 종료)` 목록, `raid_simulator`가 무기 패스 직전에 채움) 노출 하나로 해소:
schedule 함수가 부착 시각 리스트를 계산한 뒤, 각 부착 시각보다 뒤에 오는 첫 FB 창
시작 시각을 찾아 그 시각에 폭발을 방출한다. 두 개의 독립된 `scheduled_nukes` 항목
(부착 = 신규 `projectile_attachment` 타입, 폭발 = 기존 `projectile_explosion` 타입)
으로 표현되며, 상태 전이를 시뮬레이터에 새로 가르칠 필요가 없었다 — Ein/Raven이 세운
"모듈이 스케줄 계산, 엔진은 방출만" 분업의 또 다른 소비자일 뿐. 상세는
`rapi_red_hood.py`의 `build_attachable_projectiles_scheduled_nukes` docstring.

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
- **enemy-element 조건 + enemy_def_percent 배선 (gap #5)**: `SquadContext.boss_element`
  (raid_simulator 주입) + `boss_is_element(element)` 조건 헬퍼로 "적이 X Code일 때만"
  발동하는 디버프/추가딜을 게이팅. `buff_rule`/`refreshing_buff_rule`/
  `instant_nuke_pulse_rule`에 옵셔널 `condition` 파라미터 추가. 함께 `enemy_def_percent`
  (DEF ▼ 디버프, damage_formula가 이미 지원하나 inert였음)를 `_damage_instance`에 배선
  (squad 스코프 적 디버프, `damage_taken_up`과 동형). 첫 소비자 Brid(Wind Damage
  Taken)·Helm:Aquamarine(Electric Damage Taken + 추가딜)·Marciana(Electric 게이팅
  + DEF 디버프). 2026-07-16.
- **Ark Ranger Black — gap #2 Pattern B 브래킷 우회 (2026-07-16, 일반 프리미티브
  아님):** 시간감쇠 게이지·변신을 위한 일반 primitive 대신, 배터리가 결국 "변신
  ON/OFF" 이진 상태로만 딜에 영향을 준다는 점을 이용해 신규 보스 플래그
  `BossProfile.part_destructible`을 `evaluate_deck`/`simulate_raid`→
  `SquadContext.part_destructible`로 스레딩. **floor**(파츠파괴 없음 — 변신은
  버스트당 10초 창, `own_burst_activate` + `not_condition(boss_part_destructible())`)/
  **ceiling**(파츠파괴 있음 — 변신 영구, `battle_start`부터) 두 갈래로 Transform!
  자ATK+156.19%와 Ark Black Collider 지속딜(45.87%×틱)을 하드코딩(DoT 스펙의 옵셔널
  `requires_part_destructible`로 브랜치별 게이팅). Ultimate! Meteor 지속딜(266.69%×10틱)과
  자 Sustained Damage+135.83%/10초, 노멀30회마다 자 Sustained Damage+59.6%/5초는
  양쪽 브랜치 공통. 엔드투엔드로 ceiling total_damage > floor total_damage 검증
  (`test_ark_ranger_bracket.py`). **부위파괴로 게이지가 실제로 차는 메커니즘 자체는
  여전히 미모델** — 이 유닛 전용 우회일 뿐, Mihara 등 다른 Pattern B 후보에 재사용
  가능한 일반 게이지 primitive는 아니다. 상세는
  `docs/superpowers/specs/2026-07-16-ark-ranger-black-transformation-design.md`,
  `ark_ranger_black.py` docstring 참고.

- **`scheduled_nukes`의 `context.shot_times` (2026-07-17, Raven):** schedule 함수가
  소유자의 발사 시각을 읽어 **자기 발사에서 파생되는 딜**을 만들 수 있음 —
  `SquadContext.shot_times[slug]`(raid_simulator의 무기 패스가 채움, 무기 스탯 없으면
  빈 리스트). 시그니처는 `(context, fight_duration)` 그대로라 기존 소비자(Ein) 무변경.
  첫 소비자 Raven(Shock Wave: 풀차지마다 5틱 지속댐, 인스턴스가 겹쳐 쌓임 — 스택 상한
  10은 RL 케이던스상 도달 불가라 자원 모델링 불필요). **"풀차지마다 N초 DoT" 패턴이
  이제 일반적으로 풀림.**
- **`scheduled_nukes` — 소환체 가변 케이던스 (2026-07-17, Ein):** `periodic_nukes`가
  고정 간격만 지원해서 막히던, **살아있는 개체 수가 공격 주기를 바꾸는 소환체** 딜을
  위한 옵트인 경로. 스케줄이 결정론적(소환 시각 = 전투 시작 + 소유자 버스트 시각,
  수명은 고정)이라는 점을 이용해 **유닛 모듈이 시각 리스트를 계산하고 엔진은 방출만**
  한다 — 소환체 수명 관리가 시뮬레이터로 새지 않음. spec =
  `{"schedule": fn(context, fight_duration) -> times, "percent", "damage_type"(옵션),
  "full_burst_bonus_eligible"(옵션)}`. `fight_duration` 이후 시각은 드롭. 첫 소비자
  Ein(Near Feather). 기존 경로 무영향(파라미터 부재 = 아무것도 방출 안 함).
- **gap #10 배치 (2026-07-18):** `per_shot_rules` `"sequence"` 모드(단계별 요구치
  테이블 + own-burst-window 교체, gap #10 상세 참고 — Scarlet) ·
  `"every_outside_full_burst"` 모드(FB 창 밖 발사만 카운트, gap #7 거울상 —
  Velvet Sticky Fingers) · **Pulse `damage_type`**(per-shot/instant 넉의 타입
  버킷 게이팅 — 기본 "attack"이라 기존 소비자 출력 불변, Scarlet distributed
  스테이지 첫 소비).
- **Phase C 배치 (gaps #3·#6·#8·#9), 2026-07-16:**
  - **member-subset scope (#3):** `SquadMember.weapon`(옵셔널) + `_helpers.
    member_subset_buff_rule(trigger, member_filter, buffs, condition, refreshing)` —
    트리거 시점 라이브 필터를 `slugs:` 스코프로 해석(신규 Effect scope 없음,
    top_atk_slugs 선례). 소비: Ark(Wind-AR)·Arcana(선버스트 Electric B3)·Tove(SG)·
    Ada Wong(선버스트 B3).
  - **periodic_nukes FB창 옵션 (#6):** `during_full_burst`(창 시작 앵커 틱)·
    `hit_count`(틱당 N히트)·`own_burst_interval`(자기 버스트로 열린 창의 강화 틱).
    소비: Ada Wong(Flash Grenade 진댐)·Little Mermaid(Bubble Wave).
  - **resource_fill_triggered_buffs (#8):** 자원 fill 이벤트마다 필터된 아군
    부분집합에 refreshing 버프. 소비: Maiden(Blessings MP-회복 아군 버프).
  - **first-bullet 마커 + 노멀공격 배수 (#9):** `first_bullet_shot_times` 트리오 +
    `per_shot_rules` `"first_bullet"` 모드 + RoundGrant 2차 패스 리팩터(퍼샷 룰이
    기록한 그랜트도 변환) + `normal_attack_damage_multiplier`(노멀 전용 Final-ATK
    항). 소비: Jill Valentine(Magnum/Acid).
- **weapon-mode segments (v1, 2026-07-19):** 무기 프로필 자체가 버스트/상태에 따라
  바뀌는 유닛(무기 변형)을 위한 세그먼트 primitive. `attack_rate.
  generate_segmented_shots()` — 유닛별 ShotRecord 타임라인을 세그먼트 단위로 생성
  (세그먼트 안에서는 기본무기 발사를 침묵시키고, 종료 시 새 매거진으로 즉시 재개;
  `until_shots`/`end` 두 창 형태; `charge_time` 프로필은 라이브 차지속도 버프를
  그대로 반영, 명시적 `rate_of_fire` 프로필은 실측 앵커라 케이던스 버프 미적용;
  프로필별 옵셔널 `damage_type`). `simulate_raid(..., weapon_mode_schedules=
  {slug: schedule_fn})`로 옵트인 배선 — **전 유닛이 세그먼트 생성기를 경유**하도록
  통일(빈 세그먼트 = 기존 출력과 비트 동일, SR_ODD 1.19초 차지 동치 테스트로 검증).
  first/last-bullet 마커도 이제 레코드 플래그에서 나옴(raid_simulator가 낡은 마커
  함수를 더 이상 호출하지 않음). 레지스트리 맵 `_WEAPON_MODE_SCHEDULE_BUILDERS` +
  `get_weapon_mode_schedules` + roster 스레딩.
  - **소비:** snow-white(신규, 버스트 5초 차지 499.5%×10 캐논, `until_shots: 1`) ·
    maxwell(신규, 버스트 2초 차지 813.42%×3 캐논, `until_shots: 1`) ·
    laplace-signature(신규 슬러그, 애장품 — 10초 고정 창, First 1회 + 노멀 93회,
    Fienn 실측 2026-07-19) · red-hood(기존 ⚠ `scheduled_nukes` 근사에서 세그먼트로
    마이그레이션 — 정적 차감/상수 접기 제거, 덱 차지댐 버프가 변형샷에 곱해짐,
    총딜 ~+1.6%).
  - **남은 백로그(계획 2)**: cinderella-crystal-wave-mg/-snipe 듀얼슬러그(세그먼트
    비소비, 정적 프로필 2벌) · rapi-red-hood(`scheduled_nukes` context에 FB창 노출
    필요, 세그먼트 대상 아님) · snow-white-heavy-arms 검증 패스(기존 per-shot +
    multi-hit 프리미티브로 풀리는지) · velvet 변형딜(저가치 보류 확정) · laplace
    base의 5초 변형(실측 없음, 보류).
  - 상세: `docs/superpowers/specs/2026-07-18-weapon-transform-design.md`
    (상태: v1 구현 완료).
- **`SquadContext.full_burst_windows` + `core_hittable` 노출, `boss_core_hittable()`
  조건 헬퍼 (계획 2, 2026-07-19):** 무기 패스가 이미 계산해 두고 있던 두 값 —
  FB 창 `[시작, 종료)` 목록과 이번 시뮬의 코어 활성 여부 — 를 SkillRule/스케줄
  함수가 읽을 수 있게 `SquadContext`에 얹었을 뿐, 새 계산은 없다.
  `full_burst_windows`는 `raid_simulator`가 무기 패스 직전에 채우며, 모듈 계산
  스케줄(`scheduled_nukes`)이 "다음 FB 진입 시각"을 찾는 데 쓴다(rapi-red-hood의
  프로젝타일 폭발 앵커). `boss_core_hittable()`는 기존 `boss_part_destructible()`과
  같은 모양의 조건 헬퍼로, `context.core_hittable`을 읽어 "코어 활성 적 한정" 넉을
  게이팅한다(cinderella-crystal-wave MG 모드의 833.79% 코어스트라이크 넉). 첫
  소비자: rapi-red-hood(`full_burst_windows`), cinderella-crystal-wave-mg
  (`boss_core_hittable`).
- **`projectile_attachment` 데미지 타입 + `projectile_attachment_damage_up` 스탯
  (계획 2, 2026-07-19):** 기존 `projectile_explosion` 타입/스탯 페어와 나란한
  두 번째 프로젝타일류 타입 — "부착된" 프로젝타일 자체의 데미지(폭발 데미지와는
  별개 버킷)를 게이팅. `raid_simulator._TYPE_BUCKETS`에 한 줄 추가. 첫 소비자:
  rapi-red-hood(Attachable Projectiles의 부착 히트 + Power of Inheritance
  Stage 3의 421.2% 창).
- **모드-변형 듀얼슬러그 확장 — `MODE_VARIANTS`/`VARIANT_BURST_TIERS` (계획 2,
  2026-07-19):** 소유 유닛 1개가 여러 덱 후보 슬러그로 나뉘는 패턴 — 기존
  `-signature` 듀얼슬롯(julia/drake/laplace, 유저의 애장품 **투자** 상태를
  나타내고 프론트에서 해석)과는 다르게, 이건 유저의 **플레이/편성 선택**(전투 전
  고정 무기모드, 또는 어느 버스트 슬롯에 세울지)을 나타내고 백엔드 로스터
  로더에서 해석된다. `registry.MODE_VARIANTS: {base_slug: (variant_slug, ...)}`
  를 `user_roster.load_roster`가 읽어 소유 상태 하나를 후보 슬러그 전부로
  fan-out(`MODE_VARIANTS.get(character_slug) or (character_slug,)`). 변형이
  캐릭터의 명목 버스트 티어와 다른 슬롯에 앉으면 `VARIANT_BURST_TIERS`가
  override(rapi-red-hood-b1이 B3 대신 B1). 변형의 무기 프로필이 base와 다르면
  `_WEAPON_PROFILE_OVERRIDE_BUILDERS`(+ `get_weapon_profile_override`)가 스킬값
  조립 후 프로필을 교체(cinderella-crystal-wave-snipe의 SR 프로필). 덱 탐색은
  두 enumeration 경로(조합 생성·순열 정련) 모두 `_no_variant_clash`로 같은
  base의 변형 두 개가 동시 편성되는 걸 금지하고, pruning 휴리스틱의 내부 참조덱
  구성(`_reference_deck`/`_variant_safe_top`/`_swap_slot`/`_cross_tier_reference`)도
  같은 규칙으로 정합하게 보강됐다(교차 티어 변형이 참조덱 측정을 오염시키지
  않도록 대체 참조덱으로 측정, `deck_search.py` 참고). 진짜 단독 버스트 슬롯
  대역(예: Combat Assist가 실제 B1 옆에서는 자기모순이 되는 rapi-red-hood-b1)은
  `SOLE_TIER1_SLUGS`로 같은 티어의 다른 유닛과도 동시 편성을 막는다. 첫 소비자:
  cinderella-crystal-wave(-mg/-snipe), rapi-red-hood(base/-b1).
- **세그먼트 게이팅 per-shot 모드 `every_during_segment`/`every_outside_segment`
  + `caster_weapon_stats` 스킬값 주입 (계획 2, 2026-07-19):** weapon-mode
  세그먼트(v1) 안/밖에서 다른 배수로 넉을 내야 하는 유닛을 위한 `per_shot_rules`
  모드 두 개 — gap #7의 `every_during_full_burst`/`every_outside_full_burst`와
  같은 짝 구조이지만 필터가 FB 창이 아니라 세그먼트 소속이다. **샷 "시각"이
  아니라 레코드 "정체성"(`ShotRecord.in_segment`)으로 매칭** — 세그먼트가
  `until_shots`로 끝나는 순간과 매거진형 기본무기가 새 매거진으로 재개하는
  순간이 동일한 시각을 가질 수 있어(세그먼트 종료 시 즉시 재개가 v1의 확정
  시맨틱), 시각 매칭이었다면 그 경계 샷 하나가 두 모드를 동시에 만족시켜
  이중계상을 일으켰을 것 — 정체성 매칭은 이를 구조적으로 막는다(snow-white-
  heavy-arms 배치 중 발견, `raid_simulator.py`의 window_fire_indices 계산부
  주석 참고). 함께, 세그먼트 프로필이 자기 기본무기 스탯(예: 차지 배수)을 읽어야
  하는 유닛을 위해 `roster.py`의 스킬값 조립이 `caster_weapon_stats`(조립된
  `weapon_stats` 전체)를 다른 `caster_*` 캐스터-베이스스탯 키들과 나란히 주입.
  첫 소비자: snow-white-heavy-arms(Auto Fire의 평시/Fully-Active 배수 분기,
  Fully Active 세그먼트 프로필의 차지댐 조립).

### 10. 창 한정 per-shot threshold 오버라이드 — ✅ 완료 (2026-07-18, `"sequence"` 모드)

- **무엇이었나:** Scarlet: Black Shadow의 Fleetly Fading Breakthrough는 풀차지
  3/6/9회에 각기 다른 효과(283.03% 단일 / 565% distributed / 848.03% distributed,
  "한 번에 하나만")를 내는데, **버스트(Fleetly Fading Strike)가 그 요구 카운트를
  10초 동안 1/2/3으로 바꾼다**. `per_shot_rules`의 threshold는 정적이라 표현 불가.
- **해결:** `per_shot_rules`에 `"sequence"` 모드 — threshold 자리에
  `{"requirements": [3,6,9], "own_burst_window": (10.0, [1,2,3])}`, rules 자리에
  **스테이지별 룰 리스트**. 단일 러닝 카운터가 스테이지 요구치를 걷고(스테이지는
  `count >= 활성 요구치`면 발동, 마지막 스테이지 후 리셋), 자기 버스트 앵커 창
  안에서는 요구치 테이블만 교체 — **카운트/스테이지는 경계를 넘어 이어짐**(Fienn
  판정 2026-07-18; `>=` 발동이라 창 진입 시 이미 넘어선 요구치도 다음 발사부터
  차례로 발동, 진행 유실 없음). 샷당 최대 1스테이지("Only one effect at a time").
  발사 타임라인을 시간순으로 한 번 걸어 `{shot_time: stage_rules}`를 사전계산
  (`_sequence_fire_rules`).
- **소비 (1):** scarlet-black-shadow 신규 인코딩(⚠ — Asura의 FB진입 매거진 100%
  즉시 재장전만 gap #11 동류로 보류). 6/9단계 distributed 넉은 같은 배치의 Pulse
  `damage_type` 확장 소비.
- 참고: `scarlet_black_shadow.py` docstring, `special-mechanics.md`의
  "Staged shot-count table" 항목.

### 11. ~~강제 재장전 / 탄약 제거 상태머신~~ — ✅ **해소 (2026-07-20)**, 신규 발사-타임라인 프리미티브 없이

- **무엇:** Milk: Blooming Bunny의 Embarrassment 루프 — 풀차지를 0.5초 이상 유지하면
  상태 진입 → 290% Distributed + **탄약 100% 제거 + 강제 재장전**(재장전 속도 50%
  고정) + 자ATK+118.7%/40초. 상태 중 Pierce Damage+64.7%. 버스트의 Overconfident는
  10초간 Embarrassment 면역 + 447.7% Distributed 2초마다.
- **왜 막혔다고 봤나:** "탄약을 강제로 비우고 재장전시킨다"는 프리미티브가 없고,
  발사 타임라인은 매거진 크기/공속에서 결정론적으로 생성되므로 스킬이 중간에 리셋할
  경로가 없다고 판단했다.
- **왜 틀렸나 (2026-07-20):** ① 진입 조건이 "상태가 아닐 때"라 **자기 버스트 1회당
  1회**만 진입한다(Fienn: 버스트 면역으로만 해제) — 매 풀차지 루프가 아니라 국소적
  이벤트다. ② **세그먼트 경계가 이미 탄창을 끊는다** — `_base_shot_records`는 각 구간을
  `window_start`에서 새 탄창으로 재시작한다(무기변형 v1의 resume 시맨틱). 즉 "탄약 100%
  제거 + 강제 재장전"은 **샷 0개짜리 세그먼트**다. ③ 재장전 속도 조작은 이미
  `reload_speed_percent` 콜러블로 배선돼 있었고, 감소 방향 공식만 틀려 있었다(아래).
- **실제로 필요했던 것 2건:** `reload_time_with_speed`의 음수 분기(속도 감소를 시간
  증가의 거울로 — 2초 기본에 −50%면 4초가 아니라 **3초**, Fienn 인게임 수치) ·
  버스트 시각에 앵커되어 "다음 자기 버스트까지" 지속되는 버프를 위한 소형 패스
  `burst_anchored_buffs`(`UNTIL_NEXT_OWN_BURST`). 둘 다 소규모.
- **교훈:** Elegg·Mihara의 Pattern B 오분류와 같은 계열 — "엔진이 못 한다"는 판정을
  실제 운용(진입 빈도)과 기존 프리미티브의 부수 효과(세그먼트 resume) 양쪽에 대조하기
  전에 확정하면 확장 규모를 크게 과대평가하게 된다.
- 참고: `data/lootandwaifus/char_milk-blooming-bunny.json`.

### 12. 하모니 큐브 효과 배선 — ✅ 완료 (2026-07-20, 전원 Resilience Lv.15 가정)

- **해결:** 큐브를 유저 입력에서 없애고, **모든 유닛이 Resilience 큐브(렐릭 베어)
  Lv.15를 착용한 것으로 가정**한다. `cube_effects.py`가 `tables.json`의
  `resilience_cube`(구 `cube_sample`) 레코드에서 재장전 속도 29.69% / 우월 코드 대미지
  19.09%를 유도해 `self` 스코프 영구 Effect 두 개로 매 유닛에 무조건 부여
  (`roster.py::_passive_effects`). 이전 세션이 "인덱싱이 불연속이라 지어내면 안 된다"고
  기록했던 값 리스트는 실제로는 문제가 없었다 — 슬롯 1(퀵 리로드 HC)의 스킬 레벨이 3에서
  캡되므로 리스트의 뒷부분(17.5·20·22.5…)은 그 슬롯이 도달할 수 없는 구간이었을 뿐이고,
  앞 3개는 등차수열이다. `level1`/`level2`/`level3` 배열의 정체(스탯이 아니라 큐브레벨 →
  스킬레벨 사다리)는 `docs/insights.md`("Data") 참고. 인게임 툴팁과 대조 완료
  (Fienn, 2026-07-20): 재장전 29.69% / 우월코드 19.09% — 일치.
- **미결 쟁점 해소:** 갭 발견 당시 남겨뒀던 "전역 1종 / 유닛별 / 엔진이 유닛마다 최적
  큐브를 고르게" 세 갈래 중 **전역 1종 고정**으로 결정(`docs/decisions.md`). "엔진이
  최적을 고른다"가 원리적으로 가장 정확하지만(큐브가 자유 재장착이라 덱빌딩 결정변수에
  가깝다) 큐브 카탈로그 전수 수집과 평가 비용 배수를 요구해 지금 단계엔 과함 — 유닛별
  선택 UI는 다음 확장으로 남김.
- **부수 수정(같은 작업):** `damage_formula`의 우월 코드 대미지(`other_elemental_bonus`)가
  원소 우위 여부와 무관하게 가산되던 기존 버그를 `element_multiplier > 1.0`로 게이팅.
  큐브의 안티 코드 +19.09%를 전 로스터에 배선하면서 이 오차가 확대되기 전에 고쳤다.
- **동기화 경로의 평탄 스탯도 정합:** `roster_assembly.extract_inputs`의
  `harmony_cube_lv`를 수집값 대신 `ASSUMED_CUBE_LEVEL`(=15)로 고정(옵트아웃 파라미터
  있음 — collector-parity 테스트는 실측 큐브로 검증해야 하므로 opt-out).
- **알려진 한계:** 수동 입력 경로는 사용자가 입력한 합산 ATK/HP 숫자 하나를 받아 항목별
  분해가 불가능하므로, 입력 시점 미착용 유닛은 평탄 스탯이 Lv.15 큐브분(ATK 2,780/HP
  83,400)만큼 부족하다(raid400 ATK 중앙값 기준 약 2.7% 과소). 큐브 효과(재장전/우월코드)
  자체는 정상 적용된다. 수동 경로 자체를 없애는 근본 해결은 800~1,200 LOC 규모의 별도
  제품 결정으로 분리(`docs/decisions.md`).
- 상세: `docs/superpowers/specs/2026-07-20-harmony-cube-assumed-lv15-design.md`,
  `docs/superpowers/plans/2026-07-20-harmony-cube-assumed-lv15.md`.

### 13. 차지-카운트 트리거 무기 변환 (Warm Up 스택 → 변신) — 미착수 (2026-07-23)

- **무엇:** Laplace: Ultimate Hero의 핵심 딜 루프. 풀차지마다 Warm Up +1스택(차지속도
  +10%), 5스택에서 **스택 소모 + 무기 변환** "Electric Power, Fully Full Charge"
  (9.45%/발 × 120발, Pierce, 탄창 소진 시 종료 → 탄약 100% 제거) → 변환 상태 일반공격
  12회마다 Over Energy +5%(100%까지) → 100%마다 단계 상승(Max HP +2/3/7/10.5%) →
  버스트의 934.76%×단계 추가딜을 스케일.
- **왜 막혔나:** 변환 트리거가 **자기 발사(풀차지) 카운트의 누적 스택 임계치**다.
  `weapon_mode_schedules`(무기변형 v1, gap #11 경로)는 세그먼트를 battle_start / 자기
  버스트 시각에만 앵커할 수 있고, "N번째 풀차지에서 시작해 매거진 소진까지"라는
  발사-카운트 앵커가 없다. Over Energy는 그 위에 다시 변환-상태-한정 일반공격 카운터 +
  단계 자원을 얹는다.
- **막힌 유닛:** 1 (Laplace: Ultimate Hero). 인코딩은 버스트 넉(2953.84%) + 자버프
  몇 개(전투시작 ATK, 풀버스트 Attack Damage, 버스트 ATK)만 모델된 **얇은 스텁**으로
  들어갔다 — 주력 딜이 통째로 빠져 덱서치가 과소평가한다(`laplace_ultimate_hero.py`
  docstring의 deferred 목록).
- **확장 방향(미확정):** ① per_shot 카운트(gap #1)로 발사 타임라인 상의 변환 시작 시각을
  산출해 세그먼트 스케줄(`weapon_mode_schedules`)로 넘기는 결합 경로, ② 변환-상태 자원
  (Over Energy)을 named-resource(gap #2 Pattern A)로, 단계 추가딜을
  `resource_scaled_nuke`로. 규모 중간+ — 착수 전 실측(변환 주기·120발 케이던스)이 필요.
- 참고: `data/shiftypad/laplace-ultimate-hero.json`,
  `data/lootandwaifus/char_laplace-ultimate-hero-nikke.html`.

## 만들지 않는 것 (딜 개념 아님 — defer 유지)

- ~~**attack speed / charge speed**~~ → **모델됨 (Phase S, 2026-07-16 결정 뒤집기)**:
  180초 고정 전투에서 발사 간격이 줄면 발사 수가 늘어 딜이 증가 → `attack_speed_percent`
  (매거진 무기)·`charge_speed_percent`(차지 무기)를 `attack_rate.py`에 배선. 첫 소비자
  Dorothy: Serendipity(자기 +65%). Tove는 SG-아군 스코프라 Phase C 대기(gap #3). 근거는
  `docs/decisions.md` 참조.
- **hit rate / Burst Gauge fill speed** (여전히 미소비): 엔진의 딜 공식/타이밍에 들어가는
  개념이 아니라 배선해도 inert. 이런 게 유닛 가치의 대부분이면 얇은 인코딩이 정직한 답.
  (`engine-capabilities.md`의 "Stats the engine does NOT consume".)

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
- ~~#5 enemy-element 조건 (boss_element)~~ — ✅ 완료 (2026-07-16,
  `boss_is_element` + `enemy_def_percent` 배선; Brid ⚠→✅·Helm:Aqua·Marciana(신규) 소비).
- ~~ark-ranger-black (gap #2 Pattern B, 개별)~~ — ✅ 브래킷 우회로 인코딩 완료
  (2026-07-16, `part_destructible` 보스 플래그). Pattern B **일반 프리미티브**는
  여전히 미착수(아래 2번 항목).
- ~~#3 무기종/티어부분집합 스코프 + #6 FB창 periodic + #8 자원-fill-트리거 타 유닛
  버프 + #9 reload 후 첫 발 마커~~ — ✅ 완료 (2026-07-16 Phase C 배치; 소비
  Ark·Arcana·Tove·Ada Wong(신규)·Little Mermaid·Maiden·Jill).
2. **남은 방향:** #2 Pattern B(시간감쇠 게이지·변신, 일반 프리미티브 — Mihara류) ·
   상태머신(~~diesel-winter-sweets~~[**2026-07-19 완료** — Intro/Highlight 2슬러그,
   위 버스트 스케줄 정책 소비]·~~bready~~[완료]·~~eve~~[**2026-07-20 완료** —
   `every_n_critical_hits`]·~~milk-blooming-bunny~~[**2026-07-20 완료** — gap #11 재분류]) ·
   ~~무기변형~~(**v1+계획 2 완료, 2026-07-19** — `weapon_mode_schedules` 세그먼트
   primitive, snow-white·maxwell·laplace-signature·red-hood 소비(v1) +
   `MODE_VARIANTS` 듀얼슬러그(cinderella-crystal-wave-mg/-snipe)·
   `full_burst_windows`+`boss_core_hittable`(rapi-red-hood 발사기 완성 + 신규
   rapi-red-hood-b1)·`every_during_segment`/`every_outside_segment`(snow-white-
   heavy-arms, 신규 상태머신 불필요로 판명)(계획 2) 소비; velvet 변형딜·laplace
   base 5초 변형만 잔여(보류 확정), 상세는 위 "이미 만든 것" 참고) ·
   ~~아군 총탄 카운터~~(**2026-07-18 완료** — `scheduled_nukes`+`context.shot_times`
   병합으로 확장 없이 해결, Little Mermaid ⚠→✅) ·
   ~~not-in-Full-Burst per-shot 창 필터~~(**2026-07-18 완료** —
   `every_outside_full_burst`, Velvet Sticky Fingers 소비) ·
   ~~**유닛별 버스트 스케줄 정책**~~(**2026-07-19 완료** — `burst_cycle` 멤버가
   선택적 `burst_delay`를 가짐: `{"skip_cycles": N}`(앞 N사이클 제외) ·
   `{"not_before": T}`(T초 전 금지) · `{"min_interval": S}`(실효 쿨을 S로 연장).
   세 형태 모두 멤버별 ready time 한 곳(`_ready_at`)에 합쳐져 티어 선택과
   eligibility가 동일 산술을 유지한다(기존 fractional-CDR 반올림 회귀 방어 유지).
   **소비**: diesel-winter-sweets-highlight(`skip_cycles: 1` — 1사이클을 걸러야
   Highlight 상태가 확정되므로 정적 슬러그로는 과대평가) ·
   elegg-boom-and-shock(`not_before` 78초 + `min_interval` 54초, 둘 다 그녀의
   fill 값에서 유도). **함정**: `min_interval`은 CDR로 되감기는 `last_used_at`이
   아니라 **실제 발동 시각(`last_fired_at`)** 에서 재야 한다 — 벽시계로 차는
   자원은 아군 CDR로 빨라지지 않는다. 지연 유닛이 자기 티어에 혼자면 사이클이
   안 뜨지만, `ALLOWED_SHAPES`상 B3는 항상 2명 이상이라 탐색에선 발생 불가).

각 확장은 TDD로, 인벤토리가 증명한 최소 범위만. 착수 시 이 문서의 해당 유닛 목록으로
"진짜 풀리는지"를 검증하고, 풀린 유닛은 배치 인코딩한다.
