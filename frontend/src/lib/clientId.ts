// 제품 개선용 익명 식별자. 게임 계정·open_id·로스터와 무관하며, 우리 백엔드로
// 가는 요청에만 실린다 (blablalink 호출에는 절대 싣지 않는다).

const STORAGE_KEY = 'nikke-client-id'

export const getClientId = (): string => {
  const existing = localStorage.getItem(STORAGE_KEY)
  if (existing) return existing
  const id = crypto.randomUUID()
  localStorage.setItem(STORAGE_KEY, id)
  return id
}
