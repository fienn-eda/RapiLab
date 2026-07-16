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
| `pve_cube` | `{ name: string, level: int(1–10) } \| null` | PVE cube only; PVP cubes out of scope |

Open question carried from the backend (`models.py` comment): whether cube stats
are already folded into `hp/atk/def` or added separately is unconfirmed. Build
the input for what the user reads off ShiftyPad; don't encode an assumption about
that here — flag it if the UI forces the question.

## Data contract — backend API

Mirrors `backend/app/deck_search.py` (`find_best_decks` / `BossProfile`) — the
source of truth. Keep the TS request/response types in `src/api/` in sync with it.

**Endpoint status:** the FastAPI endpoint is **not implemented yet** — the main
agent owns wiring it (the `UserNikkeState[] → engine roster` assembly lives
backend-side). Build the typed API client and the results UI against this
contract **contract-first**: put the request/response types in `src/types/`, the
client in `src/api/`, and back it with a **dev mock/fixture** behind the client
so the UI is exercisable now. Do not hardcode the mock into components — when the
real endpoint lands it must swap in at the client layer only. Flag anything the
contract leaves ambiguous rather than inventing it.

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
  ]                                  // ranked by total_damage desc, length <= top_n
}
```
Validation failures (no feasible deck, unknown slug, out-of-range field) return
FastAPI's default `422` error shape.

## Dev commands

Once the project is initialized (`npm create vite@latest . -- --template react-ts`
in `frontend/`, then `npm install`):

```
npm run dev        # Vite dev server
npm run build       # production build
npx tsc --noEmit    # type-check
npm run test        # Vitest (once tests exist)
```
