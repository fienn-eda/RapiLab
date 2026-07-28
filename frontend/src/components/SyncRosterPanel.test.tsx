import { render, screen, fireEvent, act, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { SyncRosterPanel } from './SyncRosterPanel'
import { assembleRoster } from '../api/assembleRoster'
import { BLABLALINK_ORIGIN, PAYLOAD_MESSAGE } from '../lib/bookmarklet'

// This codebase's mocking convention is vi.mock + vi.mocked (see
// useBookmarkletImport.test.ts) - ESM named exports can't be intercepted with
// vi.spyOn.
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

const postPayload = () =>
  act(() => {
    window.dispatchEvent(
      new MessageEvent('message', {
        origin: BLABLALINK_ORIGIN,
        data: { type: PAYLOAD_MESSAGE, payload: RAW_PAYLOAD },
      }),
    )
  })

afterEach(() => vi.mocked(assembleRoster).mockReset())

describe('SyncRosterPanel', () => {
  it('공유 URL을 넣으면 북마크릿 링크가 나온다', () => {
    render(<SyncRosterPanel onImport={vi.fn()} />)
    fireEvent.change(screen.getByLabelText(/공유 url/i), {
      target: { value: shareUrl },
    })
    const link = screen.getByRole('link', { name: /로스터/i })
    expect(link.getAttribute('href')).toContain('javascript:')
    expect(link.getAttribute('href')).toContain('1234567890123456789')
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
    render(<SyncRosterPanel onImport={onImport} />)

    postPayload()

    await waitFor(() => expect(onImport).toHaveBeenCalledTimes(1))
    expect(onImport.mock.calls[0][0].roster).toHaveLength(1)
    expect(screen.getByText('1기 동기화됨')).toBeTruthy()
  })

  it('separates open_id/nickname from the assembled roster when calling onImport', async () => {
    vi.mocked(assembleRoster).mockResolvedValueOnce({ units: [] })
    const onImport = vi.fn()
    render(<SyncRosterPanel onImport={onImport} />)

    act(() => {
      window.dispatchEvent(
        new MessageEvent('message', {
          origin: BLABLALINK_ORIGIN,
          data: {
            type: PAYLOAD_MESSAGE,
            payload: { ...RAW_PAYLOAD, open_id: 'abc123', nickname: 'Fienn' },
          },
        }),
      )
    })

    await waitFor(() => expect(onImport).toHaveBeenCalledTimes(1))
    expect(onImport.mock.calls[0][0].openId).toBe('abc123')
    expect(onImport.mock.calls[0][0].nickname).toBe('Fienn')
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
    render(<SyncRosterPanel onImport={onImport} />)

    postPayload()

    await waitFor(() => expect(onImport).toHaveBeenCalledTimes(1))
    expect(
      await screen.findByText(/보유 유닛 중 1기가 아직 미지원/),
    ).toBeInTheDocument()
    expect(screen.getByText(/Not Encoded Unit/)).toBeInTheDocument()
  })

  it('clears the summary and link when the input is cleared', async () => {
    vi.mocked(assembleRoster).mockResolvedValueOnce({ units: [] })
    const onImport = vi.fn()
    render(<SyncRosterPanel onImport={onImport} />)
    const input = screen.getByLabelText(/공유 url/i)

    fireEvent.change(input, { target: { value: shareUrl } })
    expect(screen.getByRole('link', { name: /로스터/i })).toBeTruthy()

    postPayload()
    await waitFor(() => expect(screen.getByText('0기 동기화됨')).toBeTruthy())

    fireEvent.change(input, { target: { value: '' } })
    expect(screen.queryByText('0기 동기화됨')).toBeNull()
    expect(screen.queryByRole('link', { name: /로스터/i })).toBeNull()
  })

  it('regenerates the bookmarklet link with the new open id when a different share URL is pasted', () => {
    render(<SyncRosterPanel onImport={vi.fn()} />)
    const input = screen.getByLabelText(/공유 url/i)

    fireEvent.change(input, { target: { value: shareUrl } })
    const firstHref = screen.getByRole('link', { name: /로스터/i }).getAttribute('href')
    expect(firstHref).toContain('1234567890123456789')

    fireEvent.change(input, { target: { value: shareUrl2 } })
    const secondHref = screen.getByRole('link', { name: /로스터/i }).getAttribute('href')
    expect(secondHref).toContain('1111111111111111111')
    expect(secondHref).not.toContain('1234567890123456789')
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
})
