// 로스터 조립 요청에 실리는 익명 식별자. 게임 계정·open_id·로스터와 무관하고,
// blablalink 호출에는 싣지 않는다.
//
// 백엔드가 이 PC 안에 있으므로 이 값은 기기를 떠나지 않는다 - 닿는 곳은
// `/api/assemble-roster`의 요청 헤더와 그 엔드포인트가 남기는 집계 로그 한 줄이
// 전부다. 화면 맨 아래 개인정보 안내가 이 사실을 그대로 말한다.

const STORAGE_KEY = 'nikke-client-id'

export const getClientId = (): string => {
  const existing = localStorage.getItem(STORAGE_KEY)
  if (existing) return existing
  const id = crypto.randomUUID()
  localStorage.setItem(STORAGE_KEY, id)
  return id
}
