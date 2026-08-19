"""Which charge-weapon Nikkes have had their fire-to-charge delay settled?

Why this exists: a charge weapon (SR/RL) may or may not pause between firing a
charged shot and starting the next charge, and it is a property of the UNIT, not
of the weapon class - Liberalio and Neon have none, Snow White has 0.4 sec. The
engine defaults to none, so a unit nobody has checked is silently modelled as
having no pause, and its damage comes out too high by however long the pause
really is. Mint was reading 1.502x of her recorded damage for exactly that
reason.

So "no delay registered" has two very different meanings - checked and found to
have none, or never checked - and this script separates them. Run it after
encoding any SR/RL Nikke.

An unchecked unit no longer sits at zero: she carries the frame-resolved 22
frames Bready and Centi share (registry.ASSUMED_CHARGE_MOTION_DELAY_SECONDS),
which is a better guess than "no pause at all" but is still a guess - the real
values run 0.34 to 0.43 and four units have none. So `assumed`, `inferred` and
`UNVERIFIED` are questions for Fienn, and the exit code stays non-zero while any
of them is non-empty.

`stand-in (accepted)` is the one untimed status that is NOT a question. Those
units were scored across the whole range of real delays and their damage barely
moved (scripts/measure_charge_delay_sensitivity.py, all under 2% and most under
1%, against an allocation search whose own spread is +-5%), so the stand-in is
their answer rather than a placeholder. Keeping them red would leave this audit
red forever, and an audit that is always red stops being read.

`inferred` is a zero nobody watched: the four units confirmed to have no pause
are exactly the four whose `shot_detail.rate_of_fire` beats the charge class's
60 rounds/min, and Cinderella is the fifth unit with such a rate of fire
(attack_rate.CHARGE_ROUNDS_PER_MINUTE). That reading is what her old "pause" of
10/29 sec really was - her weapon's 180 rounds/min showing through once her
charge hit zero - but it is an inference from a table, not a clock on her.

How Fienn times one (see docs/insights.md): read the Full Burst clock at the
instant the charged bullet leaves and again when the next charge gauge starts
filling. NOT the gap between damage numbers - an RL grenade's travel time varies
with distance and contaminates those. The reading checks itself: shot-to-shot
gap must come out as charge time + delay.

Usage (any cwd):
    python3 scripts/audit_charge_motion_delay.py
    python3 scripts/audit_charge_motion_delay.py --all   # include non-charge weapons
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.attack_rate import charge_interval_floor_for  # noqa: E402
from app.skill_rules.registry import (  # noqa: E402
    INFERRED_NO_CHARGE_MOTION_DELAY,
    NO_CHARGE_MOTION_DELAY,
    STAND_IN_ACCEPTED_CHARGE_MOTION_DELAY,
    TIMED_CHARGE_MOTION_DELAY,
    _BUILDERS,
    get_charge_motion_delay,
    get_manual_tap_fire_interval,
)

CHARGE_WEAPONS = ("SR", "RL")


def _weapon(slug):
    """The unit's weapon class from collected data, or None if not collected.

    A MODE_VARIANTS slug (`cinderella-crystal-wave-mg`) has no file of its own,
    so fall back to the longest base slug that does.
    """
    for candidate in _base_candidates(slug):
        for source in ("lootandwaifus", "dotgg"):
            path = ROOT / "data" / source / f"char_{candidate}.json"
            if path.exists():
                weapon = json.loads(path.read_text(encoding="utf-8")).get("weapon")
                if weapon:
                    return weapon
    return None


def _base_candidates(slug):
    parts = slug.split("-")
    for cut in range(len(parts), 0, -1):
        yield "-".join(parts[:cut])


def status_for(slug):
    """Which of the six answers this unit has about her fire-to-charge pause."""
    if slug in TIMED_CHARGE_MOTION_DELAY:
        return "TIMED"
    if slug in NO_CHARGE_MOTION_DELAY:
        return "none (confirmed)"
    if slug in INFERRED_NO_CHARGE_MOTION_DELAY:
        return "none (inferred)"
    if slug in STAND_IN_ACCEPTED_CHARGE_MOTION_DELAY:
        return "stand-in (accepted)"
    if get_charge_motion_delay(slug):
        return "assumed"
    return "UNVERIFIED"


def is_unanswered(status):
    """Whether this status is still a question for Fienn - what the exit code is.

    `stand-in (accepted)` is NOT one. Those units were measured to barely depend
    on the value (registry.STAND_IN_ACCEPTED_CHARGE_MOTION_DELAY), so the
    stand-in is their answer and keeping them red would make the whole audit red
    forever - which is how a tool stops being read.
    """
    return status in ("UNVERIFIED", "assumed", "none (inferred)")


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--all", action="store_true",
                   help="list every encoded unit, not only the charge weapons")
    args = p.parse_args()

    rows = []
    for slug in sorted(_BUILDERS):
        weapon = _weapon(slug)
        if not args.all and weapon not in CHARGE_WEAPONS:
            continue
        status = status_for(slug)
        # 톡톡이로 모델하는 유닛은 무기의 연사가 아니라 플레이어의 손이 바닥값을
        # 정한다. 그 floor를 안 보여주면 「멈춤 0」 행이 「아무 것에도 안 걸린다」로
        # 읽히는데, 실제로는 차지가 짧아진 구간에서 그 손이 상한을 만든다.
        floor = get_manual_tap_fire_interval(slug) or charge_interval_floor_for(slug)
        rows.append((status, slug, weapon or "?", get_charge_motion_delay(slug), floor))

    order = {"TIMED": 0, "assumed": 1, "stand-in (accepted)": 2,
             "none (confirmed)": 3, "none (inferred)": 4, "UNVERIFIED": 5}
    print(f"{'status':<19} {'unit':<38} {'wpn':<4} {'delay':>6} {'floor':>7}")
    for status, slug, weapon, delay, floor in sorted(rows, key=lambda r: (order[r[0]], r[1])):
        shown = f"{floor:.3f}" if floor is not None else "-"
        print(f"{status:<19} {slug:<38} {weapon:<4} {delay:>6.2f} {shown:>7}")

    accepted = [r for r in rows if r[0] == "stand-in (accepted)"]
    print(f"\n{len(rows)} charge-weapon units: "
          f"{sum(1 for r in rows if r[0] == 'TIMED')} timed, "
          f"{sum(1 for r in rows if r[0] == 'assumed')} assumed, "
          f"{len(accepted)} stand-in accepted, "
          f"{sum(1 for r in rows if r[0] == 'none (confirmed)')} confirmed none, "
          f"{sum(1 for r in rows if r[0] == 'none (inferred)')} inferred none, "
          f"{sum(1 for r in rows if r[0] == 'UNVERIFIED')} UNVERIFIED")
    if accepted:
        print(f"\n{len(accepted)} units keep the stand-in as their answer - measuring them")
        print("was scored and would not move a recommendation "
              "(scripts/measure_charge_delay_sensitivity.py).")
    unanswered = [r for r in rows if is_unanswered(r[0])]
    if unanswered:
        # Only explain the statuses actually present - a note about `assumed`
        # rows when there are none reads as a finding rather than as boilerplate.
        open_statuses = {r[0] for r in unanswered}
        print("\nASK FIENN whether these pause between a charged shot and the next charge.")
        if "assumed" in open_statuses:
            print("An `assumed` row is carrying a stand-in, not an answer - it is still wrong")
            print("for whoever turns out to have no pause at all, as four checked units do.")
        if "none (inferred)" in open_statuses:
            print("An `inferred` row is a zero read off the rate-of-fire table, not a clock.")
        if "UNVERIFIED" in open_statuses:
            print("An `UNVERIFIED` row is modelled with no pause at all because nobody looked.")
        print("   " + ", ".join(sorted(r[1] for r in unanswered)))
    return 1 if unanswered else 0


if __name__ == "__main__":
    sys.exit(main())
