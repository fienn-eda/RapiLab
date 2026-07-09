"""Converts an equipped PVE cube's stats into permanent, self-scoped Effects.

Like overload options, cube bonuses are always-on (duration=None) buffs on
the wearer. Only the stats that affect raid DPS output are mapped; a cube's
other stats (e.g. HP potency) aren't modeled. "Superior Code Damage" is the
advantageous-element damage bonus, the same stat overload's "우월코드 대미지"
maps to (other_elemental_bonus).
"""
from app.effects import Effect


def cube_to_effects(
    name,
    source_slug,
    reload_speed_percent=None,
    superior_code_damage_percent=None,
):
    effects = []
    if reload_speed_percent is not None:
        effects.append(
            Effect("reload_speed_percent", reload_speed_percent / 100, "self", None, source_slug)
        )
    if superior_code_damage_percent is not None:
        effects.append(
            Effect("other_elemental_bonus", superior_code_damage_percent / 100, "self", None, source_slug)
        )
    return effects
