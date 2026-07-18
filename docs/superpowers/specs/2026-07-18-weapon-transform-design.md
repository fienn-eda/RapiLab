# 무기변형 (weapon-mode segments) 설계

- 날짜: 2026-07-18 (갱신 2026-07-19)
- 상태: **설계 확정** (2026-07-19) — 전 섹션 Fienn 승인. 잔여 확인 2건도
  해소(velvet 변형딜 보류, laplace-signature 슬러그 신설). 다음 단계:
  구현 계획(writing-plans).
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

## 구현 요약 (v1 범위)

- **엔진**: ① `attack_rate.generate_segmented_shots()`(샷 레코드 + first/last
  플래그, 프로필에 명시적 `rate_of_fire` 허용) ② `simulate_raid(...,
  weapon_mode_schedules=)` 옵트인 배선 ③ `scheduled_nukes` context에
  풀버스트 창 노출(rapi용 소규모).
- **유닛**: snow-white(신규) · maxwell(신규) · laplace-signature(신규 슬러그)
  · red-hood(마이그레이션) · cinderella-crystal-wave-mg/-snipe(신규 듀얼,
  세그먼트 비소비) · rapi-red-hood(신규, FB 창 노출 소비).
- **명시적 보류**: velvet 변형딜(저가치) · laplace base 변형(5초, 실측 없음)
  · snow-white-heavy-arms(차지 루프 — 별도 검증 패스).
