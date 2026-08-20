import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useBossGuides } from './useBossGuides'

beforeEach(() => {
  localStorage.clear()
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('useBossGuides', () => {
  it('없는 키에는 fallback을 준다', () => {
    const { result } = renderHook(() => useBossGuides())
    expect(result.current.guideFor('solo-40::사치스러운 거미', '')).toBe('')
    expect(result.current.guideFor('solo-40::사치스러운 거미', '기본 글')).toBe('기본 글')
  })

  it('쓴 글이 localStorage에 남고 다시 읽힌다', () => {
    const { result } = renderHook(() => useBossGuides())
    act(() => result.current.setGuide('solo-40::사치스러운 거미', '알 먼저'))
    expect(result.current.guideFor('solo-40::사치스러운 거미', '')).toBe('알 먼저')

    const reread = renderHook(() => useBossGuides())
    expect(reread.result.current.guideFor('solo-40::사치스러운 거미', '')).toBe('알 먼저')
  })

  // 키가 (회차, 보스)인 것이 요점이다 - 같은 보스가 다음 시즌에 다른 속성으로
  // 나오면 지난 시즌 글이 얹히면 안 된다.
  it('회차가 다르면 다른 칸이다', () => {
    const { result } = renderHook(() => useBossGuides())
    act(() => result.current.setGuide('solo-39::아일랜드 이터', '39시즌 글'))
    expect(result.current.guideFor('solo-40::아일랜드 이터', '')).toBe('')
  })

  it('쓴 글이 있으면 fallback을 덮는다 - 2단계에서 회차 데이터가 그 자리에 온다', () => {
    const { result } = renderHook(() => useBossGuides())
    act(() => result.current.setGuide('solo-40::사치스러운 거미', '내가 쓴 것'))
    expect(result.current.guideFor('solo-40::사치스러운 거미', '번들 값')).toBe('내가 쓴 것')
  })

  it('읽기가 막혀 있어도 던지지 않는다', () => {
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('blocked')
    })
    const { result } = renderHook(() => useBossGuides())
    expect(result.current.guideFor('solo-40::사치스러운 거미', '')).toBe('')
  })

  it('쓰기가 막혀 있어도 이번 세션 동안은 고쳐 쓸 수 있다', () => {
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('blocked')
    })
    const { result } = renderHook(() => useBossGuides())
    act(() => result.current.setGuide('solo-40::사치스러운 거미', '알 먼저'))
    expect(result.current.guideFor('solo-40::사치스러운 거미', '')).toBe('알 먼저')
  })

  it('저장된 것이 깨진 JSON이어도 빈 것으로 시작한다', () => {
    localStorage.setItem('nikke-boss-guides', '{ 이건 JSON이 아니다')
    const { result } = renderHook(() => useBossGuides())
    expect(result.current.guideFor('solo-40::사치스러운 거미', '')).toBe('')
  })
})
