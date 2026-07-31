// The boss profile inputs for POST /api/recommend: element, core hittable,
// enemy DEF, fight duration, part destructibility, and effective range band.
// Mirrors BossProfile in src/types/recommend.ts.

import { useId } from 'react'
import { elementLabel } from '../lib/elementName'
import type { BossProfileDraft, BossProfileDraftErrors } from '../types/bossProfileDraft'
import {
  BOSS_ELEMENTS,
  BOSS_RANGE_BANDS,
  type BossElement,
  type BossRangeBand,
} from '../types/recommend'
import { NumberField } from './fields/NumberField'
import { HelpTip } from './HelpTip'

// What each band pays, named by the weapons rather than by a distance the
// player cannot see. A Rocket Launcher is paid by none of them, which is why
// no option mentions one.
const RANGE_BAND_LABEL: Record<Exclude<BossRangeBand, null>, string> = {
  near: '근거리 — SG · SMG',
  mid: '중거리 — AR · MG',
  far: '원거리 — SR',
}

interface BossProfileFieldProps {
  value: BossProfileDraft
  errors?: BossProfileDraftErrors
  onChange: (value: BossProfileDraft) => void
}

export function BossProfileField({ value, errors, onChange }: BossProfileFieldProps) {
  const elementId = useId()
  const rangeBandId = useId()

  return (
    <fieldset className="group">
      <legend className="group__legend">보스 설정</legend>

      <div className="field">
        <label className="field__label" htmlFor={elementId}>
          보스 속성
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

      <div className="field">
        <span className="field__label-row">
          <label className="field__label" htmlFor={rangeBandId}>
            보스 적정거리
          </label>
          <HelpTip label="보스 적정거리">
            적정거리 안에서 쏘는 무기는 평타 대미지가 올라가요. 거리는 스테이지가
            정하는 값이라 유닛이 아니라 보스에 붙어요. 런처(RL)는 어느 거리에서도
            받지 않아요.
          </HelpTip>
        </span>
        <select
          id={rangeBandId}
          className="field__input"
          value={value.effective_range_band ?? ''}
          onChange={(event) =>
            onChange({
              ...value,
              effective_range_band: (event.target.value || null) as BossRangeBand,
            })
          }
        >
          <option value="">모름 (보너스 없음)</option>
          {BOSS_RANGE_BANDS.map((band) => (
            <option key={band} value={band}>
              {RANGE_BAND_LABEL[band]}
            </option>
          ))}
        </select>
      </div>

      {/* 설명 버튼이 <label> 밖에 있는 이유: 라벨 안에서는 아무 클릭이나
          체크박스를 토글하므로, 설명을 열려던 클릭이 보스 설정을 바꾼다. */}
      <div className="checkbox-row">
        <label className="checkbox">
          <input
            type="checkbox"
            checked={value.core_hittable}
            onChange={(event) => onChange({ ...value, core_hittable: event.target.checked })}
          />
          코어 피격 가능
        </label>
        <HelpTip label="코어 피격 가능">
          체크하면 <strong>모든 평타가 코어에 명중한다고 가정</strong>해요. 실제
          전투에서는 조준과 부위 타격 때문에 100%가 나오지 않으므로, 이 추천은
          상한 기준이고 평타 비중이 큰 유닛이 실제보다 높게 평가될 수 있어요.
        </HelpTip>
      </div>

      <div className="checkbox-row">
        <label className="checkbox">
          <input
            type="checkbox"
            checked={value.part_destructible}
            onChange={(event) =>
              onChange({ ...value, part_destructible: event.target.checked })
            }
          />
          부위파괴 기믹
        </label>
        <HelpTip label="부위파괴 기믹">
          부위파괴에 의존하는 유닛(예: 아크레인저 블랙)의 최대 잠재력 모델을
          선택해요. 체크 해제 시 하한 모델을 사용해요.
        </HelpTip>
      </div>

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
