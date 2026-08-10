import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { NikkeCard } from './NikkeCard'
import { makeEmptyDraft, type NikkeDraft } from '../types/nikkeDraft'

const filledDraft = (): NikkeDraft => ({
  ...makeEmptyDraft(),
  character_slug: 'red-hood',
  grade: 3,
  core: 7,
  level: '200',
  hp: '1000000',
  atk: '85000',
  def_: '12000',
  skill_levels: { skill1: '10', skill2: '7', burst: '4' },
  overload_options: [{ id: '1', name: '공격력 증가', value: '18.2' }],
})

// '공격력 상승'은 abbreviateOverload가 아는 이름(「공격력 증가」)이 아니라 줄여지지
// 않고 그대로 렌더된다 - 오버로드 줄 어디를 눌러도 토글되는지 보려면 클릭할 진짜
// 텍스트가 있어야 한다.
const draftWithOverload = (): NikkeDraft => ({
  ...makeEmptyDraft(),
  overload_options: [{ id: '1', name: '공격력 상승', value: '10' }],
})

const card = (
  draft: NikkeDraft = filledDraft(),
  portrait: string | null = null,
  name = 'Red Hood',
) => render(<NikkeCard draft={draft} index={0} name={name} element="Fire" portrait={portrait} />)

describe('NikkeCard', () => {
  it('falls back to a positional title when there is neither name nor slug', () => {
    card(makeEmptyDraft(), null, '')
    expect(screen.getByRole('heading', { name: '니케 1' })).toBeInTheDocument()
  })

  // The slug identifies the unit; the name is what a player reads.
  it('titles the card with the unit name, not its slug', () => {
    card()
    expect(screen.getByRole('heading', { name: 'Red Hood' })).toBeInTheDocument()
    expect(screen.queryByText('red-hood')).not.toBeInTheDocument()
  })

  it('hearts a unit whose Favorite Item is equipped', () => {
    card({ ...filledDraft(), favorite_item: true })
    expect(screen.getByTitle('애장품 장착')).toBeInTheDocument()
  })

  it('leaves the portrait unhearted when no Favorite Item is equipped', () => {
    card({ ...filledDraft(), favorite_item: false })
    expect(screen.queryByTitle('애장품 장착')).not.toBeInTheDocument()
  })

  it('falls back to the slug when no name was resolved', () => {
    card(filledDraft(), null, '')
    expect(screen.getByRole('heading', { name: 'red-hood' })).toBeInTheDocument()
  })

  it('renders the synced skill levels', () => {
    card()
    expect(screen.getByText('S1')).toBeInTheDocument()
    expect(screen.getByText('S2')).toBeInTheDocument()
    expect(screen.getByText('B')).toBeInTheDocument()
    expect(screen.getByText('10')).toBeInTheDocument()
    expect(screen.getByText('7')).toBeInTheDocument()
    expect(screen.getByText('4')).toBeInTheDocument()
  })

  it('renders synced overload option lines, abbreviated', () => {
    card()
    expect(screen.getByText('공')).toBeInTheDocument()
    expect(screen.getByText('18.2%')).toBeInTheDocument()
  })

  // Level and the raw stats are engine inputs, not something the player acts
  // on - level is pinned to 400 for everyone and the stats are derived from
  // breakthrough/core/gear, all of which the card already shows.
  it('does not show level or the raw HP/ATK/DEF', () => {
    card()
    for (const value of ['200', '1000000', '85000', '12000']) {
      expect(screen.queryByText(value)).not.toBeInTheDocument()
    }
  })

  it('shows the investment badge from grade/core', () => {
    card()
    expect(screen.getByText('★★★')).toBeInTheDocument()
    expect(screen.getByText('+7')).toBeInTheDocument()
  })

  it('renders the portrait when one resolves, and omits it otherwise', () => {
    const { unmount } = card(filledDraft(), '/portraits/red-hood.png')
    // Decorative: the heading already names the unit, so the image is alt="".
    expect(document.querySelector('img')).toHaveAttribute('src', '/portraits/red-hood.png')
    unmount()

    card()
    expect(document.querySelector('img')).toBeNull()
  })

  it('renders no editable inputs or remove button', () => {
    card()
    expect(screen.queryAllByRole('textbox')).toHaveLength(0)
    expect(screen.queryAllByRole('spinbutton')).toHaveLength(0)
    expect(screen.queryByRole('button')).not.toBeInTheDocument()
  })

  it('오버로드 줄을 눌러도 제외가 토글된다', async () => {
    const onToggleExclude = vi.fn()
    render(
      <NikkeCard
        draft={draftWithOverload()}
        index={0}
        name="Crown"
        element="Fire"
        portrait={null}
        onToggleExclude={onToggleExclude}
      />,
    )

    await userEvent.click(screen.getByText(/공격력/))

    expect(onToggleExclude).toHaveBeenCalledTimes(1)
  })

  it('이름을 눌러도 제외가 토글된다', async () => {
    const onToggleExclude = vi.fn()
    render(
      <NikkeCard draft={makeEmptyDraft()} index={0} name="Crown" element="Fire"
        portrait={null} onToggleExclude={onToggleExclude} />,
    )
    await userEvent.click(screen.getByRole('heading', { name: 'Crown' }))
    expect(onToggleExclude).toHaveBeenCalledTimes(1)
  })

  // 초상화는 버튼 안이고 버튼은 껍데기 안이다. 둘 다 핸들러를 들면 한 번 눌러
  // 두 번 토글돼 아무 일도 안 한 것처럼 보인다.
  it('초상화를 눌러도 정확히 한 번만 토글된다', async () => {
    const onToggleExclude = vi.fn()
    render(
      <NikkeCard draft={makeEmptyDraft()} index={0} name="Crown" element="Fire"
        portrait={null} onToggleExclude={onToggleExclude} />,
    )
    await userEvent.click(screen.getByRole('button', { name: 'Crown 사용' }))
    expect(onToggleExclude).toHaveBeenCalledTimes(1)
  })

  // 제외를 제안하지 않는 화면에서는 카드가 아무 데도 반응하면 안 된다.
  it('onToggleExclude가 없으면 카드는 눌리지 않는다', async () => {
    render(<NikkeCard draft={makeEmptyDraft()} index={0} name="Crown" element="Fire" portrait={null} />)
    expect(screen.queryByRole('button')).not.toBeInTheDocument()
  })
})
