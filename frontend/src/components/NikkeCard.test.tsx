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

// 인게임 장비 화면을 되돌린 표시다: 네 부위를 정사각으로 놓고, 부위마다 옵션
// 행 셋을 세우고, 롤을 수치가 아니라 단계로 강조한다.
describe('NikkeCard 오버로드 상세', () => {
  // 머리에 세 행이 다 찼고, 몸통에 한 행만 있고, 팔·다리는 비었다.
  const geared = (): NikkeDraft => ({
    ...makeEmptyDraft(),
    overload_options: [
      {
        id: '1',
        name: '우월코드 대미지 증가',
        value: '55.52',
        lines: [
          { slot: 'head', index: 1, value: 29.16, level: 15 },
          { slot: 'head', index: 3, value: 26.36, level: 13 },
        ],
      },
      {
        id: '2',
        name: '공격력 증가',
        value: '15.88',
        lines: [
          { slot: 'head', index: 2, value: 11.11, level: 10 },
          { slot: 'torso', index: 1, value: 4.77, level: 1 },
        ],
      },
    ],
  })

  const detailCard = (draft: NikkeDraft = geared()) =>
    render(
      <NikkeCard draft={draft} index={0} name="Crown" element="Fire" portrait={null}
        overloadDetail />,
    )

  it('네 부위를 인게임 배치 순서로 그린다', () => {
    detailCard()
    const slots = screen.getAllByRole('heading', { level: 4 }).map((h) => h.textContent)
    expect(slots).toEqual(['머리', '몸통', '팔', '다리'])
  })

  it('부위마다 옵션 행을 셋 그린다 - 롤이 없는 행도 자리를 지킨다', () => {
    const { container } = detailCard()
    expect(container.querySelectorAll('.gear__piece')).toHaveLength(4)
    expect(container.querySelectorAll('.gear__roll')).toHaveLength(12)
  })

  // 백엔드가 방어력 롤을 버리므로(엔진이 안 쓴다) 2행이 방어력이던 장비는 1행과
  // 3행만 온다. 당겨 붙이면 「1·2행을 굴렸다」고 말하는 셈이 된다.
  it('빠진 행이 가운데면 빈 자리도 가운데다', () => {
    const { container } = detailCard({
      ...makeEmptyDraft(),
      overload_options: [
        {
          id: '1',
          name: '우월코드 대미지 증가',
          value: '29.16',
          lines: [{ slot: 'head', index: 1, value: 29.16, level: 15 }],
        },
        {
          id: '2',
          name: '공격력 증가',
          value: '11.11',
          lines: [{ slot: 'head', index: 3, value: 11.11, level: 10 }],
        },
      ],
    })
    const head = container.querySelector('.gear__piece')!
    expect([...head.querySelectorAll('.gear__roll')].map((r) => r.textContent)).toEqual([
      '[우월코드 대미지]29.16%',
      '—',
      '[공격력]11.11%',
    ])
  })

  it('한 부위 안을 인게임과 같은 옵션 행 순서로 세운다', () => {
    const { container } = detailCard()
    const head = container.querySelector('.gear__piece')!
    const names = [...head.querySelectorAll('.gear__name')].map((n) => n.textContent)
    expect(names).toEqual(['[우월코드 대미지]', '[공격력]', '[우월코드 대미지]'])
  })

  it('요약의 축약이 아니라 인게임처럼 전체 이름을 쓴다', () => {
    detailCard()
    expect(screen.getAllByText('[우월코드 대미지]').length).toBeGreaterThan(0)
    expect(screen.queryByText('우코')).not.toBeInTheDocument()
  })

  it('합계가 아니라 롤 하나하나의 수치를 보여준다', () => {
    detailCard()
    expect(screen.getByText('29.16%')).toBeInTheDocument()
    expect(screen.getByText('26.36%')).toBeInTheDocument()
    // 55.52는 두 롤의 합계다 - 상세 모드가 말하는 값이 아니다.
    expect(screen.queryByText('55.52%')).not.toBeInTheDocument()
  })

  it('15단계 롤을 최고 강조로 표시한다', () => {
    detailCard()
    expect(screen.getByText('29.16%').closest('.gear__roll')).toHaveAttribute('data-tier', 'max')
  })

  it('12~14단계 롤을 중간 강조로 표시한다', () => {
    detailCard()
    expect(screen.getByText('26.36%').closest('.gear__roll')).toHaveAttribute('data-tier', 'high')
  })

  it('11단계 이하는 강조하지 않는다', () => {
    detailCard()
    expect(screen.getByText('11.11%').closest('.gear__roll')).not.toHaveAttribute('data-tier')
  })

  it('끄면 격자 대신 요약 줄로 돌아간다', () => {
    const { container } = render(
      <NikkeCard draft={geared()} index={0} name="Crown" element="Fire" portrait={null} />,
    )
    expect(container.querySelector('.gear')).toBeNull()
    expect(screen.getByText('우코')).toBeInTheDocument()
  })

  // 합계는 롤로 되돌릴 수 없다. 격자를 그리면 스탯이 통째로 빠진 채 완성된
  // 장비처럼 보이므로, 요약을 지키고 왜 못 보여주는지 말한다.
  it('롤을 안 실은 옛 로스터는 요약을 지키고 재동기화를 안내한다', () => {
    const { container } = detailCard({
      ...makeEmptyDraft(),
      overload_options: [{ id: '1', name: '공격력 증가', value: '18.2' }],
    })
    expect(container.querySelector('.gear')).toBeNull()
    expect(screen.getByText('공')).toBeInTheDocument()
    expect(screen.getByText(/다시 동기화/)).toBeInTheDocument()
  })

  it('오버로드가 아예 없으면 없다고만 말한다', () => {
    const { container } = detailCard(makeEmptyDraft())
    expect(container.querySelector('.gear')).toBeNull()
    expect(screen.getByText('오버로드 없음')).toBeInTheDocument()
    expect(screen.queryByText(/다시 동기화/)).not.toBeInTheDocument()
  })
})
