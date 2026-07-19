# 인코딩된 니케 목록

`backend/app/skill_rules/registry.py`의 `ENCODED_SLUGS` 기준. 덱 추천 엔진이
고려할 수 있는 니케는 이 목록뿐이다 (인코딩 안 된 니케는 후보에서 제외됨).

- 마지막 갱신: 2026-07-19 (**무기변형 v1 착지 — red-hood 세그먼트 마이그레이션
  (docs 갱신)**. 인코딩 자체는 이전 배치(`weapon_mode_schedules` 착지)에서
  완료됨 — 기존 `scheduled_nukes` 근사(정적 이중계상 차감 + 상수로 접은 차지
  배수)를 세그먼트로 교체, 덱 Charge Damage/ATK 버프가 변형샷에 실제로 곱해짐
  (총딜 ~+1.6%, 덱 버프 없는 스팟체크). 인코딩 수/커버리지 변화 없음(65명,
  65/65) — 아래 red-hood 행 비고 갱신. 설계
  `docs/superpowers/specs/2026-07-18-weapon-transform-design.md`(상태: v1
  구현 완료), 갭 집계는 `docs/engine-gaps.md` 참고.
  이전 갱신: 2026-07-19 (**Laplace Signature 신규 인코딩**, 별도 slug
  `laplace-signature` — base `laplace`는 그대로 둠). Fienn 인게임 실측(2026-07-19):
  변형 10초 창 = First 1회 + 노멀 93회. First Damage 1455.72%를 버스트 넉으로,
  Normal Damage 22.2%×93틱을 `weapon_mode_schedules` 세그먼트(rate_of_fire=93/10)로
  모델 — Hero Vision 상시 맥스스택 가정(red-hood Glaring 정상상태 선례, Fienn 승인)으로
  틱 전부 **true** 타입 고정. 틱마다 +11.9% true 추가히트는 동일 케이던스의
  `scheduled_nukes`(`build_buster_scheduled_nukes`)로 방출, 두 경로 모두
  `context.burst_times` 앵커라 케이던스 일치. Hero Bomber는 base의 `last_bullet`과
  달리 풀차지마다 발동(`every_outside_full_burst`) — 변형 창(=자기 버스트가 여는 FB 창)
  중엔 풀차지가 없어 인게임과 정확히 일치. 프런트 `resourceIdSlugMap.ts`의
  `DUAL_SLOT_BASES`에 `laplace` 추가(julia/drake 선례와 동일, `SIGNATURE_OWNED`는
  미변경 — 소유 여부 미확인). **엔진 확장 없이 인코딩**. 65명, 커버리지/로더블 65/65.
  이전 갱신: 2026-07-19 (**Maxwell 신규 인코딩**. Straight Shot(FB진입 시 최고ATK
  2인 차지속도+43.1%/ATK 버프) — **Fienn 판정(2026-07-19): 대상 2인에 Maxwell
  자신도 포함**(공유 `top_atk_slugs`/`highest_atk_buff_rule`은 항상 캐스터를
  제외하므로 그대로 못 씀 — 캐스터 포함 랭킹을 뽑는 로컬 커스텀 액션으로 모델).
  Pierce Shot(버스트): 무기를 2초 차지·1탄 캐논으로 바꾸는 변형 — 813.42%
  샷딜/300% 풀차지딜, `weapon_mode_schedules`의 `until_shots: 1` 세그먼트
  (snow-white/red-hood 선례를 잇는 세 번째 소비자). Spark Shot(적 5기 초과 조건)은
  레이드 보스 1기 상대로 항상 거짓이라 미인코딩. **엔진 확장 없이 인코딩**.
  64명, 커버리지/로더블 64/64. 이전 갱신: 2026-07-19 (**Snow White 신규 인코딩**. 버스트가 무기를
  5초 차지·1탄 캐논으로 바꾸는 변형 — `weapon_mode_schedules`의
  `until_shots: 1` 세그먼트(red-hood 선례를 잇는 두 번째 소비자, 이번엔 측정
  앵커가 아니라 실제 차지무기라 덱 차지댐/ATK 버프가 그대로 곱해짐). Seven
  Dwarves: V & VI는 자기 쿨다운(cd15) 주기 AoE 넉(`periodic_nukes`). Determination은
  기존 `every` 모드로 충분(노멀30회마다 넉+자버프). **엔진 확장 없이 인코딩**.
  63명, 커버리지/로더블 63/63. 이전 갱신: 2026-07-18 (**Red Hood 신규 인코딩 — 낡은
  Pattern B 판정 정정**. "게이지 보상=charge speed=딜 아님"은 Phase S(발사속도 배선)
  이전 판정이었음. 버스트 Step 1/2/3은 상태머신이 아니라 버스트 슬롯 선택(B3
  고정이라 Step 3만 유효), Step 3 무기변형은 Fienn 인게임 실측(10초 33발·무한탄창)
  앵커로 `scheduled_nukes` 모델 — 엔진 확장 없이 인코딩(기존 프리미티브만 소비).
  62명, 커버리지/로더블 62/62). 이전 갱신: **매니페스트 예외 4유닛 해소 — 커버리지/로더블 전원**.
  anis-star(dotgg-소스, star_anis drop 7토큰) · asuka(lootandwaifus-소스 —
  anti_at_field 픽스처를 데이터 순서로 재전사+빌더 재번호, 50샷 임계도 슬롯에서
  읽음; annihilation 픽스처의 재현 불가 '1' 슬롯은 전사 잔재라 제거; dotgg url
  `asuka-wille` 브리지로 weapon 스탯 로드) · privaty(dotgg dollskills —
  LD Assault 픽스처를 네이티브 순서로 스왑) · neon-vision-eye(lootandwaifus-소스 —
  healthy_body 픽스처 03/04 전사 오류 교정, ∞는 숫자 토큰이 아님).
  `KNOWN_MANIFEST_EXCEPTIONS`는 이제 빈 집합 — 신규 인코딩은 매니페스트 필수.
  이전 갱신: **Scarlet: Black Shadow 신규 인코딩 (gap #10 완료)** —
  `per_shot_rules` 신규 `"sequence"` 모드(단일 풀차지 카운터가 3/6/9 단계 테이블을
  걷고, 버스트가 10초간 요구치를 1/2/3으로 교체 — 카운트/스테이지는 경계를 넘어
  이어짐, Fienn 판정). 함께 **Pulse에 damage_type 추가**(per-shot 넉의 "as
  Distributed Damage"가 이제 `distributed_damage_up` 버킷과 실제로 곱해짐 — 기존
  Neon 문서에 적혀 있던 펄스 경로 한계 해소). 같은 배치: **Velvet Sticky Fingers**
  (`every_outside_full_burst` 신규 모드, gap #7의 거울상) · **Modernia Giant Leap**
  (Fienn 정정: 상태창 무관, 전투 시작부터 노멀 200히트마다 — 기존 `every` 모드로
  해결, 마지막 gap #7 후보 소진). **61명, 매니페스트 57/61, API 로더블 57/61**.
  이전 갱신: 2026-07-17 (**Raven·Sakura: Bloom in Summer 신규 인코딩** —
  `scheduled_nukes`의 schedule 함수가 소유자의 발사 시각(`context.shot_times`)을
  읽도록 확장, Raven의 Shock Wave(풀차지마다 5초 스택 DoT)가 첫 소비자. Sakura는
  확장 없이 인코딩(Full Glory가 배틀스타트 강제발동+cd30이라 스케줄이 전투 전 확정).
  **60명, 매니페스트 56/60, API 로더블 56/60** — 남은 4명(anis-star·asuka·privaty·
  neon-vision-eye)은 픽스처 재배열 건으로 dotgg와 무관. **Raven Shock Wave 모델 정정
  (Fienn, 같은 날): 스택 카운터 1개 + 풀차지마다 수명 갱신** — 최초 구현은 "풀차지마다
  독립 5초 DoT가 겹침"으로 오독해 정상상태 5스택(실제 10스택)이 되어 그녀를 **1.9배
  과소평가**하고 있었음(Shock Wave 1.28억→2.92억). 이전 갱신: **Ein 신규 인코딩** — Near Feather 소환체 스케줄을
  신규 엔진 확장 `scheduled_nukes`로 모델(Fienn의 클라 데이터마이닝 + 영상 실측
  기반). **58명, 매니페스트 54/58, API 로더블 54/58** — dotgg weapon 파일 수집으로
  ein·ark-ranger-black·prika·marciana-marine-study가 함께 로더블이 됨(50→54).
  같은 배치에서 미검증 5유닛 검증: raven·sakura-bloom-in-summer는
  기존 프리미티브로 인코딩 가능(다음 배치), scarlet-black-shadow·milk-blooming-bunny는
  갭 확인(`engine-gaps.md` 참고). 이전 갱신: 매니페스트 예외 8유닛 배치 — crown·helm·liter·
  miranda·moran·soline-frost-ticket·volume·zwei에 dotgg-소스 매니페스트 추가,
  53/57 커버. **API 로더블 50/57** (로더블 B1 4→10명 — 5덱 분배가 실제로 5덱을
  채울 수 있게 됨). 이전 갱신: 매니페스트 배치 2 — 29유닛 추가로 45/57 커버 +
  dotgg weapon 스탯 39파일 수집 + `dotgg_slug` 브리지(ada-wong·chisato·jill·takina))
- **스킬값 매니페스트 커버리지 — 예외 없음 (2026-07-18):** 전원이
  `SKILL_VALUE_MANIFESTS`를 보유(= API 조립 가능). 이 목록은
  `test_skill_value_assembly.py`의 `KNOWN_MANIFEST_EXCEPTIONS` 가드 테스트와
  거울 구조(현재 빈 집합)라, 매니페스트 없는 신규 인코딩은 테스트가 먼저 잡는다.
  - **(2026-07-18 해소)** 픽스처 재배열 4유닛(`anis-star`,
    `asuka-shikinami-langley-wille`, `privaty`, `neon-vision-eye`) — 픽스처를
    데이터 슬롯 순서로 재전사(또는 drop_tokens)하고 빌더 읽기를 재번호해 해결.
  - **(2026-07-17 해소) `ark-ranger-black`·`prika`·`marciana-marine-study`·`ein`은
    이제 dotgg weapon 파일이 있어 전부 로더블.** 이전 "dotgg 리스팅에 없음" 기록은
    수집 전 상태였을 뿐 — 넷 다 dotgg 셧다운(2026-05) 이전 출시라 데이터가 존재한다.
    **prika 로더블화로 mint+prika Encore 시너지가 실제 덱 탐색에서 처음으로 효력을
    가진다**(로드맵이 이걸 blocker로 적어두고 있었음).
- 총 **68명** (Burst 1: 11명 · Burst 2: 16명 · Burst 3: 41명) — drake는 base/signature 듀얼슬롯 2엔트리,
  Cinderella: Crystal Wave는 MG/Snipe 모드 듀얼슬롯 2엔트리(Task 6, 2026-07-19 —
  `MODE_VARIANTS`로 배선된 첫 유닛; 시그니처와 달리 둘 다 정식 base 캐릭터라
  DUAL_SLOT_BASES/SIGNATURE_OWNED 대상 아님)
- 완성도 범례: **✅ 대부분 모델링** (생존/힐 등 딜 무관 요소만 제외) ·
  **⚠ 일부 핵심 메커니즘 보류** (딜에 영향 있으나 부분적) ·
  **🔶 상당 부분 보류** (얇은 인코딩, 실제 딜 상당수 누락 — 덱 평가에 반영 안 됨)
- 각 니케의 정확한 모델링/보류 내역은 해당 `skill_rules/<slug>.py` 모듈
  docstring 참고. 엔진이 지원하지 못하는 메커니즘 패턴은
  `.claude/skills/nikke-skill-encoding/references/special-mechanics.md`에 정리됨.

---

## Burst 1 (11명)

| 이름 | 슬러그 | 클래스 | 무기 | 원소 | 완성도 | 주요 보류 내용 |
|---|---|---|---|---|---|---|
| Anis: Star | `anis-star` | Defender | RL | Electric | ⚠ | 풀차지 추가딜(120.13% 매 풀차지, per-shot)·Stardust 버프(ATK/PE/AD)·버스트 자버프 모델됨. 버스트 Shooting Stars(버스트창 주기딜, gap #6)·재진입 분기·게이지·Explosion Radius 보류 |
| D: Killer Wife | `d-killer-wife` | Supporter | SR | Fire | ⚠ | Assault Formation 공버프(5풀차지마다 AD, per-shot) + CDR(8풀차지→7s, 매 사이클 근사) 모델됨. **skill3(Kill the Target 버스트) 보류**(Fienn) |
| Liter | `liter` | Supporter | SMG | Iron | ✅ | Volt Boost(자힐, 생존계)만 미모델 |
| Little Mermaid | `little-mermaid` | Supporter | SMG | Wind | ✅ | Bubble 5.05% 받댐증·FB창 주기넉(1초마다 63.36%×4연타, during_full_burst+hit_count, gap #6 소비 2026-07-16)·**Bubble Barrage(아군총탄 500마다 85%×10연타) 모델됨(2026-07-18)** — `scheduled_nukes` schedule 함수가 `context.shot_times` 전 유닛 타임라인을 병합해 스쿼드 합산 카운터를 계산(엔진 확장 불필요). 잔여 보류는 버스트게이지 fill(inert)뿐 |
| Miranda (애장품) | `miranda` | Supporter | SMG | Fire | ✅ | Health Up 자ATK(노멀30회마다, per_shot)·Wake Up 스쿼드 크리댐/자버프 + **최고ATK top-1 크리율(1 round=탄수 버프)**·Powering Up **최고ATK top-2 정확 타겟팅**(ATK/크리댐) 모델됨. Hit Rate(inert)만 보류 |
| Moran (애장품) | `moran` | Defender | AR | Electric | ✅ | 무기변형 자해모드·생존계만 미모델 |
| Rouge | `rouge` | Supporter | SR | Electric | ⚠ | Card Throw CDR(8풀차지→7s, 매 사이클 근사)·Sword Coin AD(후열 가정, 상시)·Game Master ATK(**15.07%로 버그수정**, 기존 30.02 오독)·Max HP 버프(flat_max_hp, inert·향후 HP스케일용) 모델됨. Shield Coin(생존)만 보류 |
| Soline: Frost Ticket | `soline-frost-ticket` | Supporter | SG | Water | ✅ | CDR만 모델링 (원래 역할이 로테이션 보조뿐) |
| Tove (애장품) | `tove` | Supporter | AR | Water | ✅ | SG아군 공속+42.24%(상시, 라이브 리드로 실제 발수 증가)·SG아군 flat ATK(자ATK 24.21%/스택×3, 15초) member_subset_buff_rule로 모델됨(gap #3 소비 2026-07-16). 잔여: Temporary Modification 노멀카운트 램프 자체(풀스택 정상상태 가정) |
| Volume | `volume` | Attacker | SMG | Wind | ✅ | Freestyle(킬 트리거, 레이드엔 무의미)만 미모델 |
| Zwei (애장품) | `zwei` | Supporter | SG | Electric | ⚠ | Pierce Equation 스쿼드 Pierce(**20.13% 1 round=탄수 버프** + 10.06% 10초)·Frame Analysis 크리율·버스트 Pierce 모델됨. 풀버스트창 노멀스택 Pierce/크리·무기변형·Cover HP(생존) 보류 |

## Burst 2 (16명)

| 이름 | 슬러그 | 클래스 | 무기 | 원소 | 완성도 | 주요 보류 내용 |
|---|---|---|---|---|---|---|
| Crown | `crown` | Defender | MG | Iron | ✅ | Royal Attire(노멀공격 카운터)만 미모델 |
| Ade: Agent Bunny | `ade-agent-bunny` | Supporter | SR | Iron | ✅ | Spy Lens 스택 누적만 미모델(정상상태 근사) |
| Anchor: Innocent Maid | `anchor-innocent-maid` | Supporter | RL | Water | ✅ | 분산 대미지 버프 인코딩됨(엔진 미연결로 현재 비활성) |
| Mast: Romantic Maid | `mast-romantic-maid` | Supporter | MG | Water | ✅ | 거의 완전 (Anchor와의 취기 스택 시너지 포함) |
| Blanc | `blanc` | Defender | AR | Wind | ✅ | 거의 완전 (Rouge/Noir 조건부 자기 CDR 포함) |
| Arcana | `arcana` | Supporter | RL | Electric | ✅ | "The Magician"/"Strength"(이미 버스트한 버스트3 전기 아군: 공댐+180%·자ATK 180% flat, 15초, Wheel of Fortune 게이팅) member_subset_buff_rule로 모델됨(gap #3 소비 2026-07-16). 잔여 보류: Magician의 스킬2 쿨감 -75%(아군 스킬쿨 미시뮬) |
| Arcana: Fortune Mate | `arcana-fortune-mate` | Attacker | SG | Fire | ⚠ | Making Memories(버스트 자크리율·AD)·Memories and Moments SG아군(자신 제외) AD + **Precious Moments(자ATK+2.49%×최대3, Full Burst당 1스택 램프, `full_burst_enter`)·Keepsake Album(SG아군(자신 포함) flat ATK=caster ATK 13%×Precious Moments 스택, 15초) 모델됨(2026-07-16)**. **SG-스코프 정밀화 완료(2026-07-18)** — squad 근사 제거, 자신이 받던 except-self 과대적용도 제거. 펠릿(Happy Memories)·Snapshots(Normal Attack Damage Multiplier)는 미지원 스탯이라 보류 |
| Grave | `grave` | Supporter | AR | Fire | ✅ | Plot Spoiler(버스트 자/스쿼드 Pierce·AD·크리율)·Heat Emission(Prediction 종료 시 발동하는 스쿼드 Pierce 토글) + **Overheat I(노멀15회 후 자ATK+15.48% 영구, gap #1 `after`)·II/III(자기 버스트의 10초 상태창 Prediction 한정 노멀30/60회 자ATK+20.66%/자AD+30.8%, `every_during_own_status_window` gap #7)** 모델됨. Fienn 실측 확인(2026-07-16): I은 언락-후-영구, II/III는 Prediction 중에만 활성 → II/III는 refreshing으로 창-끝까지 부여·매 사이클 재획득. 자힐(Prediction)·+3라운드 탄약 불릿(caster 기본 탄약 불명)만 보류 |
| Brid: Silent Track | `brid-silent-track` | Supporter | SG | Fire | ✅ | 노멀5회마다 675% 넉(per-shot) + 두 Wind-Code Damage Taken 디버프(풀버스트 15.12%/노멀10회마다 12.12%, `boss_is_element("Wind")` 게이팅, 2026-07-16 gap #5). 잔여 없음 |
| Nayuta | `nayuta` | Supporter | SMG | Wind | ⚠ | 무기변형(Memory Incineration) + 복합트리거 넉 |
| Mint | `mint` | Supporter | RL | Iron | ✅ | Here I Go!(풀차지마다 스쿼드 ATK) 단독+Prika 조합 모두 모델(버스트타임 패리티/Encore 핀 시각). Dancing 자힐만 보류 |
| Prika | `prika` | Supporter | SR | Water | ✅ | 본인 풀차지 스쿼드 버프(refresh, 중첩 아님) + **Mint Encore 교차유닛 시너지**(`ally_burst_activate`) + **Encore의 자기 버스트쿨 +21초(음수 `burst_cooldown_reduction_sec` 펄스, 2026-07-17)** 모델됨 — 이게 없으면 Prika가 ~40초마다 재버스트해 Mint의 티어2 슬롯을 밀어냄; 이제 사이클 2부터 Mint가 슬롯을 전담하는 의도된 로테이션 재현. Performance 지속시간 자체는 비딜 부기만 보류 |
| Helm: Aquamarine | `helm-aquamarine` | Attacker | AR | Iron | ✅ | Admire Accompaniment 풀버스트 CDR 에스컬레이션 + 노멀30회마다 131.34% 넉(per_shot)·Aegis Cannon Suppression Fire(자동발동, periodic_nukes) + **Electric-Code 불릿 2종**(Suppression Fire Damage Taken 정상상태 28.2% + Overload 추가딜 164.83%, `boss_is_element("Electric")`, 2026-07-16 gap #5). 추가딜은 Burst 2라 FB 보너스 미적용(Fienn). 잔여 없음 |
| Velvet | `velvet` | Supporter | SR | Wind | ⚠ | Perfect Execution(버스트 자AD버프, 넉 없음) + **Bullets of Love(그녀의 실제 스쿼드 서포트): 풀버스트 중 풀차지샷마다(SR, N=1) 스쿼드 flat ATK(자ATK의 25.2%)+스쿼드 Charge Damage+100.8%(3초, refresh, Prika 선례 따라 스쿼드스코프)+풀버스트 중 노멀50회마다 자AD+15.03%/5초 + 400.92% 넉("as additional damage"→full_burst_bonus_eligible)**(`per_shot_rules`의 `every_during_full_burst` 모드, gap #7 완료·2026-07-15) 모델됨. ammo pouch(6000, 버스트 스테이지2마다 풀리필)는 소모량 대비 압도적으로 커서 비제약으로 처리(자원 미모델링). **Sticky Fingers 모델됨(2026-07-18):** 풀버스트 아닐 때 풀차지마다(SR N=1) 자ATK+30.5%/자AD+30.5% 3초 refresh — 신규 `every_outside_full_burst` 모드(gap #7 거울상). Perfect Execution 무기변형딜만 보류 |
| Rosanna: Chic Ocean | `rosanna-chic-ocean` | Supporter | AR | Wind | ⚠ | Spina di Rosa(30s 액티브, 지속딜 듀티사이클) 보류, 파츠파괴 스택 ATK 보류 |
| Takina Inoue | `takina-inoue` | Supporter | SR | Iron | ⚠ | 버스트 무기변형(200.64%) 보류. S2는 periodic 트리거로 모델(cd15s 아군 True Damage▲140%). 진댐 버프는 덱에 진댐 딜러 필요 |

## Burst 3 (41명)

> **eb (encoding batch) 진행:** Burst 3 어태커 배치 인코딩 (least-blocked 우선).
> eb1 = Noir · Isabel · Liberalio, eb2 = Ludmilla · Chisato · Jill (2026-07-12).
> **자원 primitive beachhead (gap #2 Pattern A, 2026-07-12):** Modernia · Guillotine:
> Winter Slayer — named-resource/캡 스택 카운터 엔진 확장의 첫 소비자.
> **count-스케일 넉 + multi-hit 버스트 + periodic fill (2026-07-12):** Julia(base) ·
> Julia(시그니처, 별도 slug `julia-signature`) · Cinderella — `resource_scaled_nukes`/
> `burst_hit_counts`/periodic 자원 fill 엔진 확장의 소비자. Guillotine의 Extermination
> Hero-Level DoT도 이때 완성.
> **eb3 Pattern-A 자원 유닛 배치 (2026-07-12):** Quency: Escape Queen(자원 확장 불필요,
> 정상상태 스택체인) · Soda: Twinkling Bunny(자원 **reset** + `resource_gated_buffs`
> + `("per_shot_every_during_full_burst", N)` fill) · Maiden: Ice Rose(자원
> **squad-burst-cycle-conditional fill** + `dynamic_hit_count_nukes`) — 여섯 개
> 신규 엔진 확장의 소비자. 상세는 각 모듈 docstring과 `engine-capabilities.md`
> /`special-mechanics.md` 참고.
> **eb4 배치 (2026-07-12):** Asuka Shikinami Langley: Wille · Mana — `fire_delay`
> + `own_burst_delayed`(버스트 후 지연 발동 넉/리셋) · `("per_shot_every_during_own_
> status_window", n, duration)` fill(자기 버스트 앵커 상태창 한정 fill) ·
> `full_burst_bonus_eligible`(스킬 텍스트 "as additional damage" 표시 유닛만 옵트인,
> `docs/decisions.md` 참고) · `resource_scaled_nukes`의 `resource` 필드 선택화(순수
> 반복틱 DoT) — 4개 신규 엔진 확장의 소비자. Cinderella: Crystal Wave는 배치에서
> 제외됨(Pattern-A 자원 유닛이 아니라 무기-모드 전환 상태머신 유닛으로 재분류,
> `engine-gaps.md` 참고).
> **gap #7 완료 + Phase A1 (2026-07-15):** `per_shot_rules`에 창 한정 모드
> `every_during_full_burst`/`every_during_own_status_window` 추가 — Soda(공동발동
> 최고ATK버프)·Asuka(15.62% 상태게이팅 넉) 잔여 메커니즘 재인코딩. 같은 날 기존
> per-shot 능력만으로 신규 인코딩: Helm: Aquamarine(노멀30회마다 131.34% 넉)·
> Anis: Sparkling Summer(라스트불릿 382.42% 넉 + 부위딜 refresh). 검증 중 재분류:
> grave·velvet은 gap #7로 부분 언블록 가능(다음 배치), jill-valentine은 신규
> 소규모 갭(reload 후 첫 발 마커, gap #9) 필요로 확인, rapi-red-hood는 gap #7·#9
> 어느 것으로도 안 풀리는 프로젝타일-런치 상태머신으로 확인 — 상세는
> `engine-gaps.md` 참고.
> **gap #7 두 번째 소비 배치 (2026-07-15):** Grave(Overheat II/III, 자기 버스트
> 상태창 한정 노멀30/60회마다 자버프)·Velvet(Bullets of Love, 풀버스트 한정
> 풀차지/노멀50회 카운터 — 그녀의 실제 스쿼드 서포트) 재인코딩(🔶→⚠). gap #7
> 소비자는 이로써 Soda·Asuka·Grave·Velvet 4명. ~~남은 gap #7 후보는 modernia
> (Giant Leap 상태게이팅 200히트 ATK버프) 하나뿐 — 착수 전 검증 필요.~~ →
> **해소 (2026-07-18, Fienn 정정):** Giant Leap은 인게임에서 상태창과 무관하게
> 전투 시작부터 200히트마다 발동 — gap #7이 아니라 기존 `every` 모드로 인코딩
> 완료. gap #7 후보는 소진.
> **나머지 백로그는 [`roadmap.md`](roadmap.md) To-Do 참고** (대부분 남은 Pattern A
> 자원 유닛 / Pattern B 게이지·변신 / 상태머신 / 무기변형 갭).

| 이름 | 슬러그 | 클래스 | 무기 | 원소 | 완성도 | 주요 보류 내용 |
|---|---|---|---|---|---|---|
| Anis: Sparkling Summer | `anis-sparkling-summer` | Supporter | SG | Electric | ⚠ | Sparkling Boost(FB진입 시 Electric코드 아군 flat ATK/재장전속도)·Sparkling Wave(자기 최대탄약/재장전속도) 모델됨 + **Sparkling Missile: 라스트불릿마다 382.42% 넉(2 최고ATK 적) + 자기 부위딜 +6.91%/10초 refresh**(`per_shot_rules`의 `"last_bullet"` 모드, 2026-07-15 Phase A1) 모델됨. Sparkling Wave의 Elemental Advantage Attack Damage(버킷 불명)만 보류 |
| Ark Ranger Black | `ark-ranger-black` | Attacker | AR | Wind | ⚠ | (신규 2026-07-16) Transformation 상태에서만 나오는 지속딜 위주 배터리 게이지 유닛 — 파츠파괴로 게이지가 차는 메커니즘은 모델 불가하여 신규 보스 플래그 `part_destructible`로 **floor(파츠파괴 없음)/ceiling(파츠파괴 있음)** 두 갈래를 모델링(`docs/superpowers/specs/2026-07-16-ark-ranger-black-transformation-design.md`, gap #2 Pattern B 우회). Transform! 자ATK+156.19%(floor: 버스트당 10초 창, ceiling: 전투 시작부터 영구)·Ark Black Collider 45.87% 지속딜(floor: 버스트-앵커 10틱, ceiling: 전투 내내 1초마다)·Ultimate! Meteor 266.69%×10틱 지속딜 + 자신 Sustained Damage+135.83%/10초(양쪽 분기 공통)·노멀30회마다 자신 Sustained Damage+59.6%/5초(refresh) 모델됨. skill2 풀버스트 "Wind코드 어썰트라이플 아군 Sustained Damage+77.5%/10초"(member_subset_buff_rule, gap #3 소비 2026-07-16 — Ark 자신 포함 자기적용) 모델됨. 보류: 파츠파괴로 인한 배터리 충전(이 플래그의 존재 이유)·Damage to Parts+20%(파츠딜, 레이드 DPS 무관) |
| Ada Wong | `ada-wong` | Attacker | RL | Electric | ⚠ | (신규 2026-07-16, Phase C) Covert Support: FB진입 시 "이미 버스트한 버스트3 아군" flat ATK(자ATK 60%)+진댐+50%/10초(member_subset_buff_rule, gap #3)·Flash Grenade: FB창 동안 2초마다 420% 진댐 주기넉(during_full_burst, gap #6 — 자기 버스트로 열린 FB창은 1초 틱, own_burst_interval, Fienn 판정 2026-07-16)·Secret Agent(버스트, 버프 온리): 자ATK+40%+진댐+42%/10초 + Special Modification 1라운드(차지속도▼300%+차지딜▲1500% → 매거진-경계 함정으로 감속이 착지 불가 확인, net 근사 charge_damage_bonus +2.75/1라운드로 모델 — 모듈 docstring 참고) 모델됨. 보류: Covert Support HP 회복(비딜). SKILL_VALUE_MANIFESTS는 브랜치 병합 후 백필 예정 |
| Asuka Shikinami Langley: Wille | `asuka-shikinami-langley-wille` | Attacker | MG | Wind | ⚠ | eb4. Anti A.T. Field 자원(캡30·`per_shot_every_during_own_status_window`로 자기 버스트 앵커 9초창 한정 노멀10회마다 fill·스택당 받댐+0.83%/30초, squad-scope)+무조건부 노멀50회마다 471.86% 넉("as additional damage", `full_burst_bonus_eligible`)+**같은 자원 fill 트리거에서 15.62% 상태게이팅 넉("as damage", 9초 Annihilation State 창 한정, `per_shot_rules`의 `every_during_own_status_window` 모드, gap #7 완료·2026-07-15)**+Annihilation State 버스트 자ATK/공댐(46.8%×자ATK/36%, 9초)+Emergency Repair FB진입 공댐+30.97%/10초(`own_burst_fired_this_cycle` 게이팅)+Annihilation 지연넉(버스트 9초 후 발동, 히트수=스택수, `dynamic_hit_count_nukes`+`fire_delay`, FB보너스) 모델됨. Normal Attack Damage 디버프(노멀전용 스코프 없음)·재장전/힐만 보류 |
| Chisato Nishikigi | `chisato-nishikigi` | Attacker | SMG | Iron | ✅ | eb2. Extrasensory 상시 자ATK/진댐(버스트 재충전으로 >70% 유지 근사)·버스트 자ATK/노멀진댐화·48노멀마다 진댐넉(per-shot) 모델됨. per-shot 넉이 attack타입(진댐 언더카운트)·회피/명중(inert) 보류 |
| Cinderella | `cinderella` | Attacker | RL | Fire | ⚠ | Flawless Glass 자ATK(자기 최대체력 비례)+매 풀차지 136.6% 추가딜(RL 상시 풀차지, per-shot)·Beautiful 자원(periodic fill, 3초마다·캡12)·Glass Slippers 10연타 버스트넉 + Beautiful 스택수 비례 추가딜(count-스케일 넉) 모델됨. 디코이 생성(생존)·Beautiful 자체 최대체력% 증가(연결된 소비자 없음, inert)만 보류 |
| Cinderella: Crystal Wave (MG) | `cinderella-crystal-wave-mg` | Attacker | MG | Iron | ⚠ | (신규 Task 6, 2026-07-19) 전투 전 MG/Snipe 모드 고정 선택(플레이어가 정하고 전투 내내 유지 — 상태머신이 아니라 정적 슬러그 2개, `MODE_VARIANTS["cinderella-crystal-wave"]`로 배선, 덱 탐색이 두 모드 동시 편성 금지). 공유 킷(양 모드 동일): 배틀스타트 자AD+24%(Beauty-Full)/자ATK+29%(Mode Swap)·버스트 자AD+92%/자ATK+65% 10초(Glass Slippers)·6000% 버스트넉·5초마다 900% 주기넉(`periodic_nukes`). MG 전용: 배틀스타트 Pinpoint 코어딜+26%(`other_core_damage_sources`)·FB진입 833.79% 코어스트라이크 넉(자기 버스트 이번 사이클 발동 AND 코어활성 게이팅 — 스킬텍스트가 "코어 활성 적 한정"이라 균일 코어보정 모델상 `core_hittable` 게이트로 관례 정합, `boss_core_hittable`+`own_burst_fired_this_cycle` 복합조건). 보류: 디코이 아바타(생존)·아군탄200발마다 버스트게이지+12%(inert)·Pierce·모드전환 자체(Preparation for Change 상태머신, 모드 고정이라 무의미) |
| Cinderella: Crystal Wave (Snipe) | `cinderella-crystal-wave-snipe` | Attacker | MG(정체성)/SR(발사) | Iron | ⚠ | (신규 Task 6, 2026-07-19) MG와 공유 킷 동일(위 참고). Snipe 전용: 배틀스타트 Destroy 파츠딜+26.21%(`damage_to_parts_up`)·FB진입 1189.66% 넉(자기 버스트 이번 사이클 발동만 게이팅, 코어 무관 — 전체 적/부위 대상이라 코어게이트 없음). **정적 무기 프로필 override**(`_WEAPON_PROFILE_OVERRIDE_BUILDERS`, Task 5 배선 첫 실사용): SR 62.13%·15발·차지1초·풀차지딜250%·재장전 2.5초(스킬텍스트에 값 없음 — MG 기본 재장전 차용, Fienn 판정 2026-07-19). `weapon` 필드는 아군필터용으로 "MG" 유지, 발사 케이던스/타이핑만 이 프로필의 "SR"이 결정. "풀차지=40발 회계"는 소비카운트 부기일 뿐 실제 발사는 1발(Velvet 탄약주머니 선례, little_mermaid.py 교차노트) — 이 부기가 먹이는 스킬 전부 defer라 노트만 남김. 보류: MG와 동일(디코이·게이지·Pierce·모드전환) |
| Guillotine: Winter Slayer | `guillotine-winter-slayer` | Attacker | AR | Water | ⚠ | 자원 beachhead. EXP 자원(자ATK ▲1.81%/스택, 캡100, 연속)·Hero Level 파생 Water 아군 버프(레벨 스케일)·core-conditional fill·Extermination Water 버프 + **Hero-Level 스케일 10틱 지속딜(매 틱 자기 시각 기준 count 재조회, count-스케일 넉 + full_burst_bonus, 2026-07-12 인게임 확인 반영)** 모델됨. 레벨업 리로드/힐(딜 아님)만 보류 |
| Helm (애장품) | `helm` | Attacker | SR | Water | ⚠ | Frontline Command 라스트불릿 스쿼드 크리율+14.64%/5초(`per_shot_rules`의 `"last_bullet"` 모드, refresh) 모델됨(2026-07-12, gap #1 잔여 해소) + Fire Away 스쿼드 파츠딜/공댐 모델됨. 두 스킬의 풀차지 보너스 효과(힐/게이지/추가딜)·Aegis Cannon 버스트후 차지배수(10 round) 보류 |
| Isabel | `isabel` | Attacker | SG | Electric | ✅ | eb1. Marked Target 이스컬레이팅 자버프(refresh)·Pointed Feather 주기넉(cd15)·Sonic Chaser 버스트넉 + 단계별 추가딜(activation_count 게이팅, 사이클 정확)·받댐 디버프 모델됨. Full Burst Duration▲(로테 타이밍)만 보류 |
| Jill Valentine | `jill-valentine` | Attacker | AR | Electric | ✅ | eb2. FB 자ATK·버스트 진댐/공댐/재장전속도/노멀진댐화 + Magnum Ammo(전투시작+풀재장전마다 다음 9탄 노멀공격 배수 +30%: first_bullet 마커+9샷 라운드그랜트+`normal_attack_damage_multiplier` Final-ATK 항, gap #9 소비)·Acid Ammo(192%/1초 지속딜 30초 — refresh 판정[Fienn 2026-07-16]으로 전투 내내 연속 정상상태 → 전체전투 주기 지속넉) 모델됨. 잔여: Supercop 명중 버프(inert)·강제 재장전 북키핑뿐 |
| Julia | `julia` | Attacker | AR | Water | ✅ | Decrescendo 자크리율(periodic, cd20)·Climax 버스트넉(544.5%, 단일히트)+Crescendo 라스트불릿 자원(캡5·15초 지속, 크리댐+24.79%/스택, `on_last_bullet` fill)+게이팅된 Climax 추가 544.5% 넉("as additional damage" → full_burst_bonus, `resource_scaled_nukes`) 모델됨(2026-07-12, gap #1 잔여 해소) |
| Julia (시그니처, 별도 slug) | `julia-signature` | Attacker | AR | Water | ⚠ | base와 별도 roster 엔트리(Fienn 결정, 2026-07-12). Decrescendo 자크리율/자ATK(periodic + 전투시작 강제시전)·Climax 5연타 버스트넉(544.5%×5, `burst_hit_counts`) 모델됨. Crescendo/Marcato(크리티컬 히트 카운터 — 기대값 크리 모델과 구조적으로 불가, 영구 defer)·노멀전용 크리율(버킷 없음)만 보류 |
| Liberalio | `liberalio` | Attacker | SR | Wind | ✅ | eb1. 버스트넉 925%·FB 자ATK·Raging Current 공버프 231%(풀차지 per-shot 상시)·on-core 공버프·풀차지 추가딜 5회 모델됨. Gentle Current(비-보스 대상, solo N/A)·차지속도(inert) 보류 |
| Ludmilla: Winter Owner | `ludmilla-winter-owner` | Attacker | MG | Water | ✅ | eb2. 60노멀마다 받댐 디버프+넉(per-shot)·FB 자크리율·버스트 자ATK/재장전속도 모델됨. Snowstorm 코어60넉(코어카운터 과대평가 우려로 보류)·재장전 탄약(QoL) 보류 |
| Mana | `mana` | Attacker | AR | Wind | ⚠ | eb4. Metal gamma 상시 자ATK+58.08%(전투시작, 아군 전멸 트리거 미모델로 상시 근사)+Metal sigma FB진입 공댐+21.12%/자ATK+63.36%(10초, `own_burst_fired_this_cycle`로 상태 게이팅 대체 — 엄격한 버스트 순서상 동치)+Fatal Error! 버스트(자 지속딜+52.8%/10초 + 396%/초 10틱 순수 반복DoT + full_burst_bonus, `resource_scaled_nukes`의 `resource` 필드 선택화 및 `full_burst_bonus_eligible` 첫 소비자 — 2026-07-12 인게임 확인) 모델됨. 힐/부활(아군전멸 미모델)·게이지속도(inert)·차지타임 감소(비딜+narrow scope) 보류 |
| Maiden: Ice Rose | `maiden-ice-rose` | Defender | RL | Electric | ✅ | eb3 Pattern-A. MP 자원(squad-burst-cycle-conditional fill)+Diamond Dust 버스트(`dynamic_hit_count_nukes` — 히트수=MP, 1372.8%×(10% 최대체력+ATK))+Blessings Upon You(자속성상성공댐/자ATK 버스트버프 + 풀차지마다 547.62% per-shot 넉) 모델됨. "MP 소모" 트리거는 엔진 순서상 항상 MP=0에서 드레인되므로 Diamond Dust는 매 사이클 정확히 1회 히트(엔진 확정 버스트 순서 근거, 모듈 docstring 참고). MP 회복 시 Electric 아군(자신 제외) 버프(상성공댐+40.9%[Water 보스 게이팅]·자ATK 20.9% flat, 10초 refresh)도 `resource_fill_triggered_buffs`(gap #8 소비 2026-07-16)로 모델됨. 잔여 보류: 최대체력 스택(비딜)뿐 |
| Marciana: Marine Study | `marciana-marine-study` | Attacker | AR | Iron | ⚠ | (신규 2026-07-16, gap #5 배치) Fienn 가정(rapture=1·Flagged Target=보스·High-Risk 불릿=Electric 보스 게이팅). Whistle 정상상태 자ATK+163.65%(5스택)·Elemental Advantage Attack Damage(연속 20.41% + 버스트 30.97%, **element bonus damage 그룹=`other_elemental_bonus`**, `boss_is_element("Electric")` 게이팅)·버스트 자AD+27.45%(attack_damage_up)·High-Risk DEF-10.56%/20초(`enemy_def_percent`, Electric)·Flagged Target 3789.25% 풀버스트 넉("additional damage", B3라 FB보너스)·High-Risk 20노멀마다 152.68% 넉(plain `every`, Electric 게이팅, 상시 유지 근사) 모델됨. 보류: Flagged Target ATK 버프(스코프 모호, defer)·적 처치 트리거 넉 사본(보스 미처치)·6+rapture Penguin Emergency Dispatch 넉 |
| Maxwell | `maxwell` | Attacker | SR | Iron | ⚠ | (신규 2026-07-19) Straight Shot: FB진입 시 최고ATK 2인 차지속도+4.48%/ATK+43.1% 10초 — **대상에 Maxwell 자신 포함(Fienn 판정 2026-07-19)**, 공유 `top_atk_slugs`(캐스터 항상 제외)와 달리 캐스터 포함 랭킹을 뽑는 로컬 커스텀 액션으로 모델. Pierce Shot(버스트): 무기를 2초 차지·1탄 캐논으로 변형 — 813.42% 샷딜/300% 풀차지딜, `weapon_mode_schedules`의 `until_shots: 1` 세그먼트(snow-white/red-hood 선례). 보류: Spark Shot(적 5기 초과 게이팅 — 레이드 보스 1기 상대로 항상 거짓)·Pierce Shot의 Pierce 속성(엔진 미지원) |
| Modernia | `modernia` | Attacker | MG | Fire | ⚠ | 자원 beachhead. High-Speed Evolution 히트당 3.05% 추가딜(per-shot)·200히트마다 Crit Dmg/Max Ammo 스택(캡5·10초 시한 자원) + **Giant Leap 자ATK+29.38%/10초(2026-07-18, Fienn 정정: 상태창 무관, 전투 시작부터 노멀 200히트마다 — `every` 모드, refresh)** 모델됨. Max Ammo 스택은 자기 탄창 재생성 전 계산돼 inert·Giant Leap의 스쿼드 Hit Rate(inert)·New World 버스트(Destroy Mode·무한탄·FB연장) 보류 |
| Noir | `noir` | Attacker | SG | Wind | ✅ | eb1. 버스트넉 351.64%·Lucky Charm 스쿼드 ATK(caster 비례)·Finale 파츠딜 버프 모델됨. Rabbit Twins 탄약/재장전(QoL)·Hit Rate(inert)만 보류 |
| Privaty (애장품) | `privaty` | Attacker | AR | Water | ✅ | EX Magazine 스쿼드 ATK/재장전속도/탄약감소/공댐(FB진입) 모델됨. LD Assault 라스트불릿 넉(`per_shot_rules`의 `"last_bullet"` 모드, 2026-07-12 gap #1 잔여 해소): 받댐+10.01%/10초+256.17% 추가딜("as additional damage") + Designated Target(AK Missile 자신의 버스트로부터 10초 창, `context.burst_times` 시간창 체크) 중이면 1687% 추가딜까지 중첩 발동 + AK Missile 자속성상성공댐 모델됨. Designated Target의 적 ATK 감소 디버프(생존계, 비딜)만 보류 |
| Quency: Escape Queen | `quency-escape-queen` | Attacker | SMG | Water | ✅ | eb3 Pattern-A. Explore Route(3단계 스택체인, 노멀2회마다·전단계 만캡 게이팅)+Secure Route(단계별 버프) 전부 정상상태 근사(ATK+110.3%+Distributed Damage+49.58%+Core Damage+25.25%+Crit Rate+16.73%, battle_start부터 영구 — SMG 20발/초로 스택 감쇠창보다 채우기가 압도적으로 빨라 상시 만캡)·The Great Thief 버스트(자공댐/재장전속도+1736.31% Distributed 넉) 모델됨. Hit Rate만 보류 |
| Rapi: Red Hood | `rapi-red-hood` | Attacker | MG | Fire | ⚠ | Attachable Projectiles 배틀스타트 상시 self 3건 모델됨(2026-07-17/19): PE Damage ▲100.6% + Projectile Attachment Damage ▲150.72%(각각 PE/PA 타입 넉에 적용) + Electric 보스 한정 원소우위(`other_elemental_bonus` 0.1, `boss_is_element` 게이팅). 120노멀 프로젝타일 런처 모델됨(2026-07-19, Fienn 시맨틱 확정): 요구치 도달마다 부착(카운터 리셋)·부착분 누적·다음 FB 진입 시 일괄 폭발(부착 1건당 폭발 1히트) — rapi의 `scheduled_nukes` 첫 소비자, `context.full_burst_windows`+`context.shot_times` 활용. Power of Inheritance(버스트) Stage 3 라이더: 요구치 -60/10초 + Projectile Attachment Damage ▲421.2%/10초(`own_burst_activate`). **Task 7(2026-07-19) — B1 변종 `rapi-red-hood-b1`**: Battlefield Assessment의 Combat Assist 분기(다른 B1 없으면 CA 세팅, 이미 인코딩됨)가 실제로 작동하려면 그녀를 B1 슬롯 후보로 앉힐 수 있어야 해서 등록(`MODE_VARIANTS["rapi-red-hood"]`+`VARIANT_BURST_TIERS["rapi-red-hood-b1"]=1`, 매니페스트 data_slug/dotgg_slug로 무기스탯 공유, 런처는 `stage3_requirement_cut=False`로 별도 슬러그 재사용). Power of Inheritance Stage 1 브랜치 모델됨: 넉 없음(서포트 전용) + 자 버스트CD ▼20초(`cdr_pulse_rule` self, 2사이클째부터 매 사이클 재발화) + 아군 flat ATK=캐스터ATK 18.01%/10초(Crown 캐스터ATK 선례). 덱 탐색에 **단독 B1 제약**(`SOLE_TIER1_SLUGS`/`_tier1_seating_valid`, 두 열거 경로 게이팅): 인게임에서 다른 B1과 같은 덱이면 CA가 취소돼 시뮬과 어긋나므로 배제. 부수적으로 발견/수정: `_reference_deck`이 교차 티어 변종(B1↔B3)의 형제를 B3 픽에 걸러내지 않아 프루닝 레퍼런스 덱이 두 변종을 동시에 앉히는 버그를 실데이터로 발견해 수정(회귀 테스트 추가). 잔여: Explosion Radius·Interruption Parts(원래부터 defer) |
| Rei Ayanami | `rei-ayanami` | Attacker | MG | Fire | ✅ | (신규 2026-07-16, base) Attack Support: Fire 아군 flat ATK=caster ATK 25.03%(FB진입)·버스트: Fire 아군 AD+48.02% + 990.2% 넉·Preemptive Subdual: 노멀100회마다 112.37% 넉(gap #1 `every`) + 자 Elemental Advantage AD+30.23%/3s(other_elemental_bonus, Iron 보스 게이팅 Fire>Iron, refresh). 보류: 실드딜/실드생성(비-DPS)만. dollskills 데이터 비어있음(시그니처 없음, base-only) |
| Rei Ayanami (Tentative Name) | `rei-ayanami-tentative-name` | Attacker | AR | Wind | ⚠ | (신규 2026-07-16, base; `rei-ayanami`와 별개 유닛) Attack State 버스트: 자AD+35.9%+자flat ATK=caster ATK 63.36% + 990.2% 넉·Maintenance: 스쿼드 flat ATK=caster ATK 11.61%(FB진입)·Annihilation Support: Attack State 창(자버스트 10초) 중 노멀7회마다 286.37% "additional damage" 넉(gap #7). 보류: Anti A.T. Field 590.64% 페이로드+Annihilation State 아군버프(교차유닛 콜라보 상태), MG heating up speed |
| Neon: Vision Eye | `neon-vision-eye` | Attacker | RL | Electric | ⚠ | (신규 2026-07-16, base) Firepower Gauge가 매 사이클 100 리필 → Super Firepower 매 사이클 정상상태로 근사. Maximum Firepower: 자ATK+115.09%(FB진입)·Super Firepower 버스트: 자AD+155.24%(버스트 넉 없음)·Firepower Explosion: 풀차지마다 437.98% + Super Firepower 10초 창 중 +262.79%("additional damage", gap #7). 보류: 라이브 게이지, 넉의 projectile-explosion 타이핑(pulse 경로 미지원, 자기 킷 내 inert), Explosion Radius, 생존기 |
| Raven | `raven` | Attacker | RL | Iron | ⚠ | (신규 2026-07-17) 딜의 핵심은 Shock Wave — **스택 카운터 1개**(풀차지마다 +1, 상한 10)가 초당 스택수만큼 68.46% 지속댐 틱. `lasts for 5 sec`는 **카운터의 수명이고 풀차지마다 갱신**됨(Fienn 정정 2026-07-17) — 풀차지마다 독립 DoT가 겹치는 게 아님. RL 풀차지 1초·최대 공백 3초(재장전) < 5초 갱신창이라 **카운터가 전투 내내 안 죽고 t≈12에 10스택 도달 후 고정**. 틱마다 스택수만큼 개별 인스턴스 방출(디펜스가 히트당 차감). `scheduled_nukes`+`context.shot_times`가 첫 소비자. FB진입 자 flat ATK=caster ATK 47.52%·Tempest 492.3% 넉·A.N. Mode 자 지속댐+89.44%/10초. **브래킷(Ark Ranger 선례, Fienn 판정)**: Blue Blade의 Single Point Attack(자 지속댐+47.32%)은 부위파괴 트리거라 floor(파괴 없음=미발동)/ceiling(파괴 있음=전투 내내) 두 갈래. E2E: Shock Wave 2.92억(최대 소스), floor 총 3.454억 / ceiling 3.511억. 보류: Vital Attack(Damage to Parts — 소비 경로 없어 inert) |
| Scarlet: Black Shadow | `scarlet-black-shadow` | Attacker | RL | Wind | ⚠ | (신규 2026-07-18, **gap #10 첫 소비자**) 딜의 핵심 Fleetly Fading Breakthrough — 단일 풀차지 카운터가 3/6/9 단계(283.03% 단일 attack / 565% / 848.03% **distributed** — Pulse damage_type 신규 배선으로 실제 타입 버킷 곱해짐)를 걷고 9단계 후 리셋. 버스트가 요구치를 10초간 1/2/3으로 교체(`sequence` 모드의 own_burst_window, 카운트 이어받기 — Fienn 판정) + 자ATK+115.12%/차지댐+169.63% 10초(버프 온리, burst None). Asura FB진입 자기 Max Ammo+60%/10초(라이브 매거진 반영). E2E(대표 스탯): 시퀀스 넉이 본인 딜의 ~87%, 창 안 발동밀도 창 밖의 ~3배. 보류: Asura의 FB진입 매거진 100% 즉시 재장전(발사 타임라인 개입 프리미티브 없음, gap #11 동류 — floor 인코딩) |
| Red Hood | `red-hood` | Attacker | SR | Iron | ⚠ | (신규 2026-07-18, **낡은 Pattern B 판정 정정**; **2026-07-19: 세그먼트 마이그레이션**) "게이지=charge speed라 딜 아님"은 Phase S 이전 판정 — 지금은 발사 케이던스 스탯. Glaring Eyes: 노멀마다 차지속도+3.81%×10스택(SR 케이던스상 5초 수명이 안 끊겨 **정상상태 +38.1% 상시**, Raven 카운터 선례) + **100% 초과분×240% → 차지댐 변환**(자기 소스만: 버스트 창 +100.8%와 합쳐 초과 38.9 → +93.36%p). Wild Tooth: Red Wolf 시전 시 자ATK+71.42%/10s. **버스트 "Step 1/2/3"은 상태머신이 아니라 버스트 슬롯 선택** — 엔진이 B3 고정이라 Step 3만 유효(Step 1/2와 CD-40 트릭은 도달 불가). Step 3 무기변형: Fienn 실측(창 10초 33발·무한탄창·차지시간 0 안 됨) 앵커로 **`weapon_mode_schedules`의 명시적 `rate_of_fire` 세그먼트(3.3발/초, 10초 고정 창)로 모델**(2026-07-19, snow-white/maxwell 선례를 잇는 네 번째 소비자) — 세그먼트가 창 안에서 기본 SR을 실제로 침묵시켜 이전의 정적 이중계상 차감/상수 접기가 사라졌고, 덱 Charge Damage/ATK 버프가 변형샷에 실제로 곱해짐(총딜 ~+1.6%, 덱 버프 없는 스팟체크 기준). E2E(liter+crown 덱): 창 5개×33히트, 변형이 총딜 30%. 보류: Pierce 속성/범위 |
| Snow White | `snow-white` | Attacker | AR | Iron | ⚠ | (신규 2026-07-19) Determination: 노멀30회마다 82.8% "additional damage" 넉(gap #1 `every`) + 자ATK+8.28%/5초. Seven Dwarves: V & VI: 자기 쿨다운(cd15) 주기 AoE 넉 144.73%(`periodic_nukes`, 버스트 사이클 무관). Seven Dwarves: I(버스트): 무기를 5초 차지·1탄 캐논으로 변형 — 499.5% 샷딜/1000% 풀차지딜, `weapon_mode_schedules`의 `until_shots: 1` 세그먼트(red-hood 무기변형 선례, 단 측정 앵커가 아니라 실제 차지무기라 덱 차지댐/ATK 버프가 그대로 곱해짐). 보류: Seven Dwarves: V & VI의 "풀버스트 중 사용 시 크리율+26.1%/10초" 라이더(periodic_nukes 경로엔 창-게이팅 조건 프리미티브 없음) · Seven Dwarves: I의 Pierce 속성(엔진 미지원, Red Hood 선례와 동일) · 변형샷이 Determination 자체 노멀카운터에 포함되는지는 스펙 미해결 질문 — 엔진 통일 타임라인상 현재는 포함됨(모듈 docstring 참고, Fienn 확인 시 조정) |
| Snow White: Heavy Arms | `snow-white-heavy-arms` | Attacker | SR | Water | ⚠ | (신규 Task 9, 2026-07-19) 무기변형 계획 2 잔여였던 "차지 루프 상태머신" 검증 패스 — 기존 per-shot 세그먼트 게이팅(Task 8)만으로 풀림, 신규 엔진 확장 없음. 배틀스타트 스쿼드 받댐+4.2% 영구(락온 0.2초 틱, 가동률≈100%라 상시 근사, Fienn 2026-07-19). Auto Fire(풀차지마다 발동, SR 상시 풀차지): 41.9% 전체히트 + 장전수×105.59% 연타(전탄 보스 단일 적중) — 기본 5장전(`every_outside_segment`, 569.85%) vs Fully Active 15장전×(1+158.4%)(`every_during_segment`, ≈4134.57%), 두 모드가 레코드 식별자로 상호배타(Task 8)라 이중계상 구조적으로 불가능. 차지창 자ATK+46.84%/자부위딜+62.64% 5초(매샷 refresh). Shades of White "Burst Stage 3 진입" 자ATK+73.92%/10초는 **Step 2 선례 확인**: cinderella/ein의 동일 문구(자기-스코프, `own_burst_activate`, "본인이 B3 슬롯이라 이게 곧 자기 버스트")를 따름 — rei-ayanami의 동일 문구는 스쿼드 전체 스코프(Fire 코드 아군)라 `full_burst_enter`를 쓴 것과 대조(모듈 docstring에 정밀 근거). Seven Dwarves Fully Active(버스트, cd40): 자공댐+84.48%/10초(`own_burst_activate`) + `weapon_mode_schedules` 2샷 3.2초차지 세그먼트(캐스터 자기 무기스탯의 250% 풀차지딜 + Shades of White의 +528% = 778% `charge_damage_percent`로 접어 덱 차지댐 버프가 그대로 곱해짐). 보류: DEF+42.24%(비딜)·Pierce(엔진 미지원 관례)·41.9% 파괴가능 투사체 스윕(파괴가능 투사체 미모델)·락온 멀티타겟 부기(보스 1기로 축약) |
| Sakura: Bloom in Summer | `sakura-bloom-in-summer` | Attacker | AR | Wind | ⚠ | (신규 2026-07-17) Bloom이 배틀스타트에 Skill2를 강제발동 → Full Glory가 **t=0,30,60,90,120,150**(t=cd 아님). Dancing Flower 자 공댐+15.64%/15초(cd30의 절반 = 50% 가동률, 정상상태로 뭉개지 않고 발동별 모델)·Sakura Petals 256%/초×15틱 지속댐(`scheduled_nukes`, 컨텍스트 불필요)·Ephemeral Spender 457.14%×10연타(`burst_hit_counts`) + 10연타가 각각 1스택을 깔아 **351.6%/초×10틱** 지속댐(Fienn 판정 2026-07-17, 연타수와 상한이 둘 다 10인 이유). E2E 총 2.397억. 보류: Bloom의 부위파괴 라이더 3건(자 지속댐+5.1%·Dancing Flower/Sakura Petals 지속시간+10.02초) — 전부 딜 증가분이라 이 인코딩은 floor |
| Ein | `ein` | Attacker | SR | Electric | ✅ | (신규 2026-07-17) 딜의 대부분이 Near Feather 소환체 — 신규 `scheduled_nukes` 확장으로 사전계산 스케줄에 90.81% 진댐 방출. 페더 6기 상한/개체별 수명(F1 무제한·F2 38s·F3 32s·F4 26s·F5·F6 10s)·버스트가 전 페더 재소환+쿨 초기화·공격쿨 8초에서 기수당 -16%(합연산). Feather Standby 자ATK+70.12%(자버스트)·Feather Shot 풀차지마다 자 Charge Damage+80%/1라운드·Feather-All Range 자 True Damage+55.3%/Charge Damage+140.68% + 300.02% 진댐 넉. **가정(docstring 명시): 타격 간 0.3초 스로틀**(Fienn 영상 실측 FB 31회를 정확히 재현; 공식만 쓰면 FB 21% 과대). 6기 구간 외 카운트는 공식 미검증. E2E 실측: 180초에 페더 280타 9212만(본인 평타 5101만을 상회하는 최대 딜 소스) |
| Drake | `drake` | Attacker | SG | Fire | ⚠ | (신규 2026-07-16, base) Overcharge: 스쿼드 ATK+11.85%(FB진입)·Thunderbolt: 노멀10회마다 98.55% 넉(gap #1)·Drake Special 버스트: 1254% 넉 + 자 Max Ammo+72.18%. 보류: Hit Rate(inert) |
| Drake (Signature) | `drake-signature` | Attacker | SG | Fire | ⚠ | (신규 2026-07-16, 시그니처/듀얼슬롯) base + SG아군(**정확 스코프** — 2026-07-18 member_subset 정밀화, 이전 squad 근사) ATK+63.88%/Max Ammo+50.14% + Thunderbolt 2차 트리거(노멀5회마다 201.6%) + Drake Special 3009.6% 넉 + 자AD+31.68%. 보류: Hit Rate(inert) |
| Laplace | `laplace` | Attacker | RL | Iron | ⚠ | (신규 2026-07-16, base, 얇음) Hero Bomber: 마지막 탄 81.66% "additional" 넉(gap #1 last_bullet)·Laplace Buster First Damage 897.6%를 버스트 넉으로 모델. 보류(킷 대부분): 무기변형(5초 Buster 모드 — 인게임 실측 없음, `laplace-signature`와 달리 미해결), Hero Vision(Pattern B 감쇠 스택)+맥스스택 true dmg, 파츠딜 |
| Laplace (시그니처, 별도 slug) | `laplace-signature` | Attacker | RL | Iron | ⚠ | (신규 2026-07-19, 시그니처/듀얼슬롯) base와 별도 roster 엔트리(Fienn 결정, 2026-07-12). Fienn 인게임 실측(2026-07-19): 변형 10초 창 = First 1회 + 노멀 93회. Laplace Buster First Damage 1455.72%를 버스트 넉으로, Normal Damage 22.2%×93틱을 `weapon_mode_schedules` 세그먼트(rate_of_fire=93/10)로 모델 — Hero Vision 상시 맥스스택 가정(Fienn 승인, red-hood Glaring 정상상태 선례)으로 틱 전부 **true** 타입 고정. 틱마다 +11.9% true 추가히트를 동일 93틱 케이던스의 `scheduled_nukes`(`build_buster_scheduled_nukes`)로 방출 — 두 경로 모두 `context.burst_times` 앵커라 케이던스 일치. Hero Bomber는 base의 `last_bullet`과 달리 풀차지마다 발동(`every_outside_full_burst`) — 변형 창(=자기 버스트가 여는 FB 창) 중엔 풀차지 자체가 없어 인게임과 정확히 일치. 보류: Hero Vision의 맥스스택 게이트 자체(카운터 미모델, 위 가정으로 우회)·파츠딜 14.78%·Pierce 속성·base의 5초 변형(별도 슬러그, 미해결로 남음) |
| Dorothy: Serendipity | `dorothy-serendipity` | Attacker | SG | Water | ⚠ | (신규 2026-07-16, **Phase S 소비자**) Radiant Wings: 자 Pierce+55.08% 영구·자ATK+75.24%(FB 중)·False Salvation 버스트(버프전용): 자ATK+88.12% + **자 Attack Speed+65% 15초**(Phase S 발사속도 모델). 보류: 펠릿, Hit Rate, Flash 펠릿카운터 트리거 |
| Soda: Twinkling Bunny | `soda-twinkling-bunny` | Attacker | SG | Iron | ⚠ | eb3 Pattern-A. Golden Chip 자원(캡50·전투시작 만캡·풀버스트 중 노멀3회마다 +1=`per_shot_every_during_full_burst`, 자신의 Critical Damage 스택 +1.32%/스택)+Onward Soda! 버스트(628.7% 넉 + 17로 **reset** + 리셋前 스택≥30 게이팅 ATK+65.25%/15s=`resource_gated_buffs`)+**Lucky Golden Chip 공동발동 버프(풀버스트 중 노멀3회마다 자신+최고ATK아군 Attack Damage+10.51%/2초 refresh, `per_shot_rules`의 `every_during_full_burst` 모드, gap #7 완료·2026-07-15)** 모델됨. Beginner's Rewards 전체(캐스터별 FB 지속시간 연장 개념 부재)·Hit Rate(inert)만 보류 |

---

## 공통적으로 막힌 엔진 갭 (여러 니케에 반복 등장)

> 전체 갭 인벤토리(수집 44유닛 스캔 기반 유닛 수 집계 + 확장 규모/우선순위)는
> [`docs/engine-gaps.md`](engine-gaps.md) 참고. 아래는 요약.

당장 인코딩을 막는 건 아니지만, 아래 항목이 여러 니케의 실제 딜 비중을 상당히
깎아 먹고 있어 — 우선순위 후보:

1. ~~**노멀공격/풀차지 횟수 카운터**~~ — ✅ **해결됨 (2026-07-11, `per_shot_rules`)**.
   D: Killer Wife, Miranda, Rouge, Crown, Grave, Rapi: Red Hood, Zwei, Nayuta,
   Helm: Aquamarine, Velvet, Mint, Prika 등 다수 — 엔진은 준비됨, 각 유닛 재인코딩만
   남음(후속 배치). (본인 풀차지샷=발사 카운트로 통합. "마지막 탄"만 잔여.)
2. ~~**교차 유닛 트리거** (다른 니케의 특정 스킬 발동을 감지)~~ — ✅ **해결됨
   (2026-07-11, `ally_burst_activate`)**. Prika→Mint Encore가 첫 적용 사례
   (Prika의 Encore가 Mint의 버스트에 반응). 다른 페어링 시너지에 재사용 가능.
3. ~~**ammo pouch류 자원 메커니즘**~~ — Velvet. **비이슈로 확인 (2026-07-15):**
   6000발이 사이클당 소모량 대비 압도적으로 커서 항상 풀 상태 — 자원 트래킹
   없이 비제약으로 처리(모델링 불필요, 엔진 확장 대상 아님).

네 항목 모두 `special-mechanics.md`에 상세 기록됨. 확장 여부는 Fienn 판단.

**해결된 갭**: "버스트와 무관한 자체 쿨다운 반복 발동 스킬"은 2026-07-10에
엔진 확장으로 해결됨 (`simulate_raid`의 `periodic_nukes`) — Helm: Aquamarine의
Aegis Cannon Suppression Fire가 첫 적용 사례.
