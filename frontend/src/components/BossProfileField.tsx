// The boss profile inputs for POST /api/recommend: element, core hittable,
// enemy DEF, fight duration, part destructibility, and effective range band.
// Mirrors BossProfile in src/types/recommend.ts.

import { useId, useState } from 'react'
import { bossHeading } from '../lib/bossLabel'
import {
  REFERENCE_WEAPONS,
  coreDiameterFromMeasurement,
  coreHitRateGroups,
} from '../lib/coreHitRate'
import { bossElementFor } from '../lib/elementAdvantage'
import { WEAKNESS_ICON } from '../lib/elementIcon'
import { elementLabel } from '../lib/elementName'
import { makeDefaultBossProfileDraft } from '../types/bossProfileDraft'
import type { BossProfileDraft, BossProfileDraftErrors } from '../types/bossProfileDraft'
import type { RaidRotation, RotationBoss } from '../types/raidRotation'
import { BOSS_RANGE_BANDS, type BossRangeBand } from '../types/recommend'
import type { NikkeElement } from '../types/supportedUnit'
import { NumberField } from './fields/NumberField'
import { ToggleChip } from './fields/ToggleChip'
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
 * 칸은 숫자 대신 —로 둔다.
 *
 * 코어 지름은 코어를 때릴 수 있는 보스에서만 붙는다 — 그 밖에는 엔진이 값을
 * 무시하므로 요약에 적으면 안 쓰이는 숫자를 계산 근거처럼 보이게 한다. */
const foldedSummary = (draft: BossProfileDraft): string => {
  const def = draft.enemy_def.trim()
  const seconds = draft.fight_duration.trim()
  const core = draft.core_diameter_px.trim()
  const defText = def === '' ? '—' : Number(def).toLocaleString()
  const secondsText = seconds === '' ? '—' : seconds
  const parts = [`방어력 ${defText}`, `${secondsText}초`]
  if (draft.core_hittable) parts.push(`코어 ${core === '' ? '—' : core}`)
  // 부위파괴만 켜고 시각을 안 적은 상태는 「언제 깨지는지 모른다」이고 그때는
  // 옛 근사로 도는 것이 맞다 - 「파괴 —」를 적으면 값이 있는데 못 읽은 것처럼 보인다.
  // 체크가 꺼져 있으면 엔진이 시각을 무시하므로 요약에서도 빠진다: 칸은 사라졌는데
  // 요약에는 남으면 지울 수 없는 값이 계산에 쓰이는 것처럼 보인다.
  const destructionTimes = draft.part_destruction_times.trim()
  if (draft.part_destructible && destructionTimes !== '') {
    parts.push(`파괴 ${destructionTimes}`)
  }
  return parts.join(' · ')
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

/** 화면에서 잰 두 픽셀을 엔진 단위로 옮겨 코어 지름 칸에 넣어 주는 계산기.
 *
 * 칸이 받는 단위(엔진)와 사람이 잴 수 있는 단위(화면 px)가 달라서, 이게 없으면
 * 잰 숫자를 그대로 치는 순간 조용히 틀린다. 해상도를 묻지 않는 이유는
 * **화면 px을 엔진 단위로 옮기는 일반형이 없기 때문**이다 — 비율만 쓴다
 * (`lib/coreHitRate.ts`, `docs/measurements/accuracy-circle-and-core-px.md`).
 *
 * 입력은 draft에 남기지 않는다. 잰 값을 재료로 엔진 값을 만들고 나면 할 일이
 * 끝나므로, 저장했다가 낡을 것이 없다. */
function CoreMeasurementCalculator({ onFill }: { onFill: (engineValue: string) => void }) {
  const [corePx, setCorePx] = useState('')
  const [reticlePx, setReticlePx] = useState('')
  const [weapon, setWeapon] = useState<(typeof REFERENCE_WEAPONS)[number]>(
    REFERENCE_WEAPONS[0],
  )
  const weaponId = useId()

  const engineValue = coreDiameterFromMeasurement(
    Number(corePx.trim() === '' ? Number.NaN : corePx),
    Number(reticlePx.trim() === '' ? Number.NaN : reticlePx),
    weapon,
  )
  // 판독이 ±1px이면 결과는 수 %가 흔들린다. 소수점을 더 붙이면 없는 정밀도다.
  const rounded = engineValue === null ? null : engineValue.toFixed(2)

  return (
    <div className="core-measure">
      <span className="field__label-row">
        <span className="field__label">화면에서 재서 넣기</span>
        <HelpTip label="화면에서 재서 넣기">
          <HelpText>{HELP.boss.coreMeasure}</HelpText>
        </HelpTip>
      </span>
      <div className="field-row field-row--pair">
        <NumberField label="코어 (px)" value={corePx} min={0} onChange={setCorePx} />
        <NumberField label="조준원 (px)" value={reticlePx} min={0} onChange={setReticlePx} />
      </div>
      <div className="core-measure__row">
        <label className="field__label" htmlFor={weaponId}>탄착군 측정한 무기</label>
        <select
          id={weaponId}
          className="field__input"
          value={weapon}
          onChange={(event) =>
            setWeapon(event.target.value as (typeof REFERENCE_WEAPONS)[number])
          }
        >
          {REFERENCE_WEAPONS.map((w) => (
            <option key={w} value={w}>
              {w}
            </option>
          ))}
        </select>
        <button
          type="button"
          className="btn"
          disabled={rounded === null}
          onClick={() => rounded !== null && onFill(rounded)}
        >
          코어 지름 넣기
        </button>
      </div>
      {rounded !== null && (
        <p className="field__readout group__hint" data-testid="core-measurement-result">
          = 엔진 단위 <strong>{rounded}</strong>
        </p>
      )}
    </div>
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
  /** 접힌 채로 시작할지. 솔로 탭은 보스를 시즌마다 한 번 정하고 나면 거의 안
   * 건드리므로 접어 둔다. 유니온은 전투마다 다른 보스를 고르므로 펼친 채로
   * 둔다 - 접으면 실행할 때마다 전투 수만큼 펼쳐야 한다. */
  defaultCollapsed?: boolean
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
  defaultCollapsed = false,
}: BossProfileFieldProps) {
  const elementId = useId()
  const rangeBandId = useId()
  const destructionTimesId = useId()
  const [collapsed, setCollapsed] = useState(defaultCollapsed)
  const bodyId = useId()

  // 오류가 접힌 안에 숨으면 화면에는 이유 없이 계산이 안 되는 것처럼 보인다.
  const hasErrors = Object.keys(errors ?? {}).length > 0
  const showBody = !collapsed || hasErrors

  const heading = bossHeading({
    bossName: value.boss_name,
    element: value.element,
    fallback: '보스 설정',
  })

  // 이름은 값에 실려 오므로 파생 가드가 필요 없다 - 속성을 바꾸는 모든 길이
  // 이름을 같이 지운다.
  const selectedName = value.boss_name

  // 공지가 그 단어로 적은 것(약점 · 거리)만 얹고 나머지는 전부 기본값으로 돌린다.
  // 직전 보스의 설정이 남으면 화면에는 새 보스 이름이 적혀 있는데 계산은 옛 보스
  // 가정으로 돈다. 거리를 안 적는 솔로 공지에서는 range_band가 null이라 적정거리도
  // 기본값(모름)으로 남는다.
  const pickRotationBoss = (boss: RotationBoss) => {
    onChange({
      ...makeDefaultBossProfileDraft(defaultEnemyDef),
      element: bossElementFor(boss.weakness),
      boss_name: boss.name,
      effective_range_band: boss.range_band,
      core_diameter_px:
        boss.core_diameter_px === null ? '' : String(boss.core_diameter_px),
      // 코어 지름이 기록돼 있다는 것은 그 보스를 코어로 때릴 수 있다는 뜻이다.
      // 같이 켜지 않으면 엔진이 값을 무시해, 카드를 눌러도 아무 일이 없다.
      core_hittable: boss.core_diameter_px !== null,
      spawns_adds: boss.spawns_adds,
      part_destruction_times: boss.part_destruction_times.join(', '),
      // 같은 규칙: 파괴 시각이 기록돼 있다는 것은 그 보스에 깨지는 파츠가 있다는
      // 뜻이다. 같이 켜지 않으면 불리언만 보는 소비자(아크레인저의 브래킷 ·
      // 디젤의 Mute)가 파츠 없는 보스를 가정한 채로 남는다.
      part_destructible: boss.part_destruction_times.length > 0,
    })
  }

  return (
    // 접히면 legend만 남는다. .group의 세로 여백이 그대로면 머리 아래 빈 상자가
    // 그려지고, 그건 「나와야 할 것이 안 나왔다」로 읽힌다.
    <fieldset className="group">
      {/* 카드가 있을 때만 설명을 붙인다 - 회차 데이터가 없으면 이 탭에 카드 자체가
          없어서, 카드를 고르면 어떻게 된다는 설명이 가리킬 대상이 없다. */}
      <legend className="group__legend">
        <span className="group__legend-row">
          {/* HelpTip을 감싸지 않는다 - 버튼 안의 버튼은 무효다. */}
          <button
            type="button"
            className="group__collapse"
            aria-expanded={showBody}
            aria-controls={bodyId}
            onClick={() => setCollapsed((current) => !current)}
          >
            {heading.iconSrc && (
              <img className="group__collapse-icon" src={heading.iconSrc} alt="" />
            )}
            {heading.text}
          </button>
          {rotation && (
            <HelpTip label="회차 보스">
              <HelpText>{HELP.boss.rotationPicker}</HelpText>
            </HelpTip>
          )}
        </span>
      </legend>

      {showBody && (
        <div id={bodyId} className="boss-profile__body">
          {rotation && (
            <RaidRotationPicker
              rotation={rotation}
              selectedName={selectedName}
              onPick={pickRotationBoss}
            />
          )}

          {/* 회차 보스를 고르면 약점은 그 보스가 정한다 - pickRotationBoss가
              element를 같이 넣는다. 고를 목록이 있는데 손으로 고르는 칸까지 두면
              같은 값을 두 자리에서 정하게 되고, 둘이 어긋나면 어느 쪽이 진실인지
              화면이 답하지 못한다(Fienn, 2026-08-22).

              목록이 없을 때만 남긴다. 그때는 이 칸이 약점을 넣는 유일한 입구라,
              같이 지우면 모든 보스가 「약점 없음」으로 계산된다. */}
          {rotation === null && (
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
                      onChange={() => onChange({ ...value, element: bossElement, boss_name: null })}
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
                  onChange={() => onChange({ ...value, element: null, boss_name: null })}
                />
                <span className="element-picker__name">약점 없음</span>
              </label>
            </div>
          </div>
          )}

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

          <div className="chip-row">
            <ToggleChip
              type="checkbox"
              checked={value.core_hittable}
              onChange={(checked) =>
                onChange({
                  ...value,
                  core_hittable: checked,
                  // 코어를 못 때리면 뚫고 지나갈 것도 없다. 엔진도 두 값을 같이 읽지만,
                  // 폼에서 모순 상태를 아예 만들지 않는 편이 화면이 정직하다.
                  pierce_hits_body_behind_core: checked && value.pierce_hits_body_behind_core,
                  // 코어를 못 때리면 크기도 의미가 없다. 값을 남겨 두면 화면에서
                  // 사라진 칸이 계산에는 남는다.
                  core_diameter_px: checked ? value.core_diameter_px : '',
                })
              }
              help={
                <HelpTip label="코어 타격 가능">
                  <HelpText>{HELP.boss.coreHittable}</HelpText>
                </HelpTip>
              }
            >
              코어 타격 가능
            </ToggleChip>

            <ToggleChip
              type="checkbox"
              checked={value.pierce_hits_body_behind_core}
              onChange={(checked) =>
                onChange({
                  ...value,
                  pierce_hits_body_behind_core: checked,
                  core_hittable: checked || value.core_hittable,
                })
              }
              help={
                <HelpTip label="상시 코어 2관통">
                  <HelpText>{HELP.boss.corePierce}</HelpText>
                </HelpTip>
              }
            >
              상시 코어 2관통
            </ToggleChip>

            <ToggleChip
              type="checkbox"
              checked={value.part_destructible}
              onChange={(checked) => onChange({ ...value, part_destructible: checked })}
              help={
                <HelpTip label="부위파괴 기믹">
                  <HelpText>{HELP.boss.partDestructible}</HelpText>
                </HelpTip>
              }
            >
              부위파괴 기믹
            </ToggleChip>

            <ToggleChip
              type="checkbox"
              checked={value.spawns_adds}
              onChange={(checked) => onChange({ ...value, spawns_adds: checked })}
              help={
                <HelpTip label="잡몹 생성">
                  <HelpText>{HELP.boss.spawnsAdds}</HelpText>
                </HelpTip>
              }
            >
              잡몹 생성
            </ToggleChip>

            {showElementalInterrupt && (
              <ToggleChip
                type="checkbox"
                checked={value.elemental_interrupt_required}
                onChange={(checked) =>
                  onChange({ ...value, elemental_interrupt_required: checked })
                }
                help={
                  <HelpTip label="속성저지 필수">
                    <HelpText>{HELP.boss.elementalInterrupt}</HelpText>
                  </HelpTip>
                }
              >
                속성저지 필수
              </ToggleChip>
            )}
          </div>

          {/* 거의 바꾸지 않는 값들이라 접어 둔다. 오류가 있을 때는 강제로 펼쳐
              제출을 막는 이유가 접힌 상자 안에 숨지 않게 한다. */}
          <details
            className="group__details boss-profile__folded"
            open={
              errors?.enemy_def || errors?.fight_duration || errors?.core_diameter_px
                || errors?.part_destruction_times
                ? true
                : undefined
            }
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
            {/* 코어를 못 때리는 보스에서는 엔진이 이 값을 무시하므로 칸도 없앤다 -
                켤 수는 있는데 아무 일도 안 일어나는 칸을 그리지 않는다. */}
            {value.core_hittable && (
              <>
                <NumberField
                  label="코어 지름"
                  hint="엔진 단위"
                  value={value.core_diameter_px}
                  error={errors?.core_diameter_px}
                  min={0}
                  // 화면에서 잰 길이를 환산한 값이라 눈금이 없다. 아래 계산기가
                  // toFixed(2)로 채우고 백엔드도 float으로 받으므로, 정수만
                  // 받으면 폼이 자기 계산기가 넣은 값을 거부한다.
                  step="any"
                  help={HELP.boss.coreDiameter}
                  onChange={(core_diameter_px) => onChange({ ...value, core_diameter_px })}
                />
                <CoreHitRateReadout coreDiameter={value.core_diameter_px} />
                <CoreMeasurementCalculator
                  onFill={(core_diameter_px) => onChange({ ...value, core_diameter_px })}
                />
              </>
            )}
            {/* 파츠가 안 깨지는 보스에서는 적을 시각이 없으므로 칸도 없앤다 -
                코어 지름과 같은 규칙이다. 시각이 여러 개라 NumberField로는 담기지
                않아 자유 텍스트로 받고, 파싱은 validateBossProfileDraft가 한다. */}
            {value.part_destructible && (
              <div
                className={`field${errors?.part_destruction_times ? ' field--invalid' : ''}`}
              >
                <span className="field__label-row">
                  <label className="field__label" htmlFor={destructionTimesId}>
                    파괴 시각
                    <span className="field__hint"> 초, 쉼표로 구분</span>
                  </label>
                  <HelpTip label="파괴 시각">
                    <HelpText>{HELP.boss.partDestructionTimes}</HelpText>
                  </HelpTip>
                </span>
                <input
                  id={destructionTimesId}
                  className="field__input"
                  type="text"
                  inputMode="numeric"
                  placeholder="예: 1, 61, 126"
                  value={value.part_destruction_times}
                  aria-invalid={errors?.part_destruction_times ? true : undefined}
                  aria-describedby={
                    errors?.part_destruction_times
                      ? `${destructionTimesId}-error`
                      : undefined
                  }
                  onChange={(event) =>
                    onChange({ ...value, part_destruction_times: event.target.value })
                  }
                />
                {errors?.part_destruction_times && (
                  <span
                    id={`${destructionTimesId}-error`}
                    className="field__error"
                    role="alert"
                  >
                    {errors.part_destruction_times}
                  </span>
                )}
              </div>
            )}
          </details>
        </div>
      )}
    </fieldset>
  )
}
