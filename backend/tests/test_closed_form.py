from dataclasses import replace

import pytest

from app import closed_form
from app.closed_form import (ASSUMED_CYCLE_SECONDS, FULL_BURST_SECONDS,
                             _SnapshotRegistry, _bursters, _cycle_seconds, _fire,
                             _shot_count, closed_form_score, score_with_diagnostics)
from app.deck_search import BossProfile
from app.effects import Effect, Pulse
from app.squad_engine import SkillRule, SquadContext, SquadMember
from tests.test_roster import (anis_star_spec, crown_spec, helm_spec,
                               rapi_red_hood_spec, takina_spec)


def _target(slug, element="Water"):
    return {"slug": slug, "element": element}


# --- uptime weighting: the whole reason this isn't a plain snapshot ---

def test_uptime_weighting_scales_a_timed_buff_by_its_share_of_the_cycle():
    registry = _SnapshotRegistry()
    half_cycle = ASSUMED_CYCLE_SECONDS / 2
    registry.add(Effect("atk_percent", 0.60, "squad", half_cycle, "buffer"), applied_at=0.0)
    assert registry.uptime_weighted_total("atk_percent", _target("attacker")) == pytest.approx(0.30)


def test_uptime_weighting_counts_a_permanent_buff_in_full():
    registry = _SnapshotRegistry()
    registry.add(Effect("atk_percent", 0.60, "squad", None, "buffer"), applied_at=0.0)
    assert registry.uptime_weighted_total("atk_percent", _target("attacker")) == pytest.approx(0.60)


def test_uptime_weighting_caps_a_buff_that_outlasts_the_cycle():
    registry = _SnapshotRegistry()
    registry.add(Effect("atk_percent", 0.60, "squad", ASSUMED_CYCLE_SECONDS * 5, "buffer"),
                 applied_at=0.0)
    assert registry.uptime_weighted_total("atk_percent", _target("attacker")) == pytest.approx(0.60)


def test_uptime_weighting_respects_scope():
    registry = _SnapshotRegistry()
    registry.add(Effect("atk_percent", 0.60, "self", None, "buffer"), applied_at=0.0)
    assert registry.uptime_weighted_total("atk_percent", _target("attacker")) == 0.0
    assert registry.uptime_weighted_total("atk_percent", _target("buffer")) == pytest.approx(0.60)


def test_uptime_weighting_ignores_other_stats():
    registry = _SnapshotRegistry()
    registry.add(Effect("crit_rate", 0.20, "squad", None, "buffer"), applied_at=0.0)
    assert registry.uptime_weighted_total("atk_percent", _target("attacker")) == 0.0


# --- _fire: a bullet the timeline-less context can't run must not sink the score ---

def _context():
    return SquadContext([SquadMember("a", 1, "Water"), SquadMember("b", 3, "Water")])


def test_fire_skips_a_raising_bullet_and_records_it():
    def explode(context, caster_slug, time, registry):
        raise KeyError("needs a shot timeline")

    def works(context, caster_slug, time, registry):
        registry.add(Effect("atk_percent", 0.5, "squad", None, caster_slug), applied_at=time)

    registry = _SnapshotRegistry()
    failures = []
    rules = {"a": [SkillRule(trigger="battle_start", action=explode),
                   SkillRule(trigger="battle_start", action=works)]}

    _fire("battle_start", rules, _context(), registry, failures)

    assert failures == [("a", "battle_start")]
    # the sibling bullet still landed - one bad bullet must not lose the rest
    assert registry.uptime_weighted_total("atk_percent", _target("b")) == pytest.approx(0.5)


def test_fire_ignores_rules_of_other_triggers():
    def works(context, caster_slug, time, registry):
        registry.add(Effect("atk_percent", 0.5, "squad", None, caster_slug), applied_at=time)

    registry = _SnapshotRegistry()
    _fire("battle_start", {"a": [SkillRule(trigger="full_burst_enter", action=works)]},
          _context(), registry, [])
    assert registry.uptime_weighted_total("atk_percent", _target("b")) == 0.0


# --- who bursts, and how fast the rotation turns ---

def _member(slug, tier, cooldown=20.0):
    return {"slug": slug, "burst_tier": tier, "element": "Water", "cooldown": cooldown}


def test_bursters_are_the_leftmost_member_of_each_tier():
    deck = [_member("b1", 1), _member("b2a", 2), _member("b2b", 2),
            _member("b3a", 3), _member("b3b", 3)]
    assert [m["slug"] for m in _bursters(deck)] == ["b1", "b2a", "b3a"]


def test_bursters_follow_deck_order_within_a_tier():
    deck = [_member("b1", 1), _member("b2b", 2), _member("b2a", 2), _member("b3b", 3)]
    assert [m["slug"] for m in _bursters(deck)] == ["b1", "b2b", "b3b"]


def test_cycle_length_is_the_slowest_burster_cooldown():
    bursters = [_member("b1", 1, cooldown=20.0), _member("b3", 3, cooldown=40.0)]
    assert _cycle_seconds(bursters, _SnapshotRegistry()) == pytest.approx(40.0)


def test_cooldown_reduction_shortens_the_cycle():
    bursters = [_member("b1", 1, cooldown=20.0), _member("b3", 3, cooldown=40.0)]
    registry = _SnapshotRegistry()
    registry.add_pulse(Pulse("burst_cooldown_reduction_sec", 6.0, "squad", "b1"))
    registry.add_pulse(Pulse("burst_cooldown_reduction_sec", 4.0, "squad", "b1"))
    assert _cycle_seconds(bursters, registry) == pytest.approx(30.0)


def test_cycle_never_shrinks_below_the_full_burst_window():
    bursters = [_member("b3", 3, cooldown=20.0)]
    registry = _SnapshotRegistry()
    registry.add_pulse(Pulse("burst_cooldown_reduction_sec", 999.0, "squad", "b1"))
    assert _cycle_seconds(bursters, registry) == pytest.approx(FULL_BURST_SECONDS)


def test_cycle_falls_back_when_no_burster_has_a_cooldown():
    assert _cycle_seconds([_member("b3", 3, cooldown=0.0)],
                          _SnapshotRegistry()) == pytest.approx(ASSUMED_CYCLE_SECONDS)


# --- shot count ---

def test_shot_count_is_memoized_per_weapon_and_fight():
    weapon = {"weapon": "AR", "max_ammo": 60, "reload_time": 1.5, "charge_time": 0.0}
    closed_form._shot_count_cache.clear()
    first = _shot_count(weapon, 180.0)
    assert first > 0
    assert len(closed_form._shot_count_cache) == 1
    assert _shot_count(dict(weapon), 180.0) == first
    assert len(closed_form._shot_count_cache) == 1  # same key, no second entry
    _shot_count(weapon, 90.0)
    assert len(closed_form._shot_count_cache) == 2  # fight duration is part of the key


def test_shot_count_grows_with_fight_duration():
    weapon = {"weapon": "AR", "max_ammo": 60, "reload_time": 1.5, "charge_time": 0.0}
    assert _shot_count(weapon, 180.0) > _shot_count(weapon, 90.0)


# --- end to end over real encoded units ---

def _deck():
    """A real (1,2,2) deck: 1 Burst-1, 2 Burst-2, 2 Burst-3."""
    return [anis_star_spec(), crown_spec(), takina_spec(), helm_spec(), rapi_red_hood_spec()]


def test_scoring_a_real_deck_needs_no_simulation_and_skips_nothing():
    score, failures = score_with_diagnostics(_deck(), BossProfile(element="Water"))
    assert score > 0
    # Every bullet of these encodings resolves on the timeline-less context. If
    # this starts failing, the estimate is silently ignoring part of the deck.
    assert failures == []


def test_higher_enemy_defense_lowers_the_score():
    deck = _deck()
    soft = closed_form_score(deck, BossProfile(element="Water", enemy_def=0.0))
    armored = closed_form_score(deck, BossProfile(element="Water", enemy_def=50_000.0))
    assert armored < soft


def test_a_longer_fight_scores_higher():
    deck = _deck()
    short = closed_form_score(deck, BossProfile(element="Water", fight_duration=90.0))
    long = closed_form_score(deck, BossProfile(element="Water", fight_duration=180.0))
    assert long > short


def test_elemental_advantage_raises_the_score():
    """Same deck, same boss - only the attacker's element differs."""
    boss = BossProfile(element="Fire")  # Water counters Fire
    deck = _deck()
    advantaged = closed_form_score(deck, boss)  # helm is Water
    # Iron has no advantage over Fire, and no ally buff in this deck is
    # element-scoped to Iron or Water, so the element bonus is the only change.
    neutral_deck = [replace(spec, element="Iron") if spec.slug == "helm" else spec
                    for spec in deck]
    neutral = closed_form_score(neutral_deck, boss)
    assert advantaged > neutral


def test_intra_tier_order_changes_the_score():
    """Only the tier's leftmost unit bursts, so swapping the two Burst-3s is a
    different deck - which is why callers score each ordering."""
    boss = BossProfile(element="Water")
    helm_first = _deck()
    rapi_first = helm_first[:3] + [helm_first[4], helm_first[3]]
    assert closed_form_score(rapi_first, boss) != closed_form_score(helm_first, boss)


def test_score_is_deterministic():
    deck = _deck()
    boss = BossProfile(element="Water")
    assert closed_form_score(deck, boss) == closed_form_score(deck, boss)
