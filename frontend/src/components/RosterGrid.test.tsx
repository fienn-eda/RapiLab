import { beforeEach, describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { RosterGrid } from './RosterGrid'
import { makeEmptyDraft, type NikkeDraft } from '../types/nikkeDraft'
import type { SupportedUnit } from '../types/supportedUnit'

const draft = (slug: string): NikkeDraft => ({
  ...makeEmptyDraft(),
  character_slug: slug,
  grade: 3,
  core: 0,
  level: '400',
  hp: '1',
  atk: '1',
  def_: '1',
  skill_levels: { skill1: '10', skill2: '10', burst: '10' },
  overload_options: [],
})

const SUPPORTED: SupportedUnit[] = [
  { slug: 'crown', name: 'Crown', burstTier: 1, element: 'Iron' },
  { slug: 'anne', name: 'Anne', burstTier: 1, element: 'Fire' },
  { slug: 'liter', name: 'Liter', burstTier: 2, element: 'Water' },
  { slug: 'blanc', name: 'Blanc', burstTier: 3, element: 'Wind' },
]

const grid = (slugs: string[], supportedUnits = SUPPORTED) =>
  render(
    <RosterGrid
      drafts={slugs.map(draft)}
      supportedUnits={supportedUnits}
      portraitFor={() => null}
    />,
  )

// 미사용 니케를 정하는 곳이 이 탭이다 - 솔로·유니온은 그 결정을 읽기만 한다.
// 여기 컨트롤이 없어지면 앱 전체에서 니케를 뺄 방법이 사라진다.
describe('RosterGrid 미사용 토글', () => {
  const withToggle = (slugs: string[], excludedSlugs: string[] = []) => {
    const onToggleExclude = vi.fn()
    render(
      <RosterGrid
        drafts={slugs.map(draft)}
        supportedUnits={SUPPORTED}
        portraitFor={() => null}
        excludedSlugs={excludedSlugs}
        onToggleExclude={onToggleExclude}
      />,
    )
    return onToggleExclude
  }

  it('초상화를 누르면 그 니케의 슬러그를 넘긴다', async () => {
    const onToggleExclude = withToggle(['crown', 'liter'])
    await userEvent.click(screen.getByRole('button', { name: 'Crown 사용' }))
    expect(onToggleExclude).toHaveBeenCalledWith('crown')
  })

  it('뺀 니케만 눌리지 않은 상태로 보고한다', () => {
    withToggle(['crown', 'liter'], ['liter'])
    expect(screen.getByRole('button', { name: 'Crown 사용' })).toHaveAttribute(
      'aria-pressed',
      'true',
    )
    expect(screen.getByRole('button', { name: 'Liter 사용' })).toHaveAttribute(
      'aria-pressed',
      'false',
    )
  })

  // 핸들러가 없는 화면에서는 초상화가 그냥 그림이다 - 눌러도 아무 일이 없는
  // 컨트롤을 남기지 않는다.
  it('토글을 다루지 않는 화면에서는 초상화가 버튼이 아니다', () => {
    grid(['crown'])
    expect(screen.queryByRole('button', { name: /사용/ })).not.toBeInTheDocument()
  })
})

describe('RosterGrid', () => {
  it('gives a card to every owned unit the engine supports', () => {
    grid(['crown', 'liter'])
    expect(screen.getByRole('heading', { name: 'Crown' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Liter' })).toBeInTheDocument()
  })

  // More than half a real roster is unsupported. Drawing those as full cards
  // buried the ones that can actually be fielded.
  it('demotes owned units the engine cannot simulate to a collapsed list', () => {
    const { container } = grid(['crown', '2b', 'alice-wonderland-bunny'])

    expect(screen.getByText('엔진 미지원 (2기)')).toBeInTheDocument()
    expect(container.querySelectorAll('.roster-card')).toHaveLength(1)

    const details = container.querySelector('details')!
    expect(details.open).toBe(false)
  })

  it('names an unsupported unit from its slug, since nothing else can', () => {
    grid(['2b', 'alice-wonderland-bunny'])
    expect(screen.getByText('2B')).toBeInTheDocument()
    expect(screen.getByText('Alice Wonderland Bunny')).toBeInTheDocument()
  })

  it('says nothing about unsupported units when every owned unit is supported', () => {
    const { container } = grid(['crown', 'liter'])
    expect(container.querySelector('details')).toBeNull()
  })

  // The list arrives over the network; until it does, nothing is known to be
  // supported and the whole roster lands in the collapsed section rather than
  // vanishing.
  it('keeps every unit reachable while the supported list is still empty', () => {
    grid(['crown', 'liter'], [])
    expect(screen.getByText('엔진 미지원 (2기)')).toBeInTheDocument()
    expect(screen.getByText('Crown')).toBeInTheDocument()
  })

  // A bordered toolbar with nothing to filter reads as a bug, not a feature -
  // this covers both an empty roster and a roster the supported list hasn't
  // loaded for yet.
  it('does not draw the filter toolbar when there is no supported unit to filter', () => {
    grid(['crown'], [])
    expect(screen.queryByLabelText('이름 검색')).not.toBeInTheDocument()
  })

  it('does not draw the filter toolbar for an empty roster', () => {
    grid([])
    expect(screen.queryByLabelText('이름 검색')).not.toBeInTheDocument()
  })

  describe('burst grouping and the filter', () => {
    const overloaded = (slug: string, value: number): NikkeDraft => ({
      ...draft(slug),
      overload_options: [{ id: `${slug}-ol`, name: '공격력 증가', value: String(value) }],
    })

    it('splits the supported units into B1/B2/B3 sections', () => {
      grid(['crown', 'liter', 'blanc'])
      expect(screen.getByRole('heading', { name: 'B1' })).toBeInTheDocument()
      expect(screen.getByRole('heading', { name: 'B2' })).toBeInTheDocument()
      expect(screen.getByRole('heading', { name: 'B3' })).toBeInTheDocument()
    })

    it('draws no heading for a burst tier the player owns nobody in', () => {
      grid(['crown'])
      expect(screen.getByRole('heading', { name: 'B1' })).toBeInTheDocument()
      expect(screen.queryByRole('heading', { name: 'B2' })).not.toBeInTheDocument()
    })

    // Default sort is by name, so the grid reads 가나다순 rather than in
    // whatever order the roster arrived.
    it('orders a group by name before the user chooses anything', () => {
      const { container } = grid(['crown', 'anne'])
      const names = [...container.querySelectorAll('.roster-card__name')].map((n) => n.textContent)
      expect(names).toEqual(['Anne', 'Crown'])
    })

    it('hides the cards an element filter excludes', async () => {
      const user = userEvent.setup()
      const { container } = grid(['crown', 'anne', 'liter'])
      await user.click(screen.getByRole('button', { name: '작열' }))
      expect(container.querySelectorAll('.roster-card')).toHaveLength(1)
      expect(screen.getByRole('heading', { name: 'Anne' })).toBeInTheDocument()
    })

    it('sorts a group by an overload stat within the group only', async () => {
      const user = userEvent.setup()
      render(
        <RosterGrid
          drafts={[overloaded('crown', 10), overloaded('anne', 90), overloaded('liter', 50)]}
          supportedUnits={SUPPORTED}
          portraitFor={() => null}
        />,
      )
      await user.selectOptions(screen.getByLabelText('정렬'), '공')
      await user.selectOptions(screen.getByLabelText('정렬 방향'), 'desc')

      const b1 = screen.getByRole('heading', { name: 'B1' }).closest('section')!
      expect([...b1.querySelectorAll('.roster-card__name')].map((n) => n.textContent)).toEqual([
        'Anne',
        'Crown',
      ])
      // Liter outranks neither - she is in another group entirely.
      const b2 = screen.getByRole('heading', { name: 'B2' }).closest('section')!
      expect([...b2.querySelectorAll('.roster-card__name')].map((n) => n.textContent)).toEqual([
        'Liter',
      ])
    })

    // Unsupported units have no element and no burst tier to filter on, so the
    // toolbar deliberately does not reach them.
    it('leaves the unsupported list whole no matter what is filtered', async () => {
      const user = userEvent.setup()
      grid(['crown', '2b', 'alice-wonderland-bunny'])
      await user.click(screen.getByRole('button', { name: '수냉' }))
      expect(screen.getByText('엔진 미지원 (2기)')).toBeInTheDocument()
      expect(screen.getByText('2B')).toBeInTheDocument()
    })

    it('counts against the supported units alone', async () => {
      const user = userEvent.setup()
      grid(['crown', 'anne', '2b'])
      await user.click(screen.getByRole('button', { name: '작열' }))
      expect(screen.getByText('2기 중 1기 표시 중')).toBeInTheDocument()
    })
  })
})

// 인게임 장비 화면을 되돌려 보는 모드. 탭 전체가 한꺼번에 바뀌어야 유닛끼리
// 같은 열에서 비교된다 - 카드마다 따로 펴면 그 비교가 깨진다.
describe('RosterGrid 오버로드 상세 모드', () => {
  const geared = (slug: string): NikkeDraft => ({
    ...draft(slug),
    overload_options: [
      {
        id: `${slug}-1`,
        name: '우월코드 대미지 증가',
        value: '29.16',
        lines: [{ slot: 'head', index: 1, value: 29.16, level: 15 }],
      },
    ],
  })

  const gearedGrid = (slugs: string[] = ['crown', 'liter']) =>
    render(
      <RosterGrid
        drafts={slugs.map(geared)}
        supportedUnits={SUPPORTED}
        portraitFor={() => null}
      />,
    )

  const toggle = () => screen.getByRole('button', { name: '오버로드 옵션 상세' })

  beforeEach(() => localStorage.clear())

  // 「우코」로 세지 않는다 - 정렬 메뉴에도 같은 글자가 있어 카드 밖까지 잡힌다.
  it('기본은 요약 줄이다', () => {
    const { container } = gearedGrid()
    expect(toggle()).toHaveAttribute('aria-pressed', 'false')
    expect(container.querySelector('.gear')).toBeNull()
    expect(container.querySelectorAll('.overload__name')).toHaveLength(2)
  })

  // 눌린 상태를 색으로만 말하면 색을 못 읽는 사람에게는 상태가 없다.
  it('눌린 상태를 aria-pressed로 말한다', async () => {
    gearedGrid()
    await userEvent.click(toggle())
    expect(toggle()).toHaveAttribute('aria-pressed', 'true')
  })

  // 격자의 빨간 수치와 흰 행이 무슨 뜻인지는 화면 어디에도 안 적혀 있다.
  it('버튼 옆 툴팁이 단계별 표기 규칙을 말한다', () => {
    gearedGrid()
    expect(screen.getByRole('button', { name: '오버로드 옵션 상세 설명' })).toBeInTheDocument()
    const tip = screen.getByRole('tooltip')
    expect(tip).toHaveTextContent('12~14단계')
    expect(tip).toHaveTextContent('15단계')
    expect(tip).toHaveTextContent('빨간색 수치')
    expect(tip).toHaveTextContent('흰색 바탕')
  })

  it('켜면 보이는 카드가 모두 장비 격자로 바뀐다', async () => {
    const { container } = gearedGrid()
    await userEvent.click(toggle())
    expect(container.querySelectorAll('.gear')).toHaveLength(2)
    expect(container.querySelectorAll('.overload__name')).toHaveLength(0)
  })

  // 매번 다시 켜게 만들면 모드가 아니라 잔소리가 된다 - 사이드바 접힘과 같다.
  it('선택이 다음에 열 때까지 남는다', async () => {
    const first = gearedGrid()
    await userEvent.click(toggle())
    first.unmount()

    const { container } = gearedGrid()
    expect(toggle()).toHaveAttribute('aria-pressed', 'true')
    expect(container.querySelectorAll('.gear')).toHaveLength(2)
  })

  // 사생활 모드 등으로 저장이 막혀도 모드 자체는 동작해야 한다.
  it('저장이 막혀 있어도 켜진다', async () => {
    const setItem = vi
      .spyOn(Storage.prototype, 'setItem')
      .mockImplementation(() => {
        throw new Error('storage disabled')
      })
    const { container } = gearedGrid()
    await userEvent.click(toggle())
    expect(container.querySelectorAll('.gear')).toHaveLength(2)
    setItem.mockRestore()
  })

  // 로스터가 비면 필터 툴바도 없다 - 아무것도 못 바꾸는 스위치만 남으면 안 된다.
  it('지원 유닛이 하나도 없으면 스위치를 내놓지 않는다', () => {
    render(
      <RosterGrid drafts={[draft('2b')]} supportedUnits={SUPPORTED} portraitFor={() => null} />,
    )
    expect(screen.queryByRole('button', { name: '오버로드 옵션 상세' })).not.toBeInTheDocument()
    expect(screen.queryByRole('tooltip')).not.toBeInTheDocument()
  })
})
