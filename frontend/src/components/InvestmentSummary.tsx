// The two investment facts the player actually reads off a unit: how far its
// skills are levelled, and what its overload rolled. Shared by the roster card
// and the unit palette, which hold the same numbers in different shapes - the
// card renders an editable-form draft (strings), the palette a validated
// UserNikkeState (numbers) - so both accept either.

import {
  abbreviateOverload,
  formatOverloadName,
  gearRows,
  GEAR_SLOT_LABEL,
  rollTier,
  sortOverload,
  type GearPiece,
} from '../lib/overload'

type Displayable = string | number

interface SkillLevelsProps {
  levels: { skill1: Displayable; skill2: Displayable; burst: Displayable }
  /** 'column' stacks the three beside a portrait; 'row' runs them inline. */
  layout?: 'row' | 'column'
}

/** One labelled cell in a stat column. An `<li>`, so whatever lists it lives
 * in owns the column - the palette's runs to five rows, the roster card's to
 * three, and neither should have to restate what a pip looks like. */
export function SkillPip({ label, level }: { label: string; level: Displayable }) {
  return (
    <li className="skills__pip">
      <span className="skills__label">{label}</span>
      <span className="skills__level">{level === '' ? '—' : level}</span>
    </li>
  )
}

/** Skill levels as three labelled pips. Order matches the game's skill list. */
export function SkillLevels({ levels, layout = 'row' }: SkillLevelsProps) {
  const pips: [string, Displayable][] = [
    ['S1', levels.skill1],
    ['S2', levels.skill2],
    ['B', levels.burst],
  ]
  return (
    <ul className={layout === 'column' ? 'skills skills--column' : 'skills'}>
      {pips.map(([label, level]) => (
        <SkillPip key={label} label={label} level={level} />
      ))}
    </ul>
  )
}

interface OverloadLinesProps {
  options: { name: string; value: Displayable }[]
  /** Copy shown when a unit rolled no overload at all. */
  emptyText: string
}

/** Overload lines as name/value pairs. Which stat rolled and how high is the
 * whole point - a count would say nothing about whether a unit is worth
 * fielding - so every line is named, never summarised. */
export function OverloadLines({ options, emptyText }: OverloadLinesProps) {
  if (options.length === 0) return <p className="overload__empty">{emptyText}</p>
  return (
    <ul className="overload">
      {sortOverload(options).map((option) => (
        <li key={option.name} className="overload__line">
          <span className="overload__name">{abbreviateOverload(option.name)}</span>
          <span className="overload__value">{option.value}%</span>
        </li>
      ))}
    </ul>
  )
}

/** One unit's overload drawn the way the game's own equipment screen draws it:
 * the four pieces squared up - head and torso above, arm and leg below - each
 * listing its option rows in order, each row emphasised by the level it rolled
 * at rather than by how large its percent happens to be.
 *
 * The summed view above answers "what does this unit have"; this one answers
 * "which piece should I reroll", which is a question about single rolls and
 * cannot be read off a total at all.
 *
 * Empty rows are drawn as a dash rather than skipped. Skipping them would give
 * each piece a height set by how much it rolled, and the square the player
 * reads the game's screen as would stop lining up. */
export function OverloadGearGrid({ pieces }: { pieces: GearPiece[] }) {
  return (
    <ul className="gear" aria-label="장비별 오버로드">
      {pieces.map(({ slot, rolls }) => (
        <li key={slot} className="gear__piece">
          <h4 className="gear__slot">{GEAR_SLOT_LABEL[slot]}</h4>
          <ul className="gear__rolls">
            {gearRows(rolls).map((roll, row) => (
              <li
                key={row}
                className="gear__roll"
                // Absent rather than empty when a roll earns no emphasis, so
                // the stylesheet can key on the attribute existing at all.
                data-tier={rollTier(roll?.level) ?? undefined}
              >
                {roll ? (
                  <>
                    <span className="gear__name">{formatOverloadName(roll.name)}</span>
                    <span className="gear__value">{roll.value}%</span>
                  </>
                ) : (
                  <span className="gear__empty">—</span>
                )}
              </li>
            ))}
          </ul>
        </li>
      ))}
    </ul>
  )
}
