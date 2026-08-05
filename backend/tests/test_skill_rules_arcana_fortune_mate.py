from app.burst_cycle import FULL_BURST_DURATION
from app.effects import EffectRegistry
from app.raid_simulator import _resource_fill_times, simulate_raid
from app.skill_rules.arcana_fortune_mate import (
    HAPPY_MEMORIES_FIRST,
    PRECIOUS_MOMENTS_FIRST,
    ROTATION_PERIOD,
    build_fortune_mate_rules,
    build_keepsake_album_resource_gated_buffs,
    build_memories_and_moments_resources,
    radiant_youth_burst_percent,
)
from app.squad_engine import SquadContext, SquadMember, fire_trigger

CASTER_ATK = 80000.0

# Real skill level 10 values from api.dotgg.gg.
KEEPSAKE_ALBUM = {
    "description_value_01": "13",     # squad(approx) flat ATK = 13% of caster ATK PER Precious Moments stack
    "description_value_02": "15",     # its duration
    "description_value_03": "10",     # Snapshots Normal Attack Damage Multiplier % (modeled)
    "description_value_04": "3",      # Snapshots stack cap (modeled)
}
RADIANT_YOUTH = {
    "description_value_01": "20.09",  # self Critical Rate %
    "description_value_02": "2",      # reloads (not modeled)
    "description_value_03": "29.99",  # self Attack Damage %
    "description_value_04": "554.4",  # burst nuke % of final ATK
}
MEMORIES_AND_MOMENTS = {
    "description_value_01": "6",      # deferred: Two-times reload count
    "description_value_02": "1",      # Four-times pellet count; not a damage term, unconsumed
    "description_value_03": "3",      # pellet stack cap; not a damage term, unconsumed
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
    """One burst cycle for arcana: her tier-2 burst, then Full Burst enter/end.

    Also sets `current_full_burst_end` where raid_simulator.on_full_burst_enter
    would - AFTER own_burst_activate has already fired, since tier 2 (her burst)
    always runs before tier 3 opens the window in the real tier loop. A test
    that skipped this would never reproduce the stale-window bug (own_burst_activate
    reading the PREVIOUS cycle's end) that motivated Making Memories' open-ended +
    truncate_open_ended shape."""
    fire_trigger("own_burst_activate", rules, ctx, registry, burst_time)
    ctx.current_full_burst_end = burst_time + 10.0
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

    # Open-ended (duration=None): with no full_burst_end to close it, it stays
    # active indefinitely - see test_radiant_youth_buff_survives_into_the_second_
    # full_burst_cycle for the truncation and multi-cycle behavior.
    assert round(registry.total_for("crit_rate", SELF_TARGET, now=5.0 + FULL_BURST_DURATION + 0.1), 4) == 0.2009


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


def test_radiant_youth_buff_survives_into_the_second_full_burst_cycle():
    # Regression test: apply_radiant_youth fires on own_burst_activate (her
    # own tier-2 burst), which ALWAYS runs before this cycle's tier 3 opens the
    # window and current_full_burst_end is published for it - so a version of
    # this buff that read the window (end - time) instead of going open-ended
    # was reading the PREVIOUS cycle's stale end from the second cycle onward,
    # going negative and clamping to a dead-on-arrival 0-duration buff. The
    # bug's signature was "alive in cycle 1, dead from cycle 2" - a
    # single-cycle test cannot see it, so this one runs two.
    ctx = make_context()
    registry = EffectRegistry()
    rules = {"arcana-fortune-mate": build()}

    run_cycle(rules, ctx, registry, burst_time=5.0)    # cycle 1: [5, 15)
    run_cycle(rules, ctx, registry, burst_time=25.0)   # cycle 2: [25, 35)

    # Cycle 1's window has long closed by the time cycle 2 is checked.
    assert registry.total_for("crit_rate", SELF_TARGET, now=20.0) == 0.0

    # Alive mid-cycle-2 - this is exactly what the stale-window bug zeroed out.
    assert round(registry.total_for("crit_rate", SELF_TARGET, now=30.0), 4) == 0.2009
    assert round(registry.total_for("attack_damage_up", SELF_TARGET, now=30.0), 4) == 0.2999

    # And dead once cycle 2's own Full Burst ends.
    assert registry.total_for("crit_rate", SELF_TARGET, now=35.1) == 0.0
    assert registry.total_for("attack_damage_up", SELF_TARGET, now=35.1) == 0.0


# --- the phase rotation (Fienn's in-game observation, 2026-07-28) -------------
# Every 2nd normal attack while in Making Memories fires ONE of three effects
# in rotation - 2 reload, 4 Happy Memories, 6 Precious Moments, then 8/10/12 -
# and the count restarts when Making Memories is removed (each Full Burst).

def rotation_times(first, shot_times, own_burst_times, window=FULL_BURST_DURATION):
    return _resource_fill_times(
        ("per_shot_cycle_in_own_status_window", first, ROTATION_PERIOD, window),
        shot_times, core_hittable=False, fight_duration=1000.0,
        own_burst_times=own_burst_times,
    )


def test_rotation_places_each_effect_on_its_own_step():
    # 24 shots, one per second, inside a single 30s window: Happy Memories lands
    # on the 4th/10th/16th/22nd normal and Precious Moments on the 6th/12th/18th
    # /24th. Neither ever coincides with the other, which is the "only one
    # effect is triggered at a time" Fienn confirmed at the 12th normal.
    shots = [float(i) for i in range(24)]  # shot n is at t = n-1
    happy = rotation_times(HAPPY_MEMORIES_FIRST, shots, [0.0], window=30.0)
    precious = rotation_times(PRECIOUS_MOMENTS_FIRST, shots, [0.0], window=30.0)
    assert happy == [3.0, 9.0, 15.0, 21.0]
    assert precious == [5.0, 11.0, 17.0, 23.0]
    assert not set(happy) & set(precious)


def test_rotation_restarts_in_every_window():
    # Two windows holding 8 shots each - a non-multiple of the period, so a
    # counter that ran straight through would put the second window's Happy
    # Memories on its 2nd and 8th shot instead of its 4th. Both windows must
    # look identical.
    shots = [float(i) for i in range(8)] + [100.0 + i for i in range(8)]
    happy = rotation_times(HAPPY_MEMORIES_FIRST, shots, [0.0, 100.0])
    assert happy == [3.0, 103.0]


def test_rotation_ignores_shots_outside_the_status_window():
    # She fires all fight; only the shots inside Making Memories advance the
    # rotation, so out-of-window shots must not shift the phase.
    shots = [float(i) for i in range(40)]
    happy = rotation_times(HAPPY_MEMORIES_FIRST, shots, [20.0])
    assert happy == [23.0, 29.0]


# --- end to end: the rotation driven by a real shot timeline ------------------

def arcana_deck_result(fight_duration=40.0, extra_rules=()):
    """Fortune Mate (Burst 2) between two filler allies, her SG carrying enough
    ammo to fire without a reload gap so the rotation is bounded by the Full
    Burst window rather than by her magazine. Base ATK is CASTER_ATK and enemy
    DEF is 0, so a shot's damage divided by the opening shot's is exactly her
    final-ATK ratio - which is what makes the assertions below plain arithmetic."""
    deck = [
        {"slug": "ally-b1", "burst_tier": 1, "element": "Iron", "cooldown": 20.0, "weapon": "AR"},
        {"slug": "arcana-fortune-mate", "burst_tier": 2, "element": "Fire", "cooldown": 20.0,
         "weapon": "SG"},
        {"slug": "sg-ally", "burst_tier": 3, "element": "Iron", "cooldown": 20.0, "weapon": "SG"},
    ]
    values = {"radiant_youth": RADIANT_YOUTH, "memories_and_moments": MEMORIES_AND_MOMENTS,
              "keepsake_album": KEEPSAKE_ALBUM, "caster_atk": CASTER_ATK}
    return simulate_raid(
        deck,
        {"ally-b1": [], "sg-ally": [],
         "arcana-fortune-mate": build_fortune_mate_rules(values) + list(extra_rules)},
        burst_damage_percents={},
        base_stats={m["slug"]: {"atk": CASTER_ATK if m["slug"] == "arcana-fortune-mate" else 0,
                                "def": 0, "max_hp": 0} for m in deck},
        enemy_def=0, gauge_charge_time=5.0, fight_duration=fight_duration, mode="auto",
        base_crit_rate=0.0,
        weapon_stats={"arcana-fortune-mate": {
            "weapon": "SG", "damage_percent": 100.0, "max_ammo": 200,
            "reload_time": 2.33, "charge_time": 0.0, "charge_damage_percent": 0.0}},
        resource_specs={"arcana-fortune-mate": build_memories_and_moments_resources(values)},
        resource_gated_buffs={
            "arcana-fortune-mate": build_keepsake_album_resource_gated_buffs(values)},
    )


def her_normal_attacks(result):
    return [e for e in result["damage_log"]
            if e["slug"] == "arcana-fortune-mate" and e["source"] == "normal_attack"]


def test_rotation_steps_land_on_their_own_normals_through_a_real_timeline():
    in_window = [e for e in her_normal_attacks(arcana_deck_result())
                 if 5.0 <= e["time"] < 15.0]
    h, p = 0.1, 0.0249

    def step(n):  # the nth in-window normal against the one before it
        return round(in_window[n - 1]["damage"] / in_window[n - 2]["damage"], 6)

    # Happy Memories on the 4th and 10th, Precious Moments on the 6th and 12th.
    assert step(4) == round((1 + h) / 1, 6)
    assert step(6) == round((1 + p) / 1, 6)
    assert step(10) == round((1 + 2 * h) / (1 + h), 6)
    assert step(12) == round((1 + 2 * p) / (1 + p), 6)
    # Nothing lands on the odd normals, nor on the reload steps 2 and 8.
    assert [n for n in (2, 3, 5, 7, 8, 9, 11) if step(n) != 1.0] == []
    # SG at 1.5/s puts 15 shots in the window, so the rotation stops at its 12th
    # normal - a 3rd stack needs the attack speed Fienn measured at 22 shots.
    assert len(in_window) == 15


def test_keepsake_album_reads_the_live_stack_count_and_snapshots_is_wiped():
    shots = her_normal_attacks(arcana_deck_result(fight_duration=80.0))
    base = shots[0]["damage"]  # opening shot: no burst, no stacks

    # Final ATK is base_atk x (1 + atk%) + flat_atk, and both are expressed in
    # units of base_atk here, so a post-window shot reads (1 + 2.49% x stacks)
    # + 13% x stacks exactly. A leaked Happy Memories stack would show up as a
    # further x1.1, and the old per-cycle model as 13% x 1 instead of x 2.
    after_first = next(e for e in shots if e["time"] > 15.0)
    assert round(after_first["damage"] / base, 6) == round((1 + 2 * 0.0249) + 0.13 * 2, 6)

    # Window 1 reaches the rotation's 6th and 12th normal (2 stacks), window 2
    # its 6th (the 3rd), and the cap holds from there.
    after_second = next(e for e in shots if e["time"] > 35.0)
    assert round(after_second["damage"] / base, 6) == round((1 + 3 * 0.0249) + 0.13 * 3, 6)
    after_third = next(e for e in shots if e["time"] > 55.0)
    assert round(after_third["damage"] / base, 6) == round((1 + 3 * 0.0249) + 0.13 * 3, 6)


def test_snapshots_of_youth_carries_the_cap_and_the_full_burst_end_reset():
    snapshots = next(s for s in build_memories_and_moments_resources({
        "memories_and_moments": MEMORIES_AND_MOMENTS, "keepsake_album": KEEPSAKE_ALBUM,
    }) if s.name == "snapshots_of_youth")
    # 「Happy Memories가 발동할 때」 붙으므로 채움은 로테이션의 HM 스텝과 같고,
    # 「Full Burst 종료 시 Snapshots of Youth 제거」가 리셋이다. 상한과 리셋이
    # 4번째 로테이션 스텝(22번째 평타 - Tove를 앉힌 Fienn이 도달한 지점)을 4번째
    # 스택으로 만들지 않게 막고, 창 사이에 카운터를 비운다.
    assert snapshots.cap == 3
    assert snapshots.resets == [{"trigger": "full_burst_end", "value": 0}]
    assert snapshots.fill == ("per_shot_cycle_in_own_status_window", 4, 6, FULL_BURST_DURATION)
    # 값은 스킬 데이터 슬롯에서 온다 - 피팅된 상수가 아니다.
    assert round(snapshots.buffs[0].value_fn(3), 6) == 0.3

    precious = next(s for s in build_memories_and_moments_resources({
        "memories_and_moments": MEMORIES_AND_MOMENTS, "keepsake_album": KEEPSAKE_ALBUM,
    }) if s.name == "precious_moments")
    # Precious Moments is NOT reset - Keepsake Album removes Making Memories and
    # Snapshots of Youth, not this.
    assert precious.resets == []
    assert precious.fill == ("per_shot_cycle_in_own_status_window", 6, 6, FULL_BURST_DURATION)


def test_snapshots_stacks_additively_with_the_sg_collectible_bucket():
    """Fienn의 2026-07-28 사격장 판독을 재현한다. 소장품이 이미 9.46%를 넣어 둔
    버킷에 청춘의 기록 +10%가 가산되면 스택당 한계효과는 0.1/1.0946 = 0.0913576이고,
    실측 첫 스택 기울기가 0.0913573이었다. 두 소스가 곱셈으로 붙으면 1.1이 나오는데
    그것은 실측과 0.87% 어긋난다 - 그 0.87%가 이 테스트가 지키는 값이다."""
    from app.effects import Effect
    from app.roster import _battle_start_effects_rule

    collectible = Effect("normal_attack_damage_multiplier", 0.0946, "self",
                         None, "arcana-fortune-mate")
    result = arcana_deck_result(
        extra_rules=[_battle_start_effects_rule([collectible])])
    in_window = [e for e in her_normal_attacks(result) if 5.0 <= e["time"] < 15.0]

    def step(n):
        return in_window[n - 1]["damage"] / in_window[n - 2]["damage"]

    assert round(step(4), 7) == round(1.1946 / 1.0946, 7)
    assert round(step(10), 7) == round(1.2946 / 1.1946, 7)
    assert round(step(4), 4) != 1.1
