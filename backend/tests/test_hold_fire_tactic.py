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

from app.deck_search import (BossProfile, _summarize, deck_is_valid, evaluate_deck,
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

# 홀드의 **인과**(살릴 버프의 유무가 부호를 가른다)를 재는 두 덱 - 위의 둘과
# 같은 모양이고 캐리만 에이다다. 그녀로 재는 것은 부호가 게이지 2.0~6.0초 전
# 구간에서 안 바뀌기 때문이고(+4~5.4% 대 -3~4.5%), 미하라 쪽은 그 구간 안에서
# 뒤집혀 인과가 아니라 로테이션 속도를 재게 된다
# (`test_holding_mihara_IS_A_WASH_at_this_decks_computed_gauge` 참고).
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


def test_holding_ada_pays_ONLY_in_a_deck_that_can_preserve_her_buff():
    """같은 홀더를 두 덱에 앉힌 대조 - 갈리는 것은 아군 라운드 버프의 유무뿐이고,
    그것이 부호를 가른다. 홀드가 그 자체로 주는 것은 아무것도 없다.

    에이다로 재는 이유: 이 부등식은 로테이션 속도에 민감한데(아래 미하라 참고)
    그녀는 게이지 2.0~6.0초 전 구간에서 부호가 안 바뀐다.
    """
    ordering = _ordering(WITH_GRANTER_ADA, ADA)
    assert evaluate_deck_hold_fire_options(ordering, BOSS) == [
        frozenset(), frozenset({ADA})]
    plain = evaluate_deck(ordering, BOSS)
    held = evaluate_deck(ordering, BOSS, hold_fire={ADA})
    assert held["total_damage"] > plain["total_damage"]
    assert held["total_damage"] / plain["total_damage"] == pytest.approx(1.055, abs=0.01)

    bare = _ordering(WITHOUT_GRANTER_ADA, ADA)
    bare_plain = evaluate_deck(bare, BOSS)
    bare_held = evaluate_deck(bare, BOSS, hold_fire={ADA})
    assert bare_held["total_damage"] < bare_plain["total_damage"]
    assert (bare_held["total_damage"] / bare_plain["total_damage"]
            == pytest.approx(0.962, abs=0.01))


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


def test_holding_mihara_IS_A_WASH_at_this_decks_computed_gauge():
    """미하라의 홀드는 이 편성에서 **거의 정확히 본전**이다 - 지금 엔진의 판정을
    그대로 적는다. 값이 두 번 움직였고 **둘 다 게이지 때문**이다: 상수 2.4초이던
    2026-08-21 이전에 +2.15%, 게이지가 덱의 성질이 되며 이 덱이 3.1~4.4초(중앙값
    3.8)를 계산해 **-4.9%**, 그리고 헬름(애장품)의 「풀차지마다 아군 전체 게이지
    14.31% 충전」이 배선되며 중앙값 2.4초(1.6~3.0)로 내려와 **+0.05%**
    (2026-08-22). 세 번째는 앞 판본의 독스트링이 예고한 복귀 그대로다.

    부호가 게이지의 함수라는 것은 상수만 올려 확인했다 - 2.4에서 +2.15%, 2.8에서
    +3.41%, **3.2에서 -2.61%**, 6.0에서 -7.61%. 홀드가 버리는 평타는 그대로인데
    살린 라운드 버프가 갚아 주는 양이 로테이션이 느려질수록 줄어드는 것이
    메커니즘이다. **그 표로 위의 +0.05%를 예측하지 마라** - 옛 엔진에서 게이지가
    전 사이클 하나의 상수이던 때 잰 것이고, 지금은 사이클마다 다른 분포다
    (평상 1.6~3.0, 홀드 2.0~2.8 - 그 분포 차이 자체가 효과의 일부다). 표는 부호가
    게이지에 민감하다는 것만 말한다.

    ⚠ **이 덱으로 홀드의 인과를 재지 마라.** 전환점 바로 위에 앉아 있어서 게이지를
    건드리는 어떤 변경이든 부호를 뒤집는다 - 그건 홀드가 무엇을 하는지가 아니라
    로테이션 속도를 재는 것이다. 인과는
    `test_holding_ada_pays_ONLY_in_a_deck_that_can_preserve_her_buff`가 잰다.
    그래서 밴드도 그 형제 테스트와 같은 관례(abs=0.01)로 둔다 - **판별력은 안
    잃는다**(옛 값 0.951은 이 밴드에서도 실패한다). 다섯 자리로 못박으면 게이지를
    건드리는 다음 세션이 「숫자를 갱신하라」로 읽는데, 이 테스트가 말하려는 것은
    특정 고정점이 아니라 **본전**이다.
    """
    ordering = _ordering(WITH_GRANTER, MIHARA)
    plain = evaluate_deck(ordering, BOSS)
    held = evaluate_deck(ordering, BOSS, hold_fire={MIHARA})
    assert held["total_damage"] / plain["total_damage"] == pytest.approx(1.0, abs=0.01)


def test_the_player_can_declare_the_adds_are_handled_and_get_the_hold_back():
    # 잡몹이 나오는 보스라도 플레이어의 조작에 따라 평타를 멈출 수 있는 판이 있다
    # (Fienn, 2026-08-22). `spawns_adds`는 인카운터의 사실로 남고, 그 사실을
    # 감당하겠다는 선언은 플레이어의 것이다 - 그래서 필드가 둘이다.
    ordering = _ordering(WITH_GRANTER, MIHARA)
    boss = BossProfile(spawns_adds=True, hold_fire_despite_adds=True)
    assert evaluate_deck_hold_fire_options(ordering, boss) == [
        frozenset(), frozenset({MIHARA})]


def test_the_override_does_not_bypass_the_deck_gate():
    # 오버라이드는 인카운터 게이트만 연다. 살릴 라운드 버프가 없는 덱에서 홀드는
    # 여전히 확정 손해이므로 시뮬을 돌릴 값이 없다 - 오버라이드를 게이트 전체의
    # 우회로로 만들면 여기가 깨진다.
    ordering = _ordering(WITHOUT_GRANTER, MIHARA)
    boss = BossProfile(spawns_adds=True, hold_fire_despite_adds=True)
    assert evaluate_deck_hold_fire_options(ordering, boss) == [frozenset()]


def test_the_report_path_reports_the_hold_when_the_player_overrides_the_gate():
    # 게이트를 여는 것과 리포트 경로가 그 값을 실어 보내는 것은 다른 일이다 -
    # 인카운터 게이트가 들어올 때와 같은 이유로 짝을 지어 잰다.
    #
    # **채택되는지**를 보는 테스트는 에이다로 잰다. 미하라 덱은 전환점 바로 위라
    # (`test_holding_mihara_IS_A_WASH_at_this_decks_computed_gauge`) 게이지를
    # 건드리는 무관한 변경이 부호를 뒤집어 여기를 빨갛게 만든다. 에이다는 게이지
    # 2.0~6.0초 전 구간에서 부호가 안 바뀐다.
    ordering = _ordering(WITH_GRANTER_ADA, ADA)
    handled = BossProfile(element="Iron", fight_duration=180.0,
                          spawns_adds=True, hold_fire_despite_adds=True)
    assert evaluate_deck_best_seating(ordering, handled)["hold_fire"] == [ADA]


def test_the_override_is_inert_on_a_boss_without_adds():
    # 잡몹이 없으면 이 선언은 아무것도 안 바꾼다 - 켜 둔 채로 회차를 옮겨도 조용해야
    # 한다.
    ordering = _ordering(WITH_GRANTER, MIHARA)
    assert (evaluate_deck_hold_fire_options(
                ordering, BossProfile(hold_fire_despite_adds=True))
            == evaluate_deck_hold_fire_options(ordering, BossProfile()))


def test_the_chosen_hold_is_carried_out_as_a_play_instruction():
    # 좌석·톡톡이와 같은 계열이다 - 덱 목록만 봐서는 알 수 없고, 이 수를 두지 않으면
    # 위 수치가 안 나온다. _summarize가 안 실으면 점수만 조용히 오르고 플레이어는
    # 무엇을 해야 하는지 못 듣는다. 위 테스트와 같은 이유로 에이다로 잰다.
    ordering = _ordering(WITH_GRANTER_ADA, ADA)
    boss = BossProfile(element="Iron", fight_duration=180.0)
    summary = _summarize(ordering, evaluate_deck_best_seating(ordering, boss))
    assert summary["hold_fire_slugs"] == [ADA]


def test_a_deck_that_holds_nobody_carries_an_empty_instruction():
    # 홀드가 없으면 키가 아예 없는 것이 아니라 빈 목록이어야 한다 - 응답 모델이
    # 매번 읽는 자리다.
    ordering = _ordering(WITH_GRANTER_ADA, ADA)
    noisy = BossProfile(element="Iron", fight_duration=180.0, spawns_adds=True)
    summary = _summarize(ordering, evaluate_deck_best_seating(ordering, noisy))
    assert summary["hold_fire_slugs"] == []


def test_holding_a_transforming_unit_that_never_declared_its_release_is_refused():
    # Ada is allowed because she declared what the released shot is; a unit who
    # has not is a collision the engine must not resolve by guess.
    deck = ["miranda-signature", "liter", "crown", "snow-white", "helm-signature"]
    with pytest.raises(ValueError, match="released shot"):
        assemble_simulation_inputs(_ordering(deck, "snow-white"),
                                   hold_fire={"snow-white"})
