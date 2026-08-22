import { describe, expect, it } from 'vitest'
import { formatDiagnostics } from './diagnostics'

const AT = new Date('2026-08-23T00:20:00.000Z')

const context = {
  where: '저장한 결과 「덱1 버충 08-21」',
  engineVersion: 'fb6b35bb068b',
  appVersion: 'v0.1.5',
}

describe('formatDiagnostics', () => {
  it('오류 메시지와 두 버전을 적는다', () => {
    const text = formatDiagnostics(new Error('boom'), context, AT)

    expect(text).toContain('boom')
    expect(text).toContain('fb6b35bb068b')
    expect(text).toContain('v0.1.5')
    expect(text).toContain('저장한 결과 「덱1 버충 08-21」')
  })

  // 릴리스 태그가 없는 빌드도 참인 답이다. 빈칸으로 두면 제보를 읽는 쪽이 "안 적혔다"와
  // "개발 빌드다"를 못 가른다.
  it('릴리스 태그가 없으면 개발 빌드라고 적는다', () => {
    const text = formatDiagnostics(new Error('boom'), { ...context, appVersion: null }, AT)

    expect(text).toContain('개발 빌드')
  })

  // 스택 전체는 붙여넣기에 실용적이지 않고, 우리 프레임은 늘 맨 위에 있다.
  it('스택은 앞 5줄만 싣는다', () => {
    const error = new Error('boom')
    error.stack = ['Error: boom', ...Array.from({ length: 40 }, (_, i) => `  at frame${i}`)].join(
      '\n',
    )

    const text = formatDiagnostics(error, context, AT)

    expect(text).toContain('at frame0')
    expect(text).toContain('at frame4')
    expect(text).not.toContain('at frame5')
  })

  // 이번 사고에서 결정적이었던 정보가 「그 덱이 실제로 가진 키 목록」이었다.
  // 배열을 [object Object]로 찍으면 그 값어치가 통째로 사라진다.
  it('details의 배열을 읽을 수 있게 이어 붙인다', () => {
    const text = formatDiagnostics(new Error('boom'), {
      ...context,
      details: { '덱 키': ['deck', 'total_damage', 'hold_burst_slugs'] },
    }, AT)

    expect(text).toContain('덱 키: deck, total_damage, hold_burst_slugs')
  })

  it('빈 배열도 없다고 말한다', () => {
    const text = formatDiagnostics(new Error('boom'), {
      ...context,
      details: { '덱 키': [] },
    }, AT)

    expect(text).toContain('덱 키: (없음)')
  })

  // 렌더 중에는 Error가 아닌 것도 던져질 수 있다. 진단을 만들다 또 터지면
  // 폴백 화면 자체가 사라진다.
  it('Error가 아닌 값을 던져도 만들어 낸다', () => {
    const text = formatDiagnostics('그냥 문자열', context, AT)

    expect(text).toContain('그냥 문자열')
  })

  it('null을 던져도 만들어 낸다', () => {
    expect(() => formatDiagnostics(null, context, AT)).not.toThrow()
  })
})
