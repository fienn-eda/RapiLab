import { describe, it, expect, vi, afterEach, beforeEach } from 'vitest'
import { fireEvent, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { UnionRaidPanel, suggestUnionRunName } from './UnionRaidPanel'
import { DRAG_SLUG_TYPE } from './UnitPalette'
import { makeDefaultBossProfileDraft } from '../types/bossProfileDraft'
import type { UserNikkeState } from '../types/userNikkeState'
import type { BurstTier, SupportedUnit } from '../types/supportedUnit'
import type { RaidRotation } from '../types/raidRotation'
import type { SavedRun } from '../types/profile'
import type { BossElement } from '../types/recommend'

vi.mock('../api/evaluateDecks', () => ({
  evaluateDecks: vi.fn(),
}))

import { evaluateDecks } from '../api/evaluateDecks'

/** Seats `slug` in deck `deckNumber` (1-based) the way the UI does: by drop.
 * jsdom implements no drag, so hand the handler the slug a real drag would
 * have carried — same helper RecommendPanel.test.tsx uses. */
const dropOnDeck = (deckNumber: number, slug: string) => {
  const deck = screen.getByRole('heading', { name: new RegExp(`덱 ${deckNumber}`) })
  fireEvent.drop(deck.closest('div')!, {
    dataTransfer: {
      types: [DRAG_SLUG_TYPE],
      getData: (type: string) => (type === DRAG_SLUG_TYPE ? slug : ''),
    },
  })
}

const nikke = (slug: string): UserNikkeState => ({
  character_slug: slug,
  level: 200,
  hp: 1_000_000,
  atk: 85_000,
  def_: 12_000,
  // 유니온은 싱크로 레벨로 싸우므로 동기화된 로스터는 실제 레벨 스탯을 함께
  // 갖는다. 이게 없는 로스터는 유니온 탭이 아예 막는다 - 그 경우는 아래
  // `unsyncedRoster`로 따로 만든다.
  actual_hp: 3_000_000,
  actual_atk: 250_000,
  skill_levels: { skill1: 10, skill2: 7, burst: 4 },
  overload_options: [],
})

/** 실제 레벨 스탯이 없는 로스터 - 옛 북마크릿으로 동기화했거나 손으로 입력한 것. */
const unsyncedRoster: UserNikkeState[] = Array.from({ length: 15 }, (_, i) => {
  const { actual_hp: _hp, actual_atk: _atk, ...rest } = nikke(`u${i}`)
  return rest
})

// 15 units so the three battles' 5-seat decks can actually be filled without
// repeats — union raid's "all 15 seats different Nikkes" rule.
const roster: UserNikkeState[] = Array.from({ length: 15 }, (_, i) => nikke(`u${i}`))
const supportedUnits: SupportedUnit[] = Array.from({ length: 15 }, (_, i) => ({
  slug: `u${i}`,
  name: `U${i}`,
  burstTier: ((i % 3) + 1) as 1 | 2 | 3,
  element: 'Iron' as const,
}))

const portraitFor = () => null
const nameFor = (slug: string) => slug.toUpperCase()
const burstTiersFor = (slug: string): BurstTier[] => {
  const i = Number(slug.slice(1))
  return Number.isNaN(i) ? [] : [((i % 3) + 1) as BurstTier]
}

const unionRotation: RaidRotation = {
  id: 'union-2026-07-31',
  raid: 'union',
  title: '유니온 레이드 7/31',
  starts_at: '2026-07-31T05:00:00+09:00',
  ends_at: '2026-08-06T04:59:00+09:00',
  source_url: 'https://arca.live/b/nikketgv/177833660',
  source_locale: 'ko',
  read_on: '2026-08-07',
  bosses: [
    { name: '선바스', weakness: 'Electric', range_band: null, core_diameter_px: null, stated: {} },
    { name: '토커티브', weakness: 'Water', range_band: null, core_diameter_px: null, stated: {} },
  ],
}

const noKeeping = {
  savedRuns: [],
  excludedSlugs: [],
  onSaveRun: () => true,
  onRenameRun: () => {},
  onDeleteRun: () => {},
}

const renderPanel = (overrides = {}) =>
  render(
    <UnionRaidPanel
      roster={roster}
      supportedUnits={supportedUnits}
      portraitFor={portraitFor}
      nameFor={nameFor}
      burstTiersFor={burstTiersFor}
      {...noKeeping}
      {...overrides}
    />,
  )

/** 세 전투의 좌석을 전부 채운다 - 유니온은 편성이 꽉 차야 실행된다. */
const fillDecks = async () => {
  await screen.findByRole('button', { name: /u0 배치/i })
  for (let deck = 0; deck < 3; deck += 1) {
    for (let seat = 0; seat < 5; seat += 1) {
      dropOnDeck(deck + 1, `u${deck * 5 + seat}`)
    }
  }
}

const fillAndSubmit = async (user: ReturnType<typeof userEvent.setup>) => {
  await fillDecks()
  await user.click(screen.getByRole('button', { name: /인카운터/ }))
}

beforeEach(() => {
  vi.mocked(evaluateDecks).mockReset()
})

afterEach(() => {
  vi.mocked(evaluateDecks).mockReset()
})

describe('UnionRaidPanel', () => {
  it('실제 레벨 스탯이 없으면 제출을 막고 북마크릿 재설치를 안내한다', async () => {
    // 유니온은 싱크로 레벨로 싸운다. 400레벨 값으로 대신 재면 유닛 간 상대
    // ATK가 최대 24% 뒤틀리므로 계산을 아예 하지 않는다. 안내가 "동기화를 다시"
    // 로만 끝나면 옛 북마크릿 사용자는 눌러도 같은 화면을 다시 보게 된다.
    renderPanel({ roster: unsyncedRoster })

    await fillDecks()

    expect(screen.getByRole('button', { name: /인카운터/ })).toBeDisabled()
    expect(evaluateDecks).not.toHaveBeenCalled()
    expect(screen.getByText(/북마크릿/)).toBeInTheDocument()
  })

  it('실제 레벨 스탯이 있으면 막지 않고 stat_basis를 실어 보낸다', async () => {
    // 가드가 늘 막는 것이 아님을 고정한다 - 이게 없으면 "항상 disabled"인
    // 구현도 위 테스트를 통과한다.
    const user = userEvent.setup()
    vi.mocked(evaluateDecks).mockResolvedValue({
      decks: [],
      combined_total_damage: 0,
      excluded_slugs: [],
      engine_version: 'test-engine-version',
    })
    renderPanel()

    await fillAndSubmit(user)

    expect(vi.mocked(evaluateDecks).mock.calls[0][0]).toMatchObject({
      stat_basis: 'actual',
    })
  })


  // 팔레트의 + 는 「어느 덱에」를 말하지 않는다 - 활성 덱이 그것을 정한다.
  // 이게 무너지면 전부 덱 1에 쌓이고, 드래그가 죽은 설치형 앱에서는 옮길
  // 방법도 없어 5덱 편성이라는 기능 자체가 사라진다.
  it('배치 버튼은 덱 1이 아니라 활성 덱을 채운다', async () => {
    const user = userEvent.setup()
    renderPanel()
    await screen.findByRole('button', { name: /u0 배치/i })
    await user.click(screen.getByRole('button', { name: '덱 2 활성 덱으로 선택' }))
    await user.click(screen.getByRole('button', { name: 'U0 배치' }))
    expect(screen.getAllByText(/^\d\/5$/).map((e) => e.textContent)).toEqual([
      '0/5',
      '1/5',
      '0/5',
    ])
  })

  // Fienn이 든 예: 팔레트에서 15명을 누르면 덱 3개가 차야 한다. 활성 덱이
  // 찬 뒤로는 열 번의 클릭이 전부 조용히 삼켜지고 있었다.
  it('덱이 차면 다음 덱으로 넘어가, 15번 누르면 세 덱이 다 찬다', async () => {
    const user = userEvent.setup()
    renderPanel()
    await screen.findByRole('button', { name: /u0 배치/i })

    for (let i = 0; i < 15; i += 1) {
      await user.click(screen.getByRole('button', { name: `U${i} 배치` }))
    }

    expect(screen.getAllByText(/^\d\/5$/).map((e) => e.textContent)).toEqual([
      '5/5',
      '5/5',
      '5/5',
    ])
  })

  // 다음 클릭이 어디로 갈지는 눌러 보기 전에 보여야 한다. 앉힌 「직후」 상태로
  // 다시 훑지 않으면 표시는 여섯 번째 클릭까지 덱 1에 남는다.
  it('덱이 차는 순간 활성 표시가 다음 덱으로 옮겨간다', async () => {
    const user = userEvent.setup()
    renderPanel()
    await screen.findByRole('button', { name: /u0 배치/i })

    for (let i = 0; i < 5; i += 1) {
      await user.click(screen.getByRole('button', { name: `U${i} 배치` }))
    }

    expect(screen.getByRole('button', { name: '덱 1 활성 덱으로 선택' }))
      .toHaveAttribute('aria-pressed', 'false')
    expect(screen.getByRole('button', { name: '덱 2 활성 덱으로 선택' }))
      .toHaveAttribute('aria-pressed', 'true')
  })

  it('기본으로 전투 3회분의 보스 설정을 그린다', () => {
    renderPanel()
    expect(screen.getAllByRole('group', { name: /전투/ })).toHaveLength(3)
  })

  it('전투마다 보스 속성을 따로 고를 수 있다', async () => {
    // The picker speaks in the boss's weakness: 풍압(Wind) weak -> boss is
    // Iron, 전격(Electric) weak -> boss is Water.
    renderPanel()
    const groups = screen.getAllByRole('group', { name: /전투/ })
    await userEvent.click(within(groups[0]).getByLabelText('풍압'))
    await userEvent.click(within(groups[1]).getByLabelText('전격'))
    expect(within(groups[0]).getByLabelText('풍압')).toBeChecked()
    expect(within(groups[1]).getByLabelText('전격')).toBeChecked()
  })

  // 덱 제목은 자리 번호 대신 그 전투의 보스를 부른다. 아직 안 고른 덱은
  // 부를 이름이 없으므로 자리 번호 그대로 남는다.
  it('전투의 보스 속성을 고르면 그 덱 제목이 약점 이름과 아이콘으로 바뀐다', async () => {
    renderPanel()
    expect(screen.getByRole('heading', { name: /덱 1/ })).toBeInTheDocument()
    expect(document.querySelector('.draft-editor__deck-icon')).toBeNull()

    const groups = screen.getAllByRole('group', { name: /전투/ })
    await userEvent.click(within(groups[0]).getByLabelText('풍압'))

    expect(screen.getByRole('heading', { name: /풍압/ })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: /^덱 1/ })).not.toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /덱 2/ })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /덱 3/ })).toBeInTheDocument()
    expect(document.querySelectorAll('.draft-editor__deck-icon')).toHaveLength(1)
  })

  it('전투 1에서 회차 보스를 고르면 전투 2의 선택은 그대로다', async () => {
    // 세 전투가 한 화면에 세 개의 radiogroup을 세운다 - 같은 이름을 쓰면 라디오가
    // 하나의 그룹으로 합쳐진다. useId가 전투마다 다른 그룹 이름을 주는 것을
    // 실제로 클릭해서 확인한다.
    const user = userEvent.setup()
    renderPanel({ rotations: [unionRotation] })
    const groups = screen.getAllByRole('group', { name: /전투/ })

    await user.click(within(groups[0]).getByRole('radio', { name: '전격선바스' }))

    expect(within(groups[0]).getByRole('radio', { name: '전격선바스' })).toBeChecked()
    expect(within(groups[1]).getByRole('radio', { name: '전격선바스' })).not.toBeChecked()
  })

  it('전투 시간 기본값은 180초다', () => {
    renderPanel()
    const groups = screen.getAllByRole('group', { name: /전투/ })
    expect(within(groups[0]).getByLabelText(/전투 시간/)).toHaveValue(180)
  })

  it('15칸을 다 채우기 전에는 제출을 막는다', () => {
    renderPanel()
    expect(screen.getByRole('button', { name: /인카운터/ })).toBeDisabled()
  })

  it('유니온레이드 탭에는 속성저지 체크박스가 없다', () => {
    // 이 탭은 유저가 짠 편성을 채점만 하므로 탐색 제약이 걸 곳이 없다.
    renderPanel()

    expect(screen.queryByLabelText('속성저지 필수')).not.toBeInTheDocument()
  })

  it('잠금 토글을 그리지 않는다', async () => {
    renderPanel()
    await screen.findByRole('button', { name: /u0 배치/i }) // palette rendered
    dropOnDeck(1, 'u0')
    expect(screen.getByRole('button', { name: '덱 1의 U0' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /고정/ })).not.toBeInTheDocument()
  })

  it('전투 수를 줄이면 뒤 전투의 보스 설정과 편성이 사라지고, 다시 늘리면 빈 값이 붙는다', async () => {
    const user = userEvent.setup()
    renderPanel()
    dropOnDeck(3, 'u10')
    expect(screen.getByRole('button', { name: '덱 3의 U10' })).toBeInTheDocument()

    await user.selectOptions(screen.getByLabelText('전투 수'), '1')
    expect(screen.getAllByRole('group', { name: /전투/ })).toHaveLength(1)

    await user.selectOptions(screen.getByLabelText('전투 수'), '3')
    expect(screen.getAllByRole('group', { name: /전투/ })).toHaveLength(3)
    // A fresh, empty battle 3 - shrinking and re-growing does not restore the
    // seat it lost.
    expect(screen.queryByRole('button', { name: '덱 3의 U10' })).not.toBeInTheDocument()
  })

  it('편성 15칸을 다 채우고 제출하면 전투마다 자기 몫의 보스와 5명을 evaluate-decks에 보낸다', async () => {
    const user = userEvent.setup()
    vi.mocked(evaluateDecks).mockResolvedValue({
      decks: [
        { deck: ['u0', 'u1', 'u2', 'u3', 'u4'], total_damage: 10, burst_damage: 6, normal_attack_damage: 4, skill_damage: 0, hold_burst_slugs: [] },
        { deck: ['u5', 'u6', 'u7', 'u8', 'u9'], total_damage: 20, burst_damage: 12, normal_attack_damage: 8, skill_damage: 0, hold_burst_slugs: [] },
        { deck: ['u10', 'u11', 'u12', 'u13', 'u14'], total_damage: 30, burst_damage: 18, normal_attack_damage: 12, skill_damage: 0, hold_burst_slugs: [] },
      ],
      combined_total_damage: 60,
      excluded_slugs: [],
      engine_version: 'test-engine-version',
    })

    renderPanel()
    // 덱을 먼저 채운다 - dropOnDeck은 덱 제목으로 찾는데, 보스를 고르고 나면
    // 그 제목이 자리 번호 대신 보스 이름이 된다.
    for (let deck = 0; deck < 3; deck += 1) {
      for (let seat = 0; seat < 5; seat += 1) {
        dropOnDeck(deck + 1, `u${deck * 5 + seat}`)
      }
    }

    const groups = screen.getAllByRole('group', { name: /전투/ })
    // 풍압 약점 -> 철갑 보스, 전격 약점 -> 수냉 보스, 작열 약점 -> 풍압 보스.
    await user.click(within(groups[0]).getByLabelText('풍압'))
    await user.click(within(groups[1]).getByLabelText('전격'))
    await user.click(within(groups[2]).getByLabelText('작열'))

    const submit = screen.getByRole('button', { name: /인카운터/ })
    expect(submit).toBeEnabled()
    await user.click(submit)

    expect(evaluateDecks).toHaveBeenCalledWith(
      {
        roster,
        decks: [
          {
            units: ['u0', 'u1', 'u2', 'u3', 'u4'],
            boss: expect.objectContaining({ element: 'Iron' }),
          },
          {
            units: ['u5', 'u6', 'u7', 'u8', 'u9'],
            boss: expect.objectContaining({ element: 'Water' }),
          },
          {
            units: ['u10', 'u11', 'u12', 'u13', 'u14'],
            boss: expect.objectContaining({ element: 'Wind' }),
          },
        ],
        // 유니온은 레벨 보정이 없어 싱크로 레벨 스탯으로 잰다.
        stat_basis: 'actual',
      },
      expect.any(AbortSignal),
    )
    expect(await screen.findByText('총합:', { exact: false })).toBeInTheDocument()
  })

  it('결과가 나온 뒤 보스 속성을 바꿔도 카드 표시는 제출 당시 속성 그대로다', async () => {
    // A result's damage was computed against the SUBMITTED boss. Reading the
    // live form field for its label instead would relabel a finished card out
    // from under numbers it wasn't scored against - the exact bug Task 10
    // shipped and had to fix for the evaluate mode this panel mirrors.
    const user = userEvent.setup()
    vi.mocked(evaluateDecks).mockResolvedValue({
      decks: [
        { deck: ['u0', 'u1', 'u2', 'u3', 'u4'], total_damage: 10, burst_damage: 6, normal_attack_damage: 4, skill_damage: 0, hold_burst_slugs: [] },
      ],
      combined_total_damage: 10,
      excluded_slugs: [],
      engine_version: 'test-engine-version',
    })

    renderPanel()
    await user.selectOptions(screen.getByLabelText('전투 수'), '1')
    for (const slug of ['u0', 'u1', 'u2', 'u3', 'u4']) dropOnDeck(1, slug)
    await user.click(screen.getByRole('button', { name: /인카운터/ }))

    expect(await screen.findByText('1번 덱 · 무속성')).toBeInTheDocument()

    const groups = screen.getAllByRole('group', { name: /전투/ })
    // 수냉 약점 -> 작열 보스.
    await user.click(within(groups[0]).getByLabelText('수냉'))

    expect(screen.getByText('1번 덱 · 무속성')).toBeInTheDocument()
    expect(screen.queryByText('1번 덱 · 작열')).not.toBeInTheDocument()
  })

  it('배치된 유닛을 제외하면 편성에서 빠지고, 다시 채워 제출하면 제출 로스터에도 포함되지 않는다', async () => {
    // "Exclude" must mean the same thing here as in the recommend tab's
    // palette: out of the deck AND out of the scored roster, not greyed out
    // while still seated and counted at full weight.
    const user = userEvent.setup()
    vi.mocked(evaluateDecks).mockResolvedValue({
      decks: [
        { deck: ['u1', 'u2', 'u3', 'u4', 'u5'], total_damage: 10, burst_damage: 6, normal_attack_damage: 4, skill_damage: 0, hold_burst_slugs: [] },
      ],
      combined_total_damage: 10,
      excluded_slugs: [],
      engine_version: 'test-engine-version',
    })

    // 미사용은 니케 풀 탭이 정하고 이 탭은 받아 읽는다 - 그래서 칩을 누르는
    // 대신 프로퍼티로 넣는다.
    const { rerender } = renderPanel({ excludedSlugs: [] })
    await user.selectOptions(screen.getByLabelText('전투 수'), '1')
    await screen.findByRole('button', { name: /u0 배치/i }) // palette rendered
    for (const slug of ['u0', 'u1', 'u2', 'u3', 'u4']) dropOnDeck(1, slug)

    // u0을 빼면 앉아 있던 자리에서도 빠진다.
    rerender(
      <UnionRaidPanel
        roster={roster}
        supportedUnits={supportedUnits}
        portraitFor={portraitFor}
        nameFor={nameFor}
        burstTiersFor={burstTiersFor}
        {...noKeeping}
        excludedSlugs={['u0']}
      />,
    )
    expect(screen.queryByRole('button', { name: '덱 1의 U0' })).not.toBeInTheDocument()

    // Refill the emptied seat with a different unit so the deck is complete
    // again, then submit.
    dropOnDeck(1, 'u5')
    await user.click(screen.getByRole('button', { name: /인카운터/ }))

    expect(evaluateDecks).toHaveBeenCalledWith(
      expect.objectContaining({
        roster: roster.filter((n) => n.character_slug !== 'u0'),
        decks: [{ units: ['u1', 'u2', 'u3', 'u4', 'u5'], boss: expect.anything() }],
      }),
      expect.any(AbortSignal),
    )
  })

  it('보스 필드가 하나라도 유효하지 않으면 15칸을 다 채워도 제출을 막는다', async () => {
    const user = userEvent.setup()
    renderPanel()
    await screen.findByRole('button', { name: /u0 배치/i }) // palette rendered
    for (let deck = 0; deck < 3; deck += 1) {
      for (let seat = 0; seat < 5; seat += 1) {
        dropOnDeck(deck + 1, `u${deck * 5 + seat}`)
      }
    }
    expect(screen.getByRole('button', { name: /인카운터/ })).toBeEnabled()

    const groups = screen.getAllByRole('group', { name: /전투/ })
    const fightDuration = within(groups[1]).getByLabelText(/전투 시간/)
    await user.clear(fightDuration)
    await user.type(fightDuration, '0')

    expect(screen.getByRole('button', { name: /인카운터/ })).toBeDisabled()
  })

  it('실행 버튼이 덱 컬럼 안에 있어 편성과 함께 화면에 남는다', async () => {
    renderPanel()

    expect(
      screen.getByRole('button', { name: /인카운터/ }).closest('.draft-layout__decks'),
    ).not.toBeNull()
  })

  // 팔레트는 DraftEditor 밖에 있어서, 든 유닛이 있을 때 팔레트를 누르면
  // "빈자리에 앉히기"가 아니라 "든 자리를 대신 채우기"가 되어야 한다.
  it('덱에서 유닛을 들고 팔레트의 다른 유닛을 누르면 자리를 바꾼다', async () => {
    const user = userEvent.setup()
    renderPanel()
    await screen.findByRole('button', { name: /u0 배치/i })
    // u0를 덱 1에 앉힌다.
    await user.click(screen.getByRole('button', { name: /u0 배치/i }))
    // 그 좌석을 든다.
    await user.click(screen.getByRole('button', { name: /덱 1의 U0/ }))
    // 팔레트에서 다른 유닛을 누른다.
    await user.click(screen.getByRole('button', { name: /u1 배치/i }))

    expect(screen.getByRole('button', { name: /덱 1의 U1/ })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /덱 1의 U0/ })).not.toBeInTheDocument()
    // u0는 풀로 돌아가 다시 배치할 수 있다.
    expect(screen.getByRole('button', { name: /u0 배치/i })).toBeEnabled()
  })

  // 답은 보스 설정 바로 아래에 선다. 편성 칸을 스크롤해 지나야 결과가 나오면
  // 안 된다.
  it('결과를 편성 위에 그린다', async () => {
    const user = userEvent.setup()
    vi.mocked(evaluateDecks).mockResolvedValue({
      decks: [
        { deck: ['u0', 'u1', 'u2', 'u3', 'u4'], total_damage: 10, burst_damage: 6, normal_attack_damage: 4, skill_damage: 0, hold_burst_slugs: [] },
        { deck: ['u5', 'u6', 'u7', 'u8', 'u9'], total_damage: 20, burst_damage: 12, normal_attack_damage: 8, skill_damage: 0, hold_burst_slugs: [] },
        { deck: ['u10', 'u11', 'u12', 'u13', 'u14'], total_damage: 30, burst_damage: 18, normal_attack_damage: 12, skill_damage: 0, hold_burst_slugs: [] },
      ],
      combined_total_damage: 60,
      excluded_slugs: [],
      engine_version: 'test-engine-version',
    })

    renderPanel()
    await screen.findByRole('button', { name: /u0 배치/i })
    for (let deck = 0; deck < 3; deck += 1) {
      for (let seat = 0; seat < 5; seat += 1) {
        dropOnDeck(deck + 1, `u${deck * 5 + seat}`)
      }
    }
    await user.click(screen.getByRole('button', { name: /인카운터/ }))

    const results = (await screen.findByText('1번 덱 · 무속성')).closest('ol')!
    const roster = screen.getByRole('group', { name: /편성/ })

    expect(results.compareDocumentPosition(roster) & Node.DOCUMENT_POSITION_FOLLOWING)
      .toBeTruthy()
  })
})

describe('UnionRaidPanel 결과 보관', () => {
  const evaluationSuccess = () => {
    vi.mocked(evaluateDecks).mockResolvedValue({
      decks: [
        { deck: ['u0', 'u1', 'u2', 'u3', 'u4'], total_damage: 10, burst_damage: 6, normal_attack_damage: 4, skill_damage: 0, hold_burst_slugs: [] },
        { deck: ['u5', 'u6', 'u7', 'u8', 'u9'], total_damage: 20, burst_damage: 12, normal_attack_damage: 8, skill_damage: 0, hold_burst_slugs: [] },
        { deck: ['u10', 'u11', 'u12', 'u13', 'u14'], total_damage: 30, burst_damage: 18, normal_attack_damage: 12, skill_damage: 0, hold_burst_slugs: [] },
      ],
      combined_total_damage: 60,
      excluded_slugs: [],
      engine_version: 'test-engine-version',
    })
  }

  it('결과가 없으면 저장 버튼도 없다', () => {
    renderPanel()

    expect(screen.queryByRole('button', { name: '저장' })).not.toBeInTheDocument()
  })

  // 솔로 탭의 보관물과 한 목록에 섞이지 않게 하는 것이 이 필드다.
  it('유니온 결과는 유니온 몫으로 남는다', async () => {
    const user = userEvent.setup()
    evaluationSuccess()
    const saved: SavedRun[] = []
    renderPanel({
      onSaveRun: (run: SavedRun) => {
        saved.push(run)
        return true
      },
    })

    await fillAndSubmit(user)
    await screen.findByText('1번 덱 · 무속성')
    await user.click(screen.getByRole('button', { name: '저장' }))
    await user.click(screen.getByRole('button', { name: '확인' }))

    expect(saved).toHaveLength(1)
    expect(saved[0].tab).toBe('union')
    expect(saved[0].view).toMatchObject({ numBattles: 3 })
  })

  // 제안 이름은 숫자를 낸 그 보스를 불러야 한다 - 화면의 결과 카드가 제출
  // 시점 스냅샷을 쓰는 것과 같은 이유다. 결과가 나온 뒤 보스를 만지면 숫자는
  // 옛 보스의 것인데 이름만 새 보스를 불러, 목록에서 고를 때 거짓말이 된다.
  it('저장 이름은 제출 시점 보스를 부른다 - 그 뒤에 보스를 바꿔도 따라가지 않는다', async () => {
    const user = userEvent.setup()
    evaluationSuccess()
    renderPanel()

    await screen.findByRole('button', { name: /u0 배치/i })
    for (let deck = 0; deck < 3; deck += 1) {
      for (let seat = 0; seat < 5; seat += 1) {
        dropOnDeck(deck + 1, `u${deck * 5 + seat}`)
      }
    }
    const battles = () => screen.getAllByRole('group', { name: /전투/ })
    await user.click(within(battles()[0]).getByLabelText('풍압'))
    await user.click(within(battles()[1]).getByLabelText('전격'))
    await user.click(within(battles()[2]).getByLabelText('작열'))
    await user.click(screen.getByRole('button', { name: /인카운터/ }))
    await screen.findByRole('button', { name: '저장' })

    // 결과가 나온 뒤 1번 전투의 보스만 바꾼다. 화면의 숫자는 그대로 옛 보스의
    // 것이다 - 다시 제출하지 않았으니까.
    await user.click(within(battles()[0]).getByLabelText('작열'))

    await user.click(screen.getByRole('button', { name: '저장' }))
    expect(screen.getByLabelText('이름')).toHaveValue('풍압 전격 작열')
  })

  it('보관한 유니온 결과를 열면 그때의 세 덱을 다시 그린다', async () => {
    const user = userEvent.setup()
    const boss = {
      element: null,
      core_hittable: false,
      pierce_hits_body_behind_core: false,
      enemy_def: 0,
      fight_duration: 180,
      part_destructible: false,
      effective_range_band: null,
      elemental_interrupt_required: false,
    }
    renderPanel({
      savedRuns: [
        {
          id: 'r1',
          name: '지난 주 유니온',
          savedAt: 1754438400000,
          tab: 'union' as const,
          view: {
            numBattles: 3,
            bosses: [boss, boss, boss],
            draft: { decks: [[], [], []] },
            decks: [
              { deck: ['u0', 'u1', 'u2', 'u3', 'u4'], total_damage: 888, burst_damage: 500, normal_attack_damage: 300, skill_damage: 88, hold_burst_slugs: [] },
            ],
            combinedTotalDamage: 888,
            excludedSlugs: [],
          },
        },
      ],
    })

    await user.click(screen.getByRole('button', { name: /지난 주 유니온/ }))

    expect(screen.getByText('888 총딜')).toBeInTheDocument()
  })
})

describe('UnionRaidPanel — 편성 초기화와 가져오기', () => {
  const bossOf = (element: 'Fire' | 'Water') => ({
    element,
    core_hittable: false,
    pierce_hits_body_behind_core: false,
    enemy_def: 31784,
    fight_duration: 180,
    part_destructible: false,
    core_diameter_px: null,
    effective_range_band: null,
    elemental_interrupt_required: false,
  })

  const deckOf = (slugs: string[]) => ({
    deck: slugs,
    total_damage: 10,
    burst_damage: 4,
    normal_attack_damage: 3,
    skill_damage: 3,
    hold_burst_slugs: [],
  })

  /** 두 전투짜리 보관물. */
  const unionRun = (): SavedRun => ({
    id: 'u1',
    name: '보관한 유니온',
    savedAt: 1754438400000,
    tab: 'union',
    view: {
      numBattles: 2,
      bosses: [bossOf('Water'), bossOf('Fire')],
      draft: {
        decks: [
          ['u0', 'u1', 'u2', 'u3', 'u4'].map((slug) => ({ slug, locked: false })),
          ['u5', 'u6', 'u7', 'u8', 'u9'].map((slug) => ({ slug, locked: false })),
        ],
      },
      decks: [
        deckOf(['u0', 'u1', 'u2', 'u3', 'u4']),
        deckOf(['u5', 'u6', 'u7', 'u8', 'u9']),
      ],
      combinedTotalDamage: 20,
      excludedSlugs: [],
    },
  })

  it('가져오면 전투 수·보스·편성이 함께 들어온다', async () => {
    const user = userEvent.setup()
    renderPanel({ savedRuns: [unionRun()] })

    await user.click(screen.getByRole('button', { name: '결과 가져오기' }))
    await user.click(screen.getByRole('button', { name: '가져오기' }))

    expect(screen.getByLabelText('전투 수')).toHaveValue('2')
    // 덱 제목은 속성이 있으면 약점 낱말이 된다(bossHeading). 'Water' 보스의
    // 약점은 '전격', 'Fire' 보스의 약점은 '수냉'이다. 기본 보스는
    // element: null이라 제목이 '덱 N'이므로, 제목이 바뀌었다는 것 자체가
    // 보스가 들어왔다는 증거다.
    const deck1 = screen.getByRole('heading', { name: /전격/ }).closest('div')!
    expect(within(deck1).getByText('U0')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /수냉/ })).toBeInTheDocument()
  })

  // 편성을 갈아치웠는데 옛 편성의 결과 숫자가 화면에 남으면 거짓말이 된다 -
  // 가져오기는 evaluation.reset()으로 그 결과를 내려야 한다.
  it('가져오기는 이전 평가 결과를 화면에서 내린다', async () => {
    const user = userEvent.setup()
    vi.mocked(evaluateDecks).mockResolvedValue({
      decks: [
        { deck: ['u0', 'u1', 'u2', 'u3', 'u4'], total_damage: 10, burst_damage: 6, normal_attack_damage: 4, skill_damage: 0, hold_burst_slugs: [] },
        { deck: ['u5', 'u6', 'u7', 'u8', 'u9'], total_damage: 20, burst_damage: 12, normal_attack_damage: 8, skill_damage: 0, hold_burst_slugs: [] },
        { deck: ['u10', 'u11', 'u12', 'u13', 'u14'], total_damage: 30, burst_damage: 18, normal_attack_damage: 12, skill_damage: 0, hold_burst_slugs: [] },
      ],
      combined_total_damage: 60,
      excluded_slugs: [],
      engine_version: 'test-engine-version',
    })
    renderPanel({ savedRuns: [unionRun()] })

    await fillAndSubmit(user)
    expect(await screen.findByText('총합:', { exact: false })).toBeInTheDocument()

    // 이미 앉은 유닛이 있어 가져오기가 덮어쓰기 확인을 묻는다.
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    await user.click(screen.getByRole('button', { name: '결과 가져오기' }))
    await user.click(screen.getByRole('button', { name: '가져오기' }))
    vi.mocked(window.confirm).mockRestore()

    expect(screen.queryByText('총합:', { exact: false })).not.toBeInTheDocument()
  })

  it('전체 초기화는 편성만 비운다', async () => {
    const user = userEvent.setup()
    renderPanel()
    await fillDecks()

    vi.spyOn(window, 'confirm').mockReturnValue(true)
    await user.click(screen.getByRole('button', { name: '초기화' }))

    expect(screen.getByRole('button', { name: /인카운터/ })).toBeDisabled()
    expect(screen.getByLabelText('전투 수')).toHaveValue('3')
    vi.mocked(window.confirm).mockRestore()
  })

  it('저장한 결과가 없으면 가져오기를 누를 수 없다', () => {
    renderPanel()

    expect(screen.getByRole('button', { name: '결과 가져오기' })).toBeDisabled()
  })
})

describe('suggestUnionRunName', () => {
  const boss = (element: BossElement) => ({ ...makeDefaultBossProfileDraft(), element })

  it('덱 순서대로 약점을 나열한다', () => {
    expect(suggestUnionRunName([boss('Fire'), boss('Water'), boss('Iron')])).toBe(
      '수냉 전격 풍압',
    )
  })

  it('속성을 안 고른 덱도 자리를 지킨다', () => {
    expect(suggestUnionRunName([boss('Fire'), boss(null), boss('Fire')])).toBe(
      '수냉 약점없음 수냉',
    )
  })

  it('날짜를 붙이지 않는다 - 목록이 저장 시각을 따로 찍는다', () => {
    expect(suggestUnionRunName([boss('Fire')])).toBe('수냉')
  })
})
