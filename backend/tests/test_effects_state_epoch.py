"""state_epoch semantics: the epoch index changes exactly at the boundaries of
effects MATCHING the target (any stat), never at unrelated ones - the
invariant raid_simulator's stat-bundle memo (Stage 0.5) relies on."""
from app.effects import Effect, EffectRegistry

A = {"slug": "a", "element": "Fire"}
B = {"slug": "b", "element": "Water"}


def test_state_epoch_changes_only_at_matching_boundaries():
    reg = EffectRegistry()
    reg.add(Effect("atk_percent", 0.1, "squad", 5.0, "a"), applied_at=1.0)
    # self-scoped to "b": its boundaries must NOT create epochs for target A
    reg.add(Effect("crit_rate", 0.05, "self", None, "b"), applied_at=2.0)
    assert reg.state_epoch(A, 0.0) == reg.state_epoch(A, 0.9)   # before anything
    assert reg.state_epoch(A, 1.0) != reg.state_epoch(A, 0.9)   # start boundary
    assert reg.state_epoch(A, 3.0) == reg.state_epoch(A, 1.0)   # b's start is invisible to A
    assert reg.state_epoch(A, 6.0) != reg.state_epoch(A, 3.0)   # end boundary (1.0 + 5.0)
    assert reg.state_epoch(B, 2.0) != reg.state_epoch(B, 1.9)   # self-scope boundary for B


def test_state_epoch_covers_element_and_slugs_scopes():
    reg = EffectRegistry()
    reg.add(Effect("atk_percent", 0.1, "element:Fire", 4.0, "x"), applied_at=1.0)
    reg.add(Effect("flat_atk", 10.0, "slugs:b", 2.0, "x"), applied_at=7.0)
    assert reg.state_epoch(A, 1.0) != reg.state_epoch(A, 0.5)   # Fire matches A
    assert reg.state_epoch(B, 1.0) == reg.state_epoch(B, 0.5)   # not Water
    assert reg.state_epoch(B, 7.5) != reg.state_epoch(B, 6.5)   # slugs:b matches B
    assert reg.state_epoch(A, 7.5) == reg.state_epoch(A, 6.5)   # not A


def test_version_and_epoch_react_to_every_mutation_kind():
    reg = EffectRegistry()
    v0 = reg.version
    e0 = reg.state_epoch(A, 10.0)
    reg.add(Effect("atk_percent", 0.1, "squad", None, "x"), applied_at=5.0)
    v1 = reg.version
    assert v1 != v0
    assert reg.state_epoch(A, 10.0) != e0            # cache rebuilt, boundary seen
    reg.add_refreshing(Effect("atk_percent", 0.1, "squad", 3.0, "x"), applied_at=6.0)
    v2 = reg.version
    assert v2 != v1
    reg.truncate_open_ended("atk_percent", "x", now=8.0)
    assert reg.version != v2
