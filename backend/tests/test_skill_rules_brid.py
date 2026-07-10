from app.effects import EffectRegistry
from app.skill_rules.brid_silent_track import build_brid_rules
from app.squad_engine import SquadContext, SquadMember, fire_trigger

# Real skill level 10 values from api.dotgg.gg.
IGNITION_SEQUENCE = {
    "description_value_01": "15.12",  # Wind Code enemy Damage Taken % (not modeled)
    "description_value_02": "10",     # duration
    "description_value_03": "636",    # instant nuke % of final ATK
}
FULL_THROTTLE = {
    "description_value_01": "66.52",  # squad(approx) ATK % of caster's ATK
    "description_value_02": "10",     # duration
    "description_value_03": "0",      # unused slot
    "description_value_04": "10",     # unused slot
}


def make_context():
    return SquadContext([
        SquadMember("brid-silent-track", burst_tier=2, element="Fire"),
        SquadMember("ally", burst_tier=3, element="Wind"),
    ])


def build(caster_atk=10000):
    return build_brid_rules({
        "ignition_sequence": IGNITION_SEQUENCE,
        "full_throttle": FULL_THROTTLE,
        "caster_atk": caster_atk,
    })


ALLY = {"slug": "ally", "element": "Wind"}


def test_ignition_sequence_emits_an_instant_nuke_pulse_on_full_burst_enter():
    ctx = make_context()
    registry = EffectRegistry()
    fire_trigger("full_burst_enter", {"brid-silent-track": build()}, ctx, registry, time=5.0)

    pulses = registry.drain_pulses("instant_damage_percent")
    assert len(pulses) == 1
    assert pulses[0].value == 636.0
    assert pulses[0].source_slug == "brid-silent-track"


def test_full_throttle_grants_squad_atk_on_own_burst():
    ctx = make_context()
    registry = EffectRegistry()
    fire_trigger("own_burst_activate", {"brid-silent-track": build()}, ctx, registry, time=5.0)

    # 66.52% of caster ATK 10000 = 6652, for 10 sec.
    assert registry.total_for("flat_atk", ALLY, now=5.0) == 6652.0
    assert registry.total_for("flat_atk", ALLY, now=15.1) == 0.0
