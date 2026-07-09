from app.burst_cycle import FULL_BURST_DURATION
from app.effects import EffectRegistry
from app.skill_rules.arcana_fortune_mate import build_fortune_mate_rules, radiant_youth_burst_percent
from app.squad_engine import SquadContext, SquadMember, fire_trigger

# Real skill level 10 values from api.dotgg.gg.
RADIANT_YOUTH = {
    "description_value_01": "20.09",  # self Critical Rate %
    "description_value_02": "2",      # reloads (not modeled)
    "description_value_03": "29.99",  # self Attack Damage %
    "description_value_04": "554.4",  # burst nuke % of final ATK
}
MEMORIES_AND_MOMENTS = {
    "description_value_01": "6",      # deferred: Two-times reload count
    "description_value_02": "1",      # deferred: Four-times pellet count
    "description_value_03": "3",      # deferred: pellet stack cap
    "description_value_04": "2.49",   # deferred: Six-times ATK % per stack
    "description_value_05": "3",      # deferred: stack cap
    "description_value_06": "55",     # squad(approx) Attack Damage % on burst
    "description_value_07": "10",     # duration
}


def make_context():
    return SquadContext([
        SquadMember("arcana-fortune-mate", burst_tier=2, element="Fire"),
        SquadMember("ally", burst_tier=3, element="Wind"),
    ])


def build():
    return build_fortune_mate_rules({
        "radiant_youth": RADIANT_YOUTH,
        "memories_and_moments": MEMORIES_AND_MOMENTS,
    })


SELF_TARGET = {"slug": "arcana-fortune-mate", "element": "Fire"}
ALLY = {"slug": "ally", "element": "Wind"}


def test_burst_percent_is_5544():
    assert radiant_youth_burst_percent({"radiant_youth": RADIANT_YOUTH}) == 554.4


def test_radiant_youth_grants_self_crit_rate_and_attack_damage():
    # Isolate Radiant Youth's own rule (build()[0]) to check its effect alone -
    # Fortune Mate has a second own-burst rule (Memories and Moments' squad
    # approximation) that also lands on her, tested separately below.
    ctx = make_context()
    registry = EffectRegistry()
    fire_trigger("own_burst_activate", {"arcana-fortune-mate": [build()[0]]}, ctx, registry, time=5.0)

    assert round(registry.total_for("crit_rate", SELF_TARGET, now=5.0), 4) == 0.2009
    assert round(registry.total_for("attack_damage_up", SELF_TARGET, now=5.0), 4) == 0.2999
    assert registry.total_for("crit_rate", ALLY, now=5.0) == 0.0  # self-scoped

    # expires after the Full Burst window approximation
    later = 5.0 + FULL_BURST_DURATION + 0.1
    assert registry.total_for("crit_rate", SELF_TARGET, now=later) == 0.0


def test_memories_and_moments_grants_squad_attack_damage_on_burst():
    ctx = make_context()
    registry = EffectRegistry()
    fire_trigger("own_burst_activate", {"arcana-fortune-mate": [build()[1]]}, ctx, registry, time=5.0)

    assert round(registry.total_for("attack_damage_up", ALLY, now=5.0), 4) == 0.55
    assert registry.total_for("attack_damage_up", ALLY, now=15.1) == 0.0


def test_both_own_burst_rules_stack_on_fortune_mate_herself():
    # Documented approximation: the "except self" SG-ally buff is modeled as
    # squad scope (no weapon-type scope exists), so Fortune Mate also receives
    # it on top of her own Radiant Youth self buff - a small overstatement.
    ctx = make_context()
    registry = EffectRegistry()
    fire_trigger("own_burst_activate", {"arcana-fortune-mate": build()}, ctx, registry, time=5.0)

    assert round(registry.total_for("attack_damage_up", SELF_TARGET, now=5.0), 4) == 0.8499
