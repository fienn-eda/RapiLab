"""Normalize a raw ShiftyPad bundle into the dotgg file shape.

A raw bundle is {"directory": <public directory entry>, "detail": <character
detail payload>} as dumped by collect.js --nikke. dotgg stores a unit's weapon
stats and per-level skill slots in one file; producing that exact shape lets
every downstream parser (skill_values.dotgg_slots, user_roster._weapon_stats,
the meta reads) be reused unchanged. The fixed-point conventions match dotgg's:
ShiftyPad stores damage/charge as hundredths of a percent and times as
centiseconds; dotgg stores "5.57%" strings and 2.5-second floats.

Pure function: no I/O. The collector fetches; the parity harness proves this
output equals the committed dotgg ground truth field for field.

Only the burst skill (skills[2]) carries a `cooldown` key, matching dotgg:
ShiftyPad's skill1_detail/skill2_detail report `skill_cooltime: None` (the
engine's active-skill cooldowns aren't exposed via this API), and
user_roster.py's loader only ever reads meta["skills"][2]["cooldown"] at
load time. An encoder who needs skill1/2 cooldowns reads them from the game
UI directly; this normalizer must not fabricate them.
"""

# ShiftyPad's element names mostly match dotgg's; "Electronic" is the one
# exception (dotgg/the engine's elements.py call it "Electric") and must be
# mapped or element-advantage lookups silently no-op for electric-code units.
_ELEMENT_NAMES = {"Electronic": "Electric"}

# ShiftyPad reports an all-stage unit's burst as "AllStep" instead of a tier.
# The engine seats a unit at exactly one tier, so the tier to record is the one
# the unit is actually played at. Red Hood - the only AllStep unit among all 196
# released nikkes (checked against the live directory 2026-07-26) - can burst at
# any stage, but Steps 1 and 2 come with conditions and Step 3 does not, so she
# is used as a B3 (Fienn, 2026-07-26). dotgg and lootandwaifus both record her
# as "3" for the same reason, which keeps the parity harness meaningful.
#
# Deliberately a table, not a fallback: an unrecognised burst string still
# raises rather than being guessed into a tier.
_BURST_TIERS = {"AllStep": "3"}


def _pct(hundredths):
    """6130 -> "61.3%" (dotgg's percent-string convention)."""
    return f"{hundredths / 100:g}%"


def _sec(centiseconds):
    """250 -> 2.5 (dotgg's seconds float)."""
    return centiseconds / 100


def _burst_tier(use_burst_skill):
    """"Step3" -> "3", "AllStep" -> the tier that unit is actually played at."""
    if use_burst_skill in _BURST_TIERS:
        return _BURST_TIERS[use_burst_skill]
    return str(int(use_burst_skill.removeprefix("Step")))


def _skill_levels(skill_detail):
    """Transpose ShiftyPad's slot[level] into dotgg's levels[level][slot].

    description_value_list is a list of slots, each {"description_value":
    [<level1>, <level2>, …]}. Some slots are unused and come back as `{}`
    (no "description_value" key at all) -- ShiftyPad's own dotgg_slots
    convention for "no value here" is an empty string, so those slots
    produce "" at every level rather than being dropped; downstream
    dotgg_slots() already filters out `""` values. dotgg stores a list of
    levels, each a dict of description_value_NN. The number of levels is
    the longest slot array's length.
    """
    slots = [s.get("description_value", []) for s in skill_detail["description_value_list"]]
    num_levels = max((len(slot) for slot in slots), default=0)
    levels = []
    for lvl in range(num_levels):
        levels.append(
            {
                f"description_value_{i + 1:02d}": (slot[lvl] if lvl < len(slot) else "")
                for i, slot in enumerate(slots)
            }
        )
    return levels


def normalize_shiftypad(bundle):
    directory, detail = bundle["directory"], bundle["detail"]
    shot = detail["shot_detail"]
    element = directory["element_id"]["element"]["element"]
    skills = [
        {"levels": _skill_levels(detail["skill1_detail"])},
        {"levels": _skill_levels(detail["skill2_detail"])},
        {
            "cooldown": _sec(detail["ulti_skill_detail"]["skill_cooltime"]),
            "levels": _skill_levels(detail["ulti_skill_detail"]),
        },
    ]
    return {
        "weapon": directory["shot_id"]["element"]["weapon_type"],
        "maxAmmo": int(shot["max_ammo"]),
        "damage": _pct(shot["damage"]),
        "reloadTime": _sec(shot["reload_time"]),
        "chargeTime": _sec(shot["charge_time"]),
        "chargeDamage": _pct(shot["full_charge_damage"]),
        "element": _ELEMENT_NAMES.get(element, element),
        "burst": _burst_tier(directory["use_burst_skill"]),
        "skills": skills,
    }
