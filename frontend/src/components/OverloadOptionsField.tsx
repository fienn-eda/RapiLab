// The aggregated overload stat lines (name + value), summed across the 4 gear
// pieces. The list may be empty; rows can be added and removed freely.

import {
  makeOverloadRow,
  type NikkeDraftErrors,
  type OverloadRow,
} from '../types/nikkeDraft'
import { NumberField } from './fields/NumberField'
import { TextField } from './fields/TextField'

interface OverloadOptionsFieldProps {
  rows: OverloadRow[]
  errors?: NikkeDraftErrors['overload_options']
  onChange: (rows: OverloadRow[]) => void
}

export function OverloadOptionsField({
  rows,
  errors,
  onChange,
}: OverloadOptionsFieldProps) {
  const updateRow = (id: string, patch: Partial<OverloadRow>) =>
    onChange(rows.map((row) => (row.id === id ? { ...row, ...patch } : row)))

  const removeRow = (id: string) =>
    onChange(rows.filter((row) => row.id !== id))

  return (
    <fieldset className="group">
      <legend className="group__legend">
        Overload options
        <span className="group__hint"> aggregated across 4 gear pieces</span>
      </legend>
      {rows.length === 0 && (
        <p className="group__empty">No overload lines added.</p>
      )}
      {rows.map((row) => (
        <div key={row.id} className="field-row field-row--overload">
          <TextField
            label="Stat"
            value={row.name}
            placeholder="e.g. ATK"
            error={errors?.[row.id]?.name}
            onChange={(name) => updateRow(row.id, { name })}
          />
          <NumberField
            label="Value"
            value={row.value}
            error={errors?.[row.id]?.value}
            onChange={(value) => updateRow(row.id, { value })}
          />
          <button
            type="button"
            className="btn btn--icon"
            aria-label="Remove overload line"
            onClick={() => removeRow(row.id)}
          >
            ✕
          </button>
        </div>
      ))}
      <button
        type="button"
        className="btn btn--ghost"
        onClick={() => onChange([...rows, makeOverloadRow()])}
      >
        + Add overload line
      </button>
    </fieldset>
  )
}
