# 인코딩된 니케 목록

`backend/app/skill_rules/registry.py`의 `ENCODED_SLUGS` 기준. 덱 추천 엔진이
고려할 수 있는 니케는 이 목록뿐이다 (인코딩 안 된 니케는 후보에서 제외됨).

- 마지막 갱신: 2026-07-17 (매니페스트 예외 8유닛 배치 — crown·helm·liter·
  miranda·moran·soline-frost-ticket·volume·zwei에 dotgg-소스 매니페스트 추가,
  53/57 커버. **API 로더블 50/57** (로더블 B1 4→10명 — 5덱 분배가 실제로 5덱을
  채울 수 있게 됨). 이전 갱신: 매니페스트 배치 2 — 29유닛 추가로 45/57 커버 +
  dotgg weapon 스탯 39파일 수집 + `dotgg_slug` 브리지(ada-wong·chisato·jill·takina))
- **스킬값 매니페스트 커버리지 — 예외만 표기:** 아래 4유닛 외 전원이
  `SKILL_VALUE_MANIFESTS`를 보유(= API 조립 가능). 이 목록은
  `test_skill_value_assembly.py`의 `KNOWN_MANIFEST_EXCEPTIONS` 가드 테스트와
  거울 구조라, 매니페스트 없는 신규 인코딩은 테스트가 먼저 잡는다.
  - 픽스처가 데이터 토큰과 재배열 관계라 drop_tokens로 재현 불가(4):
    `anis-star`, `asuka-shikinami-langley-wille`, `privaty`, `neon-vision-eye`
  - (매니페스트와 별개로 dotgg weapon 파일 부재로 API 제외: `ark-ranger-black`,
    `prika` — dotgg 리스팅에 없음. `marciana-marine-study`는 dotgg에 base판
    스탯만 있어 보류 — Fienn 판단 대기)
- 총 **57명** (Burst 1: 11명 · Burst 2: 16명 · Burst 3: 30명) — drake는 base/signature 듀얼슬롯 2엔트리
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
| Little Mermaid | `little-mermaid` | Supporter | SMG | Wind | ⚠ | Bubble 5.05% 받댐증·FB창 주기넉(1초마다 63.36%×4연타, during_full_burst+hit_count, gap #6 소비 2026-07-16) 모델됨. Bubble Barrage(아군총탄 500 카운터)·버스트게이지 fill은 보류(스쿼드 합산 탄약 카운터는 별도 갭) |
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
| Arcana: Fortune Mate | `arcana-fortune-mate` | Attacker | SG | Fire | ⚠ | Making Memories(버스트 자크리율·AD)·Memories and Moments 스쿼드 AD + **Precious Moments(자ATK+2.49%×최대3, Full Burst당 1스택 램프, `full_burst_enter`)·Keepsake Album(스쿼드(SG근사) flat ATK=caster ATK 13%×Precious Moments 스택, 15초) 모델됨(2026-07-16)**. 펠릿(Happy Memories)·Snapshots(Normal Attack Damage Multiplier)는 미지원 스탯이라 보류, SG-스코프는 squad 근사(Phase C gap #3 후보) |
| Grave | `grave` | Supporter | AR | Fire | ✅ | Plot Spoiler(버스트 자/스쿼드 Pierce·AD·크리율)·Heat Emission(Prediction 종료 시 발동하는 스쿼드 Pierce 토글) + **Overheat I(노멀15회 후 자ATK+15.48% 영구, gap #1 `after`)·II/III(자기 버스트의 10초 상태창 Prediction 한정 노멀30/60회 자ATK+20.66%/자AD+30.8%, `every_during_own_status_window` gap #7)** 모델됨. Fienn 실측 확인(2026-07-16): I은 언락-후-영구, II/III는 Prediction 중에만 활성 → II/III는 refreshing으로 창-끝까지 부여·매 사이클 재획득. 자힐(Prediction)·+3라운드 탄약 불릿(caster 기본 탄약 불명)만 보류 |
| Brid: Silent Track | `brid-silent-track` | Supporter | SG | Fire | ✅ | 노멀5회마다 675% 넉(per-shot) + 두 Wind-Code Damage Taken 디버프(풀버스트 15.12%/노멀10회마다 12.12%, `boss_is_element("Wind")` 게이팅, 2026-07-16 gap #5). 잔여 없음 |
| Nayuta | `nayuta` | Supporter | SMG | Wind | ⚠ | 무기변형(Memory Incineration) + 복합트리거 넉 |
| Mint | `mint` | Supporter | RL | Iron | ✅ | Here I Go!(풀차지마다 스쿼드 ATK) 단독+Prika 조합 모두 모델(버스트타임 패리티/Encore 핀 시각). Dancing 자힐만 보류 |
| Prika | `prika` | Supporter | SR | Water | ✅ | 본인 풀차지 스쿼드 버프(refresh, 중첩 아님) + **Mint Encore 교차유닛 시너지**(`ally_burst_activate`) + **Encore의 자기 버스트쿨 +21초(음수 `burst_cooldown_reduction_sec` 펄스, 2026-07-17)** 모델됨 — 이게 없으면 Prika가 ~40초마다 재버스트해 Mint의 티어2 슬롯을 밀어냄; 이제 사이클 2부터 Mint가 슬롯을 전담하는 의도된 로테이션 재현. Performance 지속시간 자체는 비딜 부기만 보류 |
| Helm: Aquamarine | `helm-aquamarine` | Attacker | AR | Iron | ✅ | Admire Accompaniment 풀버스트 CDR 에스컬레이션 + 노멀30회마다 131.34% 넉(per_shot)·Aegis Cannon Suppression Fire(자동발동, periodic_nukes) + **Electric-Code 불릿 2종**(Suppression Fire Damage Taken 정상상태 28.2% + Overload 추가딜 164.83%, `boss_is_element("Electric")`, 2026-07-16 gap #5). 추가딜은 Burst 2라 FB 보너스 미적용(Fienn). 잔여 없음 |
| Velvet | `velvet` | Supporter | SR | Wind | ⚠ | Perfect Execution(버스트 자AD버프, 넉 없음) + **Bullets of Love(그녀의 실제 스쿼드 서포트): 풀버스트 중 풀차지샷마다(SR, N=1) 스쿼드 flat ATK(자ATK의 25.2%)+스쿼드 Charge Damage+100.8%(3초, refresh, Prika 선례 따라 스쿼드스코프)+풀버스트 중 노멀50회마다 자AD+15.03%/5초 + 400.92% 넉("as additional damage"→full_burst_bonus_eligible)**(`per_shot_rules`의 `every_during_full_burst` 모드, gap #7 완료·2026-07-15) 모델됨. ammo pouch(6000, 버스트 스테이지2마다 풀리필)는 소모량 대비 압도적으로 커서 비제약으로 처리(자원 미모델링). Sticky Fingers("풀버스트 아닐 때" 풀차지 카운터 자버프 — gap #7의 거울상인 not-in-FB 창 필터 필요, 미구현, 자기전용 저가치)·Perfect Execution 무기변형딜만 보류 |
| Rosanna: Chic Ocean | `rosanna-chic-ocean` | Supporter | AR | Wind | ⚠ | Spina di Rosa(30s 액티브, 지속딜 듀티사이클) 보류, 파츠파괴 스택 ATK 보류 |
| Takina Inoue | `takina-inoue` | Supporter | SR | Iron | ⚠ | 버스트 무기변형(200.64%) 보류. S2는 periodic 트리거로 모델(cd15s 아군 True Damage▲140%). 진댐 버프는 덱에 진댐 딜러 필요 |

## Burst 3 (30명)

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
> 소비자는 이로써 Soda·Asuka·Grave·Velvet 4명. 남은 gap #7 후보는 modernia
> (Giant Leap 상태게이팅 200히트 ATK버프) 하나뿐 — 착수 전 검증 필요.
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
| Modernia | `modernia` | Attacker | MG | Fire | ⚠ | 자원 beachhead. High-Speed Evolution 히트당 3.05% 추가딜(per-shot)·200히트마다 Crit Dmg/Max Ammo 스택(캡5·10초 시한 자원) 모델됨. Max Ammo 스택은 자기 탄창 재생성 전 계산돼 inert·Giant Leap 상태게이팅 200히트 ATK버프(윈도 자원, 유의미·보류)·New World 버스트(Destroy Mode·무한탄·FB연장) 보류 |
| Noir | `noir` | Attacker | SG | Wind | ✅ | eb1. 버스트넉 351.64%·Lucky Charm 스쿼드 ATK(caster 비례)·Finale 파츠딜 버프 모델됨. Rabbit Twins 탄약/재장전(QoL)·Hit Rate(inert)만 보류 |
| Privaty (애장품) | `privaty` | Attacker | AR | Water | ✅ | EX Magazine 스쿼드 ATK/재장전속도/탄약감소/공댐(FB진입) 모델됨. LD Assault 라스트불릿 넉(`per_shot_rules`의 `"last_bullet"` 모드, 2026-07-12 gap #1 잔여 해소): 받댐+10.01%/10초+256.17% 추가딜("as additional damage") + Designated Target(AK Missile 자신의 버스트로부터 10초 창, `context.burst_times` 시간창 체크) 중이면 1687% 추가딜까지 중첩 발동 + AK Missile 자속성상성공댐 모델됨. Designated Target의 적 ATK 감소 디버프(생존계, 비딜)만 보류 |
| Quency: Escape Queen | `quency-escape-queen` | Attacker | SMG | Water | ✅ | eb3 Pattern-A. Explore Route(3단계 스택체인, 노멀2회마다·전단계 만캡 게이팅)+Secure Route(단계별 버프) 전부 정상상태 근사(ATK+110.3%+Distributed Damage+49.58%+Core Damage+25.25%+Crit Rate+16.73%, battle_start부터 영구 — SMG 20발/초로 스택 감쇠창보다 채우기가 압도적으로 빨라 상시 만캡)·The Great Thief 버스트(자공댐/재장전속도+1736.31% Distributed 넉) 모델됨. Hit Rate만 보류 |
| Rapi: Red Hood | `rapi-red-hood` | Attacker | MG | Fire | ⚠ | Attachable Projectiles + 노멀카운터 기반 버스트 대미지 |
| Rei Ayanami | `rei-ayanami` | Attacker | MG | Fire | ✅ | (신규 2026-07-16, base) Attack Support: Fire 아군 flat ATK=caster ATK 25.03%(FB진입)·버스트: Fire 아군 AD+48.02% + 990.2% 넉·Preemptive Subdual: 노멀100회마다 112.37% 넉(gap #1 `every`) + 자 Elemental Advantage AD+30.23%/3s(other_elemental_bonus, Iron 보스 게이팅 Fire>Iron, refresh). 보류: 실드딜/실드생성(비-DPS)만. dollskills 데이터 비어있음(시그니처 없음, base-only) |
| Rei Ayanami (Tentative Name) | `rei-ayanami-tentative-name` | Attacker | AR | Wind | ⚠ | (신규 2026-07-16, base; `rei-ayanami`와 별개 유닛) Attack State 버스트: 자AD+35.9%+자flat ATK=caster ATK 63.36% + 990.2% 넉·Maintenance: 스쿼드 flat ATK=caster ATK 11.61%(FB진입)·Annihilation Support: Attack State 창(자버스트 10초) 중 노멀7회마다 286.37% "additional damage" 넉(gap #7). 보류: Anti A.T. Field 590.64% 페이로드+Annihilation State 아군버프(교차유닛 콜라보 상태), MG heating up speed |
| Neon: Vision Eye | `neon-vision-eye` | Attacker | RL | Electric | ⚠ | (신규 2026-07-16, base) Firepower Gauge가 매 사이클 100 리필 → Super Firepower 매 사이클 정상상태로 근사. Maximum Firepower: 자ATK+115.09%(FB진입)·Super Firepower 버스트: 자AD+155.24%(버스트 넉 없음)·Firepower Explosion: 풀차지마다 437.98% + Super Firepower 10초 창 중 +262.79%("additional damage", gap #7). 보류: 라이브 게이지, 넉의 projectile-explosion 타이핑(pulse 경로 미지원, 자기 킷 내 inert), Explosion Radius, 생존기 |
| Drake | `drake` | Attacker | SG | Fire | ⚠ | (신규 2026-07-16, base) Overcharge: 스쿼드 ATK+11.85%(FB진입)·Thunderbolt: 노멀10회마다 98.55% 넉(gap #1)·Drake Special 버스트: 1254% 넉 + 자 Max Ammo+72.18%. 보류: Hit Rate(inert) |
| Drake (Signature) | `drake-signature` | Attacker | SG | Fire | ⚠ | (신규 2026-07-16, 시그니처/듀얼슬롯) base + SG아군(squad 근사) ATK+63.88%/Max Ammo+50.14% + Thunderbolt 2차 트리거(노멀5회마다 201.6%) + Drake Special 3009.6% 넉 + 자AD+31.68%. 보류: Hit Rate(inert), 무기종 스코프(squad 근사) |
| Laplace | `laplace` | Attacker | RL | Iron | ⚠ | (신규 2026-07-16, base, 얇음) Hero Bomber: 마지막 탄 81.66% "additional" 넉(gap #1 last_bullet)·Laplace Buster First Damage 897.6%를 버스트 넉으로 모델. 보류(킷 대부분): 무기변형(5초 Buster 모드), Hero Vision(Pattern B 감쇠 스택)+맥스스택 true dmg, 파츠딜, 시그니처(더 큰 무기변형 → 듀얼슬롯 없음) |
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
