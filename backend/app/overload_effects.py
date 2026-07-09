"""Converts ShiftyPad overload option values into permanent, self-scoped Effects.

Fienn confirmed overload values are additive on top of the base stat shown
in the character info tab (not already folded in), so these are modeled as
ordinary percentage-bonus Effects with duration=None (always active).

Some overload stats (crit rate, charge speed, max ammo) have no consumer yet
because the attack-rate model they'd feed into doesn't exist. They're still
named and converted so nothing is silently dropped before that model exists.
"""
from app.effects import Effect

NAME_TO_STAT = {
    "공격력 증가": "atk_percent",
    "우월코드 대미지 증가": "other_elemental_bonus",
    "크리티컬 대미지 증가": "other_critical_damage_sources",
    "크리티컬 확률 증가": "crit_rate",
    "차지 대미지 증가": "charge_damage_bonus",
    "차지 속도 증가": "charge_speed_percent",
    "최대 장탄 수 증가": "max_ammo_percent",
}


def overload_options_to_effects(overload_options, source_slug):
    effects = []
    for option in overload_options:
        stat = NAME_TO_STAT.get(option.name)
        if stat is None:
            raise ValueError(f"unknown overload option: {option.name}")
        effects.append(
            Effect(
                stat=stat,
                value=option.value / 100,
                scope="self",
                duration=None,
                source_slug=source_slug,
            )
        )
    return effects
