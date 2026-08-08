import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { CalculatorPanel } from './CalculatorPanel'
import type { SupportedUnit } from '../types/supportedUnit'
import type { UserNikkeState } from '../types/userNikkeState'

const UNITS: SupportedUnit[] = [
  { slug: 'miranda-signature', name: '미란다', burstTier: 1, element: 'Fire' },
  { slug: 'scarlet-black-shadow', name: '홍련: 흑영', burstTier: 3, element: 'Fire' },
]
const ROSTER = [
  // overload_options and skill_levels are required on UserNikkeState (never
  // absent, even if empty/zero) - UnitPalette reads both unconditionally
  // while rendering the Miranda calculator's palette, which is mounted here
  // even before the sub-tab is selected.
  {
    character_slug: 'miranda-signature',
    atk: 100000,
    overload_options: [],
    skill_levels: { skill1: 1, skill2: 1, burst: 1 },
  },
  {
    character_slug: 'scarlet-black-shadow',
    atk: 100000,
    overload_options: [],
    skill_levels: { skill1: 1, skill2: 1, burst: 1 },
  },
] as unknown as UserNikkeState[]

const renderPanel = () =>
  render(
    <CalculatorPanel
      roster={ROSTER}
      supportedUnits={UNITS}
      portraitFor={() => null}
      nameFor={(slug) => UNITS.find((u) => u.slug === slug)?.name ?? slug}
      burstTiersFor={(slug) => {
        const tier = UNITS.find((u) => u.slug === slug)?.burstTier
        return tier ? [tier] : []
      }}
    />,
  )

describe('CalculatorPanel', () => {
  it('opens on the charge calculator', () => {
    renderPanel()
    expect(screen.getByRole('tab', { name: '차속 + 타수 계산기' })).toHaveAttribute(
      'aria-selected', 'true')
    expect(screen.getByRole('tab', { name: '미란다 계산기' })).toHaveAttribute(
      'aria-selected', 'false')
  })

  it('switches to the Miranda calculator', async () => {
    renderPanel()
    await userEvent.click(screen.getByRole('tab', { name: '미란다 계산기' }))
    expect(screen.getByRole('tab', { name: '미란다 계산기' })).toHaveAttribute(
      'aria-selected', 'true')
    expect(screen.getByRole('heading', { name: '미란다 계산기' })).toBeVisible()
  })

  it('keeps the hidden calculator mounted so its typed input survives a switch', async () => {
    // 언마운트하면 차지 계산기에 입력한 값이 탭을 오갈 때 날아간다.
    renderPanel()
    const field = screen.getByRole('spinbutton', { name: /차지속도 합계/ })
    await userEvent.type(field, '12.5')
    await userEvent.click(screen.getByRole('tab', { name: '미란다 계산기' }))
    await userEvent.click(screen.getByRole('tab', { name: '차속 + 타수 계산기' }))
    expect(screen.getByRole('spinbutton', { name: /차지속도 합계/ })).toHaveValue(12.5)
  })
})
