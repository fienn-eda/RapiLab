"""Fienn's recorded Annihilio solo raid - the single source of truth.

This is the only ground truth the simulator is scored against, and until
2026-07-27 it lived nowhere: every calibration session rebuilt the deck list in
conversation and threw it away, so the next session could not reproduce the
number it was asked to explain. A ratio nobody can re-derive is a claim, not a
measurement - `docs/roadmap.md` carried a "Cinderella 0.61x" that turned out to
be unreproducible, and off by a factor of three in the other direction.

The boss
--------
Annihilio is IRON code (철갑) - Wind attackers counter it. `element` names the
boss's OWN code, and `elements.py` runs Water>Fire>Wind>Iron>Electric>Water, so
Wind beats IRON. This field read "Water" until 2026-07-27, justified in a
docstring as "Water element so Wind attackers get advantage", which reads the
cycle backwards and instead made the boss Electric-weak. Resolve a boss element
against `elements.py`, never from prose - see docs/decisions.md.

The numbers
-----------
Per-unit damage in absolute damage points, as Fienn read them off the raid's
own damage log (2026-07-06), reported to 0.001B. Deck 4 was supplied first
(2026-07-27) and decks 1/2/3/5 the same day.

Known discrepancy, deliberately not reconciled: these 25 per-unit figures sum
to 34.896B, while the recorded 5-deck TOTAL is 34,767,622,294 (34.768B) - a
0.37% gap, larger than rounding 25 values at 0.001B can explain. Per-unit
ratios are what the calibration argues about and they are unaffected, so the
per-unit figures stand as given; the total is carried separately rather than
back-fitted to them. Worth asking Fienn about if a deck-level ratio ever turns
on 0.4%.

Mode-variant slugs (`registry.MODE_VARIANTS`) name the mode actually played.
Deck 2's Cinderella: Crystal Wave is recorded under her MG mode - the weapon
mode was never pinned in earlier sessions and is the documented reason deck 2's
ratio moved without any model change (see docs/roadmap.md).
"""

# The boss profile every deck below was fought against.
RECORD_BOSS = dict(element="Iron", core_hittable=True, part_destructible=True,
                   enemy_def=31784.0, fight_duration=180.0)

# The recorded 5-deck total, as reported. See the docstring's note on why this
# is not simply the sum of RECORD_DECKS.
RECORD_TOTAL = 34_767_622_294.0

B = 1_000_000_000.0

# deck name -> {slug: recorded damage}. Where RECORD_ROTATIONS below has no
# entry, seat order is unknown and the harness enumerates feasible orderings.
RECORD_DECKS = {
    "deck1": {
        "anchor-innocent-maid": 0.308 * B,
        "liberalio": 3.860 * B,
        "anis-star": 1.374 * B,
        "scarlet-black-shadow": 6.509 * B,
        "mast-romantic-maid": 0.393 * B,
    },
    "deck2": {
        "cinderella-crystal-wave-mg": 2.175 * B,
        "nayuta": 2.531 * B,
        "little-mermaid": 2.087 * B,
        "privaty-signature": 0.616 * B,
        "velvet": 0.334 * B,
    },
    "deck3": {
        "rapi-red-hood-b1": 1.130 * B,
        "crown": 0.489 * B,
        "rei-ayanami-tentative-name": 1.404 * B,
        "asuka-shikinami-langley-wille": 2.805 * B,
        "helm-signature": 0.234 * B,
    },
    "deck4": {
        "volume": 0.174 * B,
        "mint": 0.178 * B,
        "prika": 0.190 * B,
        "cinderella": 2.007 * B,
        "snow-white-heavy-arms": 1.683 * B,
    },
    "deck5": {
        "moran-signature": 0.384 * B,
        "ade-agent-bunny": 0.102 * B,
        "neon-vision-eye": 1.230 * B,
        "ark-ranger-black": 1.735 * B,
        "mihara-bonding-chain": 0.964 * B,
    },
}


# Units whose recorded number does NOT describe the rotation the engine models,
# so their ratio measures the mismatch and not the encoding. Chasing one is
# chasing the record, and without saying so here every session re-opens them:
# they sit at the top of "worst by ratio" precisely because they are wrong.
RECORD_CAVEATS = {
    "ade-agent-bunny":
        "Fienn tap-fired her in the recorded run - what players call "
        "'tok-tok-i' - instead of full charging every shot, so her recorded "
        "damage does not correspond to "
        "the full-charge rotation the engine simulates (Fienn, 2026-07-29). "
        "Her charge motion delay (0.35) and per-shot damage were both measured "
        "correct beforehand, which is why the residual had no other home.",
    "ark-ranger-black":
        "Her output is a floor/ceiling bracket, not a point estimate - part "
        "destruction fills her battery on a schedule nobody can know. See the "
        "BossProfile.part_destructible decision in docs/decisions.md.",
}


# How the bursts were actually spent, per deck (Fienn, 2026-07-28). `order` is
# the seat order, which the scheduler reads as priority within a burst tier, and
# `max_bursts` names the seats whose burst was held: 0 for a totem, seated for
# its passive kit alone, 1 for an opening burst and then never again.
#
# This matters more than a tie-break. Two of the five decks seat THREE Burst 3s
# and hold one of them, so the scheduler was covering Full Bursts with a burst
# that was never spent - the tier waits on the two remaining cooldowns instead,
# and the deck reaches Full Burst fewer times over the 180 sec.
#
# Decks 1 and 2 joined on 2026-07-29, so nothing is graded by argmax any more.
# Both turned out to BE their argmax ordering, which is why neither number
# moved - unlike decks 3/4/5, where argmax had been flattering the over-reading
# units by seating them at the top of their own range. Recording them is still
# worth it: the deck-1 spread was 0.932-0.990x and rested entirely on Scarlet
# (0.86x under the two orderings Fienn did not play), so "it happens to agree"
# and "it is what he played" were different claims until he was asked.
RECORD_ROTATIONS = {
    "deck1": {
        "order": ["anis-star", "anchor-innocent-maid", "mast-romantic-maid",
                  "liberalio", "scarlet-black-shadow"],
        "max_bursts": {},
    },
    "deck2": {
        "order": ["little-mermaid", "nayuta", "velvet",
                  "cinderella-crystal-wave-mg", "privaty-signature"],
        "max_bursts": {},
    },
    "deck3": {
        "order": ["rapi-red-hood-b1", "crown", "rei-ayanami-tentative-name",
                  "asuka-shikinami-langley-wille", "helm-signature"],
        "max_bursts": {"helm-signature": 0},
    },
    "deck4": {
        "order": ["volume", "prika", "mint", "snow-white-heavy-arms", "cinderella"],
        # Prika bursts the opening cycle only; Mint takes every tier-2 burst after.
        "max_bursts": {"prika": 1},
    },
    "deck5": {
        "order": ["moran-signature", "ade-agent-bunny", "neon-vision-eye",
                  "ark-ranger-black", "mihara-bonding-chain"],
        "max_bursts": {"mihara-bonding-chain": 0},
    },
}


def deck_total(name):
    return sum(RECORD_DECKS[name].values())
