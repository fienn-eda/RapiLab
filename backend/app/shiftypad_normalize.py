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
"""


def _pct(hundredths):
    """6130 -> "61.3%" (dotgg's percent-string convention)."""
    return f"{hundredths / 100:g}%"


def _sec(centiseconds):
    """250 -> 2.5 (dotgg's seconds float)."""
    return centiseconds / 100


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
        "element": directory["element_id"]["element"]["element"],
        "burst": int(directory["use_burst_skill"].removeprefix("Step")),
        "skills": skills,
    }
