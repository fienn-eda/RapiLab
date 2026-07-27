"""Snow White: Heavy Arms (slug "snow-white-heavy-arms"), real max-level
figures from lootandwaifus, slots numbered left-to-right per skill (full
transcription, no skips - verified against the actual tokenizer output, no
drop_tokens needed; see test_skill_value_assembly.py).
"""
from types import SimpleNamespace

import pytest

from app.effects import EffectRegistry
from app.raid_simulator import simulate_raid
from app.skill_rules.snow_white_heavy_arms import (
    SKILL_VALUE_MANIFESTS,
    build_fully_active_weapon_mode_schedule,
    build_seven_dwarves_per_shot_rules,
    build_snow_white_heavy_arms_rules,
)
from app.squad_engine import SquadContext, SquadMember

SEVEN_DWARVES = {
    "description_value_01": "0.2",    # Lock-On/Auto Fire Ready/Damage Taken tick interval sec
    "description_value_02": "5",      # max Lock-On targets
    "description_value_03": "0.2",    # (repeat of the tick-interval phrase)
    "description_value_04": "42.24",  # DEF up % while Auto Fire Ready is active (deferred)
    "description_value_05": "5",      # base ammo loaded by Auto Fire Ready
    "description_value_06": "0.2",    # (repeat of the tick-interval phrase)
    "description_value_07": "4.2",    # Damage Taken up % (Lock-On targets)
    "description_value_08": "4",      # Damage Taken up duration sec
    "description_value_09": "1",      # "Effect 1" label
    "description_value_10": "41.9",   # Auto Fire all-enemy hit %
    "description_value_11": "2",      # "Effect 2" label
    "description_value_12": "105.59",  # Auto Fire sequential (per-ammo) hit %
    "description_value_13": "1",      # Fully Active use count decrement
}
SHADES_OF_WHITE = {
    "description_value_01": "1.2",    # fixed charge time sec
    "description_value_02": "5",      # Pierce duration sec (deferred)
    "description_value_03": "46.84",  # self ATK up % during Full Charge
    "description_value_04": "5",      # its duration sec
    "description_value_05": "62.64",  # Damage to Parts up % during Full Charge
    "description_value_06": "5",      # its duration sec
    "description_value_07": "3",      # "Burst Stage 3" trigger-phrase digit (unused)
    "description_value_08": "73.92",  # self ATK up % on entering Burst Stage 3
    "description_value_09": "10",     # its duration sec
    "description_value_10": "528",    # Charge Damage up % (Fully Active Full Charge)
    "description_value_11": "1",      # its duration, rounds
    "description_value_12": "158.4",  # Sequential attack damage up % (Fully Active Full Charge)
    "description_value_13": "1",      # its duration, rounds
}
FULLY_ACTIVE = {
    "description_value_01": "84.48",  # self Attack Damage up %
    "description_value_02": "10",     # its duration sec
    "description_value_03": "2",      # number of uses
    "description_value_04": "1",      # "Effect 1" label
    "description_value_05": "3.2",    # fixed charge time sec during Fully Active
    "description_value_06": "2",      # "Effect 2" label
    "description_value_07": "10",     # max Lock-On targets up
    "description_value_08": "3",      # "Effect 3" label
    "description_value_09": "10",     # max Auto Fire Ready ammo up
    "description_value_10": "0",      # "reaches 0" removal-condition digit (unused)
    "description_value_11": "41.9",   # destructible-projectile sweep % (deferred)
}
SWHA_WEAPON_STATS = {
    "weapon": "SR", "damage_percent": 69.04, "max_ammo": 6,
    "reload_time": 2.0, "charge_time": 1.2, "charge_damage_percent": 250.0,
}
SWHA_VALUES = {
    "seven_dwarves": SEVEN_DWARVES,
    "shades_of_white": SHADES_OF_WHITE,
    "fully_active": FULLY_ACTIVE,
    "caster_weapon_stats": SWHA_WEAPON_STATS,
}
SWHA = {"slug": "snow-white-heavy-arms", "element": "Water"}
ALLY = {"slug": "ally", "element": "Fire"}


def make_context():
    return SquadContext([
        SquadMember("snow-white-heavy-arms", burst_tier=3, element="Water"),
        SquadMember("ally", burst_tier=1, element="Fire"),
    ])


class _FakeRegistry:
    """Minimal registry stand-in exposing a bare `.added` list - follows the
    cinderella_crystal_wave test's helper (buff_rule's action only ever calls
    registry.add / add_refreshing)."""

    def __init__(self):
        self.added = []

    def add(self, effect, applied_at):
        self.added.append((effect.stat, effect.value, effect.scope, effect.duration))

    def add_refreshing(self, effect, applied_at):
        self.added.append((effect.stat, effect.value, effect.scope, effect.duration))


def _applied_buffs(rule):
    reg = _FakeRegistry()
    rule.action(make_context(), "snow-white-heavy-arms", 0.0, reg)
    return reg.added


def test_battle_start_and_burst_buffs():
    rules = build_snow_white_heavy_arms_rules(SWHA_VALUES)
    starts = [r for r in rules if r.trigger == "battle_start"]
    bursts = [r for r in rules if r.trigger == "own_burst_activate"]
    assert len(starts) == 1 and len(bursts) == 1

    # battle_start: Lock-On tick's Damage Taken +4.2% approximated as a
    # permanent squad debuff (charging uptime ~100%, Fienn 2026-07-19).
    assert ("damage_taken_up", 0.042, "squad", None) in _applied_buffs(starts[0])

    # own_burst_activate carries ONLY Seven Dwarves Fully Active, her own burst
    # skill's buff. Shades of White's ATK says "entering Burst Stage 3" - the
    # stage, not her cast - so it rides ally_burst_activate instead and still
    # fires in cycles another Burst 3 takes the slot.
    burst_buffs = _applied_buffs(bursts[0])
    assert ("attack_damage_up", 0.8448, "self", 10.0) in burst_buffs
    assert ("atk_percent", 0.7392, "self", 10.0) not in burst_buffs

    stage_three = [r for r in rules if r.trigger == "ally_burst_activate"]
    assert len(stage_three) == 1
    assert ("atk_percent", 0.7392, "self", 10.0) in _applied_buffs(stage_three[0])


def test_auto_fire_pulses_base_and_fully_active_variants():
    rules = build_seven_dwarves_per_shot_rules(SWHA_VALUES)
    assert len(rules) == 3
    every, outside, during = rules
    assert every == (1, "every", every[2])
    assert outside[0:2] == (1, "every_outside_segment")
    assert during[0:2] == (1, "every_during_segment")

    # charge-window refreshing buffs (self ATK/parts, both 5s from Shades of White)
    charge_buffs = _applied_buffs(every[2][0])
    atk_buff = next(b for b in charge_buffs if b[0] == "atk_percent")
    parts_buff = next(b for b in charge_buffs if b[0] == "damage_to_parts_up")
    assert atk_buff == ("atk_percent", pytest.approx(0.4684), "self", 5.0)
    assert parts_buff == ("damage_to_parts_up", pytest.approx(0.6264), "self", 5.0)

    # The sweep and the sequential volley are SEPARATE pulses: "Sequential
    # attack damage 158.4%" belongs to the shared Damage-Up bucket and must
    # reach only the sequential hits, so it cannot ride one merged coefficient
    # (measured 2026-07-28 - see the module docstring).
    def _pulses(rules, time=1.0):
        reg = EffectRegistry()
        for rule in rules:
            rule.action(make_context(), "snow-white-heavy-arms", time, reg)
        return reg.drain_pulses("instant_damage_percent")

    # base cadence: 41.9% all-hit sweep, then 5-ammo x 105.59% sequential
    base_pulses = _pulses(outside[2])
    assert [p.value for p in base_pulses] == [pytest.approx(41.9), pytest.approx(527.95)]
    assert [p.damage_type for p in base_pulses] == ["attack", "sequential"]

    # Fully Active cadence: same sweep, 15 ammo, and the 158.4% arriving as a
    # self buff rather than folded into the volley's percent
    reg = EffectRegistry()
    for rule in during[2]:
        rule.action(make_context(), "snow-white-heavy-arms", 1.0, reg)
    seg_pulses = reg.drain_pulses("instant_damage_percent")
    assert [p.value for p in seg_pulses] == [pytest.approx(41.9), pytest.approx(1583.85)]
    assert [p.damage_type for p in seg_pulses] == ["attack", "sequential"]
    seq_up = [e for e, _ in reg._entries if e.stat == "sequential_attack_damage_up"]
    assert seq_up and seq_up[0].value == pytest.approx(1.584)


def test_fully_active_segment_is_two_slow_charged_shots():
    schedule = build_fully_active_weapon_mode_schedule(SWHA_VALUES)
    segments = schedule(SimpleNamespace(
        burst_times={"snow-white-heavy-arms": [20.0]}), 180.0)
    # `shares_magazine` is the part that makes this NOT a weapon transform:
    # Fully Active re-times her own charge and keeps firing her own rounds
    # (Fienn, in game, 2026-07-28).
    assert segments == [{"start": 20.0, "until_shots": 2, "shares_magazine": True,
                         "profile": {
        "weapon": "SR", "damage_percent": 69.04,
        "charge_damage_percent": pytest.approx(778.0), "charge_time": 3.2}}]


def test_fully_active_schedule_empty_with_no_bursts():
    schedule = build_fully_active_weapon_mode_schedule(SWHA_VALUES)
    assert schedule(SimpleNamespace(burst_times={}), 180.0) == []


def test_manifest_registered():
    manifest = SKILL_VALUE_MANIFESTS["snow-white-heavy-arms"]
    assert manifest["source"] == "lootandwaifus"
    assert manifest["test_module"] == "test_skill_rules_snow_white_heavy_arms"


def _swha_sim_deck():
    # Tiers 1/2 are inert placeholders so the burst cycle can complete - only
    # snow-white-heavy-arms (tier 3) carries rules/a weapon. Cooldowns are
    # large enough that only one cycle completes inside fight_duration, so
    # her burst - and its 2-shot Fully Active segment - lands at a known,
    # deterministic time (t=5.0, the gauge_charge_time floor).
    return [
        {"slug": "b1", "burst_tier": 1, "element": "Water", "cooldown": 20.0},
        {"slug": "b2", "burst_tier": 2, "element": "Water", "cooldown": 20.0},
        {"slug": "snow-white-heavy-arms", "burst_tier": 3, "element": "Water", "cooldown": 40.0},
    ]


def test_e2e_burst_opens_fully_active_segment_which_spends_her_own_magazine():
    # Her burst at t=5.0 opens a 2-shot segment at 3.2s charge cadence (each
    # shot carrying the empowered Auto Fire pulse via every_during_segment),
    # landing at t=8.2 and t=11.4. Those two shots come out of the SAME 6-round
    # magazine as her base cadence, which is the whole point of
    # `shares_magazine`: rounds 1-4 fire at 1.2/2.4/3.6/4.8, the segment spends
    # rounds 5 and 6, and the second Fully Active shot EMPTIES the magazine -
    # so she reloads instead of resuming one charge later.
    from app.skill_rules.registry import build_nikke_rules, get_per_shot_rules, get_weapon_mode_schedules

    slug = "snow-white-heavy-arms"
    rules, burst_percent = build_nikke_rules(slug, SWHA_VALUES)
    assert burst_percent is None  # burst is state-change only, no direct nuke

    deck = _swha_sim_deck()
    base_stats = {m["slug"]: {"atk": 10000.0} for m in deck}
    result = simulate_raid(
        deck=deck, rules_by_slug={slug: rules}, burst_damage_percents={},
        base_stats=base_stats, enemy_def=0.0, gauge_charge_time=5.0,
        fight_duration=30.0, mode="auto", base_crit_rate=0.0,
        weapon_stats={slug: SWHA_WEAPON_STATS},
        weapon_mode_schedules={slug: get_weapon_mode_schedules(slug, SWHA_VALUES)},
        per_shot_rules={slug: get_per_shot_rules(slug, SWHA_VALUES)},
    )
    shots = sorted(e["time"] for e in result["damage_log"] if e["source"] == "normal_attack")

    # the two Fully Active segment shots, 3.2s apart, starting one charge
    # after burst (t=5.0 + 3.2 = 8.2)
    # The shared-magazine walk accumulates from one shot to the next (it has to
    # - a reload shifts everything after it), so segment times carry ordinary
    # float drift where the fresh-magazine path recomputed start + k*interval.
    seg_shots = [t for t in shots if 5.0 < t < 12.0]
    assert seg_shots == [pytest.approx(8.2), pytest.approx(11.4)]
    # Four base rounds before the burst interrupts the fifth charge.
    assert [t for t in shots if t < 5.0] == [1.2, 2.4, pytest.approx(3.6), 4.8]
    # Magazine empty at 11.4 -> reload (2.0s) then one 1.2s charge = 14.6.
    # Under the old fresh-magazine resume this shot landed at 12.6.
    assert min(t for t in shots if t > 12.0) == pytest.approx(14.6)

    per_shot = [e for e in result["damage_log"] if e["source"] == "per_shot_nuke"]
    segment_pulses = [e for e in per_shot if e["time"] in seg_shots]
    resume = min(t for t in shots if t > 12.0)
    base_pulse_at_resume = [e for e in per_shot if e["time"] == resume]
    # Two pulses per shot now (sweep + sequential volley), so the segment's two
    # shots are four entries and the resumed base shot is two.
    assert len(segment_pulses) == 4
    assert len(base_pulse_at_resume) == 2
    # The empowered volley (15 x 105.59% carrying +158.4% in the Damage-Up
    # bucket) dwarfs the base one (5 x 105.59%) - structurally impossible to
    # double-count (mutually exclusive every_during_segment/every_outside_segment).
    assert max(p["damage"] for p in segment_pulses) > max(p["damage"] for p in base_pulse_at_resume)
