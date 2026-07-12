# 인코딩된 니케 목록

`backend/app/skill_rules/registry.py`의 `ENCODED_SLUGS` 기준. 덱 추천 엔진이
고려할 수 있는 니케는 이 목록뿐이다 (인코딩 안 된 니케는 후보에서 제외됨).

- 마지막 갱신: 2026-07-12
- 총 **42명** (Burst 1: 11명 · Burst 2: 16명 · Burst 3: 15명)
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
| Little Mermaid | `little-mermaid` | Supporter | SMG | Wind | ⚠ | Bubble 5.05% 받댐증 모델됨. Bubble Barrage(아군총탄 카운터)·FB창 주기넉 보류 |
| Miranda (애장품) | `miranda` | Supporter | SMG | Fire | ✅ | Health Up 자ATK(노멀30회마다, per_shot)·Wake Up 스쿼드 크리댐/자버프 + **최고ATK top-1 크리율(1 round=탄수 버프)**·Powering Up **최고ATK top-2 정확 타겟팅**(ATK/크리댐) 모델됨. Hit Rate(inert)만 보류 |
| Moran (애장품) | `moran` | Defender | AR | Electric | ✅ | 무기변형 자해모드·생존계만 미모델 |
| Rouge | `rouge` | Supporter | SR | Electric | ⚠ | Card Throw CDR(8풀차지→7s, 매 사이클 근사)·Sword Coin AD(후열 가정, 상시)·Game Master ATK(**15.07%로 버그수정**, 기존 30.02 오독)·Max HP 버프(flat_max_hp, inert·향후 HP스케일용) 모델됨. Shield Coin(생존)만 보류 |
| Soline: Frost Ticket | `soline-frost-ticket` | Supporter | SG | Water | ✅ | CDR만 모델링 (원래 역할이 로테이션 보조뿐) |
| Tove (애장품) | `tove` | Supporter | AR | Water | ✅ | 공속 버프, 샷건전용 변형만 미모델 |
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
| Arcana | `arcana` | Supporter | RL | Electric | ⚠ | "이미 버스트한 버스트3 전기속성 아군" 대상 버프(수치 큼) |
| Arcana: Fortune Mate | `arcana-fortune-mate` | Attacker | SG | Fire | 🔶 | 노멀공격 스택 체인(펠릿·Precious Moments) 대부분 보류 |
| Grave | `grave` | Supporter | AR | Fire | ⚠ | Overheat(노멀공격 카운터 자버프) |
| Brid: Silent Track | `brid-silent-track` | Supporter | SG | Fire | ⚠ | 노멀5회마다 675% 넉 모델됨(per-shot). Wind속성 조건부 디버프만 보류(boss-element 갭) |
| Nayuta | `nayuta` | Supporter | SMG | Wind | ⚠ | 무기변형(Memory Incineration) + 복합트리거 넉 |
| Mint | `mint` | Supporter | RL | Iron | ✅ | Here I Go!(풀차지마다 스쿼드 ATK) 단독+Prika 조합 모두 모델(버스트타임 패리티/Encore 핀 시각). Dancing 자힐만 보류 |
| Prika | `prika` | Supporter | SR | Water | ✅ | 본인 풀차지 스쿼드 버프(refresh, 중첩 아님) + **Mint Encore 교차유닛 시너지**(`ally_burst_activate`) 모델됨. Performance 지속시간/자기 CD 등 비딜 부기만 보류 |
| Helm: Aquamarine | `helm-aquamarine` | Attacker | AR | Iron | ⚠ | 노멀30회 넉, Electric속성 조건부 추가딜/디버프 (**자동발동 스킬은 엔진 확장으로 모델링됨**) |
| Velvet | `velvet` | Supporter | SR | Wind | 🔶 | 대부분 보류(자기전용) — ammo pouch 자원 + 본인 풀차지/노멀50회 카운터 |
| Rosanna: Chic Ocean | `rosanna-chic-ocean` | Supporter | AR | Wind | ⚠ | Spina di Rosa(30s 액티브, 지속딜 듀티사이클) 보류, 파츠파괴 스택 ATK 보류 |
| Takina Inoue | `takina-inoue` | Supporter | SR | Iron | ⚠ | 버스트 무기변형(200.64%) 보류. S2는 periodic 트리거로 모델(cd15s 아군 True Damage▲140%). 진댐 버프는 덱에 진댐 딜러 필요 |

## Burst 3 (15명)

> **eb (encoding batch) 진행:** Burst 3 어태커 배치 인코딩 (least-blocked 우선).
> eb1 = Noir · Isabel · Liberalio, eb2 = Ludmilla · Chisato · Jill (2026-07-12).
> **자원 primitive beachhead (gap #2 Pattern A, 2026-07-12):** Modernia · Guillotine:
> Winter Slayer — named-resource/캡 스택 카운터 엔진 확장의 첫 소비자.
> **count-스케일 넉 + multi-hit 버스트 + periodic fill (2026-07-12):** Julia(base) ·
> Julia(시그니처, 별도 slug `julia-signature`) · Cinderella — `resource_scaled_nukes`/
> `burst_hit_counts`/periodic 자원 fill 엔진 확장의 소비자. Guillotine의 Extermination
> Hero-Level DoT도 이때 완성.
> **나머지 백로그는 [`roadmap.md`](roadmap.md) To-Do 참고** (대부분 남은 Pattern A
> 자원 유닛 / Pattern B 게이지·변신 / 상태머신 / 무기변형 갭).

| 이름 | 슬러그 | 클래스 | 무기 | 원소 | 완성도 | 주요 보류 내용 |
|---|---|---|---|---|---|---|
| Anis: Sparkling Summer | `anis-sparkling-summer` | Supporter | SG | Electric | ⚠ | last-bullet 넉/파츠 디버프(트리거 부재), Elemental Advantage Attack Damage(버킷 불명) |
| Chisato Nishikigi | `chisato-nishikigi` | Attacker | SMG | Iron | ✅ | eb2. Extrasensory 상시 자ATK/진댐(버스트 재충전으로 >70% 유지 근사)·버스트 자ATK/노멀진댐화·48노멀마다 진댐넉(per-shot) 모델됨. per-shot 넉이 attack타입(진댐 언더카운트)·회피/명중(inert) 보류 |
| Cinderella | `cinderella` | Attacker | RL | Fire | ⚠ | Flawless Glass 자ATK(자기 최대체력 비례)+매 풀차지 136.6% 추가딜(RL 상시 풀차지, per-shot)·Beautiful 자원(periodic fill, 3초마다·캡12)·Glass Slippers 10연타 버스트넉 + Beautiful 스택수 비례 추가딜(count-스케일 넉) 모델됨. 디코이 생성(생존)·Beautiful 자체 최대체력% 증가(연결된 소비자 없음, inert)만 보류 |
| Guillotine: Winter Slayer | `guillotine-winter-slayer` | Attacker | AR | Water | ⚠ | 자원 beachhead. EXP 자원(자ATK ▲1.81%/스택, 캡100, 연속)·Hero Level 파생 Water 아군 버프(레벨 스케일)·core-conditional fill·Extermination Water 버프 + **Hero-Level 스케일 10틱 지속딜(매 틱 자기 시각 기준 count 재조회, count-스케일 넉)** 모델됨. 레벨업 리로드/힐(딜 아님)만 보류 |
| Helm (애장품) | `helm` | Attacker | SR | Water | ⚠ | 라스트불릿 트리거 + 풀차지 효과(힐/게이지/보너스딜) |
| Isabel | `isabel` | Attacker | SG | Electric | ✅ | eb1. Marked Target 이스컬레이팅 자버프(refresh)·Pointed Feather 주기넉(cd15)·Sonic Chaser 버스트넉 + 단계별 추가딜(activation_count 게이팅, 사이클 정확)·받댐 디버프 모델됨. Full Burst Duration▲(로테 타이밍)만 보류 |
| Jill Valentine | `jill-valentine` | Attacker | AR | Electric | ⚠ | eb2(부분). FB 자ATK·버스트 진댐/공댐/재장전속도/노멀진댐화 모델됨. Magnum(9탄 노멀배수)·Acid(재장전 지속딜 DoT)·명중(inert) 보류 |
| Julia | `julia` | Attacker | AR | Water | ⚠ | Decrescendo 자크리율(periodic, cd20)·Climax 버스트넉(544.5%, 단일히트) 모델됨. Crescendo(라스트불릿 트리거, 매거진경계 마커 부재)·이에 게이팅된 Climax 추가딜 보류 |
| Julia (시그니처, 별도 slug) | `julia-signature` | Attacker | AR | Water | ⚠ | base와 별도 roster 엔트리(Fienn 결정, 2026-07-12). Decrescendo 자크리율/자ATK(periodic + 전투시작 강제시전)·Climax 5연타 버스트넉(544.5%×5, `burst_hit_counts`) 모델됨. Crescendo/Marcato(크리티컬 히트 카운터 — 기대값 크리 모델과 구조적으로 불가, 영구 defer)·노멀전용 크리율(버킷 없음)만 보류 |
| Liberalio | `liberalio` | Attacker | SR | Wind | ✅ | eb1. 버스트넉 925%·FB 자ATK·Raging Current 공버프 231%(풀차지 per-shot 상시)·on-core 공버프·풀차지 추가딜 5회 모델됨. Gentle Current(비-보스 대상, solo N/A)·차지속도(inert) 보류 |
| Ludmilla: Winter Owner | `ludmilla-winter-owner` | Attacker | MG | Water | ✅ | eb2. 60노멀마다 받댐 디버프+넉(per-shot)·FB 자크리율·버스트 자ATK/재장전속도 모델됨. Snowstorm 코어60넉(코어카운터 과대평가 우려로 보류)·재장전 탄약(QoL) 보류 |
| Modernia | `modernia` | Attacker | MG | Fire | ⚠ | 자원 beachhead. High-Speed Evolution 히트당 3.05% 추가딜(per-shot)·200히트마다 Crit Dmg/Max Ammo 스택(캡5·10초 시한 자원) 모델됨. Max Ammo 스택은 자기 탄창 재생성 전 계산돼 inert·Giant Leap 상태게이팅 200히트 ATK버프(윈도 자원, 유의미·보류)·New World 버스트(Destroy Mode·무한탄·FB연장) 보류 |
| Noir | `noir` | Attacker | SG | Wind | ✅ | eb1. 버스트넉 351.64%·Lucky Charm 스쿼드 ATK(caster 비례)·Finale 파츠딜 버프 모델됨. Rabbit Twins 탄약/재장전(QoL)·Hit Rate(inert)만 보류 |
| Privaty (애장품) | `privaty` | Attacker | AR | Water | ⚠ | LD Assault(퍼샷 인스턴스), 지정타겟 조건부 효과 |
| Rapi: Red Hood | `rapi-red-hood` | Attacker | MG | Fire | ⚠ | Attachable Projectiles + 노멀카운터 기반 버스트 대미지 |

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
3. **ammo pouch류 자원 메커니즘** — Velvet. 수량 기반 자원 트래킹 없음.

네 항목 모두 `special-mechanics.md`에 상세 기록됨. 확장 여부는 Fienn 판단.

**해결된 갭**: "버스트와 무관한 자체 쿨다운 반복 발동 스킬"은 2026-07-10에
엔진 확장으로 해결됨 (`simulate_raid`의 `periodic_nukes`) — Helm: Aquamarine의
Aegis Cannon Suppression Fire가 첫 적용 사례.
