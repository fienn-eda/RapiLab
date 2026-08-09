import { afterEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MirandaCalculatorPanel, seatedMirandaSlug } from './MirandaCalculatorPanel'
import { DRAG_SLUG_TYPE } from './UnitPalette'
import type { SupportedUnit } from '../types/supportedUnit'
import type { UserNikkeState } from '../types/userNikkeState'

// UnitPalette fetches its own portrait manifest over the same global `fetch`
// these tests stub for /api/miranda-targets - unmocked, that fetch would be
// the first recorded call and shift every mock.calls index by one.
vi.mock('../hooks/usePortraitManifest', () => ({
  usePortraitManifest: () => ({ portraitFor: () => null }),
}))

const UNITS: SupportedUnit[] = [
  { slug: 'miranda-signature', name: '미란다', burstTier: 1, element: 'Fire' },
  { slug: 'miranda', name: '미란다', burstTier: 1, element: 'Fire' },
  { slug: 'crown', name: '크라운', burstTier: 2, element: 'Iron' },
  { slug: 'ada-wong', name: '에이다 웡', burstTier: 3, element: 'Fire' },
  { slug: 'cinderella', name: '신데렐라', burstTier: 3, element: 'Water' },
  { slug: 'isabel', name: '이사벨', burstTier: 3, element: 'Wind' },
  // 로스터엔 있지만 어느 덱에도 앉히지 않는 여섯째 - 있어야 "roster를 그대로
  // 보냈다"와 "편성한 다섯을 보냈다"가 실제로 갈린다.
  { slug: 'snow-white', name: '백설공주', burstTier: 2, element: 'Electric' },
]

const FULL = ['miranda-signature', 'crown', 'ada-wong', 'cinderella', 'isabel']

const WIRE = {
  seats: FULL.map((slug, i) => ({ slug, burst_tier: i === 0 ? 1 : i === 1 ? 2 : 3 })),
  miranda_slug: 'miranda-signature',
  has_favorite_item: true,
  cycles: [{ index: 1, powering_up: ['ada-wong', 'crown'], wake_up_crit_rate: ['ada-wong'] }],
  overload_thresholds: [],
  overload_atk_cap_percent: 58.52,
  notes: [],
}

const state = (slug: string) =>
  ({
    character_slug: slug,
    atk: 100000,
    skill_levels: { skill1: 1, skill2: 1, burst: 1 },
    overload_options: [],
  }) as unknown as UserNikkeState

const renderPanel = (roster: UserNikkeState[]) =>
  render(
    <MirandaCalculatorPanel
      roster={roster}
      supportedUnits={UNITS}
      portraitFor={() => null}
      nameFor={(slug) => UNITS.find((u) => u.slug === slug)?.name ?? slug}
      burstTiersFor={(slug) => {
        const tier = UNITS.find((u) => u.slug === slug)?.burstTier
        return tier ? [tier] : []
      }}
    />,
  )

/** 팔레트에서 덱으로 끌어다 놓는 것과 같은 경로 - DraftEditor의 덱 컨테이너가
 * 드롭을 받아 자리에 앉힌다. */
const seat = (container: HTMLElement, ...slugs: string[]) => {
  for (const slug of slugs) {
    const deck = container.querySelector('.draft-editor__deck')!
    fireEvent.drop(deck, {
      dataTransfer: { getData: (type: string) => (type === DRAG_SLUG_TYPE ? slug : '') },
    })
  }
}

afterEach(() => vi.unstubAllGlobals())

describe('MirandaCalculatorPanel', () => {
  it('seats Miranda before the player touches anything', () => {
    renderPanel([state('miranda-signature'), state('crown'), state('ada-wong')])
    // 좌석은 하나 차 있고 나머지 넷이 비어 있다.
    expect(screen.getByText('1/5')).toBeInTheDocument()
    // 그리고 그 자리는 비울 수 없다.
    expect(screen.queryByRole('button', { name: /미란다 제거/ })).not.toBeInTheDocument()
  })

  it('prefers the favorite-item build, falls back to the base one, and reports neither', () => {
    // 어느 빌드가 앉는지는 답을 바꾼다(애장품이면 파워업! 2명 + 웨이크업!3,
    // 아니면 파워업! 1명뿐). 화면 글자로는 둘 다 "미란다"라 구분되지 않으므로
    // 고르는 함수를 직접 본다.
    expect(seatedMirandaSlug([state('miranda'), state('crown')])).toBe('miranda')
    expect(seatedMirandaSlug([state('miranda-signature'), state('crown')]))
      .toBe('miranda-signature')
    expect(seatedMirandaSlug([state('crown')])).toBeNull()
    // 둘 다 있을 때가 MIRANDA_SLUGS 순서가 실제로 일을 하는 유일한 경우다 -
    // 로스터에 들어온 순서와 무관하게 애장품 쪽이 이겨야 한다.
    expect(seatedMirandaSlug([state('miranda'), state('miranda-signature')]))
      .toBe('miranda-signature')
    expect(seatedMirandaSlug([state('miranda-signature'), state('miranda')]))
      .toBe('miranda-signature')
  })

  // 설치형 앱(WebView2)에서는 드래그가 dragstart 뒤로 죽어 자리에 앉힐 방법이
  // 없었다. 팔레트의 배치 버튼이 드롭과 같은 결과를 내야 한다.
  it('배치 버튼만으로 빈자리를 채운다', async () => {
    renderPanel([state('miranda-signature'), state('crown'), state('ada-wong')])
    expect(screen.getByText('1/5')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: '크라운 배치' }))
    expect(screen.getByText('2/5')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /크라운 제거/ })).toBeInTheDocument()
    // 앉은 유닛은 더 이상 앉힐 수 없다.
    expect(screen.queryByRole('button', { name: '크라운 배치' })).not.toBeInTheDocument()
  })

  it('asks the player to sync when the roster has no Miranda at all', () => {
    renderPanel([state('crown'), state('ada-wong')])
    expect(screen.getByText(/미란다가 로스터에 없어요/)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /계산/ })).not.toBeInTheDocument()
  })

  it('keeps the run button disabled until all five seats are filled', () => {
    renderPanel([state('miranda-signature'), state('crown'), state('ada-wong')])
    expect(screen.getByRole('button', { name: /계산/ })).toBeDisabled()
  })

  it('submits the five seated slugs once the deck is full', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve(WIRE) })
    vi.stubGlobal('fetch', fetchMock)
    // 로스터엔 편성에 없는 여섯째(백설공주)도 있다 - roster와 편성이 우연히
    // 같은 다섯이면, 구현이 roster를 통째로 보내도 이 테스트가 못 잡는다.
    const { container } = renderPanel([...FULL.map(state), state('snow-white')])
    seat(container, 'crown', 'ada-wong', 'cinderella', 'isabel')
    const run = screen.getByRole('button', { name: '계산' })
    await waitFor(() => expect(run).toBeEnabled())
    await userEvent.click(run)
    await waitFor(() => expect(fetchMock).toHaveBeenCalled())
    const body = JSON.parse(fetchMock.mock.calls[0][1].body as string)
    expect(body.units.sort()).toEqual([...FULL].sort())
  })

  it('shows the backend detail when the request fails', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false, status: 422,
      json: () => Promise.resolve({ detail: '이 다섯으로는 성립하는 버스트 순서가 없어요.' }),
    }))
    const { container } = renderPanel(FULL.map(state))
    seat(container, 'crown', 'ada-wong', 'cinderella', 'isabel')
    await userEvent.click(screen.getByRole('button', { name: '계산' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('버스트 순서')
    // 실패해도 편성은 남는다 - 다시 짜게 만들면 화면이 유저를 벌주는 셈이다.
    expect(screen.getByText('5/5')).toBeInTheDocument()
  })
})
