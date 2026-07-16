// A labeled text input with inline validation error.

import { useId } from 'react'

interface TextFieldProps {
  label: string
  value: string
  onChange: (value: string) => void
  error?: string
  placeholder?: string
  hint?: string
}

export function TextField({
  label,
  value,
  onChange,
  error,
  placeholder,
  hint,
}: TextFieldProps) {
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
        type="text"
        value={value}
        placeholder={placeholder}
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
