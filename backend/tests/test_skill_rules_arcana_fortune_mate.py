from app.burst_cycle import FULL_BURST_DURATION
from app.effects import EffectRegistry
from app.skill_rules.arcana_fortune_mate import build_fortune_mate_rules, radiant_youth_burst_percent
from app.squad_engine import SquadContext, SquadMember, fire_trigger

CASTER_ATK = 80000.0

# Real skill level 10 values from api.dotgg.gg.
KEEPSAKE_ALBUM = {
    "description_value_01": "13",     # squad(approx) flat ATK = 13% of caster ATK PER Precious Moments stack
    "description_value_02": "15",     # its duration
    "description_value_03": "10",     # deferred: Snapshots Normal Attack Damage Multiplier %
    "description_value_04": "3",      # deferred: Snapshots stack cap
}
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
    "description_value_04": "2.49",   # Six-times Precious Moments self ATK % per stack
    "description_value_05": "3",      # Precious Moments stack cap
    "description_value_06": "55",     # squad(approx) Attack Damage % on burst
    "description_value_07": "10",     # duration
}


def make_context():
    return SquadContext([
        SquadMember("arcana-fortune-mate", burst_tier=2, element="Fire", weapon="SG"),
        SquadMember("ally", burst_tier=3, element="Wind", weapon="AR"),
        SquadMember("sg-ally", burst_tier=1, element="Iron", weapon="SG"),
    ])


def build():
    return build_fortune_mate_rules({
        "radiant_youth": RADIANT_YOUTH,
        "memories_and_moments": MEMORIES_AND_MOMENTS,
        "keepsake_album": KEEPSAKE_ALBUM,
        "caster_atk": CASTER_ATK,
    })


def run_cycle(rules, ctx, registry, burst_time):
    """One burst cycle for arcana: her tier-2 burst, then Full Burst enter/end."""
    fire_trigger("own_burst_activate", rules, ctx, registry, burst_time)
    fire_trigger("full_burst_enter", rules, ctx, registry, burst_time + 1.0)
    fire_trigger("full_burst_end", rules, ctx, registry, burst_time + 10.0)


SELF_TARGET = {"slug": "arcana-fortune-mate", "element": "Fire"}
ALLY = {"slug": "ally", "element": "Wind"}
SG_ALLY = {"slug": "sg-ally", "element": "Iron"}


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


def test_memories_and_moments_grants_sg_allies_attack_damage_on_burst():
    ctx = make_context()
    registry = EffectRegistry()
    fire_trigger("own_burst_activate", {"arcana-fortune-mate": [build()[1]]}, ctx, registry, time=5.0)

    # "all shotgun-wielding allies (except self)" - exact scope via the
    # gap #3 member filter: SG ally yes, AR ally no, Fortune Mate herself no.
    assert round(registry.total_for("attack_damage_up", SG_ALLY, now=5.0), 4) == 0.55
    assert registry.total_for("attack_damage_up", SG_ALLY, now=15.1) == 0.0
    assert registry.total_for("attack_damage_up", ALLY, now=5.0) == 0.0
    assert registry.total_for("attack_damage_up", SELF_TARGET, now=5.0) == 0.0


def test_own_burst_grants_self_only_radiant_youth_attack_damage():
    # The "except self" SG-ally buff no longer lands on Fortune Mate herself
    # (was a documented squad-approx overstatement before the gap #3 filter).
    ctx = make_context()
    registry = EffectRegistry()
    fire_trigger("own_burst_activate", {"arcana-fortune-mate": build()}, ctx, registry, time=5.0)

    assert round(registry.total_for("attack_damage_up", SELF_TARGET, now=5.0), 4) == 0.2999


def test_precious_moments_self_atk_ramps_one_stack_per_cycle():
    ctx = make_context()
    registry = EffectRegistry()
    rules = {"arcana-fortune-mate": build()}

    run_cycle(rules, ctx, registry, burst_time=5.0)
    assert round(registry.total_for("atk_percent", SELF_TARGET, now=6.0), 4) == 0.0249  # 1 stack
    run_cycle(rules, ctx, registry, burst_time=45.0)
    assert round(registry.total_for("atk_percent", SELF_TARGET, now=46.0), 4) == 0.0498  # 2 stacks
    run_cycle(rules, ctx, registry, burst_time=85.0)
    assert round(registry.total_for("atk_percent", SELF_TARGET, now=86.0), 4) == 0.0747  # 3 stacks
    # caps at 3: a fourth cycle adds nothing
    run_cycle(rules, ctx, registry, burst_time=125.0)
    assert round(registry.total_for("atk_percent", SELF_TARGET, now=126.0), 4) == 0.0747
    # self-scoped: allies never get Precious Moments
    assert registry.total_for("atk_percent", ALLY, now=126.0) == 0.0


def test_precious_moments_requires_making_memories():
    # No burst this cycle -> no Making Memories -> Full Burst enter grants no stack.
    ctx = make_context()
    registry = EffectRegistry()
    rules = {"arcana-fortune-mate": build()}
    fire_trigger("full_burst_enter", rules, ctx, registry, time=6.0)
    assert registry.total_for("atk_percent", SELF_TARGET, now=6.0) == 0.0


def test_keepsake_album_sg_atk_scales_with_precious_moments_stacks():
    ctx = make_context()
    registry = EffectRegistry()
    rules = {"arcana-fortune-mate": build()}

    # cycle 1: 1 Precious Moments stack -> flat ATK = 13% of caster ATK x 1, for
    # 15 sec, on shotgun wielders only (Fortune Mate herself is SG and included).
    run_cycle(rules, ctx, registry, burst_time=5.0)
    assert round(registry.total_for("flat_atk", SG_ALLY, now=15.0), 4) == round(0.13 * CASTER_ATK, 4)
    assert round(registry.total_for("flat_atk", SELF_TARGET, now=15.0), 4) == round(0.13 * CASTER_ATK, 4)
    assert registry.total_for("flat_atk", ALLY, now=15.0) == 0.0  # AR ally excluded
    assert registry.total_for("flat_atk", SG_ALLY, now=30.1) == 0.0  # 15s from full_burst_end (t=15)

    # cycle 3: 3 stacks -> 13% x 3
    run_cycle(rules, ctx, registry, burst_time=45.0)
    run_cycle(rules, ctx, registry, burst_time=85.0)
    assert round(registry.total_for("flat_atk", SG_ALLY, now=95.0), 4) == round(0.13 * CASTER_ATK * 3, 4)
