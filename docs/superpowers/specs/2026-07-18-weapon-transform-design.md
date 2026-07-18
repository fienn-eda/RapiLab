# 무기변형 (weapon-mode segments) 설계 — 초안 (논의 진행 중)

- 날짜: 2026-07-18
- 상태: **초안** — 섹션 1까지 논의됨, Fienn 승인 대기. 섹션 2(유닛별 적용)·
  섹션 3(테스트 전략)은 미작성.
- 참여: Fienn · Bot

## 배경과 범위

무기변형(버스트/상태가 유닛의 무기 프로필 자체를 바꾸는 메커니즘)은 남은
미인코딩 유닛의 최대 수요처다(`docs/roadmap.md` Phase 3 백로그). 이번 설계의
범위는 **전담 4명 + 잔여 메커니즘 3명** (Fienn 확정):

| 유닛 | 변형 내용 (Lv10 텍스트 기준) | 형태 |
|---|---|---|
| snow-white | 버스트: 차지 5초 · 499.5% · 풀차지 1000% · 장탄 1 · Pierce | 버스트 앵커 **단발형** |
| maxwell | 버스트: 차지 2초 · 813.42% · 풀차지 300% · 장탄 1 · Pierce | 버스트 앵커 **단발형** |
| laplace | 버스트: First 897.6% + 노멀 14.52% 틱 · 5초 (기존 인코딩 ⚠, 변형딜 보류분) | 버스트 앵커 지속형 |
| velvet | 버스트: 7% 틱 · 10초 (Perfect Execution, 기존 ⚠ 보류분) | 버스트 앵커 지속형 |
| cinderella-crystal-wave | 재장전 이벤트 구동 MG↔Snipe 토글 + 모드가 FB 넉 변종 게이팅 | **비버스트 상태머신** |
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

## 섹션 1 — 계약 · 세그먼트 생성기 · 배선 (승인 대기)

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

- 고정 길이 창은 `{"start": t0, "end": t1, "profile": ...}` (laplace·velvet형).
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

## 미논의 (다음 섹션)

- 섹션 2: 유닛별 적용 계획 — snow-white·maxwell·laplace·velvet·cinderella
  각각의 세그먼트 스케줄 + rapi(FB 창 노출 `scheduled_nukes`)·
  snow-white-heavy-arms(프로필 "풀차지 N연타" 확장 여부) 별도 처리.
- 섹션 3: 테스트 전략(TDD)·회귀 기준·red_hood 마이그레이션 여부.
- 미해결 인게임 질문: 변형샷이 자기 노멀공격 카운터에 포함되는가(유닛별
  인코딩 시 Fienn 확인).
