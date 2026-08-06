// 개인정보 안내가 화면에 닿는지. 문안의 정확성은 백엔드의
// tests/test_privacy_claims.py가 코드와 대조해 지키고, 여기가 보는 것은
// "읽을 수 있는가"다.

import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { PrivacyNotice } from './PrivacyNotice'
import { HELP } from '../lib/helpText'

describe('PrivacyNotice', () => {
  it('접힌 채로 시작한다', () => {
    render(<PrivacyNotice />)

    // 푸터가 본문으로 채워지면 안 된다 - 평소에는 표지 한 줄이어야 한다.
    expect(screen.getByText('개인정보 처리방침')).toBeInTheDocument()
    expect(screen.getByRole('group')).not.toHaveAttribute('open')
  })

  it('펼치면 모든 항목이 나온다', async () => {
    render(<PrivacyNotice />)

    await userEvent.click(screen.getByText('개인정보 처리방침'))

    expect(screen.getByRole('group')).toHaveAttribute('open')
    for (const section of HELP.privacy.sections) {
      expect(screen.getByRole('heading', { name: section.heading })).toBeInTheDocument()
    }
    // 항목 수가 문구 파일과 어긋나면 렌더가 조용히 일부를 빠뜨린 것이다.
    const items = HELP.privacy.sections.reduce((sum, s) => sum + s.items.length, 0)
    expect(screen.getAllByRole('listitem')).toHaveLength(items)
  })

  it('바깥으로 나가는 링크를 두지 않는다', () => {
    // 이 앱은 주소창도 뒤로가기도 없는 네이티브 창이라, 바깥 주소로 넘어가면
    // 돌아올 방법이 없다. 안내는 오프라인에서도 읽혀야 한다.
    const { container } = render(<PrivacyNotice />)

    expect(container.querySelector('a')).toBeNull()
  })
})
