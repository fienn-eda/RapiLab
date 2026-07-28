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
from app.deck_evaluation import InfeasibleDeck, evaluate_decks
from app.deck_search import BossProfile, search_best_decks
from app.engine_version import engine_version
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
    # 클라이언트가 결과를 입력 해시로 캐싱한다. 어떤 엔진이 낸 답인지 같이
    # 실어주지 않으면 엔진을 고친 뒤에도 낡은 수치가 캐시에서 계속 나온다.
    engine_version: str


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
    engine_version: str


class EvaluateDeckIn(BaseModel):
    """평가할 고정 편성 하나와 그 덱이 맞설 보스.

    보스가 덱 안에 있는 이유는 유니온 레이드다 - 3회 전투의 보스 속성을 유저가
    전투마다 고른다. 필드를 다시 선언하지 않고 BossProfileIn을 그대로 품어서,
    엔진이 보스 플래그를 늘려도 고칠 곳이 한 군데로 남는다."""
    units: list[str]
    boss: BossProfileIn


class EvaluateDecksRequest(BaseModel):
    roster: list[UserNikkeState]
    decks: list[EvaluateDeckIn]


class EvaluateDecksResponse(BaseModel):
    # pinned_slugs도 leftover_slugs도 없다: 잠금은 최적화의 개념이고, 안 고른
    # 유닛은 클라이언트가 이미 아는 것이라 배분 결과와 달리 알려줄 것이 없다.
    decks: list[DeckRecommendation]
    combined_total_damage: float
    excluded_slugs: list[str]
    engine_version: str


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
        engine_version=engine_version(),
    )


def _variant_alternatives(specs):
    """A drafted seat may name an OWNED slug the engine models as several mode
    candidates (MODE_VARIANTS) rather than a spec of its own - that is what the
    palette offers, since it is what the roster owns. Such a seat travels as one
    representative spec plus its alternatives, and the engine settles the mode
    by completing the deck each way (deck_allocation's `_seed_choices`).

    Keyed by the MODE_VARIANTS base (what a client's draft/deck names a seat
    by), not yet by the representative spec's own slug - a caller resolves a
    seat against the client-sent base slug first, then rekeys to the chosen
    representative once every seat is settled (deck_allocation and
    deck_evaluation both key their `alternatives` argument that way)."""
    by_slug = {u.slug: u for u in specs}
    alternatives = {}
    for base, variants in MODE_VARIANTS.items():
        loadable = tuple(by_slug[v] for v in variants if v in by_slug)
        if base not in by_slug and loadable:
            alternatives[base] = loadable
    return by_slug, alternatives


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

    by_slug, alternatives = _variant_alternatives(specs)

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
        engine_version=engine_version(),
    )


def _evaluate_decks_sync(request: EvaluateDecksRequest, cancel) -> EvaluateDecksResponse:
    # 평가는 탐색이 없어 수 초에 끝난다. SimPool을 만들지 않으므로 토큰에
    # 접을 풀도 없다 - 인자는 _run_cancellable의 계약을 맞추기 위한 것.
    _reject_unknown_overload_options(request.roster)
    specs, excluded = load_roster(request.roster)
    if not request.decks:
        raise HTTPException(422, "평가할 덱이 없어요.")

    by_slug, alternatives = _variant_alternatives(specs)

    decks, bosses, requested = [], [], []
    for index, deck_in in enumerate(request.decks, start=1):
        if len(deck_in.units) != DECK_SIZE:
            raise HTTPException(
                422, f"{index}번 덱은 {len(deck_in.units)}명이에요. 덱마다 정확히 "
                     f"{DECK_SIZE}명이어야 해요.")
        seat = []
        for slug in deck_in.units:
            options = alternatives.get(slug)
            if options is None and slug not in by_slug:
                raise HTTPException(422, f"엔진이 쓸 수 없는 슬러그예요: {slug}")
            seat.append(options[0] if options else by_slug[slug])
            requested.append(slug)
        decks.append(seat)
        bosses.append(BossProfile(
            element=deck_in.boss.element,
            core_hittable=deck_in.boss.core_hittable,
            enemy_def=deck_in.boss.enemy_def,
            fight_duration=deck_in.boss.fight_duration,
            part_destructible=deck_in.boss.part_destructible,
        ))

    # 클라가 보낸 슬러그로 보고한다 - 해석된 대표 슬러그를 들이대면 유저가
    # 자기가 안 쓴 이름을 보게 된다.
    if len(requested) != len(set(requested)):
        dups = sorted({s for s in requested if requested.count(s) > 1})
        raise HTTPException(422, f"여러 덱에 겹쳐 들어간 니케가 있어요: {dups}")

    alternatives = {options[0].slug: options for options in alternatives.values()}
    try:
        out = evaluate_decks(decks, bosses, alternatives=alternatives)
    except InfeasibleDeck as e:
        # 세 티어가 다 있어도 인원 수 조합(ALLOWED_SHAPES)이 아니면 여전히
        # 불가능하다 - "1·2·3단계가 모두 필요하다"는 말은 거짓일 수 있으므로
        # 실제 허용 대형을 구체적으로 알려준다. 두 번째 원인(버퍼 좌석 충돌)도
        # 같은 문장에서 짚어서 원인마다 다른 예외를 새로 만들지 않는다.
        raise HTTPException(
            422, f"{e.deck_index + 1}번 덱은 성립하는 버스트 순서가 없어요. 버스트 "
                 f"1·2·3단계 인원 수가 1·1·3, 1·2·2, 2·1·2 중 하나가 아니거나, 같은 "
                 f"단계에 모더니아·벨벳처럼 버퍼로만 앉아야 하는 니케가 여럿이면 "
                 f"이렇게 돼요.")

    return EvaluateDecksResponse(
        decks=[DeckRecommendation(
            deck=d["deck"], total_damage=d["total_damage"],
            burst_damage=d["burst_damage"],
            normal_attack_damage=d["normal_attack_damage"],
            skill_damage=d["skill_damage"]) for d in out["decks"]],
        combined_total_damage=out["combined_total_damage"],
        excluded_slugs=excluded,
        engine_version=engine_version(),
    )


# 니케 한 덱은 5명 - 엔진의 고정 덱 크기.
DECK_SIZE = 5

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


@app.post("/api/evaluate-decks", response_model=EvaluateDecksResponse)
async def evaluate_decks_route(
    request: EvaluateDecksRequest, http_request: Request
) -> EvaluateDecksResponse:
    return await _run_cancellable(http_request, _evaluate_decks_sync, request)


@app.get("/api/supported-units", response_model=list[SupportedUnit])
def supported_units_route() -> list[SupportedUnit]:
    return [SupportedUnit(**u) for u in _supported_units()]


@app.get("/api/engine-version")
def engine_version_route() -> dict[str, str]:
    """클라이언트는 요청을 보내기 전에 결과 캐시를 조회하므로, 버전을 응답으로만
    받으면 조회 시점에 알 수가 없다. 그래서 GET으로도 낸다."""
    return {"engine_version": engine_version()}


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
