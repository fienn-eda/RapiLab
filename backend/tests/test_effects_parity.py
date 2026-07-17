"""Parity net for the EffectRegistry segment-table rewrite (perf design spec,
2026-07-17): a FROZEN copy of the pre-rewrite naive total_for loop is compared
against registry.total_for for exact (bit-identical) equality - every scope
kind, refreshing truncation, open-ended closing, zero-length windows, and
queries interleaved with mutations (cache-invalidation coverage). The suite's
hundreds of exact numeric asserts are the end-to-end net; this file is the
targeted, adversarial one. Do not "modernize" naive_total_for - its point is
to stay identical to the old loop, insertion order and all."""
from app.effects import Effect, EffectRegistry, _matches_scope

A = {"slug": "a", "element": "Fire"}
B = {"slug": "b", "element": "Water"}


def naive_total_for(registry, stat, target, now):
    total = 0.0
    for effect, applied_at in registry._entries:
        if effect.stat != stat:
            continue
        if effect.duration is None:
            active = now >= applied_at
        else:
            active = applied_at <= now < applied_at + effect.duration
        if not active:
            continue
        if effect.scope == "self":
            if effect.source_slug == target["slug"]:
                total += effect.value
        elif _matches_scope(effect.scope, target):
            total += effect.value
    return total


def build_adversarial_registry():
    reg = EffectRegistry()
    reg.add(Effect("atk_percent", 0.1, "squad", None, "a"), applied_at=0.0)
    reg.add(Effect("atk_percent", 0.07, "self", 10.0, "a"), applied_at=1.0)
    reg.add(Effect("atk_percent", 0.03, "element:Water", 5.0, "b"), applied_at=2.0)
    reg.add(Effect("atk_percent", 0.11, "slugs:a,b", 4.0, "b"), applied_at=2.5)
    reg.add(Effect("crit_rate", 0.05, "squad", 3.0, "a"), applied_at=0.5)
    # Refreshing re-applications from one source truncate the previous window;
    # the same-timestamp one produces a zero-length window.
    for t in (3.0, 4.0, 5.0, 5.0):
        reg.add_refreshing(Effect("flat_atk", 100.0, "squad", 3.0, "a"), applied_at=t)
    # A different source must stay independent of the refresh chain above.
    reg.add_refreshing(Effect("flat_atk", 50.0, "squad", 2.0, "b"), applied_at=4.5)
    # Close the open-ended atk_percent from source "a" at t=8.
    reg.truncate_open_ended("atk_percent", "a", now=8.0)
    return reg


def probe_times(reg):
    boundaries = set()
    for effect, applied_at in reg._entries:
        boundaries.add(applied_at)
        if effect.duration is not None:
            boundaries.add(applied_at + effect.duration)
    probes = set()
    for b in boundaries:
        probes.update((b - 0.25, b, b + 0.25))
    probes.update(x * 0.5 for x in range(41))  # dense 0..20 grid
    return sorted(probes)


def assert_parity(reg):
    for stat in ("atk_percent", "crit_rate", "flat_atk", "never_granted"):
        for target in (A, B):
            for now in probe_times(reg):
                expected = naive_total_for(reg, stat, target, now)
                got = reg.total_for(stat, target, now)
                assert got == expected, (stat, target["slug"], now, got, expected)


def test_parity_on_adversarial_registry():
    assert_parity(build_adversarial_registry())


def test_parity_survives_mutations_after_queries():
    # assert_parity warms any cache; each later mutation - including in-place
    # duration truncations that never go through add() - must invalidate it.
    reg = build_adversarial_registry()
    assert_parity(reg)
    reg.add(Effect("atk_percent", 0.2, "squad", 6.0, "b"), applied_at=9.0)
    assert_parity(reg)
    reg.add_refreshing(Effect("flat_atk", 100.0, "squad", 3.0, "a"), applied_at=6.0)
    assert_parity(reg)
    reg.add(Effect("crit_rate", 0.02, "self", None, "b"), applied_at=1.0)
    reg.truncate_open_ended("crit_rate", "b", now=12.0)
    assert_parity(reg)
