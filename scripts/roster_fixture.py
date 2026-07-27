"""Rosters for the measurement scripts: the real synced one, or a synthetic stand-in.

Every perf number before 2026-07-25 was measured on `synthetic_roster` - the
first N supported slugs, all given identical stats. That is not a small
simplification. Against the real synced roster it differs on every axis that
decides a swap: uniform ATK 60,000 vs 82,895-144,793 (1.75x spread), uniform
skill 10/10/10 vs 23 distinct level combinations (10/10/10 down to 1/1/1), and
no overload at all vs 0-6 aggregated rows per unit. Uniform stats make same-tier
units nearly interchangeable, which is the condition that produces the MOST
near-tie swap verdicts - so synthetic numbers likely overstate how much work the
hill-climb has to do.

Prefer `real_roster`. Keep `synthetic_roster` for comparing against the older
measurements, and say which one a number came from.

The real roster is the app's own synced state, lifted from the browser's
localStorage as NikkeDraft[] (see tools/collect-blablalink/.gitignore for how it
gets there). Drafts are already slug-resolved - a unit whose Favorite Item is
owned arrives on its `-signature` slug - so nothing here re-derives identity.
Personal investment data: gitignored, local only, never committed.
"""
import json
from pathlib import Path

from app.models import UserNikkeState

REAL_ROSTER_JSON = (Path(__file__).resolve().parent.parent
                    / "tools" / "collect-blablalink" / "roster-drafts.json")


def _state_from_draft(draft):
    """One NikkeDraft (the frontend's string-typed form state) as a UserNikkeState.

    The collectible fields are optional because a draft saved before the sync
    carried them has neither - such a roster measures as if nobody had one
    equipped, which is what it was measured as all along. A re-sync fills them.
    """
    return UserNikkeState.model_validate({
        "character_slug": draft["character_slug"],
        "level": int(draft["level"]),
        "hp": float(draft["hp"]),
        "atk": float(draft["atk"]),
        "def_": float(draft["def_"]),
        "skill_levels": {k: int(v) for k, v in draft["skill_levels"].items()},
        "overload_options": [{"name": row["name"], "value": float(row["value"])}
                             for row in draft.get("overload_options", [])],
        "collectible_tid": int(draft.get("collectible_tid") or 0),
        "collectible_level": int(draft.get("collectible_level") or 0),
    })


def real_roster(path=REAL_ROSTER_JSON, limit=None):
    """The synced roster's UserNikkeStates, or None when it has not been saved.

    Returning None rather than raising lets a script fall back to synthetic and
    say so, instead of dying on a machine where nobody has synced yet.
    """
    path = Path(path)
    if not path.is_file():
        return None
    drafts = json.loads(path.read_text(encoding="utf-8"))
    states = [_state_from_draft(d) for d in drafts]
    return states[:limit] if limit else states


def synthetic_roster(limit, supported):
    """`limit` supported slugs at identical investment - the pre-2026-07-25 fixture.

    `supported` is supported_units()' output, passed in so this module does not
    import it (a script that only wants the real roster should not pay for the
    manifest scan).
    """
    return [
        UserNikkeState.model_validate({
            "character_slug": u["slug"], "level": 200,
            "hp": 1_000_000.0, "atk": 60_000.0, "def_": 3_000.0,
            "skill_levels": {"skill1": 10, "skill2": 10, "burst": 10},
        })
        for u in supported[:limit]
    ]
