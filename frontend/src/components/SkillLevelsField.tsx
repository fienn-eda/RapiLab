// The three skill levels (Skill 1, Skill 2, Burst), each an int 1–10.

import { CONSTRAINTS } from '../types/userNikkeState'
import { NumberField } from './fields/NumberField'

interface SkillLevelsValue {
  skill1: string
  skill2: string
  burst: string
}

interface SkillLevelsErrors {
  skill1?: string
  skill2?: string
  burst?: string
}

interface SkillLevelsFieldProps {
  value: SkillLevelsValue
  errors?: SkillLevelsErrors
  onChange: (value: SkillLevelsValue) => void
}

export function SkillLevelsField({
  value,
  errors,
  onChange,
}: SkillLevelsFieldProps) {
  const { min, max } = CONSTRAINTS.skill
  return (
    <fieldset className="group">
      <legend className="group__legend">Skill levels</legend>
      <div className="field-row field-row--thirds">
        <NumberField
          label="Skill 1"
          value={value.skill1}
          error={errors?.skill1}
          min={min}
          max={max}
          step={1}
          onChange={(skill1) => onChange({ ...value, skill1 })}
        />
        <NumberField
          label="Skill 2"
          value={value.skill2}
          error={errors?.skill2}
          min={min}
          max={max}
          step={1}
          onChange={(skill2) => onChange({ ...value, skill2 })}
        />
        <NumberField
          label="Burst"
          value={value.burst}
          error={errors?.burst}
          min={min}
          max={max}
          step={1}
          onChange={(burst) => onChange({ ...value, burst })}
        />
      </div>
    </fieldset>
  )
}
