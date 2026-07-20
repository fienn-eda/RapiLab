// Editor for a single Nikke's investment data. Owns the layout of one
// UserNikkeState draft and surfaces validation errors once the card is touched.

import { useMemo, useState } from 'react'
import {
  validateDraft,
  type NikkeDraft,
  type OverloadRow,
} from '../types/nikkeDraft'
import { CONSTRAINTS } from '../types/userNikkeState'
import { NumberField } from './fields/NumberField'
import { TextField } from './fields/TextField'
import { SkillLevelsField } from './SkillLevelsField'
import { OverloadOptionsField } from './OverloadOptionsField'
import { InvestmentBadge } from './InvestmentBadge'

interface NikkeCardProps {
  draft: NikkeDraft
  index: number
  onChange: (draft: NikkeDraft) => void
  onRemove: () => void
}

const countIssues = (errors: object): number =>
  Object.values(errors).reduce((total, value) => {
    if (value == null) return total
    if (typeof value === 'string') return total + 1
    return total + countIssues(value as object)
  }, 0)

export function NikkeCard({ draft, index, onChange, onRemove }: NikkeCardProps) {
  const [touched, setTouched] = useState(false)
  const { errors, value } = useMemo(() => validateDraft(draft), [draft])

  const shownErrors = touched ? errors : {}
  const issues = countIssues(errors)
  const title = draft.character_slug.trim() || `Nikke ${index + 1}`

  return (
    <section
      className="card"
      onBlur={() => setTouched(true)}
      aria-label={`Investment data for ${title}`}
    >
      <header className="card__header">
        <h2 className="card__title">{title}</h2>
        <InvestmentBadge grade={draft.grade} core={draft.core} />
        <div className="card__header-right">
          {value ? (
            <span className="pill pill--ok">Ready</span>
          ) : touched ? (
            <span className="pill pill--warn">
              {issues} {issues === 1 ? 'issue' : 'issues'}
            </span>
          ) : (
            <span className="pill pill--muted">Draft</span>
          )}
          <button
            type="button"
            className="btn btn--icon"
            aria-label={`Remove ${title}`}
            onClick={onRemove}
          >
            ✕
          </button>
        </div>
      </header>

      <TextField
        label="Character slug"
        hint="identifies the Nikke"
        value={draft.character_slug}
        placeholder="e.g. red-hood"
        error={shownErrors.character_slug}
        onChange={(character_slug) => onChange({ ...draft, character_slug })}
      />

      <div className="field-row">
        <NumberField
          label="Level"
          value={draft.level}
          error={shownErrors.level}
          min={CONSTRAINTS.level.min}
          step={1}
          onChange={(level) => onChange({ ...draft, level })}
        />
      </div>

      <div className="field-row field-row--thirds">
        <NumberField
          label="HP"
          value={draft.hp}
          error={shownErrors.hp}
          min={CONSTRAINTS.hp.min}
          onChange={(hp) => onChange({ ...draft, hp })}
        />
        <NumberField
          label="ATK"
          value={draft.atk}
          error={shownErrors.atk}
          min={CONSTRAINTS.atk.min}
          onChange={(atk) => onChange({ ...draft, atk })}
        />
        <NumberField
          label="DEF"
          value={draft.def_}
          error={shownErrors.def_}
          min={CONSTRAINTS.def_.min}
          onChange={(def_) => onChange({ ...draft, def_ })}
        />
      </div>

      <SkillLevelsField
        value={draft.skill_levels}
        errors={shownErrors.skill_levels}
        onChange={(skill_levels) => onChange({ ...draft, skill_levels })}
      />

      <OverloadOptionsField
        rows={draft.overload_options}
        errors={shownErrors.overload_options}
        onChange={(overload_options: OverloadRow[]) =>
          onChange({ ...draft, overload_options })
        }
      />
    </section>
  )
}
