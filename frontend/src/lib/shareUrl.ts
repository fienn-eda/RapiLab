// ShiftyPad의 공개 공유 URL에서 intl_open_id를 뽑는다. uid는
// "<앞자리>-<intl_open_id>"의 base64이고, 앞자리는 API가 받는 nikke_area_id가
// 아니므로 버린다 - 계정의 서버 리전은 uid에서 읽을 수 없다.

const OPEN_ID = /^\d{6,}$/

export const parseShareUrl = (input: string): string => {
  const trimmed = input.trim()
  if (OPEN_ID.test(trimmed)) return trimmed

  const uid = (() => {
    try {
      return new URL(trimmed).searchParams.get('uid')
    } catch {
      return null
    }
  })()
  if (!uid) throw new Error('ShiftyPad 공유 URL이 아니에요: uid 파라미터가 없어요.')

  let decoded: string
  try {
    decoded = atob(uid)
  } catch {
    throw new Error('ShiftyPad 공유 URL이 아니에요: uid가 base64 형식이 아니에요.')
  }
  const openId = decoded.split('-').at(-1) ?? ''
  if (!OPEN_ID.test(openId)) {
    throw new Error('ShiftyPad 공유 URL이 아니에요: uid 안에 open id가 없어요.')
  }
  return openId
}
