import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { SyncRosterPanel } from './SyncRosterPanel'
import { assembleRoster } from '../api/assembleRoster'
import { takeSyncInbox } from '../api/syncInbox'

// This codebase's mocking convention is vi.mock + vi.mocked (see
// useBookmarkletImport.test.ts) - ESM named exports can't be intercepted with
// vi.spyOn.
vi.mock('../api/syncInbox', () => ({ takeSyncInbox: vi.fn() }))

// 앱은 네이티브 창이라 북마크 바가 없다 - 북마크릿은 드래그가 아니라 복사로
// 건네므로, 검사 대상은 링크의 href가 아니라 클립보드에 들어간 값이다.
const copied: string[] = []
vi.stubGlobal('navigator', {
  ...navigator,
  clipboard: { writeText: (text: string) => { copied.push(text); return Promise.resolve() } },
})
const copyBookmarklet = () =>
  fireEvent.click(screen.getByRole('button', { name: /북마크릿 주소 복사/ }))
vi.mock('../api/assembleRoster', () => ({
  assembleRoster: vi.fn(),
}))

const uid = btoa('29080-1234567890123456789')
const shareUrl = `https://www.blablalink.com/shiftyspad?uid=${uid}`
const uid2 = btoa('29080-1111111111111111111')
const shareUrl2 = `https://www.blablalink.com/shiftyspad?uid=${uid2}`

// open_id는 프로필의 키라 없으면 import 자체가 거절된다 - 이 파일의 테스트들은
// 그 뒤의 파싱/표시를 보는 것이므로 유효한 값을 달고 출발한다.
const RAW_PAYLOAD = {
  open_id: 'abc123',
  owned: [],
  character_details: [],
  recycle_room_researches: [],
}

// 북마크릿이 인박스에 두고 간 상태를 만든다. 패널의 훅이 마운트하자마자
// 확인하므로 render 앞에서 부른다.
const postPayload = () =>
  vi.mocked(takeSyncInbox).mockResolvedValueOnce(RAW_PAYLOAD)

const postTwoServers = () =>
  vi.mocked(takeSyncInbox).mockResolvedValueOnce({
    open_id: 'abc123',
    servers: [
      { area: 81, nickname: 'FIENN', owned: [{ name_code: 1 }, { name_code: 2 }], character_details: [], recycle_room_researches: [] },
      { area: 83, nickname: 'FIENN', owned: [{ name_code: 3 }], character_details: [], recycle_room_researches: [] },
    ],
  })


afterEach(() => vi.mocked(assembleRoster).mockReset())

describe('SyncRosterPanel', () => {
  it('공유 URL을 넣으면 북마크릿을 복사할 수 있다', () => {
    copied.length = 0
    render(<SyncRosterPanel onImport={vi.fn()} />)
    fireEvent.change(screen.getByLabelText(/공유 url/i), {
      target: { value: shareUrl },
    })

    copyBookmarklet()

    expect(copied).toHaveLength(1)
    expect(copied[0]).toContain('javascript:')
    expect(copied[0]).toContain('1234567890123456789')
  })

  it('잘못된 URL은 에러를 보여주고 링크를 만들지 않는다', () => {
    render(<SyncRosterPanel onImport={vi.fn()} />)
    fireEvent.change(screen.getByLabelText(/공유 url/i), {
      target: { value: 'https://example.com' },
    })
    expect(screen.getByRole('alert')).toBeTruthy()
    expect(screen.queryByRole('link', { name: /로스터/i })).toBeNull()
  })

  it('delivers a payload through parseRosterJson to onImport and shows the summary', async () => {
    vi.mocked(assembleRoster).mockResolvedValueOnce({
      units: [
        {
          name_en: 'Rapunzel',
          raid400: { hp: 100000, atk: 20000, def: 5000 },
        },
      ],
    })
    const onImport = vi.fn()
    postPayload()
    render(<SyncRosterPanel onImport={onImport} />)

    await waitFor(() => expect(onImport).toHaveBeenCalledTimes(1))
    expect(onImport.mock.calls[0][0].roster).toHaveLength(1)
    expect(screen.getByText('1기 동기화됨')).toBeTruthy()
  })

  it('separates open_id/nickname from the assembled roster when calling onImport', async () => {
    vi.mocked(assembleRoster).mockResolvedValueOnce({ units: [] })
    const onImport = vi.fn()
    vi.mocked(takeSyncInbox).mockResolvedValueOnce({
      ...RAW_PAYLOAD, open_id: 'abc123', nickname: 'Fienn',
    })

    render(<SyncRosterPanel onImport={onImport} />)

    await waitFor(() => expect(onImport).toHaveBeenCalledTimes(1))
    expect(onImport.mock.calls[0][0].openId).toBe('abc123')
    expect(onImport.mock.calls[0][0].nickname).toBe('Fienn')
    // The legacy flat payload (no `servers` array) is a single-server account -
    // promoted to area 81 (JP), same as the profile store's own migration.
    expect(onImport.mock.calls[0][0].area).toBe(81)
  })

  it('surfaces parse warnings (e.g. unsupported owned units) as note paragraphs', async () => {
    vi.mocked(assembleRoster).mockResolvedValueOnce({
      units: [
        {
          resource_id: 999999, // not in RESOURCE_ID_TO_SLUG -> unsupported
          name_en: 'Not Encoded Unit',
          raid400: { hp: 1, atk: 2, def: 3 },
        },
      ],
    })
    const onImport = vi.fn()
    postPayload()
    render(<SyncRosterPanel onImport={onImport} />)

    await waitFor(() => expect(onImport).toHaveBeenCalledTimes(1))
    expect(
      await screen.findByText(/보유 유닛 중 1기가 아직 미지원/),
    ).toBeInTheDocument()
    expect(screen.getByText(/Not Encoded Unit/)).toBeInTheDocument()
  })

  it('clears the summary and link when the input is cleared', async () => {
    vi.mocked(assembleRoster).mockResolvedValueOnce({ units: [] })
    const onImport = vi.fn()
    // 인박스는 마운트 직후 한 번 확인된다 - 로스터는 화면이 뜬 시점에 이미
    // 들어와 있고, 이 테스트가 보는 것은 그 뒤 입력을 비웠을 때의 정리다.
    postPayload()

    render(<SyncRosterPanel onImport={onImport} />)
    const input = screen.getByLabelText(/공유 url/i)

    fireEvent.change(input, { target: { value: shareUrl } })
    expect(screen.getByRole('button', { name: /북마크릿 주소 복사/ })).toBeTruthy()

    await waitFor(() => expect(screen.getByText('0기 동기화됨')).toBeTruthy())

    fireEvent.change(input, { target: { value: '' } })
    expect(screen.queryByText('0기 동기화됨')).toBeNull()
    expect(screen.queryByRole('button', { name: /북마크릿 주소 복사/ })).toBeNull()
  })

  it('다른 공유 URL을 넣으면 그 계정의 북마크릿이 복사된다', () => {
    copied.length = 0
    render(<SyncRosterPanel onImport={vi.fn()} />)
    const input = screen.getByLabelText(/공유 url/i)

    fireEvent.change(input, { target: { value: shareUrl } })
    copyBookmarklet()
    expect(copied[0]).toContain('1234567890123456789')

    fireEvent.change(input, { target: { value: shareUrl2 } })
    copyBookmarklet()
    expect(copied[1]).toContain('1111111111111111111')
    expect(copied[1]).not.toContain('1234567890123456789')
  })

  it('주소를 바꾸면 앞의 "복사했어요"가 남지 않는다', async () => {
    // 남아 있으면 방금 만든 북마크가 최신인 줄 알게 된다.
    render(<SyncRosterPanel onImport={vi.fn()} />)
    const input = screen.getByLabelText(/공유 url/i)

    fireEvent.change(input, { target: { value: shareUrl } })
    copyBookmarklet()
    // 클립보드 쓰기는 프라미스라 상태 표시는 한 틱 뒤에 나온다.
    await waitFor(() => expect(screen.getByRole('status')).toBeInTheDocument())

    fireEvent.change(input, { target: { value: shareUrl2 } })
    expect(screen.queryByRole('status')).toBeNull()
  })

  it('도움말은 기본으로 접혀 있다', () => {
    render(<SyncRosterPanel onImport={vi.fn()} />)
    expect(screen.getByRole('button', { name: '동기화 방법' })).toHaveAttribute(
      'aria-expanded',
      'false',
    )
    expect(screen.getByText(/복사한 URL을 아래 칸에 붙여넣어요/)).not.toBeVisible()
  })

  it('동기화 방법 버튼을 누르면 도움말이 펼쳐진다', () => {
    render(<SyncRosterPanel onImport={vi.fn()} />)
    const toggle = screen.getByRole('button', { name: '동기화 방법' })

    fireEvent.click(toggle)

    expect(toggle).toHaveAttribute('aria-expanded', 'true')
    expect(screen.getByText(/복사한 URL을 아래 칸에 붙여넣어요/)).toBeVisible()
    // 라벨 없는 아이콘 두 개를 지목하는 것이 이 도움말의 존재 이유다.
    expect(screen.getByAltText(/공유 아이콘/)).toBeVisible()
    expect(screen.getByAltText(/링크 복사하기/)).toBeVisible()
  })

  it('defaultHelpOpen이면 처음부터 펼쳐져 있다', () => {
    render(<SyncRosterPanel onImport={vi.fn()} defaultHelpOpen />)
    expect(screen.getByRole('button', { name: '동기화 방법' })).toHaveAttribute(
      'aria-expanded',
      'true',
    )
    expect(screen.getByText(/계정마다 북마크가 따로 필요해요/)).toBeVisible()
  })

  it('서버가 둘이면 어느 것을 가져올지 묻고, 고르기 전엔 임포트하지 않는다', async () => {
    const onImport = vi.fn()
    postTwoServers()

    render(<SyncRosterPanel onImport={onImport} />)

    expect(await screen.findByText(/어느 서버의 계정을 가져올까요/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /JP \(2기\)/ })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /KR \(1기\)/ })).toBeInTheDocument()
    expect(onImport).not.toHaveBeenCalled()
  })

  it('고른 서버의 area가 onImport로 넘어간다', async () => {
    const user = userEvent.setup()
    vi.mocked(assembleRoster).mockResolvedValueOnce({ units: [] })
    const onImport = vi.fn()
    postTwoServers()

    render(<SyncRosterPanel onImport={onImport} />)

    await user.click(await screen.findByRole('button', { name: /KR \(1기\)/ }))

    await waitFor(() => expect(onImport).toHaveBeenCalledOnce())
    expect(onImport.mock.calls[0][0].area).toBe(83)
  })
})
