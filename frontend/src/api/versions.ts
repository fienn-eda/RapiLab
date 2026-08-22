// GET /api/engine-version. 결과 캐시를 조회하는 시점(요청을 보내기 전)에
// 엔진 버전을 이미 알고 있어야 해서, 응답에 실려 오는 것과 별개로 이 GET이 있다.
//
// 릴리스 태그도 같은 왕복에 실려 온다. 캐시와는 아무 상관이 없고 - 무효화 축은
// engine_version 하나다 - 화면이 진단 정보에 적기 위한 것이다. 태그 없는 빌드
// (개발 실행)에서는 null이고, 그것도 참인 답이라 감추지 않는다.

export interface Versions {
  engineVersion: string
  /** 릴리스 태그(`v0.1.5`). 태그 없이 돌고 있으면 null. */
  appVersion: string | null
}

export const fetchVersions = async (signal?: AbortSignal): Promise<Versions> => {
  const response = await fetch('/api/engine-version', { signal })
  if (!response.ok) throw new Error(`engine-version failed: ${response.status}`)
  const body = (await response.json()) as {
    engine_version: string
    app_version: string | null
  }
  // app_version은 이 필드가 생기기 전 백엔드와도 섞일 수 있다(앱과 백엔드가 같은
  // 프로세스라 실제로는 못 어긋나지만, 개발 중에는 창과 서버가 따로 뜬다).
  return { engineVersion: body.engine_version, appVersion: body.app_version ?? null }
}
