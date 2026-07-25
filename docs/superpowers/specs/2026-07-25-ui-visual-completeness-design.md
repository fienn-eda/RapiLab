# UI visual completeness — design

**Date:** 2026-07-25
**Status:** approved, phased implementation
**Scope:** `frontend/` only. No backend or engine changes.

## Context

Yesterday's session fixed the frontend's *structure*: a dev mock that made the
palette lie was deleted, the roster moved to its own tab, palette chips shrank
to a portrait, and draft seats became drag-and-drop targets. What was
explicitly left undone is visual completeness — the app still looks like a
default-system-font admin tool.

Measured against the real 159-Nikke roster, the gap is not only cosmetic:

| Finding | Number |
|---|---|
| Roster tab cards, one per full-width row | 159 |
| …of those, not supported by the engine (no portrait, cannot be fielded) | 89 |
| Owned ∩ engine-supported — what the palette actually shows | 70 |
| Palette label claims are in the search pool | "159/159" |
| Palette chip box vs. its contents | 134×154 holding 72×144 + 48×85 |

Names render as raw slugs (`ada-wong`, `alice-wonderland-bunny`). Recommend
results render as monospace slug lists while every other surface is portraits.

## Decisions

All six were chosen by Fienn during brainstorming.

1. **Target look:** game tool, not admin dashboard. Portraits lead; text supports.
2. **Theme:** dark only. The light token set and the `prefers-color-scheme`
   split are removed. Portrait art reads better on a dark ground, and one
   theme is half the surface area to finish properly.
3. **Engine-unsupported units:** kept, but demoted — usable units in the grid,
   the other 89 in a `<details>` below, collapsed by default, names only.
4. **Roster tile content:** everything on the tile, including overload. No
   hover card in the Roster tab; that tab exists to read investment.
5. **Recommend results:** portrait rows, matching the palette's language.
6. **Draft deck slots:** the game's squad-slot look — square, face-only,
   `+` for an empty slot, no name text, burst tier as the only badge.

## Portraits: no new image source needed

The deck slots want a square face. The shipped art is 256×512 full-body from
lootandwaifus (`mi_c###_00_s.webp`).

Probed for a square variant and there is none: `si_`, `ci_`, `fi_`, `icon_`
prefixes, a `.png` extension, and the `/assets/nikke/` path all return 404.
`mi_c###_00_s.webp` is the only asset. This confirms the earlier finding that
`_l`/`_m`/no-suffix 404 as well.

Cropping the existing art is enough. Comparing square windows at y = 0/24/48/72
of the 512-tall source, **y=48** keeps the whole head and the chin for every
sampled character; y=0 leaves dead headroom and clips chins, y=72 starts
cutting hair.

That crop is reachable in CSS with no image reprocessing. On a square box with
`object-fit: cover`, the image renders W×2W, hiding W box-pixels = 256 image
rows. Hiding 48 of them from the top is `object-position: center 18.75%`
(48/256).

```css
.slot__portrait {
  aspect-ratio: 1;
  object-fit: cover;
  object-position: center 18.75%;
}
```

## Architecture

Three surfaces show a unit: the roster tile, the palette chip, and a deck slot
/ result cell. They stay three components — a roster tile is static
information, a palette chip is a toggle and a drag source, a deck slot is a
drop target with lock/remove — and a single component with a `variant` prop
would be a bag of flags. They share primitives instead, continuing the pattern
`InvestmentSummary` already established across the roster card and the palette.

New shared pieces:

- **`lib/unitName.ts`** — `displayName(slug, supportedUnits)`. A supported slug
  uses the backend's `name`; anything else derives from the slug
  (`ada-wong` → `Ada Wong`). The 89 unsupported units have no name source in
  the frontend at all, and derivation avoids shipping a second directory.
- **`useSupportedUnits` hoisted to `App`** — one fetch feeds both tabs. Today
  only `RecommendPanel` calls it, so the Roster tab has no access to names,
  burst tiers or elements. With the backend down, name resolution degrades to
  slug-derived and the Roster tab still renders.

## Phase 1 — draft deck slots

The live pain: a unit dropped into the wrong deck must be removed and re-added.

**Slot rendering.** Each deck always draws `MAX_DRAFT_SEATS_PER_DECK` (5)
slots. A filled slot is the square face portrait with the burst tier
(Ⅰ/Ⅱ/Ⅲ) in the top-left corner; an empty slot is a `+` placeholder. Drawing
empty slots makes the drop target large and makes remaining capacity readable
without counting.

**Moving between decks.** The slot itself becomes a drag source, using the
same `DRAG_SLUG_TYPE` the palette uses. The drop handler collapses to one
path — *remove the slug from wherever it sits, then place it here*:

```ts
export const moveUnit = (draft: Draft, deckIndex: number, slug: string): Draft => {
  const locked = /* the seat's current lock state, or false */
  return placeUnit(removeUnitBySlug(draft, slug), deckIndex, slug, locked)
}
```

A palette drag hits the same code: the slug is not seated, so
`removeUnitBySlug` no-ops and the behaviour is identical to today's. The
`locked` flag survives a move. A full target deck already refuses the drop —
`onDragOver` declines to `preventDefault`, so `onDrop` never fires.

**Controls.** Removing the name text also removes the `Lock` checkbox label and
the `×` button's text. Both keep their function as corner controls on the
slot: a lock toggle shown always (accent when locked), and a remove `×`
revealed on hover or focus. Both are real buttons, so keyboard access
survives.

**Burst-tier warning.** Seats are membership only — the engine assigns burst
roles — but a deck still needs tiers 1, 2 and 3 present to be feasible. With
names gone the deck title carries it: `Deck 1 · 2/5` plus a warning when a
tier is missing.

**Lookups.** `DraftEditor` gains `burstTierFor(slug)` alongside the existing
`portraitFor(slug)`, both supplied by `RecommendPanel` from `supportedUnits`.

## Phase 2 — dark theme and tokens

`index.css` drops the light token block and the `prefers-color-scheme` media
query; `color-scheme: dark`. Adds a five-colour element token set
(Fire/Water/Wind/Iron/Electric) so a portrait's border states its element
without a text label, and layers `--bg` / `--surface` / `--surface-2` for
depth rather than one flat ground.

## Phase 3 — roster tab

A tile grid of the 70 usable units: portrait with element-tinted border,
breakthrough stars and core overlaid on the portrait, then name, skill levels
and overload lines. The 89 unsupported units go into a collapsed `<details>`
below, names only.

Two honesty fixes ride along: the header still says "Enter each owned Nikke's
investment data from ShiftyPad" when the roster has been sync-only for a
while, and the palette summary claims `159/159 in the search pool` while
rendering 70 chips — the count must be the owned ∩ supported intersection,
with the excluded remainder stated.

## Phase 4 — recommend results

`DeckCard` becomes a portrait row: five square faces with names beneath,
damage on the right, the pin badge on the portrait, and the existing
added/removed diff below. `RaidResults`, `DraftResults` and `DeckResults` all
render through `DeckCard`, so one change reaches all three.

## Testing

Baseline is 234 frontend tests passing; that number only goes up.

- `moveUnit`: moves between decks, preserves `locked`, no-ops on a full
  target, and behaves as a plain place for an unseated slug.
- Dropping a seated unit on another deck relocates it rather than duplicating
  or dropping it.
- Empty slots render to fill a deck to five.
- `displayName`: supported slug takes the backend name; unsupported derives
  from the slug.
- The unsupported-unit section is collapsed by default and lists the right
  count.
- A result deck renders portraits and names, not slugs.

Vitest runs with `css: false` and cannot see layout. Every phase is checked in
a real browser with Playwright screenshots before it is committed — that is
how the `hidden`-attribute bug got through a green suite yesterday.
