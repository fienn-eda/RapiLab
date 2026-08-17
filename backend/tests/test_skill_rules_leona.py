"""Leona - a Burst-2 Water SG supporter built around Roar, a 5-stack squad
Critical Rate counter her own shots fill."""
from app.attack_rate import generate_shot_times
from app.effects import EffectRegistry
from app.skill_rules.leona import (
    ROAR_SHOT_COUNT,
    build_leona_resources,
    build_leona_rules,
    build_lions_heart_resource_gated_buffs,
)
from app.squad_engine import SquadContext, SquadMember, fire_trigger

# ShiftyPad native slots (data/shiftypad/leona.json, level 10).
THUNDEROUS_ROAR = {
    "description_value_01": "5", "description_value_02": "2.62",
    "description_value_03": "5", "description_value_04": "5",
    "description_value_05": "15", "description_value_06": "20",
    "description_value_07": "10",
}
COURAGEOUS_LOOK = {
    "description_value_01": "20.28", "description_value_02": "10",
    "description_value_03": "2", "description_value_04": "5",
    "description_value_05": "10",
}
LIONS_HEART = {
    "description_value_01": "34.64", "description_value_02": "10",
    "description_value_03": "21.32", "description_value_04": "10",
}
LEONA = {
    "thunderous_roar": THUNDEROUS_ROAR,
    "courageous_look": COURAGEOUS_LOOK,
    "lions_heart": LIONS_HEART,
}

SELF = {"slug": "leona", "element": "Water"}
SHOTGUN_ALLY = {"slug": "shotgun-ally", "element": "Fire"}
RIFLE_ALLY = {"slug": "rifle-ally", "element": "Iron"}


def _ctx():
    return SquadContext([
        SquadMember("leona", burst_tier=2, element="Water", weapon="SG"),
        SquadMember("shotgun-ally", burst_tier=3, element="Fire", weapon="SG"),
        SquadMember("rifle-ally", burst_tier=1, element="Iron", weapon="AR"),
    ])


def test_courageous_look_gives_the_squad_hit_rate_on_full_burst_enter():
    reg = EffectRegistry()
    fire_trigger("full_burst_enter", {"leona": build_leona_rules(LEONA)}, _ctx(), reg, 12.0)
    assert round(reg.total_for("hit_rate", RIFLE_ALLY, 12.0), 4) == 0.2028
    assert round(reg.total_for("hit_rate", SELF, 21.9), 4) == 0.2028
    assert reg.total_for("hit_rate", SELF, 22.1) == 0.0  # 10 sec


def test_the_pellet_bonus_reaches_the_two_highest_atk_shotgun_allies():
    """Pellet count moves no damage directly (measured on Arcana: Fortune Mate),
    but it feeds Dorothy: Serendipity's Flash counter, whose procs do - so the
    targeting has to be the text's: shotguns AND top-2, not either alone."""
    reg = EffectRegistry()
    fire_trigger("full_burst_enter", {"leona": build_leona_rules(LEONA)}, _ctx(), reg, 12.0)
    assert reg.total_for("pellet_count_bonus", SHOTGUN_ALLY, 12.0) == 5.0
    assert reg.total_for("pellet_count_bonus", SELF, 12.0) == 5.0  # only 2 shotguns here
    assert reg.total_for("pellet_count_bonus", RIFLE_ALLY, 12.0) == 0.0
    assert reg.total_for("pellet_count_bonus", SHOTGUN_ALLY, 22.1) == 0.0  # 10 sec


def test_a_third_shotgun_does_not_widen_the_pellet_bonus():
    """The bullet names TWO shotgun allies, so with three in the deck the
    lowest-ATK one misses out - approximating this as "every shotgun ally"
    would speed up a Flash counter the game never touched."""
    ctx = SquadContext(
        [
            SquadMember("leona", burst_tier=2, element="Water", weapon="SG"),
            SquadMember("shotgun-ally", burst_tier=3, element="Fire", weapon="SG"),
            SquadMember("third-shotgun", burst_tier=1, element="Wind", weapon="SG"),
        ],
        base_atk={"leona": 50000, "shotgun-ally": 90000, "third-shotgun": 10000},
    )
    reg = EffectRegistry()
    fire_trigger("full_burst_enter", {"leona": build_leona_rules(LEONA)}, ctx, reg, 12.0)
    third = {"slug": "third-shotgun", "element": "Wind"}
    assert reg.total_for("pellet_count_bonus", SHOTGUN_ALLY, 12.0) == 5.0   # 90k
    assert reg.total_for("pellet_count_bonus", SELF, 12.0) == 5.0           # 50k, she competes
    assert reg.total_for("pellet_count_bonus", third, 12.0) == 0.0          # 10k, cut


def test_leona_competes_for_her_own_two_slots():
    """Her bullet carries no "except caster" clause, so she is in the pool from
    the start whenever she meets its conditions - and she does, being a shotgun
    (Fienn, 2026-08-08). Two shotguns outranking her push her out; that is the
    ranking working, not an exclusion rule."""
    ctx = SquadContext(
        [
            SquadMember("leona", burst_tier=2, element="Water", weapon="SG"),
            SquadMember("shotgun-ally", burst_tier=3, element="Fire", weapon="SG"),
            SquadMember("second-shotgun", burst_tier=1, element="Iron", weapon="SG"),
        ],
        base_atk={"leona": 50000, "shotgun-ally": 90000, "second-shotgun": 80000},
    )
    reg = EffectRegistry()
    fire_trigger("full_burst_enter", {"leona": build_leona_rules(LEONA)}, ctx, reg, 12.0)
    second = {"slug": "second-shotgun", "element": "Iron"}
    assert reg.total_for("pellet_count_bonus", SHOTGUN_ALLY, 12.0) == 5.0
    assert reg.total_for("pellet_count_bonus", second, 12.0) == 5.0
    assert reg.total_for("pellet_count_bonus", SELF, 12.0) == 0.0  # outranked, not excluded


def test_the_pellet_bonus_stays_on_her_alone_with_no_other_shotgun():
    """The only shotgun in the deck is her own, so both slots have one
    candidate and the rifle ally never qualifies."""
    ctx = SquadContext(
        [
            SquadMember("leona", burst_tier=2, element="Water", weapon="SG"),
            SquadMember("rifle-ally", burst_tier=3, element="Iron", weapon="AR"),
        ],
        base_atk={"leona": 50000, "rifle-ally": 90000},
    )
    reg = EffectRegistry()
    fire_trigger("full_burst_enter", {"leona": build_leona_rules(LEONA)}, ctx, reg, 12.0)
    assert reg.total_for("pellet_count_bonus", SELF, 12.0) == 5.0
    assert reg.total_for("pellet_count_bonus", RIFLE_ALLY, 12.0) == 0.0


def test_lions_heart_gives_the_whole_squad_critical_damage():
    reg = EffectRegistry()
    fire_trigger("own_burst_activate", {"leona": build_leona_rules(LEONA)}, _ctx(), reg, 10.0)
    assert round(reg.total_for("other_critical_damage_sources", RIFLE_ALLY, 10.0), 4) == 0.3464
    assert reg.total_for("other_critical_damage_sources", RIFLE_ALLY, 20.1) == 0.0


def test_roar_is_a_squad_wide_five_stack_crit_rate_counter():
    (spec,) = build_leona_resources(LEONA)
    assert spec.name == "roar"
    assert spec.fill == ("per_shot_every", ROAR_SHOT_COUNT)
    assert spec.cap == 5
    (buff,) = spec.buffs
    assert buff.stat == "crit_rate"
    assert buff.scope == "squad"
    assert round(buff.value_fn(1), 4) == 0.0262
    assert round(buff.value_fn(5), 4) == 0.131


def test_roar_stacks_do_not_expire_individually():
    """"Stacks up to 5 time(s) and lasts for 5 sec" is ONE counter refreshed by
    every trigger (the Raven ruling), not five independent 5-second stacks. Her
    own cadence is what makes the distinction decidable, and it decides it: the
    gap between fills never reaches 5 sec, so the counter never lapses and a
    permanent accumulation is the faithful model. Modelling it as per-stack
    expiry would pin her at 2 stacks for the whole fight."""
    (spec,) = build_leona_resources(LEONA)
    assert spec.lifetime is None

    shots = generate_shot_times("SG", 9, 1.5, 0.0, 180.0)
    fills = shots[ROAR_SHOT_COUNT - 1::ROAR_SHOT_COUNT]
    gaps = [b - a for a, b in zip(fills, fills[1:])]
    assert max(gaps) < 5.0, f"a gap of {max(gaps):.2f}s would drop the counter"


def test_lions_hearts_second_bullet_is_gated_on_roar_at_max_stacks():
    (spec,) = build_lions_heart_resource_gated_buffs(LEONA)
    assert spec["resource"] == "roar"
    assert spec["cap"] == 5
    assert spec["stat"] == "crit_rate"
    assert round(spec["value"], 4) == 0.2132
    assert spec["duration"] == 10.0
    assert not spec["gate_fn"](4)
    assert spec["gate_fn"](5)


def test_the_max_stack_bullet_reaches_only_shotgun_allies():
    (spec,) = build_lions_heart_resource_gated_buffs(LEONA)
    members = _ctx().members
    reached = [m.slug for m in members if spec["member_filter"](m, "leona")]
    assert reached == ["leona", "shotgun-ally"]


def test_the_effective_range_bullet_registers_nothing():
    """"Maximum Effective Range ▲ 20%" widens the range band itself, which the
    encounter sets and no skill can move - so it must not land as a stat."""
    reg = EffectRegistry()
    ctx = _ctx()
    rules = {"leona": build_leona_rules(LEONA)}
    for trigger in ("battle_start", "own_burst_activate", "full_burst_enter", "full_burst_end"):
        fire_trigger(trigger, rules, ctx, reg, 12.0)
    assert reg.total_for("effective_range_bonus", SELF, 12.0) == 0.0
