// 렌더 중 예외가 트리 전체를 걷어내지 못하게 막는 울타리.
//
// 왜 필요한가: 2026-08-22, 옛 릴리스에서 저장한 결과를 열면 `DeckCard`가 없는
// 필드를 읽어 TypeError를 던졌고, 울타리가 없어 React가 앱 전체를 언마운트했다.
// 배경이 `#0e0d13`이라 유저가 본 것은 "검은 화면"이었고, 원인을 앱 바깥
// (서버·GPU·오버레이)에서 찾게 만들었다. 같은 계열 사고가 그때가 두 번째였다.
//
// 클래스 컴포넌트인 이유는 React가 이 기능에 훅을 주지 않기 때문이다 -
// `getDerivedStateFromError`/`componentDidCatch`가 유일한 길이다.
//
// 이 울타리는 "고치는" 것이 아니라 **번지는 범위를 정하는** 것이다. 그래서
// 무엇을 감쌀지가 설계다: 보관물 하나마다 감싸면 하나가 깨져도 나머지가 열리고,
// 루트에 하나 더 두면 어디서 터지든 검은 화면 대신 이 카드가 나온다.

import { Component, type ErrorInfo, type ReactNode } from 'react'
import { formatDiagnostics, type DiagnosticContext } from '../lib/diagnostics'

interface ErrorBoundaryProps {
  children: ReactNode
  /** 폴백 카드의 제목. 유저에게 "무엇이" 안 열렸는지 말한다. */
  title: string
  /** 진단 텍스트에 실을 맥락. 터진 자리가 아는 사실을 넣는다. */
  context: DiagnosticContext
  /** 폴백에 함께 그릴 복구 수단(예: 이 보관물 삭제, 새로고침). */
  actions?: ReactNode
}

interface ErrorBoundaryState {
  error: unknown
  caught: boolean
  /** 클립보드가 막혔을 때 직접 복사하도록 펼친 상태. */
  revealed: boolean
  copied: boolean
}

const INITIAL: ErrorBoundaryState = {
  error: null,
  caught: false,
  revealed: false,
  copied: false,
}

/** 카드 머리에 한 줄로 적을 요약. 스택은 진단 텍스트에만 넣는다. */
const oneLine = (error: unknown): string => {
  if (error instanceof Error) return `${error.name}: ${error.message}`
  return String(error)
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = INITIAL

  static getDerivedStateFromError(error: unknown): Partial<ErrorBoundaryState> {
    return { error, caught: true }
  }

  componentDidCatch(error: unknown, info: ErrorInfo) {
    // 배포 빌드는 콘솔이 없지만 `RapiLab.exe --debug`로 다시 띄우면 열린다.
    // 거기서 검색할 수 있게 표식을 단다.
    console.error('[RapiLab] 렌더 중 예외:', error, info.componentStack)
  }

  private diagnostics(): string {
    return formatDiagnostics(this.state.error, this.props.context)
  }

  private copy = () => {
    const written = navigator.clipboard?.writeText(this.diagnostics())
    // 클립보드가 아예 없거나(비보안 컨텍스트) 거절하면 직접 복사할 수 있게 펼친다.
    // 배포 빌드에는 콘솔이 없으니 여기가 막히면 정보를 꺼낼 길이 사라진다.
    if (written === undefined) {
      this.setState({ revealed: true })
      return
    }
    written.then(
      () => this.setState({ copied: true }),
      () => this.setState({ revealed: true }),
    )
  }

  render() {
    if (!this.state.caught) return this.props.children

    return (
      <div className="error-card" role="alert">
        <p className="error-card__title">
          <span aria-hidden="true">⚠</span> {this.props.title}
        </p>
        <p className="error-card__message">{oneLine(this.state.error)}</p>
        <div className="error-card__actions">
          <button type="button" className="btn" onClick={this.copy}>
            진단 정보 복사
          </button>
          {this.props.actions}
        </div>
        {this.state.copied && (
          <p className="error-card__hint" role="status">
            복사했습니다. 제보에 그대로 붙여넣어 주세요.
          </p>
        )}
        {this.state.revealed && (
          <textarea
            className="error-card__text"
            readOnly
            rows={10}
            value={this.diagnostics()}
            aria-label="진단 정보"
          />
        )}
      </div>
    )
  }
}
