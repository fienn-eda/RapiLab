"""FastAPI surface for the deck recommender - the real POST /api/recommend
behind frontend/README.md's contract (plus excluded_slugs, per the roster
assembly design spec). Run from backend/: uvicorn app.api:app --reload

Both endpoints search via the budget-aware search_best_decks (canonical-order
scoring + top-K permutation refinement; large rosters get a candidate cut) -
see docs/superpowers/specs/2026-07-17-five-deck-allocation-design.md.
"""
import asyncio
import logging
from typing import Literal

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from app.cancellation import CancelToken, Cancelled
from app.deck_allocation import InfeasibleDraft, allocate_decks, recommend_from_draft
from app.deck_search import BossProfile, search_best_decks
from app.models import UserNikkeState
from app.overload_effects import NAME_TO_STAT
from app.roster_assembly import assemble_roster, load_directory, to_roster_json
from app.sim_pool import SimPool
from app.skill_rules.registry import MODE_VARIANTS
from app.stat_assembly import load_stat_tables
from app.supported_units import supported_units as _supported_units
from app.user_roster import load_roster

logger = logging.getLogger(__name__)
# uvicorn only configures its own uvicorn.* loggers; it never touches the
# root logger, which defaults to WARNING with no handler. Left alone, this
# logger's INFO records (the roster_sync telemetry below) would silently
# vanish under a real run. Configure this logger directly - not root - so
# uvicorn's own access/error lines are untouched and nothing double-logs.
if not logger.handlers:
    logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.INFO)


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
    # Everything that was neither a burst nor a normal attack - DoTs, per-shot
    # riders, self-cooldowned procs. The three add up to total_damage.
    skill_damage: float


class RecommendResponse(BaseModel):
    decks: list[DeckRecommendation]
    excluded_slugs: list[str]


class DraftUnit(BaseModel):
    slug: str
    locked: bool = False


class DraftDeck(BaseModel):
    units: list[DraftUnit]


class RecommendRaidRequest(RecommendRequest):
    num_decks: int = Field(5, ge=1, le=5)
    draft: list[DraftDeck] = []


class RaidDeck(DeckRecommendation):
    """A raid deck additionally reports which of its slugs were pinned by the
    caller's draft - not part of the shared DeckRecommendation shape since
    /api/recommend has no draft concept."""
    pinned_slugs: list[str] = []


class DraftAllocation(BaseModel):
    decks: list[RaidDeck]
    combined_total_damage: float
    leftover_slugs: list[str]


class RecommendRaidResponse(BaseModel):
    decks: list[RaidDeck]
    combined_total_damage: float
    excluded_slugs: list[str]
    leftover_slugs: list[str]
    within_draft: DraftAllocation | None = None
    baseline_total_damage: float | None = None


class SupportedUnit(BaseModel):
    slug: str
    name: str
    burst_tier: int
    element: str
    # Present only on an OWNED slug that the roster loader fans out into several
    # engine candidates (MODE_VARIANTS): the candidate slugs it stands for. A
    # deck in a result names candidates, never this slug, and a draft can only
    # seat a candidate - so a client that has to pick one concrete unit reads
    # this to know the choice is the engine's, not the player's.
    candidates: list[str] | None = None


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



def _recommend_sync(request: RecommendRequest, cancel) -> RecommendResponse:
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
        # search_best_decks takes no token; folding its pool is what stops it,
        # so the pool is registered before any batch starts.
        cancel.attach(pool)
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
                skill_damage=r["skill_damage"],
            )
            for r in results
        ],
        excluded_slugs=excluded,
    )


def _to_recs(decks, pinned_by_deck=None):
    pinned_by_deck = pinned_by_deck or [[] for _ in decks]
    return [
        RaidDeck(
            deck=d["deck"], total_damage=d["total_damage"],
            burst_damage=d["burst_damage"], normal_attack_damage=d["normal_attack_damage"],
            skill_damage=d["skill_damage"],
            pinned_slugs=pinned,
        )
        for d, pinned in zip(decks, pinned_by_deck)
    ]



def _recommend_raid_sync(request: RecommendRaidRequest, cancel) -> RecommendRaidResponse:
    _reject_unknown_overload_options(request.roster)
    specs, excluded = load_roster(request.roster)
    boss = BossProfile(
        element=request.boss.element,
        core_hittable=request.boss.core_hittable,
        enemy_def=request.boss.enemy_def,
        fight_duration=request.boss.fight_duration,
        part_destructible=request.boss.part_destructible,
    )
    if len(request.draft) > request.num_decks:
        raise HTTPException(
            422, f"draft has {len(request.draft)} decks but num_decks is {request.num_decks}")

    by_slug = {u.slug: u for u in specs}
    # A drafted seat may name an OWNED slug the engine models as several mode
    # candidates (MODE_VARIANTS) rather than a spec of its own - that is what the
    # palette offers, since it is what the roster owns. Such a seat travels as one
    # representative spec plus its alternatives, and the engine settles the mode
    # by completing the deck each way (deck_allocation's `_seed_choices`).
    alternatives = {}
    for base, variants in MODE_VARIANTS.items():
        loadable = tuple(by_slug[v] for v in variants if v in by_slug)
        if base not in by_slug and loadable:
            alternatives[base] = loadable

    # resolve draft slugs -> specs; unknown/unsupported slug is a client error
    draft, locked, requested = [], set(), []
    for deck in request.draft:
        seat = []
        for u in deck.units:
            options = alternatives.get(u.slug)
            if options is None and u.slug not in by_slug:
                raise HTTPException(422, f"draft references unusable slug: {u.slug}")
            seat.append(options[0] if options else by_slug[u.slug])
            requested.append(u.slug)
            if u.locked:
                locked.add(u.slug)
        draft.append(seat)
    # Keyed by the representative spec, which is what the draft now holds.
    alternatives = {options[0].slug: options for options in alternatives.values()}
    # Reported against what the CLIENT sent, not the resolved representative -
    # naming a slug the caller never used would be a riddle.
    if len(requested) != len(set(requested)):
        dups = {s for s in requested if requested.count(s) > 1}
        raise HTTPException(
            422, f"slug(s) appear in more than one draft deck: {sorted(dups)}")

    try:
        out = recommend_from_draft(specs, boss, num_decks=request.num_decks,
                                   draft=draft, locked=locked, workers="auto",
                                   alternatives=alternatives, cancel=cancel)
    except InfeasibleDraft as e:
        raise HTTPException(422, str(e))

    rec = out["recommended"]
    if not rec["decks"]:
        raise HTTPException(
            status_code=422,
            detail=f"no feasible deck from the usable roster (excluded: {excluded})",
        )
    rec_decks = _to_recs(rec["decks"], out["pinned_by_deck"])
    within = None
    if out["within_draft"] is not None:
        wd = out["within_draft"]
        within = DraftAllocation(
            decks=_to_recs(wd["decks"]),
            combined_total_damage=sum(d["total_damage"] for d in wd["decks"]),
            leftover_slugs=wd["leftover_slugs"],
        )
    return RecommendRaidResponse(
        decks=rec_decks,
        combined_total_damage=sum(d.total_damage for d in rec_decks),
        excluded_slugs=excluded,
        leftover_slugs=rec["leftover_slugs"],
        within_draft=within,
        baseline_total_damage=out["baseline_total_damage"],
    )


# How often the loop asks whether the client is still there. The search runs
# one to two minutes, so half a second is far finer than it needs to be and
# costs nothing; what it buys is that a cancel lands within a batch rather than
# after one.
DISCONNECT_POLL_SEC = 0.5

# Nginx's code for "client closed the request". Nothing reads this response -
# the socket is gone by definition - but a status says what happened in the
# access log, where a 200 would claim work that never finished.
CLIENT_CLOSED_REQUEST = 499


async def _cancel_when_client_leaves(http_request: Request, cancel: CancelToken):
    try:
        while not await http_request.is_disconnected():
            await asyncio.sleep(DISCONNECT_POLL_SEC)
        cancel.cancel()
    except asyncio.CancelledError:
        pass


async def _run_cancellable(http_request: Request, work, *args):
    """Run a search in a worker thread while the loop watches the connection.

    The searches are ordinary blocking code, so they cannot be asked to stop
    the way async code can - they take a token instead, and the pool they build
    registers with it. Measured before this existed: a disconnected request kept
    eight workers busy to completion.
    """
    cancel = CancelToken()
    watcher = asyncio.ensure_future(_cancel_when_client_leaves(http_request, cancel))
    try:
        return await run_in_threadpool(work, *args, cancel)
    except Cancelled:
        raise HTTPException(CLIENT_CLOSED_REQUEST, "client closed the request")
    finally:
        watcher.cancel()


@app.post("/api/recommend", response_model=RecommendResponse)
async def recommend(request: RecommendRequest, http_request: Request) -> RecommendResponse:
    return await _run_cancellable(http_request, _recommend_sync, request)


@app.post("/api/recommend-raid", response_model=RecommendRaidResponse)
async def recommend_raid(
    request: RecommendRaidRequest, http_request: Request
) -> RecommendRaidResponse:
    return await _run_cancellable(http_request, _recommend_raid_sync, request)


@app.get("/api/supported-units", response_model=list[SupportedUnit])
def supported_units_route() -> list[SupportedUnit]:
    return [SupportedUnit(**u) for u in _supported_units()]


@app.post("/api/assemble-roster")
def assemble_roster_endpoint(
    request: AssembleRosterRequest,
    x_client_id: str | None = Header(default=None),
) -> dict:
    """Assemble a bookmarklet-collected roster. Stateless: the request body is
    never persisted - see the privacy posture in the sub-project 4 spec."""
    units, unmeasured = assemble_roster(_STAT_TABLES, _DIRECTORY,
                                        request.model_dump())
    # Aggregates only. Counting unknown name_codes is how we learn the
    # directory snapshot has gone stale against a newly released Nikke, and
    # counting unmeasured units is how we learn an account owns a combination
    # the ground truth never covered - one used to fail the whole request.
    logger.info(
        "roster_sync client=%s owned=%d assembled=%d unknown_name_codes=%d "
        "unmeasured=%d",
        x_client_id or "none",
        len(request.owned),
        len(units),
        sum(1 for o in request.owned if o.get("name_code") not in _KNOWN_NAME_CODES),
        len(unmeasured),
    )
    return to_roster_json(units, unmeasured)
