// The optional PVE (combat) cube: a name and a level 1–10, or none at all.
// PVP/arena cubes are out of scope.

import { CONSTRAINTS } from '../types/userNikkeState'
import { NumberField } from './fields/NumberField'
import { TextField } from './fields/TextField'

interface PveCubeValue {
  name: string
  level: string
}

interface PveCubeErrors {
  name?: string
  level?: string
}

interface PveCubeFieldProps {
  hasCube: boolean
  value: PveCubeValue
  errors?: PveCubeErrors
  onToggle: (hasCube: boolean) => void
  onChange: (value: PveCubeValue) => void
}

export function PveCubeField({
  hasCube,
  value,
  errors,
  onToggle,
  onChange,
}: PveCubeFieldProps) {
  return (
    <fieldset className="group">
      <legend className="group__legend">PVE cube</legend>
      <label className="checkbox">
        <input
          type="checkbox"
          checked={hasCube}
          onChange={(event) => onToggle(event.target.checked)}
        />
        A PVE cube is equipped
      </label>
      {hasCube && (
        <div className="field-row field-row--cube">
          <TextField
            label="Cube"
            value={value.name}
            placeholder="e.g. Bastion"
            error={errors?.name}
            onChange={(name) => onChange({ ...value, name })}
          />
          <NumberField
            label="Level"
            value={value.level}
            error={errors?.level}
            min={CONSTRAINTS.cubeLevel.min}
            max={CONSTRAINTS.cubeLevel.max}
            step={1}
            onChange={(level) => onChange({ ...value, level })}
          />
        </div>
      )}
    </fieldset>
  )
}
