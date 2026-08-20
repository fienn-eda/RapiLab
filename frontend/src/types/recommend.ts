// Request/response types for POST /api/recommend.
// SOURCE OF TRUTH: backend/app/deck_search.py (BossProfile, find_best_decks)
// and frontend/README.md "Data contract — backend API". Keep in sync; never
// edit the Python. The endpoint itself isn't implemented yet — see
// src/api/recommend.ts for the dev-mock client that stands in for it.

import type { UserNikkeState } from './userNikkeState'

export type BossElement = 'Fire' | 'Water' | 'Wind' | 'Iron' | 'Electric' | null

export type BossRangeBand = 'near' | 'mid' | 'far' | null

export const BOSS_RANGE_BANDS: Exclude<BossRangeBand, null>[] = ['near', 'mid', 'far']

export interface BossProfile {
  element: BossElement // null = non-elemental
  core_hittable: boolean // default false
  pierce_hits_body_behind_core: boolean // default false — 코어와 본체가 별개 객체인
  // 보스. 관통 특화 니케의 탄이 코어를 뚫고 뒤의 본체까지 때려 통상공격 1발이 두 번
  // 들어간다. core_hittable에 의존한다 — 뚫고 지나갈 코어가 없으면 성립하지 않는다.
  enemy_def: number // default 0
  fight_duration: number // seconds, default 180
  part_destructible: boolean // default false — boss has a part-destruction gimmick;
  // selects the ceiling (max-potential) model for units whose kit depends on
  // part destruction (e.g. Ark Ranger Black), false = floor (lower-bound) model.
  spawns_adds: boolean // default false — 잡몹이 주기적으로 생성되는 보스. 딜 계산에는
  // 안 들어가고, 홀드 파이어 택틱(자기 풀버스트 동안 평타를 멈춰 라운드 버프를
  // 살리는 수)을 후보에서 지우는 데만 쓰인다 — 나오는 잡몹을 치워야 하므로 평타를
  // 멈출 수 없다.
  part_destruction_times: number[] // default [] — 파츠가 실제로 깨지는 시각(초).
  // 그 보스를 관측해야 나오는 값이라 공지에서 오지 않는다. 비어 있으면 파괴에
  // 반응하는 스킬은 위 불리언만 보던 근사로 돌고, 시각이 있으면 그 시각마다
  // 자기 지속시간만큼 창을 연다(레이븐·디젤).
  effective_range_band: BossRangeBand // default null — how far away the boss is
  // fought. The band decides WHICH weapons are inside their effective range and
  // collect +0.30 on their normal attacks: near pays SG/SMG, mid pays AR/MG, far
  // pays SR, and a Rocket Launcher is paid by none. null = unknown, pays nobody.
  // gauge_charge_time and mode also exist on the backend BossProfile but are
  // left to backend defaults and not surfaced here (per the README contract).
  core_diameter_px: number | null // default null — 코어 지름(엔진 단위, 화면 픽셀이
  // 아니다). 무기 탄착군과의 면적비가 평타의 코어 명중률을 정한다. null이면
  // 모델링하지 않고 적격 평타가 전부 코어에 든다고 본다 — 엔진이 오래 모델해 온
  // 상한이다. core_hittable이 거짓이면 무시된다.
  elemental_interrupt_required: boolean // default false — 기믹 파훼에 약점 속성 니케가
  // 덱당 최소 1기 필요하다. 무속성 보스에서는 무시된다(약점이 없으므로 어떤 덱도
  // 만족시킬 수 없고, 강제하면 모든 로스터가 불능이 된다).
}

export interface RecommendRequest {
  roster: UserNikkeState[] // needs a feasible 5-unit deck: burst tiers 1, 2, 3 all present
  boss: BossProfile
  top_n?: number // optional, default 5
}

export interface DeckRecommendation {
  deck: string[] // 5 character slugs, ordered by burst role (B1 -> B2 -> B3)
  total_damage: number
  burst_damage: number
  normal_attack_damage: number
  // Everything that was neither a burst nor a normal attack — DoTs, per-shot
  // riders, self-cooldowned procs. The three add up to total_damage.
  skill_damage: number
  // 덱 순서만으로는 표현할 수 없는 플레이 지시: 이 슬러그들은 첫 풀버스트에
  // 버스트를 아껴야 채점된 그 상태가 걸린다. 거의 항상 빈 배열이다 — 엔진은
  // 동점이면 그대로 플레이 가능한 순서를 고르므로, 홀드가 더 높게 나올 때만 찬다.
  hold_burst_slugs: string[]
  // 위 수치가 **수동 톡톡이**(차지하자마자 발사)를 전제로 계산된 슬러그. 같은
  // 성격의 플레이 지시이고, 누가 여기 들어가는지는 엔진이 정해서 실어 보낸다 —
  // 화면이 슬러그를 보고 판단하지 않는다.
  tap_fire_slugs: string[]
  // 그중 **배율을 실제로 버린** 슬러그. 여기 없으면 그 유닛은 차지가 0으로 내려간
  // 구간에서만 톡톡이이고, 그때는 눌러도 풀차지라 잃는 것이 없다.
  partial_charge_slugs: string[]
  // 그 좌석이 매거진 하나에서 실제로 쏜 풀차지 발수(최빈값). 화면 문구는 이 필드와
  // `partial_charge_slugs` **둘의 조합**으로 세 갈래로 갈린다 — 슬러그가 없으면
  // (배율을 안 버렸으면) 버스트 턴만 톡톡이, 슬러그가 있고 이 값이 0이면 매거진을
  // 통째로 톡톡이, 1 이상이면 매거진 안에서 풀차지와 섞었다(밀크: 블루밍 바니).
  // 문안 자체는 helpText.ts의 tapFireBurstOnly/tapFireAlways/tapFireMixed 참고.
  partial_charge_full_rounds: Record<string, number>
  // 「자신과 양 옆 아군 2명」을 대상으로 하는 버프를 가진 유닛(루주의 Sword Coin,
  // 플로라 애장품의 Peace of Mind)을 어떻게 앉혀야 위 수치가 나오는지. 그런 유닛이
  // 없는 덱은 빈 객체다. 이것도 덱 목록에 안 담기는 편성 지시인데, 이유가
  // hold_burst_slugs와 다르다: 자리는 버스트 우선순위와 **다른 축**이라 애초에
  // 목록이 표현하는 것이 아니다.
  seating: Record<string, SeatingEntry>
}

export interface SeatingEntry {
  // 시전자 양 옆에 앉힐 아군 둘.
  allies: string[]
  // 시전자가 앉을 수 있는 자리(1부터). 원문이 자리를 요구하는 유닛만 좁다 —
  // 루주는 뒷열이라 [2, 4]. 이 목록이 덱 크기와 같으면 제약이 없다는 뜻이고,
  // 그때는 화면이 자리 이야기를 꺼내지 않는다. 「양 옆에 둘」만으로는 부족해서
  // 필요한 필드다: 3번 자리도 양 옆이 둘이지만 앞열이라 루주의 버프가 안 켜진다.
  seats: number[]
}

export interface RecommendResponse {
  decks: DeckRecommendation[] // ranked by total_damage desc, length <= top_n
  excluded_slugs: string[] // submitted slugs the backend can't evaluate yet (not encoded / no data); shown as "not yet supported"
  // 이 결과를 낸 엔진의 버전 — 결과 캐시의 무효화 축(lib/inputHash.ts).
  engine_version: string
}

// A deck needs 5 Nikkes. This is necessary but NOT sufficient for a feasible
// deck — feasibility also requires burst tiers 1, 2, and 3 all present, which
// depends on burst_tier metadata that's only looked up backend-side from
// character_slug (not part of UserNikkeState). The client can only guard on
// roster size; the backend still returns 422 for a roster that has 5+ Nikkes
// but can't cover all three burst tiers.
export const MIN_DECK_ROSTER_SIZE = 5

// POST /api/recommend-raid: splits the roster into up to num_decks DISJOINT
// decks against one boss and maximizes their summed damage. Semantically
// different from /api/recommend — that endpoint ranks alternatives for ONE
// deck; this one returns a partition the player fields all at once (no Nikke
// appears in two decks).
// Draft-based raid seeding (frontend/README.md "Draft-based raid
// recommendation"): the player seeds decks with key units and the engine
// fills/optimizes the rest. Membership only — seat position is NOT burst
// order, the engine assigns it. This is the WIRE shape POST
// /api/recommend-raid expects; the editor's own state shape lives in
// types/draft.ts (DraftEditor.tsx's toRequestDraft converts between them).
export interface DraftUnit {
  slug: string
  locked: boolean // default false; true = engine must keep this unit in this deck
}

export interface DraftDeck {
  units: DraftUnit[] // 0..5 units
}

export interface RecommendRaidRequest {
  roster: UserNikkeState[]
  boss: BossProfile
  num_decks?: number // int, 1–5, default 5
  draft?: DraftDeck[] // optional; omitted or [] = zero-base behavior (no draft seeding)
}

// A raid deck additionally reports which of its slugs were pinned by the
// caller's draft (locked units the engine kept) — a draft-only concept, not
// part of the shared DeckRecommendation shape /api/recommend also uses.
export interface RaidDeck extends DeckRecommendation {
  pinned_slugs: string[]
}

// The best allocation using ONLY the drafted units (no bench) — present only
// when the submitted draft is COMPLETE (draft.length === num_decks and every
// drafted deck has exactly 5 units).
export interface DraftAllocation {
  decks: RaidDeck[]
  combined_total_damage: number
  leftover_slugs: string[]
}

export interface RecommendRaidResponse {
  decks: RaidDeck[] // one entry per allocated deck, in allocation
  // order (NOT ranked alternatives) — may be fewer than num_decks when the
  // roster can't fill more feasible decks; this is the bench-inclusive
  // RECOMMENDED tier
  combined_total_damage: number // sum over decks
  excluded_slugs: string[] // same meaning as /api/recommend
  leftover_slugs: string[] // usable units the allocation left out (sorted)
  within_draft: DraftAllocation | null // non-null only for a COMPLETE draft
  baseline_total_damage: number | null // the user's exact drafted groupings scored;
  // non-null only for a COMPLETE draft. Monotone guarantee (complete draft):
  // baseline_total_damage <= sum(within_draft.decks.total_damage) <= combined_total_damage
  // 탐색이 상한에 걸리지 않고 끝까지 갔는지. false면 더 나은 배분이 남아 있을 수 있다.
  swap_converged: boolean
  // 이 결과를 낸 엔진의 버전 — 결과 캐시의 무효화 축(lib/inputHash.ts).
  engine_version: string
}

export const MIN_NUM_DECKS = 1
export const MAX_NUM_DECKS = 5
export const DEFAULT_NUM_DECKS = 5
