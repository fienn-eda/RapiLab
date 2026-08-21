"""Holding fire through your own Full Burst, so an ally's "for N round(s)" buff
survives it.

A round buff is spent BY a bullet. Not firing keeps it, so every skill hit in
the window lands under it - Mihara's chain DoT, Ein's Near Feathers. Real
in-game tactic (Fienn, 2026-08-18).

It is a PLAY DECISION, never a unit property: with no round buff to preserve,
holding fire only removes shots. That is why nothing switches it on by itself
and why the deck gate exists.
"""
import pytest

from app.deck_search import (BossProfile, deck_is_valid, evaluate_deck,
                             evaluate_deck_best_seating,
                             evaluate_deck_hold_fire_options, feasible_orderings)
from app.models import UserNikkeState
from app.roster import assemble_simulation_inputs
from app.skill_rules._helpers import (HOLD_FIRE_RELEASE_MARGIN, hold_fire_segments,
                                      round_buff_rule)
from app.skill_rules.registry import (deck_grants_ally_round_buffs,
                                      get_hold_fire_release_shots)
from app.user_roster import load_roster

BOSS = BossProfile(element="Iron", fight_duration=180.0)
RL = {"weapon": "RL", "damage_percent": 100.0, "charge_damage_percent": 250.0}
MIHARA = "mihara-bonding-chain"
WITH_GRANTER = ["miranda-signature", "liter", "crown", MIHARA, "helm-signature"]
WITHOUT_GRANTER = ["liter", "volume", "crown", MIHARA, "helm-signature"]

# 홀드의 **부호**를 재는 두 덱 - 위의 둘과 같은 모양이고 캐리만 에이다다.
#
# 캐리가 미하라가 아닌 이유: 게이지가 덱의 양이 되면서(`burst_gauge.fill_times`)
# 이 편성의 게이지가 상수 2.4초에서 사이클별 3.1~4.4초(중앙값 3.8)로 늘었고,
# 미하라의 홀드는 게이지 3.0초 부근에서 순이익에서 순손해로 넘어간다(상수를
# 2.4 -> 6.0으로 올려 가며 확인: +2.15% -> -7.6%). 그녀의 부호는 로테이션 속도에
# 달려 있어 여기서 못박을 값이 아니다 - ATK 스프레드로도 뒤집힌다는 것이 이미
# 기록돼 있다.
#
# 에이다는 같은 구간 전체에서 부호가 안 바뀐다(+4~5.4% 대 -3~4.5%). 이 테스트가
# 못박으려는 인과 - **살릴 버프의 유무가 부호를 가른다** - 를 타임라인과 무관하게
# 재현하는 쪽이다.
ADA = "ada-wong"
WITH_GRANTER_ADA = ["miranda-signature", "liter", "crown", ADA, "helm-signature"]
WITHOUT_GRANTER_ADA = ["liter", "volume", "crown", ADA, "helm-signature"]


class _Context:
    def __init__(self, bursts, windows):
        self.burst_times = {"unit": bursts}
        self.full_burst_windows = windows


def test_holding_throughout_fires_nothing_in_the_window():
    schedule = hold_fire_segments(RL, "unit", release_shots=0)
    (segment,) = schedule(_Context([2.5], [(2.6, 12.6)]), 180.0)
    assert (segment["start"], segment["end"]) == (2.6, 12.6)
    assert segment["profile"]["damage_percent"] == 0.0
    # One interval is twice the window, so the first shot would land past its end.
    assert 1.0 / segment["profile"]["rate_of_fire"] > segment["end"] - segment["start"]
    assert "until_shots" not in segment


def test_the_released_shot_lands_just_INSIDE_full_burst():
    # The window is half-open, so a shot exactly on the bell is outside it and
    # loses the Full Burst bonus the tactic exists to collect.
    schedule = hold_fire_segments(RL, "unit", release_shots=1)
    (segment,) = schedule(_Context([2.5], [(2.6, 12.6)]), 180.0)
    assert segment["until_shots"] == 1
    shot = segment["start"] + 1.0 / segment["profile"]["rate_of_fire"]
    assert shot == pytest.approx(12.6 - HOLD_FIRE_RELEASE_MARGIN)
    assert 2.6 <= shot < 12.6
    assert segment["profile"]["damage_percent"] == RL["damage_percent"]
    assert segment["profile"]["charge_damage_percent"] == RL["charge_damage_percent"]


def test_only_full_bursts_the_unit_opened_herself_are_held():
    # Two windows, one burst: the ally-opened window is not hers to hold.
    schedule = hold_fire_segments(RL, "unit", release_shots=0)
    segments = schedule(_Context([20.0], [(2.6, 12.6), (20.1, 30.1)]), 180.0)
    assert [s["start"] for s in segments] == [20.1]


def test_the_window_is_the_real_one_so_an_extension_counts():
    schedule = hold_fire_segments(RL, "unit", release_shots=0)
    (segment,) = schedule(_Context([2.5], [(2.6, 17.6)]), 180.0)   # +5 sec extension
    assert segment["end"] == 17.6


def test_the_table_says_who_plays_it_and_who_releases():
    assert get_hold_fire_release_shots(MIHARA) == 0
    assert get_hold_fire_release_shots("ein") == 1
    assert get_hold_fire_release_shots("ada-wong") == 1
    assert get_hold_fire_release_shots("snow-white") is None


def test_adas_released_shot_is_her_special_modification_not_a_plain_rl():
    # The charge she holds through the window IS the Special Modification shot,
    # so the hold REPLACES that one-shot segment rather than running beside it -
    # and the round is still unspent when she lets go, so it carries the whole
    # 1750% (250% weapon + 1500% skill), not her plain 250%.
    ordering = _ordering(["miranda-signature", "liter", "crown", "ada-wong",
                          "helm-signature"], "ada-wong")
    inputs = assemble_simulation_inputs(ordering, hold_fire={"ada-wong"})

    class _Context:
        burst_times = {"ada-wong": [2.6]}
        full_burst_windows = [(2.6, 12.6)]

    (segment,) = inputs["weapon_mode_schedules"]["ada-wong"](_Context(), 180.0)
    assert segment["until_shots"] == 1
    assert segment["profile"]["charge_damage_percent"] == 1750.0
    # Timing is the hold's, not the charge's: she lets go one frame inside the
    # close, whenever the x4 charge happened to finish.
    shot = segment["start"] + 1.0 / segment["profile"]["rate_of_fire"]
    assert shot == pytest.approx(12.6 - HOLD_FIRE_RELEASE_MARGIN)


def test_holding_ada_pays_in_a_deck_that_can_preserve_her_buff():
    deck = ["miranda-signature", "liter", "crown", "ada-wong", "helm-signature"]
    ordering = _ordering(deck, "ada-wong")
    assert evaluate_deck_hold_fire_options(ordering, BOSS) == [
        frozenset(), frozenset({"ada-wong"})]
    plain = evaluate_deck(ordering, BOSS)
    held = evaluate_deck(ordering, BOSS, hold_fire={"ada-wong"})
    assert held["total_damage"] > plain["total_damage"]


def test_the_gate_reads_the_rules_not_a_list_of_granter_slugs():
    ally = round_buff_rule("full_burst_enter", [("crit_rate", 0.5, ("top_atk", 1))])
    mine = round_buff_rule("per_shot", [("crit_rate", 0.5, "self")])
    assert deck_grants_ally_round_buffs({"a": [ally]})
    assert not deck_grants_ally_round_buffs({"a": [mine]})
    assert not deck_grants_ally_round_buffs({"a": []})


def _nikke(slug, carry):
    return UserNikkeState.model_validate({
        "character_slug": slug, "level": 200, "core_level": 0, "hp": 1_000_000.0,
        "atk": 95_000.0 if slug == carry else 55_000.0, "def_": 3_000.0,
        "skill_levels": {"skill1": 10, "skill2": 10, "burst": 10}})


def _ordering(deck, carry):
    specs, excluded = load_roster([_nikke(s, carry) for s in deck])
    assert not excluded, excluded
    return next(o for o in feasible_orderings(specs)
                if {u.slug for u in o} == set(deck) and deck_is_valid(o))


def test_a_deck_with_nobody_to_preserve_a_buff_for_is_never_offered_the_hold():
    assert evaluate_deck_hold_fire_options(
        _ordering(WITHOUT_GRANTER, MIHARA), BOSS) == [frozenset()]


def test_a_deck_with_a_granter_and_a_holder_is_offered_both():
    options = evaluate_deck_hold_fire_options(_ordering(WITH_GRANTER, MIHARA), BOSS)
    assert options == [frozenset(), frozenset({MIHARA})]


def test_a_deck_with_a_granter_but_no_holder_is_not_offered_the_hold():
    deck = ["miranda-signature", "liter", "crown", "snow-white", "helm-signature"]
    assert evaluate_deck_hold_fire_options(
        _ordering(deck, "snow-white"), BOSS) == [frozenset()]


def test_a_boss_that_spawns_adds_is_never_offered_the_hold():
    # 잡몹이 주기적으로 나오는 보스에서는 평타를 멈출 수 없다 - 살릴 라운드 버프가
    # 있어도 그 창 동안 잡몹을 치워야 하므로 택틱 자체가 성립하지 않는다
    # (Fienn, 2026-08-20, 솔로 40시즌). 덱 게이트와 같은 이유로 후보를 아예 안 낸다:
    # 시뮬을 돌려 봐야 지는 선택지다.
    ordering = _ordering(WITH_GRANTER, MIHARA)
    assert evaluate_deck_hold_fire_options(
        ordering, BossProfile(spawns_adds=True)) == [frozenset()]


def test_the_report_path_reports_no_hold_against_a_boss_that_spawns_adds():
    # 게이트가 있어도 리포트 경로가 보스를 안 넘기면 결과에는 홀드가 그대로 남는다 -
    # `effective_range_band`가 정확히 그렇게 사라졌었다.
    # 조용한 쪽이 홀드를 **실제로 고르는** 덱이어야 아래 두 줄이 대조가 된다 -
    # 안 고르는 덱이면 두 줄 다 무조건 통과한다.
    ordering = _ordering(WITH_GRANTER_ADA, ADA)
    quiet = BossProfile(element="Iron", fight_duration=180.0)
    noisy = BossProfile(element="Iron", fight_duration=180.0, spawns_adds=True)

    assert evaluate_deck_best_seating(ordering, quiet)["hold_fire"] == [ADA]
    assert "hold_fire" not in evaluate_deck_best_seating(ordering, noisy)


def test_the_adds_gate_is_the_encounters_call_not_the_decks():
    # 같은 덱이 잡몹 없는 보스에서는 여전히 홀드를 제안받는다 - 게이트가 덱에
    # 박히면 보스를 바꿔도 안 돌아온다.
    ordering = _ordering(WITH_GRANTER, MIHARA)
    assert evaluate_deck_hold_fire_options(ordering, BossProfile()) == [
        frozenset(), frozenset({MIHARA})]


def test_holding_pays_when_there_is_a_buff_to_preserve_and_costs_when_there_is_not():
    # 같은 홀더를 두 덱에 앉힌 대조다 - 갈리는 것은 아군 라운드 버프의 유무뿐.
    ordering = _ordering(WITH_GRANTER_ADA, ADA)
    plain = evaluate_deck(ordering, BOSS)
    held = evaluate_deck(ordering, BOSS, hold_fire={ADA})
    assert held["total_damage"] > plain["total_damage"]

    bare = _ordering(WITHOUT_GRANTER_ADA, ADA)
    assert (evaluate_deck(bare, BOSS, hold_fire={ADA})["total_damage"]
            < evaluate_deck(bare, BOSS)["total_damage"])


def test_holding_a_transforming_unit_that_never_declared_its_release_is_refused():
    # Ada is allowed because she declared what the released shot is; a unit who
    # has not is a collision the engine must not resolve by guess.
    deck = ["miranda-signature", "liter", "crown", "snow-white", "helm-signature"]
    with pytest.raises(ValueError, match="released shot"):
        assemble_simulation_inputs(_ordering(deck, "snow-white"),
                                   hold_fire={"snow-white"})
