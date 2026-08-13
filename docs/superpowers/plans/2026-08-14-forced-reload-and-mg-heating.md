# 강제 재장전 적용 + MG 예열 속도 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 네 유닛의 「탄약 제거 + 강제 재장전」을 이미 있는 세그먼트 관용구로 인코딩하고, 스킬이 MG 예열 속도를 바꿀 수 있게 엔진에 스탯 하나를 신설한다.

**Architecture:** 두 갈래다. 갈래 1(질·라플라스UH·그레이브·아스카)은 **엔진 코드 0줄** — 발사 0인 `weapon_mode_schedules` 세그먼트가 「탄창 폐기 → 재장전 → 새 탄창」을 이미 표현하며, 밀크와 스칼렛이 쓰고 있는 관용구다. 갈래 2는 새 스탯 `mg_heating_speed_percent`를 `attack_rate`의 순수 함수 하나와 `raid_simulator`의 람다 하나로 배선한다. 아스카가 둘 다의 소비자라 마지막에 온다.

**Tech Stack:** Python 3.14 · pytest · 백엔드 전용(프론트 무변경)

**Spec:** `docs/superpowers/specs/2026-08-14-forced-reload-and-mg-heating-design.md`

## Global Constraints

- **모든 pytest는 `backend/`에서 실행한다.** 루트에서는 `No module named 'app'`으로 수집이 깨진다.
- **슬롯 번호를 추론하지 않는다.** 이 계획의 슬롯 번호는 전부 `assemble_skill_values`를 실제로 돌려 읽은 값이다. 새 값이 필요하면 같은 방법으로 읽는다.
- **엔진 코드는 갈래 2에서만 바뀐다.** Task 2·3·4는 `backend/app/skill_rules/` 와 `backend/tests/` 밖을 건드리지 않는다.
- **버프가 없을 때 트렁크와 바이트 동일해야 한다.** 갈래 2의 기본값은 `_zero`다.
- **각 Task의 마지막에 커밋한다.** 커밋 메시지는 한국어, 무엇을/왜만 적고 "예전엔 이랬다"는 쓰지 않는다.
- **세그먼트 프로필은 명시적 `rate_of_fire`를 쓴다.** 계약상 명시적 연사 프로필은 어떤 cadence 버프도 받지 않으므로, 아군 차지속도 버프가 무발사 창을 줄여 유령 발사를 흘리지 못한다.
- **`reload_time_with_speed(reload_time, s) = max(0.0, reload_time * (1 - s) + 0.148)`** — 아핀이다. `s=0`은 항등이 아니다.
- **기준선은 `2299 passed · 3 skipped`** (2026-08-14, `0ad7ed00` 기준, 107초). 각 Task의 전체 스위트 단계는 이 수에 새 테스트를 더한 값이어야 한다.
- **`caster_weapon_stats["reload_time"]`은 이미 클립 분할이 곱해진 값이다.** `user_roster.py:110-112`가 `get_clip_reload_splits(slug)`를 곱한 뒤 빌더에 넘긴다. 그레이브는 `CLIP_RELOAD_SPLITS["grave"] = 2`(「AR, 60발을 절반씩」, 무기 번들의 `shot_detail.reload_bullet`에서 온 값)라 그녀가 받는 값은 **파일 1.0초가 아니라 2.0초**다. 스킬의 `Reload Ratio`와 **다른 것**이다 — 전자는 무기의 상시 성질, 후자는 방열 동안만 걸리는 스킬 효과다.
- **새 세그먼트 유닛 셋이 생기므로** `backend/tests/test_weapon_mode_collectible.py`(등록된 모든 스케줄 빌더를 도는 파라미터 테스트)와 `scripts/check_transform_window_overlap.py`(새 변형 유닛을 인코딩할 때 돌리라고 자기 독스트링이 지시한다)를 Task 2·4·7에서 각각 돌린다.

읽어 둔 실제 슬롯 (`assemble_skill_values`, 전 스킬 레벨 10):

| 유닛 / 불릿 | 슬롯 | 값 |
|---|---|---|
| `asuka` / `emergency_repair` | `_03` 예열 ▼% · `_04` 지속 · `_05` 탄약제거% · `_08` 재장전고정% · `_09` 회수 | 100 · 3 · 100 · 60 · 1 |
| `rei-…-tentative-name` / `maintenance_and_resupply` | `_01` 예열 ▲% · `_02` 지속 | 100 · 13 |
| `jill-valentine` / `supercop` | `_01` 재장전고정% · `_03` 탄약제거% | 99.96 · 100 |
| `grave` / `heat_emission` | `_01` 탄약제거% · `_02` Reload Ratio ▼% · `_05` Pierce% | 100 · 50 · 48.4 |

## 확인했고 범위 밖인 것 — 나유타의 무한탄창

Fienn이 착수 중에 물었다(2026-08-14): 나유타도 무기변형 중에는 무한탄창(탄 소모 없음)인데 구현돼 있나?

**돼 있다, 그리고 그것이 그 구현을 고른 이유다.** `build_memory_incineration_weapon_mode_schedule`은 `until_shots`가 아니라 `{"start": t, "end": t + duration}`으로 시간을 끝내고, 독스트링이 이렇게 적고 있다 — *"segments never reload, and Memory Incineration grants 'Unlimited ammunition' for exactly the same 10 sec, so there is no magazine to interrupt the window."* 아니스: 스타의 등가-차지속도 우회 대신 세그먼트를 쓴 근거가 바로 무한탄창이다. **할 일 없음.**

「탄 **소모** 없음」의 두 번째 결과 — 아군 소모탄 카운터 — 는 모델돼 있지 않다.
`raid_simulator.py:1365`가 `ammo_rounds_per_shot.get(slug, (1.0, 1.0))`으로 슬러그 단위 계상만 하므로 그녀의 변형 발사도 발당 1라운드로 세어진다. 세그먼트별 구분은 `_AMMO_ROUNDS_PER_SHOT`의 `(풀버스트 안, 밖)` 튜플로 표현할 수 없다.

**크기가 무시할 만해서 범위 밖으로 둔다:** 변형은 버스트당 10초 · 1.8초 간격이라 5발, 180초 4버스트면 ~20발이다. 그녀 SMG는 같은 전투에서 20발/초로 수천 발을 쏜다. 살아 있는 소비자는 리틀 머메이드의 Bubble Barrage(아군 500발마다) 하나뿐이다. 같은 성질이 `moran`·`grave`·`laplace-ultimate-hero`에도 있으므로, 고친다면 유닛 하나가 아니라 그 축 전체를 고쳐야 한다.

---

## File Structure

**갈래 1 (엔진 0줄):**
- `backend/app/skill_rules/jill_valentine.py` — 스케줄 빌더 추가, 낡은 보류 삭제
- `backend/app/skill_rules/laplace_ultimate_hero.py` — 기존 `build_laplace_transform_schedule`에 재장전 세그먼트 추가
- `backend/app/skill_rules/grave.py` — 무한탄약 버프 · 강제 재장전 세그먼트 · 방열 지속시간 정정
- `backend/app/skill_rules/asuka_shikinami_langley_wille.py` — 스케줄 빌더 + 예열 ▼ 버프
- `backend/app/skill_rules/registry.py:975` — `_WEAPON_MODE_SCHEDULE_BUILDERS`에 세 슬러그 추가

**갈래 2 (엔진):**
- `backend/app/attack_rate.py` — `spinup_with_speed` 신설, 네 호출부(643·773·865·1064줄)가 새 인자를 받음
- `backend/app/raid_simulator.py:1334 부근` — `heating_speed_percent_at` 람다
- `backend/app/skill_rules/rei_ayanami_tentative_name.py` — 예열 ▲ 버프

**문서:**
- `.claude/skills/nikke-skill-encoding/references/engine-capabilities.md` — 관용구 기재
- `docs/engine-gaps.md` · `docs/encoded-nikkes.md` — 최종 갱신

---

### Task 1: 카탈로그에 「발사 0 세그먼트 = 강제 재장전」을 적는다

**왜 먼저인가:** Task 2·3·4의 독스트링이 전부 이 문장을 근거로 삼는다. 그리고 이 갭이 열려 있던 유일한 이유가 **능력을 만든 날 카탈로그에 안 적은 것**이다.

**Files:**
- Modify: `.claude/skills/nikke-skill-encoding/references/engine-capabilities.md` (`weapon_mode_schedules` 절 끝)

**Interfaces:**
- Consumes: 없음
- Produces: 없음 (문서)

- [ ] **Step 1: 현재 문장을 찾는다**

Run: `grep -n "weapon_mode_schedules" .claude/skills/nikke-skill-encoding/references/engine-capabilities.md`

`First consumers:` 로 시작하는 문단을 찾는다. 그 문단 끝에 아래를 잇는다.

- [ ] **Step 2: 관용구를 추가한다**

```markdown
**A segment that fires nothing IS an ammo dump + forced reload.** A segment
boundary is this engine's "discard the magazine, resume with a fresh one", so a
window that emits no shots models "Removes N% of ammo" + "Forced Reload"
exactly, and a ZERO-LENGTH segment models an instant full reload. Two idioms,
both already in production: `milk_blooming_bunny.py` (a
`reload_time_with_speed`-long window whose profile's interval is twice the
window, so no shot fits, and `damage_percent: 0.0` so a boundary shot would be
harmless anyway) and `scarlet_black_shadow.py` (zero length, for Asura's
"Reload 100% of the magazine(s)"). Use an explicit `rate_of_fire` profile, never
`charge_time`: an explicit-rate profile takes NO cadence buffs by contract, so
an ally's Charge Speed cannot shrink the empty window and leak a shot into it.

Do NOT reach for a segment when the window must keep the unit's LIVE cadence
buffs - the same contract that makes an explicit `rate_of_fire` safe here also
freezes attack speed. "Unlimited ammo for a window on the unit's own weapon" is
that case: raise `max_ammo_percent` for the window instead (see `grave.py`).
A weapon MODE swap that happens to be unlimited-ammo is different, and a
segment is right there (see `moran`'s Fair and Square).
```

- [ ] **Step 3: 검증 — 다음 인코더가 찾을 수 있는가**

Run: `grep -n "forced reload\|ammo dump\|zero-length" .claude/skills/nikke-skill-encoding/references/engine-capabilities.md`
Expected: 최소 3줄이 잡힌다 (착수 전에는 0줄이었다).

- [ ] **Step 4: 커밋**

```bash
git add .claude/skills/nikke-skill-encoding/references/engine-capabilities.md
git commit -m "발사 0 세그먼트가 탄약 제거와 강제 재장전이라는 것을 카탈로그에 적는다"
```

---

### Task 2: 질 발렌타인 — 관용구의 첫 적용

**Files:**
- Modify: `backend/app/skill_rules/jill_valentine.py`
- Modify: `backend/app/skill_rules/registry.py:975` (`_WEAPON_MODE_SCHEDULE_BUILDERS`)
- Test: `backend/tests/test_skill_rules_jill_valentine_forced_reload.py` (신규)

**Interfaces:**
- Consumes: `attack_rate.reload_time_with_speed(reload_time, reload_speed_percent) -> float`
- Produces: `jill_valentine.build_jill_weapon_mode_schedule(values) -> schedule`, 여기서 `schedule(context, fight_duration) -> list[dict]`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/tests/test_skill_rules_jill_valentine_forced_reload.py`:

```python
"""Jill Valentine's Supercop empties her magazine and forces a reload.

The window's length is derived from her own weapon's reload time through the
skill's own "reload speed is fixed at" value, the same way Milk's is - not a
transcribed constant.
"""
import pytest

from app.attack_rate import reload_time_with_speed
from app.skill_rules.jill_valentine import build_jill_weapon_mode_schedule

SLUG = "jill-valentine"

# Read from assemble_skill_values at skill level 10: _01 is the fixed reload
# speed (99.96%), _03 is the ammo removed (100%).
SUPERCOP = {
    "description_value_01": "99.96",
    "description_value_02": "10",
    "description_value_03": "100",
    "description_value_04": "80.78",
    "description_value_05": "10",
    "description_value_06": "75",
    "description_value_07": "10",
    "description_value_08": "10",
}
VALUES = {
    "supercop": SUPERCOP,
    "caster_weapon_stats": {"weapon": "AR", "reload_time": 1.5},
}


class _Context:
    def __init__(self, burst_times):
        self.burst_times = {SLUG: burst_times}


def test_segment_starts_at_her_burst_and_lasts_the_fixed_reload():
    schedule = build_jill_weapon_mode_schedule(VALUES)

    (segment,) = schedule(_Context([20.0]), 180.0)

    assert segment["start"] == pytest.approx(20.0)
    assert segment["end"] == pytest.approx(20.0 + reload_time_with_speed(1.5, 0.9996))


def test_no_shot_fits_in_the_window_and_it_would_be_harmless_if_one_did():
    schedule = build_jill_weapon_mode_schedule(VALUES)

    (segment,) = schedule(_Context([20.0]), 180.0)

    window = segment["end"] - segment["start"]
    assert 1.0 / segment["profile"]["rate_of_fire"] > window
    assert segment["profile"]["damage_percent"] == 0.0
    assert segment["profile"]["weapon"] == "AR"


def test_segment_is_clipped_by_the_fight_end():
    schedule = build_jill_weapon_mode_schedule(VALUES)

    segments = schedule(_Context([179.9]), 180.0)

    assert segments[-1]["end"] == pytest.approx(180.0)


def test_no_segment_for_a_burst_at_or_past_the_bell():
    schedule = build_jill_weapon_mode_schedule(VALUES)

    assert schedule(_Context([180.0]), 180.0) == []
```

- [ ] **Step 2: 실패를 확인한다**

Run: `cd backend && python -m pytest tests/test_skill_rules_jill_valentine_forced_reload.py -v`
Expected: FAIL — `ImportError: cannot import name 'build_jill_weapon_mode_schedule'`

- [ ] **Step 3: 빌더를 구현한다**

`backend/app/skill_rules/jill_valentine.py` 파일 끝에 추가하고, 맨 위 import에 `reload_time_with_speed`를 더한다:

```python
from app.attack_rate import reload_time_with_speed
```

```python
def build_jill_weapon_mode_schedule(values):
    """Supercop's "Removes 100% of ammo" + "Forced Reload", as a segment that
    fires nothing: entering it discards her magazine and the base weapon
    resumes with a fresh one when it ends, which is what lets her 10-sec buff
    window spend a FULL magazine.

    The window's length is her own weapon's reload under the skill's "Reload
    speed is fixed at a 99.96% increase" clause. "Fixed" means it overrides
    whatever else is live, so the length is derived from that value alone and
    not from the registry - the same reading Milk's forced reload already
    implements. `rate_of_fire` (not `charge_time`) so no ally's Charge Speed
    buff can shrink the empty window into leaking a shot.
    """
    supercop = values["supercop"]
    fixed_reload_speed = float(supercop["description_value_01"]) / 100
    weapon_stats = values["caster_weapon_stats"]
    reload_seconds = reload_time_with_speed(weapon_stats["reload_time"], fixed_reload_speed)
    weapon = weapon_stats["weapon"]

    def schedule(context, fight_duration):
        segments = []
        for burst_time in context.burst_times.get("jill-valentine", []):
            if burst_time >= fight_duration:
                continue
            segments.append({
                "start": burst_time,
                "end": min(burst_time + reload_seconds, fight_duration),
                "profile": {
                    "weapon": weapon,
                    "damage_percent": 0.0,
                    "rate_of_fire": 1.0 / (reload_seconds * 2),
                },
            })
        return segments

    return schedule
```

- [ ] **Step 4: 레지스트리에 등록한다**

`registry.py:93-96`의 jill import 블록에 `build_jill_weapon_mode_schedule`을 더하고, `_WEAPON_MODE_SCHEDULE_BUILDERS`(975~1002줄) 안에 한 줄 더한다:

```python
    "jill-valentine": lambda sv: build_jill_weapon_mode_schedule(sv),  # Supercop's ammo dump + forced reload
```

그 다음 등록된 **모든** 스케줄 빌더를 도는 레지스트리 전역 가드를 돌린다:

Run: `cd backend && python -m pytest tests/test_weapon_mode_collectible.py -q`
Expected: PASS (밀크가 같은 모양으로 이미 통과한다)

- [ ] **Step 5: 낡은 보류를 지운다**

`jill_valentine.py` 독스트링에서 아래 두 줄을 **삭제**하고,

```
- Supercop's forced-reload / ammo-removal bookkeeping ("Removes 100% of ammo",
  "Forced Reload"): the engine has no way to empty a magazine mid-fight.
```

`Modeled (DPS-relevant):` 절 끝에 아래를 더한다:

```
- Supercop's "Removes 100% of ammo" + "Forced Reload": a segment that fires
  nothing, spanning her weapon's reload under the skill's own fixed reload
  speed. See build_jill_weapon_mode_schedule.
```

`Not modeled / deferred:` 절이 비면 그 헤딩도 지운다.

- [ ] **Step 6: 테스트가 통과하는지 확인한다**

Run: `cd backend && python -m pytest tests/test_skill_rules_jill_valentine_forced_reload.py tests/test_skill_rules_burst3_eb2.py -v`
Expected: PASS

- [ ] **Step 7: 가드를 직접 떼서 빨개지는지 확인한다**

`build_jill_weapon_mode_schedule`의 `rate_of_fire`를 `1.0 / (reload_seconds * 2)` 대신 `12.0`으로 바꾸고 테스트를 돌린다.
Expected: `test_no_shot_fits_in_the_window_and_it_would_be_harmless_if_one_did` 가 FAIL.
확인 후 되돌린다. **빨개지지 않으면 그 테스트는 아무것도 재지 않는 것이다.**

- [ ] **Step 8: 전체 스위트로 회귀를 확인한다**

Run: `cd backend && python -m pytest -q`
Expected: 착수 시 기록한 기준선과 같은 수 + 새 테스트 4개.

- [ ] **Step 9: 커밋**

```bash
git add backend/app/skill_rules/jill_valentine.py backend/app/skill_rules/registry.py backend/tests/test_skill_rules_jill_valentine_forced_reload.py
git commit -m "질 발렌타인의 Supercop 탄약 제거와 강제 재장전을 인코딩한다"
```

---

### Task 3: 라플라스: 얼티메이트 히어로 — 변형 뒤의 재장전

**배경:** 그녀 독스트링이 이미 이 항을 적어 뒀다 — *"resumes the base weapon at the segment's end with a fresh magazine and no reload, so she fires ~2 extra base shots during the 2.5s reload the real cycle spends."* 그것이 `Removes 100% of ammo`(Fully Full Charge 종료 시)다. **그녀는 이 계획에서 유일하게 기존 세그먼트가 있는 유닛**이라 합성 검증 사례다.

**Files:**
- Modify: `backend/app/skill_rules/laplace_ultimate_hero.py` (`build_laplace_transform_schedule`)
- Test: `backend/tests/test_skill_rules_laplace_ultimate_hero.py` (기존 파일에 추가; 없으면 신규)

**Interfaces:**
- Consumes: `attack_rate.reload_time_with_speed`; 기존 `_plan_from_percent`, `_transform_times`, `_PLAN_ATTR`
- Produces: 변경 없음 — `build_laplace_transform_schedule(values) -> schedule` 의 반환 리스트가 변형 세그먼트마다 재장전 세그먼트를 하나씩 더 담는다

- [ ] **Step 1: 실패하는 테스트를 쓴다**

기존 테스트 파일이 있으면 거기에, 없으면 `backend/tests/test_skill_rules_laplace_ultimate_hero_reload.py`에:

```python
"""Laplace: Ultimate Hero's transform ends by removing 100% of her ammo, so the
base weapon does not resume for one reload. Without this the engine hands her
free shots in the gap the real cycle spends reloading.
"""
import pytest

from app.attack_rate import reload_time_with_speed
from app.skill_rules.laplace_ultimate_hero import build_laplace_transform_schedule


def test_every_transform_is_followed_by_a_silent_reload_segment(laplace_uh_values):
    schedule = build_laplace_transform_schedule(laplace_uh_values)

    segments = schedule(_Context(), 180.0)

    transforms = [s for s in segments if s["profile"]["damage_percent"] > 0]
    reloads = [s for s in segments if s["profile"]["damage_percent"] == 0.0]
    assert len(reloads) == len(transforms)


def test_the_reload_segment_starts_where_the_transform_ends(laplace_uh_values):
    schedule = build_laplace_transform_schedule(laplace_uh_values)

    segments = schedule(_Context(), 180.0)

    transform = segments[0]
    reload_segment = segments[1]
    # An `until_shots` window ends AT its last shot's time.
    interval = 1.0 / transform["profile"]["rate_of_fire"]
    transform_end = transform["start"] + transform["until_shots"] * interval
    assert reload_segment["start"] == pytest.approx(transform_end)


def test_the_two_segments_do_not_overlap(laplace_uh_values):
    schedule = build_laplace_transform_schedule(laplace_uh_values)

    segments = sorted(schedule(_Context(), 180.0), key=lambda s: s["start"])

    for earlier, later in zip(segments, segments[1:]):
        end = earlier.get("end")
        if end is None:
            interval = 1.0 / earlier["profile"]["rate_of_fire"]
            end = earlier["start"] + earlier["until_shots"] * interval
        assert end <= later["start"] + 1e-9
```

`_Context`와 `laplace_uh_values` 픽스처는 기존 라플라스UH 테스트에서 쓰는 것을 그대로 재사용한다. 없으면 이 파일 안에 만든다 — `context`는 `max_ammo_percent_at(0.0)`을 제공해야 한다:

```python
class _Context:
    def __init__(self):
        self.max_ammo_percent_at = lambda _t: 0.0
```

- [ ] **Step 2: 실패를 확인한다**

Run: `cd backend && python -m pytest tests/test_skill_rules_laplace_ultimate_hero_reload.py -v`
Expected: FAIL — 재장전 세그먼트가 없어 `len(reloads) == 0`.

- [ ] **Step 3: 빌더를 고친다**

`build_laplace_transform_schedule`의 `schedule` 안에서, 변형 세그먼트마다 재장전 세그먼트를 뒤에 붙인다:

```python
    def schedule(context, fight_duration):
        shots, window, period = _plan_from_percent(weapon, context.max_ammo_percent_at(0.0))
        setattr(context, _PLAN_ATTR, (shots, window, period))
        profile = {
            "weapon": "SMG",
            "damage_percent": shot_percent,
            "rate_of_fire": SMG_RATE_OF_FIRE,
        }
        reload_seconds = reload_time_with_speed(weapon["reload_time"], 0.0)
        interval = 1.0 / SMG_RATE_OF_FIRE
        segments = []
        for t in _transform_times(period, fight_duration):
            segments.append({"start": t, "until_shots": shots, "profile": profile})
            # "Removes 100% of ammo" when Fully Full Charge ends: the base
            # weapon does not resume until one reload has been spent. An
            # `until_shots` window ends AT its last shot, so that instant is
            # where the silent window opens.
            transform_end = t + shots * interval
            if transform_end >= fight_duration:
                continue
            segments.append({
                "start": transform_end,
                "end": min(transform_end + reload_seconds, fight_duration),
                "profile": {
                    "weapon": weapon["weapon"],
                    "damage_percent": 0.0,
                    "rate_of_fire": 1.0 / (reload_seconds * 2),
                },
            })
        return segments
```

파일 맨 위에 `from app.attack_rate import reload_time_with_speed` 를 더한다 (이미 있으면 생략).

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

Run: `cd backend && python -m pytest tests/test_skill_rules_laplace_ultimate_hero_reload.py -v`
Expected: PASS

- [ ] **Step 5: 겹침 거부 가드에 걸리지 않는지 확인한다**

Run: `cd backend && python -m pytest tests/ -k "laplace or overlap or segment" -q`
Expected: PASS. `_reject_unrepresentable_overlaps`가 겹침을 거부하므로, 여기서 실패하면 위 `transform_end` 계산이 틀린 것이다.

- [ ] **Step 6: 독스트링을 갱신한다**

`Not modeled / deferred:` 의 아래 불릿을 삭제한다:

```
- The reload gap after a transform: `generate_segmented_shots` resumes the base
  weapon at the segment's end with a fresh magazine and no reload, so she fires
  ~2 extra base shots during the 2.5s reload the real cycle spends. ...
```

`Modeled` 절에 더한다:

```
- "Removes 100% of ammo" when Electric Power, Fully Full Charge ends: a silent
  segment one reload long, right after the transform window. Before this the
  base weapon resumed with a fresh magazine and no reload at all.
```

- [ ] **Step 7: 전체 스위트**

Run: `cd backend && python -m pytest -q`
Expected: 기준선 + 새 테스트.

- [ ] **Step 8: 커밋**

```bash
git add backend/app/skill_rules/laplace_ultimate_hero.py backend/tests/test_skill_rules_laplace_ultimate_hero_reload.py
git commit -m "라플라스 얼티메이트 히어로의 변형 종료 탄약 제거를 인코딩한다"
```

---

### Task 4: 그레이브 — 무한탄약 · 강제 재장전 ×2 · 방열 지속시간 정정

**이 계획에서 가장 큰 조각이고, 유일하게 기존 인코딩을 고친다.**

세 항:
1. Prediction 10초 동안 **무한탄약** — 세그먼트가 아니라 큰 `max_ammo_percent`. 세그먼트로 하면 명시적 `rate_of_fire` 계약 때문에 **그녀 버프가 다 켜진 창에서 공속이 얼어붙는다.** (`moran`의 Fair and Square가 세그먼트인 것은 그쪽이 **무기 모드 스왑**이라 프로필 교체 자체가 목적이기 때문이다. 그레이브는 자기 무기를 그대로 쓴다.)
2. Prediction 종료 시 **탄약 제거 + 재장전 ×2** — `Reload Ratio ▼50%`가 0탄약에서 절반씩 두 번 장전을 만든다(Fienn 인게임).
3. **방열 지속시간 정정** — 인게임 툴팁 「[방열 제거 조건] ① 재장전을 최대 장탄까지 완료 시 ② 버스트 사용 시」. ①이 훨씬 먼저 문다: 두 번째 장전이 최대 장탄에 닿는 순간 방열이 꺼진다. 현재 코드는 스쿼드 Pierce Damage를 `duration=None`으로 걸고 다음 버스트에서 자른다 — **40초 주기 중 ~30초**를 산다.

**Files:**
- Modify: `backend/app/skill_rules/grave.py`
- Modify: `backend/app/skill_rules/registry.py:975`
- Test: `backend/tests/test_skill_rules_grave_prediction_cycle.py` (신규)

**Interfaces:**
- Consumes: `attack_rate.reload_time_with_speed`, `attack_rate.rate_of_fire_for_weapon(weapon) -> float`, 기존 `grave.PREDICTION_DURATION`
- Produces: `grave.build_grave_weapon_mode_schedule(values) -> schedule`, `grave.heat_emission_seconds(values) -> float`, `grave.unlimited_ammo_percent(values) -> float`

- [ ] **Step 1: 방열 지속시간 가드를 먼저 쓰고, 지금 코드에서 빨개지는 것을 확인한다**

**이 순서가 중요하다.** 이 가드는 현재 코드에서 반드시 실패해야 한다 — 통과하면 아무것도 재지 않는 것이다.

`backend/tests/test_skill_rules_grave_prediction_cycle.py`:

```python
"""Grave's Prediction cycle: unlimited ammo, then the ammo dump, then a reload
that runs twice because Reload Ratio halves each load.

The in-game tooltip ("[방열 제거 조건]") gives Heat Emission TWO removal
conditions - a reload that reaches max ammo, or her burst - and the first fires
far earlier. So the squad buff hanging off Heat Emission lives for the double
reload, not until her next burst.
"""
import pytest

from app.attack_rate import rate_of_fire_for_weapon, reload_time_with_speed
from app.effects import EffectRegistry
from app.skill_rules.grave import (
    PREDICTION_DURATION,
    build_grave_rules,
    build_grave_weapon_mode_schedule,
    heat_emission_seconds,
    unlimited_ammo_percent,
)
from app.squad_engine import SquadContext, SquadMember, fire_trigger

SLUG = "grave"

# Read from assemble_skill_values at skill level 10.
HEAT_EMISSION = {
    "description_value_01": "100",
    "description_value_02": "50",
    "description_value_03": "2",
    "description_value_04": "38.96",
    "description_value_05": "48.4",
}
PLOT_SPOILER = {
    "description_value_01": "10",
    "description_value_02": "30",
    "description_value_03": "20",
    "description_value_04": "25",
    "description_value_05": "3",
    "description_value_06": "15",
}
# reload_time is 2.0, not her file's 1.0: CLIP_RELOAD_SPLITS["grave"] = 2 (her
# AR loads 60 rounds in halves) is already multiplied in by user_roster before
# a builder ever sees the dict. That is her WEAPON's standing behaviour; the
# skill's Reload Ratio is a separate, Heat-Emission-only halving on top.
VALUES = {
    "heat_emission": HEAT_EMISSION,
    "plot_spoiler": PLOT_SPOILER,
    "caster_weapon_stats": {"weapon": "AR", "reload_time": 2.0, "max_ammo": 60},
}


class _Context:
    def __init__(self, burst_times):
        self.burst_times = {SLUG: burst_times}


def test_heat_emission_lives_for_a_doubled_reload_not_until_her_next_burst():
    # THE point of the tooltip: condition 1 (a reload reaching max ammo) fires
    # long before condition 2 (her next burst, 40 sec away). Reload Ratio down
    # 50% halves what each load puts back, so it takes TWICE HER NORMAL reload
    # to reach max - and her normal one already includes the clip split.
    normal = reload_time_with_speed(2.0, 0.0)
    assert heat_emission_seconds(VALUES) == pytest.approx(2 * normal)
    assert heat_emission_seconds(VALUES) < PREDICTION_DURATION


def test_the_squad_pierce_buff_expires_with_heat_emission():
    registry = EffectRegistry()
    context = SquadContext([SquadMember(SLUG, 2, "Fire", "AR")])
    rules = build_grave_rules(VALUES)

    fire_trigger(rules, "own_burst_activate", context, SLUG, 0.0, registry)
    fire_trigger(rules, "full_burst_end", context, SLUG, PREDICTION_DURATION, registry)

    target = {"slug": SLUG, "element": "Fire"}
    live = PREDICTION_DURATION + heat_emission_seconds(VALUES)
    assert registry.total_for("pierce_damage_up", target, live - 0.01) > 0.0
    assert registry.total_for("pierce_damage_up", target, live + 0.01) == pytest.approx(0.0)


def test_unlimited_ammo_covers_the_prediction_window_with_headroom():
    # 10 sec at an AR's 12/s is 120 rounds; the grant must cover that even
    # under heavy attack-speed buffs.
    percent = unlimited_ammo_percent(VALUES)
    rounds = 60 * (1 + percent)
    assert rounds >= PREDICTION_DURATION * rate_of_fire_for_weapon("AR") * 4


def test_the_forced_reload_segment_is_twice_a_normal_reload():
    schedule = build_grave_weapon_mode_schedule(VALUES)

    (segment,) = schedule(_Context([0.0]), 180.0)

    assert segment["start"] == pytest.approx(PREDICTION_DURATION)
    assert segment["end"] - segment["start"] == pytest.approx(2 * reload_time_with_speed(2.0, 0.0))
    assert 1.0 / segment["profile"]["rate_of_fire"] > segment["end"] - segment["start"]
    assert segment["profile"]["damage_percent"] == 0.0
```

- [ ] **Step 2: 지금 코드에서 실패하는 것을 확인한다**

Run: `cd backend && python -m pytest tests/test_skill_rules_grave_prediction_cycle.py -v`
Expected: FAIL — import 에러(`heat_emission_seconds` 없음). import를 임시로 지우고 `test_the_squad_pierce_buff_expires_with_heat_emission`만 돌리면 **버프가 안 꺼져서** 실패해야 한다. 그 실패를 눈으로 확인한 뒤 진행한다.

- [ ] **Step 3: 헬퍼 셋을 구현한다**

`backend/app/skill_rules/grave.py`에 추가한다. 맨 위 import에 더한다:

```python
from app.attack_rate import rate_of_fire_for_weapon, reload_time_with_speed
```

```python
# Prediction's unlimited ammo only has to outlast the window. Four times the
# rounds an unbuffed AR spends in it is headroom no deck's attack speed
# reaches, and the magazine is discarded at the window's end anyway.
UNLIMITED_AMMO_HEADROOM = 4.0


def unlimited_ammo_percent(values):
    """Prediction's unlimited ammunition, as a max-ammo ratio big enough that no
    reload lands inside the window.

    NOT a weapon-mode segment: a segment would silence her own weapon and take
    its cadence from an explicit `rate_of_fire`, which by contract ignores live
    buffs - and this window is exactly when her deck's buffs are up. Raising
    max ammo keeps every live buff and costs one approximation instead: capacity
    is sampled at each magazine's START, so the grant reaches the first magazine
    that begins inside Prediction rather than the one already in flight. That
    leaves one extra reload in the window, which understates her.
    """
    weapon = values["caster_weapon_stats"]
    rounds = (PREDICTION_DURATION * rate_of_fire_for_weapon(weapon["weapon"])
              * UNLIMITED_AMMO_HEADROOM)
    return rounds / weapon["max_ammo"] - 1.0


def heat_emission_seconds(values):
    """How long Heat Emission lives: the lengthened reload it takes to get back
    to max ammo from empty.

    In-game tooltip "[방열 제거 조건]": Heat Emission is removed (1) when a
    reload completes to MAX AMMUNITION, or (2) when she bursts again. Condition
    1 fires first by a wide margin - her burst cooldown is 40 sec - so the
    status, and everything hanging off it, lives exactly as long as this.

    Reload Ratio down 50% halves what each load puts back, so it takes twice as
    many loads to reach max, which is what Fienn read in game as "she loads half
    a magazine twice - the reload just takes twice as long". This is a MULTIPLIER
    on her reload, not an absolute load count: her AR already loads in halves
    (`CLIP_RELOAD_SPLITS["grave"] = 2`, folded into `reload_time` before a
    builder sees it), and the skill halves that ratio again on top.

    Approximation: the reload's fixed animation segment (RELOAD_FIXED_SECONDS)
    is paid once per lengthened reload, not once per load. Unmeasured either
    way, and it is 0.148 sec against a multi-second window.
    """
    ratio_reduction = float(values["heat_emission"]["description_value_02"]) / 100
    reload_multiplier = 1 / (1 - ratio_reduction)
    normal = reload_time_with_speed(values["caster_weapon_stats"]["reload_time"], 0.0)
    return reload_multiplier * normal
```

- [ ] **Step 4: 세그먼트 빌더를 구현한다**

```python
def build_grave_weapon_mode_schedule(values):
    """The ammo dump when Prediction ends, as a segment that fires nothing.

    "Removes 100% of bullets" lands at the end of her own burst's Prediction
    window, and the reload that follows runs for `heat_emission_seconds` - twice
    a normal one, because Reload Ratio only puts half the magazine back per
    load. `rate_of_fire` (not `charge_time`) so no ally's Charge Speed buff can
    shrink the window into leaking a shot.
    """
    reload_seconds = heat_emission_seconds(values)
    weapon = values["caster_weapon_stats"]["weapon"]

    def schedule(context, fight_duration):
        segments = []
        for burst_time in context.burst_times.get("grave", []):
            start = burst_time + PREDICTION_DURATION
            if start >= fight_duration:
                continue
            segments.append({
                "start": start,
                "end": min(start + reload_seconds, fight_duration),
                "profile": {
                    "weapon": weapon,
                    "damage_percent": 0.0,
                    "rate_of_fire": 1.0 / (reload_seconds * 2),
                },
            })
        return segments

    return schedule
```

- [ ] **Step 5: 무한탄약 버프와 방열 지속시간 정정을 `build_grave_rules`에 넣는다**

`apply_plot_spoiler` 안, 마지막 `registry.add(...)` 뒤에 더한다:

```python
        # Prediction's unlimited ammunition, for the window her own burst opens.
        registry.add(
            Effect("max_ammo_percent", unlimited_ammo, "self", PREDICTION_DURATION, caster_slug),
            applied_at=time,
        )
```

`build_grave_rules` 상단에 더한다:

```python
    unlimited_ammo = unlimited_ammo_percent(values)
    heat_emission_duration = heat_emission_seconds(values)
```

`apply_heat_emission`을 **유한 지속**으로 고친다:

```python
    def apply_heat_emission(context, caster_slug, time, registry):
        if context.has_status(caster_slug, HEAT_EMISSION_STATUS):
            return
        context.set_status(caster_slug, HEAT_EMISSION_STATUS)
        # The status ends when a reload reaches max ammo (in-game tooltip
        # condition 1), which the double reload below does. Her burst - the
        # other removal condition - is 40 sec away and never gets there first,
        # so `remove_heat_emission_on_reburst` stays only as a safety net.
        registry.add(
            Effect("pierce_damage_up", heat_emission_pierce, "squad",
                   heat_emission_duration, caster_slug),
            applied_at=time,
        )
```

`remove_heat_emission_on_reburst`의 `registry.truncate_open_ended(...)` 호출은 **삭제**한다 — 더 이상 무기한 효과가 없다. 상태 클리어는 남긴다:

```python
    def remove_heat_emission_on_reburst(context, caster_slug, time, registry):
        # Removal condition 2. The buff itself is already timed out by then
        # (condition 1 fires within two reloads), so only the status flag is
        # cleared here.
        if context.has_status(caster_slug, HEAT_EMISSION_STATUS):
            context.clear_status(caster_slug, HEAT_EMISSION_STATUS)
```

- [ ] **Step 6: 레지스트리에 등록한다**

`registry.py:141`의 한 줄짜리 grave import(`from app.skill_rules.grave import build_grave_rules, build_overheat_per_shot_rules`)에 `build_grave_weapon_mode_schedule`을 더하고, `_WEAPON_MODE_SCHEDULE_BUILDERS`(975~1002줄)에 한 줄 더한다:

```python
    "grave": lambda sv: build_grave_weapon_mode_schedule(sv),  # Prediction's ammo dump + the doubled reload
```

Run: `cd backend && python -m pytest tests/test_weapon_mode_collectible.py -q`

- [ ] **Step 7: 테스트가 통과하는지 확인한다**

Run: `cd backend && python -m pytest tests/test_skill_rules_grave_prediction_cycle.py tests/test_skill_rules_grave.py -v`
Expected: PASS (기존 그레이브 테스트 중 방열 지속시간을 단정하던 것이 있으면 그 기대값을 이 계획의 판정에 맞게 고친다 — 값이 아니라 **툴팁**이 근거다).

- [ ] **Step 8: 가드를 직접 떼서 빨개지는지 확인한다**

`apply_heat_emission`의 `heat_emission_duration`을 `None`으로 되돌리고 돌린다.
Expected: `test_the_squad_pierce_buff_expires_with_heat_emission` FAIL. 확인 후 되돌린다.

- [ ] **Step 9: 전체 스위트**

Run: `cd backend && python -m pytest -q`

- [ ] **Step 10: 독스트링을 갱신한다**

`grave.py` 독스트링에서 *"Her self HP drain and the unlimited ammunition (both Prediction) are not modeled."* 를 *"Her self HP drain (Prediction) is not modeled - survivability."* 로 줄이고, Heat Emission 문단의 「removed exactly when Grave uses her burst skill AGAIN」을 툴팁의 두 조건으로 고쳐 쓴다. 무한탄약·이중 재장전·방열 지속시간을 `Modeled` 쪽에 적는다.

- [ ] **Step 11: 커밋**

```bash
git add backend/app/skill_rules/grave.py backend/app/skill_rules/registry.py backend/tests/test_skill_rules_grave_prediction_cycle.py
git commit -m "그레이브의 Prediction 무한탄약과 이중 재장전을 인코딩하고 방열 지속시간을 바로잡는다"
```

---

### Task 5: 엔진 — `mg_heating_speed_percent`

**Files:**
- Modify: `backend/app/attack_rate.py` (`spinup_with_speed` 신설; 643·773·865·1064줄의 네 호출부)
- Modify: `backend/app/raid_simulator.py` (`attack_speed_percent_at` 람다 옆)
- Test: `backend/tests/test_mg_spinup.py` (기존 파일에 추가)

**Interfaces:**
- Consumes: 기존 `Spinup`, `MG_SPINUP`, `spinup_for_weapon`, `RATE_OF_FIRE_60FPS`
- Produces: `attack_rate.spinup_with_speed(spinup, heating_speed_percent, rate_of_fire) -> Spinup | None`; 네 생성기가 새 키워드 인자 `heating_speed_percent_at=_zero`를 받는다

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/tests/test_mg_spinup.py` 끝에 추가:

```python
from app.attack_rate import MG_SPINUP, spinup_with_speed


def test_zero_is_the_identity():
    assert spinup_with_speed(MG_SPINUP, 0.0, 60.0) is MG_SPINUP


def test_none_stays_none_for_a_weapon_without_a_warm_up():
    assert spinup_with_speed(None, 1.0, 12.0) is None


def test_heating_speed_down_100_percent_doubles_the_ramp():
    # Fienn (2026-08-14): a speed arrow reads as a multiplier on the DURATION,
    # the same shape as Ada's charge speed down 300% meaning charge time x4.
    scaled = spinup_with_speed(MG_SPINUP, -1.0, 60.0)
    assert scaled.seconds == pytest.approx(MG_SPINUP.seconds * 2)
    assert scaled.intervals == MG_SPINUP.intervals


def test_heating_speed_up_100_percent_halves_the_ramp():
    scaled = spinup_with_speed(MG_SPINUP, 1.0, 60.0)
    assert scaled.seconds == pytest.approx(MG_SPINUP.seconds / 2)
    assert scaled.intervals == MG_SPINUP.intervals


def test_the_ramp_can_never_beat_the_nominal_rate():
    # A warm-up is a slow start, not an accelerator. 137/60 sec over 48 gaps
    # only reaches the nominal 48/60 at +185.4%, so clamp above that.
    scaled = spinup_with_speed(MG_SPINUP, 5.0, 60.0)
    assert scaled.seconds == pytest.approx(MG_SPINUP.intervals / 60.0)


def test_a_debuffed_magazine_takes_longer_to_empty():
    from app.attack_rate import generate_magazine_shot_times

    plain = generate_magazine_shot_times(
        rate_of_fire=60.0, max_ammo=300, reload_time=2.0, fight_duration=30.0,
        weapon="MG")
    slowed = generate_magazine_shot_times(
        rate_of_fire=60.0, max_ammo=300, reload_time=2.0, fight_duration=30.0,
        weapon="MG", heating_speed_percent_at=lambda _t: -1.0)

    assert len(slowed) < len(plain)


def test_an_unbuffed_unit_is_bit_identical_to_the_default():
    from app.attack_rate import generate_magazine_shot_times

    default = generate_magazine_shot_times(
        rate_of_fire=60.0, max_ammo=300, reload_time=2.0, fight_duration=30.0,
        weapon="MG")
    explicit_zero = generate_magazine_shot_times(
        rate_of_fire=60.0, max_ammo=300, reload_time=2.0, fight_duration=30.0,
        weapon="MG", heating_speed_percent_at=lambda _t: 0.0)

    assert default == explicit_zero
```

`generate_magazine_shot_times`의 실제 키워드 이름은 착수 시 시그니처를 열어 맞춘다.

- [ ] **Step 2: 실패를 확인한다**

Run: `cd backend && python -m pytest tests/test_mg_spinup.py -v`
Expected: FAIL — `ImportError: cannot import name 'spinup_with_speed'`

- [ ] **Step 3: `spinup_with_speed`를 구현한다**

`backend/app/attack_rate.py`, `spinup_for_weapon` 바로 아래:

```python
def spinup_with_speed(spinup, heating_speed_percent, rate_of_fire):
    """This warm-up under a live "MG heating up speed" buff or debuff.

    Fienn's ruling (2026-08-14): the arrow scales the DURATION, so up 100%
    halves the ramp and down 100% doubles it - the same shape as Ada's charge
    speed down 300% meaning charge time x4. The number of gaps the ramp covers
    (`intervals`) does NOT move; the 48 rounds just take longer or less long.

    Note the positive direction deliberately differs from
    `reload_time_with_speed`, whose `(1 - s)` would erase the ramp entirely at
    up 100%. The negative direction agrees with it (both give x2 at down 100%).

    The clamp is what keeps a warm-up a slow start rather than an accelerator:
    the ramp can never be tighter than the weapon's nominal gap. MG_SPINUP only
    reaches that at +185.4%, so no shipped value touches it.
    """
    if spinup is None or not heating_speed_percent:
        return spinup
    if heating_speed_percent >= 0:
        seconds = spinup.seconds / (1 + heating_speed_percent)
    else:
        seconds = spinup.seconds * (1 - heating_speed_percent)
    return Spinup(intervals=spinup.intervals,
                  seconds=max(seconds, spinup.intervals / rate_of_fire))
```

- [ ] **Step 4: 네 호출부를 배선한다**

`attack_rate.py`의 네 곳 모두, 시그니처에 `heating_speed_percent_at=_zero`를 더하고 `spinup = spinup_for_weapon(weapon)`를 탄창 루프 **안**으로 옮겨 `magazine_start`에서 샘플링한다:

```python
    base_spinup = spinup_for_weapon(weapon)
    while magazine_start < fight_duration:
        shot_interval = 1.0 / (rate_of_fire * (1 + attack_speed_percent_at(magazine_start)))
        spinup = spinup_with_speed(
            base_spinup, heating_speed_percent_at(magazine_start), rate_of_fire)
        ...
```

네 곳:
1. `generate_magazine_shot_times` (643줄 부근)
2. last-bullet 마커 생성기 (773줄 부근)
3. first-bullet 마커 생성기 (865줄 부근)
4. `_base_shot_records` (1064줄 부근) — 여기서는 `rate = rate_of_fire_for_weapon(weapon)`가 이미 있다

**마커 둘을 빼먹으면 first/last-bullet 트리거가 실제 탄창과 어긋난다.** 예열이 처음 착륙했을 때 배선 지점이 넷이었던 이유가 그것이다.

- [ ] **Step 5: `raid_simulator`에 람다를 더한다**

`attack_speed_percent_at` 람다 바로 뒤(1334줄 부근):

```python
        heating_speed_percent_at = lambda t, target=target: registry.total_for(
            "mg_heating_speed_percent", target, t
        )
```

그리고 `generate_segmented_shots(...)` 호출과, 마커/발사시각 생성기를 부르는 모든 자리에 `heating_speed_percent_at=heating_speed_percent_at`를 넘긴다. `grep -n "attack_speed_percent_at=" backend/app/raid_simulator.py` 로 자리를 전부 찾는다 — **같은 수만큼** 넘겨야 한다.

- [ ] **Step 6: 테스트가 통과하는지 확인한다**

Run: `cd backend && python -m pytest tests/test_mg_spinup.py tests/test_attack_rate.py -v`
Expected: PASS

- [ ] **Step 7: 회귀 — 버프 없는 전 로스터가 불변인지**

Run: `cd backend && python -m pytest -q`
Expected: 기준선과 **정확히 같은 수**가 통과. 하나라도 숫자가 움직였다면 기본값이 `_zero`가 아니거나 호출부 하나를 잘못 고친 것이다.

- [ ] **Step 8: 커밋**

```bash
git add backend/app/attack_rate.py backend/app/raid_simulator.py backend/tests/test_mg_spinup.py
git commit -m "스킬이 MG 예열 속도를 바꿀 수 있게 배선한다"
```

---

### Task 6: 레이 아야나미 — 예열 ▲의 첫 소비자

**Files:**
- Modify: `backend/app/skill_rules/rei_ayanami_tentative_name.py`
- Test: `backend/tests/test_skill_rules_rei_ayanami_tentative_name.py` (기존 파일에 추가)

**Interfaces:**
- Consumes: `_helpers.member_subset_buff_rule(trigger, member_filter, buffs)`; Task 5의 `mg_heating_speed_percent`
- Produces: `build_rei_tentative_rules`가 규칙을 하나 더 반환한다

- [ ] **Step 1: 실패하는 테스트를 쓴다**

```python
def test_maintenance_speeds_up_only_mg_allies_who_already_burst():
    registry = EffectRegistry()
    context = SquadContext([
        SquadMember("rei-ayanami-tentative-name", 3, "Wind", "AR"),
        SquadMember("asuka-shikinami-langley-wille", 3, "Wind", "MG"),
        SquadMember("liter", 1, "Wind", "SMG"),
    ])
    context.burst_used_this_cycle.add("asuka-shikinami-langley-wille")
    rules = build_rei_tentative_rules(VALUES)

    fire_trigger(rules, "full_burst_enter", context, "rei-ayanami-tentative-name", 5.0, registry)

    mg_ally = {"slug": "asuka-shikinami-langley-wille", "element": "Wind"}
    smg_ally = {"slug": "liter", "element": "Wind"}
    assert registry.total_for("mg_heating_speed_percent", mg_ally, 6.0) == pytest.approx(1.0)
    assert registry.total_for("mg_heating_speed_percent", smg_ally, 6.0) == pytest.approx(0.0)


def test_the_heating_buff_lasts_its_stated_thirteen_seconds():
    registry = EffectRegistry()
    context = SquadContext([
        SquadMember("rei-ayanami-tentative-name", 3, "Wind", "AR"),
        SquadMember("asuka-shikinami-langley-wille", 3, "Wind", "MG"),
    ])
    context.burst_used_this_cycle.add("asuka-shikinami-langley-wille")
    rules = build_rei_tentative_rules(VALUES)

    fire_trigger(rules, "full_burst_enter", context, "rei-ayanami-tentative-name", 5.0, registry)

    mg_ally = {"slug": "asuka-shikinami-langley-wille", "element": "Wind"}
    assert registry.total_for("mg_heating_speed_percent", mg_ally, 17.9) == pytest.approx(1.0)
    assert registry.total_for("mg_heating_speed_percent", mg_ally, 18.1) == pytest.approx(0.0)
```

`context.burst_used_this_cycle`의 실제 이름·형태는 `member_subset_buff_rule`이 읽는 것을 확인해 맞춘다 (`_helpers.py:192` 독스트링이 "all Burst 3 allies who previously used their Burst Skill"을 예로 든다).

- [ ] **Step 2: 실패를 확인한다**

Run: `cd backend && python -m pytest tests/test_skill_rules_rei_ayanami_tentative_name.py -v`
Expected: FAIL — `mg_heating_speed_percent`가 0.

- [ ] **Step 3: 규칙을 더한다**

`build_rei_tentative_rules`에 더한다. 상단 import에 `member_subset_buff_rule`를 추가:

```python
    heating_speed = float(maintenance["description_value_01"]) / 100
    heating_duration = float(maintenance["description_value_02"])
```

반환 리스트에 더한다:

```python
        # "Affects all allies with a Machine Gun who have used their Burst
        # Skills" - the narrow subset Effect.scope can't express, resolved live
        # so the "already burst" half is read at the trigger's own moment.
        member_subset_buff_rule(
            "full_burst_enter",
            lambda member, context: (
                member.weapon == "MG"
                and member.slug in context.burst_used_this_cycle),
            [("mg_heating_speed_percent", heating_speed, heating_duration)],
        ),
```

- [ ] **Step 4: 독스트링을 고친다**

`Not modeled / deferred:` 에서 아래를 **삭제**한다:

```
- Maintenance and Resupply's "MG heating up speed +100%" for MG allies - a
  niche MG spin-up mechanic the engine doesn't model.
```

`Modeled` 절에 더한다:

```
- Maintenance and Resupply's second bullet: on Full Burst entry, allies holding
  a Machine Gun who have already used their Burst Skill get MG heating up speed
  +100% for 13 sec - halving the 2.28-sec warm-up every one of their magazines
  pays (docs/measurements/mg-spinup.md).
```

- [ ] **Step 5: 테스트 통과 확인**

Run: `cd backend && python -m pytest tests/test_skill_rules_rei_ayanami_tentative_name.py -v`

- [ ] **Step 6: 가드를 떼서 확인한다**

`member.weapon == "MG"` 조건을 지우고 돌린다.
Expected: `test_maintenance_speeds_up_only_mg_allies_who_already_burst`의 SMG 단정이 FAIL. 되돌린다.

- [ ] **Step 7: 커밋**

```bash
git add backend/app/skill_rules/rei_ayanami_tentative_name.py backend/tests/test_skill_rules_rei_ayanami_tentative_name.py
git commit -m "레이의 MG 예열 속도 버프를 인코딩한다"
```

---

### Task 7: 아스카 — 갈래 1과 2를 동시에

**Task 5·6 이후여야 한다.** 그녀 혼자 세그먼트와 예열 디버프를 같은 순간에 받는다.

**Files:**
- Modify: `backend/app/skill_rules/asuka_shikinami_langley_wille.py`
- Modify: `backend/app/skill_rules/registry.py:975`
- Test: `backend/tests/test_skill_rules_asuka_shikinami_langley_wille.py` (기존 파일에 추가)

**Interfaces:**
- Consumes: `attack_rate.reload_time_with_speed`, `_helpers.buff_rule`, Task 5의 `mg_heating_speed_percent`
- Produces: `build_asuka_weapon_mode_schedule(values) -> schedule`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

```python
def test_emergency_repair_dumps_her_magazine_for_a_fixed_reload():
    schedule = build_asuka_weapon_mode_schedule(VALUES)

    (segment,) = schedule(_Context([20.0]), 180.0)

    # "Reload speed is fixed at a 60% increase" (slot _08).
    assert segment["start"] == pytest.approx(20.0)
    assert segment["end"] == pytest.approx(
        20.0 + reload_time_with_speed(VALUES["caster_weapon_stats"]["reload_time"], 0.60))
    assert segment["profile"]["damage_percent"] == 0.0


def test_emergency_repair_halves_her_own_heating_speed_for_three_seconds():
    registry = EffectRegistry()
    context = SquadContext([SquadMember(SLUG, 3, "Wind", "MG")])
    rules = build_asuka_rules_including_emergency_repair(VALUES)

    fire_trigger(rules, "own_burst_activate", context, SLUG, 20.0, registry)

    target = {"slug": SLUG, "element": "Wind"}
    assert registry.total_for("mg_heating_speed_percent", target, 22.9) == pytest.approx(-1.0)
    assert registry.total_for("mg_heating_speed_percent", target, 23.1) == pytest.approx(0.0)
```

두 번째 테스트의 규칙 빌더 이름은 그녀의 기존 빌더 구조에 맞춘다 — 새 빌더를 만들지 말고 **기존 규칙 리스트에 불릿을 더한다**.

- [ ] **Step 2: 실패를 확인한다**

Run: `cd backend && python -m pytest tests/test_skill_rules_asuka_shikinami_langley_wille.py -v`

- [ ] **Step 3: 세그먼트 빌더를 구현한다**

```python
def build_asuka_weapon_mode_schedule(values):
    """Emergency Repair's "Removes 100% of ammo" (slot _05), as a segment that
    fires nothing. Its length is her own reload under the same bullet's "Reload
    speed is fixed at a 60% increase" (slot _08) - "fixed" overrides whatever
    else is live, so it is derived from that value alone.

    The segment ends by starting a fresh magazine, which re-arms her warm-up -
    and that new ramp is the one Effect 1's heating debuff slows down. The two
    halves of this skill meet on the same instant.
    """
    repair = values["emergency_repair"]
    fixed_reload_speed = float(repair["description_value_08"]) / 100
    weapon_stats = values["caster_weapon_stats"]
    reload_seconds = reload_time_with_speed(weapon_stats["reload_time"], fixed_reload_speed)
    weapon = weapon_stats["weapon"]

    def schedule(context, fight_duration):
        segments = []
        for burst_time in context.burst_times.get("asuka-shikinami-langley-wille", []):
            if burst_time >= fight_duration:
                continue
            segments.append({
                "start": burst_time,
                "end": min(burst_time + reload_seconds, fight_duration),
                "profile": {
                    "weapon": weapon,
                    "damage_percent": 0.0,
                    "rate_of_fire": 1.0 / (reload_seconds * 2),
                },
            })
        return segments

    return schedule
```

- [ ] **Step 4: 예열 디버프를 그녀의 기존 규칙에 더한다**

```python
        # Effect 1: "MG heating up speed down 100% for 3 sec" (slots _03/_04).
        # Negative, because a down arrow subtracts.
        buff_rule("own_burst_activate", [
            ("mg_heating_speed_percent",
             -float(repair["description_value_03"]) / 100, "self",
             float(repair["description_value_04"])),
        ]),
```

- [ ] **Step 5: 레지스트리에 등록한다**

`registry.py:50-52`의 asuka import 블록에 `build_asuka_weapon_mode_schedule`을 더하고, `_WEAPON_MODE_SCHEDULE_BUILDERS`에 더한다:

```python
    "asuka-shikinami-langley-wille": lambda sv: build_asuka_weapon_mode_schedule(sv),  # Emergency Repair's ammo dump
```

세그먼트 유닛이 셋 늘었으므로, 여기서 겹침 행렬 스크립트를 돌린다 — 자기 독스트링이 「새 변형 유닛을 인코딩할 때 돌리라」고 지시한다:

Run: `cd backend && python -m pytest tests/test_weapon_mode_collectible.py -q && python ../scripts/check_transform_window_overlap.py`
Expected: 예외 보고 0건.

- [ ] **Step 6: 독스트링을 고친다**

`Not modeled / deferred:` 의 아래 줄을 고친다:

```
- Emergency Repair's heating speed / ammo removal / HP recovery / reload speed
  effects: HP and bookkeeping, not damage - not consumed by the engine ...
```

→ HP 회복만 남기고, 나머지 셋은 `Modeled` 절로 옮겨 적는다. **이 문장이 셋을 「딜이 아니다」로 잘못 묶고 있었다는 것이 이 작업의 출발점이다.**

- [ ] **Step 7: 테스트 통과 + 가드 제거 확인**

Run: `cd backend && python -m pytest tests/test_skill_rules_asuka_shikinami_langley_wille.py -v`
그 다음 예열 값의 음수 부호를 지우고 돌려 `test_emergency_repair_halves_her_own_heating_speed_for_three_seconds`가 FAIL하는지 본다 — **부호 오류는 값 검증을 전부 통과한다.**

- [ ] **Step 8: 전체 스위트**

Run: `cd backend && python -m pytest -q`

- [ ] **Step 9: 커밋**

```bash
git add backend/app/skill_rules/asuka_shikinami_langley_wille.py backend/app/skill_rules/registry.py backend/tests/test_skill_rules_asuka_shikinami_langley_wille.py
git commit -m "아스카의 Emergency Repair 탄약 제거와 예열 감속을 인코딩한다"
```

---

### Task 8: 측정과 문서

**Files:**
- Modify: `docs/engine-gaps.md`, `docs/encoded-nikkes.md`, `docs/roadmap.md`

**Interfaces:**
- Consumes: Task 1~7의 결과
- Produces: 없음

- [ ] **Step 1: 실기록 캘리브레이션을 잰다**

Run: `cd backend && python ../scripts/measure_record_calibration.py`

아스카와 레이가 덱3에 앉아 있어 움직인다. **방향을 예측하지 말고 나온 값을 적는다.** 무기군 표(특히 MG)도 같이 기록한다.

- [ ] **Step 2: 스윕으로 유닛별 델타를 잰다**

질·라플라스UH·그레이브·아스카 넷의 고정 셸 델타를 잰다. **그레이브는 스쿼드 버프가 짧아졌으므로 그녀가 든 덱이 내려간다** — 그 크기를 따로 적는다.

- [ ] **Step 3: `docs/engine-gaps.md`를 정정한다**

적을 것:
- 갭 #11은 이미 닫혀 있었고 **카탈로그 누락**이 네 모듈을 막고 있었다는 것 ([[stale-defers-need-the-catalog-not-the-docstring]] 네 번째 사례)
- census 스크립트의 **두 함정**: 스코프 필터가 아스카를 삼켜 질과 짝이 갈라진 것, 그리고 `deferred_bullets()`가 보류 절 **뒤의** 절까지 담아 갭 통 95가 열린 갭 95가 아니라는 것(`laplace`의 `Modeled` 절이 갭으로 세어짐)
- 우선순위 표에서 **팬텀 base는 갭이 아니다** — 게임 교착이다
- MG 예열 속도 갭은 닫혔다
- 새 측정값

- [ ] **Step 4: `docs/encoded-nikkes.md`를 갱신한다**

질·라플라스UH·그레이브·아스카·레이 다섯의 보류 내역과 완성도 등급을 고친다.

- [ ] **Step 5: 커밋**

```bash
git add docs/
git commit -m "강제 재장전과 MG 예열 착륙 결과를 문서에 반영한다"
```

---

## Self-Review

**Spec coverage:** 설계문서의 A(카탈로그)=Task 1 · B 네 유닛=Task 2·3·4·7 · C 엔진=Task 5 · C 소비자=Task 6·7 · 검증=Task 8. 「이 설계가 다루지 않는 것」에 있는 항목(census 스크립트 수정, 벨벳, HP 회복, 밀크)은 어떤 Task도 건드리지 않는다.

**Placeholder scan:** 없음. 착수 시 확인이 필요한 세 곳은 명시했다 — `generate_magazine_shot_times`의 키워드 이름(Task 5 Step 1), `context.burst_used_this_cycle`의 실제 형태(Task 6 Step 1), 아스카 기존 규칙 빌더의 이름(Task 7 Step 1). 셋 다 「열어서 맞춘다」로 지시했고 값을 지어내지 않았다.

**Type consistency:** `build_*_weapon_mode_schedule(values) -> schedule(context, fight_duration) -> list[dict]` 이 네 유닛에서 동일. 세그먼트 dict 키는 `start`/`end`/`profile` (라플라스UH의 변형 세그먼트만 `until_shots`). `spinup_with_speed(spinup, heating_speed_percent, rate_of_fire)`가 Task 5에서 정의되고 Task 5 안에서만 호출된다. 스탯 이름 `mg_heating_speed_percent`가 Task 5·6·7에서 동일.
