import { describe, expect, it } from 'vitest'
import { SERVERS, SERVER_AREAS, serverLabel } from './server'

describe('SERVERS', () => {
  it('blablalink의 다섯 서버를 area와 표기로 담는다', () => {
    expect(SERVERS.map((s) => [s.area, s.label])).toEqual([
      [81, 'JP'],
      [82, 'NA'],
      [83, 'KR'],
      [84, 'GL'],
      [85, 'SEA'],
    ])
  })

  it('SERVER_AREAS는 SERVERS의 area만 순서대로 담는다', () => {
    expect(SERVER_AREAS).toEqual([81, 82, 83, 84, 85])
  })
})

describe('serverLabel', () => {
  it('area를 서버 표기로 바꾼다', () => {
    expect(serverLabel(81)).toBe('JP')
    expect(serverLabel(83)).toBe('KR')
  })

  // 새 서버가 열리면 목록보다 데이터가 먼저 도착할 수 있다. 그때 라벨 자리가
  // 비는 것보다 숫자가 보이는 편이 낫다.
  it('모르는 area는 숫자를 그대로 보여준다', () => {
    expect(serverLabel(99)).toBe('99')
  })
})
