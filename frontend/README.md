# NIKKE Deck Builder — Frontend

The web UI for the deck builder. Lets a user enter their per-character
investment data (from ShiftyPad) and, later, see the recommended decks the
backend engine produces.

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

## Current scope (do this first)

**The ShiftyPad investment-data input UI.** This is fully independent of the
backend API — it collects and validates the user's per-Nikke data client-side.
Build it now; the recommendation-display half waits on the API contract below.

## Data contract — user input

The input form collects one `UserNikkeState` per owned Nikke. This is the
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
character stats. So the user copies those numbers in as-is and the cube is never
added on top. Overload is the opposite: ShiftyPad shows it separately and it IS
additive.

## Data contract — backend API

Mirrors `backend/app/deck_search.py` (`find_best_decks` / `BossProfile`) — the
source of truth. Keep the TS request/response types in `src/api/` in sync with it.

**Endpoint status: implemented** (`backend/app/api.py`). Run it from `backend/`
with `uvicorn app.api:app --reload` (port 8000). The dev client fetches a
*relative* `/api/recommend`, which `vite.config.ts` proxies to
`http://localhost:8000` — so for live end-to-end dev run both servers and start
Vite with `VITE_RECOMMEND_API=live npm run dev`. Without that env var the client
uses the dev mock (`src/api/recommendClient.mock.ts`); the switch lives only in
`src/api/recommend.ts`, so components never depend on which one is active.

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
flight. The mock client should simulate a short (~1 s) delay so dev flows stay
snappy.

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
  live/mock switch stays confined to `src/api/` (one module decides, callers
  never know which is active — mirror how `recommend.ts` does it), state in a
  hook next to `useRecommend`, display components next to `DeckResults`.
  Reuse/extract shared pieces rather than duplicating the single-deck ones.

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
