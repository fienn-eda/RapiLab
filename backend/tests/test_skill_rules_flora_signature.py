"""Flora's Favorite Item build - the Max-HP bump at Burst Stage 2 entry drives a
self-contained shield combo that turns her into a real ATK buffer."""
from app.effects import EffectRegistry
from app.skill_rules.flora_signature import build_flora_signature_rules
from app.squad_engine import SquadContext, SquadMember, fire_trigger

# lootandwaifus dollskills, level 10, slots numbered left-to-right over EVERY
# number in the text - including the literal "Burst Stage 2" (petunia slot 06)
# and Iris's "90%" HP threshold (iris slot 01), which are trigger wording rather
# than buff values. Numbering them keeps the doll's Iris slots aligned with base
# Flora's ShiftyPad slots (01=90, 04=30.97).
PETUNIA = {
    "description_value_01": "1", "description_value_02": "4",
    "description_value_03": "5", "description_value_04": "100",
    "description_value_05": "1", "description_value_06": "2",
    "description_value_07": "15.01", "description_value_08": "2",
}
IRIS = {
    "description_value_01": "90", "description_value_02": "10.22",
    "description_value_03": "10", "description_value_04": "30.97",
    "description_value_05": "10", "description_value_06": "45.12",
    "description_value_07": "10",
}
SECRET_GARDEN = {
    "description_value_01": "10.45", "description_value_02": "42.39",
    "description_value_03": "10", "description_value_04": "85.86",
    "description_value_05": "10",
}
CASTER_ATK = 60_000.0
CASTER_MAX_HP = 1_000_000.0
FLORA_SIG = {
    "petunia": PETUNIA, "iris": IRIS, "secret_garden": SECRET_GARDEN,
    "caster_atk": CASTER_ATK, "caster_max_hp": CASTER_MAX_HP,
}

SELF = {"slug": "flora-signature", "element": "Electric"}
ALLY = {"slug": "ally-b3", "element": "Fire"}


def _ctx():
    return SquadContext([
        SquadMember("flora-signature", burst_tier=2, element="Electric", weapon="MG"),
        SquadMember("other-b2", burst_tier=2, element="Water", weapon="SMG"),
        SquadMember("ally-b3", burst_tier=3, element="Fire", weapon="AR"),
    ])


def _fire(trigger, burster=None, time=0.0, ctx=None):
    reg = EffectRegistry()
    ctx = ctx or _ctx()
    if burster is not None:
        ctx.last_burst_slug = burster
    fire_trigger(trigger, {"flora-signature": build_flora_signature_rules(FLORA_SIG)},
                 ctx, reg, time)
    return reg


def test_iris_true_damage_is_permanent_like_the_base_build():
    reg = _fire("battle_start")
    assert round(reg.total_for("true_damage_up", ALLY, 0.0), 4) == 0.3097
    assert round(reg.total_for("true_damage_up", ALLY, 179.0), 4) == 0.3097


def test_stage_two_entry_grants_max_hp_for_two_seconds():
    reg = _fire("ally_burst_activate", burster="flora-signature", time=20.0)
    expected = CASTER_MAX_HP * 0.1501
    assert round(reg.total_for("flat_max_hp", ALLY, 20.0), 2) == round(expected, 2)
    assert reg.total_for("flat_max_hp", ALLY, 22.1) == 0.0  # 2 sec


def test_stage_two_entry_also_grants_the_shield_combo_atk_for_ten_seconds():
    # Max HP up WITHOUT healing drops every ally below 90% HP, which fires
    # Iris's shield, which fires the Favorite Item's ATK bullet (Fienn, 2026-07-24).
    reg = _fire("ally_burst_activate", burster="flora-signature", time=20.0)
    expected = CASTER_ATK * 0.4512
    assert round(reg.total_for("flat_atk", ALLY, 20.0), 2) == round(expected, 2)
    assert round(reg.total_for("flat_atk", ALLY, 29.9), 2) == round(expected, 2)
    assert reg.total_for("flat_atk", ALLY, 30.1) == 0.0  # 10 sec


def test_stage_two_bullets_fire_even_when_another_burst2_ally_takes_the_slot():
    reg = _fire("ally_burst_activate", burster="other-b2", time=20.0)
    assert round(reg.total_for("flat_max_hp", ALLY, 20.0), 2) == round(CASTER_MAX_HP * 0.1501, 2)
    assert round(reg.total_for("flat_atk", ALLY, 20.0), 2) == round(CASTER_ATK * 0.4512, 2)


def test_stage_two_bullets_do_not_fire_on_another_tier_burst():
    reg = _fire("ally_burst_activate", burster="ally-b3", time=20.0)
    assert reg.total_for("flat_max_hp", ALLY, 20.0) == 0.0
    assert reg.total_for("flat_atk", ALLY, 20.0) == 0.0


def _shielded_ctx():
    """크라운은 아군 전체에게 쉴드를 놓는다 (SHIELD_PROVIDER_SLUGS)."""
    return SquadContext([
        SquadMember("flora-signature", burst_tier=2, element="Electric", weapon="MG"),
        SquadMember("crown", burst_tier=2, element="Water", weapon="SMG"),
        SquadMember("ally-b3", burst_tier=3, element="Fire", weapon="AR"),
    ])


def test_a_shielding_ally_keeps_the_atk_bullet_up_from_battle_start():
    # "이 유닛 앞에 쉴드가 놓이면"의 천장 분기. 엔진에 쉴드 이벤트가 없으므로
    # 덱에 쉴드를 놓는 아군이 있는지가 물을 수 있는 전부다 (크라운 Royal Attire와
    # 같은 논리).
    reg = _fire("battle_start", ctx=_shielded_ctx())
    expected = round(CASTER_ATK * 0.4512, 2)
    assert round(reg.total_for("flat_atk", ALLY, 0.0), 2) == expected
    assert round(reg.total_for("flat_atk", ALLY, 179.0), 2) == expected


def test_without_a_shielding_ally_the_atk_bullet_waits_for_her_own_combo():
    reg = _fire("battle_start")
    assert reg.total_for("flat_atk", ALLY, 0.0) == 0.0


def test_the_two_shield_paths_never_stack():
    # 같은 불릿이 두 경로로 걸리면 안 된다 - 아군이 쉴드를 놓으면 자기 콤보 경로는
    # 물러선다.
    reg = EffectRegistry()
    ctx = _shielded_ctx()
    rules = {"flora-signature": build_flora_signature_rules(FLORA_SIG)}
    fire_trigger("battle_start", rules, ctx, reg, 0.0)
    ctx.last_burst_slug = "flora-signature"
    fire_trigger("ally_burst_activate", rules, ctx, reg, 20.0)
    assert round(reg.total_for("flat_atk", ALLY, 20.0), 2) == round(CASTER_ATK * 0.4512, 2)


def test_the_max_hp_bullet_is_unaffected_by_a_shielding_ally():
    reg = _fire("ally_burst_activate", burster="flora-signature", time=20.0,
                ctx=_shielded_ctx())
    assert round(reg.total_for("flat_max_hp", ALLY, 20.0), 2) == round(CASTER_MAX_HP * 0.1501, 2)


def test_burst_adds_squad_atk_on_top_of_its_true_damage():
    reg = _fire("own_burst_activate", time=20.0)
    assert round(reg.total_for("true_damage_up", ALLY, 20.0), 4) == 0.4239
    assert round(reg.total_for("flat_atk", ALLY, 20.0), 2) == round(CASTER_ATK * 0.8586, 2)
    assert reg.total_for("flat_atk", ALLY, 30.1) == 0.0


# "Affects all allies in the Peace of Mind state" - Peace of Mind is Petunia's
# first bullet, "self and both adjacent allies", granted at battle start and
# continuous. So the set is Flora plus her 2 neighbors: 3 of the 5 seats.
FIVE_UNIT_ATK = {"flora-signature": 100.0, "ally1": 400.0, "ally2": 300.0,
                 "ally3": 200.0, "ally4": 100.0}


def _five_unit_ctx(adjacency=None, shielder=None):
    allies = ["ally1", "ally2", "ally3", "ally4"]
    if shielder is not None:
        allies[allies.index(shielder)] = "crown"
    return SquadContext(
        [SquadMember("flora-signature", burst_tier=2, element="Electric", weapon="MG")]
        + [SquadMember(slug, burst_tier=3, element="Fire", weapon="AR") for slug in allies],
        base_atk={("crown" if slug == shielder else slug): atk
                  for slug, atk in FIVE_UNIT_ATK.items()},
        adjacency=adjacency,
    )


def _recipients(reg, ctx, stat, time):
    return {member.slug for member in ctx.members
            if reg.total_for(stat, {"slug": member.slug, "element": member.element}, time) > 0}


def test_peace_of_mind_max_hp_reaches_only_the_caster_and_two_allies():
    ctx = _five_unit_ctx()
    reg = _fire("ally_burst_activate", burster="flora-signature", time=20.0, ctx=ctx)
    assert _recipients(reg, ctx, "flat_max_hp", 20.0) == {"flora-signature", "ally1", "ally2"}


def test_peace_of_mind_atk_reaches_only_the_caster_and_two_allies():
    ctx = _five_unit_ctx()
    reg = _fire("ally_burst_activate", burster="flora-signature", time=20.0, ctx=ctx)
    assert _recipients(reg, ctx, "flat_atk", 20.0) == {"flora-signature", "ally1", "ally2"}


def test_the_shielded_atk_path_is_seated_too():
    # 천장 분기도 같은 불릿이다 - 여기만 squad로 남으면 쉴드를 놓는 아군이 있는
    # 덱에서만 5명에게 간다.
    ctx = _five_unit_ctx(shielder="ally2")
    reg = _fire("battle_start", ctx=ctx)
    assert _recipients(reg, ctx, "flat_atk", 0.0) == {"flora-signature", "ally1", "crown"}


def test_an_explicit_seating_decides_who_is_in_peace_of_mind():
    ctx = _five_unit_ctx(adjacency={"flora-signature": ["ally3", "ally4"]})
    reg = _fire("ally_burst_activate", burster="flora-signature", time=20.0, ctx=ctx)
    assert _recipients(reg, ctx, "flat_atk", 20.0) == {"flora-signature", "ally3", "ally4"}


def test_the_all_allies_bullets_stay_squad_wide():
    # Iris의 True Damage와 Secret Garden은 원문이 "Affects all allies"라 좌석과
    # 무관하다 - 좌석 스코프가 옆 불릿으로 번지면 여기서 잡힌다.
    everyone = {"flora-signature", "ally1", "ally2", "ally3", "ally4"}
    ctx = _five_unit_ctx()
    assert _recipients(_fire("battle_start", ctx=ctx), ctx, "true_damage_up", 0.0) == everyone
    ctx = _five_unit_ctx()
    reg = _fire("own_burst_activate", time=20.0, ctx=ctx)
    assert _recipients(reg, ctx, "flat_atk", 20.0) == everyone
