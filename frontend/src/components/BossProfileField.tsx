// The boss profile inputs for POST /api/recommend: element, core hittable,
// enemy DEF, fight duration, and part destructibility. Mirrors BossProfile in
// src/types/recommend.ts.

import { useId } from 'react'
import type { BossProfileDraft, BossProfileDraftErrors } from '../types/bossProfileDraft'
import { BOSS_ELEMENTS, type BossElement } from '../types/recommend'
import { NumberField } from './fields/NumberField'

interface BossProfileFieldProps {
  value: BossProfileDraft
  errors?: BossProfileDraftErrors
  onChange: (value: BossProfileDraft) => void
}

export function BossProfileField({ value, errors, onChange }: BossProfileFieldProps) {
  const elementId = useId()

  return (
    <fieldset className="group">
      <legend className="group__legend">Boss profile</legend>

      <div className="field">
        <label className="field__label" htmlFor={elementId}>
          Element
        </label>
        <select
          id={elementId}
          className="field__input"
          value={value.element ?? ''}
          onChange={(event) =>
            onChange({
              ...value,
              element: (event.target.value || null) as BossElement,
            })
          }
        >
          <option value="">Non-elemental</option>
          {BOSS_ELEMENTS.map((element) => (
            <option key={element} value={element}>
              {element}
            </option>
          ))}
        </select>
      </div>

      <label className="checkbox">
        <input
          type="checkbox"
          checked={value.core_hittable}
          onChange={(event) => onChange({ ...value, core_hittable: event.target.checked })}
        />
        Core is hittable
      </label>

      <label className="checkbox">
        <input
          type="checkbox"
          checked={value.part_destructible}
          onChange={(event) =>
            onChange({ ...value, part_destructible: event.target.checked })
          }
        />
        Part-destruction gimmick
        <span className="group__hint">
          {' '}
          selects the max-potential model for part-dependent units (e.g. Ark Ranger
          Black); unchecked uses the lower-bound model
        </span>
      </label>

      <div className="field-row field-row--pair">
        <NumberField
          label="Enemy DEF"
          value={value.enemy_def}
          error={errors?.enemy_def}
          min={0}
          onChange={(enemy_def) => onChange({ ...value, enemy_def })}
        />
        <NumberField
          label="Fight duration"
          hint="seconds"
          value={value.fight_duration}
          error={errors?.fight_duration}
          min={0}
          step={1}
          onChange={(fight_duration) => onChange({ ...value, fight_duration })}
        />
      </div>
    </fieldset>
  )
}
