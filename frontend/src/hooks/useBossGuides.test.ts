import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useBossGuides, type GuideEvent } from './useBossGuides'

const KEY = 'solo-40::사치스러운 거미'

const event = (over: Partial<GuideEvent> = {}): GuideEvent => ({
  id: 'e1',
  at: 20,
  text: '탄막 사격 — 엄폐로 넘긴다',
  ...over,
})

beforeEach(() => {
  localStorage.clear()
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('useBossGuides', () => {
  it('없는 키에는 fallback을 준다', () => {
    const { result } = renderHook(() => useBossGuides())
    expect(result.current.guideFor(KEY, [])).toEqual([])

    const bundled = [event({ text: '번들 값' })]
    expect(result.current.guideFor(KEY, bundled)).toEqual(bundled)
  })

  it('쓴 이벤트가 localStorage에 남고 다시 읽힌다', () => {
    const { result } = renderHook(() => useBossGuides())
    act(() => result.current.setGuide(KEY, [event()]))
    expect(result.current.guideFor(KEY, [])).toEqual([event()])

    const reread = renderHook(() => useBossGuides())
    expect(reread.result.current.guideFor(KEY, [])).toEqual([event()])
  })

  it('시각 없는 「상시」 항목도 그대로 남는다', () => {
    const always = event({ id: 'e2', at: null, text: '잡몹이 계속 나온다' })
    const { result } = renderHook(() => useBossGuides())
    act(() => result.current.setGuide(KEY, [always]))
    expect(result.current.guideFor(KEY, [])).toEqual([always])
  })

  // 키가 (회차, 보스)인 것이 요점이다 - 같은 보스가 다음 시즌에 다른 속성으로
  // 나오면 지난 시즌 글이 얹히면 안 된다.
  it('회차가 다르면 다른 칸이다', () => {
    const { result } = renderHook(() => useBossGuides())
    act(() => result.current.setGuide('solo-39::아일랜드 이터', [event()]))
    expect(result.current.guideFor('solo-40::아일랜드 이터', [])).toEqual([])
  })

  // 개정 전에 자유 문장으로 쓴 글을 버리지 않는다.
  it('저장된 것이 옛 문자열이면 「상시」 항목 하나로 읽는다', () => {
    localStorage.setItem(
      'nikke-boss-guides',
      JSON.stringify({ guides: { [KEY]: '알을 먼저 깨고 본체를 친다' } }),
    )
    const { result } = renderHook(() => useBossGuides())
    const loaded = result.current.guideFor(KEY, [])
    expect(loaded).toHaveLength(1)
    expect(loaded[0].at).toBeNull()
    expect(loaded[0].text).toBe('알을 먼저 깨고 본체를 친다')
    expect(loaded[0].id).toBeTruthy()
  })

  it('읽기가 막혀 있어도 던지지 않는다', () => {
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('blocked')
    })
    const { result } = renderHook(() => useBossGuides())
    expect(result.current.guideFor(KEY, [])).toEqual([])
  })

  it('쓰기가 막혀 있어도 이번 세션 동안은 고쳐 쓸 수 있다', () => {
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('blocked')
    })
    const { result } = renderHook(() => useBossGuides())
    act(() => result.current.setGuide(KEY, [event()]))
    expect(result.current.guideFor(KEY, [])).toEqual([event()])
  })

  it('저장된 것이 깨진 JSON이어도 빈 것으로 시작한다', () => {
    localStorage.setItem('nikke-boss-guides', '{ 이건 JSON이 아니다')
    const { result } = renderHook(() => useBossGuides())
    expect(result.current.guideFor(KEY, [])).toEqual([])
  })
})
