import { describe, expect, it } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import { MirandaTargets } from './MirandaTargets'
import type { MirandaTargetsResult } from '../types/mirandaTargets'

const NAMES: Record<string, string> = {
  'miranda-signature': '미란다', crown: '크라운', 'ada-wong': '에이다 웡',
  cinderella: '신데렐라', isabel: '이사벨', miranda: '미란다',
}
const nameFor = (slug: string) => NAMES[slug] ?? slug

const base: MirandaTargetsResult = {
  seats: [
    { slug: 'miranda-signature', burstTier: 1 },
    { slug: 'crown', burstTier: 2 },
    { slug: 'ada-wong', burstTier: 3 },
    { slug: 'cinderella', burstTier: 3 },
    { slug: 'isabel', burstTier: 3 },
  ],
  mirandaSlug: 'miranda-signature',
  hasFavoriteItem: true,
  cycles: [
    { index: 1, poweringUp: ['ada-wong', 'crown'], wakeUpCritRate: ['ada-wong'] },
    { index: 2, poweringUp: ['ada-wong', 'crown'], wakeUpCritRate: ['ada-wong'] },
  ],
  overloadThresholds: [],
  overloadAtkCapPercent: 58.52,
  notes: [],
  engineVersion: 'abc',
}

const renderResult = (result: MirandaTargetsResult) =>
  render(<MirandaTargets result={result} portraitFor={() => null} nameFor={nameFor} />)

const row = (name: string) => screen.getByRole('listitem', { name })

describe('MirandaTargets', () => {
  it('gives the wake-up recipient both badges and the powering-up-only unit the silver pair', () => {
    renderResult(base)
    expect(within(row('에이다 웡')).getByText('크확')).toBeInTheDocument()
    expect(within(row('에이다 웡')).getByText('공격력')).toBeInTheDocument()
    expect(within(row('크라운')).queryByText('크확')).not.toBeInTheDocument()
    expect(within(row('크라운')).getByText('크댐')).toBeInTheDocument()
    expect(within(row('이사벨')).queryByText('공격력')).not.toBeInTheDocument()
  })

  it('marks a badge that only holds in some cycles with n/T', () => {
    renderResult({
      ...base,
      cycles: [
        { index: 1, poweringUp: ['ada-wong', 'crown'], wakeUpCritRate: ['ada-wong'] },
        { index: 2, poweringUp: ['ada-wong', 'isabel'], wakeUpCritRate: ['ada-wong'] },
      ],
    })
    expect(within(row('크라운')).getByText('1/2')).toBeInTheDocument()
    expect(within(row('에이다 웡')).queryByText('1/2')).not.toBeInTheDocument()
  })

  it('names the cycles where powering-up changed hands', () => {
    renderResult({
      ...base,
      cycles: [
        { index: 1, poweringUp: ['ada-wong', 'crown'], wakeUpCritRate: ['ada-wong'] },
        { index: 2, poweringUp: ['ada-wong', 'isabel'], wakeUpCritRate: ['ada-wong'] },
      ],
    })
    expect(screen.getByText(/2사이클/)).toBeInTheDocument()
  })

  it('says outright when Miranda could not burst every cycle', () => {
    renderResult({
      ...base,
      cycles: [
        { index: 1, poweringUp: ['ada-wong', 'crown'], wakeUpCritRate: ['ada-wong'] },
        { index: 2, poweringUp: [], wakeUpCritRate: ['ada-wong'] },
      ],
    })
    expect(screen.getByText(/미란다는 2사이클 중 1번만 버스트해요/)).toBeInTheDocument()
  })

  it('states what a unit needs, what it can lose, and when nothing is enough', () => {
    renderResult({
      ...base,
      overloadThresholds: [
        { slug: 'crown', currentPercent: 8, kind: 'gain', thresholdPercent: 11.47 },
        { slug: 'ada-wong', currentPercent: 12, kind: 'keep', thresholdPercent: 9.9 },
        { slug: 'cinderella', currentPercent: 0, kind: 'keep', thresholdPercent: 0 },
        { slug: 'isabel', currentPercent: 0, kind: 'gain', thresholdPercent: null },
      ],
    })
    expect(screen.getByText(/8\.00% → 11\.47% 필요 \(\+3\.47%p\)/)).toBeInTheDocument()
    expect(screen.getByText(/9\.90% 밑으로 내려가면 놓쳐요/)).toBeInTheDocument()
    expect(screen.getByText(/오버로드 공격력이 없어도 유지돼요/)).toBeInTheDocument()
    expect(screen.getByText(/상한\(58\.52%\)까지 올려도 못 받아요/)).toBeInTheDocument()
  })

  it('shows every note the backend sent', () => {
    renderResult({ ...base, notes: ['무속성 보스·180초 전투를 가정해 계산했어요.'] })
    expect(screen.getByText(/무속성 보스/)).toBeInTheDocument()
  })
})
