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
    api/          # backend client — one module per endpoint group
    components/   # React components
    types/        # TypeScript mirrors of backend data shapes
    hooks/        # shared React hooks
    lib/          # framework-free helpers (bookmarklet, inputHash, unitName)
  README.md       # this contract
```

Keep the existing `src/api` and `src/components` dirs; add `src/types` and
`src/hooks` as needed. Don't introduce a different top-level structure without
the main agent updating this file.

## Current scope

**Roster is sync-only.** The roster comes exclusively from a blablalink sync
(the bookmarklet flow below); there is no manual entry form and no
ExiaInvasion file import — both were removed. The roster display
(`RosterGrid` / `NikkeCard`) is read-only. If ShiftyPad/blablalink can't supply
a field the deck search needs, that's an engine-data gap to raise with the main
agent, not something to patch over with a manual-input form.

The app is **two tabs**, Roster and Recommend. Both panels stay mounted and only
toggle `hidden`: a raid run takes 1–2 minutes, and unmounting the recommend
panel to switch tabs would abandon a request already in flight.

## Multi-account profiles

The app supports **multiple blablalink accounts side by side**, each possibly
holding a separate roster **on more than one game server** — a blablalink
account isn't specific enough to key a roster by itself, so a **profile** is
keyed by the (account, server) pair. This replaces the old single-roster
`nikke-roster` key.

- **Storage:** one `localStorage` key, `nikke-profiles`, holding
  `{ activeKey, profiles: Record<'<openId>:<area>', Profile> }`. Each `Profile`
  is keyed by `` `${openId}:${area}` `` (`types/profile.ts`'s `profileKey`) and
  holds that account-on-that-server's roster plus its cached recommend-raid
  results (see below). `area` is blablalink's `nikke_area_id` — the game
  server the roster was synced from (`src/types/server.ts`: 81 JP, 82 NA,
  83 KR, 84 GL, 85 SEA).
- **Isolation invariant:** different `(open_id, area)` pairs are never merged
  — including **one `open_id` on two different servers**, which is a normal
  case (a blablalink account can hold its own roster on each server), not a
  duplicate-account edge case. Syncing one profile never touches another
  profile's roster, cache, or active-result state, whether the two differ by
  account or only by server. Switching profiles swaps the whole roster +
  result view; it never blends two profiles' data.
- **Sync capture, client-only:** the sync bookmarklet also calls
  `GetUserProfileBasicInfo` to grab the account's display `nickname`, and
  already has `open_id` from the share URL. Both are **client-only** —
  `src/api/assembleRoster.ts` destructures them out of the payload before
  the fetch, so `POST /api/assemble-roster` receives only roster fields.
  The backend never learns any account's `open_id` or `nickname`. That
  backend runs on the user's own machine — the app bundles it and serves it
  on localhost — so no call from this app reaches a remote service; the
  stripping is what keeps those two fields out of the request and its
  telemetry line regardless. The only identifier any call carries is the
  anonymous `clientId` (`src/lib/clientId.ts`, sent as `X-Client-Id`) —
  unrelated to any game account and never sent to blablalink.
- **Bookmarklet `servers` payload:** the bookmarklet probes all five servers
  (`GetUserCharacters` per `nikke_area_id`) and posts back
  `{ open_id, servers: [{ area, nickname, owned, character_details,
  recycle_room_researches }] }` — one entry per server that actually returned
  a roster (a server with none is silently skipped, not sent as empty).
  `useBookmarkletImport` reads this: one entry imports directly; more than one
  means the account holds rosters on several servers, so the hook surfaces a
  **server picker** (`status: 'choosing'`, `candidates: [{ area, count }]`,
  `choose(area)`) instead of guessing — `SyncRosterPanel` renders it as one
  button per server, labelled with `serverLabel(area)` and that server's unit
  count, and the user's pick is what actually gets assembled and imported.
- **Dropped units:** the assemble response carries
  `unmeasured: [{ name_en, reason }]` alongside `units` — owned Nikkes the
  backend could not give level-400 stats because nobody has measured them (a
  cored PILGRIM/OVERSPEC Supporter's per-core flat). `parseRosterJson` turns
  that into a warning line; never drop it silently, since these units ARE
  encoded and would otherwise look like they simply vanished from the roster.
- **A blank nickname never overwrites a stored one.** It comes from a separate
  blablalink call whose failure the bookmarklet swallows, so `''` means "this
  sync could not read it" — see `types/profile.ts`'s `upsertProfile`.
- **Upsert:** a sync for a new `(open_id, area)` pair creates and activates a
  profile; a sync for an existing pair refreshes its nickname/roster in place
  (and switches to it). If the refreshed roster actually differs from what was
  stored, that profile's cached results are invalidated — they no longer
  describe the current roster.
- **Profiles UI:** `ProfileSwitcher` lists profiles as
  `` `<nickname> (<server>)` `` (e.g. `FIENN (JP)`) with a dropdown to switch
  and a button to delete the active one (with a confirmation, since it drops
  that profile's roster and cache). The server suffix exists because the same
  nickname can legitimately appear twice — one account, two servers — and
  nickname alone can't tell those apart.
- **Migration:** the app isn't deployed yet, so a legacy `nikke-roster` key
  (pre-profiles) is **discarded** on load, not migrated — `useProfiles.ts`.
  The profile store itself, once it existed, went through one real schema
  change: the pre-server-support store keyed profiles by bare `open_id` and
  tracked `activeOpenId`. `useProfiles.ts`'s `migrate` re-keys every such
  profile to `` `${openId}:81` `` (that generation of synced data was always
  read from area 81) and re-derives `activeKey` from the old `activeOpenId`.
  This runs per-profile, not once for the whole store, so a store with a mix
  of old- and new-shaped entries migrates every entry correctly rather than
  short-circuiting on the presence of a new-shaped `activeKey`.

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
      "normal_attack_damage": number,
      "skill_damage": number        // everything neither a burst nor a normal attack (DoTs,
                                     // per-shot riders, self-cooldowned procs); the three
                                     // damage fields add up to total_damage
    }
  ],                                 // ranked by total_damage desc, length <= top_n
  "excluded_slugs": string[],        // submitted slugs the backend can't evaluate yet
                                     // (not encoded / no local data); excluded from the
                                     // search and shown as "not yet supported" — never a
                                     // 422 by themselves
  "engine_version": string          // see engine_version below (evaluate-decks section)
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
  "leftover_slugs": string[],        // usable units the allocation left out
                                     // (sorted; shown so the player knows who
                                     // sat on the bench)
  "engine_version": string          // see engine_version below (evaluate-decks section)
}
```
`422` mirrors `/api/recommend` (no feasible deck at all in the usable roster).

**Latency warning:** with a realistic full roster this endpoint takes **~1–2
minutes** (the backend runs thousands of 180 s simulations; it is already
process-pool parallelized). The client must NOT impose a request timeout, must
show a persistent in-progress state with copy telling the user the wait is
expected and roughly how long, and must disable re-submission while a run is in
flight.

### UI scope — raid mode (built)

The recommendation flow carries a mode switch: **single deck**
(`/api/recommend`) vs **raid allocation** (`/api/recommend-raid`) vs
**draft-based** (the same raid endpoint, seeded).

- Mode switch + `num_decks` selector (1–5, default 5) live in the recommend
  panel; the boss profile fields are shared across modes.
- Raid results render the decks as "Deck 1..N" (allocation order — they are
  NOT ranked alternatives), each with the same per-deck breakdown the single
  mode shows (total / burst / normal attack), plus the combined total
  prominently, plus leftover and excluded lists.
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

### POST /api/evaluate-decks (고정 편성 평가 — 솔로 5덱 / 유니온 3덱)

The three modes above all ask the engine to **build** a deck. This endpoint is
the opposite: the player has already filled every seat, and the engine only
**scores** what they built — no search, no substitution.

Request body:
```jsonc
{
  "roster": UserNikkeState[],
  "decks": [
    {
      "units": string[],   // exactly 5 character slugs
      "boss": BossProfile  // same shape as /api/recommend's boss
    }
  ]                        // 1-5 entries
}
```
Each deck carries **its own** boss rather than one boss shared across the
whole request — a union raid pits different decks against different bosses in
the same run, so the request has to let each deck name its own.

Response `200`:
```jsonc
{
  "decks": [
    {
      "deck": string[],              // the same 5 slugs, in the seating order
                                      // the ENGINE chose (B1 -> B2 -> B3) — NOT
                                      // necessarily the order submitted; this
                                      // is the order the player must reproduce
                                      // in game to get the stated damage
      "total_damage": number,
      "burst_damage": number,
      "normal_attack_damage": number
    }
  ],                                  // one entry per submitted deck, same order
  "combined_total_damage": number,    // sum over decks
  "excluded_slugs": string[],         // same meaning as /api/recommend
  "engine_version": string
}
```

`422` in five cases: an empty `decks` list; a deck whose `units` isn't exactly
5 slugs; the same slug submitted across two different decks; a slug the engine
can't evaluate (unencoded / no local data) — unlike `/api/recommend`'s
`excluded_slugs`, there's no substitute to route around here, since the deck
is fixed by the player, not searched; and a deck whose tier counts/seating
aren't fieldable, checked by `deck_search.deck_is_valid` — the same shape and
seating rule the search itself never violates, so it has to be checked
explicitly here.

**`engine_version`** is the axis the frontend's result cache invalidates on:
`lib/inputHash.ts` mixes it into the cache key, so a code change to the engine
— not just a change to the inputs — busts any stored result, since the
engine's output is only deterministic within one version of itself.
`GET /api/engine-version` exists as a separate call because the frontend
checks its cache **before** sending a request at all, so it has to learn the
current engine version independently of any response.

### `POST /api/charge-window`

FB 10초 창 안 타수와, 다음 타수를 사는 차지속도 임계값. `차지` 탭 전용.

요청:

```jsonc
{
  "slug": "scarlet-black-shadow",
  "roster": [ /* UserNikkeState[] — /api/recommend 와 같은 모양 */ ],
  "with_liberalio": true,
  "overrides": {
    "charge_speed_lines": [12.18],
    "max_ammo_percent": 0.8537,
    "reload_speed_percent": null
  }
}
```

응답:

```json
{
  "interval": 0.53,
  "magazine": 22,
  "charge_speed_percent": 0.0,
  "current": {"low_shots": 18, "low_probability": 0.132,
              "high_shots": 19, "high_probability": 0.868},
  "thresholds": [{"charge_speed_percent": 0.0, "interval": 0.53,
                  "outcome": {"low_shots": 18, "low_probability": 0.132,
                              "high_shots": 19, "high_probability": 0.868}}],
  "notes": ["탄창이 창 안에서 비어 재장전이 걸립니다 — ..."]
}
```

- `slug` 는 `scarlet-black-shadow` · `liberalio` · `neon-vision-eye` 셋뿐이고, 나머지는 **422**. 로스터에 그 슬러그가 없어도 422.
- `overrides` 의 각 필드는 `null` 이면 동기화된 로스터 값을 쓴다. `charge_speed_lines` 는 퍼센트 단위 줄 목록이고(집계 규칙이 미결이라 목록으로 받는다), `max_ammo_percent` · `reload_speed_percent` 는 비율이다.
- `thresholds` 는 케이던스를 **실제로 바꾸는** 차지속도만 오름차순으로 담는다. 두 타수와 각 확률을 함께 주는 이유는 FB 진입 위상이 플레이어의 선택이 아니기 때문이다.
- `notes` 는 사용자에게 그대로 보여줄 한국어 문장이다. 집계 규칙이 갈리는 경우는 `charge_speed_lines` 를 보낸 요청에서만 알 수 있으므로(동기화된 로스터는 부위별이 아닌 합계만 안다) 그때만 나온다. `with_liberalio` 를 켰는데 로스터에 리버렐리오가 없으면 버프 없이 계산하고 그 사실을 note 로 알린다.

### `GET /api/supported-units`

Feeds the palettes and every place a slug has to be named or drawn:
```jsonc
[ { "slug": string, "name": string,
    "burst_tier": 1 | 2 | 3,
    "element": "Fire" | "Water" | "Wind" | "Iron" | "Electric",
    "candidates": string[] | null } ]
```
Group the palette by `burst_tier` (B1/B2/B3). `name` is a display name (may be a
humanized slug). No request body; safe to fetch once and cache.

**Two vocabularies live in this list, and intersecting the roster with the wrong
one hides owned Nikkes.** A roster entry names the character the player *owns*;
a result deck names an engine *candidate*. They usually coincide, but a character
the engine models in several modes appears as both — one entry for the owned slug
(`bready`), carrying `candidates: ["bready-lingering", "bready-recommended"]`,
plus one entry per candidate. So:

- **Owned-vs-supported checks** (palette membership, the roster grid, pool
  counts) match on the roster's `character_slug`, which is the owned entry.
- **Naming or drawing a result deck** looks up the candidate slug directly.
- **A draft sends the owned slug**, same as the palette shows. The backend
  resolves the mode itself, by completing that deck once per candidate and
  keeping the best — the player never picks a mode, because for some characters
  (Bready) it is not theirs to pick.
- **Reconciling what was sent against what came back** — the per-deck diff and
  the deck matching in `DraftResults` — must map result slugs through
  `ownedSlugFor` (`types/supportedUnit.ts`, built from `candidates`). A drafted
  `bready` returns as `bready-lingering`; comparing raw slugs reads that as the
  engine dropping one unit and adding another, and can fail to pair the deck at
  all. `pinned_slugs` needs no mapping: it already names the seated candidate,
  which is what a result row draws.
- **An owned entry can be a candidate of itself**, and then its `candidates`
  includes its own slug — `rapi-red-hood` carries
  `["rapi-red-hood", "rapi-red-hood-b1"]`. She is also the only character whose
  candidates sit at DIFFERENT burst tiers, so `burst_tier` on her entry is the
  nominal one and does not tell you where a deck will actually seat her.
  Anything asking "does this deck cover tier N" reads `burstTiersFor`
  (`types/supportedUnit.ts`), not `burstTier`, or it warns "B1 없음" over a deck
  the engine fields happily. Chips, slot numerals and tier sorting still use the
  nominal tier: those place her in the palette, they do not judge a deck.

### `GET /api/raid-rotations`

Feeds the boss-setting screen's rotation card picker
(`components/RaidRotationPicker.tsx`). No request body; safe to fetch once
and cache.

Response `200`:
```jsonc
{
  "schema_version": number,
  "rotations": [
    {
      "id": string,
      "raid": "solo" | "union",
      "title": string,
      "starts_at": string | null,  // ISO 8601 with KST offset; null when the
                                    // announcement gave no start time
      "ends_at": string,           // ISO 8601 with KST offset
      "source_url": string,
      "source_locale": "ko" | "en",
      "read_on": string,           // YYYY-MM-DD, the day the announcement was read
      "bosses": [
        {
          "name": string,
          "weakness": "Fire" | "Water" | "Wind" | "Iron" | "Electric",
          "range_band": "near" | "mid" | "far" | null,  // null when the
                                    // announcement states no distance (solo raids)
          "stated": Record<string, string | string[]>
        }
      ]
    }
  ]
}
```
**`weakness` and `range_band` are the only machine-read fields per boss.**
Picking a rotation card writes those two into the boss profile — the weakness
becomes `element`, the band becomes `effective_range_band` — and resets every
other field to its default. Both arrive already translated into engine
vocabulary: the announcement is read by the `/update-raid-bosses` skill, which
is where Korean wording (`근거리` → `near`) is turned into these values.

`stated` is the announcement's raw prose — squad recommendation, part-break
hints, grade, flavour text, whatever that raid type's announcement happens to
print — keyed however the announcement laid it out, one array entry per line
for a multi-line value. It is a provenance record only: nothing renders it and
nothing reads it. Do not add logic that parses a `stated` value to drive
behavior — that would put a Korean-prose parser in the app, which is exactly
what the skill exists to keep out.

### Portraits

Static, served from `frontend/public/portraits/`. The map lives at
`/portraits/manifest.json`:
```jsonc
{ "source": "...", "portraits": { "<slug>": "<filename>" } }
```
Resolve a slug's icon as `manifest.portraits[slug]` → prefix `/portraits/`. A slug
with no entry gets an empty placeholder of the same size, so a row or grid stays
aligned. Every view must work identically with or without a portrait — icons are
a presentation layer only.

The manifest is keyed by **both** vocabularies above (owned slugs and engine
candidates), since the palette asks for one and a result row asks for the other;
a character's candidates all resolve to her single portrait file. Regenerate with
`python scripts/download_portraits.py` after adding a slug — keying it on one
vocabulary only leaves the other drawing empty boxes.

The art is **256×512 full-body**, and it is the only size there is (probed:
`si_`/`ci_`/`fi_`/`icon_` prefixes, `.png`, and `/assets/nikke/` all 404). The
square face crop the deck slots, roster tiles and result rows use is pure CSS —
`object-fit: cover` with `object-position: center 18.75%` on a square box. See
`docs/insights.md` for why that number.

### UI scope — draft editor (built)

- **Palette:** owned units (from the active profile's roster) ∩ supported
  (`/api/supported-units`), grouped B1/B2/B3. A chip is a portrait plus a
  five-row stat column (breakthrough, core, S1, S2, B); name, tier, element and
  overload are on a hover card. Clicking the portrait toggles the unit in or out
  of the search pool.
- **Editor:** 5 decks × 5 square slots, always drawn (an open slot shows `+`).
  Slots are membership (order engine-assigned) with a per-unit **lock toggle**;
  a unit may sit in at most one deck (enforce client-side). A slot is both a
  drop target and a drag source, so a misplaced unit is **moved** between decks
  rather than removed and re-added.
- **Submit:** build `draft` from the editor and POST to `/api/recommend-raid`.
  - Complete draft with `within_draft`/`baseline_total_damage` present → render the
    **three tiers** (baseline → within_draft +Δ1 → recommended +Δ2), a per-deck diff
    vs the submitted draft, and `pinned_slugs` badges.
  - Otherwise → the single recommended allocation (reuse the raid results view).
- Keep the fetch client confined to `src/api/`; mirror the existing raid module.

### UI scope — 평가 모드 · 유니온 레이드 탭 (built)

- The recommend tab gained a fourth mode, **평가** (1–5 decks, one shared boss),
  alongside single/raid/draft. A new third top-level tab, **유니온 레이드**,
  holds 1–3 battles (default 3), each with its own full boss profile and a
  180s default fight duration.
- Both screens submit to `/api/evaluate-decks` and share one results
  component, `components/EvaluationResults.tsx`, which labels each deck with
  its own boss's element and states that the shown seating order is the one
  to reproduce in game.
- Both reuse `DraftEditor` with the new `showLocks?: boolean` prop (default
  `true`) set to `false` — there's nothing to lock when every seat is already
  fixed by the player.
- **Evaluate results are not cached.** The call resolves in seconds, not the
  minutes raid/draft allocation takes, so re-running is cheap; caching it
  would also mean widening the stored-result schema, which is shaped for
  allocation results, not for a per-deck-per-boss score.

### UI conventions

- **Dark theme only.** `src/index.css` holds the tokens; there is no light set
  and no `prefers-color-scheme` split. Never hardcode a colour that a token
  covers.
- **Units are shown as faces, never as slugs.** A slug is an identifier. Names
  come from `/api/supported-units`; anything it does not know (a unit the engine
  cannot simulate yet) derives a name from its slug via `src/lib/unitName.ts`.
- **Overload lines are sorted, never in arrival order** — see `sortOverload` in
  `components/InvestmentSummary.tsx`. A fixed order is what lets two units be
  compared down the column.

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
