// The boss profile inputs for POST /api/recommend: element, core hittable,
// enemy DEF, fight duration, and part destructibility. Mirrors BossProfile in
// src/types/recommend.ts.

import { useId } from 'react'
import { elementLabel } from '../lib/elementName'
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
      <legend className="group__legend">보스 설정</legend>

      <div className="field">
        <label className="field__label" htmlFor={elementId}>
          속성
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
          <option value="">무속성</option>
          {BOSS_ELEMENTS.map((element) => (
            <option key={element} value={element}>
              {elementLabel(element)}
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
        코어 피격 가능
      </label>

      <label className="checkbox">
        <input
          type="checkbox"
          checked={value.part_destructible}
          onChange={(event) =>
            onChange({ ...value, part_destructible: event.target.checked })
          }
        />
        부위파괴 기믹
        <span className="group__hint">
          {' '}
          부위파괴에 의존하는 유닛(예: 아크레인저 블랙)의 최대 잠재력 모델을
          선택해요. 체크 해제 시 하한 모델을 사용해요.
        </span>
      </label>

      <div className="field-row field-row--pair">
        <NumberField
          label="적 방어력"
          value={value.enemy_def}
          error={errors?.enemy_def}
          min={0}
          onChange={(enemy_def) => onChange({ ...value, enemy_def })}
        />
        <NumberField
          label="전투 시간"
          hint="초"
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
