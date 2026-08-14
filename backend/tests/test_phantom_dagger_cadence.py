"""Phantom's Favorite Item dagger: the 60-shot proc constant is EXACT, and this
derives it from the skill's own numbers rather than trusting the comment.

`phantom_signature.VISION_PROC_SHOTS = 60` was entered as Fienn's in-game
cadence ("about 5 sec of fire"). Walking the skill text against a shot timeline
shows it is not an approximation at all: above a fire-rate cliff the dagger
reaches max stacks every 60th shot exactly, at every rate.

Why it comes out so clean. The dagger has two sources:

  1. "a normal attack on a Rapture that is NOT in the Calling Card state" - which
     grants a stack AND applies Calling Card, both for the same 5 sec. Because
     the two clocks are the SAME LENGTH, the moment Calling Card lapses and this
     source can fire again is the moment its own previous stack expires. Its net
     contribution past the first stack after each proc is therefore zero. That is
     the same cancellation that pins the BASE build at one stack forever - the
     Favorite Item does not break the symmetry, it adds a second source beside it.
  2. "after landing 30 normal attacks" - an independent metronome.

So source 2 is the only thing that accumulates, and reaching the 3-stack cap
takes exactly two of its ticks: 30 x 2 = 60.

Below 6.0 shots/sec (where 30 shots takes longer than the 5 sec stack lifetime)
source 2's own stacks expire before the next arrives and the dagger can NEVER
reach max - a real cliff, but unreachable: her AR fires 12/sec at base and the
game has no attack-speed debuff for your own units.

These tests exist so that a data update which moves the 30-shot threshold, the
5 sec durations, or the 3-stack cap fails loudly instead of leaving a constant
that silently no longer follows.
"""
import pytest

from app.skill_rules.phantom_signature import VISION_PROC_SHOTS, dagger_timeline

# Real skill level 10 values (lootandwaifus dollskills[0]), slot indices read
# off the parsed data rather than counted in the bullet text.
CALLING_CARD = {
    "description_value_02": "5",    # Calling Card lasts 5 sec
    "description_value_03": "25.75",  # Hit Rate per dagger stack
    "description_value_04": "3",    # Thief's Dagger stacks up to 3
    "description_value_05": "5",    # ...and lasts for 5 sec
    "description_value_06": "30",   # the Favorite Item source: every 30 normals
}
VALUES = {"calling_card": CALLING_CARD}


def dagger_procs(shot_times, values=VALUES):
    """The module's own walk - deliberately NOT a second copy of it here, so the
    derivation these tests pin is the one the encoding actually runs."""
    return dagger_timeline(shot_times, values)[1]


def even_shots(rate, duration=300.0):
    interval = 1.0 / rate
    return [i * interval for i in range(1, int(duration * rate))]


def proc_gaps_in_shots(shots, procs):
    index = {t: i for i, t in enumerate(shots)}
    return [index[b] - index[a] for a, b in zip(procs, procs[1:])]


CLIFF = 6.0  # = 30 shots / 5 sec: below this the dagger can never reach max


@pytest.mark.parametrize("rate", [6.1, 8.0, 12.0, 20.0, 40.0])
def test_proc_cadence_is_exactly_the_encoded_constant(rate):
    """Above the cliff the gap is the constant at EVERY rate - which is what
    makes 60 exact rather than a fit to one deck."""
    shots = even_shots(rate)
    procs = dagger_procs(shots)
    gaps = proc_gaps_in_shots(shots, procs)
    assert gaps, f"no procs at {rate}/sec"
    assert set(gaps) == {VISION_PROC_SHOTS}, (
        f"at {rate} shots/sec the dagger procs every {sorted(set(gaps))} shots, "
        f"but phantom_signature.VISION_PROC_SHOTS says {VISION_PROC_SHOTS}"
    )


def test_the_constant_is_two_ticks_of_the_favorite_item_source():
    """The derivation in one line: source 1 nets zero past the first stack, so
    the cap is reached on source 2's second tick."""
    source_two_shots = int(float(CALLING_CARD["description_value_06"]))
    cap = int(float(CALLING_CARD["description_value_04"]))
    assert VISION_PROC_SHOTS == source_two_shots * (cap - 1)


def test_source_one_and_calling_card_share_a_clock():
    """The cancellation the derivation rests on: the stack source 1 grants and
    the Calling Card that gates it expire together. If a data update ever
    separated them, source 1 would start contributing and 60 would be wrong."""
    assert (CALLING_CARD["description_value_05"]
            == CALLING_CARD["description_value_02"])


@pytest.mark.parametrize("rate", [3.0, 5.0, 5.9, CLIFF])
def test_below_the_cliff_the_dagger_never_reaches_max(rate):
    """At or under 30 shots per stack lifetime, source 2's own stacks expire
    before the next one lands. Unreachable for her AR (12/sec base), but it is
    the one place the encoded constant would be wrong, so it is pinned."""
    assert dagger_procs(even_shots(rate)) == []


def test_cliff_is_where_the_two_durations_cross():
    source_two_shots = int(float(CALLING_CARD["description_value_06"]))
    stack_seconds = float(CALLING_CARD["description_value_05"])
    assert CLIFF == source_two_shots / stack_seconds
