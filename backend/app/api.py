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
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.cancellation import CancelToken, Cancelled
from app.cube_effects import CUBE_NAMES, DEFAULT_CUBE
from app.charge_window import (outcome, reload_intervenes, shot_interval,
                               shots_without_magazine_limit, thresholds)
from app.charge_window_inputs import (CALCULATOR_SLUGS, LIBERALIO_SLUG, Overrides,
                                      build_inputs, charge_speed_rolls_known)
from app.deck_allocation import InfeasibleDraft, allocate_decks, recommend_from_draft
from app.deck_evaluation import InfeasibleDeck, evaluate_decks
from app.deck_search import BossProfile, search_best_decks
from app.engine_version import engine_version
from app.miranda_targets import miranda_slug_in, miranda_target_report
from app.models import UserNikkeState
from app.overload_effects import NAME_TO_STAT, max_charge_speed_percent
from app.paths import frontend_dist
from app.raid_rotations import load_rotations
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
    # How far away this boss is fought. The band decides WHICH weapons are
    # inside their effective range and collect +0.30 on their normal attacks:
    # near pays SG/SMG, mid pays AR/MG, far pays SR, and a Rocket Launcher is
    # paid by none of them. None means "not known for this boss" and pays
    # nobody - see raid_simulator.EFFECTIVE_RANGE_BANDS.
    effective_range_band: Literal["near", "mid", "far"] | None = None
    # See BossProfile.pierce_hits_body_behind_core - only meaningful together
    # with core_hittable.
    pierce_hits_body_behind_core: bool = False
    # See BossProfile.core_diameter_px - only meaningful together with
    # core_hittable. Must be positive: zero or negative divides by zero or
    # invents a positive core-hit share for an impossible boss.
    core_diameter_px: float | None = Field(default=None, gt=0)
    # See BossProfile.elemental_interrupt_required. Inert on an element-less boss.
    elemental_interrupt_required: bool = False


class RotationBoss(BaseModel):
    """공지가 적은 보스 하나.

    앱이 해석하는 것은 `weakness`와 `range_band` 둘뿐이다 - 화면이 전자로 보스
    속성을 역산하고 후자를 적정거리에 그대로 얹는다. 둘 다 공지를 읽는 시점에
    스킬이 엔진 어휘로 옮겨 적으므로, 앱이 `stated`의 한글 산문을 파싱하지 않는다.

    `weakness`는 비워둘 수 없다 - 로더가 이미 거부하므로
    (raid_rotations.validate_rotations) 여기 닿는 값은 항상 5원소 중 하나다.
    `range_band`는 유니온 공지에만 있어 비어 있을 수 있고, 그때 적정거리는
    「모름」으로 남는다.

    `stated`는 공지 원문 기록이다. 자유 형식인 이유는 솔로 공지와 유니온 공지가
    서로 다른 항목을 적기 때문이다(솔로: 보스 속성·스쿼드 추천·공격 패턴 /
    유니온: 등급·거리).
    """
    name: str
    weakness: Literal["Fire", "Water", "Wind", "Iron", "Electric"]
    range_band: Literal["near", "mid", "far"] | None = None
    # 그 보스와 싸우며 화면에서 잰 코어 지름을 엔진 단위로 환산한 값. 안 잰
    # 보스는 None이고, 그때 코어히트율은 모델링되지 않는다 - 적격 평타가 전부
    # p=1.0을 받는 동작 그대로다.
    core_diameter_px: float | None = None
    stated: dict[str, str | list[str]] = {}


class RaidRotation(BaseModel):
    id: str
    raid: Literal["solo", "union"]
    title: str
    # 공지 본문이 종료 시각만 적는 경우가 있어 시작은 비어 있을 수 있다.
    starts_at: str | None = None
    ends_at: str
    source_url: str
    # `name`이 한국 서버 표기인지 영문명인지. 읽는 쪽이 알아야 한다.
    source_locale: Literal["ko", "en"]
    read_on: str
    bosses: list[RotationBoss]


class RaidRotationsResponse(BaseModel):
    schema_version: int
    rotations: list[RaidRotation]


def boss_profile(boss: BossProfileIn) -> BossProfile:
    """The request's boss as the engine's BossProfile.

    Every field of BossProfileIn is a BossProfile field of the same name, so
    this spreads rather than listing them. That is the point: three endpoints
    build this same object, and listing the fields is how `effective_range_band`
    reached the engine without reaching any of them (2026-07-31).
    """
    return BossProfile(**boss.model_dump())


class RecommendRequest(BaseModel):
    roster: list[UserNikkeState]
    boss: BossProfileIn
    top_n: int = Field(default=5, ge=1)
    # 어느 스탯 벌로 잴지. 솔로레이드는 전원 레벨 400 보정이고 유니온레이드는
    # 레벨 보정 자체가 없어 계정 싱크로 레벨로 싸운다. 엔드포인트로 가르지 않는
    # 이유는 `/api/recommend-raid`가 이름과 달리 솔로 탭의 5덱 배분이기
    # 때문이다 - 컨텐츠와 엔드포인트가 이미 어긋나 있어, 거기 정책을 걸면
    # 유니온 추천이 생기는 날 조용히 틀린다. 기본값이 곧 현행 동작이다.
    stat_basis: Literal["raid400", "actual"] = "raid400"


class DeckRecommendation(BaseModel):
    deck: list[str]
    total_damage: float
    burst_damage: float
    normal_attack_damage: float
    # Everything that was neither a burst nor a normal attack - DoTs, per-shot
    # riders, self-cooldowned procs. The three add up to total_damage.
    skill_damage: float
    # Seats the player has to hold back by hand for this order to be the one
    # that was scored (deck_search's `hold_burst_slugs`). Empty for nearly every
    # deck: the seat order is preferred playable whenever the scores tie, so
    # this only fills when holding the burst is what the higher score is FOR.
    hold_burst_slugs: list[str] = []


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
    # 탐색이 상한에 걸리지 않고 끝까지 갔는지. 기본 True - 이 필드를 모르는
    # 클라이언트에게 경고를 띄우지 않는다.
    swap_converged: bool = True
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
    # RecommendRequest의 같은 필드와 뜻이 같다. 이 엔드포인트는 유니온 탭만
    # 쓰므로 실제로 오는 값은 "actual"이지만, 기본값은 현행 동작으로 둔다.
    stat_basis: Literal["raid400", "actual"] = "raid400"


class EvaluateDecksResponse(BaseModel):
    # pinned_slugs도 leftover_slugs도 없다: 잠금은 최적화의 개념이고, 안 고른
    # 유닛은 클라이언트가 이미 아는 것이라 배분 결과와 달리 알려줄 것이 없다.
    decks: list[DeckRecommendation]
    combined_total_damage: float
    excluded_slugs: list[str]
    engine_version: str


class ChargeWindowOverrides(BaseModel):
    """What the user typed over the synced roster; omitted fields keep it."""
    charge_speed_lines: list[float] | None = None
    max_ammo_percent: float | None = None
    reload_speed_percent: float | None = None


class ChargeWindowRequest(BaseModel):
    slug: str
    roster: list[UserNikkeState]
    with_liberalio: bool = False
    overrides: ChargeWindowOverrides = Field(default_factory=ChargeWindowOverrides)
    # The wearer's harmony cube. Everywhere else in the app it is an assumption
    # (cube_effects.DEFAULT_CUBE); here it is a question worth asking, because a
    # Tactical Bear's rounds decide whether the magazine empties inside the
    # window - two different shot counts on the same gear.
    cube: str = DEFAULT_CUBE


class ShotOutcome(BaseModel):
    low_shots: int
    low_probability: float
    high_shots: int
    high_probability: float


class ChargeWindowThreshold(BaseModel):
    charge_speed_percent: float
    interval: float
    outcome: ShotOutcome


class ChargeWindowResponse(BaseModel):
    interval: float
    magazine: int
    charge_speed_percent: float
    # The most overload alone can grant. The ladder stops here, so the screen
    # needs it to say WHY it stops rather than looking like it ran out of grid.
    charge_speed_ceiling: float
    current: ShotOutcome
    thresholds: list[ChargeWindowThreshold]
    notes: list[str]


class MirandaTargetsRequest(BaseModel):
    roster: list[UserNikkeState]
    units: list[str]


class MirandaSeat(BaseModel):
    slug: str
    burst_tier: int


class MirandaCycle(BaseModel):
    index: int
    powering_up: list[str]
    wake_up_crit_rate: list[str]


class MirandaOverloadThreshold(BaseModel):
    """이 니케가 전 사이클 웨이크업!3을 받는 오버로드 공격력의 경계."""
    slug: str
    current_percent: float
    # gain: 지금 못 받는다 - threshold_percent 이상이면 받는다
    # keep: 지금 받는다 - threshold_percent 밑으로 내려가면 놓친다
    kind: Literal["gain", "keep"]
    # gain에서 오버로드 상한 안에 답이 없으면 None. 누락이 아니라 「그런 값이
    # 없다」는 뜻을 지닌 값이다.
    threshold_percent: float | None


class MirandaTargetsResponse(BaseModel):
    seats: list[MirandaSeat]
    miranda_slug: str
    has_favorite_item: bool
    cycles: list[MirandaCycle]
    overload_thresholds: list[MirandaOverloadThreshold]
    overload_atk_cap_percent: float
    notes: list[str]


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
    # 계정 싱크로 레벨. 옵셔널인 이유는 이미 설치된 북마크릿이 이 값을 안 보내기
    # 때문이다 - 북마크릿은 설치 시점 소스가 박제된 것이라, 필수로 두면 기존
    # 사용자의 동기화가 전부 깨진다. 없으면 유니온용 스탯이 없는 로스터가 되고,
    # 그 사실은 유니온 탭이 알린다.
    synchro_level: int | None = None


app = FastAPI(title="NIKKE Deck Builder")
# blablalink이 허용 출처인 이유: 로스터 동기화 북마클릿이 그 페이지 안에서 돌고
# (거기서만 유저 세션으로 blablalink API를 부를 수 있다) 수집한 것을 이 로컬
# 서버로 보낸다. 2026-07-31 라이브 확인에서 https 페이지 -> http://127.0.0.1
# 요청 자체는 통과했다(브라우저가 loopback을 안전한 출처로 친다) - 막고 있던
# 것은 이 헤더뿐이었다.
#
# 목록에 적힌 출처만 허용되므로 아무 사이트나 이 서버를 호출하지는 못한다.
ALLOWED_ORIGINS = [
    "http://localhost:5173",   # Vite 개발 서버
    "https://www.blablalink.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
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


def _reject_missing_actual_stats(roster: list[UserNikkeState]) -> None:
    """유니온은 싱크로 레벨로 싸우므로 실제 레벨 스탯 없이는 잴 수가 없다.

    400레벨 값으로 대신 재면 유닛 간 상대 ATK가 최대 24% 뒤틀린다 - 레벨은 base
    커브에만 들어가고 장비·큐브·소장품은 레벨과 무관하게 더해지기 때문이다.
    그래서 근사하지 않고 거절한다.

    DEF는 보지 않는다: 스탯 모델이 DEF를 내지 않아 동기화된 로스터에서 "없음"과
    0을 구분할 수 없다.
    """
    missing = sorted({s.character_slug for s in roster
                      if s.actual_atk is None or s.actual_hp is None})
    if missing:
        raise HTTPException(
            status_code=422,
            detail=(
                "실제 레벨 스탯이 없는 니케가 있어요. 북마크릿을 다시 설치하고 "
                f"로스터를 다시 동기화해 주세요: {', '.join(missing)}"
            ),
        )



def _recommend_sync(request: RecommendRequest, cancel) -> RecommendResponse:
    _reject_unknown_overload_options(request.roster)
    if request.stat_basis == "actual":
        _reject_missing_actual_stats(request.roster)
    specs, excluded = load_roster(request.roster, stat_basis=request.stat_basis)
    boss = boss_profile(request.boss)
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
                hold_burst_slugs=r["hold_burst_slugs"],
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

    A base that is ITSELF one of its candidates (rapi-red-hood, whose Combat
    Assist seat is the other) gets alternatives too. Being a loadable spec only
    settles which spec represents the seat - it does not settle the mode, and
    for her the two candidates sit at DIFFERENT burst tiers, so pinning her to
    the nominal one makes a deck whose only tier-1 is her Combat Assist seat
    report no feasible ordering at all.

    Keyed by the MODE_VARIANTS base (what a client's draft/deck names a seat
    by), not yet by the representative spec's own slug - a caller resolves a
    seat against the client-sent base slug first, then rekeys to the chosen
    representative once every seat is settled (deck_allocation and
    deck_evaluation both key their `alternatives` argument that way)."""
    by_slug = {u.slug: u for u in specs}
    alternatives = {}
    for base, variants in MODE_VARIANTS.items():
        loadable = tuple(by_slug[v] for v in variants if v in by_slug)
        if loadable:
            alternatives[base] = loadable
    return by_slug, alternatives


def _to_recs(decks, pinned_by_deck=None):
    pinned_by_deck = pinned_by_deck or [[] for _ in decks]
    return [
        RaidDeck(
            deck=d["deck"], total_damage=d["total_damage"],
            burst_damage=d["burst_damage"], normal_attack_damage=d["normal_attack_damage"],
            skill_damage=d["skill_damage"],
            hold_burst_slugs=d["hold_burst_slugs"],
            pinned_slugs=pinned,
        )
        for d, pinned in zip(decks, pinned_by_deck)
    ]



def _recommend_raid_sync(request: RecommendRaidRequest, cancel) -> RecommendRaidResponse:
    _reject_unknown_overload_options(request.roster)
    if request.stat_basis == "actual":
        _reject_missing_actual_stats(request.roster)
    specs, excluded = load_roster(request.roster, stat_basis=request.stat_basis)
    boss = boss_profile(request.boss)
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
        swap_converged=out["swap_converged"],
        engine_version=engine_version(),
    )


def _evaluate_decks_sync(request: EvaluateDecksRequest, cancel) -> EvaluateDecksResponse:
    # 평가는 탐색이 없어 수 초에 끝난다. SimPool을 만들지 않으므로 토큰에
    # 접을 풀도 없다 - 인자는 _run_cancellable의 계약을 맞추기 위한 것.
    _reject_unknown_overload_options(request.roster)
    if request.stat_basis == "actual":
        _reject_missing_actual_stats(request.roster)
    specs, excluded = load_roster(request.roster, stat_basis=request.stat_basis)
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
        bosses.append(boss_profile(deck_in.boss))

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
            skill_damage=d["skill_damage"],
            hold_burst_slugs=d["hold_burst_slugs"]) for d in out["decks"]],
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


def _shot_outcome(value) -> ShotOutcome:
    """charge_window.Outcome -> the wire model. Written out field by field so a
    rename on either side is a type error rather than a silently missing key."""
    return ShotOutcome(
        low_shots=value.low_shots,
        low_probability=value.low_probability,
        high_shots=value.high_shots,
        high_probability=value.high_probability,
    )


def _charge_window_notes(request, inputs, current, ceiling, liberalio_in_roster,
                         rolls_known):
    """The judgements worth surfacing next to the ladder. Each is a fact the
    calculator can check rather than a caveat the reader has to remember."""
    notes = []
    if reload_intervenes(inputs):
        notes.append(
            "탄창이 창 안에서 비어 재장전이 걸립니다 — 엔진의 재장전 모델이 실측과 "
            "어긋나 있어(docs/engine-gaps.md) 마지막 한 발이 불확실합니다.")
    # Which axis is the binding one. Without this a magazine-capped ladder shows
    # the same count on every row and reads as a broken table rather than as the
    # answer "charge speed is not what is stopping you".
    uncapped = shots_without_magazine_limit(inputs)
    if uncapped > current.high_shots:
        notes.append(
            f"최대장탄이 타수를 막고 있습니다 — 탄창 {inputs.max_ammo}발로는 "
            f"{current.high_shots}타지만, 창 안에서 안 비울 만큼 넉넉하면 같은 "
            f"차지속도로 {uncapped}타입니다. 여기서는 차지속도보다 최대장탄이 "
            f"먼저입니다.")
    # The ladder is cut at the ceiling, so a total above it has to be named -
    # otherwise the row past the cut looks like something overload could buy.
    if inputs.charge_speed_percent > ceiling + 1e-9:
        notes.append(
            f"차지속도 합계 {inputs.charge_speed_percent * 100:.2f}%가 오버로드 상한 "
            f"{ceiling * 100:.0f}%를 넘습니다 — 4부위 전부 최고 굴림이 그 상한이라, "
            f"나머지는 덱 버프이거나 직접 입력한 값입니다.")
    if request.with_liberalio and request.slug != LIBERALIO_SLUG:
        if not liberalio_in_roster:
            notes.append(
                "리버렐리오가 로스터에 없어 차지속도 버프를 빼고 계산했습니다 — "
                "그녀의 스킬 레벨과 소장품을 모르면 버프 크기를 알 수 없습니다.")
        elif inputs.charge_time_reduction_sec == 0.0:
            notes.append(
                "리버렐리오의 최종 공격력이 더 낮아 차지속도 버프가 그녀 자신에게 "
                "갑니다 — 대상은 '최저 최종 공격력 버스트 3 아군'이고 시전자를 "
                "제외하지 않습니다. 판정 시점은 풀버스트 진입이라 그녀의 자버프 "
                "공격력 +160%와 대상 자신의 버스트 공격력 증가가 모두 들어갑니다.")
    # Charge speed rounds per roll, so a total that several roll combinations
    # could have produced does not pin the frame count. An override supplies the
    # rolls; a synced roster supplies them only if it carried them.
    if request.overrides.charge_speed_lines is None and not rolls_known:
        notes.append(
            "차지속도를 부위별 굴림이 아니라 합계에서 추정했습니다 — 굴림 값이 서로 "
            "다르면 한 프레임 어긋날 수 있습니다. 로스터를 다시 동기화하면 정확해집니다.")
    return notes


@app.post("/api/charge-window", response_model=ChargeWindowResponse)
def charge_window_route(request: ChargeWindowRequest) -> ChargeWindowResponse:
    """FB 창 안 타수와, 다음 타수를 사는 차지속도 임계값."""
    if request.slug not in CALCULATOR_SLUGS:
        raise HTTPException(422, f"charge-window calculator does not cover {request.slug}")
    if request.cube not in CUBE_NAMES:
        raise HTTPException(422, f"no harmony cube table for {request.cube}")
    by_slug = {state.character_slug: state for state in request.roster}
    if request.slug not in by_slug:
        raise HTTPException(422, f"{request.slug} is not in the submitted roster")
    try:
        inputs = build_inputs(
            by_slug[request.slug], request.with_liberalio,
            Overrides(request.overrides.charge_speed_lines,
                      request.overrides.max_ammo_percent,
                      request.overrides.reload_speed_percent),
            liberalio_state=by_slug.get(LIBERALIO_SLUG),
            cube=request.cube,
        )
    except ValueError as error:
        raise HTTPException(422, str(error)) from error

    current = outcome(inputs)
    ceiling = max_charge_speed_percent(load_stat_tables()) / 100
    notes = _charge_window_notes(
        request, inputs, current, ceiling, LIBERALIO_SLUG in by_slug,
        charge_speed_rolls_known(by_slug[request.slug]))
    return ChargeWindowResponse(
        interval=shot_interval(inputs),
        magazine=inputs.max_ammo,
        charge_speed_percent=inputs.charge_speed_percent,
        charge_speed_ceiling=ceiling,
        current=_shot_outcome(current),
        thresholds=[
            ChargeWindowThreshold(
                charge_speed_percent=row.charge_speed_percent,
                interval=row.interval,
                outcome=_shot_outcome(row.outcome),
            )
            # A total past the ceiling is the reader's to state - a deck buffer
            # or a typed value - so the ladder still reaches the row they are
            # standing on. Cutting below it would hide their own marker.
            for row in thresholds(inputs, max(ceiling, inputs.charge_speed_percent))
        ],
        notes=notes,
    )


# 이 계산기는 보스를 묻지 않는다. 답하는 것은 「누가 받는가」 하나이고, 그
# 순위를 정하는 것은 대부분 덱 자신의 버프이기 때문이다. 그래서 BossProfileIn의
# 기본값(무속성·180초)을 쓰고, 그 전제는 notes로 언제나 화면에 닿는다.
MIRANDA_CALCULATOR_BOSS = BossProfileIn()

MIRANDA_BOSS_NOTE = (
    "무속성 보스·180초 전투를 가정해 계산했어요. 보스 속성에 걸린 공격력 버프를 "
    "가진 니케가 있으면 실제 레이드와 순위가 다를 수 있어요."
)


def _miranda_targets_sync(request: MirandaTargetsRequest, cancel) -> MirandaTargetsResponse:
    # 평가와 임계값 탐색을 합쳐 수 초다. SimPool을 만들지 않으므로 토큰에 접을
    # 풀이 없다 - 인자는 _run_cancellable의 계약을 맞추기 위한 것.
    _reject_unknown_overload_options(request.roster)
    if len(request.units) != DECK_SIZE:
        raise HTTPException(422, f"덱은 {DECK_SIZE}명이어야 해요.")
    if len(request.units) != len(set(request.units)):
        dups = sorted({s for s in request.units if request.units.count(s) > 1})
        raise HTTPException(422, f"이 덱에 같은 니케가 겹쳐 들어갔어요: {dups}")
    if miranda_slug_in(request.units) is None:
        raise HTTPException(422, "덱에 미란다가 없어요. 미란다를 넣어야 계산할 수 있어요.")

    specs, _excluded = load_roster(request.roster)
    by_slug, alternatives = _variant_alternatives(specs)
    deck_specs = []
    for slug in request.units:
        options = alternatives.get(slug)
        if options is None and slug not in by_slug:
            raise HTTPException(422, f"엔진이 쓸 수 없는 슬러그예요: {slug}")
        deck_specs.append(options[0] if options else by_slug[slug])

    alternatives = {options[0].slug: options for options in alternatives.values()}
    try:
        report = miranda_target_report(deck_specs, boss_profile(MIRANDA_CALCULATOR_BOSS),
                                       by_slug, alternatives=alternatives)
    except InfeasibleDeck:
        raise HTTPException(
            422, "이 다섯으로는 성립하는 버스트 순서가 없어요. 버스트 1·2·3단계 "
                 "인원 수가 1·1·3, 1·2·2, 2·1·2 중 하나여야 해요.") from None

    return MirandaTargetsResponse(
        seats=[MirandaSeat(**seat) for seat in report["seats"]],
        miranda_slug=report["miranda_slug"],
        has_favorite_item=report["has_favorite_item"],
        cycles=[MirandaCycle(**cycle) for cycle in report["cycles"]],
        overload_thresholds=[MirandaOverloadThreshold(**row)
                             for row in report["overload_thresholds"]],
        overload_atk_cap_percent=report["overload_atk_cap_percent"],
        notes=[*report["notes"], MIRANDA_BOSS_NOTE],
    )


@app.post("/api/miranda-targets", response_model=MirandaTargetsResponse)
async def miranda_targets_route(
    request: MirandaTargetsRequest, http_request: Request
) -> MirandaTargetsResponse:
    """덱 5인 중 누가 미란다의 파워업!과 웨이크업!3을 받는가."""
    return await _run_cancellable(http_request, _miranda_targets_sync, request)


@app.get("/api/supported-units", response_model=list[SupportedUnit])
def supported_units_route() -> list[SupportedUnit]:
    return [SupportedUnit(**u) for u in _supported_units()]


@app.get("/api/raid-rotations", response_model=RaidRotationsResponse)
def raid_rotations_route() -> RaidRotationsResponse:
    """공지에서 읽어둔 회차 보스 전부. 어느 회차를 노출할지는 화면이 정한다."""
    return RaidRotationsResponse(**load_rotations())


@app.get("/api/engine-version")
def engine_version_route() -> dict[str, str]:
    """클라이언트는 요청을 보내기 전에 결과 캐시를 조회하므로, 버전을 응답으로만
    받으면 조회 시점에 알 수가 없다. 그래서 GET으로도 낸다."""
    return {"engine_version": engine_version()}


# 북마클릿이 놓고 가면 앱이 집어가는 한 칸.
#
# 네이티브 창(WebView2)은 유저 브라우저와 별개 저장소를 쓰므로 기존
# `window.open` + `postMessage` 경로가 앱 창에 닿지 않는다. 대신 북마클릿이
# 이 로컬 서버로 직접 POST하고, 앱이 폴링해서 가져간다.
#
# 프로세스 메모리에만 있고 디스크에 쓰지 않는다 - 앱을 닫으면 사라진다.
# 한 칸인 이유는 동기화가 유저가 의도적으로 한 번 하는 행위이기 때문이고,
# 새 것이 앞의 것을 덮는 이유는 두 번 눌렀을 때 기대되는 것이 마지막
# 결과이기 때문이다.
_sync_inbox: dict | None = None


@app.post("/api/sync-inbox")
def put_sync_inbox(payload: dict) -> dict:
    """북마크릿이 모은 것을 그대로 받는다.

    구조를 강제하지 않는 이유: 북마크릿이 보내는 것은 `{open_id, servers:[...]}`,
    즉 **서버 후보 목록**이다. 조립 형태(`{owned, character_details,
    recycle_room_researches}`)가 되는 것은 유저가 서버를 고른 뒤이고, 그 변환은
    프론트가 한다. 인박스가 조립 형태를 요구하면 실제 payload는 전부 422로
    떨어지고, 북마크릿에는 "앱을 찾지 못했다"로 보인다 - 2026-07-31에 실제로
    그렇게 나갔다.

    형태 검사는 이 자리가 아니라 받는 쪽(`useBookmarkletImport`의 handle)이
    한다. 모양이 어긋난 것은 거기서 조용히 무시된다.
    """
    global _sync_inbox
    _sync_inbox = payload
    return {"received": True}


@app.get("/api/sync-inbox")
def take_sync_inbox() -> dict:
    """가져가면서 비운다 - 앱이 폴링하므로, 비우지 않으면 같은 로스터를
    계속 다시 집어간다."""
    global _sync_inbox
    payload, _sync_inbox = _sync_inbox, None
    return {"payload": payload}


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


class _SpaFiles(StaticFiles):
    """정적 파일을 주되, 없는 경로에는 `index.html`을 준다.

    앱은 SPA라 클라이언트가 서버가 모르는 경로를 가질 수 있고(새로고침·딥링크),
    그때 404를 주면 빈 화면이 된다. 다만 `/api/*`는 폴백에서 제외한다 - 오타 난
    엔드포인트가 HTML을 돌려주면 클라이언트는 JSON 파싱 오류를 보게 되고, 그
    증상은 원인에서 한참 떨어져 있다.
    """

    @staticmethod
    def _is_api(path: str) -> bool:
        # StaticFiles는 이 자리에 OS 구분자로 정규화된 경로를 준다 - Windows에서는
        # `api\no-such-endpoint`라, 슬래시로 접두사를 검사하면 조용히 빗나간다.
        return path.replace("\\", "/").lstrip("/").startswith("api/")

    @staticmethod
    def _is_asset(path: str) -> bool:
        """확장자가 있으면 자산 요청이다 - 없는 자산은 404여야 한다.

        폴백이 여기까지 삼키면 `<script src="/assets/app.js">`가 HTML을 200으로
        받는다. 브라우저는 그것을 파싱하다 실패하고 아무것도 그리지 않으므로,
        증상은 원인을 한 마디도 담지 않은 **빈 검은 화면**이다(2026-07-31 실제로
        겪음). 404면 최소한 어느 파일이 없는지가 콘솔에 남는다.

        SPA 라우트는 확장자를 갖지 않으므로 이 구분으로 갈린다.
        """
        return "." in path.replace("\\", "/").rsplit("/", 1)[-1]

    async def get_response(self, path: str, scope):
        # StaticFiles는 없는 파일에 404를 '반환'하지 않고 HTTPException으로
        # 던진다. 둘 다 받아야 폴백이 실제로 걸린다.
        try:
            response = await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code != 404 or self._is_api(path) or self._is_asset(path):
                raise
            return await super().get_response("index.html", scope)
        if (response.status_code == 404
                and not self._is_api(path) and not self._is_asset(path)):
            return await super().get_response("index.html", scope)
        return response


def build_app() -> FastAPI:
    """라우트가 전부 붙은 app에 프론트 번들을 (있으면) 얹는다.

    마운트가 마지막이어야 하는 이유: `/`에 걸린 정적 서빙은 그 아래 모든 경로를
    가져가므로, `/api/*` 라우트보다 먼저 붙으면 API가 전부 정적 404가 된다.
    번들이 없으면 아무것도 하지 않는다 - 개발 중에는 :5173이 프론트를 맡고
    백엔드는 API만 답하는 것이 정상이다.
    """
    # 멱등하게: 라우트는 데코레이터로 모듈 전역 `app`에 붙으므로 여기서 새
    # FastAPI를 만들 수 없고, 그래서 이 함수를 두 번 부르면 마운트가 쌓인다.
    # 앞선 마운트를 걷어내고 다시 붙이면 재호출이 안전해진다.
    app.routes[:] = [r for r in app.routes if getattr(r, "name", None) != "frontend"]
    dist = frontend_dist()
    if (dist / "index.html").is_file():
        app.mount("/", _SpaFiles(directory=dist, html=True), name="frontend")
    return app
