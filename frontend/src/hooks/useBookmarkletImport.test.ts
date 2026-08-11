import { act, renderHook, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useBookmarkletImport } from './useBookmarkletImport'
import { takeSyncInbox } from '../api/syncInbox'
import { assembleRoster } from '../api/assembleRoster'

// 이 코드베이스의 모킹 관례는 vi.mock + vi.mocked다 (RecommendPanel.test.tsx 참고).
// ESM 명명 export는 vi.spyOn으로 가로챌 수 없다.
vi.mock('../api/assembleRoster', () => ({
  assembleRoster: vi.fn(),
}))
vi.mock('../api/syncInbox', () => ({ takeSyncInbox: vi.fn() }))

const EMPTY = { owned: [], character_details: [], recycle_room_researches: [] }

// 북마크릿이 인박스에 두고 간 상태를 만든다. 훅은 마운트하자마자 한 번
// 확인하므로 renderHook 앞에서 부른다.
const inbox = (payload: unknown) =>
  vi.mocked(takeSyncInbox).mockResolvedValueOnce(payload)

const server = (area: number, count: number, nickname = '') => ({
  area,
  nickname,
  owned: Array.from({ length: count }, (_, i) => ({ name_code: i + 1 })),
  character_details: [],
  recycle_room_researches: [],
})

beforeEach(() => {
  // 기본은 빈 인박스. 각 테스트가 inbox()로 하나를 넣는다.
  vi.mocked(takeSyncInbox).mockResolvedValue(null)
})
afterEach(() => {
  vi.mocked(assembleRoster).mockReset()
  vi.mocked(takeSyncInbox).mockReset()
})

describe('useBookmarkletImport', () => {
  it('blablalink에서 온 payload를 조립해 넘긴다', async () => {
    vi.mocked(assembleRoster).mockResolvedValue({ units: [] })
    const onRoster = vi.fn()
    inbox({ ...EMPTY, open_id: 'abc123' })

    renderHook(() => useBookmarkletImport(onRoster))

    await waitFor(() =>
      expect(onRoster).toHaveBeenCalledWith({
        openId: 'abc123',
        area: 81,
        nickname: '',
        nicknameError: '',
        raw: { units: [] },
      }),
    )
  })

  // open_id는 프로필의 키다. 없는 채로 통과시키면 빈 문자열로 키가 잡힌 계정이
  // 저장소에 생기는데, 그건 드롭다운에 이름 없는 칸으로 보이고 어느 계정인지
  // 알 수도 없다. 계정을 특정할 수 없으면 로스터도 받지 않는다.
  it('open_id가 없는 payload는 프로필을 만들지 않고 오류를 낸다', async () => {
    vi.mocked(assembleRoster).mockResolvedValue({ units: [] })
    const onRoster = vi.fn()
    inbox(EMPTY)

    const { result } = renderHook(() => useBookmarkletImport(onRoster))

    await waitFor(() => expect(result.current.status).toBe('error'))
    expect(result.current.error).toMatch(/계정/)
    expect(onRoster).not.toHaveBeenCalled()
  })

  it('open_id가 공백뿐인 payload도 거절한다', async () => {
    vi.mocked(assembleRoster).mockResolvedValue({ units: [] })
    const onRoster = vi.fn()
    inbox({ ...EMPTY, open_id: '   ' })

    const { result } = renderHook(() => useBookmarkletImport(onRoster))

    await waitFor(() => expect(result.current.status).toBe('error'))
    expect(onRoster).not.toHaveBeenCalled()
  })

  // 닉네임은 로스터와 다른 호출에서 오고 그 실패는 삼켜진다 - 필드가 통째로
  // 빠진 서버가 와도 로스터는 멀쩡해야 하고, 저장되는 값은 언제나 문자열이어야
  // 한다. `undefined`가 새면 "빈 닉네임"과 "없는 닉네임"이 갈려 읽는 쪽마다
  // 두 경우를 다 막아야 한다.
  it('닉네임이 아예 없는 서버도 빈 문자열로 넘긴다', async () => {
    vi.mocked(assembleRoster).mockResolvedValue({ units: [] })
    const onRoster = vi.fn()
    const { nickname: _omitted, ...noNickname } = server(83, 1)
    inbox({ open_id: 'abc123', servers: [noNickname] })

    renderHook(() => useBookmarkletImport(onRoster))

    await waitFor(() => expect(onRoster).toHaveBeenCalled())
    expect(onRoster.mock.calls[0][0].nickname).toBe('')
    expect(onRoster.mock.calls[0][0].area).toBe(83)
  })

  it('payload의 open_id/nickname을 분리해 raw와 함께 onRoster로 넘긴다', async () => {
    vi.mocked(assembleRoster).mockResolvedValue({ units: [] })
    const onRoster = vi.fn()
    inbox({ ...EMPTY, open_id: 'abc123', nickname: 'Fienn' })

    renderHook(() => useBookmarkletImport(onRoster))

    await waitFor(() =>
      expect(onRoster).toHaveBeenCalledWith({
        openId: 'abc123',
        area: 81,
        nickname: 'Fienn',
        nicknameError: '',
        raw: { units: [] },
      }),
    )
  })


  it('조립 실패는 error 상태로 드러난다', async () => {
    vi.mocked(assembleRoster).mockRejectedValue(new Error('boom'))
    inbox({ ...EMPTY, open_id: 'abc123' })

    const { result } = renderHook(() => useBookmarkletImport(vi.fn()))

    await waitFor(() => expect(result.current.status).toBe('error'))
    expect(result.current.error).toContain('boom')
  })


  it('blablalink 출처라도 payload가 없거나 형태가 이상하면 assembleRoster를 부르지 않는다', async () => {
    const onRoster = vi.fn()
    renderHook(() => useBookmarkletImport(onRoster))

    inbox(undefined) // payload 누락
    inbox(null)
    inbox('not-a-roster') // garbage
    inbox({ owned: [] }) // 필드 일부만

    await new Promise((r) => setTimeout(r, 10))
    expect(assembleRoster).not.toHaveBeenCalled()
    expect(onRoster).not.toHaveBeenCalled()
  })


  it('서버가 하나면 묻지 않고 바로 조립해 넘긴다', async () => {
    vi.mocked(assembleRoster).mockResolvedValue({ units: [] })
    const onRoster = vi.fn()
    inbox({ open_id: 'abc123', servers: [server(83, 181, 'FIENN')] })

    renderHook(() => useBookmarkletImport(onRoster))

    await waitFor(() =>
      expect(onRoster).toHaveBeenCalledWith({
        openId: 'abc123',
        area: 83,
        nickname: 'FIENN',
        nicknameError: '',
        raw: { units: [] },
      }),
    )
  })

  it('서버 payload의 synchro_level을 조립 요청에 실어 보낸다', async () => {
    // 유니온 레이드는 레벨 보정이 없어 이 값이 곧 전투 레벨이다. 훅은 값을
    // 해석하지 않고 나르기만 한다 - 해석은 백엔드 조립기가 한다.
    vi.mocked(assembleRoster).mockResolvedValue({ units: [] })
    inbox({ open_id: 'abc123', servers: [{ ...server(83, 1), synchro_level: 668 }] })

    renderHook(() => useBookmarkletImport(vi.fn()))

    await waitFor(() => expect(assembleRoster).toHaveBeenCalled())
    expect(vi.mocked(assembleRoster).mock.calls[0][0]).toMatchObject({
      synchro_level: 668,
    })
  })

  it('싱크로 레벨이 없는 옛 북마크릿 payload도 그대로 조립한다', async () => {
    // 이미 설치된 북마크릿은 설치 시점 소스가 박제된 것이라 이 값을 안 보낸다.
    // 그래도 동기화는 성공해야 한다 - 없어지는 것은 유니온 스탯뿐이다.
    vi.mocked(assembleRoster).mockResolvedValue({ units: [] })
    inbox({ open_id: 'abc123', servers: [server(83, 1)] })

    renderHook(() => useBookmarkletImport(vi.fn()))

    await waitFor(() => expect(assembleRoster).toHaveBeenCalled())
    expect(vi.mocked(assembleRoster).mock.calls[0][0].synchro_level).toBeUndefined()
  })

  it('서버가 둘이면 고르기 전에는 아무것도 조립하지 않는다', async () => {
    vi.mocked(assembleRoster).mockResolvedValue({ units: [] })
    const onRoster = vi.fn()
    inbox({ open_id: 'abc123', servers: [server(81, 186), server(83, 10)] })

    const { result } = renderHook(() => useBookmarkletImport(onRoster))

    await waitFor(() => expect(result.current.status).toBe('choosing'))
    expect(result.current.candidates).toEqual([
      { area: 81, count: 186 },
      { area: 83, count: 10 },
    ])
    expect(assembleRoster).not.toHaveBeenCalled()
    expect(onRoster).not.toHaveBeenCalled()
  })

  it('고른 서버 하나만 조립한다', async () => {
    vi.mocked(assembleRoster).mockResolvedValue({ units: [] })
    const onRoster = vi.fn()
    inbox({ open_id: 'abc123', servers: [server(81, 186), server(83, 10)] })

    const { result } = renderHook(() => useBookmarkletImport(onRoster))
    await waitFor(() => expect(result.current.status).toBe('choosing'))

    // `choose`는 상태를 바꾸므로 act 안에서 부른다 - 밖에서 부르면 경고가 찍히고,
    // 이 저장소는 테스트 출력이 깨끗해야 통과다.
    await act(async () => {
      result.current.choose(83)
    })

    await waitFor(() => expect(onRoster).toHaveBeenCalledOnce())
    expect(onRoster).toHaveBeenCalledWith({
      openId: 'abc123',
      area: 83,
      nickname: '',
      nicknameError: '',
      raw: { units: [] },
    })
    expect(vi.mocked(assembleRoster).mock.calls[0][0].owned).toHaveLength(10)
  })

  // choose()를 노출하는 버튼은 더블클릭될 수 있다. 이미 조립이 진행 중이면
  // 같은 서버를 다시 눌러도 assembleRoster를 한 번 더 부르지 않아야 한다.
  it('조립이 진행 중일 때 같은 서버를 다시 골라도 조립은 한 번만 한다', async () => {
    let resolveAssemble: (value: { units: never[] }) => void = () => {}
    vi.mocked(assembleRoster).mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveAssemble = resolve
        }),
    )
    const onRoster = vi.fn()
    inbox({ open_id: 'abc123', servers: [server(81, 186), server(83, 10)] })

    const { result } = renderHook(() => useBookmarkletImport(onRoster))
    await waitFor(() => expect(result.current.status).toBe('choosing'))

    act(() => {
      result.current.choose(83)
    })
    expect(result.current.status).toBe('importing')

    act(() => {
      result.current.choose(83)
    })
    expect(assembleRoster).toHaveBeenCalledTimes(1)

    await act(async () => {
      resolveAssemble({ units: [] })
    })
    await waitFor(() => expect(onRoster).toHaveBeenCalledOnce())
  })

  // 이미 설치된 북마크릿은 area 81로 조회한 데이터를 옛 모양으로 보낸다.
  it('구 payload는 area 81 서버 하나로 받는다', async () => {
    vi.mocked(assembleRoster).mockResolvedValue({ units: [] })
    const onRoster = vi.fn()
    inbox({ ...EMPTY, open_id: 'abc123', nickname: 'FIENN' })

    renderHook(() => useBookmarkletImport(onRoster))

    await waitFor(() =>
      expect(onRoster).toHaveBeenCalledWith({
        openId: 'abc123',
        area: 81,
        nickname: 'FIENN',
        nicknameError: '',
        raw: { units: [] },
      }),
    )
  })
})
