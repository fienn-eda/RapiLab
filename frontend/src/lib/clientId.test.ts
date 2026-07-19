import { beforeEach, describe, expect, it } from 'vitest'
import { getClientId } from './clientId'

beforeEach(() => localStorage.clear())

describe('getClientId', () => {
  it('한 번 만들면 계속 같은 값을 준다', () => {
    expect(getClientId()).toBe(getClientId())
  })

  it('저장소를 비우면 새 값을 만든다', () => {
    const first = getClientId()
    localStorage.clear()
    expect(getClientId()).not.toBe(first)
  })

  it('게임 계정과 무관한 임의 값이다', () => {
    expect(getClientId()).toMatch(/^[0-9a-f-]{36}$/)
  })
})
