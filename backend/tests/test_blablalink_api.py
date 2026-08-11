from app.blablalink_api import fetch_roster


class FakeCaller:
    """Records calls and replays canned data, standing in for a live session."""
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def call(self, endpoint, body):
        self.calls.append((endpoint, body))
        return self.responses[endpoint]


def test_fetch_roster_makes_three_calls_and_bundles_them():
    caller = FakeCaller({
        "GetUserCharacters": {"characters": [{"name_code": 5001, "lv": 400, "core": 3, "grade": 3}]},
        "GetUserCharacterDetails": {"character_details": [{"name_code": 5001, "grade": 3, "core": 3}]},
        "GetUserProfileOutpostInfo": {"outpost_info": {
            "recycle_room_researches": [{"tid": 1201, "lv": 170}],
            "synchro_level": 668,
            # Sits next to it in the real response and is NOT the synchro level -
            # picking this one up would be a plausible, silent mistake.
            "outpost_battle_level": 677,
        }},
    })
    out = fetch_roster(caller, "OPENID", area=81)

    # Owned first (its name_codes feed the details call), then details, then outpost.
    assert [c[0] for c in caller.calls] == [
        "GetUserCharacters", "GetUserCharacterDetails", "GetUserProfileOutpostInfo",
    ]
    # Every call carries the identity params.
    for _, body in caller.calls:
        assert body["intl_open_id"] == "OPENID"
        assert body["nikke_area_id"] == 81
    # Details is asked for exactly the owned name_codes.
    assert caller.calls[1][1]["name_codes"] == [5001]
    # Bundled shape is what assemble_roster consumes.
    assert out["owned"][0]["name_code"] == 5001
    assert out["character_details"][0]["name_code"] == 5001
    assert out["recycle_room_researches"] == [{"tid": 1201, "lv": 170}]
    # The account's synchro device level - what every Nikke fights union content
    # at, since union raid has no level correction.
    assert out["synchro_level"] == 668


def test_an_account_without_outpost_data_yields_no_researches_and_no_synchro_level():
    """Only Fienn's account was ever observed; another user's outpost may be absent.

    A missing synchro level must degrade to "no union stats" rather than break
    the sync: the level-400 stats do not depend on it.
    """
    caller = FakeCaller({
        "GetUserCharacters": {"characters": [{"name_code": 5001, "lv": 400, "core": 3, "grade": 3}]},
        "GetUserCharacterDetails": {"character_details": []},
        "GetUserProfileOutpostInfo": {},
    })
    out = fetch_roster(caller, "OPENID", area=81)

    assert out["recycle_room_researches"] == []
    assert out["synchro_level"] is None
