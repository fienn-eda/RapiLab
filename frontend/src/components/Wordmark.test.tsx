import { describe, it, expect } from 'vitest'
import { render } from '@testing-library/react'
import { Wordmark } from './Wordmark'

describe('Wordmark', () => {
  // 워드마크는 그림이고, 읽히는 이름은 이것을 감싸는 <h1>의 숨김 텍스트가
  // 댄다. 여기서 이름을 한 번 더 내면 스크린 리더가 앱 이름을 두 번 읽는다.
  // 생성기가 aria-hidden을 빠뜨리면 그 회귀는 눈으로는 보이지 않는다.
  it('스스로는 읽히지 않는다', () => {
    const { container } = render(<Wordmark />)
    const svg = container.querySelector('svg')
    expect(svg).toHaveAttribute('aria-hidden', 'true')
    expect(svg).not.toHaveAttribute('aria-label')
  })

  // 색은 그라디언트로 구워져 있지만 그 양 끝은 앱 토큰이어야 한다. 생성기에
  // 색값을 직접 넣으면 워드마크만 팔레트를 안 따라가고, 그 어긋남은 토큰을
  // 바꾸는 날에야 드러난다.
  it('그라디언트 양 끝이 앱 토큰이다', () => {
    const { container } = render(<Wordmark />)
    const stops = [...container.querySelectorAll('stop')]
    expect(stops).toHaveLength(2)
    expect(stops.map((s) => s.getAttribute('stop-color'))).toEqual([
      'var(--text)',
      'var(--accent)',
    ])
  })

  // fill과 stroke가 같은 그라디언트를 가리켜야 덧댄 획이 글자와 같은 색으로
  // 이어진다. 굵기는 합성이라 stroke가 곧 글자의 바깥 절반이다.
  it('덧댄 획도 같은 그라디언트로 칠한다', () => {
    const { container } = render(<Wordmark />)
    const path = container.querySelector('path')
    const id = container.querySelector('linearGradient')?.getAttribute('id')
    expect(id).toBeTruthy()
    expect(path).toHaveAttribute('fill', `url(#${id})`)
    expect(path).toHaveAttribute('stroke', `url(#${id})`)
    expect(path).toHaveAttribute('paint-order', 'stroke')
  })

  it('획을 그린다', () => {
    const { container } = render(<Wordmark />)
    const d = container.querySelector('path')?.getAttribute('d') ?? ''
    expect(d.length).toBeGreaterThan(100)
  })
})
