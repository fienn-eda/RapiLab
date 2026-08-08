# 유닛별 코어 대미지 배율 — 설계

**날짜:** 2026-08-08
**갭:** `docs/engine-gaps.md` — 「코어 보너스 배율이 유닛별로 다르다」
**선행 설계:** `docs/superpowers/specs/2026-08-07-hit-rate-core-accuracy-design.md` §9

코어 히트 한 발이 몇 배를 때리는지가 유닛마다 다르다. 엔진은 전원에게 2.0배를
쓰고 있고, 그래서 2.5배인 유닛들이 과소 계상 중이다. 이 문서는 그 배율을
유닛별 상수로 만든다.

**명중률 작업과 섞지 않는다.** 그쪽은 코어에 *맞을 확률*이고 이건 맞았을 때의
*크기*다. 두 항은 `damage_formula._major_modifiers`에서
`core_hit_rate x (core_hit_bonus + other_core_damage_sources)`로 곱해지므로
서로 독립이고, 이 설계는 가운데 항 하나만 건드린다.

## 배경 — 지금의 지형

`raid_simulator.CORE_HIT_BONUS = 1.0`은 major modifier의 가산 버킷에 들어가
`1 + 1.0 = 2.0배`가 된다. 이 상수는 **엔진 전체에서 한 곳**에서만 읽힌다
(`raid_simulator.py:907`).

게임 데이터의 대응 필드는 `shot_detail.core_damage_rate`이고, 같은
`shot_detail`의 원문이 그 뜻을 적어 준다:

> Deals {core_damage_rate}% damage when attacking core.

만분율이라 `20000`은 200% = 2.0배다. 엔진의 기본값과 일치한다. 그러므로
환산은 하나뿐이다:

```
core_hit_bonus = core_damage_rate / 10000 - 1
```

## 1. 데이터 — 유닛별이지 무기별이 아니다

`data/shiftypad/raw/*.json` 83번들 전수:

| 무기 | 20000 | 25000 |
|-----|------:|------:|
| AR  | 18 | — |
| MG  | 14 | — |
| RL  | 14 | — |
| SG  | 13 | — |
| SR  | 17 | — |
| SMG | 3  | **4** |

**SMG 안에서 갈린다** — 나유타·볼륨·리타는 20000, 미란다·퀀시: 이스케이프
퀸·리틀 머메이드·치사토는 25000. 무기 클래스에서 유도할 수 있는 값이
아니라는 뜻이고, 이것이 `accuracy.WEAPON_SPREAD_DIAMETER`(클래스 내 분산 0)와
갈리는 지점이다.

**인코딩 슬러그 기준 영향은 5개다:**

| 슬러그 | raw 이름 | rid |
|--------|----------|-----|
| `miranda` | Miranda | 32 |
| `miranda-signature` | Miranda | 32 |
| `quency-escape-queen` | Quency: Escape Queen | 403 |
| `little-mermaid` | Little Mermaid | 513 |
| `chisato-nishikigi` | Chisato | 860 |

갭 문서가 적은 「4」는 `miranda-signature`가 빠진 수다. 애장품 빌드는
`load_weapon_data`가 base 유닛의 무기 파일을 읽으므로 같은 무기이고, 따라서
같은 배율이다. 문서도 5로 고친다.

**커버리지는 완전하다.** 인코딩 101슬러그 전부가 raw 번들에 대응된다(94개는
영문 이름이 그대로 일치, 콜라보 7개는 raw 쪽 이름이 짧다 — `Chisato` /
`Rei` / `Ada` / `Jill` / `Takina` / `Asuka: WILLE` / `Rei (Tentative Name)`).
그 7개 중 25000은 치사토 하나뿐이다. 오늘 로스터에 대해 위 표는 빠진 유닛이
없다.

## 2. 표가 코드에 있는 이유 — 데이터 경로는 막혀 있다

원칙적으로는 이 값이 수집 데이터를 타고 `weapon_stats`로 흘러야 한다. 막힌다:

- `data/dotgg/char_*.json`에 `core_damage_rate` 필드가 **없다**. dotgg는
  `weapon / maxAmmo / damage / reloadTime / chargeTime / chargeDamage`만 담는다.
- 인코딩 101슬러그 중 **83개가 무기를 dotgg에서 읽는다**(shiftypad는 18개).
  `load_weapon_data`는 `weapon_source`가 shiftypad가 아니면 전부 dotgg로
  보내므로, 소스가 lootandwaifus인 58슬러그도 무기는 dotgg에서 온다. **영향
  5슬러그는 전부 그 dotgg 쪽이다** — 이 경로로는 하나도 닿지 않는다.
- raw는 **rid로 키가 잡혀 있고** 슬러그 매핑은 데이터가 아니라
  `normalize_shiftypad_raw.py`에 사람이 주는 인자다. rid→슬러그 색인을
  데이터로 만들면 표 크기는 그대로(101줄)인데 유지 대상만 늘고, rid는 수집
  회차의 부산물이라 슬러그보다 잘 낡는다.

그래서 `accuracy.WEAPON_SPREAD_DIAMETER`와 같은 선택을 한다: **손으로 적은 표
+ 데이터와 대조하는 감사 스크립트.** 표만 만들고 감사를 만들지 않는 선택지는
없다 — 이 저장소에서 손으로 유지되는 목록은 이미 두 번 조용히 낡았다.

## 3. 모듈 — `backend/app/core_damage.py`

`accuracy.py`와 같은 크기·같은 역할의 작은 모듈. 새 모듈로 두는 이유는 감사
스크립트가 `raid_simulator`(무거운 import 사슬)를 끌어오지 않고 표를 읽을 수
있어야 하기 때문이다.

```python
DEFAULT_CORE_DAMAGE_RATE = 20000     # 200% = 2.0배 = major modifier에 +1.0

CORE_DAMAGE_RATE = {                 # 25000 = 250% = +1.5
    "miranda": 25000,
    "miranda-signature": 25000,
    "quency-escape-queen": 25000,
    "little-mermaid": 25000,
    "chisato-nishikigi": 25000,
}

def core_hit_bonus_for(slug):
    """이 유닛의 코어 히트가 major modifier에 더하는 값."""
    return CORE_DAMAGE_RATE.get(slug, DEFAULT_CORE_DAMAGE_RATE) / 10000 - 1
```

**보너스(1.5)가 아니라 게임의 원값(25000)을 담는다.** 감사가 데이터와 직접
비교할 수 있고, `20000 ↔ +1.0` 환산이 코드 한 곳에만 있다.

`raid_simulator.CORE_HIT_BONUS`는 이 모듈로 옮기며 사라진다. 실제 import는
`backend/tests/test_raid_simulator.py` 한 곳뿐이고, 거기서도
`core_hit_bonus_for("gunner")`로 바꾸면 테스트가 엔진과 같은 식으로 값을
읽는다.

## 4. 배선 — 한 줄

`raid_simulator.py:907`:

```python
core_hit_bonus=core_hit_bonus_for(slug) if hits_core else 0.0,
```

**적용 범위: `hits_core`가 참인 모든 인스턴스**(Fienn, 2026-08-08). 평타에만
거는 분기는 만들지 않는다. `hits_core`는
`core_hittable and core_eligible(source, damage_type)`이므로 평타와
`core_strike` 스킬딜이 함께 들어오고, 둘 다 시전자의 배율을 쓴다.

오늘은 결과가 같다 — 영향 5슬러그 중 `core_eligible` 스킬딜을 가진 유닛이
없다. 이 결정이 정하는 것은 앞으로 인코딩될 유닛이 물려받을 기본값이다.

관통 경로(`_entries`의 `instance(True)` / `instance(False, weight=share)`)는
손댈 필요가 없다. 본체 인스턴스는 `hits_core=False`로 들어와 이미 보너스를
받지 않는다.

## 5. 영향

**게이트가 둘이다.** `hits_core`는 `core_hittable`을 이미 접고 있으므로 코어가
없는 보스에서는 변화가 0이다. 코어가 있는 보스에서는 `core_diameter_px`
opt-in 여부와 **무관하게** 문다 — 그 옵션이 없으면 코어 히트율이 1.0이라
오히려 변화가 최대다.

**한 발의 크기.** 다른 major modifier가 없는 맨 인스턴스는 `1 + 1.0 = 2.0`이
`1 + 1.5 = 2.5`가 되어 정확히 1.25배다. 실전에서는 같은 가산 버킷에
풀버스트(+0.5)·유효사거리(+0.3)·크리 기대값이 함께 들어가므로 비율이
희석된다 — 예컨대 그 셋이 다 붙은 인스턴스는 `2.875 → 3.375`로 1.174배다.
**총딜 +25%가 아니다**, 그리고 실제 수치는 구현 후 측정으로 보고한다.

**실기록 캘리브레이션은 움직인다.** `little-mermaid`가 덱 2의 좌석이고
(2.087B 기록), `RECORD_BOSS`는 `core_hittable=True`에 `core_diameter_px`가
없다. 그녀의 sim 값이 오르므로 덱 2 비율과 5덱 합산 1.055x가 함께 오른다.

방향은 예측 가능하고 그 자체로는 이 변경에 대한 반증이 아니다 — 코어 히트율이
1.0으로 고정된 실기록에서 sim/record는 원래 상한이다(`scripts/raid_record.py`
docstring). 다만 **이건 상한 아티팩트가 아니라 진짜 수정**이므로, 새 숫자는
그대로 측정해서 보고하고 `docs/measurements/` 쪽 해석이 바뀌면 그것도 적는다.
「예상대로 올랐다」로 갈음하지 않는다.

## 6. 감사 스크립트 — `scripts/audit_core_damage_rate.py`

`audit_weapon_accuracy_scales.py`와 같은 형태. **테스트가 아니라 스크립트인
이유:** `data/shiftypad/`와 `data/dotgg/`는 gitignore라 워크트리·CI에서 없을 수
있고, 조건부 테스트로 만들면 데이터가 없는 곳에서 조용히 skip되어 「초록인데
아무것도 안 본」 상태가 된다.

**무엇을 하나:**

1. `data/shiftypad/raw/*.json`에서 `{영문 이름: (rid, core_damage_rate)}`를 모은다.
2. `ENCODED_SLUGS` 각각에 대해 캐릭터 데이터의 영문 이름으로 그 표를 찾는다.
   콜라보 7유닛은 raw 쪽 이름이 짧으므로 별칭 표(7줄)를 스크립트가 들고 있다.
3. 데이터의 rate와 `CORE_DAMAGE_RATE`(없으면 기본값)를 대조한다.

**어긋나면 exit 1.** 잡는 것 셋:

- 표에 없는 2.5배 유닛이 새로 온보딩됐다 (누락)
- 표에 있는데 데이터가 그 값이 아니다 (낡음)
- 이름이 안 풀리는 인코딩 슬러그가 있다 (감사 자체의 사각지대)

세 번째가 특히 중요하다 — 이름 매칭이 조용히 실패하면 감사가 아무것도 안 보고
초록을 낸다. 그래서 「못 풀었다」는 통과가 아니라 실패다.

`docs/` 및 스크립트 자체의 **언제 쓰나**: 로스터 재동기화 뒤, 새 니케 온보딩
뒤, 코어 관련 값을 만지기 전.

## 7. 테스트

`data/`가 gitignore라 전수 대조는 테스트가 될 수 없다. 추적되는
`backend/tests/fixtures/shiftypad/`로 두 방향을 박는다.

1. **표가 수집 데이터와 맞는다 (양·음 양쪽)** —
   `fixtures/shiftypad/miranda.json`의 `core_damage_rate`가 25000이고
   `CORE_DAMAGE_RATE["miranda"]`와 같다. `julia.json`은 20000이고 `julia`는
   표에 없다(= 기본값). 픽스처 하나만 보면 「표에 있으면 맞다」만 지켜지고
   「없으면 기본값이 맞다」는 안 지켜진다.
2. **환산** — `core_hit_bonus_for("miranda") == 1.5`,
   `core_hit_bonus_for("julia") == 1.0`, 모르는 슬러그도 1.0.
3. **엔진이 실제로 그 값을 쓴다** — 같은 덱·같은 보스에서 미란다의 코어 히트
   인스턴스가 기본값 유닛의 1.25배다. **비율이 아니라 값으로 박는다**:
   ATK 10000 × 발당 100%에 다른 major modifier가 없으면 한 발은
   `10000 x 2.5`이고, 「1.25배」라고만 적으면 두 상수가 함께 움직여도 테스트가
   계속 통과한다 (`test_core_hit_rate.py`의 관례).
4. **관통 본체 히트는 안 움직인다** — 2.5배 유닛이 관통을 가지면 코어
   인스턴스만 2.5배가 되고 본체 인스턴스는 그대로다.

기존 테스트 중 `CORE_HIT_BONUS`를 산술에 쓰는 것은 합성 슬러그(`gunner` 등)를
쓰므로 기본값 경로에 남는다 — 값은 불변이고 import만 바뀐다.

## 8. 범위 밖

- **무기변형 세그먼트의 자체 `core_damage_rate`.** 세그먼트가 다른 무기를
  자칭할 때 그 무기의 코어 배율을 따로 가질 수 있다. 영향 5슬러그 중 변형
  유닛이 없어 오늘은 물지 않는다. 배선이 필요하면 `ShotRecord` 쪽에 붙는다.
- **MG 정확도 예열**(`engine-gaps.md`) — 별개 갭, 손대지 않는다.
- **`other_core_damage_sources`** — 스킬이 주는 코어 대미지 증가 버프는 이미
  유닛별이고 지금도 맞게 돈다.

## 9. 문서 갱신

- `docs/engine-gaps.md` — 이 갭을 **해소**로 옮기고, 4 → 5(`miranda-signature`)로
  고친다. 요약 표의 해당 행도 같이.
- `docs/decisions.md` — 「수집 데이터가 있는데도 표를 코드에 두는 판단」과 그
  근거(dotgg에 필드 없음 / 88 슬러그가 dotgg), 그리고 적용 범위를 평타로
  좁히지 않은 결정.
- `docs/insights.md` — 「같은 무기 클래스 안에서 갈리는 스탯이 있다」와
  「애장품 빌드는 base의 무기 파일을 읽으므로 무기 유래 상수를 같이 받는다」.
- 캘리브레이션이 움직이면 `docs/measurements/` 및 `scripts/raid_record.py`
  docstring의 관련 숫자.
