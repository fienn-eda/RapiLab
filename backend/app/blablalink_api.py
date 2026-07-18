"""Fetch a blablalink roster over an injected session.

The three endpoints and their param shape were confirmed by cross-account
reconnaissance (2026-07-19): GetUserCharacters -> owned, GetUserCharacterDetails
(name_codes: whole roster in one call) -> investment, GetUserProfileOutpostInfo
-> corporation research ranks. nikke_area_id is 81 for the international server
(NOT the ShiftyPad region id in a share-URL uid). The session is injected as a
SessionCaller so this module never handles credentials; see spec sub-project 4.
"""
from typing import Protocol


class SessionCaller(Protocol):
    def call(self, endpoint: str, body: dict) -> dict:
        """POST to api.blablalink.com/api/game/proxy/Game/<endpoint>; raise on code != 0."""
        ...


def fetch_roster(caller: SessionCaller, open_id: str, area: int = 81) -> dict:
    base = {"intl_open_id": open_id, "nikke_area_id": area}
    owned = caller.call("GetUserCharacters", dict(base)).get("characters", [])
    detail = caller.call(
        "GetUserCharacterDetails",
        {**base, "name_codes": [c["name_code"] for c in owned]},
    )
    outpost = caller.call("GetUserProfileOutpostInfo", dict(base))
    return {
        "owned": owned,
        "character_details": detail.get("character_details", []),
        "recycle_room_researches": outpost["outpost_info"]["recycle_room_researches"],
    }
