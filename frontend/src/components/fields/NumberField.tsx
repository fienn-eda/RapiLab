// A labeled numeric input with inline validation error. Value is a string so
// the field can be empty/partial while typing; parsing happens in validation.

import { useId } from 'react'
import { HelpText } from '../HelpText'
import { HelpTip } from '../HelpTip'

interface NumberFieldProps {
  label: string
  value: string
  onChange: (value: string) => void
  error?: string
  min?: number
  max?: number
  /** `'any'`는 소수를 그대로 받는다 - 화면에서 재서 환산한 값처럼 눈금이 없는
   * 양에 쓴다. 생략하면 HTML 기본값이라 정수만 유효해진다. */
  step?: number | 'any'
  hint?: string
  /** Explanation to fold behind a ? on the label line, as the boss form does.
   * `hint` is the unit or a few words that must stay visible; this is the
   * paragraph that only needs reading once. */
  help?: string
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
  help,
}: NumberFieldProps) {
  const id = useId()
  const errorId = `${id}-error`
  const labelText = (
    <label className="field__label" htmlFor={id}>
      {label}
      {hint && <span className="field__hint"> {hint}</span>}
    </label>
  )
  return (
    <div className={`field${error ? ' field--invalid' : ''}`}>
      {help === undefined ? labelText : (
        <span className="field__label-row">
          {labelText}
          <HelpTip label={label}>
            <HelpText>{help}</HelpText>
          </HelpTip>
        </span>
      )}
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
