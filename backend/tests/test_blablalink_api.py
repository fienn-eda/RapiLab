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
        "GetUserProfileOutpostInfo": {"outpost_info": {"recycle_room_researches": [{"tid": 1201, "lv": 170}]}},
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


def test_an_account_without_outpost_data_yields_no_researches():
    """Only Fienn's account was ever observed; another user's outpost may be absent."""
    caller = FakeCaller({
        "GetUserCharacters": {"characters": [{"name_code": 5001, "lv": 400, "core": 3, "grade": 3}]},
        "GetUserCharacterDetails": {"character_details": []},
        "GetUserProfileOutpostInfo": {},
    })
    out = fetch_roster(caller, "OPENID", area=81)

    assert out["recycle_room_researches"] == []
