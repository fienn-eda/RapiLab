# NIKKE Deck Builder — Frontend

The web UI for the deck builder. A user syncs their roster's per-character
investment data from blablalink (one or more accounts) and sees the
recommended decks the backend engine produces.

This file is the **contract** the `frontend-builder` agent implements against.
The main agent maintains it; the frontend agent follows it and reports back any
gap rather than inventing structure or API shapes.

## Stack

- **React + Vite + TypeScript**
- Package manager: npm
- Type-check with `tsc --noEmit`; component tests with Vitest.

## Folder layout

```
frontend/
  src/
    api/          # backend client — one module per endpoint group (deferred; see below)
    components/   # React components
    types/        # TypeScript mirrors of backend data shapes
    hooks/        # shared React hooks
  README.md       # this contract
```

Keep the existing `src/api` and `src/components` dirs; add `src/types` and
`src/hooks` as needed. Don't introduce a different top-level structure without
the main agent updating this file.

## Current scope

**Roster is sync-only.** The roster comes exclusively from a blablalink sync
(the bookmarklet flow below); there is no manual entry form and no
ExiaInvasion file import — both were removed. The roster display (`NikkeCard`)
is read-only. If ShiftyPad/blablalink can't supply a field the deck search
needs, that's an engine-data gap to raise with the main agent, not something
to patch over with a manual-input form.

## Multi-account profiles

The app supports **multiple blablalink accounts side by side**, each in its
own isolated **profile**. This replaces the old single-roster `nikke-roster`
key.

- **Storage:** one `localStorage` key, `nikke-profiles`, holding
  `{ activeOpenId, profiles: Record<openId, Profile> }`. Each `Profile` is
  keyed by the blablalink account's `open_id` and holds that account's roster
  plus its cached recommend-raid results (see below).
- **Isolation invariant:** different `open_id`s are never merged. Syncing
  account B never touches account A's roster, cache, or active-result state.
  Switching profiles swaps the whole roster + result view; it never blends
  two accounts' data.
- **Sync capture, client-only:** the sync bookmarklet also calls
  `GetUserProfileBasicInfo` to grab the account's display `nickname`, and
  already has `open_id` from the share URL. Both are **client-only** —
  `src/api/assembleRoster.ts` destructures them out of the payload before
  the fetch, so `POST /api/assemble-roster` receives only roster fields.
  The backend never learns any account's `open_id` or `nickname`. The only
  identifier our backend ever sees, on any call, is the anonymous `clientId`
  (`src/lib/clientId.ts`, sent as `X-Client-Id`) — unrelated to any game
  account and never sent to blablalink.
- **Upsert:** a sync for a new `open_id` creates and activates a profile; a
  sync for an existing `open_id` refreshes its nickname/roster in place (and
  switches to it). If the refreshed roster actually differs from what was
  stored, that profile's cached results are invalidated — they no longer
  describe the current roster.
- **Profiles UI:** `ProfileSwitcher` lists profiles by nickname with a
  dropdown to switch and a button to delete the active one (with a
  confirmation, since it drops that profile's roster and cache).
- **Migration:** the app isn't deployed yet, so a legacy `nikke-roster` key
  (pre-profiles) is **discarded** on load, not migrated — `useProfiles.ts`.

### Result persistence

Raid and draft recommendation results are cached **per profile** so reopening
the app or switching back to a profile restores the last view instantly,
without re-running the (~1-2 minute) backend call:

- **Cache key:** a deterministic hash (`src/lib/inputHash.ts`, FNV-1a over a
  canonicalized — sorted keys, order-independent roster/draft — JSON
  snapshot) of `(roster investment data, boss profile, draft, num_decks)`.
  The engine has no RNG, so identical inputs always produce identical output;
  this hash is exact, not a staleness heuristic.
- **Storage:** each `Profile.results` is a `Record<inputHash, StoredResult>`,
  capped at `RESULTS_CAP` (20) entries with oldest-first (LRU) eviction.
  `Profile.lastResultHash` + `Profile.lastInputs` point at the most recent
  run so it can be restored (form state and all) on reopen/profile-switch
  without a re-run.
- **Scope:** only raid and draft-mode results (`POST /api/recommend-raid`)
  are cached this way. **Single-deck mode is not cached** — `/api/recommend`
  is cheap enough to just re-run.
- **Invalidation:** re-syncing a profile whose roster changed clears that
  profile's cached results (see upsert above), since a stale result for a
  changed roster would be wrong, not just old.

## Data contract — user input

Each owned Nikke's investment data is one `UserNikkeState`. This is the
**source of truth in `backend/app/models.py`** (Pydantic). Mirror it in
`src/types/` and keep it in sync; never edit the Python:

| Field | Type | Constraint |
|---|---|---|
| `character_slug` | string | identifies the Nikke (fixed metadata — element/weapon/class/burst — is looked up backend-side from the slug, not entered here) |
| `level` | int | ≥ 1 |
| `core_level` | int | ≥ 0 |
| `hp` | float | ≥ 0 |
| `atk` | float | ≥ 0 |
| `def_` | float | ≥ 0 (note the trailing underscore in the Python model) |
| `skill_levels` | `{ skill1, skill2, burst }` | each int, 1–10 |
| `overload_options` | `{ name: string, value: float }[]` | aggregated across 4 gear pieces; may be empty |

There is no `pve_cube` field — cube is not user input. Every Nikke is simulated
wearing a Resilience Cube Lv.15, a backend-side assumption applied to the whole
roster regardless of what's entered (`docs/decisions.md`, 2026-07-20). The UI
states this assumption; it does not collect a cube.

Resolved (Fienn, 2026-07-17): ShiftyPad's displayed `hp/atk/def` **already include**
the equipped cube — with a cube on it reflects the cube, with none it shows bare
character stats. So the synced numbers are used as-is and the cube is never
added on top. Overload is the opposite: ShiftyPad shows it separately and it IS
additive.

## Data contract — backend API

Mirrors `backend/app/deck_search.py` (`find_best_decks` / `BossProfile`) — the
source of truth. Keep the TS request/response types in `src/api/` in sync with it.

**Endpoint status: implemented** (`backend/app/api.py`). Run it from `backend/`
with `uvicorn app.api:app --reload` (port 8000). The client fetches a *relative*
`/api/recommend`, which `vite.config.ts` proxies to `http://localhost:8000` — so
dev needs **both servers running**; `npm run dev` alone will fail its API calls.

**There is no dev mock.** Each `src/api/` module talks to the real backend, so
what you see in the browser is always what the engine actually returns. Tests
stub these modules with `vi.mock` instead (see `App.test.tsx`).

### `POST /api/recommend`

Request body:
```jsonc
{
  "roster": UserNikkeState[],   // the entered roster (needs a feasible 5-unit deck: burst tiers 1,2,3 all present)
  "boss": {
    "element": "Fire" | "Water" | "Wind" | "Iron" | "Electric" | null,  // null = non-elemental
    "core_hittable": boolean,   // default false
    "enemy_def": number,        // default 0
    "fight_duration": number,   // seconds, default 180
    "part_destructible": boolean // default false — boss has a part-destruction gimmick.
                                 // Selects the ceiling (max-potential) model for units whose
                                 // kit depends on part destruction (e.g. Ark Ranger Black);
                                 // false = floor (lower-bound) model.
  },
  "top_n": number               // optional, default 5
}
```
(`BossProfile` also has `gauge_charge_time` and `mode` — leave them to backend
defaults; don't surface them in the UI yet.)

Response `200`:
```jsonc
{
  "decks": [
    {
      "deck": string[],             // 5 character slugs, ordered by burst role (B1 → B2 → B3)
      "total_damage": number,
      "burst_damage": number,
      "normal_attack_damage": number
    }
  ],                                 // ranked by total_damage desc, length <= top_n
  "excluded_slugs": string[]         // submitted slugs the backend can't evaluate yet
                                     // (not encoded / no local data); excluded from the
                                     // search and shown as "not yet supported" — never a
                                     // 422 by themselves
}
```
Validation failures (malformed body, out-of-range field, or no feasible deck in
the *usable* roster after exclusions) return FastAPI's default `422` error shape;
the no-feasible-deck detail names the excluded slugs.

### `POST /api/recommend-raid` (multi-deck allocation — solo raid)

Splits the roster into up to `num_decks` **disjoint** decks against one boss and
maximizes their summed damage. Semantically different from `/api/recommend`:
that endpoint returns ranked *alternatives* for ONE deck; this one returns a
*partition* — the player fields ALL returned decks in one raid, and no Nikke
appears in two of them. The UI must not present these as "top N candidates".

Request body: same shape as `/api/recommend` (`roster` + `boss`), plus:
```jsonc
{
  "num_decks": number   // int 1–5, default 5. (top_n is inherited by the
                        // backend model but unused — omit it.)
}
```

Response `200`:
```jsonc
{
  "decks": [ /* same DeckRecommendation shape as /api/recommend */ ],
                                     // one entry per allocated deck, in
                                     // allocation order (may be FEWER than
                                     // num_decks when the roster can't fill
                                     // more feasible decks)
  "combined_total_damage": number,   // sum over decks
  "excluded_slugs": string[],        // same meaning as /api/recommend
  "leftover_slugs": string[]         // usable units the allocation left out
                                     // (sorted; shown so the player knows who
                                     // sat on the bench)
}
```
`422` mirrors `/api/recommend` (no feasible deck at all in the usable roster).

**Latency warning:** with a realistic full roster this endpoint takes **~1–2
minutes** (the backend runs thousands of 180 s simulations; it is already
process-pool parallelized). The client must NOT impose a request timeout, must
show a persistent in-progress state with copy telling the user the wait is
expected and roughly how long, and must disable re-submission while a run is in
flight.

### UI scope — raid mode (current task)

Extend the recommendation flow with a mode switch: **single deck** (existing
`/api/recommend` flow, unchanged) vs **raid allocation** (`/api/recommend-raid`).

- Mode switch + `num_decks` selector (1–5, default 5) live in the recommend
  panel; the boss profile fields are shared between both modes.
- Raid results render the decks as "Deck 1..N" (allocation order — they are
  NOT ranked alternatives), each with the same per-deck breakdown the single
  mode shows (total / burst / normal attack, slugs in burst-role order), plus
  the combined total prominently, plus leftover and excluded slug lists.
- Follow the established structure: types in `src/types/recommend.ts`, the
  fetch client in its own `src/api/` module (one per endpoint — mirror how
  `recommend.ts` does it), state in a hook next to `useRecommend`, display
  components next to `DeckResults`. Reuse/extract shared pieces rather than
  duplicating the single-deck ones.

### Draft-based raid recommendation (`POST /api/recommend-raid` with `draft`)

The raid endpoint accepts an optional **draft** — the user seeds decks with their
own key units and the engine fills/optimizes the rest. Membership only: seat
position is NOT burst order (the engine assigns order). Omitting `draft` (or `[]`)
is exactly today's zero-base behavior.

Request adds to the raid body:
```jsonc
{
  "draft": [                     // optional; [] or omitted = zero-base
    { "units": [
        { "slug": string, "locked": boolean }   // locked default false
    ] }                          // one DraftDeck per seeded deck (0..5 units each)
  ]                              // length <= num_decks; a slug appears in at most ONE deck
}
```
- `locked: true` = the engine MUST keep this unit in this deck (survival unit, etc.).
- `locked: false`/omitted = a warm-start hint; the engine may move or replace it.

Response — each deck is now a **RaidDeck** (the `/api/recommend` `DeckRecommendation`
shape **plus** `pinned_slugs`), and two additive top-level fields appear:
```jsonc
{
  "decks": [ { /* ...DeckRecommendation..., */ "pinned_slugs": string[] } ],
                                   // = the bench-inclusive RECOMMENDED tier;
                                   // pinned_slugs = the locked slugs the engine kept here
  "combined_total_damage": number,
  "excluded_slugs": string[],
  "leftover_slugs": string[],
  "within_draft":                  // NON-NULL only for a COMPLETE draft (see below), else null
    { "decks": RaidDeck[], "combined_total_damage": number, "leftover_slugs": string[] }
    | null,                        // best allocation using ONLY the drafted units (no bench)
  "baseline_total_damage": number | null  // the user's exact drafted groupings scored
}
```
- A draft is **complete** when `draft.length === num_decks` AND every drafted deck
  has exactly 5 units. Only then are `within_draft` and `baseline_total_damage`
  non-null; for a partial draft both are `null` and only `decks`/top-level appear.
- **Monotone guarantee (complete draft):**
  `baseline_total_damage ≤ sum(within_draft.decks.total_damage) ≤ combined_total_damage`.
  The recommendation is never worse than what the user submitted. Present these as
  three ascending tiers: *your config* → *best within your own units (+Δ1)* →
  *bench-inclusive best (+Δ2)*.
- `422` (in addition to the no-feasible-deck case): a draft slug not in the usable
  roster; the same slug placed in two decks; an over-constrained draft whose locked
  tier counts fit no legal deck shape. The `detail` names the offending slug/deck.

### `GET /api/supported-units`

Feeds the draft palette. Returns every engine-supported Nikke:
```jsonc
[ { "slug": string, "name": string,
    "burst_tier": 1 | 2 | 3,
    "element": "Fire" | "Water" | "Wind" | "Iron" | "Electric" } ]
```
Group the palette by `burst_tier` (B1/B2/B3). `name` is a display name (may be a
humanized slug). No request body; safe to fetch once and cache.

### Portraits

Static, served from `frontend/public/portraits/`. The map lives at
`/portraits/manifest.json`:
```jsonc
{ "source": "...", "portraits": { "<slug>": "<filename>" } }
```
Resolve a slug's icon as `manifest.portraits[slug]` → prefix `/portraits/`. When a
slug has no entry, fall back to a chip (name + tier + element/class tint). The
editor logic must work identically with or without a portrait — icons are a
presentation layer only.

### UI scope — draft editor (next task)

- **Palette:** owned units (from the active profile's roster) ∩ supported
  (`/api/supported-units`), grouped B1/B2/B3, each a portrait (or chip fallback).
- **Editor:** 5 decks × 5 seats; seats are membership (order engine-assigned); a
  per-unit **lock toggle**; a unit may sit in at most one deck (enforce client-side).
- **Submit:** build `draft` from the editor and POST to `/api/recommend-raid`.
  - Complete draft with `within_draft`/`baseline_total_damage` present → render the
    **three tiers** (baseline → within_draft +Δ1 → recommended +Δ2), a per-deck diff
    vs the submitted draft, and `pinned_slugs` badges.
  - Otherwise → the single recommended allocation (reuse the raid results view).
- Keep the fetch client confined to `src/api/`; mirror the existing raid module.

## Dev commands

Once the project is initialized (`npm create vite@latest . -- --template react-ts`
in `frontend/`, then `npm install`):

```
npm run dev           # Vite dev server
npm run build         # production build
npx tsc -b --noEmit   # type-check (must be -b: the root tsconfig is a
                      # references-only shell with "files": [], so a bare
                      # `tsc --noEmit` checks NOTHING and always exits 0)
npm run test          # Vitest
```
