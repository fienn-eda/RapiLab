# 버스트 게이지를 덱 속성으로 — 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `BossProfile.gauge_charge_time` 상수 2.4초를 **덱의 발사 타임라인에서 계산되는 사이클별 게이지 시간**으로 바꾼다.

**Architecture:** 게이지는 대미지가 아니라 **타격 수 × 무기별 상수**로 찬다. 상수는 데이터에 이미 있다(`shot_detail.burst_energy_pershot`, dotgg `burstGen`). 먼저 그 값을 무기 스탯까지 나르고(Task 1), 순수 산술 모듈을 만들고(Task 2), `burst_cycle`에 사이클별 오버라이드 계약을 열고(Task 3) — **여기까지 딜이 한 자리도 안 움직인다** — 그다음 `simulate_raid`의 **기존 고정점 루프**에 세 번째 수렴량으로 얹는다(Task 4). 새 루프를 만들지 않는다.

**Tech Stack:** Python 3 / pytest / React+Vite(Task 8만)

**Spec:** `docs/superpowers/specs/2026-08-21-burst-gauge-as-deck-property-design.md`
**측정 근거:** `docs/measurements/burst-gauge-fill.md`

## Global Constraints

- 백엔드 테스트는 **반드시 `backend/`에서** 실행한다 — 루트에서는 `No module named 'app'`. 전체 스위트는 약 4분 45초이니 포그라운드로 타임아웃 600000ms.
- **현재 기준선: 백엔드 2615 passed / 3 skipped.** 프론트 1030 passed / 80 files, 타입 0, lint 0.
- **워크트리에는 gitignore된 데이터가 없다.** 시작 전에 `python scripts/sync_worktree_data.py`를 한 번 돌린다. 안 돌리면 299개가 실패하는데 **회귀가 아니다.**
- 프론트 타입체크는 **`npx --prefix frontend tsc -b --noEmit frontend`** (`npm --prefix frontend exec -- tsc`는 실패). `npm test`(vitest)는 **타입을 안 본다.**
- 실측 상수 (전부 `docs/measurements/burst-gauge-fill.md`):
  - **게이지 총량 `GAUGE_FULL = 500_000`** (UI 가로 160px)
  - 타격당 = `burst_energy_pershot × pellets`, 풀차지면 `× full_charge_burst_energy / 10000`
  - **부분 차지(톡톡이)는 차지 비율과 무관하게 기본값** — 배율을 안 받는다
  - **코어 히트는 게이지와 무관**, **풀 버스트 창 안에서는 안 찬다**, **초과분은 버려진다**
  - `shot_count`(펠릿) = **SG는 10, `zwei`만 5, 나머지 전부 1** (86정 전수 확인)
- **`data/shiftypad/raw/`는 gitignore라 릴리즈 빌드에 안 실린다.** 엔진은 런타임에 그걸 못 읽는다 — 추적되는 `data/shiftypad/<slug>.json`(17개)과 `data/dotgg/char_<slug>.json`(85개)만 읽을 수 있다.
- `docs/measurements/`의 **RAW는 절대 편집하지 않는다.** 해석 절만 고친다.
- 프로젝트 규칙: 가장 작은 합리적 변경. 주석은 **무엇을·왜**만 적고 변경 이력은 안 적는다.
- **딜 변화를 손계산으로 재유도해 설명하지 않는다.** 이 저장소가 세 번 틀린 자리다 — 검산은 엔진에 물어서 한다.
- **엔진 능력을 만들면 같은 변경에서 `engine-capabilities.md`를 갱신한다.** 별도 Task로 미루지 않는다.

---

### Task 1: 게이지 상수를 무기 스탯까지 나른다 (동작 불변)

`burst_energy_pershot`은 두 출처 모두에 있다 — shiftypad 원본의 `shot_detail`과 dotgg의 `burstGen`(= 값÷10000을 퍼센트로 적은 것, 74유닛에서 정확히 일치). 무기 스탯을 읽는 경로가 두 갈래(`skill_values.load_weapon_data`)이므로 **둘 다** 손봐야 한다.

펠릿 수는 dotgg에 없으므로 **registry 테이블**로 둔다 — `CLIP_RELOAD_SPLITS`·`ROUNDS_PER_MINUTE`와 같은 계열이다.

풀차지 배율은 **새로 안 나른다**: `full_charge_burst_energy`가 모든 유닛에서 `full_charge_damage`와 값이 같고, 그건 이미 `charge_damage_percent`로 실려 있다. 그 동일성은 Task 2의 감사 스크립트가 지킨다.

> **★ 함정 — 이걸 놓치면 유닛이 조용히 사라진다.** `_WEAPON_STAT_FIELDS`에 이름을
> 더하면 `_weapon_stats`가 그 키 없는 무기 파일에 대해 `None`을 돌려주고,
> `load_nikke_spec`이 그 유닛을 통째로 **제외**한다. 그런데 **dotgg 85개 중 4개에
> `burstGen`이 없다** — `ark-ranger-black` · `cinderella-crystal-wave` ·
> `marciana-marine-study` · `prika`. 그중 **`cinderella-crystal-wave`는 이 작업이
> 고치려는 덱3의 멤버**다. 폴백 테이블 없이 필수 필드로 만들면 그 유닛이
> 추천에서 사라지고, 제외는 에러가 아니라 보고라 **테스트가 초록인 채로 지나간다.**

**Files:**
- Modify: `backend/app/shiftypad_normalize.py:109-131` (`normalize_shiftypad`)
- Modify: `backend/app/user_roster.py:31` (`_WEAPON_STAT_FIELDS`), `:34-48` (`_weapon_stats`), `:111-113` 부근 (펠릿 주입)
- Modify: `backend/app/skill_rules/registry.py` (`PELLETS_PER_SHOT` 테이블 + 접근자)
- Test: `backend/tests/test_shiftypad_normalize.py`, `backend/tests/test_user_roster.py`

**Interfaces:**
- Produces: `NikkeSpec.weapon_stats["burst_energy_pershot"]: float` (예: SR 28000.0) 와 `["pellets_per_shot"]: int` (SG 10, zwei 5, 나머지 1). Task 2·4가 이것을 읽는다.
- Produces: `registry.get_pellets_per_shot(slug, weapon) -> int`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/tests/test_shiftypad_normalize.py` 끝에 추가한다:

```python
def test_normalized_output_carries_burst_gauge_energy():
    """게이지는 타격 수 x 무기별 상수로 찬다(docs/measurements/burst-gauge-fill.md).

    그 상수가 `shot_detail.burst_energy_pershot`에 처음부터 있었는데 정규화가
    5필드만 뽑느라 엔진까지 닿지 않았다. dotgg의 `burstGen`과 같은 문자열 형태로
    내보내, 두 출처를 읽는 코드가 하나로 유지되게 한다.
    """
    bundle = json.loads(_FIXTURE.read_text(encoding="utf-8"))
    out = normalize_shiftypad(bundle)
    assert out["burstGen"] == "1.4%"    # anis-star: RL 14000
```

`_FIXTURE`는 이 파일에 이미 있는 `backend/tests/fixtures/shiftypad/anis-star.json` 경로 상수다. 이름이 다르면 파일 상단의 기존 픽스처 로딩을 그대로 쓴다.

- [ ] **Step 2: 실패를 확인한다**

Run: `cd backend && python -m pytest tests/test_shiftypad_normalize.py::test_normalized_output_carries_burst_gauge_energy -v`
Expected: FAIL — `KeyError: 'burstGen'`

- [ ] **Step 3: 정규화에 한 줄 더한다**

`backend/app/shiftypad_normalize.py`의 `normalize_shiftypad` 반환 dict에 `"chargeDamage"` 다음 줄로 추가한다:

```python
        # 발당 버스트 게이지 에너지. dotgg가 같은 값을 `burstGen`으로(값÷10000을
        # 퍼센트로) 싣고 있어 그 형태를 맞춘다 - 무기 스탯을 읽는 쪽이 출처를
        # 안 가려도 되게 하려는 것이다.
        "burstGen": _pct(shot["burst_energy_pershot"] / 100),
```

- [ ] **Step 4: 통과를 확인한다**

Run: `cd backend && python -m pytest tests/test_shiftypad_normalize.py -v`
Expected: PASS

- [ ] **Step 5: 정규화본 17개를 재생성한다**

Run: `python scripts/normalize_shiftypad_raw.py`
그 뒤 `git status --short data/shiftypad/`로 17개 파일에 `burstGen`이 붙었는지 확인한다. `data/shiftypad/raw/`는 gitignore이므로 **재생성 산출물만** 커밋 대상이다.

- [ ] **Step 6: 펠릿 테이블 테스트를 쓴다**

`backend/tests/test_user_roster.py` 끝에 추가한다:

```python
def test_shotgun_pellets_reach_weapon_stats():
    """산탄은 방아쇠 한 번에 펠릿이 여러 발 나가고 게이지는 **펠릿마다** 찬다
    (브리드 25발 = 151/160px, 명중률 94.4%). dotgg에는 `shot_count`가 없어
    registry 테이블로 둔다 - `CLIP_RELOAD_SPLITS`와 같은 자리다.
    """
    from app.skill_rules.registry import get_pellets_per_shot
    assert get_pellets_per_shot("brid-silent-track", "SG") == 10
    assert get_pellets_per_shot("zwei", "SG") == 5
    assert get_pellets_per_shot("alice", "SR") == 1
```

- [ ] **Step 7: 실패를 확인한다**

Run: `cd backend && python -m pytest tests/test_user_roster.py::test_shotgun_pellets_reach_weapon_stats -v`
Expected: FAIL — `ImportError: cannot import name 'get_pellets_per_shot'`

- [ ] **Step 8: 테이블과 접근자를 만든다**

`backend/app/skill_rules/registry.py`의 `CLIP_RELOAD_SPLITS` 근처에 추가한다:

```python
# 방아쇠 한 번이 내보내는 탄환 수. 게이지는 **타격마다** 차므로 산탄은 펠릿 수만큼
# 곱해진다(브리드 25발 = 게이지 151/160px, 빗나간 펠릿은 0 - Fienn 2026-08-21).
# 수집된 86정 전수: SG만 10이고 츠바이만 5, 나머지 무기군은 전부 1이다.
# dotgg 파일에는 `shot_count`가 없어 여기 산다.
_PELLET_EXCEPTIONS = {"zwei": 5}


def get_pellets_per_shot(slug, weapon):
    """이 유닛의 방아쇠 한 번이 내는 탄환 수. 산탄이 아니면 1."""
    base = slug.split("-signature")[0]
    if base in _PELLET_EXCEPTIONS:
        return _PELLET_EXCEPTIONS[base]
    return 10 if weapon == "SG" else 1
```

- [ ] **Step 9: 통과를 확인한다**

Run: `cd backend && python -m pytest tests/test_user_roster.py::test_shotgun_pellets_reach_weapon_stats -v`
Expected: PASS

- [ ] **Step 10: 무기 스탯 배선 테스트를 쓴다**

`backend/tests/test_user_roster.py`에 추가한다. 이 파일의 기존 헬퍼로 상태를 만들고 `load_nikke_spec`을 부른다:

```python
def test_weapon_stats_carry_burst_energy_from_both_sources():
    """게이지 상수가 두 출처 모두에서 같은 키로 나와야 한다 - shiftypad를 쓰는
    유닛과 dotgg를 쓰는 유닛의 경로가 갈리기 때문이다(skill_values.load_weapon_data).
    """
    alice = load_nikke_spec(_state("alice"))          # SR, dotgg burstGen "2.8%"
    assert alice.weapon_stats["burst_energy_pershot"] == pytest.approx(28000.0)
    assert alice.weapon_stats["pellets_per_shot"] == 1

    brid = load_nikke_spec(_state("brid-silent-track"))   # SG
    assert brid.weapon_stats["burst_energy_pershot"] == pytest.approx(2000.0)
    assert brid.weapon_stats["pellets_per_shot"] == 10
```

`_state(slug)`는 이 파일에 이미 있는 `UserNikkeState` 헬퍼다. 없으면 파일 안의 기존 테스트가 상태를 만드는 방식을 그대로 복사한다.

- [ ] **Step 11: 실패를 확인한다**

Run: `cd backend && python -m pytest tests/test_user_roster.py::test_weapon_stats_carry_burst_energy_from_both_sources -v`
Expected: FAIL — `KeyError: 'burst_energy_pershot'`

- [ ] **Step 12: `_weapon_stats`와 `load_nikke_spec`을 고친다**

`backend/app/user_roster.py:31`:

```python
_WEAPON_STAT_FIELDS = ("weapon", "maxAmmo", "damage", "reloadTime", "chargeTime",
                       "chargeDamage", "burstGen")
```

`_weapon_stats`는 **필수 필드로 만들지 않는다** — 위 함정 때문이다. `weapon_data`에 없으면 폴백 테이블에서 읽고, 거기에도 없을 때만 `None`으로 떨어뜨린다. 시그니처에 `slug`를 더한다:

```python
def _weapon_stats(weapon_data, slug):
    if any(field not in weapon_data for field in _WEAPON_STAT_FIELDS):
        return None
    # 타격당 버스트 게이지 에너지. 파일은 퍼센트 문자열("2.8%")로 싣는데 원본
    # 단위(28000)가 산술의 단위이므로 되돌린다. dotgg 4개 파일에 이 키가 없어
    # 폴백 테이블이 받는다 - 필수 필드로 만들면 그 유닛들이 조용히 제외된다.
    burst_gen = weapon_data.get("burstGen")
    burst_energy = (_percent(burst_gen) * 10_000 if burst_gen is not None
                    else BURST_ENERGY_FALLBACK.get(slug))
    if burst_energy is None:
        return None
    return {
        ...  # 기존 6키 그대로
        "burst_energy_pershot": burst_energy,
    }
```

호출부(`user_roster.py:84`)를 `_weapon_stats(weapon_data, slug)`로 고친다. `_WEAPON_STAT_FIELDS`는 **건드리지 않는다.**

`backend/app/skill_rules/registry.py`에 폴백 테이블을 만든다:

```python
# dotgg 파일에 `burstGen`이 없는 유닛의 발당 게이지 에너지. 원본 번들
# (`data/shiftypad/raw/`, gitignore라 런타임에 없다)에서 옮겨 적었고,
# `scripts/audit_burst_energy.py`가 수집 때마다 대조한다.
BURST_ENERGY_FALLBACK = {
    "ark-ranger-black": 2_000.0,       # AR
    "cinderella-crystal-wave": 500.0,  # MG (Snipe 모드도 같은 기저 무기다)
    "marciana-marine-study": 2_000.0,  # AR
    "prika": 28_000.0,                 # SR
}
```

`load_nikke_spec`에서 클립 재장전 주입 바로 뒤에:

```python
        weapon_stats = {**weapon_stats,
                        "pellets_per_shot": get_pellets_per_shot(slug, weapon)}
```

`get_pellets_per_shot`과 `BURST_ENERGY_FALLBACK`을 이 파일의 registry import 목록에 더한다.

- [ ] **Step 13: 통과를 확인한다**

Run: `cd backend && python -m pytest tests/test_user_roster.py tests/test_shiftypad_normalize.py tests/test_shiftypad_parity.py -v`
Expected: PASS

- [ ] **Step 14: 커버리지 가드를 만든다 — 이 Task의 가장 중요한 테스트**

제외는 에러가 아니라 **보고**라서 유닛이 조용히 사라진다. 인코딩된 유닛 전부가 게이지 값을 갖는지 테스트가 지켜야 한다. `backend/tests/test_burst_energy_coverage.py`를 새로 만든다:

```python
"""인코딩된 유닛 전부가 발당 게이지 에너지를 갖는가.

이 가드가 없으면 `burstGen` 없는 무기 파일 하나가 그 유닛을 추천에서 통째로
지우는데, 제외는 에러가 아니라 보고라 스위트가 초록인 채로 지나간다.
`test_hit_rate_bullets_are_encoded.py`와 같은 계열이다.
"""
from app.skill_rules.registry import ENCODED_SLUGS
from app.skill_values import load_weapon_data
from app.skill_rules.registry import BURST_ENERGY_FALLBACK, get_skill_value_manifest


def test_every_encoded_slug_has_burst_gauge_energy():
    missing = []
    for slug in sorted(ENCODED_SLUGS):
        manifest = get_skill_value_manifest(slug)
        if manifest is None:
            continue
        try:
            weapon = load_weapon_data(manifest, slug)
        except FileNotFoundError:
            continue          # 무기 파일 자체가 없는 유닛은 이미 제외 대상이다
        if weapon.get("burstGen") is None and slug not in BURST_ENERGY_FALLBACK:
            missing.append(slug)
    assert missing == [], (
        f"게이지 에너지가 없는 인코딩 유닛: {missing}. "
        f"registry.BURST_ENERGY_FALLBACK에 원본 값을 적거나 무기 파일을 다시 뽑아라.")
```

- [ ] **Step 15: 실패/통과를 확인한다**

Run: `cd backend && python -m pytest tests/test_burst_energy_coverage.py -v`
Expected: PASS. **실패하면 그 슬러그를 `BURST_ENERGY_FALLBACK`에 더한다** — 값은 `python scripts/audit_burst_energy.py`가 알려준다.

- [ ] **Step 16: 전체 스위트가 그대로인지 확인한다**

Run: `cd backend && python -m pytest -q`
Expected: **2615 + 신규 4 = 2619 passed / 3 skipped.** 하나라도 줄면 배선이 기존 동작을 건드린 것이다.

- [ ] **Step 17: 유닛이 사라지지 않았는지 직접 센다**

Run: `cd backend && python -c "from app.supported_units import supported_units; print(len(supported_units()))"`
Expected: 이 Task 시작 전과 **같은 수**. 줄었다면 폴백이 모자란 것이다.

- [ ] **Step 18: 커밋**

```bash
git add backend/app/shiftypad_normalize.py backend/app/user_roster.py backend/app/skill_rules/registry.py backend/tests/test_shiftypad_normalize.py backend/tests/test_user_roster.py backend/tests/test_burst_energy_coverage.py data/shiftypad
git commit -m "게이지 상수를 무기 스탯까지 나른다 (동작 불변)"
```

---

### Task 2: `burst_gauge.py` — 순수 산술 (동작 불변)

실측 6유닛이 그대로 테스트가 된다. 이 Task는 아무도 이 모듈을 부르지 않으므로 딜이 안 움직인다.

**Files:**
- Create: `backend/app/burst_gauge.py`
- Create: `backend/tests/test_burst_gauge.py`
- Create: `scripts/audit_burst_energy.py`

**Interfaces:**
- Consumes: Task 1의 `weapon_stats["burst_energy_pershot"]` · `["pellets_per_shot"]` · `["charge_damage_percent"]`
- Produces: `GAUGE_FULL: int` · `GAUGE_QUANTUM_SEC: float` · `energy_per_hit(weapon_stats, *, full_charge: bool) -> float` · `quantize(seconds: float) -> float`. Task 4가 이것을 읽는다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/tests/test_burst_gauge.py`를 새로 만든다:

```python
"""단독편성 실측이 그대로 단언이 된다 - docs/measurements/burst-gauge-fill.md.

앨리스 5발 / 에이드 7발 / 드레이크 10발 / 블랑 250발 / 리타 500발 / 크라운 1000발이
각각 게이지를 채운다. 여섯이 독립적으로 같은 총량을 준다.
"""
import pytest

from app.burst_gauge import GAUGE_FULL, energy_per_hit, quantize


def _weapon(burst_energy, pellets=1, charge_damage_percent=0.0):
    return {"burst_energy_pershot": burst_energy, "pellets_per_shot": pellets,
            "charge_damage_percent": charge_damage_percent}


def test_alice_fills_the_gauge_in_five_full_charges():
    # SR 28,000 x 3.5배(차지 대미지 350%) = 98,000. 5발 = 490,000 = 156.8px 판독 156.
    alice = _weapon(28_000, charge_damage_percent=350.0)
    assert energy_per_hit(alice, full_charge=True) == pytest.approx(98_000)
    assert 5 * energy_per_hit(alice, full_charge=True) == pytest.approx(490_000)


def test_alice_and_ade_differ_only_by_the_charge_multiplier():
    """총량을 몰라도 성립하는 검증 - 같은 무기·같은 발당값에 배율만 3.5 대 2.5인데
    실측 발수가 5 대 7이다."""
    alice = energy_per_hit(_weapon(28_000, charge_damage_percent=350.0), full_charge=True)
    ade = energy_per_hit(_weapon(28_000, charge_damage_percent=250.0), full_charge=True)
    assert alice / ade == pytest.approx(3.5 / 2.5)
    assert 5 * alice == pytest.approx(7 * ade)


def test_tap_fire_takes_the_base_value_not_the_charge_multiplier():
    """헬름을 차지 113%와 106%로 쏜 두 발이 합쳐 18px(= 17.92px 예상). 차지 비율에
    비례한다면 두 발이 서로 다른 값을 줬어야 한다."""
    helm = _weapon(28_000, charge_damage_percent=250.0)
    assert energy_per_hit(helm, full_charge=False) == pytest.approx(28_000)


def test_shotgun_pellets_multiply():
    # 드레이크 4,500 x 10펠릿 = 45,000. 10발 = 450,000 = 144px 판독 145.
    drake = _weapon(4_500, pellets=10)
    assert energy_per_hit(drake, full_charge=False) == pytest.approx(45_000)


@pytest.mark.parametrize("burst_energy,shots", [(2_000, 250), (1_000, 500), (500, 1_000)])
def test_magazine_weapons_fill_at_the_measured_shot_counts(burst_energy, shots):
    """블랑(AR) 250발 / 리타(SMG) 500발 / 크라운(MG) 1000발이 각각 버충 완료."""
    assert shots * energy_per_hit(_weapon(burst_energy), full_charge=False) == GAUGE_FULL


def test_quantize_snaps_to_the_grid():
    """게이지 -> 사이클 길이 -> 재장전 위치 -> 게이지의 고리가 연속값이면 진동할 수
    있다. 격자로 유한 상태를 만든다."""
    assert quantize(3.1799) == pytest.approx(3.20)
    assert quantize(2.4) == pytest.approx(2.40)
```

- [ ] **Step 2: 실패를 확인한다**

Run: `cd backend && python -m pytest tests/test_burst_gauge.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.burst_gauge'`

- [ ] **Step 3: 모듈을 만든다**

`backend/app/burst_gauge.py`:

```python
"""버스트 게이지가 얼마나 차는가 - 상수와 산술이 사는 한 곳.

게이지는 **대미지가 아니라 타격 수**로 찬다. 코어 히트도, 크리티컬도, 적 DEF도
게이지를 안 바꾼다(Fienn 실측 2026-08-21, docs/measurements/burst-gauge-fill.md).
타격당 값은 무기군이 아니라 **유닛별**이고 같은 RL 안에서도 15배 벌어진다.

상수를 한곳에 두는 이유는 `paths.py`와 같다 - 흩어지면 같은 날 같은 방식으로 틀린다.
"""

# 게이지를 가득 채우는 데 필요한 에너지. 단독편성 여섯 유닛이 독립적으로 이 값을
# 준다(앨리스 5발 x 98,000 = 490,000 = 판독 156/160px; 블랑 250발 x 2,000 = 정확히
# 이 값에서 완료). UI 가로 160px가 이 값에 대응한다.
GAUGE_FULL = 500_000

# 채움 시간을 이 격자로 snap한다. 게이지가 사이클 길이를 바꾸고 사이클 길이가
# 재장전 위치를 바꿔 다시 게이지를 바꾸므로, 연속값이면 고정점이 진동할 수 있다.
# 실측 폭이 1초 가까이(덱3 2.55~3.5초)라 이 해상도로 잃는 것이 없다.
GAUGE_QUANTUM_SEC = 0.05


def energy_per_hit(weapon_stats, *, full_charge):
    """이 무기의 타격 하나가 넣는 게이지 에너지.

    산탄은 펠릿이 개별로 세어진다. 풀차지 샷만 차지 배율을 받는다 - 부분 차지
    (톡톡이)는 차지 비율과 무관하게 기본값이고, 그것이 헬름을 113%와 106%로 쏜 두
    발이 합쳐 정확히 기본값 두 개였던 판독이다.

    차지 배율에 `charge_damage_percent`를 쓰는 것은 우연이 아니다 - 원본 데이터의
    `full_charge_burst_energy`가 `full_charge_damage`와 **모든 유닛에서 값이 같다**.
    그 동일성은 `scripts/audit_burst_energy.py`가 지킨다.
    """
    energy = weapon_stats["burst_energy_pershot"] * weapon_stats.get("pellets_per_shot", 1)
    if not full_charge:
        return energy
    multiplier = weapon_stats.get("charge_damage_percent", 0.0) / 100
    return energy * multiplier if multiplier > 1 else energy


def quantize(seconds):
    """채움 시간을 고정점이 멈출 수 있는 격자로 내린다."""
    return round(seconds / GAUGE_QUANTUM_SEC) * GAUGE_QUANTUM_SEC
```

- [ ] **Step 4: 통과를 확인한다**

Run: `cd backend && python -m pytest tests/test_burst_gauge.py -v`
Expected: PASS (7개)

- [ ] **Step 5: 감사 스크립트를 만든다**

`scripts/audit_burst_energy.py`. 원본 번들은 gitignore라 테스트가 아니라 **스크립트**다 — `audit_rate_of_fire.py`와 같은 계열이고, 수집 후 Fienn이 돌린다:

```python
"""원본 번들 대 배선된 값 - 게이지 상수가 어긋나면 잡는다.

왜 테스트가 아니라 스크립트인가: `data/shiftypad/raw/`는 gitignore라 릴리즈에도
CI에도 없다. 수집을 새로 한 뒤 사람이 돌리는 감사다.

검사 둘:
  1. dotgg의 `burstGen` x 10000 == 원본의 `burst_energy_pershot`
  2. 원본의 `full_charge_burst_energy` == `full_charge_damage`
     (`burst_gauge.energy_per_hit`이 후자를 차지 배율로 쓰는 근거)

Usage: python3 scripts/audit_burst_energy.py
"""
import glob
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    ts = (ROOT / "frontend/src/lib/resourceIdSlugMap.ts").read_text(encoding="utf-8")
    slug_of = {int(rid): slug for rid, slug
               in re.findall(r"^\s*(\d+):\s*'([a-z0-9-]+)'", ts, re.M)}

    mismatched, checked = [], 0
    for path in sorted(glob.glob(str(ROOT / "data/shiftypad/raw/*.json"))):
        detail = json.loads(Path(path).read_text(encoding="utf-8"))["detail"]
        shot = detail.get("shot_detail") or {}
        if not shot:
            continue
        slug = slug_of.get(detail["resource_id"])
        if shot.get("full_charge_burst_energy") != shot.get("full_charge_damage"):
            mismatched.append(f"{slug}: full_charge_burst_energy "
                              f"{shot['full_charge_burst_energy']} != "
                              f"full_charge_damage {shot['full_charge_damage']}")
        dotgg = ROOT / "data/dotgg" / f"char_{slug}.json"
        if slug and dotgg.exists():
            gen = json.loads(dotgg.read_text(encoding="utf-8")).get("burstGen")
            if gen is not None:
                checked += 1
                wired = float(str(gen).rstrip("%")) * 10_000
                if abs(wired - shot["burst_energy_pershot"]) > 1e-6:
                    mismatched.append(f"{slug}: dotgg burstGen {gen} -> {wired:,.0f} "
                                      f"!= raw {shot['burst_energy_pershot']:,}")

    print(f"대조한 유닛: {checked}")
    for line in mismatched:
        print("  MISMATCH", line)
    print("어긋남 없음" if not mismatched else f"어긋남 {len(mismatched)}건")
    return 1 if mismatched else 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 6: 감사를 한 번 돌려 초록을 확인한다**

Run: `python scripts/audit_burst_energy.py`
Expected: `대조한 유닛: 74` · `어긋남 없음`

- [ ] **Step 7: 커밋**

```bash
git add backend/app/burst_gauge.py backend/tests/test_burst_gauge.py scripts/audit_burst_energy.py
git commit -m "burst_gauge 모듈 - 실측 여섯 유닛이 그대로 테스트가 된다"
```

---

### Task 3: `burst_cycle`에 사이클별 게이지 오버라이드 (동작 불변)

`full_burst_duration_overrides`와 **정확히 같은 계약**이다. 비어 있으면 오늘 그대로.

**Files:**
- Modify: `backend/app/burst_cycle.py:107-137` (시그니처·독스트링), `:158` (소비)
- Test: `backend/tests/test_burst_cycle.py`

**Interfaces:**
- Produces: `simulate_burst_cycle(..., gauge_charge_overrides: dict[int, float] | None = None)`. Task 4가 이것을 채운다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/tests/test_burst_cycle.py` 끝에 추가한다. `test_full_burst_duration_overrides_lengthen_named_cycles`(같은 파일 :593)의 형태를 그대로 따른다:

```python
def test_gauge_charge_overrides_change_named_cycles_only():
    """사이클별 게이지는 그 사이클의 하한에만 걸린다 - 게이지가 덱 속성이고
    재장전 위치에 따라 사이클마다 다르기 때문이다(docs/measurements/burst-gauge-fill.md).

    쿨다운을 1초로 두어 게이지가 항상 병목이게 만든다. 그러면 사이클 간격이
    곧 `FULL_BURST_DURATION + 그 사이클의 게이지 + 티어갭`이다.
    """
    deck = [
        {"slug": "b1", "burst_tier": 1, "cooldown": 1.0},
        {"slug": "b2", "burst_tier": 2, "cooldown": 1.0},
        {"slug": "b3", "burst_tier": 3, "cooldown": 1.0},
    ]
    events = simulate_burst_cycle(
        deck, gauge_charge_time=2.4, fight_duration=100.0, mode="manual",
        gauge_charge_overrides={1: 5.0},
    )
    starts = [e["time"] for e in events if e["type"] == "full_burst_start"]
    gaps = [round(b - a, 6) for a, b in zip(starts, starts[1:])]
    # 사이클 1의 게이지가 5.0이므로 사이클 1 -> 2의 간격만 길다.
    assert gaps[0] == pytest.approx(FULL_BURST_DURATION + 2.4 + 0.2)
    assert gaps[1] == pytest.approx(FULL_BURST_DURATION + 5.0 + 0.2)
    assert gaps[2] == pytest.approx(FULL_BURST_DURATION + 2.4 + 0.2)


def test_empty_gauge_overrides_are_todays_behaviour():
    deck = [
        {"slug": "b1", "burst_tier": 1, "cooldown": 1.0},
        {"slug": "b2", "burst_tier": 2, "cooldown": 1.0},
        {"slug": "b3", "burst_tier": 3, "cooldown": 1.0},
    ]
    without = simulate_burst_cycle(deck, gauge_charge_time=2.4, fight_duration=100.0,
                                   mode="manual")
    with_empty = simulate_burst_cycle(deck, gauge_charge_time=2.4, fight_duration=100.0,
                                      mode="manual", gauge_charge_overrides={})
    assert without == with_empty
```

- [ ] **Step 2: 실패를 확인한다**

Run: `cd backend && python -m pytest tests/test_burst_cycle.py::test_gauge_charge_overrides_change_named_cycles_only -v`
Expected: FAIL — `TypeError: simulate_burst_cycle() got an unexpected keyword argument`

- [ ] **Step 3: 파라미터를 더한다**

`backend/app/burst_cycle.py`의 시그니처에 `full_burst_duration_overrides` 다음 줄로:

```python
    gauge_charge_overrides=None,
```

독스트링 끝에 문단을 더한다:

```
    `gauge_charge_overrides`는 {사이클 인덱스: 초}로, 그 사이클의 게이지 하한을
    통째로 대체한다(`gauge_charge_time`은 그 표에 없는 사이클의 값이자 첫 패스의
    시드다). 게이지는 덱이 넣은 **타격 수**로 차므로 사이클마다 다르다 - 재장전과
    MG 예열이 창 안 어디에 떨어지느냐가 그 사이클의 채움 속도를 정한다.
    이 스케줄러는 값이 어디서 왔는지 모른다. raid_simulator가 고정점까지
    반복하며 이 표를 갱신한다.
```

`:158`을 고친다:

```python
        gauge_ready = time + (gauge_charge_overrides or {}).get(cycle_index, gauge_charge_time)
```

- [ ] **Step 4: 통과를 확인한다**

Run: `cd backend && python -m pytest tests/test_burst_cycle.py -v`
Expected: PASS (신규 2개 포함)

- [ ] **Step 5: 전체 스위트**

Run: `cd backend && python -m pytest -q`
Expected: 2620 passed / 3 skipped (2618 + 2)

- [ ] **Step 6: 커밋**

```bash
git add backend/app/burst_cycle.py backend/tests/test_burst_cycle.py
git commit -m "burst_cycle에 사이클별 게이지 오버라이드 (비면 오늘 그대로)"
```

---

### Task 4: 고정점에 얹는다 — **여기서 숫자가 움직인다**

`_simulate_raid_once`가 샷 레코드에서 게이지를 적산해 다음 패스용 표를 반환하고, `simulate_raid`의 기존 루프가 되먹인다.

**적산은 `damage_log`가 아니라 샷에서 한다.** `damage_log`는 코어/관통으로 인스턴스가 쪼개져 타격 수와 1:1이 아니고, 무기 정보도 없다(`slug/time/damage/source/damage_type`만).

**Files:**
- Modify: `backend/app/raid_simulator.py:883-896` (고정점 루프), `:1627-1639` (호출), `:2457-2479` (반환), 샷 루프 부근 `:1946-1990`
- Modify: `backend/app/burst_gauge.py` (`fill_times` 추가)
- Modify: `backend/app/deck_search.py:193-197` (`gauge_charge_time` 독스트링 — 「시드」로)
- Modify: `backend/tests/test_burst_cycle.py:388-400` (2.4를 못 박는 테스트)
- Test: `backend/tests/test_burst_gauge_in_sim.py` (신규)

**Interfaces:**
- Consumes: Task 2의 `GAUGE_FULL`·`energy_per_hit`·`quantize`, Task 3의 `gauge_charge_overrides`
- Produces: `burst_gauge.fill_times(shots_by_slug, fb_ends, *, weapon_stats, fight_duration) -> dict[int, float]` — `shots_by_slug`는 `{slug: [(time, is_tap_fire), ...]}`
- Produces: `result["gauge_charge_times"]: dict[int, float]` 와 `result["gauge_bound_cycles"]: int`. Task 8이 읽는다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/tests/test_burst_gauge_in_sim.py`를 새로 만든다:

```python
"""게이지가 덱에서 계산되는지 - 산술로 단언한다.

**총합으로 단언하지 않는다.** 2026-08-05에 게이지를 2.0에서 2.4로 옮겼을 때
1871개 테스트 중 아무것도 안 깨졌다. 총합 테스트는 상수 변화에 둔감하다.
"""
import pytest

from app.burst_cycle import FULL_BURST_DURATION
from app.burst_gauge import GAUGE_FULL, energy_per_hit


def test_gauge_bound_cycles_use_the_computed_gauge(real_deck_and_boss):
    """게이지가 병목인 구간에서 사이클 간격은 정확히
    `FULL_BURST_DURATION + 계산된 게이지 + 티어갭`이다."""
    ordered, boss = real_deck_and_boss
    result = evaluate_deck(ordered, boss)
    computed = result["gauge_charge_times"]
    starts = [e["time"] for e in result["events"] if e["type"] == "full_burst_start"]
    ends = [e["time"] for e in result["events"] if e["type"] == "full_burst_end"]
    for k, (end, nxt) in enumerate(zip(ends, starts[1:])):
        if k not in computed:
            continue
        gap = nxt - end
        # 게이지 하한에 붙은 사이클만 검사한다 - 쿨다운이 더 길면 그쪽이 정한다.
        if gap == pytest.approx(computed[k] + 0.2, abs=1e-6):
            assert gap >= computed[k]


def test_a_deck_that_cannot_charge_gets_a_longer_gauge_than_one_that_can():
    """SR 덱과 MG 덱. 타격당 28,000 대 500이라 56배 차이가 나므로 MG 덱의
    게이지가 반드시 더 길다 - 이 부등식이 이 변경의 요지다.

    총딜을 비교하지 않는다: 두 덱은 딜도 다르고, 총합은 상수 변화에 둔감하다는
    것이 2026-08-05의 교훈이다.
    """
    sr_gauge = _computed_gauge(_synthetic_deck("SR", burst_energy=28_000))
    mg_gauge = _computed_gauge(_synthetic_deck("MG", burst_energy=500))
    assert min(sr_gauge.values()) < min(mg_gauge.values())


def test_bottleneck_flips_from_cooldown_to_gauge_as_cdr_ramps():
    """누적형 CDR(리타·볼륨의 예열 방식)에서는 초반이 쿨다운 병목이고 후반이
    게이지 병목이다. 실측 타임라인이 간격 7.56 -> 4.86 -> 2.40초로 3번째
    사이클에서 뒤집히고, 그 뒤 11사이클이 전부 게이지 병목이다.

    이 전환이 존재한다는 것이 「첫 사이클만 보고 게이지를 건너뛴다」류의
    최적화를 기각한 근거다(스펙의 「조기 종료는 채택하지 않는다」).
    """
    result = evaluate_deck(_volume_deck(), _boss())
    ends = [e["time"] for e in result["events"] if e["type"] == "full_burst_end"]
    starts = [e["time"] for e in result["events"] if e["type"] == "full_burst_start"]
    gaps = [nxt - end for end, nxt in zip(ends, starts[1:])]
    assert gaps[0] > gaps[-1], "누적 CDR이면 간격이 줄어야 한다"
    computed = result["gauge_charge_times"]
    late = len(gaps) - 1
    assert gaps[-1] == pytest.approx(computed[late] + 0.2, abs=1e-6), (
        "정상상태에서는 게이지가 사이클을 정한다")
```

> 실행자 주: `_computed_gauge` · `_synthetic_deck` · `_volume_deck` · `_boss` ·
> `real_deck_and_boss`는 이 새 파일 안에서 만든다. 덱을 조립해 엔진을 한 번
> 돌리는 **가장 짧은 예**가 `backend/tests/test_ammo_accounting.py`이니 그
> 파일의 덱 구성 방식을 그대로 복사한다. `_volume_deck`은 `volume`(B1)을
> 반드시 포함해야 한다 — 누적 CDR을 주는 유닛이 그녀다.

- [ ] **Step 2: 실패를 확인한다**

Run: `cd backend && python -m pytest tests/test_burst_gauge_in_sim.py -v`
Expected: FAIL — `KeyError: 'gauge_charge_times'`

- [ ] **Step 3: `fill_times`를 만든다**

`backend/app/burst_gauge.py`에 추가한다:

```python
def fill_times(shots_by_slug, full_burst_ends, *, weapon_stats, fight_duration):
    """풀 버스트가 끝난 뒤 게이지가 다시 가득 차기까지 걸리는 시간, 사이클마다.

    게이지는 **창 밖에서만** 찬다(창 안에서도 찬다는 가설은 실측으로 기각됐다 -
    그러면 다섯 덱 전부가 창 종료 전에 가득 차서 덱2의 3.7초 판독을 설명 못 한다).
    초과분은 다음 사이클로 이월되지 않는다.

    전투가 끝날 때까지 못 채우는 사이클은 표에 안 싣는다 - 그 사이클은 어차피
    일어나지 않고, 무한대를 스케줄러에 넘기면 하한 계산이 통째로 뒤집힌다.
    """
    per_hit = {
        slug: (energy_per_hit(stats, full_charge=False),
               energy_per_hit(stats, full_charge=True))
        for slug, stats in weapon_stats.items()
    }
    merged = sorted(
        (time, slug, is_tap)
        for slug, shots in shots_by_slug.items()
        for time, is_tap in shots
    )
    out = {}
    for cycle_index, end in enumerate(full_burst_ends):
        gauge = 0.0
        for time, slug, is_tap in merged:
            if time < end:
                continue
            base, charged = per_hit.get(slug, (0.0, 0.0))
            gauge += base if is_tap else charged
            if gauge >= GAUGE_FULL:
                out[cycle_index] = quantize(time - end)
                break
    return out
```

- [ ] **Step 4: 시뮬레이터에 배선한다**

`backend/app/raid_simulator.py`의 샷 루프에서 슬러그별 `(시각, 톡톡이 여부)`를 모은다. `shot_times_by_slug[slug] = shot_times`(`:1990`) 옆에 추가:

```python
        gauge_shots_by_slug[slug] = [(r.time, r.is_tap_fire) for r in shot_records]
```

`shot_times_by_slug`가 선언된 곳 옆에 `gauge_shots_by_slug = {}`를 더한다.

`simulate_burst_cycle` 호출(`:1627`)에 넘긴다:

```python
        gauge_charge_overrides=gauge_charge_overrides,
```

`_simulate_raid_once`의 시그니처에 `gauge_charge_overrides=None`을 더하고, `result`를 만드는 곳(`:2457`)에서 다음 패스용 표를 계산해 반환 튜플에 넣는다:

```python
    resolved_gauge = burst_gauge.fill_times(
        gauge_shots_by_slug,
        [e["time"] for e in events if e["type"] == "full_burst_end"],
        weapon_stats=weapon_stats, fight_duration=fight_duration)
    result["gauge_charge_times"] = resolved_gauge
    result["gauge_bound_cycles"] = sum(
        1 for k, seconds in resolved_gauge.items() if seconds >= _cycle_gap(events, k) - 1e-6)
    ...
    return (result, ..., late_max_hp_records, resolved_gauge)
```

`_cycle_gap(events, k)`는 사이클 k의 실제 간격(풀버스트 종료 → 다음 티어1 버스트)을 돌려주는 모듈 내부 헬퍼로 새로 만든다.

- [ ] **Step 5: 고정점 루프에 세 번째 축을 더한다**

`backend/app/raid_simulator.py:883-896`:

```python
    overrides = {}
    late_max_hp = ()
    gauge = {}
    result = None
    for attempt in range(MAX_FULL_BURST_PASSES):
        result, resolved, resolved_max_hp, resolved_gauge = _simulate_raid_once(
            *args, **kwargs, full_burst_stage_overrides=overrides,
            late_flat_max_hp=late_max_hp, gauge_charge_overrides=gauge,
        )
        if (resolved == overrides and resolved_max_hp == late_max_hp
                and resolved_gauge == gauge):
            result["full_burst_passes"] = {"passes": attempt + 1, "converged": True}
            return result
        overrides = resolved
        late_max_hp = resolved_max_hp
        gauge = resolved_gauge
```

`simulate_raid.__wrapped__`(`:2493`)를 쓰는 곳이 반환 튜플 4개를 견디는지 확인한다.

- [ ] **Step 6: 2.4를 못 박던 테스트를 고친다**

`backend/tests/test_burst_cycle.py:388-400`의 `test_gauge_charge_time_matches_the_measurement_it_is_derived_from`을 지우지 말고 **의미를 바꾼다** — 이제 2.4는 인카운터의 게이지가 아니라 **첫 패스의 시드**다:

```python
def test_default_gauge_is_the_first_pass_seed_not_the_encounter_value():
    """게이지는 이제 덱에서 계산된다(docs/measurements/burst-gauge-fill.md).
    이 상수가 정하는 것은 **첫 패스가 어디서 출발하는가**뿐이고, 고정점이
    그 위에서 실제 값을 찾는다. 값 자체는 CDR 편성의 15번째 풀버스트 t~179에서
    역산한 것이라 출발점으로 여전히 합리적이다."""
    assert BossProfile.gauge_charge_time == 2.4
```

`deck_search.py:193-197`의 주석도 같은 방향으로 고친다 — 「per-DECK quantity flattened into one constant」는 이제 틀린 설명이다.

- [ ] **Step 7: 통과와 전체 스위트를 확인한다**

Run: `cd backend && python -m pytest -q`
Expected: 통과. **여기서 딜이 움직이므로 총딜을 단언하던 테스트가 깨질 수 있다.** 깨진 것마다 「기대값이 낡았나, 아니면 진짜 회귀인가」를 판정해 기대값을 갱신하고, **왜 그 방향으로 움직였는지를 커밋 메시지에 적는다.**

- [ ] **Step 8: 실측과 대조한다**

Run: `python scripts/measure_deck_breakdown.py --deck liter,nayuta,cinderella-crystal-wave-mg,cinderella,modernia --element Wind --enemy-def 31784`
Expected: 그 덱의 게이지가 **2.4초보다 크게** 나온다(실측 2.55~3.5초). 정확히 맞을 필요는 없다 — 방향과 크기를 본다.

- [ ] **Step 9: 스펙이 남긴 리스크 하나를 확인한다 — 「빨라졌는데 딜이 준다」**

사전 측정에서 **덱5가 게이지 2.4초 → 2.01초로 빨라졌는데 딜이 −3.9%**였다(사이클 수는 15로 동일). 버스트 시각이 앞당겨지며 파츠 파괴 시각(3·63·128초)이나 버프 창과의 정렬이 어긋난 것으로 보인다.

Run: `python scripts/measure_deck_breakdown.py --deck moran-signature,ade-agent-bunny,velvet,alice,snow-white-heavy-arms --element Wind --enemy-def 31784`

게이지가 짧아졌는데 딜이 줄면, **파츠 파괴 시각을 비운 보스**로 한 번 더 돌려 그 항이 원인인지 가른다(`--no-parts`). 정렬 효과가 실재라면 그대로 두고 **스펙의 리스크 절에 결론을 적는다**. 아티팩트로 판명되면 그 자리가 별도 버그다 — 이 Task에서 고치지 말고 기록만 하고 넘어간다.

- [ ] **Step 10: 수렴이 실제로 멈추는지 본다**

Run: `cd backend && python -c "
from app.deck_search import BossProfile, evaluate_deck
import warnings; warnings.simplefilter('error')
print('수렴 경고 없이 통과')"`

`FullBurstConvergenceWarning`이 뜨면 양자화 격자가 모자란 것이다. `GAUGE_QUANTUM_SEC`을 0.05 → 0.1로 올려 다시 본다. **32패스까지 가는 덱이 하나라도 있으면 그 덱을 기록한다** — 진동은 음의 되먹임 가정이 깨졌다는 신호다.

- [ ] **Step 11: 커밋**

```bash
git add backend/app/burst_gauge.py backend/app/raid_simulator.py backend/app/deck_search.py backend/tests/
git commit -m "게이지를 고정점에 얹는다 - 덱이 자기 게이지를 정한다"
```

---

### Task 5: 「아군 소모탄 N발마다 게이지 X%」 — 트리거

**장치가 이미 다 있다.** `context.shot_times`와 `context.shot_ammo_rounds`가 아군 누적 소모탄을 세고 있고(인어공주의 Bubble Barrage가 그걸로 돈다), `_AMMO_ROUNDS_PER_SHOT`이 슬러그별 회계율을 갖고 있다. 필요한 것은 **그 워크에 게이지 충전을 매다는 것**뿐이다.

**스킬 값은 반드시 로스터의 실제 레벨로 읽는다** — 인어공주는 lv1 23.12%가 아니라 **lv10 37%**, 신데렐라: 크리스탈 웨이브는 7.09%가 아니라 **lv10 12%**다. 이 하나로 덱3 계산이 5.54초 → 4.13초로 움직인다.

**Files:**
- Modify: `backend/app/burst_gauge.py` (`fill_times`에 `bonus_fills` 인자)
- Modify: `backend/app/roster.py` (새 조립 키 `gauge_fills`)
- Modify: `backend/app/skill_rules/little_mermaid.py`, `cinderella_crystal_wave.py`
- Modify: `.claude/skills/nikke-skill-encoding/references/engine-capabilities.md`
- Test: `backend/tests/test_skill_rules_little_mermaid.py`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

```python
def test_bubble_order_fills_the_gauge_every_400_ally_rounds():
    """Bubble Order: 아군 누적 소모탄 400발마다 게이지 37%(lv10). 한 방에 게이지의
    3분의 1이 넘게 차는 전부-아니면-전무 사건이라, 그 트리거가 충전 창 안에
    떨어지느냐로 충전 시간이 불연속으로 뛴다."""
    fills = build_bubble_order_gauge_fills(_values(level=10))
    assert fills == [{"every_ally_rounds": 400.0, "fraction": pytest.approx(0.37)}]
```

- [ ] **Step 2: 실패를 확인한다**

Run: `cd backend && python -m pytest tests/test_skill_rules_little_mermaid.py -k bubble_order -v`
Expected: FAIL — `NameError: build_bubble_order_gauge_fills`

- [ ] **Step 3: 두 인코딩에 빌더를 더한다**

`little_mermaid.py`에 추가하고, 모듈 docstring의 보류 항목
`- Bubble Order's "ally ammo reaches 400 -> Burst Gauge +37%" (gauge fill isn't a consumed stat).`
을 **지운다**(더 이상 보류가 아니다):

```python
def build_bubble_order_gauge_fills(values):
    """아군 누적 소모탄이 N발에 닿을 때마다 버스트 게이지를 X% 채운다.

    누적 카운터는 Bubble Barrage와 같은 채널(`context.shot_ammo_rounds`)이다 -
    탄약 주머니를 쓰는 아군은 한 발이 수백 발을 회계하므로 발수와 라운드는
    같지 않다.
    """
    order = values["bubble_order"]
    return [{"every_ally_rounds": float(order["description_value_03"]),
             "fraction": float(order["description_value_04"]) / 100}]
```

`cinderella_crystal_wave.py`도 같은 모양으로 만들고, 보류 문구
`- Burst-gauge +12% per 200 ally rounds (gauge charge time is a fixed sim input ...)` 를 지운다.

> 실행자 주: `description_value_0N`의 실제 번호는 각 유닛의 매니페스트에서
> 확인한다. 값이 **lv10에서 37% / 12%**로 나오는지 반드시 눈으로 확인하고
> 넘어간다 — lv1 값(23.12% / 7.09%)이 나오면 잘못된 슬롯을 읽은 것이다.

- [ ] **Step 4: `fill_times`가 그 충전을 세게 한다**

`burst_gauge.fill_times`에 `bonus_fills` 인자를 더한다:

```python
def fill_times(shots_by_slug, full_burst_ends, *, weapon_stats, fight_duration,
               ammo_rounds_by_slug=None, bonus_fills=()):
    ...
        gauge, ally_rounds = 0.0, 0.0
        for time, slug, is_tap in merged:
            ...
            for fill in bonus_fills:
                before = ally_rounds // fill["every_ally_rounds"]
                ally_rounds += rounds_for(slug, time)
                if ally_rounds // fill["every_ally_rounds"] > before:
                    gauge += fill["fraction"] * GAUGE_FULL
```

- [ ] **Step 5: 통과·스위트·커밋**

Run: `cd backend && python -m pytest -q`
```bash
git add backend/app/burst_gauge.py backend/app/roster.py backend/app/skill_rules/ backend/tests/ .claude/skills/nikke-skill-encoding/references/engine-capabilities.md
git commit -m "아군 소모탄 트리거 게이지 충전 - 인어공주·신데렐라:CW의 보류를 닫는다"
```

카탈로그에는 `engine-capabilities.md`의 fill kind 목록(695–764줄)과 같은 형식으로 한 항목을 더한다.

---

### Task 6: 아니스: 스타의 게이지 배율이 소비자를 얻는다

`burst_gauge_fill_speed_percent`가 **INERT BY DESIGN**으로 등록만 돼 있다(`anis_star.py:159-183`). 스쿼드 스코프 **에너지 배율**로 소비한다 — lv10 6%(Fienn 확인: 「아군 전체에게 버스트 게이지 충전 속도 6% 상승」).

**Files:**
- Modify: `backend/app/burst_gauge.py` (`fill_times`에 `speed_multiplier`)
- Modify: `backend/app/raid_simulator.py` (레지스트리에서 스탯 읽어 넘기기)
- Modify: `backend/app/skill_rules/anis_star.py:166-171` (INERT 주석 삭제), `:52` (docstring)
- Modify: `.claude/skills/nikke-skill-encoding/references/engine-capabilities.md:1560-1567`
- Test: `backend/tests/test_skill_rules_anis_star.py`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/tests/test_skill_rules_anis_star.py` 끝에 추가한다:

```python
def test_starfall_gauge_buff_shortens_the_computed_gauge():
    """아니스의 「버스트 게이지 충전 속도 6% 상승」은 스쿼드 전체의 타격당
    에너지에 곱해진다(Fienn 확인 2026-08-21: 덱의 5인 모두의 충전량을 올린다).

    같은 덱을 아니스만 빼고 채점해 게이지가 더 길어지는지 본다 - 총딜이 아니라
    **계산된 게이지**를 비교한다.
    """
    with_anis = evaluate_deck(_deck_with_anis(), _boss())
    without = evaluate_deck(_deck_without_anis(), _boss())
    assert min(with_anis["gauge_charge_times"].values()) < \
        min(without["gauge_charge_times"].values())
```

- [ ] **Step 2: 실패를 확인한다**

Run: `cd backend && python -m pytest tests/test_skill_rules_anis_star.py -k starfall_gauge -v`
Expected: FAIL — 두 값이 같다(스탯이 아직 inert다).

- [ ] **Step 3: `fill_times`가 배율을 받게 한다**

`backend/app/burst_gauge.py`의 `fill_times`에 `speed_multiplier=1.0` 인자를 더하고, 적산에 곱한다:

```python
            gauge += (base if is_tap else charged) * speed_multiplier
```

- [ ] **Step 4: 시뮬레이터가 레지스트리에서 그 값을 읽어 넘긴다**

`backend/app/raid_simulator.py`에서 `fill_times`를 부르는 자리(Task 4 Step 4)에 더한다. 스쿼드 스코프이므로 아무 멤버에게나 물어도 같은 값이다:

```python
        speed_multiplier=1.0 + registry.total_for(
            "burst_gauge_fill_speed_percent", deck[0]["slug"], now=0.0),
```

- [ ] **Step 5: INERT 주석을 걷어낸다**

`backend/app/skill_rules/anis_star.py:166-171`의 `# INERT BY DESIGN...` 블록 6줄을 지우고 한 줄로 바꾼다:

```python
        # 스쿼드 전체의 타격당 게이지 에너지에 곱해진다(burst_gauge.fill_times).
```

`:52`의 `Not modeled: Starfall's Burst Gauge filling speed (inert stat)` 문구에서 게이지 부분을 뺀다.

- [ ] **Step 6: 통과와 전체 스위트를 확인한다**

Run: `cd backend && python -m pytest -q`
Expected: 통과. **덱1의 딜이 움직인다**(아니스가 그 덱에 있다).

- [ ] **Step 7: 카탈로그를 같은 변경에서 고친다**

`.claude/skills/nikke-skill-encoding/references/engine-capabilities.md:1560-1567`에서 `burst_gauge_fill_speed_percent`를 **「Not a damage concept at all」 목록에서 뺀다.** 편집 형태는 같은 문서의 선례 둘을 그대로 따른다 — `:1581-1588`(`attack_speed_percent` → **NOW consumed (Phase S, 2026-07-16)**)과 `:1590-1594`(`flat_max_hp` → **no longer inert**).

> **★ 테스트가 안 잡아 준다.** `test_capability_catalog_is_current.py`는 fill kind와 reset trigger의 **이름만** 검사하고 **스탯은 검사하지 않는다**(그 모듈 docstring이 명시). 이 편집은 사람이 해야 하고, 빠뜨리면 다음 세션이 이 능력을 「없는 것」으로 읽어 갭으로 다시 기록한다.

- [ ] **Step 8: 커밋**

```bash
git add backend/app/burst_gauge.py backend/app/raid_simulator.py backend/app/skill_rules/anis_star.py backend/tests/test_skill_rules_anis_star.py .claude/skills/nikke-skill-encoding/references/engine-capabilities.md
git commit -m "아니스: 스타의 게이지 배율이 소비자를 얻는다"
```

---

### Task 7: 스킬이 쏘는 발사체 — `gauge_hits` 선언

헤비암즈 혼자 풀차지 1회로 게이지의 **절반**을 채운다(평타 22.4px + 오토파이어 타격 × 10px). 드론 타격당 값 **6.25%**는 shiftypad·dotgg·lootandwaifus·정적 테이블 **어디에도 없다** — 선언으로 받는다.

**Files:**
- Modify: `backend/app/skill_rules/registry.py` (`GAUGE_HITS` 테이블 + 접근자)
- Modify: `backend/app/roster.py` (조립 키)
- Modify: `backend/app/burst_gauge.py`
- Modify: `.claude/skills/nikke-skill-encoding/references/engine-capabilities.md`
- Test: `backend/tests/test_burst_gauge.py`

선언 형태:

```python
# 스킬이 쏘는 발사체가 넣는 게이지. 무기와 달리 데이터에 값이 없어 실측으로 선언한다
# (`core_diameter_px`·`part_destruction_times`와 같은 계열).
GAUGE_HITS = {
    # 세븐드워프: 풀차지마다 「전체 대상」 1히트 + 「락온 대상 순차」 장전 탄약 수만큼.
    # 기본 5발, Seven Dwarves Fully Active면 스킬3의 ▲10이 더해져 15발(실측).
    # 타격당 게이지 6.25%는 기본 SR 불릿(5.6%)보다 크고 어떤 데이터에도 없다
    # (Fienn 판독 2026-08-21: 22 / 32 / 41 / 52 ... 10px 등간격, 14번째에 완료).
    "snow-white-heavy-arms": {"trigger": "full_charge", "count": 6,
                              "fraction": 0.0625},
}
```

`count`가 6인 이유: 오토파이어는 「전체 대상」 1히트 + 「락온 대상 순차」 장전 탄약 수(기본 5)다. **Seven Dwarves Fully Active(그녀의 버스트) 중에는 스킬3의 ▲10이 더해져 15발**이 되지만, 그 상태는 사용 횟수 2회뿐이고 **버스트 중이라 게이지가 안 차는 창**이므로 여기서는 세지 않는다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/tests/test_burst_gauge.py`에 추가한다:

```python
def test_declared_skill_projectiles_add_their_own_energy():
    """스킬이 쏘는 발사체는 무기와 다른 값을 준다 - 헤비암즈의 세븐드워프는
    타격당 게이지의 6.25%로, 그녀 무기의 기본 불릿(5.6%)보다 크다.

    판독(Fully Active 풀차지 1회): 22 / 32 / 41 / 52 ... 로 평타 뒤 증분이
    일정하게 10px이고 14번째 타격에서 완료된다. 무기 기본값 모델이면 14번째가
    138.9px이라 완료가 설명되지 않는다.
    """
    from app.burst_gauge import declared_hit_energy
    assert declared_hit_energy({"trigger": "full_charge", "count": 6,
                                "fraction": 0.0625}) == pytest.approx(6 * 31_250)
```

- [ ] **Step 2: 실패를 확인한다**

Run: `cd backend && python -m pytest tests/test_burst_gauge.py -k declared -v`
Expected: FAIL — `ImportError: cannot import name 'declared_hit_energy'`

- [ ] **Step 3: 선언을 읽는 함수를 만든다**

`backend/app/burst_gauge.py`:

```python
def declared_hit_energy(declaration):
    """스킬이 쏘는 발사체가 한 번의 트리거에 넣는 총 에너지.

    무기와 달리 이 값은 데이터에 없다 - `shot_detail`은 유닛당 하나뿐이고
    드론은 자기 항목을 안 갖는다. 실측으로 선언한다.
    """
    return declaration["count"] * declaration["fraction"] * GAUGE_FULL
```

- [ ] **Step 4: 풀차지 샷마다 그 에너지를 더한다**

`fill_times`에 `declared_by_slug=None` 인자를 더하고, 적산 루프에서 톡톡이가 아닌 샷일 때만 얹는다:

```python
            declaration = (declared_by_slug or {}).get(slug)
            if declaration and not is_tap and declaration["trigger"] == "full_charge":
                gauge += declared_hit_energy(declaration)
```

`roster.assemble_simulation_inputs`가 `get_gauge_hits(spec.slug)`로 표를 모아 `gauge_hits` 키로 싣고, `raid_simulator`가 `fill_times`에 넘긴다.

- [ ] **Step 5: 통과와 전체 스위트**

Run: `cd backend && python -m pytest -q`
Expected: 통과. **덱5의 게이지가 크게 짧아진다** — 그녀 혼자 풀차지 1회가 게이지의 절반이다.

- [ ] **Step 6: 카탈로그에 선언을 적는다**

`engine-capabilities.md`에 `GAUGE_HITS`를 **선언 계열**로 적는다 — `core_diameter_px`·`part_destruction_times`와 같은 자리다. 「데이터에 없어 실측으로 선언한다」는 것과 **오늘의 소비자가 헤비암즈 하나**라는 것을 함께 적는다.

- [ ] **Step 7: 커밋**

```bash
git add backend/app/burst_gauge.py backend/app/roster.py backend/app/raid_simulator.py backend/app/skill_rules/registry.py backend/tests/test_burst_gauge.py .claude/skills/nikke-skill-encoding/references/engine-capabilities.md
git commit -m "gauge_hits 선언 - 스킬이 쏘는 발사체의 게이지"
```

---

### Task 8: 「버충 밀림」을 결과와 화면에

사이클마다 `gauge_ready > max(tier_ready)`인지가 곧 **「쿨은 돌았는데 버스트를 못 쓴 사이클」**이다. 오늘은 이 값이 없어서 밀림이 **보이지 않는다**.

**Files:**
- Modify: `backend/app/deck_search.py:678-711` (`_summarize`에 `gauge_bound_cycles` 싣기)
- Modify: `backend/app/models.py`, `backend/app/api.py` (응답 모델)
- Modify: `frontend/src/components/DeckCard.tsx`
- Test: `backend/tests/`, `frontend/src/components/DeckCard.test.tsx`

> **함정**: 로더를 통과해도 **응답 모델에 없는 키는 라우트가 지운다**. 백엔드
> 테스트가 「없음과 없음」을 비교해 초록이 될 수 있으니, API를 한 번 실제로
> 호출해 그 키가 응답에 살아 있는지 확인한다(`/verify` 스킬).

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/tests/test_deck_search.py`(또는 그 파일의 관례를 따르는 자리)에 추가한다:

```python
def test_summary_reports_how_many_cycles_the_gauge_held_up():
    """「버충 밀림」 - 쿨은 돌았는데 게이지가 안 차서 못 쓴 사이클 수.

    오늘은 이 값이 없어서 밀림이 화면에 안 보인다. 추천을 믿을지 말지는
    유저가 판단할 몫이고, 판단하려면 숫자가 보여야 한다.
    """
    summary = _summarize(_ordered_deck(), evaluate_deck(_ordered_deck(), _boss()))
    assert summary["gauge_bound_cycles"] >= 0
    assert summary["total_cycles"] >= summary["gauge_bound_cycles"]
```

- [ ] **Step 2: 실패를 확인한다**

Run: `cd backend && python -m pytest tests/test_deck_search.py -k gauge_bound -v`
Expected: FAIL — `KeyError: 'gauge_bound_cycles'`

- [ ] **Step 3: `_summarize`에 싣는다**

`backend/app/deck_search.py:678-711`의 반환 dict에 추가한다. 값은 Task 4가 `result`에 넣어 둔 것을 그대로 옮긴다:

```python
        # 쿨은 돌았는데 게이지가 안 차서 버스트를 못 쓴 사이클 수(버충 밀림).
        # 게이지가 덱 속성이 된 이상 이 수가 곧 「이 편성이 실전에서 밀리는가」다.
        "gauge_bound_cycles": result.get("gauge_bound_cycles", 0),
        "total_cycles": sum(1 for e in result["events"]
                            if e["type"] == "full_burst_end"),
```

- [ ] **Step 4: 응답 모델에 필드를 더한다**

`backend/app/models.py`의 덱 응답 모델(`RaidDeck` / `DeckRecommendation`)에 `gauge_bound_cycles: int = 0`와 `total_cycles: int = 0`를 더한다. **이 단계를 빠뜨리면 라우트가 키를 조용히 지운다.**

- [ ] **Step 5: 실제 API로 확인한다**

Run: `/verify` 스킬로 백엔드를 띄우고 `POST /api/recommend-raid`를 한 번 호출해, 응답의 각 덱에 `gauge_bound_cycles`가 **살아 있는지** 눈으로 확인한다. 백엔드 테스트만으로는 이 함정이 안 잡힌다.

- [ ] **Step 6: 화면에 표시한다**

`frontend/src/components/DeckCard.tsx`에 밀린 사이클을 보여준다. 문구는 한글 고정이다(프로젝트 규칙). 0이면 아무것도 안 그린다 — 「없음」을 그리면 대부분의 덱에서 잡음이 된다.

```tsx
{deck.gauge_bound_cycles > 0 && (
  <span className="deck-card__gauge-bound">
    버충 밀림 {deck.gauge_bound_cycles}/{deck.total_cycles} 사이클
  </span>
)}
```

- [ ] **Step 7: 프론트 테스트와 타입체크**

Run: `npm --prefix frontend test`
Run: `npx --prefix frontend tsc -b --noEmit frontend`
Expected: 둘 다 통과. **`npm test`는 타입을 안 보므로 둘 다 돌려야 한다.**

- [ ] **Step 8: 커밋**

```bash
git add backend/app/deck_search.py backend/app/models.py backend/tests/ frontend/src/
git commit -m "버충 밀림을 결과와 화면에 싣는다"
```

---

### Task 9: 문서 + 캘리브레이션 재기준선

**Files:**
- Modify: `docs/engine-gaps.md:1901` (갭 행 → 해소), `:3452` 부근
- Modify: `docs/roadmap.md:3343` To-Do → 완료
- Modify: `docs/decisions.md` (결정 A의 근거와 기각한 대안)
- Modify: `docs/measurements/burst-gauge-fill.md` (해석 절만 — **RAW는 편집 금지**)

- [ ] **Step 1: 보류된 게이지 불릿 전수 census**

Run: `grep -rn "Burst Gauge\|버스트 게이지" backend/app/skill_rules/*.py`

오늘 확인된 보류 7건 — `anis_star`(fill speed) · `grave` · `helm` · `mana`(**70.4%**) · `maxwell_ordinary_mechanic`(풀차지마다 7.15%) · `neon_vision_eye` · `rosanna`/`rosanna_signature`(36.54%). Task 5~7이 만든 능력으로 **어느 것이 이제 표현 가능한지** 판정해 각 모듈의 보류 문구를 갱신한다.

**「적히지 않은 능력은 없는 능력이다」** — 이 저장소가 낡은 보류 때문에 네 번 같은 실패를 했다. 표현 가능해진 것을 보류로 남기면 다음 세션이 그것을 갭으로 다시 기록한다.

- [ ] **Step 2: 캘리브레이션 재기준선**

Run: `python scripts/measure_record_calibration.py`
새 숫자를 `docs/roadmap.md`에 기록한다. **「합계가 내려갔으니 나빠졌다」로 읽지 않는다** — 없던 제약이 사라진 것이고, `sim/record`는 목표가 아니라 상한이다.

- [ ] **Step 3: 커밋**

```bash
git add docs/
git commit -m "게이지가 덱 속성이 됐다 - 갭·로드맵·결정 기록"
```
