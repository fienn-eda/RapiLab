// GET /api/engine-version. 결과 캐시를 조회하는 시점(요청을 보내기 전)에
// 버전을 이미 알고 있어야 해서, 응답에 실려 오는 것과 별개로 이 GET이 있다.

export const fetchEngineVersion = async (signal?: AbortSignal): Promise<string> => {
  const response = await fetch('/api/engine-version', { signal })
  if (!response.ok) throw new Error(`engine-version failed: ${response.status}`)
  const body = (await response.json()) as { engine_version: string }
  return body.engine_version
}
