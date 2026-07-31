// 문구 파일이 쓰는 `**강조**` 표기. 이것이 조용히 깨지면 안내가 별표를 단 채로
// 화면에 나온다 - 눈에 띄지만 아무도 테스트하지 않으면 배포까지 간다.

import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { HelpText } from './HelpText'
import { HELP } from '../lib/helpText'

describe('HelpText', () => {
  it('별표로 감싼 부분만 굵게 그린다', () => {
    const { container } = render(
      <p>
        <HelpText>{'앞 **가운데** 뒤'}</HelpText>
      </p>,
    )

    expect(screen.getByText('가운데').tagName).toBe('STRONG')
    expect(container.textContent).toBe('앞 가운데 뒤')
  })

  it('한 문장에 강조가 여럿이면 각각 굵어진다', () => {
    const { container } = render(
      <p>
        <HelpText>{'**하나** 사이 **둘**'}</HelpText>
      </p>,
    )

    expect(container.querySelectorAll('strong')).toHaveLength(2)
    expect(container.textContent).toBe('하나 사이 둘')
  })

  it('별표가 없는 문구는 글자 그대로 나온다', () => {
    const { container } = render(
      <p>
        <HelpText>{'강조 없는 안내 문장'}</HelpText>
      </p>,
    )

    expect(container.querySelector('strong')).toBeNull()
    expect(container.textContent).toBe('강조 없는 안내 문장')
  })

  it('문구 파일의 별표는 짝이 맞는다', () => {
    // 짝이 안 맞는 별표는 굵어지지도 사라지지도 않고 그대로 보인다.
    const texts: string[] = []
    const walk = (value: unknown): void => {
      if (typeof value === 'string') texts.push(value)
      else if (Array.isArray(value)) value.forEach(walk)
      else if (value && typeof value === 'object') Object.values(value).forEach(walk)
    }
    walk(HELP)

    for (const text of texts) {
      expect(text.split('**').length % 2, `짝이 맞지 않는 별표: ${text}`).toBe(1)
    }
  })
})
