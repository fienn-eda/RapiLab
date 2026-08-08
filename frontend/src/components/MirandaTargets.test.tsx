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
  it('gives the wake-up recipient both badges and the powering-up-only unit the silver pair, and Miranda herself none', () => {
    renderResult(base)
    expect(within(row('에이다 웡')).getByText('크확')).toBeInTheDocument()
    expect(within(row('에이다 웡')).getByText('공격력')).toBeInTheDocument()
    expect(within(row('크라운')).queryByText('크확')).not.toBeInTheDocument()
    expect(within(row('크라운')).getByText('크댐')).toBeInTheDocument()
    expect(within(row('이사벨')).queryByText('공격력')).not.toBeInTheDocument()
    // 미란다는 자기 자신의 대상이 될 수 없다 - 뱃지 대신 「시전자」만 뜬다.
    expect(within(row('미란다')).getByText('시전자')).toBeInTheDocument()
    expect(within(row('미란다')).queryByText('크확')).not.toBeInTheDocument()
    expect(within(row('미란다')).queryByText('공격력')).not.toBeInTheDocument()
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
    // 「2사이클」만 검사하면 버스트-일부-실패 캐비엇("미란다는 2사이클 중…")과
    // 안 갈린다 - 이 캐비엇 특유의 문장까지 확인한다.
    expect(screen.getByText(/2사이클에는 파워업!을 받는 니케가 달라요/)).toBeInTheDocument()
  })

  it('does not flag a change when the first cycle is simply a miss and the rest agree', () => {
    renderResult({
      ...base,
      cycles: [
        { index: 1, poweringUp: [], wakeUpCritRate: ['ada-wong'] },
        { index: 2, poweringUp: ['ada-wong', 'crown'], wakeUpCritRate: ['ada-wong'] },
        { index: 3, poweringUp: ['ada-wong', 'crown'], wakeUpCritRate: ['ada-wong'] },
      ],
    })
    // 1사이클은 미란다가 못 쏜 것뿐이지 대상이 「바뀐」게 아니다 - 빈 배열을
    // 기준으로 삼으면 2·3사이클이 (사실은 서로 같은데도) 갈렸다고 오판한다.
    expect(screen.queryByText(/파워업!을 받는 니케가 달라요/)).not.toBeInTheDocument()
  })

  it('does not flag a change when the same two recipients swap rank order', () => {
    renderResult({
      ...base,
      cycles: [
        { index: 1, poweringUp: ['ada-wong', 'crown'], wakeUpCritRate: ['ada-wong'] },
        { index: 2, poweringUp: ['crown', 'ada-wong'], wakeUpCritRate: ['ada-wong'] },
      ],
    })
    // 백엔드는 순위 순으로 대상을 준다 - 자리만 바뀐 것을 「받는 사람이
    // 바뀌었다」로 읽으면 안 된다. 집합으로 비교해야 한다.
    expect(screen.queryByText(/파워업!을 받는 니케가 달라요/)).not.toBeInTheDocument()
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
    expect(within(row('크라운')).getByText(/8\.00% → 11\.47% 필요 \(\+3\.47%p\)/)).toBeInTheDocument()
    expect(within(row('에이다 웡')).getByText(/9\.90% 밑으로 내려가면 놓쳐요/)).toBeInTheDocument()
    expect(within(row('신데렐라')).getByText(/오버로드 공격력이 없어도 유지돼요/)).toBeInTheDocument()
    expect(within(row('이사벨')).getByText(/상한\(58\.52%\)까지 올려도 못 받아요/)).toBeInTheDocument()
  })

  it('shows every note the backend sent', () => {
    renderResult({ ...base, notes: ['무속성 보스·180초 전투를 가정해 계산했어요.'] })
    expect(screen.getByText(/무속성 보스/)).toBeInTheDocument()
  })
})
