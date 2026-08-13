"""Who receives a refill, and when.

A refill's trigger is an event the burst cycle already scheduled, so the
simulator - not the roster - resolves it: the roster assembles a deck and does
not know the encounter, the same split the boss-element gate on skill refunds
already uses.
"""
from app.attack_rate import AmmoRefill
from app.raid_simulator import resolve_ammo_refills


def _member(slug, grant=None):
    member = {"slug": slug}
    if grant is not None:
        member["ammo_refill_grant"] = grant
    return member


EVENTS = [
    {"type": "burst", "tier": 1, "slug": "noir", "time": 3.0},
    {"type": "full_burst_start", "time": 5.0},
    {"type": "full_burst_end", "time": 15.0},
    {"type": "burst", "tier": 3, "slug": "little-mermaid", "time": 44.0},
    {"type": "full_burst_start", "time": 46.0},
    {"type": "full_burst_end", "time": 56.0},
]


def test_a_squad_refill_reaches_every_member_including_the_caster():
    deck = [_member("noir", {"percent": 39.88, "scope": "squad",
                             "event": "full_burst_enter"}),
            _member("scarlet-black-shadow"), _member("liberalio")]
    refills = resolve_ammo_refills(deck, EVENTS)
    for slug in ("noir", "scarlet-black-shadow", "liberalio"):
        assert [r.time for r in refills[slug]] == [5.0, 46.0]
        assert refills[slug][0].percent == 39.88


def test_a_self_refill_reaches_nobody_else():
    deck = [_member("asuka-shikinami-langley-wille",
                    {"percent": 21.0, "scope": "self", "event": "own_burst"}),
            _member("liberalio")]
    refills = resolve_ammo_refills(deck, [
        {"type": "burst", "tier": 3,
         "slug": "asuka-shikinami-langley-wille", "time": 9.0}])
    assert [r.time for r in refills["asuka-shikinami-langley-wille"]] == [9.0]
    assert refills.get("liberalio", ()) == ()


def test_an_own_burst_refill_reads_the_casters_burst_times_not_full_burst():
    deck = [_member("little-mermaid", {"percent": 33.26, "scope": "squad",
                                       "event": "own_burst"}),
            _member("liberalio")]
    refills = resolve_ammo_refills(deck, EVENTS)
    assert [r.time for r in refills["liberalio"]] == [44.0]


def test_a_deck_with_no_grant_gets_no_refills():
    deck = [_member("liberalio"), _member("scarlet-black-shadow")]
    assert resolve_ammo_refills(deck, EVENTS) == {}
