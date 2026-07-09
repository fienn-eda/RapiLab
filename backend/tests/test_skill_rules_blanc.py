from app.effects import EffectRegistry
from app.skill_rules.blanc import build_blanc_rules
from app.squad_engine import SquadContext, SquadMember, fire_trigger

# Real skill level 10 values from api.dotgg.gg.
SHOWTIME = {
    "description_value_01": "3.84",   # heal (not modeled)
    "description_value_02": "8",
    "description_value_03": "1",
    "description_value_04": "10",
    "description_value_05": "31.68",  # lowest-HP ally Max HP (not modeled)
    "description_value_06": "10",
    "description_value_07": "39.26",  # enemy Damage Taken %
    "description_value_08": "10",
}
RABBIT_TWINS_W = {
    "description_value_01": "3.68",   # heal (not modeled)
    "description_value_02": "5",
    "description_value_03": "40.76",  # self Burst cooldown reduction sec
}


def build():
    return build_blanc_rules({"showtime": SHOWTIME, "rabbit_twins_w": RABBIT_TWINS_W})


def deck_with(*extra_slugs):
    members = [
        SquadMember("blanc", burst_tier=2, element="Wind"),
        SquadMember("dealer", burst_tier=3, element="Fire"),
    ]
    members += [SquadMember(s, burst_tier=1, element="Fire") for s in extra_slugs]
    return SquadContext(members)


DEALER = {"slug": "dealer", "element": "Fire"}


def test_showtime_applies_squad_damage_taken_debuff():
    ctx = deck_with()
    registry = EffectRegistry()
    fire_trigger("own_burst_activate", {"blanc": build()}, ctx, registry, time=5.0)

    # 39.26% enemy Damage Taken, modeled squad-scoped for 10 sec.
    assert round(registry.total_for("damage_taken_up", DEALER, now=5.0), 4) == 0.3926
    assert registry.total_for("damage_taken_up", DEALER, now=15.1) == 0.0


def test_self_cdr_only_fires_with_a_squad_twin_present():
    # Rabbit Twins W's cooldown reduction needs Rouge or Noir in the deck.
    without_twin = deck_with()
    registry = EffectRegistry()
    fire_trigger("full_burst_end", {"blanc": build()}, without_twin, registry, time=15.0)
    assert registry.drain_pulses("burst_cooldown_reduction_sec") == []

    with_twin = deck_with("rouge")
    registry = EffectRegistry()
    fire_trigger("full_burst_end", {"blanc": build()}, with_twin, registry, time=15.0)
    pulses = registry.drain_pulses("burst_cooldown_reduction_sec")
    assert len(pulses) == 1
    assert pulses[0].value == 40.76
    assert pulses[0].scope == "self"        # reduces only Blanc's cooldown
    assert pulses[0].source_slug == "blanc"


def test_self_cdr_also_fires_with_noir():
    ctx = deck_with("noir")
    registry = EffectRegistry()
    fire_trigger("full_burst_end", {"blanc": build()}, ctx, registry, time=15.0)
    assert len(registry.drain_pulses("burst_cooldown_reduction_sec")) == 1
