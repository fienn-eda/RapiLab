import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { UnitPalette } from './UnitPalette'
import type { SupportedUnit } from '../types/supportedUnit'
import type { UserNikkeState } from '../types/userNikkeState'
import { HELP } from '../lib/helpText'

vi.mock('../hooks/usePortraitManifest', () => ({
  usePortraitManifest: () => ({ portraitFor: () => null }),
}))

const UNITS: SupportedUnit[] = [
  { slug: 'crown', name: 'Crown', burstTier: 1, element: 'Iron' },
  { slug: 'anne', name: 'Anne', burstTier: 1, element: 'Fire' },
  { slug: 'liter', name: 'Liter', burstTier: 2, element: 'Water' },
  { slug: 'blanc', name: 'Blanc', burstTier: 3, element: 'Wind' },
  { slug: 'noir', name: 'Noir', burstTier: 3, element: 'Electric' },
]

const owned = (
  slug: string,
  investment: Partial<Pick<UserNikkeState, 'skill_levels' | 'overload_options'>> = {},
): UserNikkeState => ({
  character_slug: slug,
  level: 400,
  hp: 1,
  atk: 1,
  def_: 1,
  skill_levels: { skill1: 10, skill2: 10, burst: 10 },
  overload_options: [],
  ...investment,
})

const base = {
  roster: [owned('crown'), owned('liter'), owned('blanc')],
  supportedUnits: UNITS,
  excludedSlugs: [],
  onToggleExclude: () => {},
}

const renderPalette = (overrides: Partial<Parameters<typeof UnitPalette>[0]> = {}) =>
  render(<UnitPalette {...base} {...overrides} />)

describe('UnitPalette', () => {
  const unitButton = (name: RegExp) => screen.getByRole('button', { name })

  it('groups owned-and-supported units under B1/B2/B3, excluding unowned', () => {
    render(<UnitPalette {...base} draggable usedSlugs={[]} />)
    expect(screen.getByRole('heading', { name: 'B1' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'B2' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'B3' })).toBeInTheDocument()
    expect(unitButton(/crown/i)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /anne/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /noir/i })).not.toBeInTheDocument()
  })

  // The chip is a portrait and its skill pips; the name, tier and element it
  // used to print are on the hover card, and the button carries the name for
  // anyone not looking at pixels.
  it('names each unit through its button rather than visible chip text', () => {
    render(<UnitPalette {...base} />)
    expect(unitButton(/crown 사용/i)).toBeInTheDocument()
    expect(unitButton(/liter 사용/i)).toBeInTheDocument()
    // Element renders as its Korean label in the chip's meta line, not the raw name.
    expect(screen.getByText(/B1 · 철갑/)).toBeInTheDocument()
  })

  it('reports pool membership as the pressed state of the portrait toggle', () => {
    render(<UnitPalette {...base} excludedSlugs={['liter']} />)
    expect(unitButton(/crown 사용/i)).toHaveAttribute('aria-pressed', 'true')
    expect(unitButton(/liter 사용/i)).toHaveAttribute('aria-pressed', 'false')
  })

  it('toggles a unit out of the pool when its portrait is clicked', async () => {
    const user = userEvent.setup()
    const onToggleExclude = vi.fn()
    render(<UnitPalette {...base} onToggleExclude={onToggleExclude} />)
    await user.click(unitButton(/crown 사용/i))
    expect(onToggleExclude).toHaveBeenCalledWith('crown')
  })

  it('only lets an included, unseated unit be dragged in draft mode', () => {
    render(<UnitPalette {...base} draggable usedSlugs={['crown']} excludedSlugs={['blanc']} />)
    expect(unitButton(/liter 사용/i)).toHaveAttribute('draggable', 'true')
    // Already in a deck, so there is nothing left to seat.
    expect(unitButton(/crown 사용/i)).toHaveAttribute('draggable', 'false')
    // Out of the pool entirely.
    expect(unitButton(/blanc 사용/i)).toHaveAttribute('draggable', 'false')
  })

  it('drags nothing outside draft mode', () => {
    render(<UnitPalette {...base} />)
    expect(unitButton(/liter 사용/i)).toHaveAttribute('draggable', 'false')
  })

  // Clicking a portrait asks "will you field this one?", which the portrait
  // alone cannot answer - so skill levels sit on the chip, and the hover card
  // carries the unit's identity and what it rolled.
  it("shows each unit's skill levels and named overload rolls", () => {
    render(
      <UnitPalette
        {...base}
        roster={[
          owned('crown', {
            skill_levels: { skill1: 10, skill2: 4, burst: 7 },
            overload_options: [
              { name: '공격력 증가', value: 40.91 },
              { name: '우월코드 대미지 증가', value: 99.82 },
            ],
          }),
        ]}
      />,
    )
    expect(screen.getByText('10')).toBeInTheDocument()
    expect(screen.getByText('4')).toBeInTheDocument()
    expect(screen.getByText('7')).toBeInTheDocument()
    // Named and valued, never merely counted: "공 40.91%" and a revive chance
    // are both one line but not remotely the same decision. Names are
    // abbreviated to the forms used at the table.
    // Scoped to the overload line itself: the filter toolbar's sort <select>
    // offers the same abbreviations as option text.
    expect(screen.getByText('공', { selector: '.overload__name' })).toBeInTheDocument()
    expect(screen.getByText('40.91%')).toBeInTheDocument()
    expect(screen.getByText('우코', { selector: '.overload__name' })).toBeInTheDocument()
    expect(screen.getByText('99.82%')).toBeInTheDocument()
  })

  it('says so when a unit rolled no overload at all', () => {
    render(<UnitPalette {...base} roster={[owned('crown')]} />)
    expect(screen.getByText('오버로드 없음')).toBeInTheDocument()
  })

  // Five rows top to bottom - breakthrough, core, S1, S2, B - so the column
  // lines up across every chip in the grid.
  describe('the stat column beside the portrait', () => {
    const chip = (investment: { grade?: number; core?: number }) =>
      render(
        <UnitPalette
          {...base}
          roster={[owned('crown', { skill_levels: { skill1: 10, skill2: 4, burst: 7 } })]}
          investmentFor={() => investment}
        />,
      )

    it('leads with breakthrough and core, then the three skill levels', () => {
      const { container } = chip({ grade: 2, core: 4 })
      const cells = [...container.querySelectorAll('.palette__stats > li')]
      expect(cells.map((cell) => cell.textContent)).toEqual([
        '★★☆',
        '+4',
        'S110',
        'S24',
        'B7',
      ])
    })

    it('keeps breakthrough and core in cells of their own', () => {
      const { container } = chip({ grade: 3, core: 2 })
      expect(container.querySelectorAll('.palette__stat--grade')).toHaveLength(1)
      expect(container.querySelectorAll('.palette__stat--core')).toHaveLength(1)
    })

    // A dash, not "+0" or an empty cell: the row still has to hold its place
    // in the column, and there is nothing to report in it.
    it('dashes an uncored unit rather than claiming a zero', () => {
      const { container } = chip({ grade: 3, core: 0 })
      expect(container.querySelector('.palette__stat--core')).toHaveTextContent('—')
    })

    it('dashes breakthrough when the unit carries no grade at all', () => {
      const { container } = chip({})
      expect(container.querySelector('.palette__stat--grade')).toHaveTextContent('—')
    })
  })

  describe('the filter toolbar', () => {
    const filtered = () =>
      render(
        <UnitPalette
          {...base}
          roster={[
            owned('crown', { overload_options: [{ name: '공격력 증가', value: 10 }] }),
            owned('liter', { overload_options: [{ name: '공격력 증가', value: 50 }] }),
            owned('blanc'),
          ]}
        />,
      )

    it('hides the units a name search does not match', async () => {
      const user = userEvent.setup()
      filtered()
      await user.type(screen.getByLabelText('이름 검색'), 'cro')
      expect(unitButton(/crown 사용/i)).toBeInTheDocument()
      expect(screen.queryByRole('button', { name: /liter 사용/i })).not.toBeInTheDocument()
    })

    it('drops a burst heading once its last unit is filtered away', async () => {
      const user = userEvent.setup()
      filtered()
      await user.click(screen.getByRole('button', { name: '철갑' }))
      expect(screen.getByRole('heading', { name: 'B1' })).toBeInTheDocument()
      expect(screen.queryByRole('heading', { name: 'B2' })).not.toBeInTheDocument()
      expect(screen.queryByRole('heading', { name: 'B3' })).not.toBeInTheDocument()
    })

    // Sorting reorders inside each burst group; it never merges them, because
    // a deck is always built tier by tier.
    it('sorts within a burst group without dissolving the groups', async () => {
      const user = userEvent.setup()
      render(
        <UnitPalette
          {...base}
          roster={[
            owned('crown', { overload_options: [{ name: '공격력 증가', value: 10 }] }),
            owned('anne', { overload_options: [{ name: '공격력 증가', value: 90 }] }),
            owned('liter'),
          ]}
        />,
      )
      await user.selectOptions(screen.getByLabelText('정렬'), '공')
      await user.selectOptions(screen.getByLabelText('정렬 방향'), 'desc')

      expect(screen.getByRole('heading', { name: 'B1' })).toBeInTheDocument()
      expect(screen.getByRole('heading', { name: 'B2' })).toBeInTheDocument()
      const b1 = screen.getByRole('heading', { name: 'B1' }).closest('section')!
      const names = [...b1.querySelectorAll('.palette__name')].map((n) => n.textContent)
      expect(names).toEqual(['Anne', 'Crown'])
    })

    // The load-bearing invariant: the filter narrows the view, and the pool is
    // a separate decision the user made per unit.
    it('keeps a hidden unit excluded, and hands it back on clearing the filter', async () => {
      const user = userEvent.setup()
      render(<UnitPalette {...base} excludedSlugs={['liter']} />)
      await user.click(screen.getByRole('button', { name: '철갑' }))
      expect(screen.queryByRole('button', { name: /liter 사용/i })).not.toBeInTheDocument()

      await user.click(screen.getByRole('button', { name: '필터 해제' }))
      expect(unitButton(/liter 사용/i)).toHaveAttribute('aria-pressed', 'false')
    })

    it('counts against the units it draws, not the whole roster', async () => {
      const user = userEvent.setup()
      filtered()
      await user.click(screen.getByRole('button', { name: '철갑' }))
      expect(screen.getByText('3기 중 1기 표시 중')).toBeInTheDocument()
    })

    // A bordered toolbar with nothing to filter reads as a bug, not a feature.
    it('does not draw the filter toolbar when the roster owns no supported unit', () => {
      render(<UnitPalette {...base} roster={[]} />)
      expect(screen.queryByLabelText('이름 검색')).not.toBeInTheDocument()
    })
  })
})

describe('without onToggleExclude', () => {
  it('draws the chip as a plain drag source rather than a toggle', () => {
    // 이 화면(미란다 계산기)에는 탐색이 없어 후보 풀이라는 개념이 없다.
    // 켤 수는 있는데 아무 일도 안 일어나는 컨트롤을 남기지 않는다.
    renderPalette({ onToggleExclude: undefined, excludedSlugs: undefined, draggable: true })
    const chip = screen.getByRole('button', { name: 'Crown' })
    expect(chip).not.toHaveAttribute('aria-pressed')
    expect(chip).toHaveAttribute('draggable', 'true')
  })

  // A button with no click handler and a tab stop is the same failure this
  // task removes, just moved from the toggle state to the element role: it
  // still announces as actionable to a keyboard user and still does nothing.
  it('takes the chip out of the tab sequence when it is not a toggle', () => {
    renderPalette({ onToggleExclude: undefined, excludedSlugs: undefined })
    const chip = screen.getByRole('button', { name: 'Crown' })
    expect(chip).toHaveAttribute('tabIndex', '-1')
  })

  it('still toggles when the handler is given', () => {
    const onToggleExclude = vi.fn()
    renderPalette({ onToggleExclude })
    const chip = screen.getByRole('button', { name: /Crown 사용/ })
    expect(chip).toHaveAttribute('aria-pressed', 'true')
    fireEvent.click(chip)
    expect(onToggleExclude).toHaveBeenCalledWith('crown')
  })

  // Regression guard for the recommend and union tabs: giving a handler must
  // restore default focusability, not merely restore the toggle attributes.
  it('leaves the chip in the tab sequence when the handler is given', () => {
    renderPalette({ onToggleExclude: vi.fn() })
    const chip = screen.getByRole('button', { name: /Crown 사용/ })
    expect(chip).not.toHaveAttribute('tabIndex')
  })
})

// 드래그는 설치형 앱(WebView2)에서 dragstart 뒤로 아무 이벤트도 오지 않아
// 자리에 앉힐 방법이 되지 못한다. 그래서 배치는 칩 위의 제 버튼이 맡는다 -
// 칩 본체의 클릭은 이미 "후보 풀에서 빼기"라 겹쳐 쓸 수 없다.
describe('UnitPalette 클릭 배치', () => {
  it('onSeat이 주어지면 배치 버튼을 그리고 그 유닛의 슬러그를 넘긴다', async () => {
    const onSeat = vi.fn()
    renderPalette({ onSeat })
    await userEvent.click(screen.getByRole('button', { name: 'Crown 배치' }))
    expect(onSeat).toHaveBeenCalledWith('crown')
  })

  it('앉힐 곳이 없는 화면에서는 배치 버튼을 안 그린다', () => {
    renderPalette()
    expect(screen.queryByRole('button', { name: /배치/ })).not.toBeInTheDocument()
  })

  // 이미 앉은 유닛은 누를 것이 없다 - 칩이 통째로 컨트롤이므로, 버튼을 지우는
  // 대신 끈다(자리는 그대로 두어 그리드가 흔들리지 않는다).
  it('이미 앉은 유닛의 칩은 눌리지 않는다', async () => {
    const onSeat = vi.fn()
    renderPalette({ onSeat, usedSlugs: ['crown'] })
    const seated = screen.getByRole('button', { name: 'Crown 배치됨' })
    expect(seated).toBeDisabled()
    await userEvent.click(seated)
    expect(onSeat).not.toHaveBeenCalled()
  })

  // 배치가 버튼이 된 덕에 편성이 키보드로도 된다 - 드래그였을 때는 마우스가
  // 없으면 아예 못 하던 일이다.
  it('배치는 탭으로 닿는다', () => {
    renderPalette({ onSeat: vi.fn() })
    expect(screen.getByRole('button', { name: 'Crown 배치' })).not.toHaveAttribute('tabIndex', '-1')
  })

  // 두 뜻을 한 번의 누름에 담을 수 없다. 덱이 옆에 있는 화면에서는 배치가 이긴다.
  it('배치와 제외가 둘 다 주어지면 배치가 이긴다', async () => {
    const onSeat = vi.fn()
    const onToggleExclude = vi.fn()
    renderPalette({ onSeat, onToggleExclude })
    const chip = screen.getByRole('button', { name: 'Crown 배치' })
    expect(chip).not.toHaveAttribute('aria-pressed')
    await userEvent.click(chip)
    expect(onSeat).toHaveBeenCalledWith('crown')
    expect(onToggleExclude).not.toHaveBeenCalled()
  })

  // 표적은 버튼(초상화·이름·티어·오버로드)이 아니라 칩 테두리 안 전체다 - 돌파·
  // 코어·S1/S2/B 칸은 버튼 밖에 있어서, 껍데기가 받지 않으면 죽은 자리가 된다.
  it('스킬레벨 칸을 눌러도 배치된다', async () => {
    const onSeat = vi.fn()
    render(<UnitPalette {...base} onSeat={onSeat} usedSlugs={[]} />)

    const chip = screen.getByRole('button', { name: /crown 배치/i }).closest('.palette__item')!
    await userEvent.click(chip.querySelector('.palette__stat--core')!)

    expect(onSeat).toHaveBeenCalledWith('crown')
  })

  it('초상화를 눌러도 정확히 한 번만 배치된다', async () => {
    const onSeat = vi.fn()
    render(<UnitPalette {...base} onSeat={onSeat} usedSlugs={[]} />)
    await userEvent.click(screen.getByRole('button', { name: /crown 배치/i }))
    expect(onSeat).toHaveBeenCalledTimes(1)
  })

  // 니케 풀에서 「안 쓴다」고 정한 유닛이 배치 화면에서 들어오면 그 결정이 무효다.
  it('제외된 유닛은 칩 어디를 눌러도 배치되지 않는다', async () => {
    const onSeat = vi.fn()
    render(<UnitPalette {...base} onSeat={onSeat} usedSlugs={[]} excludedSlugs={['crown']} />)

    const chip = screen.getByRole('button', { name: /crown/i }).closest('.palette__item')!
    await userEvent.click(chip.querySelector('.palette__stat--core')!)
    await userEvent.click(chip.querySelector('.palette__name')!)

    expect(onSeat).not.toHaveBeenCalled()
  })

  it('이미 앉은 유닛도 칩 어디를 눌러도 다시 배치되지 않는다', async () => {
    const onSeat = vi.fn()
    render(<UnitPalette {...base} onSeat={onSeat} usedSlugs={['crown']} />)

    const chip = screen.getByRole('button', { name: /crown/i }).closest('.palette__item')!
    await userEvent.click(chip.querySelector('.palette__stat--core')!)

    expect(onSeat).not.toHaveBeenCalled()
  })

  // 니케 풀 탭에는 onSeat이 없다. 거기서 제외된 칩까지 막으면 되돌릴 길이 없어진다.
  it('니케 풀에서는 제외된 칩도 계속 눌린다', async () => {
    const onToggleExclude = vi.fn()
    render(<UnitPalette {...base} onToggleExclude={onToggleExclude} excludedSlugs={['crown']} />)

    const chip = screen.getByRole('button', { name: /crown/i }).closest('.palette__item')!
    await userEvent.click(chip.querySelector('.palette__stat--core')!)

    expect(onToggleExclude).toHaveBeenCalledWith('crown')
  })
})

// 니케 풀에서 뺀 니케는 팔레트에서 흐려질 뿐 사라지지는 않는다 - 그래서
// 「내가 뭘 뺐더라」를 되짚으려면 필터가 필요하다.
describe('UnitPalette 제외한 니케 필터', () => {
  it('켜면 제외된 니케만 남는다', async () => {
    const user = userEvent.setup()
    render(<UnitPalette {...base} excludedSlugs={['liter']} />)
    await user.click(screen.getByRole('button', { name: '제외한 니케' }))
    expect(screen.getByRole('button', { name: /liter 사용/i })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /crown 사용/i })).not.toBeInTheDocument()
  })

  // 미란다 계산기에는 후보 풀이 없다 - 거기서 이 칩은 언제나 빈 격자를 만든다.
  it('후보 풀이 없는 화면에는 칩 자체가 없다', () => {
    render(<UnitPalette {...base} excludedSlugs={undefined} onToggleExclude={undefined} />)
    expect(screen.queryByRole('button', { name: '제외한 니케' })).not.toBeInTheDocument()
  })
})

// 제외를 푸는 곳은 니케 풀 탭이다. 솔로·유니온의 팔레트에는 되돌릴 컨트롤이
// 없으므로, 누름에 아무 답도 없으면 칩이 고장 난 것으로 읽힌다.
describe('UnitPalette 제외된 칩을 눌렀을 때', () => {
  const seatingWithExcluded = () => {
    const onSeat = vi.fn()
    render(<UnitPalette {...base} onSeat={onSeat} excludedSlugs={['crown']} />)
    return onSeat
  }
  const bubbleOn = (name: RegExp) =>
    screen
      .getByRole('button', { name })
      .closest('.palette__item')!
      .querySelector('.palette__blocked')

  it('어디서 풀 수 있는지 그 칩 옆에 말해준다', async () => {
    const onSeat = seatingWithExcluded()
    await userEvent.click(screen.getByRole('button', { name: /crown 제외됨/i }))
    expect(onSeat).not.toHaveBeenCalled()
    expect(bubbleOn(/crown/i)).toHaveTextContent(HELP.draft.excludedElsewhere)
  })

  // 버튼 밖(돌파·코어·스킬레벨 칸)도 같은 칩이다.
  it('스킬레벨 칸을 눌러도 같은 안내가 뜬다', async () => {
    seatingWithExcluded()
    const chip = screen.getByRole('button', { name: /crown/i }).closest('.palette__item')!
    await userEvent.click(chip.querySelector('.palette__stat--core')!)
    expect(bubbleOn(/crown/i)).toHaveTextContent(HELP.draft.excludedElsewhere)
  })

  // 말풍선은 aria-hidden이라, 화면을 못 보는 사람에게 답을 전하는 것은 이쪽뿐이다.
  it('라이브 영역으로도 읽힌다', async () => {
    const { container } = render(
      <UnitPalette {...base} onSeat={vi.fn()} excludedSlugs={['crown']} />,
    )
    const live = container.querySelector('[aria-live="polite"]')!
    expect(live).toHaveTextContent('')
    await userEvent.click(screen.getByRole('button', { name: /crown 제외됨/i }))
    expect(live).toHaveTextContent(HELP.draft.excludedElsewhere)
  })

  // 다른 칩을 눌렀다는 것 자체가 안내를 다 읽었다는 뜻이다.
  it('다른 니케를 배치하면 안내가 걷힌다', async () => {
    const onSeat = seatingWithExcluded()
    await userEvent.click(screen.getByRole('button', { name: /crown 제외됨/i }))
    await userEvent.click(screen.getByRole('button', { name: /liter 배치/i }))
    expect(onSeat).toHaveBeenCalledWith('liter')
    expect(bubbleOn(/crown/i)).toBeNull()
  })

  // 배치는 못 하지만 눌리기는 해야 한다 - disabled면 그 누름이 아예 안 와서
  // 왜 안 되는지 말할 기회가 없다.
  it('칩은 죽지 않고 「눌러도 안 된다」만 알린다', () => {
    seatingWithExcluded()
    const chip = screen.getByRole('button', { name: /crown 제외됨/i })
    expect(chip).not.toBeDisabled()
    expect(chip).toHaveAttribute('aria-disabled', 'true')
  })
})
