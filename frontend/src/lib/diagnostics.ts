// 렌더가 터졌을 때 유저가 그대로 넘길 수 있는 한 덩어리의 텍스트.
//
// 배포 빌드는 콘솔이 없다 - 개발자 도구는 `RapiLab.exe --debug`로 다시 띄워야
// 열린다. 그러니 유저가 스택을 볼 길이 없고, 제보는 "검은 화면이 났다" 한 줄로
// 온다. 그 한 줄로는 아무것도 못 고친다. 이 포맷터는 그 자리에서 알 수 있는
// 것을 전부 적어 붙여넣기 한 번으로 넘어가게 한다.
//
// 무엇을 적을지는 실제 사고가 정했다: 2026-08-22의 검은 화면을 가른 것은
// 「그 덱이 실제로 가진 키 목록」이었다(없는 필드를 읽고 있었다). 그래서
// details는 자유 형식이고, 터진 자리가 자기가 아는 사실을 그대로 넣는다.

export interface DiagnosticContext {
  /** 어디가 터졌는지, 사람이 읽을 이름. */
  where: string
  engineVersion: string | null
  /** 릴리스 태그. 태그 없이 돌고 있으면 null. */
  appVersion: string | null
  /** 터진 자리가 아는 사실들. 배열은 이어 붙이고, 나머지는 그대로 찍는다. */
  details?: Record<string, unknown>
}

/** 스택 앞쪽 몇 프레임에만 우리 코드가 있다. 전부 실으면 붙여넣기가 실용적이지 않다.
 * 세는 것은 프레임이라, 맨 앞의 메시지 줄은 이 수에 안 들어간다. */
const STACK_FRAMES = 5

const describeError = (error: unknown): string[] => {
  if (error instanceof Error) {
    const stack = (error.stack ?? '').split('\n').slice(0, STACK_FRAMES + 1).join('\n')
    return stack === '' ? [`오류: ${error.name}: ${error.message}`] : [`오류: ${stack}`]
  }
  return [`오류: ${String(error)}`]
}

const describeValue = (value: unknown): string => {
  if (Array.isArray(value)) return value.length === 0 ? '(없음)' : value.join(', ')
  if (value === null || value === undefined) return '(없음)'
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

export const formatDiagnostics = (
  error: unknown,
  context: DiagnosticContext,
  now: Date = new Date(),
): string => {
  const lines = [
    'RapiLab 진단 정보',
    `발생 위치: ${context.where}`,
    `앱 버전: ${context.appVersion ?? '(개발 빌드 — 릴리스 태그 없음)'}`,
    `엔진 버전: ${context.engineVersion ?? '(모름)'}`,
    `시각: ${now.toISOString()}`,
    '',
    ...describeError(error),
  ]
  const details = Object.entries(context.details ?? {})
  if (details.length > 0) {
    lines.push('')
    for (const [key, value] of details) lines.push(`${key}: ${describeValue(value)}`)
  }
  return lines.join('\n')
}
