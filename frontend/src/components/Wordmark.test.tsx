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

  // 색을 구워넣으면 헤더의 색을 못 따라간다. 밝은 바탕과 어두운 바탕 양쪽에
  // 올라가므로 currentColor여야 한다.
  it('색을 CSS에 맡긴다', () => {
    const { container } = render(<Wordmark />)
    expect(container.querySelector('svg')).toHaveAttribute('fill', 'currentColor')
  })

  it('획을 그린다', () => {
    const { container } = render(<Wordmark />)
    const d = container.querySelector('path')?.getAttribute('d') ?? ''
    expect(d.length).toBeGreaterThan(100)
  })
})
