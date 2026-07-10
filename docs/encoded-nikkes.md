# 인코딩된 니케 목록

`backend/app/skill_rules/registry.py`의 `ENCODED_SLUGS` 기준. 덱 추천 엔진이
고려할 수 있는 니케는 이 목록뿐이다 (인코딩 안 된 니케는 후보에서 제외됨).

- 마지막 갱신: 2026-07-10
- 총 **31명** (Burst 1: 11명 · Burst 2: 16명 · Burst 3: 4명)
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
| Anis: Star | `anis-star` | Defender | RL | Electric | ⚠ | 버스트 재진입 분기, 풀차지 보너스 대미지 |
| D: Killer Wife | `d-killer-wife` | Supporter | SR | Fire | ⚠ | 풀차지 카운터 기반 CDR·공버프, Wipe-Out 디버프 |
| Liter | `liter` | Supporter | SMG | Iron | ✅ | Volt Boost(자힐, 생존계)만 미모델 |
| Little Mermaid | `little-mermaid` | Supporter | SMG | Wind | ⚠ | Bubble 5.05% 받댐증 모델됨. Bubble Barrage(아군총탄 카운터)·FB창 주기넉 보류 |
| Miranda (애장품) | `miranda` | Supporter | SMG | Fire | ⚠ | 노멀공격 카운터 자버프, 최고ATK아군 크리 |
| Moran (애장품) | `moran` | Defender | AR | Electric | ✅ | 무기변형 자해모드·생존계만 미모델 |
| Rouge | `rouge` | Supporter | SR | Electric | ⚠ | 풀차지 카운터 CDR, 후열 포지션 버프 |
| Soline: Frost Ticket | `soline-frost-ticket` | Supporter | SG | Water | ✅ | CDR만 모델링 (원래 역할이 로테이션 보조뿐) |
| Tove (애장품) | `tove` | Supporter | AR | Water | ✅ | 공속 버프, 샷건전용 변형만 미모델 |
| Volume | `volume` | Attacker | SMG | Wind | ✅ | Freestyle(킬 트리거, 레이드엔 무의미)만 미모델 |
| Zwei (애장품) | `zwei` | Supporter | SG | Electric | ⚠ | 라운드/노멀공격 스택 변형, 무기변형 |

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
| Mint | `mint` | Supporter | RL | Iron | 🔶 | Here I Go! 전체 보류 (본인 풀차지샷 트리거 부재) |
| Prika | `prika` | Supporter | SR | Water | 🔶 | 대부분 보류 — 본인 풀차지샷 + **Mint 교차유닛 시너지**(그녀의 실질 핵심 가치) |
| Helm: Aquamarine | `helm-aquamarine` | Attacker | AR | Iron | ⚠ | 노멀30회 넉, Electric속성 조건부 추가딜/디버프 (**자동발동 스킬은 엔진 확장으로 모델링됨**) |
| Velvet | `velvet` | Supporter | SR | Wind | 🔶 | 대부분 보류(자기전용) — ammo pouch 자원 + 본인 풀차지/노멀50회 카운터 |
| Rosanna: Chic Ocean | `rosanna-chic-ocean` | Supporter | AR | Wind | ⚠ | Spina di Rosa(30s 액티브, 지속딜 듀티사이클) 보류, 파츠파괴 스택 ATK 보류 |
| Takina Inoue | `takina-inoue` | Supporter | SR | Iron | ⚠ | 버스트 무기변형(200.64%) 보류. S2는 periodic 트리거로 모델(cd15s 아군 True Damage▲140%). 진댐 버프는 덱에 진댐 딜러 필요 |

## Burst 3 (4명)

| 이름 | 슬러그 | 클래스 | 무기 | 원소 | 완성도 | 주요 보류 내용 |
|---|---|---|---|---|---|---|
| Anis: Sparkling Summer | `anis-sparkling-summer` | Supporter | SG | Electric | ⚠ | last-bullet 넉/파츠 디버프(트리거 부재), Elemental Advantage Attack Damage(버킷 불명) |
| Helm (애장품) | `helm` | Attacker | SR | Water | ⚠ | 라스트불릿 트리거 + 풀차지 효과(힐/게이지/보너스딜) |
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
2. **교차 유닛 트리거** (다른 니케의 특정 스킬 발동을 감지) — Prika→Mint
   페어링처럼, 덱 조합 특화 시너지에 반복 등장할 가능성.
3. **ammo pouch류 자원 메커니즘** — Velvet. 수량 기반 자원 트래킹 없음.

네 항목 모두 `special-mechanics.md`에 상세 기록됨. 확장 여부는 Fienn 판단.

**해결된 갭**: "버스트와 무관한 자체 쿨다운 반복 발동 스킬"은 2026-07-10에
엔진 확장으로 해결됨 (`simulate_raid`의 `periodic_nukes`) — Helm: Aquamarine의
Aegis Cannon Suppression Fire가 첫 적용 사례.
