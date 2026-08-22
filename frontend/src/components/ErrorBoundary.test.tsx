// 이 컴포넌트가 있는 이유는 2026-08-22의 검은 화면이다: 결과 카드 하나가 던진
// TypeError가 트리 전체를 언마운트했고, 앱 배경이 어두워 유저에게는 "검은 화면"이
// 됐다. 여기서 재는 것은 "예외가 어디까지 번지는가"다.

import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ErrorBoundary } from './ErrorBoundary'

const CONTEXT = {
  where: '테스트 자리',
  engineVersion: 'fb6b35bb068b',
  appVersion: 'v0.1.5',
}

const Boom = ({ message = '터졌다' }: { message?: string }) => {
  throw new Error(message)
}

// React는 잡힌 예외를 그대로 console.error로 흘린다. 이 스위트의 출력은 깨끗해야
// 하므로 매번 가로채고, 우리가 남기는 줄이 실제로 있는지는 테스트로 확인한다.
beforeEach(() => {
  vi.spyOn(console, 'error').mockImplementation(() => {})
})

afterEach(() => {
  vi.restoreAllMocks()
})

const withClipboard = (writeText: (text: string) => Promise<void>) => {
  Object.defineProperty(navigator, 'clipboard', {
    value: { writeText },
    configurable: true,
  })
}

const withoutClipboard = () => {
  Object.defineProperty(navigator, 'clipboard', {
    value: undefined,
    configurable: true,
  })
}

describe('ErrorBoundary', () => {
  it('아무 일 없으면 자식을 그대로 그린다', () => {
    render(
      <ErrorBoundary title="결과" context={CONTEXT}>
        <p>멀쩡한 내용</p>
      </ErrorBoundary>,
    )

    expect(screen.getByText('멀쩡한 내용')).toBeInTheDocument()
  })

  it('자식이 던지면 제목과 오류를 적은 카드로 바꾼다', () => {
    render(
      <ErrorBoundary title="이 결과는 열 수 없습니다" context={CONTEXT}>
        <Boom />
      </ErrorBoundary>,
    )

    expect(screen.getByRole('alert')).toHaveTextContent('이 결과는 열 수 없습니다')
    expect(screen.getByRole('alert')).toHaveTextContent('터졌다')
  })

  // **이 테스트가 이 컴포넌트의 요점이다.** 하나가 터져도 나머지가 살아야
  // "검은 화면"이 "카드 하나가 안 열림"으로 줄어든다.
  it('터진 것은 그 경계 안에서 멈추고 형제는 산다', () => {
    render(
      <>
        <ErrorBoundary title="깨진 것" context={CONTEXT}>
          <Boom />
        </ErrorBoundary>
        <ErrorBoundary title="멀쩡한 것" context={CONTEXT}>
          <p>다른 보관물</p>
        </ErrorBoundary>
      </>,
    )

    expect(screen.getByText('다른 보관물')).toBeInTheDocument()
    expect(screen.getByRole('alert')).toHaveTextContent('깨진 것')
  })

  it('복구 수단을 받으면 폴백에 함께 그린다', async () => {
    const onDelete = vi.fn()
    render(
      <ErrorBoundary
        title="결과"
        context={CONTEXT}
        actions={
          <button type="button" onClick={onDelete}>
            이 보관물 삭제
          </button>
        }
      >
        <Boom />
      </ErrorBoundary>,
    )

    await userEvent.click(screen.getByRole('button', { name: '이 보관물 삭제' }))

    expect(onDelete).toHaveBeenCalledOnce()
  })

  it('진단 복사는 버전과 오류가 담긴 텍스트를 클립보드에 넣는다', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined)
    withClipboard(writeText)
    render(
      <ErrorBoundary title="결과" context={{ ...CONTEXT, details: { '덱 키': ['deck'] } }}>
        <Boom />
      </ErrorBoundary>,
    )

    await userEvent.click(screen.getByRole('button', { name: /진단 정보 복사/ }))

    expect(writeText).toHaveBeenCalledOnce()
    const text = writeText.mock.calls[0][0] as string
    expect(text).toContain('터졌다')
    expect(text).toContain('v0.1.5')
    expect(text).toContain('fb6b35bb068b')
    expect(text).toContain('덱 키: deck')
  })

  // 클립보드가 막힌 환경에서도 유저가 제보할 수 있어야 한다 - 배포 빌드에는
  // 콘솔이 없으니 여기가 막히면 정보를 꺼낼 길이 사라진다.
  it('클립보드가 없으면 직접 복사하도록 펼쳐 보여준다', async () => {
    withoutClipboard()
    render(
      <ErrorBoundary title="결과" context={CONTEXT}>
        <Boom />
      </ErrorBoundary>,
    )

    await userEvent.click(screen.getByRole('button', { name: /진단 정보 복사/ }))

    const box = screen.getByRole('textbox') as HTMLTextAreaElement
    expect(box.value).toContain('터졌다')
  })

  it('클립보드가 거절해도 펼쳐 보여준다', async () => {
    withClipboard(() => Promise.reject(new Error('막힘')))
    render(
      <ErrorBoundary title="결과" context={CONTEXT}>
        <Boom />
      </ErrorBoundary>,
    )

    await userEvent.click(screen.getByRole('button', { name: /진단 정보 복사/ }))

    expect(screen.getByRole('textbox')).toBeInTheDocument()
  })

  // `RapiLab.exe --debug`로 띄운 창에서는 개발자 도구가 열린다. 거기서 찾을 수
  // 있게 우리 표식을 달아 남긴다.
  it('콘솔에 표식과 함께 남긴다', () => {
    render(
      <ErrorBoundary title="결과" context={CONTEXT}>
        <Boom />
      </ErrorBoundary>,
    )

    expect(vi.mocked(console.error)).toHaveBeenCalledWith(
      expect.stringContaining('[RapiLab]'),
      expect.anything(),
      expect.anything(),
    )
  })
})
