// 북마크릿이 로컬 서버에 두고 간 로스터를 집어온다.
//
// 네이티브 창(WebView2)은 유저 브라우저와 별개 브라우저라 북마크릿의
// postMessage가 앱에 닿지 않는다. 그래서 북마크릿은 `127.0.0.1`의 인박스로
// POST하고, 앱은 이 함수로 가져간다. 서버는 내주면서 비우므로, 같은 로스터를
// 두 번 집어오는 일은 없다.

/** 인박스에 있던 원시 payload, 비어 있으면 null. */
export const takeSyncInbox = async (signal?: AbortSignal): Promise<unknown> => {
  const response = await fetch('/api/sync-inbox', { signal })
  if (!response.ok) return null
  const body = (await response.json()) as { payload?: unknown }
  return body.payload ?? null
}
