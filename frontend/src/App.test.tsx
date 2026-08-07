import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { renderSettled } from './test/renderSettled'
import App from './App'
import { makeEmptyDraft, type NikkeDraft } from './types/nikkeDraft'
import { profileKey, type ProfilesState } from './types/profile'
import { HELP } from './lib/helpText'

vi.mock('./api/recommendRaid', () => ({
  recommendRaidDecks: vi.fn(),
}))
vi.mock('./api/supportedUnits', () => ({
  getSupportedUnits: vi.fn(),
}))
vi.mock('./api/raidRotations', () => ({
  getRaidRotations: vi.fn(),
}))

import { recommendRaidDecks } from './api/recommendRaid'
import { getSupportedUnits } from './api/supportedUnits'
import { getRaidRotations } from './api/raidRotations'
import type { RaidRotation } from './types/raidRotation'

const validDraft = (overrides: Partial<NikkeDraft> = {}): NikkeDraft => ({
  ...makeEmptyDraft(),
  character_slug: 'red-hood',
  level: '200',
  hp: '1000000',
  atk: '85000',
  def_: '12000',
  skill_levels: { skill1: '10', skill2: '7', burst: '4' },
  ...overrides,
})

// RecommendPanel's raid mode requires MIN_DECK_ROSTER_SIZE (5) ready Nikkes
// before its submit button enables.
const fiveValidDrafts = (slugPrefix: string): NikkeDraft[] =>
  Array.from({ length: 5 }, (_, i) => validDraft({ character_slug: `${slugPrefix}-${i}` }))

const seedProfiles = (state: ProfilesState) => {
  localStorage.setItem('nikke-profiles', JSON.stringify(state))
}

const ACCT_A = profileKey('acct-a', 81)
const ACCT_B = profileKey('acct-b', 81)

beforeEach(() => {
  localStorage.clear()
  vi.mocked(getSupportedUnits).mockResolvedValue([])
  vi.mocked(getRaidRotations).mockResolvedValue([])
})

afterEach(() => {
  vi.mocked(recommendRaidDecks).mockReset()
  vi.mocked(getSupportedUnits).mockReset()
  vi.mocked(getRaidRotations).mockReset()
})

describe('App', () => {
  it('앱 이름을 RapiLab으로 내건다', async () => {
    await renderSettled(<App />)
    expect(screen.getByRole('heading', { level: 1, name: 'RapiLab' })).toBeInTheDocument()
  })

  it('states the harmony cube assumption, and whose it is', async () => {
    // The 계산기 tab asks which cube the unit wears, so an unqualified "every
    // Nikke wears a reload cube" is a claim the app contradicts on that screen.
    await renderSettled(<App />)
    expect(screen.getByText(/덱 추천은 .*재장전 큐브 15레벨/i)).toBeInTheDocument()
  })

  it('prompts to sync and hides the roster/recommend panel when there is no active profile', async () => {
    await renderSettled(<App />)
    expect(screen.getByText(/동기화된 계정이 없어요/i)).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: '솔로 레이드' })).not.toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'red-hood' })).not.toBeInTheDocument()
  })

  it('팬 제작물 고지는 접히지 않고 늘 떠 있다', async () => {
    // 펼쳐야 보이는 고지는 고지가 아니다 - 개인정보 안내와 달리 이것은
    // 클릭 없이 읽혀야 한다.
    await renderSettled(<App />)

    for (const line of HELP.attribution) {
      expect(screen.getByText(line)).toBeVisible()
    }
  })

  it('개인정보 안내는 아직 동기화하지 않은 화면에도 있다', async () => {
    // 계정을 맡길지 정하는 순간이 바로 이때다. 푸터를 프로필이 있을 때만
    // 그리면, 그 안내는 이미 맡긴 사람에게만 보인다.
    await renderSettled(<App />)

    expect(screen.getByText('개인정보 처리방침')).toBeInTheDocument()
    expect(screen.queryByText(/기 준비 완료/)).not.toBeInTheDocument()
  })

  // The roster grid cards a unit only once /api/supported-units confirms the
  // engine can simulate it, so these have to wait for that list to land.
  const SUPPORTED = [
    { slug: 'red-hood', name: 'Red Hood', burstTier: 1, element: 'Fire' },
    { slug: 'privaty', name: 'Privaty', burstTier: 2, element: 'Water' },
  ] as const

  it('opens on the roster tab and reaches the recommend panel through its tab', async () => {
    const user = userEvent.setup()
    vi.mocked(getSupportedUnits).mockResolvedValue([...SUPPORTED])
    seedProfiles({
      activeKey: ACCT_A,
      profiles: {
        [ACCT_A]: {
          openId: 'acct-a',
          area: 81,
          nickname: '본계',
          roster: [validDraft()],
          results: {},
          lastResultHash: null,
          lastInputs: null,
          savedRuns: [],
        },
      },
    })

    render(<App />)

    expect(await screen.findByRole('heading', { name: 'Red Hood' })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: '솔로 레이드' })).not.toBeInTheDocument()

    await user.click(screen.getByRole('tab', { name: '솔로 레이드' }))

    expect(screen.getByRole('heading', { name: '솔로 레이드' })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Red Hood' })).not.toBeInTheDocument()
  })

  it('renders five tabs and reaches the union raid panel through its own tab', async () => {
    const user = userEvent.setup()
    vi.mocked(getSupportedUnits).mockResolvedValue([...SUPPORTED])
    seedProfiles({
      activeKey: ACCT_A,
      profiles: {
        [ACCT_A]: {
          openId: 'acct-a',
          area: 81,
          nickname: '본계',
          roster: [validDraft()],
          results: {},
          lastResultHash: null,
          lastInputs: null,
          savedRuns: [],
        },
      },
    })

    render(<App />)
    expect(screen.getAllByRole('tab')).toHaveLength(5)
    expect(screen.queryByRole('heading', { name: '유니온 레이드' })).not.toBeInTheDocument()

    await user.click(screen.getByRole('tab', { name: '유니온 레이드' }))

    expect(screen.getByRole('heading', { name: '유니온 레이드' })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Red Hood' })).not.toBeInTheDocument()
  })

  const ROTATIONS: RaidRotation[] = [
    {
      id: 'solo-39',
      raid: 'solo',
      title: '솔로 레이드 39시즌',
      starts_at: '2026-07-16T12:00:00+09:00',
      ends_at: '2026-07-23T04:59:00+09:00',
      source_url: 'https://arca.live/b/nikketgv/177017741',
      source_locale: 'ko',
      read_on: '2026-08-07',
      bosses: [{ name: '아일랜드 이터', weakness: 'Iron', stated: {} }],
    },
    {
      id: 'union-2026-07-31',
      raid: 'union',
      title: '유니온 레이드 7/31',
      starts_at: '2026-07-31T05:00:00+09:00',
      ends_at: '2026-08-06T04:59:00+09:00',
      source_url: 'https://arca.live/b/nikketgv/177833660',
      source_locale: 'ko',
      read_on: '2026-08-07',
      bosses: [{ name: '선바스', weakness: 'Electric', stated: {} }],
    },
  ]

  it('탭마다 그 레이드의 회차 보스만 뜬다', async () => {
    const user = userEvent.setup()
    vi.mocked(getSupportedUnits).mockResolvedValue([...SUPPORTED])
    vi.mocked(getRaidRotations).mockResolvedValue([...ROTATIONS])
    seedProfiles({
      activeKey: ACCT_A,
      profiles: {
        [ACCT_A]: {
          openId: 'acct-a',
          area: 81,
          nickname: '본계',
          roster: [validDraft()],
          results: {},
          lastResultHash: null,
          lastInputs: null,
          savedRuns: [],
        },
      },
    })

    render(<App />)

    await user.click(screen.getByRole('tab', { name: '솔로 레이드' }))
    expect(await screen.findByRole('radio', { name: '철갑아일랜드 이터' })).toBeInTheDocument()
    expect(screen.queryByRole('radio', { name: '전격선바스' })).not.toBeInTheDocument()

    await user.click(screen.getByRole('tab', { name: '유니온 레이드' }))
    // 유니온 탭은 전투마다 자기 몫의 카드 목록을 그린다(기본 3전투) - 같은
    // 회차라 보스 카드가 전투 수만큼 반복되므로 한 전투로 좁혀서 본다.
    const firstBattle = screen.getByRole('group', { name: '1번 전투' })
    expect(within(firstBattle).getByRole('radio', { name: '전격선바스' })).toBeInTheDocument()
    expect(screen.queryByRole('radio', { name: '철갑아일랜드 이터' })).not.toBeInTheDocument()
  })

  it('switches the displayed roster when the active profile changes (isolation)', async () => {
    const user = userEvent.setup()
    vi.mocked(getSupportedUnits).mockResolvedValue([...SUPPORTED])
    seedProfiles({
      activeKey: ACCT_A,
      profiles: {
        [ACCT_A]: {
          openId: 'acct-a',
          area: 81,
          nickname: '본계',
          roster: [validDraft({ character_slug: 'red-hood' })],
          results: {},
          lastResultHash: null,
          lastInputs: null,
          savedRuns: [],
        },
        [ACCT_B]: {
          openId: 'acct-b',
          area: 81,
          nickname: '부계',
          roster: [validDraft({ character_slug: 'privaty' })],
          results: {},
          lastResultHash: null,
          lastInputs: null,
          savedRuns: [],
        },
      },
    })

    render(<App />)
    expect(await screen.findByRole('heading', { name: 'Red Hood' })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Privaty' })).not.toBeInTheDocument()

    await user.selectOptions(screen.getByLabelText('계정'), '부계 (JP)')

    expect(screen.getByRole('heading', { name: 'Privaty' })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Red Hood' })).not.toBeInTheDocument()
  })

  it('resets in-flight raid state and form mode when switching profiles (RecommendPanel is remounted per profile)', async () => {
    const user = userEvent.setup()
    // Never resolves during the test - if the profile-keyed remount didn't
    // isolate RecommendPanel's useRecommendRaid instance, this promise
    // landing later could leak profile A's loading/result into profile B.
    vi.mocked(recommendRaidDecks).mockImplementation(() => new Promise(() => {}))

    seedProfiles({
      activeKey: ACCT_A,
      profiles: {
        [ACCT_A]: {
          openId: 'acct-a',
          area: 81,
          nickname: '본계',
          roster: fiveValidDrafts('a'),
          results: {},
          lastResultHash: null,
          lastInputs: null,
          savedRuns: [],
        },
        [ACCT_B]: {
          openId: 'acct-b',
          area: 81,
          nickname: '부계',
          roster: fiveValidDrafts('b'),
          results: {},
          lastResultHash: null,
          lastInputs: null,
          savedRuns: [],
        },
      },
    })

    render(<App />)
    await user.click(screen.getByRole('tab', { name: '솔로 레이드' }))
    await user.click(screen.getByLabelText(/전부 최적화/i))
    await user.click(
      within(document.getElementById('panel-recommend')!).getByRole('button', {
        name: /인카운터/,
      }),
    )
    expect(await screen.findByRole('status')).toHaveTextContent(/2~5분/)
    expect(screen.getByLabelText(/전부 최적화/i)).toBeChecked()

    await user.selectOptions(screen.getByLabelText('계정'), '부계 (JP)')

    // A fresh RecommendPanel instance: no in-flight status banner (a new
    // useRecommendRaid, not the one A's never-resolving promise still
    // targets) and mode reset to its 'single' default - proof of a full
    // remount, not just the restore effect (which never touches `mode`).
    expect(screen.queryByRole('status')).not.toBeInTheDocument()
    expect(screen.getByLabelText(/단일 덱/i)).toBeChecked()
  })

  it('drops a computed charge ladder when switching profiles (ChargeWindowPanel is remounted per profile)', async () => {
    const user = userEvent.setup()
    const outcome = {
      low_shots: 18, low_probability: 0.132, high_shots: 19, high_probability: 0.868,
    }
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({
        interval: 0.53,
        magazine: 22,
        charge_speed_percent: 0,
        current: outcome,
        thresholds: [{ charge_speed_percent: 0, interval: 0.53, outcome }],
        notes: [],
      }),
    }))
    seedProfiles({
      activeKey: ACCT_A,
      profiles: {
        [ACCT_A]: {
          openId: 'acct-a',
          area: 81,
          nickname: '본계',
          roster: [validDraft({ character_slug: 'scarlet-black-shadow' })],
          results: {},
          lastResultHash: null,
          lastInputs: null,
          savedRuns: [],
        },
        [ACCT_B]: {
          openId: 'acct-b',
          area: 81,
          nickname: '부계',
          roster: [validDraft({ character_slug: 'scarlet-black-shadow' })],
          results: {},
          lastResultHash: null,
          lastInputs: null,
          savedRuns: [],
        },
      },
    })

    render(<App />)
    await user.click(screen.getByRole('tab', { name: '계산기' }))
    await user.click(screen.getByRole('button', { name: '계산' }))
    expect(await screen.findByText(/탄창 22발/)).toBeInTheDocument()

    await user.selectOptions(screen.getByLabelText('계정'), '부계 (JP)')

    // Account A's ladder is A's roster's answer. Without the profile key the
    // panel keeps its result state and shows it against B's roster.
    expect(screen.queryByText(/탄창 22발/)).not.toBeInTheDocument()
    vi.unstubAllGlobals()
  })

  it('keeps an in-flight raid alive across a tab switch', async () => {
    const user = userEvent.setup()
    // A raid allocation runs 1-2 minutes. Looking at the roster mid-run is a
    // normal thing to do, and it must not abandon the request: the panel is
    // hidden on tab switch, never unmounted.
    vi.mocked(recommendRaidDecks).mockImplementation(() => new Promise(() => {}))

    seedProfiles({
      activeKey: ACCT_A,
      profiles: {
        [ACCT_A]: {
          openId: 'acct-a',
          area: 81,
          nickname: '본계',
          roster: fiveValidDrafts('a'),
          results: {},
          lastResultHash: null,
          lastInputs: null,
          savedRuns: [],
        },
      },
    })

    render(<App />)
    await user.click(screen.getByRole('tab', { name: '솔로 레이드' }))
    await user.click(screen.getByLabelText(/전부 최적화/i))
    await user.click(
      within(document.getElementById('panel-recommend')!).getByRole('button', {
        name: /인카운터/,
      }),
    )
    expect(await screen.findByRole('status')).toHaveTextContent(/2~5분/)

    await user.click(screen.getByRole('tab', { name: '니케 풀' }))
    await user.click(screen.getByRole('tab', { name: '솔로 레이드' }))

    // Still running, and still in raid mode - a remount would have reset both.
    expect(screen.getByRole('status')).toHaveTextContent(/2~5분/)
    expect(screen.getByLabelText(/전부 최적화/i)).toBeChecked()
    expect(vi.mocked(recommendRaidDecks)).toHaveBeenCalledTimes(1)
  })

  it('활성 프로필이 없는 화면에서는 동기화 도움말이 펼쳐져 있다', async () => {
    await renderSettled(<App />)
    expect(screen.getByRole('button', { name: '동기화 방법' })).toHaveAttribute(
      'aria-expanded',
      'true',
    )
  })

  it('이미 동기화한 계정이 있으면 동기화 탭의 도움말은 접혀 있다', async () => {
    const user = userEvent.setup()
    const OPEN_1 = profileKey('open-1', 81)
    seedProfiles({
      activeKey: OPEN_1,
      profiles: {
        [OPEN_1]: {
          openId: 'open-1',
          area: 81,
          nickname: 'Fienn',
          roster: [],
          results: {},
          lastResultHash: null,
          lastInputs: null,
          savedRuns: [],
        },
      },
    })
    render(<App />)
    await user.click(screen.getByRole('tab', { name: '동기화' }))
    expect(screen.getByRole('button', { name: '동기화 방법' })).toHaveAttribute(
      'aria-expanded',
      'false',
    )
  })

  it('동기화는 니케 풀이 아니라 자기 탭에 있다', async () => {
    const user = userEvent.setup()
    const OPEN_1 = profileKey('open-1', 81)
    seedProfiles({
      activeKey: OPEN_1,
      profiles: {
        [OPEN_1]: {
          openId: 'open-1',
          area: 81,
          nickname: 'Fienn',
          roster: [],
          results: {},
          lastResultHash: null,
          lastInputs: null,
          savedRuns: [],
        },
      },
    })
    render(<App />)

    // 탭 패널은 전부 마운트된 채 hidden으로만 감춰지므로, 문서에 있느냐가
    // 아니라 어느 패널 안에 있느냐를 본다.
    const rosterPanel = screen.getByRole('tabpanel', { name: '니케 풀' })
    expect(within(rosterPanel).queryByLabelText('ShiftyPad 공유 URL')).not.toBeInTheDocument()
    expect(screen.getByLabelText('ShiftyPad 공유 URL')).not.toBeVisible()

    await user.click(screen.getByRole('tab', { name: '동기화' }))
    expect(screen.getByLabelText('ShiftyPad 공유 URL')).toBeVisible()
  })
})

describe('계산기 탭', () => {
  const seedActiveProfile = () =>
    seedProfiles({
      activeKey: ACCT_A,
      profiles: {
        [ACCT_A]: {
          openId: 'acct-a',
          area: 81,
          nickname: '본계',
          roster: [validDraft()],
          results: {},
          lastResultHash: null,
          lastInputs: null,
          savedRuns: [],
        },
      },
    })

  it('is one of the tabs', async () => {
    seedActiveProfile()
    await renderSettled(<App />)
    expect(screen.getByRole('tab', { name: '계산기' })).toBeInTheDocument()
  })

  it('shows the calculator when selected', async () => {
    seedActiveProfile()
    render(<App />)
    await userEvent.click(screen.getByRole('tab', { name: '계산기' }))
    const panel = screen.getByRole('tabpanel', { name: '계산기' })
    expect(within(panel).getByLabelText('유닛')).toBeInTheDocument()
  })

  it('keeps the other panels mounted so a running request survives', async () => {
    seedActiveProfile()
    render(<App />)
    await userEvent.click(screen.getByRole('tab', { name: '계산기' }))
    // hidden, not unmounted - the same rule the recommend panel follows.
    // Identified by id rather than accessible name: dom-accessibility-api
    // computes the name of anything carrying the `hidden` attribute as "",
    // so getByRole's `name` filter can never match a hidden tabpanel.
    const recommendPanel = document.getElementById('panel-recommend')
    expect(recommendPanel).toHaveAttribute('aria-labelledby', 'tab-recommend')
    expect(recommendPanel).toHaveAttribute('hidden')
  })
})
