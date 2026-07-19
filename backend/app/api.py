"""FastAPI surface for the deck recommender - the real POST /api/recommend
behind frontend/README.md's contract (plus excluded_slugs, per the roster
assembly design spec). Run from backend/: uvicorn app.api:app --reload

Both endpoints search via the budget-aware search_best_decks (canonical-order
scoring + top-K permutation refinement; large rosters get a candidate cut) -
see docs/superpowers/specs/2026-07-17-five-deck-allocation-design.md.
"""
import logging
from typing import Literal

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.deck_allocation import allocate_decks
from app.deck_search import BossProfile, search_best_decks
from app.models import UserNikkeState
from app.overload_effects import NAME_TO_STAT
from app.roster_assembly import assemble_roster, load_directory, to_roster_json
from app.sim_pool import SimPool
from app.stat_assembly import load_stat_tables
from app.user_roster import load_roster

logger = logging.getLogger(__name__)


class BossProfileIn(BaseModel):
    element: Literal["Fire", "Water", "Wind", "Iron", "Electric"] | None = None
    core_hittable: bool = False
    enemy_def: float = 0.0
    fight_duration: float = 180.0
    part_destructible: bool = False


class RecommendRequest(BaseModel):
    roster: list[UserNikkeState]
    boss: BossProfileIn
    top_n: int = Field(default=5, ge=1)


class DeckRecommendation(BaseModel):
    deck: list[str]
    total_damage: float
    burst_damage: float
    normal_attack_damage: float


class RecommendResponse(BaseModel):
    decks: list[DeckRecommendation]
    excluded_slugs: list[str]


class RecommendRaidRequest(RecommendRequest):
    num_decks: int = Field(5, ge=1, le=5)


class RecommendRaidResponse(BaseModel):
    decks: list[DeckRecommendation]
    combined_total_damage: float
    excluded_slugs: list[str]
    leftover_slugs: list[str]


class AssembleRosterRequest(BaseModel):
    """The three raw blablalink payloads the bookmarklet collects, verbatim."""
    owned: list[dict]
    character_details: list[dict]
    recycle_room_researches: list[dict]


app = FastAPI(title="NIKKE Deck Builder")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Reference tables are read-only and identical for every request, so load once.
_STAT_TABLES = load_stat_tables()
_DIRECTORY = load_directory()
_KNOWN_NAME_CODES = {e["name_code"] for e in _DIRECTORY}


def _reject_unknown_overload_options(roster: list[UserNikkeState]) -> None:
    """A mistyped overload option name is a client input error, not a unit to
    silently exclude - reject it at the boundary so the deep engine ValueError
    (overload_effects) never surfaces as a 500. Valid names come from the
    engine's NAME_TO_STAT, so this list stays in sync automatically."""
    invalid = sorted(
        {option.name
         for state in roster
         for option in state.overload_options
         if option.name not in NAME_TO_STAT}
    )
    if invalid:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Unknown overload option name(s): {invalid}. "
                f"Valid names: {sorted(NAME_TO_STAT)}."
            ),
        )


@app.post("/api/recommend", response_model=RecommendResponse)
def recommend(request: RecommendRequest) -> RecommendResponse:
    _reject_unknown_overload_options(request.roster)
    specs, excluded = load_roster(request.roster)
    boss = BossProfile(
        element=request.boss.element,
        core_hittable=request.boss.core_hittable,
        enemy_def=request.boss.enemy_def,
        fight_duration=request.boss.fight_duration,
        part_destructible=request.boss.part_destructible,
    )
    # SimPool only spawns worker processes for big batches (large rosters);
    # small requests run inline at zero pool cost.
    with SimPool(specs, boss, workers="auto") as pool:
        results = search_best_decks(specs, boss, top_n=request.top_n, pool=pool)
    if not results:
        raise HTTPException(
            status_code=422,
            detail=(
                "No feasible 5-unit deck (burst tiers 1, 2 and 3 all required) "
                f"in the usable roster. Excluded (not yet supported): {excluded}."
            ),
        )
    return RecommendResponse(
        decks=[
            DeckRecommendation(
                deck=r["deck"], total_damage=r["total_damage"],
                burst_damage=r["burst_damage"], normal_attack_damage=r["normal_attack_damage"],
            )
            for r in results
        ],
        excluded_slugs=excluded,
    )


@app.post("/api/recommend-raid", response_model=RecommendRaidResponse)
def recommend_raid(request: RecommendRaidRequest) -> RecommendRaidResponse:
    _reject_unknown_overload_options(request.roster)
    specs, excluded = load_roster(request.roster)
    boss = BossProfile(
        element=request.boss.element,
        core_hittable=request.boss.core_hittable,
        enemy_def=request.boss.enemy_def,
        fight_duration=request.boss.fight_duration,
        part_destructible=request.boss.part_destructible,
    )
    result = allocate_decks(specs, boss, num_decks=request.num_decks, workers="auto")
    if not result["decks"]:
        raise HTTPException(
            status_code=422,
            detail=f"no feasible deck from the usable roster (excluded: {excluded})",
        )
    return RecommendRaidResponse(
        decks=[
            DeckRecommendation(
                deck=d["deck"], total_damage=d["total_damage"],
                burst_damage=d["burst_damage"], normal_attack_damage=d["normal_attack_damage"],
            )
            for d in result["decks"]
        ],
        combined_total_damage=sum(d["total_damage"] for d in result["decks"]),
        excluded_slugs=excluded,
        leftover_slugs=result["leftover_slugs"],
    )


@app.post("/api/assemble-roster")
def assemble_roster_endpoint(
    request: AssembleRosterRequest,
    x_client_id: str | None = Header(default=None),
) -> dict:
    """Assemble a bookmarklet-collected roster. Stateless: the request body is
    never persisted - see the privacy posture in the sub-project 4 spec."""
    units = assemble_roster(_STAT_TABLES, _DIRECTORY, request.model_dump())
    # Aggregates only. Counting unknown name_codes is how we learn the
    # directory snapshot has gone stale against a newly released Nikke.
    logger.info(
        "roster_sync client=%s owned=%d assembled=%d unknown_name_codes=%d",
        x_client_id or "none",
        len(request.owned),
        len(units),
        sum(1 for o in request.owned if o.get("name_code") not in _KNOWN_NAME_CODES),
    )
    return to_roster_json(units)
