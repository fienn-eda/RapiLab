// 지금 백엔드가 돌리는 엔진의 버전. 마운트 시 1회 가져오고, 실패하면 null로
// 남는다 - 버전을 모른다고 추천을 못 쓰게 만들 이유는 없다. null이면 캐시
// 키에 null이 들어가고, 버전이 도착한 뒤 한 번 미스한 다음부터 정상이다.

import { useEffect, useState } from 'react'
import { fetchEngineVersion } from '../api/engineVersion'

export const useEngineVersion = (): string | null => {
  const [version, setVersion] = useState<string | null>(null)

  useEffect(() => {
    const controller = new AbortController()
    fetchEngineVersion(controller.signal)
      .then(setVersion)
      .catch(() => {})
    return () => controller.abort()
  }, [])

  return version
}
