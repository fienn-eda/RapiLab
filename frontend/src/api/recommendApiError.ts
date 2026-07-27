// Typed error thrown by the recommend API client on a non-2xx response, plus
// a helper to turn it into a user-facing message. `detail` is the parsed JSON
// response body — FastAPI's default shape for validation/error responses is
// `{ detail: string | { msg, loc, type }[] }`.

export class RecommendApiError extends Error {
  readonly status: number
  readonly detail: unknown

  constructor(status: number, detail: unknown) {
    super(`Recommend request failed with status ${status}`)
    this.name = 'RecommendApiError'
    this.status = status
    this.detail = detail
  }
}

const extractDetailMessage = (detail: unknown): string | undefined => {
  if (detail == null || typeof detail !== 'object') return undefined
  const inner = (detail as Record<string, unknown>).detail
  if (typeof inner === 'string') return inner
  if (Array.isArray(inner)) {
    const messages = inner
      .map((item) =>
        item && typeof item === 'object' && 'msg' in item
          ? String((item as { msg: unknown }).msg)
          : undefined,
      )
      .filter((msg): msg is string => msg != null)
    if (messages.length > 0) return messages.join('; ')
  }
  return undefined
}

/** A user-facing message for a RecommendApiError, preferring the backend's own detail. */
export const describeRecommendApiError = (err: RecommendApiError): string => {
  const detailMessage = extractDetailMessage(err.detail)
  if (err.status === 422) {
    return (
      detailMessage ??
      '로스터 또는 보스 설정이 덱 추천에 유효하지 않아요.'
    )
  }
  return detailMessage ?? `덱 추천 요청이 실패했어요 (${err.status}).`
}
