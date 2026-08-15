// 오버로드 옵션의 이름 규칙과, 합계 뒤의 롤을 장비 부위별로 되돌리는 배치.
// 표시(오버로드 줄)와 정렬(필터 툴바)이 같은 목록을 봐야 하므로 컴포넌트가
// 아니라 lib에 둔다.

import type { OverloadLine } from '../types/userNikkeState'

// Overload names are long enough to set the width of anything they sit in
// ("우월코드 대미지 증가"), and there are only seven of them, so the player
// reads them as symbols rather than sentences. Abbreviate to the forms used at
// the table (Fienn, 2026-07-25). The trailing "증가" is dropped first: every
// type carries it, so it distinguishes nothing.
const ABBREVIATIONS: Record<string, string> = {
  '우월코드 대미지': '우코',
  '최대 장탄 수': '장탄',
  공격력: '공',
  '차지 대미지': '차댐',
  '차지 속도': '차속',
  '크리티컬 확률': '크확',
  '크리티컬 대미지': '크댐',
  // OVERLOAD_KEYS에는 없다 - 정렬 메뉴가 아니라 표시만 줄인다(Fienn, 2026-08-09).
  명중률: '명중',
}

// The order Fienn reads them in (2026-07-25), not the order blablalink happens
// to return. A fixed order is what lets two units be compared down the column
// instead of line by line - and it doubles as the order of the sort menu.
export const OVERLOAD_KEYS = ['우코', '공', '장탄', '차속', '크댐', '크확', '차댐'] as const

export type OverloadKey = (typeof OVERLOAD_KEYS)[number]

/** The name without the trailing "증가" every type carries. */
const stripIncrease = (name: string): string => name.replace(/\s*증가$/, '')

/** Short label for an overload line. An unrecognised name (a new effect type,
 * or another locale) keeps its full text rather than being mangled. */
export const abbreviateOverload = (name: string): string => {
  const stripped = stripIncrease(name)
  return ABBREVIATIONS[stripped] ?? stripped
}

/** An overload line's name as the game's own gear screen writes it: the stat in
 * brackets, without the "증가" every type shares.
 *
 * Deliberately a second function rather than a flag on `abbreviateOverload` -
 * the summary line abbreviates so a tile stays narrow, the detail view spells
 * the stat out because it is redrawing an in-game screen. To spell the detail
 * view short as well, this body becomes `[${abbreviateOverload(name)}]` and the
 * grid's minimum column width in App.css comes down with it. */
export const formatOverloadName = (name: string): string => `[${stripIncrease(name)}]`

/** Sorts overload lines into OVERLOAD_KEYS order. An unrecognised effect sorts
 * after all the known ones, keeping its incoming order among its peers - a new
 * type should appear, not disappear or displace a known one. */
export const sortOverload = <T extends { name: string }>(options: T[]): T[] => {
  const rank = (option: T) => {
    const index = OVERLOAD_KEYS.indexOf(abbreviateOverload(option.name) as OverloadKey)
    return index === -1 ? OVERLOAD_KEYS.length : index
  }
  return [...options].sort((a, b) => rank(a) - rank(b))
}

// The four gear pieces overload rolls on, in the order the game's equipment
// screen lays them out - head and torso across the top, arm and leg beneath.
// Read two-up that order IS the layout, so the grid needs no second list.
// Mirrors GEAR_SLOTS in backend/app/overload_decode.py.
export const GEAR_SLOTS = ['head', 'torso', 'arm', 'leg'] as const

export type GearSlot = (typeof GEAR_SLOTS)[number]

export const GEAR_SLOT_LABEL: Record<GearSlot, string> = {
  head: '머리',
  torso: '몸통',
  arm: '팔',
  leg: '다리',
}

/** How hard the game draws attention to a roll. */
export type RollTier = 'max' | 'high'

// The game emphasises a roll by the level it landed at, not by its percent: 15
// - the top of the roll range - is drawn on a black row, 12 through 14 get a
// bright value, and anything lower is plain. Measured off Fienn's own gear
// screen (2026-08-15): 최대 장탄 수 85.37% is the level 15 black row and
// 우월코드 대미지 26.36% the level 13 bright one, both confirmed against the
// value table. The ceiling matches MAX_LEVEL in backend/app/overload_decode.py.
const TOP_ROLL_LEVEL = 15
const HIGH_ROLL_LEVEL = 12

/** The emphasis a roll of this level earns, or null for none. An unknown level
 * earns none: a roster synced before levels were carried must not be drawn as
 * if every roll maxed. */
export const rollTier = (level: number | undefined): RollTier | null => {
  if (level == null) return null
  if (level >= TOP_ROLL_LEVEL) return 'max'
  return level >= HIGH_ROLL_LEVEL ? 'high' : null
}

/** One roll as the gear screen shows it: which stat, how much, how high it
 * rolled, and which of its piece's three option rows it sits in. */
export interface GearRoll {
  name: string
  value: number
  level?: number
  index?: number
}

export interface GearPiece {
  slot: GearSlot
  /** In option-row order, 0 to 3 of them. Empty is normal - a piece can carry
   * fewer than three rolls, and the empty rows still hold the layout open. */
  rolls: GearRoll[]
}

/** One unit's overload as the game's equipment screen arranges it, or null when
 * that screen cannot be drawn honestly.
 *
 * The engine and blablalink both read overload as per-stat totals; the game
 * reads it as four pieces of gear. This turns the first back into the second
 * using the rolls each total was summed from.
 *
 * null means "show the summed view instead", for three cases that would each
 * make the grid quietly understate the player's gear: a roster synced before
 * the rolls were carried, a total hand-edited away from its rolls (validateDraft
 * drops `lines` rather than send a stale pair), and a slot name that is not one
 * of the four. Each would drop a whole stat out of a grid that looks complete -
 * the summed view says less, but it never shows gear that is not there. */
export const byGearPiece = (
  options: { name: string; value: string | number; lines?: OverloadLine[] }[],
): GearPiece[] | null => {
  if (options.length === 0) return null
  const placed = new Map<GearSlot, GearRoll[]>(GEAR_SLOTS.map((slot) => [slot, []]))
  for (const option of options) {
    if (!option.lines?.length) return null
    for (const line of option.lines) {
      const rolls = placed.get(line.slot as GearSlot)
      if (!rolls) return null
      rolls.push({ name: option.name, value: line.value, level: line.level, index: line.index })
    }
  }
  return GEAR_SLOTS.map((slot) => ({ slot, rolls: inRowOrder(placed.get(slot)!) }))
}

/** A piece's rolls in the order the game lists them. Falling back to stat order
 * keeps a roster synced before the row numbers were carried readable, and keeps
 * it consistent with the summary line above it. */
const inRowOrder = (rolls: GearRoll[]): GearRoll[] =>
  rolls.every((roll) => roll.index != null)
    ? [...rolls].sort((a, b) => a.index! - b.index!)
    : sortOverload(rolls)

// Every gear piece offers three overload rows, rolled or not.
const ROWS_PER_PIECE = 3

/** A piece's rolls laid out on its option rows, padded to the three the gear
 * screen always shows. An empty row is `undefined`.
 *
 * Placed by row number rather than packed together, because the rows a piece is
 * missing are not always its last ones. DEF rolls never reach the frontend -
 * overload_decode drops them as `unconsumed_effect_types` - so a piece whose
 * second row rolled DEF arrives here as rows 1 and 3. Packing would slide the
 * survivors up and blank the bottom row, claiming the piece rolled its first
 * two rows when what it actually has is a hole in the middle.
 *
 * Rolls with no row number are packed instead: which row is blank is precisely
 * what a roster synced before the numbers were carried cannot say, and guessing
 * would put the hole somewhere the player can check and find wrong. */
export const gearRows = (rolls: GearRoll[]): (GearRoll | undefined)[] => {
  const placed = rolls.every((roll) => roll.index != null)
  const rows: (GearRoll | undefined)[] = Array.from({
    length: Math.max(
      ROWS_PER_PIECE,
      placed ? Math.max(0, ...rolls.map((roll) => roll.index!)) : rolls.length,
    ),
  })
  rolls.forEach((roll, packedRow) => {
    rows[placed ? roll.index! - 1 : packedRow] = roll
  })
  return rows
}
