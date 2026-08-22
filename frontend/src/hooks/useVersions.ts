// 지금 백엔드가 돌리는 엔진의 버전과 이 빌드의 릴리스 태그. 마운트 시 1회
// 가져오고, 실패하면 둘 다 null로 남는다 - 버전을 모른다고 추천을 못 쓰게 만들
// 이유는 없다. engineVersion이 null이면 캐시 키에 null이 들어가고, 버전이 도착한
// 뒤 한 번 미스한 다음부터 정상이다.
//
// 둘을 한 훅으로 두는 이유는 한 왕복에서 같이 오기 때문이다. 쓰임은 다르다:
// engineVersion은 캐시 무효화 축이고, appVersion은 진단에 적는 값이다.

import { useEffect, useState } from 'react'
import { fetchVersions } from '../api/versions'

export interface VersionState {
  engineVersion: string | null
  appVersion: string | null
}

const UNKNOWN: VersionState = { engineVersion: null, appVersion: null }

export const useVersions = (): VersionState => {
  const [versions, setVersions] = useState<VersionState>(UNKNOWN)

  useEffect(() => {
    const controller = new AbortController()
    fetchVersions(controller.signal)
      .then(setVersions)
      .catch(() => {})
    return () => controller.abort()
  }, [])

  return versions
}
