import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { SavedRunList } from './SavedRunList'
import { HELP } from '../lib/helpText'
import type { SavedRun } from '../types/profile'

const run = (overrides: Partial<SavedRun> = {}): SavedRun => ({
  id: 'r1',
  name: '작열 · 전부 최적화 · 08-06',
  savedAt: 1754438400000,
  tab: 'solo',
  view: {
    mode: 'raid',
    boss: {
      element: 'Fire',
      core_hittable: false,
      pierce_hits_body_behind_core: false,
      enemy_def: 31784,
      fight_duration: 180,
      part_destructible: false,
      part_destruction_times: [],
      spawns_adds: false,
      hold_fire_despite_adds: false,
      core_diameter_px: null,
      effective_range_band: null,
      elemental_interrupt_required: false,
    },
    numDecks: 5,
    decks: [],
    combinedTotalDamage: 1,
    excludedSlugs: [],
    leftoverSlugs: [],
  },
  ...overrides,
})

const noop = () => {}

const renderList = (overrides = {}) =>
  render(
    <SavedRunList
      runs={[run()]}
      renderRun={() => <p>결과 내용</p>}
      onRestore={noop}
      onRename={noop}
      onDelete={noop}
      {...overrides}
    />,
  )

describe('SavedRunList', () => {
  it('보관한 것이 없으면 없다고 말한다', () => {
    renderList({ runs: [] })

    expect(screen.getByText(HELP.savedRuns.empty)).toBeInTheDocument()
  })

  it('열기 전에는 결과를 그리지 않는다', async () => {
    const user = userEvent.setup()
    renderList()
    expect(screen.queryByText('결과 내용')).not.toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /작열 · 전부 최적화/ }))

    expect(screen.getByText('결과 내용')).toBeInTheDocument()
  })

  // 여는 것만으로 폼이 바뀌면, 결과를 훑어보려던 클릭이 지금 짜던 설정을 지운다.
  it('여는 것만으로는 폼을 되돌리지 않는다', async () => {
    const user = userEvent.setup()
    const onRestore = vi.fn()
    renderList({ onRestore })

    await user.click(screen.getByRole('button', { name: /작열 · 전부 최적화/ }))
    expect(onRestore).not.toHaveBeenCalled()

    await user.click(screen.getByRole('button', { name: '이 설정으로 폼 채우기' }))
    expect(onRestore).toHaveBeenCalledWith(run())
  })

  it('지우기 전에 묻는다', async () => {
    const user = userEvent.setup()
    const onDelete = vi.fn()
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(false)
    renderList({ onDelete })

    await user.click(screen.getByRole('button', { name: /작열 · 전부 최적화/ }))
    await user.click(screen.getByRole('button', { name: '삭제' }))
    expect(onDelete).not.toHaveBeenCalled()

    confirmSpy.mockReturnValue(true)
    await user.click(screen.getByRole('button', { name: '삭제' }))
    expect(onDelete).toHaveBeenCalledWith('r1')

    confirmSpy.mockRestore()
  })

  it('그 자리에서 이름을 바꾼다', async () => {
    const user = userEvent.setup()
    const onRename = vi.fn()
    renderList({ onRename })

    await user.click(screen.getByRole('button', { name: /작열 · 전부 최적화/ }))
    await user.click(screen.getByRole('button', { name: '이름 바꾸기' }))
    const field = screen.getByLabelText('이름')
    await user.clear(field)
    await user.type(field, '새 이름')
    await user.click(screen.getByRole('button', { name: '확인' }))

    expect(onRename).toHaveBeenCalledWith('r1', '새 이름')
  })

  it('빈 이름으로는 바꾸지 않는다', async () => {
    const user = userEvent.setup()
    const onRename = vi.fn()
    renderList({ onRename })

    await user.click(screen.getByRole('button', { name: /작열 · 전부 최적화/ }))
    await user.click(screen.getByRole('button', { name: '이름 바꾸기' }))
    await user.clear(screen.getByLabelText('이름'))
    await user.click(screen.getByRole('button', { name: '확인' }))

    expect(onRename).not.toHaveBeenCalled()
  })

  // 이름에도 날짜가 들어갈 수 있으므로 시각까지 있는 형식으로 특정한다.
  it('저장한 때를 보여준다', () => {
    renderList()

    expect(screen.getByText(/^\d{2}-\d{2} \d{2}:\d{2}$/)).toBeInTheDocument()
  })
})

// 보관물은 그때의 응답을 그대로 박제한 기록이고, 로스터 재동기화에도 앱
// 업데이트에도 살아남는다. 그래서 옛 모양이 새 화면으로 들어오는 일이 구조적으로
// 생기고, 2026-08-22에는 그것이 앱 전체를 언마운트시켰다(검은 화면). 여기서 재는
// 것은 그 사고가 이제 "이 항목 하나가 안 열림"으로 줄어드는가다.
describe('SavedRunList 열다가 터졌을 때', () => {
  const Boom = () => {
    throw new Error('Cannot read properties of undefined')
  }

  beforeEach(() => {
    vi.spyOn(console, 'error').mockImplementation(() => {})
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  // 한 번에 한 항목만 펼쳐지므로 "둘이 동시에 산다"가 아니라 "터진 뒤에도 목록이
  // 살아 있어 다른 것을 열 수 있다"가 재는 값이다. 울타리가 없으면 첫 클릭에서
  // 목록째 사라져 두 번째 클릭 자체가 불가능하다.
  it('터진 뒤에도 목록이 살아 다른 항목을 열 수 있다', async () => {
    const user = userEvent.setup()
    const broken = run({ id: 'bad', name: '깨진 보관물' })
    const fine = run({ id: 'ok', name: '멀쩡한 보관물' })
    render(
      <SavedRunList
        runs={[broken, fine]}
        renderRun={(r) => (r.id === 'bad' ? <Boom /> : <p>결과 내용</p>)}
        onRestore={noop}
        onRename={noop}
        onDelete={noop}
      />,
    )

    await user.click(screen.getByRole('button', { name: /깨진 보관물/ }))
    expect(screen.getByRole('alert')).toHaveTextContent('깨진 보관물')

    await user.click(screen.getByRole('button', { name: /멀쩡한 보관물/ }))
    expect(screen.getByText('결과 내용')).toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  // 열 수 없는 보관물을 손에 쥔 유저에게 남는 유일한 수가 삭제다. 이것이 없으면
  // localStorage를 통째로 지우는 것 말고는 빠져나올 길이 없다. 그 버튼은 울타리
  // **바깥**에 있어야 살아남는다 - 안쪽에 있으면 폴백이 그것까지 걷어낸다.
  it('안내가 떠도 그 보관물을 지우는 길이 남아 있다', async () => {
    const user = userEvent.setup()
    const onDelete = vi.fn()
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    render(
      <SavedRunList
        runs={[run({ id: 'bad', name: '깨진 보관물' })]}
        renderRun={() => <Boom />}
        onRestore={noop}
        onRename={noop}
        onDelete={onDelete}
      />,
    )

    await user.click(screen.getByRole('button', { name: /깨진 보관물/ }))
    expect(screen.getByRole('alert')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: '삭제' }))

    expect(onDelete).toHaveBeenCalledWith('bad')
  })

  // 같은 자리에 삭제가 둘이면 안 된다 - 하나만 확인을 묻는 상태로 갈리기 때문이다.
  it('안내가 삭제 버튼을 하나 더 만들지 않는다', async () => {
    const user = userEvent.setup()
    render(
      <SavedRunList
        runs={[run({ id: 'bad', name: '깨진 보관물' })]}
        renderRun={() => <Boom />}
        onRestore={noop}
        onRename={noop}
        onDelete={noop}
      />,
    )

    await user.click(screen.getByRole('button', { name: /깨진 보관물/ }))

    expect(screen.getAllByRole('button', { name: /삭제/ })).toHaveLength(1)
  })

  // 이번 사고를 가른 정보가 정확히 이것이었다: 그 덱이 실제로 무슨 키를 갖고
  // 있는가. 유저가 그것을 버튼 하나로 넘길 수 있어야 한다.
  it('진단에 버전과 덱이 가진 키 목록을 담는다', async () => {
    const user = userEvent.setup()
    const writeText = vi.fn().mockResolvedValue(undefined)
    Object.defineProperty(navigator, 'clipboard', {
      value: { writeText },
      configurable: true,
    })
    const legacy = run({ id: 'bad', name: '깨진 보관물' })
    // v0.1.4에서 저장된 덱의 모양 - hold_fire_slugs가 없다.
    ;(legacy.view as { decks: unknown[] }).decks = [
      { deck: ['a'], total_damage: 1, hold_burst_slugs: [] },
    ]
    render(
      <SavedRunList
        runs={[legacy]}
        renderRun={() => <Boom />}
        onRestore={noop}
        onRename={noop}
        onDelete={noop}
        versions={{ engineVersion: 'fb6b35bb068b', appVersion: 'v0.1.5' }}
      />,
    )

    await user.click(screen.getByRole('button', { name: /깨진 보관물/ }))
    await user.click(screen.getByRole('button', { name: /진단 정보 복사/ }))

    const text = writeText.mock.calls[0][0] as string
    expect(text).toContain('v0.1.5')
    expect(text).toContain('fb6b35bb068b')
    expect(text).toContain('깨진 보관물')
    expect(text).toContain('deck, total_damage, hold_burst_slugs')
  })
})
