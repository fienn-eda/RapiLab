"""Charge Damage buffs only reach a unit that is actually firing a charge shot.

"Charge Damage ▲ X%" multiplies a fully-charged shot. An SMG, MG, AR or SG has
no charge, so a squad-wide Charge Damage buff does nothing for its bearer
(Fienn, 2026-07-26) - and the engine was multiplying every allied normal attack
by it regardless. Velvet's +100.8% was roughly DOUBLING her SMG and MG
teammates' normal attacks in Fienn's recorded deck 2.

The exception is what makes this a window test rather than a weapon test:
Nayuta's burst transforms her normal attack into a charge attack for 10s
(`weapon_mode_schedules` with an SR profile), so the buff must reach her for
exactly that window and no longer.

Charge Damage is also NORMAL-ATTACK-only. The damage formula marks it with an
asterisk - "Modifiers with an asterisk (*) are exclusive to Normal Attacks
only" - and its glossary entry reads "Damage bonus available to Charge
weapons' normal attacks ... Charge Damage Sources include buffs from the unit
or allies" (nikke.gg/damage-formula). So a skill that fires ON a full charge
collects none of it; see the last test.
"""
from app.raid_simulator import simulate_raid

RULES_BY_SLUG = {"buffer": [], "midtier": [], "attacker": []}


def make_deck():
    return [
        {"slug": "buffer", "burst_tier": 1, "element": "Iron", "cooldown": 20.0},
        {"slug": "midtier", "burst_tier": 2, "element": "Iron", "cooldown": 20.0},
        {"slug": "attacker", "burst_tier": 3, "element": "Iron", "cooldown": 40.0},
    ]


def make_base_stats():
    return {s["slug"]: {"atk": 100000.0, "def": 5000.0, "max_hp": 500000.0}
            for s in make_deck()}


SMG = {"weapon": "SMG", "damage_percent": 10.0, "max_ammo": 300,
       "reload_time": 2.0, "charge_time": 0.0, "charge_damage_percent": 100.0}
SR = {"weapon": "SR", "damage_percent": 10.0, "max_ammo": 6,
      "reload_time": 2.0, "charge_time": 1.0, "charge_damage_percent": 100.0}
# 재장전이 0이면 톡톡이가 언제나 이기므로 이 무기는 매거진을 통째로 톡톡이로 쏜다 -
# 그래야 아래 테스트가 톡톡이 샷만 보고 있다는 것이 보장된다.
TAP_SR = {**SR, "reload_time": 0.0, "tap_fire": True,
          "tap_fire_interval": 15 / 60, "charge_motion_delay": 22 / 60}


def _normal_damage(weapon_stats, charge_bonus, schedules=None):
    from app.effects import Effect
    from app.squad_engine import SkillRule

    def grant(context, caster_slug, time, registry):
        registry.add(Effect("charge_damage_bonus", charge_bonus, "squad", None,
                            caster_slug), applied_at=time)

    rules = dict(RULES_BY_SLUG)
    rules["buffer"] = [SkillRule(trigger="battle_start", action=grant)]
    result = simulate_raid(
        make_deck(), rules,
        burst_damage_percents={}, base_stats=make_base_stats(),
        enemy_def=0, gauge_charge_time=2.0, fight_duration=40.0, mode="manual",
        base_crit_rate=0.0,
        weapon_stats={s["slug"]: weapon_stats for s in make_deck()},
        weapon_mode_schedules=schedules or {},
    )
    return sum(e["damage"] for e in result["damage_log"]
               if e["slug"] == "attacker" and e["source"] == "normal_attack")


def test_a_charge_damage_buff_does_nothing_for_a_non_charge_weapon():
    assert _normal_damage(SMG, 1.008) == _normal_damage(SMG, 0.0)


def test_a_charge_damage_buff_still_reaches_a_charge_weapon():
    assert _normal_damage(SR, 1.008) > _normal_damage(SR, 0.0)


def test_a_weapon_transform_into_a_charge_mode_lets_the_buff_through():
    """Nayuta's case: an SMG whose burst turns her normal attack into a charge
    attack for a window. Inside it the buff must count."""
    def schedule(context, fight_duration):
        return [{"start": 5.0, "end": 15.0,
                 "profile": {"weapon": "SR", "damage_percent": 10.0,
                             "rate_of_fire": 1.0, "charge_damage_percent": 100.0}}]

    schedules = {"attacker": schedule}
    assert (_normal_damage(SMG, 1.008, schedules)
            > _normal_damage(SMG, 0.0, schedules))


def test_a_skill_nuke_collects_no_charge_damage_even_from_a_charge_bearer():
    """The asterisk case: a burst nuke fired by an SR bearer under a +100%
    Charge Damage buff is still bare. Charge Damage multiplies the charged
    SHOT, not a separate damage instance that a charge happens to trigger -
    which is what Scarlet's staged nukes, Velvet's Bullets of Love and Neon's
    Firepower Explosion all are."""
    from app.skill_rules._helpers import buff_rule

    deck = make_deck()
    result = simulate_raid(
        deck,
        {"buffer": [buff_rule("battle_start",
                              [("charge_damage_bonus", 1.0, "squad", None)])],
         "midtier": [], "attacker": []},
        burst_damage_percents={"attacker": 100.0},
        base_stats={s["slug"]: {"atk": 10000, "def": 0, "max_hp": 0} for s in deck},
        enemy_def=0,
        gauge_charge_time=2.0,
        fight_duration=30.0,
        base_crit_rate=0.0,
        weapon_stats={"attacker": {
            "weapon": "SR", "damage_percent": 10.0, "max_ammo": 5,
            "reload_time": 2.0, "charge_time": 1.0, "charge_damage_percent": 250.0,
        }},
    )
    burst = next(e["damage"] for e in result["damage_log"] if e["source"] == "burst")
    assert burst == 10000.0
    # Her normal attacks DO collect it, weapon multiplier and buff together:
    # 10% coefficient x (1 + buff 1.0 + weapon 1.5).
    shot = next(e["damage"] for e in result["damage_log"]
                if e["source"] == "normal_attack")
    assert round(shot, 4) == round(10000 * 0.10 * 3.5, 4)


def test_the_tap_fire_fixture_actually_taps():
    """아래 테스트가 무언가를 검증하려면 이 무기가 **실제로** 톡톡이를 써야 한다.

    안 그러면 「차지 대미지가 톡톡이에 안 붙는다」가 톡톡이 샷이 하나도 없어서
    참인 항진명제가 된다.
    """
    from app.attack_rate import generate_segmented_shots
    shots = generate_segmented_shots(TAP_SR, (), 10.0)
    assert shots, "이 무기가 한 발도 안 쏜다"
    assert all(s.is_tap_fire for s in shots)


def test_a_charge_damage_buff_does_not_reach_a_tap_fired_shot():
    """톡톡이 샷은 차지를 안 채웠으므로 fully-charged가 아니다 - 이 파일의 첫
    문단이 말하는 그 조건을 만족하지 않는다.

    브래디 실측(2026-08-20)이 그것을 보였다: 차지 대미지를 7.59%에서 11.11%로
    올려도 같은 게이지의 대미지가 +0.06%밖에 안 달라진다. 직접 곱해진다면
    +3.27%여야 한다. docs/measurements/bready-charge-damage.md

    바로 위 `test_a_charge_damage_buff_still_reaches_a_charge_weapon`이 같은 SR을
    풀차지로 쏠 때는 버프가 통한다는 것을 지키고 있으므로, 이 둘이 함께
    「풀차지에는 붙고 톡톡이에는 안 붙는다」를 못박는다.
    """
    assert _normal_damage(TAP_SR, 1.008) == _normal_damage(TAP_SR, 0.0)
