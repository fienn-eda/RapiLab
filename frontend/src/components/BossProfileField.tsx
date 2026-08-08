// The boss profile inputs for POST /api/recommend: element, core hittable,
// enemy DEF, fight duration, part destructibility, and effective range band.
// Mirrors BossProfile in src/types/recommend.ts.

import { useId, useState } from 'react'
import { coreHitRateGroups } from '../lib/coreHitRate'
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

/** 코어 지름 하나가 무기별로 무엇을 뜻하는지 한 줄로. 「33.33」은 사용자에게
 * 아무 의미가 없어서, 값이 틀려도 조용히 덱 순위만 바뀐다 — 결과를 옆에 적어
 * 두면 그 자리에서 이상함이 보인다.
 *
 * 명중 버프가 없는 기준이다. 실제 유닛은 명중이 탄착군을 좁혀 이보다 높게
 * 나오므로, 이 줄은 「이 코어가 큰가 작은가」를 가늠하는 눈금이지 예측이 아니다. */
function CoreHitRateReadout({ coreDiameter }: { coreDiameter: string }) {
  const parsed = Number(coreDiameter.trim())
  // 빈 칸과 유효하지 않은 값에서는 아무것도 적지 않는다 - 편집 중인 반쪽짜리
  // 숫자에 대고 비율을 내면 값이 춤춘다.
  if (coreDiameter.trim() === '' || !Number.isFinite(parsed) || parsed <= 0) return null
  return (
    <p className="field__readout group__hint" data-testid="core-hit-rate-readout">
      무버프 코어 명중 —{' '}
      {coreHitRateGroups(parsed)
        // 확실한 값에 「100.0%」로 소수점을 붙이면 없는 정밀도를 주장하게 된다.
        .map((group) => `${group.label} ${
          group.rate >= 1 ? '100' : (group.rate * 100).toFixed(1)}%`)
        .join(' · ')}
    </p>
  )
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
  defaultEnemyDef,
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
    picked && bossElementFor(picked.weakness) === value.element ? picked.name : null

  // 공지가 그 단어로 적은 것(약점 · 거리)만 얹고 나머지는 전부 기본값으로 돌린다.
  // 직전 보스의 설정이 남으면 화면에는 새 보스 이름이 적혀 있는데 계산은 옛 보스
  // 가정으로 돈다. 거리를 안 적는 솔로 공지에서는 range_band가 null이라 적정거리도
  // 기본값(모름)으로 남는다.
  const pickRotationBoss = (boss: RotationBoss) => {
    setPickedName(boss.name)
    onChange({
      ...makeDefaultBossProfileDraft(defaultEnemyDef),
      element: bossElementFor(boss.weakness),
      effective_range_band: boss.range_band,
      core_diameter_px:
        boss.core_diameter_px === null ? '' : String(boss.core_diameter_px),
      // 코어 지름이 기록돼 있다는 것은 그 보스를 코어로 때릴 수 있다는 뜻이다.
      // 같이 켜지 않으면 엔진이 값을 무시해, 카드를 눌러도 아무 일이 없다.
      core_hittable: boss.core_diameter_px !== null,
    })
  }

  return (
    <fieldset className="group">
      {/* 카드가 있을 때만 설명을 붙인다 - 회차 데이터가 없으면 이 탭에 카드 자체가
          없어서, 카드를 고르면 어떻게 된다는 설명이 가리킬 대상이 없다. */}
      <legend className="group__legend">
        <span className="group__legend-row">
          보스 설정
          {rotation && (
            <HelpTip label="회차 보스">
              <HelpText>{HELP.boss.rotationPicker}</HelpText>
            </HelpTip>
          )}
        </span>
      </legend>

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
                // 코어를 못 때리면 크기도 의미가 없다. 값을 남겨 두면 화면에서
                // 사라진 칸이 계산에는 남는다.
                core_diameter_px: event.target.checked ? value.core_diameter_px : '',
              })
            }
          />
          코어 피격 가능
        </label>
        <HelpTip label="코어 피격 가능">
          <HelpText>{HELP.boss.coreHittable}</HelpText>
        </HelpTip>
      </div>

      {value.core_hittable && (
        <>
          <NumberField
            label="코어 지름"
            hint="엔진 단위"
            value={value.core_diameter_px}
            error={errors?.core_diameter_px}
            min={0}
            help={HELP.boss.coreDiameter}
            onChange={(core_diameter_px) => onChange({ ...value, core_diameter_px })}
          />
          <CoreHitRateReadout coreDiameter={value.core_diameter_px} />
        </>
      )}

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
