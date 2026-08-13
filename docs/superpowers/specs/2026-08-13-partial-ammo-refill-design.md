# 부분 재장전 / 탄약 환급 — 단위·트리거·대상 불일치 해소 (2026-08-13)

## 무엇이 막혀 있나

엔진의 탄약 환급은 `attack_rate.AmmoRefund` 하나이고, 그 모양은 **「자기 발수
카운터로, 전투 내내, 정수 발수를, 자기에게」** 다. 게임이 쓰는 「재장전」 문구는 그보다
넓어서, 여섯 줄이 표현 수단이 없다는 이유로 보류돼 있다.

| # | 슬러그 | 원문 (lv10) | 값 | 단위 | 트리거 | 대상 |
|---|---|---|---|---|---|---|
| 1 | `noir` | Rabbit Twins B: `Activates when entering Full Burst. Affects all allies. / Reload 39.88% magazine(s).` | 39.88% | **%** | 풀버스트 진입 | **아군 전원** |
| 2 | `little-mermaid` | Siren's Song: `Affects all allies. / Reloads 33.26% magazine(s).` | 33.26% | **%** | 자기 버스트 | **아군 전원** |
| 3 | `asuka-shikinami-langley-wille` | Annihilation State: `Effect 2: Reloads 21% magazine(s).` | 21% | **%** | 자기 버스트 | 자기 |
| 4 | `arcana-fortune-mate` | Making Memories: `Effect 2: Reloads 2 round(s).` | 2발 | 발수 | 자기 버스트 | 자기 |
| 5 | `arcana-fortune-mate` | 로테이션: `Two times: Reloads 6 rounds.` | 6발 | 발수 | **창 안 2·8·14…번째 평타** | 자기 |
| 6 | `tove-signature` | Emergency-Crafted Bullets: `Activates after 10 normal attack(s). Affects self. / Reload 5.31% of the magazine.` | 5.31% | **%** | 10발마다 | 자기 |

여섯 줄 전부 **floor**다 — 넣으면 딜이 는다. 넣기 전 그녀들의 발사 수는 하한이다.

**엔진이 이미 하는 것**: `scarlet-black-shadow`의 Asura가 「풀버스트 진입 시 즉시
100% 재장전」을 길이 0 `weapon_mode_schedules` 세그먼트로 표현한다. 즉 「이벤트 트리거
즉시 재장전」이라는 개념 자체는 있고, 없는 것은 **부분 %**와 **아군 대상** 둘이다.

## 이 설계가 다루지 않는 것

- **`tove`(base 빌드)** — lv10 원문이 `There is a 5% chance of activating when
  attacking`이다. 확률 롤은 결정론적 엔진이 표현할 수 없고, 기대값으로 펴는 것은 이
  저장소가 반복해서 거절해 온 종류의 근사다. 계속 보류.
- **`asuka`의 Emergency Repair `Removes 100% of ammo`** — 탄약 제거 상태머신(gap #11의
  모양)이고 환급이 아니다. 별건.
- **`charge_window.py`** — 아래 「배선」 참고. 범위 밖이다.

**공짜로 따라오는 것**: `scarlet-black-shadow`의 「스킬 레벨 7 미만에서 Asura가 30%/60%
부분 재장전」 보류는 이 프리미티브가 그대로 덮는다. 프로덕션은 lv10(100%)이라 **inert**
이므로 작업은 없고, 그 독스트링의 보류 사유만 갱신하면 된다.

## Fienn 판정 둘 (2026-08-13)

이 설계의 산술을 정하는 두 가지이고, 코드로는 유도할 수 없다.

1. **퍼센트가 발수로 안 떨어지면 반올림한다.** 기존 `max_ammo` 규약(「탄창 크기는 가장
   가까운 정수로 반올림」)과 같은 방향이다.
2. **재장전 중에 떨어진 환급은 버려진다.** 재장전은 그대로 끝나고 그 환급은 값이 0이다.

판정 2의 결과로 아군 대상 환급은 **타이밍 의존**이 된다 — 풀버스트 진입 순간 마침
재장전 중인 아군은 아무것도 못 받는다. 이것이 「탄창 % 버프로 근사하면 된다」를
기각하는 이유이기도 하다(기존 `AmmoRefund` 독스트링의 비단조성 논거와 같은 뿌리).

## 왜 이게 가능한가 — 버스트 일정이 발사 생성보다 먼저다

`simulate_burst_cycle`은 `(deck, gauge_charge_time, fight_duration, mode)`만 받고
**발사 시각을 보지 않는다**(`raid_simulator.py:1162`). 그 결과 `events`와
`full_burst_windows`가 유닛별 발사 생성(`:1277`)보다 **먼저** 확정된다.

따라서 「풀버스트 진입 시」·「내 버스트 때」·「이 창 안에서만」은 전부 발사 생성 시점에
이미 아는 시각이다. 모더니아의 「최대장탄이 이미 짜인 탄창을 되돌려 못 키운다」와 달리,
이 작업은 **자원 해석 패스에 의존하지 않는다.**

## 접근법

**채택 — A. 시각 트리거 환급을 탄창 워크에 끼운다.** `magazine_shot_count`는 이미
발 단위로 걷는다(환급 값이 탄창 잔량에 의존하므로). 여기에 시각 트리거를 더한다.

**기각 — B. 스칼렛의 길이 0 세그먼트를 부분 %로 확장.** 세그먼트 경계는 「전부 아니면
전무의 새 탄창」으로 문서화돼 있고 세그먼트는 **무기 모드** 개념이다. 남의 버프로 내
총이 채워지는 것을 무기 모드로 표현하면 두 개념이 섞이고, 아군 대상이면 풀버스트
15회 × 아군 5명만큼 세그먼트를 남의 스케줄에 주입해야 한다. 세그먼트는 비싼 경로다.

**기각 — C. 타임라인 생성 후 후처리로 깁기.** 환급은 이후의 모든 발사 시각과 재장전
위상을 바꾸므로 「깁는다」가 곧 「생성기를 다시 돈다」이다. 절약이 없다.

## 자료구조

기존 `AmmoRefund`가 세 축을 얻는다. **기본값은 전부 현재 동작이다.**

```python
@dataclass(frozen=True)
class AmmoRefund:
    every_shots: int
    rounds: int = 0
    percent: float = 0.0     # 탄창 용량의 %, 반올림
    first_shot: int = 0      # 0 = every_shots와 동일 (지금 동작)
    windows: tuple = ()      # 비면 전투 내내·카운터 누적 (지금 동작)
```

새 타입 하나가 시각 트리거를 표현한다.

```python
@dataclass(frozen=True)
class AmmoRefill:
    time: float              # 전투 절대 시각
    rounds: int = 0
    percent: float = 0.0
```

둘 다 `rounds_for(capacity)` 하나로 발수를 낸다. 퍼센트는 **그 탄창의 라이브 용량**에
대해 반올림한다.

`first_shot`의 뜻: 지금 동작은 `every_shots`, `2×every_shots`, …번째 발에서 터진다.
`first_shot=F`를 주면 `F`, `F+every_shots`, `F+2×every_shots`, … 가 된다. 아르카나는
`(F=2, every=6)`이므로 2·8·14…이고, 6·12·18이 **아니다.**

**가드가 내려간다.** 지금 `AmmoRefund.__post_init__`은 「환급이 발사보다 많으면 탄창이
안 빈다」를 `rounds >= every_shots`로 본다. 퍼센트는 용량을 알아야 판정되므로, 이
검증은 `_refund_sequence`(용량 모름)에서 `magazine_shot_count`(용량 앎)로 내려간다.
순수한 이동이 아니라 **검증 시점이 생성자에서 워크로 늦춰지는 것**이다.

## 배선 — 깔때기 하나

`magazine_shot_count` 호출부는 **11곳**이다: `attack_rate` 안의 여섯 생성기(탄창·차지
× 발사·마지막탄·첫탄)와 세그먼트 경로 둘, 그리고 `charge_window` 셋. MG 예열이
배선 지점 넷 때문에 `magazine_shot_offset`을 뽑아야 했던 것과 같은 구조다 — **로직은
전부 이 함수 안에 둔다.** 생성기 루프에 흩으면 열 군데가 따로 놀다 어긋난다.

```python
def magazine_shot_count(capacity, shots_before, refund, *,
                        magazine_start=None, shot_interval=None,
                        spinup=None, refills=()):
```

- `refills`가 비고 `windows`가 비면 **현재 루프 그대로** 돈다. 시각 산술을 한 줄도
  하지 않으므로 기존 타임라인은 **비트 동일**이다(`refund is None`과 같은 규약).
- 아니면 같은 워크를 돌되 라운드 `i`의 시각을
  `magazine_start + magazine_shot_offset(i, shot_interval, spinup)`로 얻는다. 이미
  순수 함수라 새 산술이 아니다.
- **`time < magazine_start`인 `AmmoRefill`은 버린다.** 그것이 판정 2다. 탄창은 시간
  순으로 처리되므로 매 탄창에 전체 튜플을 넘겨도 결과가 같고 상태를 들 필요가 없다.

### 이벤트를 만드는 전처리

유닛 루프 직전에 한 번 계산한다.

```python
ammo_refills = resolve_ammo_refills(deck, events)   # {slug: (AmmoRefill, ...)}
```

`events`에서 트리거 시각을 읽고(느와르는 `full_burst_start`, 나머지는 시전자 자신의
`burst`), 스코프에 따라 수신자에게 나눠 담는다. 루프 안에서 기존 환급과 나란히 실린다:

```python
weapon = {**weapon,
          "ammo_refund": resolve_ammo_refunds(weapon, boss_element),
          "ammo_refills": ammo_refills.get(slug, ())}
```

선언 경로는 기존 `get_skill_ammo_refund`를 그대로 흉내 낸다 —
`registry.get_ammo_refill_grant(slug, values)` → `roster`가
`timeline["ammo_refill_grant"]`에 싣기. **로스터는 덱을 조립할 뿐 인카운터를 모르므로
시각 해석은 지금처럼 시뮬레이터가 한다**(보스 원소 게이트와 같은 규약).

### `charge_window.py`는 범위 밖

한 개 풀버스트 창짜리 UI 계산기이고 **전투 절대 시각이 없다.** 자기 문서에 「창 시작 시
탄창은 가득」을 명시적 가정으로 적어두고 있다. `refills=()`를 넘겨 현재 동작을 유지한다.
(느와르가 낀 덱이라면 그 화면에도 두 번째 그런 사실이 생기지만, 그 계산기는 덱이 아니라
유닛 하나의 입력을 받는다. 별도 작업이다.)

## 아르카나는 창 게이트가 아니라 로테이션이다

원문이 명시한다:

```
Effect varies according to the number of attacks. Only one effect is triggered
at a time. Resets when Making Memories is removed.
Two times: Reloads 6 rounds.
Four times: Happy Memories ...
Six times: Precious Moments ...
```

즉 「6발마다」가 아니라 **주기 6짜리 로테이션의 한 위상**이고, 카운터는 Making
Memories가 걷힐 때(=매 풀버스트) **리셋**된다. Fienn이 18발까지 세어 확인한 결정적
부정도 같은 것을 말한다 — **12번째에서는 재장전이 안 뜬다.**

인코딩: `first_shot=2, every_shots=6, rounds=6, windows=(그녀 버스트 → 그 사이클
풀버스트 종료, ...)`.

**왜 기존 룰 기계를 못 쓰나.** 나머지 두 위상은
`per_shot_cycle_from_own_burst_to_full_burst_end` 필 모드로 이미 표현돼 있다. 그러나
그 패스는 `shot_times`가 **이미 있을 때** 돌고, 재장전은 바로 그 `shot_times`를 바꾼다.
자기 참조라 룰 쪽에 둘 수 없고 워크 안에서 앞으로 걸으며 세야 한다. 창의 경계(그녀
버스트 시각, 그 사이클 FB 종료)는 `events`에 있으므로 생성 시점에 이미 안다.

이 줄이 여섯 중 가장 비싸다 — 나머지 다섯은 필드 둘로 끝나는데 이것만 축 둘을 더
요구한다. 그래서 **구현 순서에서 마지막**에 두어, 앞 다섯이 초록인 상태에서 떼어낼 수
있게 한다.

## 짚어둔 근사

느와르의 환급은 **자기가 같은 순간에 주는 `max_ammo_rounds +5`와 같은 시각**에
떨어진다(`noir.py:78`, 이미 인코딩됨). 엔진은 탄창 용량을 탄창 시작 시각에 한 번만
읽으므로, 39.88%는 **그 탄창이 만들어질 때의 용량**에 대해 계산된다. 새 근사가 아니라
기존 max-ammo 입도 그대로이고, 「퍼센트는 그 탄창의 라이브 용량에 대해」와 일관된다.

## 테스트

원칙: **「구현을 어떻게 망가뜨리면 이게 빨개지나」에 답 못 하는 테스트는 쓰지 않는다.**

### 깔때기

| 테스트 | 깨뜨리는 방법 |
|---|---|
| 기존 `test_ammo_refund.py` **17건**이 **한 글자도 안 바뀌고** 초록 | 빈 `refills`에서 시각 산술을 타면 값이 어긋난다 |
| `AmmoRefund(10, percent=5.31)` @ 용량 60 → **3발**, @ 용량 9 → **0발** | 반올림을 버림/올림으로 바꾸면 둘 중 하나가 깨진다 |
| 해석된 발수 ≥ `every_shots`면 `ValueError` | 가드를 지우면 워크가 안 끝나 테스트가 멈춘다 |

### 시각 트리거

| 테스트 | 깨뜨리는 방법 |
|---|---|
| **재장전 구간에 떨어진 환급은 버려진다** — 탄창이 비는 시각과 다음 탄창 시작 사이에 `AmmoRefill`을 두면 다음 탄창은 평범한 만탄 | `time < magazine_start` 드롭을 빼면 다음 탄창으로 이월돼 발수가 는다 |
| 상한 캡 — 1발만 쓴 탄창에 39.88%가 떨어지면 **1발**만 돌아온다 | `min(capacity, ...)`를 빼면 용량을 넘는다 |
| 아군 팬아웃 — 느와르가 낀 덱에서 **다섯 명 전원(그녀 포함)** 이 진입 시각을 받는다 | 스코프를 self로 두면 네 명이 빈 튜플이라 빨개진다 |

### 아르카나 로테이션

실측이 이미 있는 것이 이 줄의 강점이다.

- 창 안 2·8·14번째 발에서 재장전이 뜬다
- **12번째에서는 안 뜬다** ← `first_shot`을 무시하고 `every_shots`만 보면(6·12·18)
  정확히 이 한 줄이 빨개진다
- 창이 닫혔다 열리면 카운터가 2부터 다시 시작한다 ← 리셋을 빼면 위상이 창을 가로질러
  끌려간다

### 유닛 여섯과 캘리브레이션

각 슬러그에 대해 「딜이 늘었다」가 아니라 **발사 수의 절대값**을 고정한다. 「늘었다」는
기준선을 같은 코드로 계산하면 토톨로지가 된다.

**캘리브레이션은 움직인다.** 아스카(덱3)와 리틀머메이드(덱2)가 실기록 좌석에 있고 둘 다
floor라 위로 간다. 리틀머메이드는 이미 1.154x이므로 **더 멀어진다** — 회귀가 아니라
상한의 성질이므로(`sim/record`는 목표가 아니라 상한) 착륙 전후 값을 재서 문서에 남기고
되돌리지 않는다.

### 성능

환급이 없는 유닛은 빈 튜플이라 비용이 정확히 0이다. 있는 유닛은 탄창(≈13) × 환급(≤15)
비교라 발사 생성 자체에 비하면 작을 것으로 보이지만 **가정하지 않고
`scripts/bench_evaluate_deck.py`로 잰다.**

## 구현 순서

TDD로 **깔때기 → 시각 트리거 → 아군 팬아웃 → 유닛 다섯 → 아르카나**. 아르카나는 축이
둘 더 붙으므로 마지막에 둔다.
