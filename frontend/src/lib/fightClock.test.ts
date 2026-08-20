import { describe, expect, it } from 'vitest'
import { parseRemaining, remainingLabel } from './fightClock'

describe('remainingLabel', () => {
  it('경과 초를 남은 시간으로 뒤집는다', () => {
    expect(remainingLabel(0, 180)).toBe('3:00')
    expect(remainingLabel(1, 180)).toBe('2:59')
    expect(remainingLabel(61, 180)).toBe('1:59')
    expect(remainingLabel(126, 180)).toBe('0:54')
    expect(remainingLabel(180, 180)).toBe('0:00')
  })

  it('초를 두 자리로 채운다 - 2:5는 시계가 아니다', () => {
    expect(remainingLabel(175, 180)).toBe('0:05')
  })

  // 음수 시계는 게임에 없다.
  it('전투 시간을 넘긴 값은 0:00으로 눕힌다', () => {
    expect(remainingLabel(200, 180)).toBe('0:00')
  })

  it('전투 시간이 바뀌면 같은 경과 초가 다른 잔여시간이 된다', () => {
    expect(remainingLabel(60, 180)).toBe('2:00')
    expect(remainingLabel(60, 200)).toBe('2:20')
  })
})

describe('parseRemaining', () => {
  it('사람이 친 남은 시간을 경과 초로 돌린다', () => {
    expect(parseRemaining('3:00', 180)).toBe(0)
    expect(parseRemaining('2:59', 180)).toBe(1)
    expect(parseRemaining('0:54', 180)).toBe(126)
    expect(parseRemaining('0:00', 180)).toBe(180)
  })

  it('앞뒤 공백은 무시한다', () => {
    expect(parseRemaining('  1:30  ', 180)).toBe(90)
  })

  // 이게 이 함수의 존재 이유다 - 치는 중인 값에 null을 줘야 목록이 안 튄다.
  it('치는 중인 값은 읽지 않는다', () => {
    expect(parseRemaining('', 180)).toBeNull()
    expect(parseRemaining('2', 180)).toBeNull()
    expect(parseRemaining('2:', 180)).toBeNull()
    expect(parseRemaining('2:4', 180)).toBeNull()
  })

  it('시계가 아닌 값은 거절한다', () => {
    expect(parseRemaining('2:60', 180)).toBeNull()
    expect(parseRemaining('abc', 180)).toBeNull()
    expect(parseRemaining('90', 180)).toBeNull()
  })

  // 전투 시간보다 많이 남을 수는 없다. 눕히면 판독이 틀렸다는 사실이 감춰진다.
  it('전투 시간보다 큰 잔여시간은 거절한다', () => {
    expect(parseRemaining('3:01', 180)).toBeNull()
    expect(parseRemaining('3:20', 200)).toBe(0)
  })
})
