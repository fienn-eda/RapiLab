// The player's unit grid, shared by all three recommend modes. Owned units
// (active profile roster) intersected with engine-supported units
// (GET /api/supported-units), grouped under B1/B2/B3.
//
// A chip is its portrait and its skill levels, nothing else. Clicking
// anywhere on the chip toggles whether that unit is in the candidate pool
// (default in); an excluded one greys out. Everything a chip used to spell
// out - name, burst tier, element, overload rolls - is on the hover card
// instead, so the grid stays dense enough to scan a whole roster at once.
//
// On a seating screen (`onSeat`) a press seats that unit instead, which the
// keyboard reaches as well as the mouse. `draggable` adds dragging the
// portrait onto a deck on top of that - a browser-only convenience, since the
// packaged app's WebView2 delivers no drop.

import { useEffect, useState } from 'react'
import { usePortraitManifest } from '../hooks/usePortraitManifest'
import { BURST_TIERS, type SupportedUnit } from '../types/supportedUnit'
import type { UserNikkeState } from '../types/userNikkeState'
import { elementLabel } from '../lib/elementName'
import { EMPTY_FILTER, filterAndSort, type UnitFacets, type UnitFilterState } from '../lib/unitFilter'
import { HELP } from '../lib/helpText'
import { FavoriteItemBadge } from './FavoriteItemBadge'
import { OverloadLines, SkillPip } from './InvestmentSummary'
import { UnitFilterBar } from './UnitFilterBar'

/** Breakthrough, core and Favorite Item for one unit. They live on NikkeDraft,
 * not on the wire-shaped UserNikkeState the engine takes, so they arrive
 * alongside the roster rather than inside it. */
export interface UnitInvestment {
  grade?: number
  core?: number
  favoriteItem?: boolean
}

const STAR_SLOTS = 3

/** 「니케 풀에서 풀어 주세요」 말풍선이 떠 있는 시간(ms). 답이지 알림이 아니라
 * 스스로 사라진다 - 닫기 버튼을 달면 유저가 치워야 할 것이 하나 더 생기고,
 * 안 사라지면 팔레트 밖을 눌렀을 때 말풍선만 남는다. */
const BLOCKED_NOTICE_MS = 4000

/** dataTransfer key for a dragged unit. A custom type (rather than text/plain)
 * keeps a stray drag from elsewhere in the page reading as a unit drop. */
export const DRAG_SLUG_TYPE = 'application/x-nikke-slug'

/** Toggles a slug's membership in an excluded-slugs set - the Set half of
 * "exclude". RecommendPanel and UnionRaidPanel both pair this with
 * DraftEditor's removeUnitBySlug (unseat a NEWLY excluded unit from wherever
 * it's placed) so "exclude" means the same thing everywhere it appears:
 * out of the deck AND out of the submitted roster, never one without the
 * other. */
export const toggleExcludedSlug = (excluded: Set<string>, slug: string): Set<string> => {
  const next = new Set(excluded)
  if (next.has(slug)) next.delete(slug)
  else next.add(slug)
  return next
}

interface UnitPaletteProps {
  /** The owned, validated roster - membership decides what the palette shows,
   * and each entry supplies that unit's investment display. */
  roster: UserNikkeState[]
  supportedUnits: SupportedUnit[]
  /** Slugs the user has toggled OUT of the candidate pool. Absent on a screen
   * with no pool to narrow. */
  excludedSlugs?: string[]
  /** Omit on a screen where excluding a unit would do nothing — the chip then
   * stays a drag source instead of pretending to be a toggle. */
  onToggleExclude?: (slug: string) => void
  /** Draft mode only: slugs already seated in a deck. */
  usedSlugs?: string[]
  /** Draft mode only: lets an included, unseated unit be dragged onto a deck.
   * A browser-only convenience - see `onSeat`. */
  draggable?: boolean
  /** Draft mode only: pressing the chip seats the unit. This is the path that
   * has to work — the packaged app's WebView2 fires `dragstart` and then
   * delivers no dragover or drop at all, so dragging can never finish there.
   * It also puts seating on the keyboard, which dragging never could.
   *
   * Given together with `onToggleExclude` this wins: one press cannot mean two
   * things, and on a screen with decks beside the palette, pressing a Nikke
   * means putting her in one. Excluding lives on the roster tab instead. */
  onSeat?: (slug: string) => void
  /** Breakthrough/core per slug. Defaults to unknown, which draws the two
   * cells as dashes rather than claiming a unit has none. */
  investmentFor?: (slug: string) => UnitInvestment
}

const NO_INVESTMENT: UnitInvestment = {}

export function UnitPalette({
  roster,
  supportedUnits,
  excludedSlugs,
  onToggleExclude,
  usedSlugs = [],
  draggable = false,
  onSeat,
  investmentFor = () => NO_INVESTMENT,
}: UnitPaletteProps) {
  const { portraitFor } = usePortraitManifest()
  const ownedBySlug = new Map(roster.map((nikke) => [nikke.character_slug, nikke]))
  const usedSet = new Set(usedSlugs)
  const excludedSet = new Set(excludedSlugs ?? [])
  const shown = supportedUnits.filter((unit) => ownedBySlug.has(unit.slug))

  /** 배치 화면에서 제외된 칩을 눌렀을 때 뜨는 말풍선의 주인. 같은 칩을 다시
   * 눌러도 시계가 처음부터 가도록 nonce를 함께 센다 - slug만 담으면 React가
   * 같은 값이라고 보고 상태를 안 바꿔, 사라지려던 말풍선이 그대로 사라진다. */
  const [blocked, setBlocked] = useState<{ slug: string; nonce: number } | null>(null)

  useEffect(() => {
    if (blocked === null) return
    const timer = setTimeout(() => setBlocked(null), BLOCKED_NOTICE_MS)
    return () => clearTimeout(timer)
  }, [blocked])

  // Owned by the palette rather than by RecommendPanel: nothing outside this
  // component may read the filter, precisely because reading it would invite
  // narrowing the request to match. Mode switching remounts the palette and so
  // resets the filter, which is the accepted cost of keeping it local.
  const [filter, setFilter] = useState<UnitFilterState>(EMPTY_FILTER)

  const facetsFor = (unit: SupportedUnit): UnitFacets => ({
    slug: unit.slug,
    name: unit.name,
    element: unit.element,
    burstTier: unit.burstTier,
    overload: ownedBySlug.get(unit.slug)!.overload_options,
    excluded: excludedSet.has(unit.slug),
  })

  // Sorted across the whole palette, then partitioned by tier below - a
  // partition preserves relative order, so each group comes out in sort order
  // without sorting three times.
  const visible = filterAndSort(shown, facetsFor, filter)

  return (
    <div className="palette">
      {shown.length > 0 && (
        <UnitFilterBar
          value={filter}
          onChange={setFilter}
          shown={visible.length}
          total={shown.length}
          excludable={excludedSlugs !== undefined}
        />
      )}
      {/* 처음부터 자리를 지키는 라이브 영역. 문구와 함께 영역 자체가 새로 붙으면
          스크린리더가 놓치는 일이 있어, 문장만 갈아 끼운다. role="status" 대신
          같은 뜻의 속성 둘을 직접 거는 이유는, 팔레트를 품은 화면이 제 진행
          상황을 알리는 status를 이미 갖고 있어서다 - 한 화면에 status가 둘이면
          어느 쪽이 그 화면의 답인지 말할 수 없다. */}
      <p className="visually-hidden" aria-live="polite" aria-atomic="true">
        {blocked === null ? '' : HELP.draft.excludedElsewhere}
      </p>
      {BURST_TIERS.map((tier) => {
        const units = visible.filter((unit) => unit.burstTier === tier)
        if (units.length === 0) return null
        return (
          <section key={tier} className="palette__group">
            {/* Same burst icon the roster grid and the filter chips use; the
                alt keeps the group named for anyone who cannot see it. */}
            <h4 className="palette__heading">
              <img
                className="burst-heading__icon"
                src={`/elements/icon-burst-${tier}.png`}
                alt={`B${tier}`}
              />
            </h4>
            <ul className="palette__list">
              {units.map((unit) => {
                const owned = ownedBySlug.get(unit.slug)!
                const isUsed = usedSet.has(unit.slug)
                const isExcluded = excludedSet.has(unit.slug)
                const portrait = portraitFor(unit.slug)
                const { grade, core, favoriteItem } = investmentFor(unit.slug)
                const classes = ['palette__item']
                if (isExcluded) classes.push('palette__item--excluded')
                if (isUsed) classes.push('palette__item--seated')

                // 표적은 칩 테두리 안 전체다. 껍데기 핸들러는 버튼의 disabled를
                // 우회하므로 같은 조건을 여기서 다시 본다 - 안 그러면 제외된
                // 칩의 스킬레벨 칸을 눌러 배치할 수 있다.
                //
                // 제외된 칩은 막되 침묵하지는 않는다: 제외를 푸는 곳은 니케 풀
                // 탭이라 이 화면에는 되돌릴 컨트롤이 없고, 아무 답도 없으면
                // 칩이 고장 난 것으로 읽힌다.
                const handleChipClick = onSeat
                  ? () => {
                      if (isExcluded) {
                        setBlocked((prev) => ({ slug: unit.slug, nonce: (prev?.nonce ?? 0) + 1 }))
                        return
                      }
                      // 다른 칩을 눌렀다는 것 자체가 말풍선을 다 읽었다는 뜻이다.
                      setBlocked(null)
                      if (isUsed) return
                      onSeat(unit.slug)
                    }
                  : onToggleExclude
                    ? () => onToggleExclude(unit.slug)
                    : undefined

                return (
                  <li
                    key={unit.slug}
                    className={classes.join(' ')}
                    // Element drives a colour, not a word: the chip has no room
                    // to spell it and the hover card already does.
                    data-element={unit.element}
                    onClick={handleChipClick}
                  >
                    <button
                      type="button"
                      className="palette__face"
                      // Three shapes, and the name always lives here because
                      // the chip shows no text of its own:
                      //  - seating screen: pressing seats her, and a chip
                      //    already seated has nothing left to do.
                      //  - pool toggle: a toggle, so it reports its state
                      //    rather than pretending each press is fresh.
                      //  - neither: a plain drag source, taken out of the tab
                      //    sequence since a keyboard user would find nothing
                      //    to press.
                      aria-pressed={!onSeat && onToggleExclude ? !isExcluded : undefined}
                      aria-label={
                        onSeat
                          ? isUsed
                            ? `${unit.name} 배치됨`
                            : isExcluded
                              ? `${unit.name} 제외됨`
                              : `${unit.name} 배치`
                          : onToggleExclude
                            ? `${unit.name} 사용`
                            : unit.name
                      }
                      // 앉은 칩은 진짜로 죽는다 - 앉았다는 테두리가 이미 이유를
                      // 말한다. 제외된 칩은 aria-disabled로 「눌러도 안 된다」만
                      // 알리고 초점과 클릭은 살려 둔다: 왜 안 되는지는 누른
                      // 뒤에야 뜨는데, disabled면 그 누름이 아예 안 온다.
                      disabled={onSeat !== undefined && isUsed}
                      aria-disabled={onSeat !== undefined && isExcluded ? true : undefined}
                      tabIndex={onSeat || onToggleExclude ? undefined : -1}
                      draggable={draggable && !isExcluded && !isUsed}
                      onDragStart={(event) => {
                        event.dataTransfer.setData(DRAG_SLUG_TYPE, unit.slug)
                        event.dataTransfer.effectAllowed = 'move'
                      }}
                    >
                      <span className="palette__figure">
                        {portrait ? (
                          <img className="palette__portrait" src={portrait} alt="" />
                        ) : (
                          <span className="palette__portrait palette__portrait--missing" />
                        )}
                        {/* On the art, like the roster card's - the chip shows
                            no text of its own to hang it off. */}
                        <FavoriteItemBadge equipped={favoriteItem} />
                        {/* Everything the chip stopped showing. Presentational:
                            the button is already named, and this would other-
                            wise read back as a second copy of the same unit. */}
                        <span className="palette__details" role="presentation">
                          <span className="palette__name">{unit.name}</span>
                          <span className="palette__meta">
                            B{unit.burstTier} · {elementLabel(unit.element)}
                          </span>
                          <OverloadLines
                            options={owned.overload_options}
                            emptyText="오버로드 없음"
                          />
                        </span>
                      </span>
                    </button>

                    {/* Five rows top to bottom: breakthrough, core, then the
                        three skill levels. Breakthrough and core get a cell
                        each here (unlike the roster card's single badge) so
                        the column lines up across every chip in the grid. */}
                    <ul className="palette__stats">
                      <li className="skills__pip palette__stat--grade">
                        <span className="investment__stars">
                          {grade === undefined
                            ? '—'
                            : '★'.repeat(grade) + '☆'.repeat(Math.max(0, STAR_SLOTS - grade))}
                        </span>
                      </li>
                      <li className="skills__pip palette__stat--core">
                        <span className="investment__core">{core ? `+${core}` : '—'}</span>
                      </li>
                      <SkillPip label="S1" level={owned.skill_levels.skill1} />
                      <SkillPip label="S2" level={owned.skill_levels.skill2} />
                      <SkillPip label="B" level={owned.skill_levels.burst} />
                    </ul>

                    {/* 칩 오른쪽으로 열린다 - 오버로드 팝오버가 아래로 열리는데,
                        누르는 동안은 마우스가 칩 위에 있어 둘이 동시에 떠 있다.
                        읽히는 것은 팔레트 뿌리의 라이브 영역 쪽이라 여기서는
                        숨긴다: 같은 문장을 두 번 읽어 준다. */}
                    {blocked?.slug === unit.slug && (
                      <p className="palette__blocked" aria-hidden="true">
                        {HELP.draft.excludedElsewhere}
                      </p>
                    )}
                  </li>
                )
              })}
            </ul>
          </section>
        )
      })}
    </div>
  )
}
