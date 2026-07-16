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

## Data contract — backend API (DEFERRED)

**Not defined yet.** The recommendation-display components (submitting the roster,
receiving ranked decks) depend on a FastAPI contract the main agent will add here
before that work starts. Until it appears in this file, do not call or assume any
endpoint — build the input UI and its types, and report the block.

## Dev commands

Once the project is initialized (`npm create vite@latest . -- --template react-ts`
in `frontend/`, then `npm install`):

```
npm run dev        # Vite dev server
npm run build       # production build
npx tsc --noEmit    # type-check
npm run test        # Vitest (once tests exist)
```
