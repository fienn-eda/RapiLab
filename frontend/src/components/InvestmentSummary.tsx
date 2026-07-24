// The two investment facts the player actually reads off a unit: how far its
// skills are levelled, and what its overload rolled. Shared by the roster card
// and the unit palette, which hold the same numbers in different shapes - the
// card renders an editable-form draft (strings), the palette a validated
// UserNikkeState (numbers) - so both accept either.

type Displayable = string | number

interface SkillLevelsProps {
  levels: { skill1: Displayable; skill2: Displayable; burst: Displayable }
}

/** Skill levels as three labelled pips. Order matches the game's skill list. */
export function SkillLevels({ levels }: SkillLevelsProps) {
  const pips: [string, Displayable][] = [
    ['S1', levels.skill1],
    ['S2', levels.skill2],
    ['B', levels.burst],
  ]
  return (
    <ul className="skills">
      {pips.map(([label, level]) => (
        <li key={label} className="skills__pip">
          <span className="skills__label">{label}</span>
          <span className="skills__level">{level === '' ? '—' : level}</span>
        </li>
      ))}
    </ul>
  )
}

// Every overload line the backend emits ends in "증가" ("increase"); it is the
// same word on all seven effect types, so it carries no information and only
// costs width in a chip. Anything that ever stops matching keeps its full name.
const shortName = (name: string): string => name.replace(/\s*증가$/, '')

interface OverloadLinesProps {
  options: { name: string; value: Displayable }[]
  /** Copy shown when a unit rolled no overload at all. */
  emptyText?: string
}

/** Overload lines as name/value pairs. Which stat rolled and how high is the
 * whole point - a count would say nothing about whether a unit is worth
 * fielding - so every line is named, never summarised. */
export function OverloadLines({ options, emptyText = 'No overload lines.' }: OverloadLinesProps) {
  if (options.length === 0) return <p className="overload__empty">{emptyText}</p>
  return (
    <ul className="overload">
      {options.map((option) => (
        <li key={option.name} className="overload__line">
          <span className="overload__name">{shortName(option.name)}</span>
          <span className="overload__value">{option.value}%</span>
        </li>
      ))}
    </ul>
  )
}
