# 무기변형 (weapon-mode segments) 설계

- 날짜: 2026-07-18 (갱신 2026-07-19)
- 상태: **v1 + 계획 2 구현 완료 (2026-07-19)** — 설계 확정(전 섹션 Fienn 승인) 후
  `weapon_mode_schedules` 세그먼트 primitive + snow-white·maxwell·
  laplace-signature 신규 인코딩 + red-hood 마이그레이션(v1)까지 착지, 이어서
  v1이 이월했던 cinderella-crystal-wave 듀얼슬러그·rapi-red-hood FB창 노출·
  snow-white-heavy-arms 검증 패스(계획 2)까지 전부 착지. 아래 "구현 요약
  (계획 2 범위)" 참고.
- 참여: Fienn · Bot

## 배경과 범위

무기변형(버스트/상태가 유닛의 무기 프로필 자체를 바꾸는 메커니즘)은 남은
미인코딩 유닛의 최대 수요처다(`docs/roadmap.md` Phase 3 백로그). 이번 설계의
범위는 **전담 4명 + 잔여 메커니즘 3명** (Fienn 확정):

| 유닛 | 변형 내용 (Lv10 텍스트 기준) | 형태 |
|---|---|---|
| snow-white | 버스트: 차지 5초 · 499.5% · 풀차지 1000% · 장탄 1 · Pierce | 버스트 앵커 **단발형** |
| maxwell | 버스트: 차지 2초 · 813.42% · 풀차지 300% · 장탄 1 · Pierce | 버스트 앵커 **단발형** |
| laplace | 버스트: First 897.6% + 노멀 14.52% 틱 · 5초 (기존 인코딩 ⚠, 변형딜 보류분) | 버스트 앵커 지속형 → **laplace-signature 슬러그로 해소** (섹션 2) |
| velvet | 버스트: 7% 틱 · 10초 (Perfect Execution, 기존 ⚠ 보류분) | 버스트 앵커 지속형 → **보류 확정** (섹션 2) |
| cinderella-crystal-wave | ~~재장전 이벤트 구동 MG↔Snipe 토글~~ → **듀얼 변형 슬러그로 재분류** (아래 참고) | 세그먼트 대상 아님 |
| snow-white-heavy-arms | 차지 중 락온/장전 누적 → 풀차지 연속 히트, 버스트는 파라미터 변경 | 차지 루프 상태머신 (별도 검토) |
| rapi-red-hood | 120노멀마다 프로젝타일 발사 → FB 진입 시 폭발 | 무기 프로필 교체 **아님** (별도 경로) |

선례: `red_hood.py` (2026-07-18) — 엔진 확장 없이 Fienn 실측(10초 33발) 앵커
`scheduled_nukes`로 해결했으나 두 한계가 docstring에 명시돼 있다:
① 무기 패스가 창 안에서도 노멀샷을 계속 방출해 **정적 차감으로 이중계상을
근사**해야 했고, ② 차지 배수를 히트당 퍼센트에 상수로 접어 **덱의 차지댐/
차지속도 버퍼가 변형딜을 못 곱한다**. 변형이 헤드라인 딜인 유닛 4명에게 이
왜곡을 반복하면 "버퍼 시너지 랭킹"이라는 덱 빌더의 존재 이유가 정확히 그
지점에서 깨진다.

## 접근 선택 (Fienn 확정)

- **A. weapon-mode segments 엔진 프리미티브 ← 채택.** 수요 6~7건으로
  data-first 전략의 "빈도 증명 후 확장" 기준 충족.
- B. red_hood식 유닛별 scheduled_nukes 반복 — 기각: 덱 버프 왜곡 누적 +
  유닛별 실측 의존.
- C. 하이브리드(단발형만 소형 경로) — 기각: 경로 2개 유지보수.

## 섹션 1 — 계약 · 세그먼트 생성기 · 배선 (승인됨, 2026-07-18)

### 현재 구조 (변경 전)

`raid_simulator.py`의 무기 패스는 유닛마다 `generate_shot_times()`를 한 번
호출해 bare 발사 시각 리스트를 받고, 모든 발사에 동일한
`weapon["damage_percent"]`를 기록한다. "한 유닛 = 무기 하나 = 전투 내내 같은
프로필"이 하드코딩 — 변형 유닛이 막히는 근본 원인.

### ① 계약: 모듈이 세그먼트를 계산, 엔진이 방출

새 파라미터 `simulate_raid(..., weapon_mode_schedules={slug: schedule_fn})`.
schedule 함수는 `scheduled_nukes`의 schedule과 동형으로
`(context, fight_duration)`을 받아 구간 목록을 돌려준다:

```python
# 예: snow_white.py
def weapon_mode_schedule(context, fight_duration):
    return [
        {"start": t, "until_shots": 1,        # 1발 쏘면 종료 (단발형)
         "profile": {"weapon": "SR", "damage_percent": 499.5,
                     "charge_damage_percent": 1000.0,
                     "max_ammo": 1, "reload_time": 0.0, "charge_time": 5.0}}
        for t in context.burst_times.get("snow-white", [])
    ]
```

- 고정 길이 창은 `{"start": t0, "end": t1, "profile": ...}`
  (laplace-signature·red-hood형).
- `profile`은 기존 `weapon_stats` 항목과 **같은 모양** — 새 개념 없음.
- 창 앵커는 모듈 책임(버스트형은 `context.burst_times`, cinderella는 자기
  재장전 주기에서 결정론 계산). Ein/Raven의 "모듈이 계산, 엔진은 방출" 분업의
  무기 패스판.

### ② `attack_rate.py`: 세그먼트 생성기

새 함수 `generate_segmented_shots()`:

```
t=0 ─[기본 AR 발사]─ 버스트(t=20) ─[대포: 5초 차지 → t=25에 499.5%×10 1발]─
     ─[기본 AR, 새 매거진 즉시 재개]─ 다음 버스트 …
```

- 세그먼트 시작: 기본 무기 발사를 멈추고 오버라이드 프로필로 **새 매거진**
  시작.
- 세그먼트 종료(`end` 도달 또는 `until_shots` 소진): 기본 무기가 **새 매거진
  으로 즉시** 재개 (**Fienn 확정 2026-07-18, 인게임 기준**).
- 반환은 bare 시각이 아니라 **샷 레코드**: `(시각, damage_percent,
  charge_bonus, first/last 매거진 플래그)` — 구간별로 다른 딜을 기록하려면
  퍼센트가 샷에 실려야 한다.
- 기존 라이브 버프 콜러블(`charge_speed_percent_at` 등)은 세그먼트 안에서도
  그대로 평가 → 덱 차지속도 버퍼가 snow-white의 5초 차지를 실제로 단축하고,
  차지댐/ATK 버퍼가 변형샷을 곱한다. red_hood식 상수 접기에서 잃었던
  상호작용이 살아남.

### ③ `raid_simulator.py` 무기 패스: 옵트인 소비

- `weapon_mode_schedules`에 등록된 유닛만 새 생성기를 타고, 샷 레코드의
  per-샷 percent로 `record()`.
- first/last bullet 마커: 세그먼트 유닛은 별도 함수 재계산 대신 레코드의
  플래그를 사용 (laplace의 `last_bullet` 트리거가 변형 구간과 어긋나지 않게
  정합이 생성 시점에 보장됨).
- per-shot 카운터·resource fill·RoundGrant는 기존처럼 `shot_times`(레코드의
  시각 투영)를 소비 — 변형샷도 발사로 센다.
- **미등록 유닛은 기존 경로 무변경** — 순수 옵트인. 기존 유닛 출력 불변이
  회귀 기준.

## 확정된 시맨틱 (Fienn 판정)

- 변형 창 종료 후 기본 무기는 **가득 찬 새 매거진으로 즉시** 사격 재개
  (재장전 대기 없음). 2026-07-18.
- **cinderella-crystal-wave는 세그먼트 프리미티브 대상에서 제외** (Fienn,
  2026-07-18 스펙 리뷰): 이 유닛의 컨셉은 유저가 보스 특성에 맞춰 모드를
  미리 골라 전투 내내 유지하는 것이라 전투 중 전환이 매우 드물다. 따라서
  재장전 구동 토글 상태머신 대신 **"MG로 3분" / "Snipe로 3분" 두 케이스를
  각각 시뮬레이션**하고, 결과에 어느 모드였는지 표시한다.
  - 구현: julia/julia-signature·drake/drake-signature 듀얼슬러그 선례 —
    `cinderella-crystal-wave-mg` / `cinderella-crystal-wave-snipe` 두 슬러그를
    별도 덱 후보로 등록. 모드가 고정이면 각 변형은 **정적 무기 프로필**이라
    기존 엔진 경로 그대로 돌고, 모드 게이팅 부속 효과(FB 넉 변종 1189.66%
    전체 vs 833.79% 코어, Destroy vs Pinpoint 상시 버프)도 변형별 정적 배선.
    슬러그가 결과 표시를 겸한다.
  - 소항목: 두 변형이 같은 덱에 동시 편성되지 않게 하는 상호 배제 —
    julia/drake 선례가 로스터 레벨(투자 상태로 한쪽만 후보화)인지 탐색
    레벨인지 구현 착수 때 확인. cinderella는 항상 둘 다 후보라 명시적
    배제가 필요할 수 있음.
  - Snipe 프로필 세부(장탄 15 vs 풀차지 40발 소모 등 텍스트 모호)는
    인코딩 시 Fienn 확인.

## 섹션 2 — 유닛별 적용 계획 (승인됨, 2026-07-19)

**세그먼트 프리미티브 소비:**

| 유닛 | 세그먼트 스케줄 | 프로필 | 비고 |
|---|---|---|---|
| snow-white | 버스트마다 `until_shots: 1` | 차지 5초 · 499.5% · 풀차지 1000% · 장탄 1 | 데이터 완결 |
| maxwell | 버스트마다 `until_shots: 1` | 차지 2초 · 813.42% · 풀차지 300% · 장탄 1 | 데이터 완결 |
| **laplace-signature (신설)** | 버스트마다 10초 고정 창 | First 1회 + 노멀 93회 (**Fienn 실측 2026-07-19, 애장품 기준**) | julia/drake 듀얼슬러그 선례. base의 5초 변형은 계속 보류 (Fienn 확정 2026-07-19) |
| red-hood | **v1에서 마이그레이션** (Fienn 확정) | 실측 10초 33발 → rate 3.3/초 · 무한 매거진 프로필 | 기존 한계(덱 버퍼 미적용·정적 차감) 해소 |

- **velvet Perfect Execution은 보류 (Fienn 확정 2026-07-19):** B2 서포터의
  7% 틱은 덱 평가에 미미 — 변형딜은 계속 defer, 기존 버프 인코딩만 유지.
  세그먼트 소비자에서 제외.

- 지속형 케이던스는 무기종 조회 대신 프로필의 명시적 `rate_of_fire`로 입력
  (소규모 프로필 필드 추가).
- 미해결 인게임 질문: 변형샷이 자기 노멀공격 카운터에 포함되는가 — 유닛별
  인코딩 시 Fienn 확인.

**세그먼트 외 처리:**

- **cinderella-crystal-wave**: 듀얼슬러그 정적 프로필 (위 "확정된 시맨틱").
- **rapi-red-hood**: 프리미티브 무관. 필요한 엔진 변경은 `scheduled_nukes`
  context에 **풀버스트 창 시각 노출** 하나뿐(무기 패스가 이미 계산하는
  `full_burst_windows`를 컨텍스트에 싣는 소규모 확장). 모듈이 "120노멀 시점
  부착딜 → 다음 FB 진입 시각 폭발딜"을 결정론 계산.
- **snow-white-heavy-arms**: 이번 배치 **보류**. 핵심 딜이 차지 루프(락온
  누적 → 풀차지 시 105.59%×장전수 연타)라 세그먼트와 결이 다르고, 고정
  차지시간 덕에 기존 per-shot + multi-hit 프리미티브로 풀릴 가능성 — 프리미티브
  착지 후 별도 검증 패스.

**Velvet ammo pouch 시맨틱 (Fienn 2026-07-19):** pouch는 실탄이 아니라
"탄환 소모량으로 집계되는" 시너지 자원 — velvet은 실제로 풀차지 1발을 쏘지만
소모 탄환 수는 100발(S1)/300발(S2)로 계산된다. **파생 상호작용:** Little
Mermaid의 Bubble Barrage(아군 총탄 500발마다)는 현재 "샷 1발=1탄" 가정으로
`context.shot_times`를 합산하는데, velvet이 같은 덱이면 pouch 소모분이
카운터를 크게 가속한다 — Little Mermaid 모듈에 교차 항목으로 기록, 구현
여부는 인코딩 시 판단.

## 섹션 3 — 테스트 전략 (요약)

TDD. ① `attack_rate` 세그먼트 생성기 단위 테스트(경계에서 새 매거진 즉시
재개·`until_shots` 종료·세그먼트 안 라이브 버프 콜러블 평가·fight_duration
클리핑·세그먼트 없는 호출 = 기존 생성기와 동일 출력) → ② 무기 패스 옵트인
배선 테스트(레코드 percent로 record, first/last 플래그 정합) → ③ 유닛별
인코딩 테스트 → ④ engine-test-runner 전체 스위트. **미등록 유닛 출력 불변**
이 회귀 기준. red_hood 마이그레이션은 기존 테스트의 기대값이 바뀌므로(정적
차감 제거·버프 상호작용 추가) 마이그레이션 커밋에서 기대값 갱신을 명시적으로
수행.

## 구현 요약 (v1 범위) — 착지 완료 2026-07-19

- **엔진**: ① `attack_rate.generate_segmented_shots()`(세그먼트 단위 ShotRecord
  + first/last 플래그, 프로필에 명시적 `rate_of_fire` 허용, 전 유닛이 경유하도록
  통일) ② `simulate_raid(..., weapon_mode_schedules=)` 옵트인 배선.
- **유닛 (v1 실착지, 4명)**: snow-white(신규) · maxwell(신규) ·
  laplace-signature(신규 슬러그) · red-hood(마이그레이션, 정적 차감/상수 접기
  제거·덱 차지댐 버프 적용·총딜 ~+1.6%).
- **계획 2로 이동 (v1 범위 밖으로 확정, 세그먼트 비소비/미착수)**:
  ~~`scheduled_nukes` context에 풀버스트 창 노출(rapi용 소규모)~~ ·
  cinderella-crystal-wave-mg/-snipe(신규 듀얼, 정적 프로필 2벌) ·
  rapi-red-hood(FB 창 노출 소비) — 둘 다 이번 배치에서 미착수, 별도 계획으로
  이월.
- **명시적 보류**: velvet 변형딜(저가치, 보류 확정) · laplace base 변형(5초,
  실측 없음) · snow-white-heavy-arms(차지 루프 — 별도 검증 패스).

## 구현 요약 (계획 2 범위) — 착지 완료 2026-07-19

v1이 이월한 세 항목을 전부 닫았다. 세 유닛 모두 세그먼트 primitive 자체를
소비하지 않는다 — 세그먼트는 v1에서 이미 닫힌 범위이고, 계획 2는 v1이 남긴
잔여 갭 세 개가 각각 다른 소규모 확장(또는 확장 없음)으로 풀린다는 걸 보여준다.

- **cinderella-crystal-wave → `-mg`/`-snipe` 듀얼슬러그:** 위 "확정된 시맨틱"에
  적힌 설계 그대로 구현. `registry.MODE_VARIANTS["cinderella-crystal-wave"] =
  ("cinderella-crystal-wave-mg", "cinderella-crystal-wave-snipe")` — 소유 유닛
  1개를 로스터 로더가 후보 슬러그 둘로 fan-out, 덱 탐색은 `_no_variant_clash`로
  두 모드 동시 편성을 금지. Snipe의 SR 무기 프로필은 `_WEAPON_PROFILE_OVERRIDE_
  BUILDERS`가 스킬값 조립 후 교체. 신규 세그먼트 소비 없음 — 두 모드 모두 기존
  평범한(비변형) 무기 경로를 정적으로 탄다.
- **rapi-red-hood FB창 노출:** 설계가 예상한 그대로 소규모 — 새 스케줄
  primitive가 아니라 `SquadContext.full_burst_windows`(무기 패스가 이미 계산해
  둔 값을 컨텍스트에 얹기만 함) + `boss_core_hittable()` 조건 헬퍼 하나. 120노멀
  프로젝타일 발사기가 `scheduled_nukes` 두 항목(부착/폭발, 신규
  `projectile_attachment` 타입)으로 완성. **범위 추가(설계 문서엔 없었음):**
  착수 중 그녀의 Combat Assist(B1 대역)를 실제 B1 후보로 편성하는 신규 슬러그
  `rapi-red-hood-b1`이 함께 들어갔다 — `VARIANT_BURST_TIERS`로 B3가 아닌 B1
  슬롯에 앉히고, `SOLE_TIER1_SLUGS`로 진짜 B1과의 동시 편성(자기모순 —
  Combat Assist는 다른 B1이 있으면 스스로 꺼짐)을 막는다. `MODE_VARIANTS`가
  두 번째 소비자를 얻으며 "슬롯 재편성"이라는 세 번째 변형 축(모드 선택/
  듀얼슬롯 투자에 이어)을 실증.
- **snow-white-heavy-arms 검증 패스:** 설계가 남겨둔 질문("차지 루프가 기존
  per-shot + multi-hit 프리미티브로 풀리는지")에 대한 답은 **그렇다, 그리고
  세그먼트도 하나 더 필요했다**였다 — 신규 상태머신은 필요 없었다. 락온/장전
  누적은 고정 차지시간 안에서 결정론적(장전수는 모드별 상수)이라 별도 자원
  트래킹 없이 상수로 접혔고, Auto Fire(매 풀차지 발동)는 기존 `per_shot_rules`를
  그대로 탔다. 유일한 진짜 gap은 "Fully Active 상태의 강화 Auto Fire와 평시
  Auto Fire가 같은 풀차지 이벤트에서 이중계상되지 않게 막을 방법"이었는데,
  이건 세그먼트 primitive(Fully Active를 3.2초 차지 2발 세그먼트로 표현)와 신규
  `every_during_segment`/`every_outside_segment` per-shot 모드 조합으로 풀렸다 —
  두 모드는 샷의 시각이 아니라 레코드 정체성으로 매칭돼 구조적으로 상호
  배타적이다(세그먼트 경계에서 종료 샷과 재개 샷이 같은 시각을 가질 수 있어
  시각 매칭은 안전하지 않았다). Fully Active 세그먼트 프로필은 자기 기본무기
  스탯(차지 배수)을 읽어야 해서, 신규 `caster_weapon_stats` 스킬값 주입도 함께
  들어갔다.
- **엔진 (4개, 계획 2)**: `SquadContext.full_burst_windows`+`core_hittable`
  노출 + `boss_core_hittable()` · `projectile_attachment` 데미지 타입/스탯 ·
  `MODE_VARIANTS`/`VARIANT_BURST_TIERS`/`_WEAPON_PROFILE_OVERRIDE_BUILDERS`/
  `SOLE_TIER1_SLUGS` 모드-변형 듀얼슬러그 확장(로스터 fan-out + 덱 탐색
  양쪽 enumeration 경로·pruning 참조덱까지 배제 정합) · `every_during_segment`/
  `every_outside_segment` per-shot 모드 + `caster_weapon_stats` 스킬값 주입.
  상세는 `docs/engine-gaps.md`의 "이미 만든 것" 참고.
- **유닛 (계획 2 실착지, 4슬러그)**: cinderella-crystal-wave-mg(신규) ·
  cinderella-crystal-wave-snipe(신규) · rapi-red-hood-b1(신규, 범위 추가) ·
  snow-white-heavy-arms(신규, 세그먼트 소비하되 세그먼트 자체는 v1 범위).
  rapi-red-hood(base)는 기존 ⚠ 인코딩에 발사기가 더해져 갱신.
- **여전히 보류**: velvet 변형딜(저가치, 보류 확정) · laplace base 변형(5초,
  실측 없음, 보류) — v1 요약과 동일, 계획 2에서 변경 없음.
