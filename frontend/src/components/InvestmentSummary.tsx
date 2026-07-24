// The two investment facts the player actually reads off a unit: how far its
// skills are levelled, and what its overload rolled. Shared by the roster card
// and the unit palette, which hold the same numbers in different shapes - the
// card renders an editable-form draft (strings), the palette a validated
// UserNikkeState (numbers) - so both accept either.

type Displayable = string | number

interface SkillLevelsProps {
  levels: { skill1: Displayable; skill2: Displayable; burst: Displayable }
  /** 'column' stacks the three beside a portrait; 'row' runs them inline. */
  layout?: 'row' | 'column'
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
        <li key={label} className="skills__pip">
          <span className="skills__label">{label}</span>
          <span className="skills__level">{level === '' ? '—' : level}</span>
        </li>
      ))}
    </ul>
  )
}

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
}

/** Short label for an overload line. An unrecognised name (a new effect type,
 * or another locale) keeps its full text rather than being mangled. */
export const abbreviateOverload = (name: string): string => {
  const stripped = name.replace(/\s*증가$/, '')
  return ABBREVIATIONS[stripped] ?? stripped
}

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
          <span className="overload__name">{abbreviateOverload(option.name)}</span>
          <span className="overload__value">{option.value}%</span>
        </li>
      ))}
    </ul>
  )
}
