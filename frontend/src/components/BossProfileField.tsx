// The boss profile inputs for POST /api/recommend: element, core hittable,
// enemy DEF, fight duration, part destructibility, and effective range band.
// Mirrors BossProfile in src/types/recommend.ts.

import { useId, useState } from 'react'
import { bossElementFor } from '../lib/elementAdvantage'
import { WEAKNESS_ICON } from '../lib/elementIcon'
import { elementLabel } from '../lib/elementName'
import { makeDefaultBossProfileDraft } from '../types/bossProfileDraft'
import type { BossProfileDraft, BossProfileDraftErrors } from '../types/bossProfileDraft'
import type { RaidRotation, RotationBoss } from '../types/raidRotation'
import { BOSS_RANGE_BANDS, type BossRangeBand } from '../types/recommend'
import type { NikkeElement } from '../types/supportedUnit'
import { NumberField } from './fields/NumberField'
import { RaidRotationPicker } from './RaidRotationPicker'
import { HelpTip } from './HelpTip'
import { HelpText } from './HelpText'
import { HELP } from '../lib/helpText'

// What each band pays, named by the weapons rather than by a distance the
// player cannot see. A Rocket Launcher is paid by none of them, which is why
// no option mentions one.
const RANGE_BAND_LABEL: Record<Exclude<BossRangeBand, null>, string> = {
  near: '근거리 — SG · SMG',
  mid: '중거리 — AR · MG',
  far: '원거리 — SR',
}

// 화면에 그리는 것은 보스 본인 속성이 아니라 그 보스를 이기는 속성이다 — 플레이어가
// 편성할 때 보는 값이 그쪽이기 때문.
const WEAKNESS_CHOICES: NikkeElement[] = ['Fire', 'Water', 'Wind', 'Iron', 'Electric']

/** 접힌 채로도 무슨 값으로 계산되는지 보이게 하는 요약. 편집 중이라 비어 있는
 * 칸은 숫자 대신 —로 둔다. */
const foldedSummary = (draft: BossProfileDraft): string => {
  const def = draft.enemy_def.trim()
  const seconds = draft.fight_duration.trim()
  const defText = def === '' ? '—' : Number(def).toLocaleString()
  const secondsText = seconds === '' ? '—' : seconds
  return `방어력 ${defText} · ${secondsText}초`
}

interface BossProfileFieldProps {
  value: BossProfileDraft
  errors?: BossProfileDraftErrors
  onChange: (value: BossProfileDraft) => void
  /** 속성저지 필수를 그릴지. 유니온레이드 탭은 탐색이 없어 제약이 걸 곳이 없으므로
   * 항목 자체를 감춘다 - 켤 수는 있는데 아무 일도 안 일어나는 것이 더 나쁘다. */
  showElementalInterrupt?: boolean
  /** 이번 회차 보스 목록. 없으면 카드 피커를 그리지 않는다. */
  rotation?: RaidRotation | null
  /** 카드를 골랐을 때 방어력이 되돌아갈 값. 솔로 보스와 유니온 보스는 방어력이
   *  달라 공유 기본값 하나로는 한쪽이 틀린 값으로 계산된다 —
   *  makeDefaultBossProfileDraft가 인자를 받는 것과 같은 이유다. */
  defaultEnemyDef?: string
}

export function BossProfileField({
  value,
  errors,
  onChange,
  showElementalInterrupt = true,
  rotation = null,
  defaultEnemyDef = '0',
}: BossProfileFieldProps) {
  const elementId = useId()
  const rangeBandId = useId()

  // 어느 보스 카드를 눌렀는지. 이름으로 들고 있는 이유는 같은 약점을 가진 보스가
  // 한 회차에 둘 나올 수 있어서다 — 속성만으로는 어느 쪽인지 못 가른다.
  const [pickedName, setPickedName] = useState<string | null>(null)

  // 카드는 「이 보스로 계산 중」이라고 말한다. 그래서 약점이 그 보스와 달라진
  // 순간(사용자가 아이콘을 직접 눌렀을 때) 체크를 놓아야 한다.
  const picked = rotation?.bosses.find((boss) => boss.name === pickedName) ?? null
  const selectedName =
    picked && picked.weakness !== null && bossElementFor(picked.weakness) === value.element
      ? picked.name
      : null

  // 공지가 명시한 약점만 얹고 나머지는 전부 기본값으로 돌린다. 직전 보스의 설정이
  // 남으면 화면에는 새 보스 이름이 적혀 있는데 계산은 옛 보스 가정으로 돈다.
  const pickRotationBoss = (boss: RotationBoss) => {
    setPickedName(boss.name)
    onChange({
      ...makeDefaultBossProfileDraft(defaultEnemyDef),
      element: boss.weakness === null ? null : bossElementFor(boss.weakness),
    })
  }

  return (
    <fieldset className="group">
      <legend className="group__legend">보스 설정</legend>

      {rotation && (
        <RaidRotationPicker
          rotation={rotation}
          selectedName={selectedName}
          onPick={pickRotationBoss}
        />
      )}

      <div className="field">
        <span className="field__label" id={`${elementId}-label`}>
          보스 약점 속성
        </span>
        {/* 진짜 라디오를 시각적으로만 숨긴다. div/button으로 만들면 화살표 이동과
            화면 낭독기의 그룹 읽기를 둘 다 잃는다. */}
        <div className="element-picker" role="radiogroup" aria-labelledby={`${elementId}-label`}>
          {WEAKNESS_CHOICES.map((weakness) => {
            const bossElement = bossElementFor(weakness)
            return (
              <label
                key={weakness}
                className="element-picker__option"
                data-element={weakness}
              >
                <input
                  type="radio"
                  className="visually-hidden"
                  name={elementId}
                  checked={value.element === bossElement}
                  onChange={() => onChange({ ...value, element: bossElement })}
                />
                <img className="element-picker__icon" src={WEAKNESS_ICON[weakness]} alt="" />
                <span className="element-picker__name">{elementLabel(weakness)}</span>
              </label>
            )
          })}
          <label className="element-picker__option element-picker__option--none">
            <input
              type="radio"
              className="visually-hidden"
              name={elementId}
              checked={value.element === null}
              onChange={() => onChange({ ...value, element: null })}
            />
            <span className="element-picker__name">약점 없음</span>
          </label>
        </div>
      </div>

      <div className="field">
        <span className="field__label-row">
          <label className="field__label" htmlFor={rangeBandId}>
            보스 적정거리
          </label>
          <HelpTip label="보스 적정거리">
            <HelpText>{HELP.boss.rangeBand}</HelpText>
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
            onChange={(event) =>
              onChange({
                ...value,
                core_hittable: event.target.checked,
                // 코어를 못 때리면 뚫고 지나갈 것도 없다. 엔진도 두 값을 같이 읽지만,
                // 폼에서 모순 상태를 아예 만들지 않는 편이 화면이 정직하다.
                pierce_hits_body_behind_core:
                  event.target.checked && value.pierce_hits_body_behind_core,
              })
            }
          />
          코어 피격 가능
        </label>
        <HelpTip label="코어 피격 가능">
          <HelpText>{HELP.boss.coreHittable}</HelpText>
        </HelpTip>
      </div>

      <div className="checkbox-row">
        <label className="checkbox">
          <input
            type="checkbox"
            checked={value.pierce_hits_body_behind_core}
            onChange={(event) =>
              onChange({
                ...value,
                pierce_hits_body_behind_core: event.target.checked,
                core_hittable: event.target.checked || value.core_hittable,
              })
            }
          />
          상시 코어 2관통
        </label>
        <HelpTip label="상시 코어 2관통">
          <HelpText>{HELP.boss.corePierce}</HelpText>
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
          <HelpText>{HELP.boss.partDestructible}</HelpText>
        </HelpTip>
      </div>

      {showElementalInterrupt && (
        <div className="checkbox-row">
          <label className="checkbox">
            <input
              type="checkbox"
              checked={value.elemental_interrupt_required}
              onChange={(event) =>
                onChange({ ...value, elemental_interrupt_required: event.target.checked })
              }
            />
            속성저지 필수
          </label>
          <HelpTip label="속성저지 필수">
            <HelpText>{HELP.boss.elementalInterrupt}</HelpText>
          </HelpTip>
        </div>
      )}

      {/* 거의 바꾸지 않는 두 값이라 접어 둔다. 오류가 있을 때는 강제로 펼쳐
          제출을 막는 이유가 접힌 상자 안에 숨지 않게 한다. */}
      <details
        className="group__details boss-profile__folded"
        open={errors?.enemy_def || errors?.fight_duration ? true : undefined}
      >
        <summary className="group__hint">기타 설정 — {foldedSummary(value)}</summary>
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
      </details>
    </fieldset>
  )
}
