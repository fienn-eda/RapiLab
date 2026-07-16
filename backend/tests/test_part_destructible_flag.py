from app.squad_engine import SquadContext, SquadMember, boss_part_destructible


def _ctx(part_destructible):
    return SquadContext(
        [SquadMember("ark-ranger-black", burst_tier=3, element="Wind")],
        part_destructible=part_destructible,
    )


def test_context_defaults_part_destructible_false():
    assert SquadContext([SquadMember("x", 3, "Wind")]).part_destructible is False


def test_boss_part_destructible_condition_reads_flag():
    assert boss_part_destructible()(_ctx(True), "ark-ranger-black") is True
    assert boss_part_destructible()(_ctx(False), "ark-ranger-black") is False
