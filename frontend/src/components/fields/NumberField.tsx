// A labeled numeric input with inline validation error. Value is a string so
// the field can be empty/partial while typing; parsing happens in validation.

import { useId } from 'react'

interface NumberFieldProps {
  label: string
  value: string
  onChange: (value: string) => void
  error?: string
  min?: number
  max?: number
  step?: number
  hint?: string
}

export function NumberField({
  label,
  value,
  onChange,
  error,
  min,
  max,
  step,
  hint,
}: NumberFieldProps) {
  const id = useId()
  const errorId = `${id}-error`
  return (
    <div className={`field${error ? ' field--invalid' : ''}`}>
      <label className="field__label" htmlFor={id}>
        {label}
        {hint && <span className="field__hint"> {hint}</span>}
      </label>
      <input
        id={id}
        className="field__input"
        type="number"
        inputMode="decimal"
        value={value}
        min={min}
        max={max}
        step={step}
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? errorId : undefined}
        onChange={(event) => onChange(event.target.value)}
      />
      {error && (
        <span id={errorId} className="field__error" role="alert">
          {error}
        </span>
      )}
    </div>
  )
}
