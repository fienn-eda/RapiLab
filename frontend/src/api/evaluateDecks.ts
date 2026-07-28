// POST /api/evaluate-decks의 타입드 클라이언트. api/recommendRaid.ts와 같은
// 계약을 따른다: 타임아웃 없음(마감을 걸면 잘 돌고 있는 실행을 끊는다),
// 호출자의 `signal`이 유저의 취소를 담당하고, 연결이 끊기면 서버도 멈춘다.
// 평가는 탐색이 없어 수 초에 끝나므로 대기 안내가 배분만큼 절실하지는 않다.

import type { EvaluateDecksRequest, EvaluateDecksResponse } from '../types/evaluate'
import { RecommendApiError } from './recommendApiError'

export const evaluateDecks = async (
  request: EvaluateDecksRequest,
  signal?: AbortSignal,
): Promise<EvaluateDecksResponse> => {
  const response = await fetch('/api/evaluate-decks', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
    signal,
  })
  if (!response.ok) {
    const detail: unknown = await response.json().catch(() => null)
    throw new RecommendApiError(response.status, detail)
  }
  return (await response.json()) as EvaluateDecksResponse
}
