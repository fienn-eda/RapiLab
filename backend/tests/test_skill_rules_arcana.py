from app.effects import EffectRegistry
from app.skill_rules.arcana import arcana_burst_percent, build_arcana_rules
from app.squad_engine import SquadContext, SquadMember, fire_trigger

# Real skill level 10 values from api.dotgg.gg.
AWAKENED_DESTINY = {
    "description_value_01": "3",    # Burst 3 (subset bullet's tier filter)
    "description_value_02": "75",   # deferred: Cooldown of Skill 2 down %
    "description_value_03": "15",   # deferred: duration
    "description_value_04": "180",  # The Magician: Attack damage %
    "description_value_05": "15",   # duration
    "description_value_06": "5",    # squad ATK % of caster's ATK
    "description_value_07": "10",   # duration
}
CYCLE_OF_DESTINY = {
    "description_value_01": "3",    # Burst 3 (subset bullet's tier filter)
    "description_value_02": "180",  # Strength: ATK % of caster's ATK
    "description_value_03": "15",   # duration
    "description_value_04": "6",    # Death: Cooldown of Burst Skill down sec
    "description_value_05": "50",   # Death: ATK % of caster's ATK
    "description_value_06": "5",    # Death: duration
    "description_value_07": "7.5",  # squad Attack damage %
    "description_value_08": "10",   # duration
}
SHACKLES_OF_DESTINY = {
    "description_value_01": "10",   # Wheel of Fortune: Attack damage %
    "description_value_02": "10",   # duration
    "description_value_03": "300",  # burst nuke % of final ATK
    "description_value_04": "10",   # Judgement: Damage taken %
    "description_value_05": "10",   # duration
}


def make_context():
    return SquadContext([
        SquadMember("arcana", burst_tier=2, element="Electric"),
        SquadMember("electric-ally", burst_tier=3, element="Electric"),
        SquadMember("fire-ally", burst_tier=1, element="Fire"),
    ])


def build(caster_atk=10000):
    return build_arcana_rules({
        "awakened_destiny": AWAKENED_DESTINY,
        "cycle_of_destiny": CYCLE_OF_DESTINY,
        "shackles_of_destiny": SHACKLES_OF_DESTINY,
        "caster_atk": caster_atk,
    })


ELECTRIC_ALLY = {"slug": "electric-ally", "element": "Electric"}
FIRE_ALLY = {"slug": "fire-ally", "element": "Fire"}


def test_burst_percent_is_300():
    assert arcana_burst_percent({"shackles_of_destiny": SHACKLES_OF_DESTINY}) == 300.0


def test_shackles_grants_electric_attack_damage_and_enemy_damage_taken():
    ctx = make_context()
    registry = EffectRegistry()
    fire_trigger("own_burst_activate", {"arcana": build()}, ctx, registry, time=5.0)

    assert round(registry.total_for("attack_damage_up", ELECTRIC_ALLY, now=5.0), 4) == 0.10
    assert registry.total_for("attack_damage_up", FIRE_ALLY, now=5.0) == 0.0  # element-gated
    assert round(registry.total_for("damage_taken_up", FIRE_ALLY, now=5.0), 4) == 0.10  # squad-wide


def test_awakened_destiny_squad_atk_applies_unconditionally():
    ctx = make_context()
    registry = EffectRegistry()
    # arcana's own burst has NOT fired this cycle
    fire_trigger("full_burst_end", {"arcana": build()}, ctx, registry, time=15.0)

    assert registry.total_for("flat_atk", FIRE_ALLY, now=15.0) == 500.0  # 5% of 10000


def test_death_bullet_needs_the_wheel_still_running_at_full_burst_end():
    # 수레바퀴는 그녀가 버스트 스테이지 2에서 시전할 때 시작하는 10초짜리다.
    ctx = make_context()
    ctx.record_burst_time("arcana", 2.5)
    registry = EffectRegistry()
    # 표준 10초 창: 그녀의 시전은 창이 열리기 전이므로 종료 시점엔 이미 만료다.
    fire_trigger("full_burst_end", {"arcana": build()}, ctx, registry, time=12.6)

    assert registry.drain_pulses("burst_cooldown_reduction_sec") == []
    # Awakened Destiny의 무조건 5%만 적용된다 (Death의 50%는 아니다)
    assert registry.total_for("flat_atk", FIRE_ALLY, now=12.6) == 500.0

    # 이사벨이 창을 5초로 줄인 사이클에서는 아직 살아 있다.
    ctx2 = make_context()
    ctx2.record_burst_time("arcana", 2.5)
    registry2 = EffectRegistry()
    fire_trigger("full_burst_end", {"arcana": build()}, ctx2, registry2, time=7.6)

    pulses = registry2.drain_pulses("burst_cooldown_reduction_sec")
    assert len(pulses) == 1
    assert pulses[0].value == 6.0
    assert pulses[0].scope == "squad"
    # Awakened의 5% (500) + Death의 50% (5000)
    assert registry2.total_for("flat_atk", FIRE_ALLY, now=7.6) == 5500.0


def test_death_bullet_does_not_fire_when_arcana_never_burst():
    ctx = make_context()
    registry = EffectRegistry()
    fire_trigger("full_burst_end", {"arcana": build()}, ctx, registry, time=7.6)
    assert registry.drain_pulses("burst_cooldown_reduction_sec") == []
    assert registry.total_for("flat_atk", FIRE_ALLY, now=7.6) == 500.0


def test_cycle_of_destiny_attack_damage_bullet_applies_unconditionally():
    ctx = make_context()
    registry = EffectRegistry()
    fire_trigger("full_burst_end", {"arcana": build()}, ctx, registry, time=15.0)
    assert round(registry.total_for("attack_damage_up", FIRE_ALLY, now=15.0), 4) == 0.075


def _b3_context():
    return SquadContext([
        SquadMember("arcana", burst_tier=2, element="Electric"),
        SquadMember("electric-b3", burst_tier=3, element="Electric"),
        SquadMember("fire-b3", burst_tier=3, element="Fire"),
    ])


ELECTRIC_B3 = {"slug": "electric-b3", "element": "Electric"}
FIRE_B3 = {"slug": "fire-b3", "element": "Fire"}


def test_magician_and_strength_hit_bursted_electric_b3_allies():
    # The Magician (Awakened Destiny) / Strength (Cycle of Destiny): FB end,
    # all Burst 3 Electric Code allies who previously cast their Burst Skill,
    # if Arcana is still in Wheel of Fortune status at that instant.
    ctx = _b3_context()
    ctx.burst_used_this_cycle.update({"arcana", "electric-b3", "fire-b3"})
    ctx.record_burst_time("arcana", 10.0)  # wheel still up at t=15.0 (10.0 + 10 > 15.0)
    registry = EffectRegistry()
    fire_trigger("full_burst_end", {"arcana": build()}, ctx, registry, time=15.0)

    # Electric B3: squad 0.075 + Magician 1.80
    assert round(registry.total_for("attack_damage_up", ELECTRIC_B3, now=15.0), 4) == 1.875
    # Fire B3: squad 0.075 only
    assert round(registry.total_for("attack_damage_up", FIRE_B3, now=15.0), 4) == 0.075
    # Electric B3 flat ATK: Awakened 500 + Death 5000 + Strength 18000 (180% of 10000)
    assert registry.total_for("flat_atk", ELECTRIC_B3, now=15.0) == 23500.0
    assert registry.total_for("flat_atk", FIRE_B3, now=15.0) == 5500.0
    # 15s duration: gone at 30.1
    assert round(registry.total_for("attack_damage_up", ELECTRIC_B3, now=30.1), 4) == 0.0


def test_magician_and_strength_need_the_wheel_still_running():
    ctx = _b3_context()
    ctx.burst_used_this_cycle.update({"arcana", "electric-b3", "fire-b3"})
    ctx.record_burst_time("arcana", 2.5)

    # 10초 창: 만료 - 스쿼드 공댐 7.5%와 Awakened의 500만 남는다.
    registry = EffectRegistry()
    fire_trigger("full_burst_end", {"arcana": build()}, ctx, registry, time=12.6)
    assert round(registry.total_for("attack_damage_up", ELECTRIC_B3, now=12.6), 4) == 0.075
    assert registry.total_for("flat_atk", ELECTRIC_B3, now=12.6) == 500.0

    # 5초 창: 살아 있다 - Magician 1.80 + 스쿼드 0.075
    registry2 = EffectRegistry()
    fire_trigger("full_burst_end", {"arcana": build()}, ctx, registry2, time=7.6)
    assert round(registry2.total_for("attack_damage_up", ELECTRIC_B3, now=7.6), 4) == 1.875
    assert round(registry2.total_for("attack_damage_up", FIRE_B3, now=7.6), 4) == 0.075
    # Awakened 500 + Death 5000 + Strength 18000
    assert registry2.total_for("flat_atk", ELECTRIC_B3, now=7.6) == 23500.0
    assert registry2.total_for("flat_atk", FIRE_B3, now=7.6) == 5500.0


def test_magician_and_strength_skip_a_target_that_did_not_burst():
    ctx = _b3_context()
    ctx.burst_used_this_cycle.add("arcana")   # 수레바퀴는 있지만 대상이 안 터졌다
    ctx.record_burst_time("arcana", 2.5)
    registry = EffectRegistry()
    fire_trigger("full_burst_end", {"arcana": build()}, ctx, registry, time=7.6)
    assert round(registry.total_for("attack_damage_up", ELECTRIC_B3, now=7.6), 4) == 0.075
    assert registry.total_for("flat_atk", ELECTRIC_B3, now=7.6) == 5500.0
