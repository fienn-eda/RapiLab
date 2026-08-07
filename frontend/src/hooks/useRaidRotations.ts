// 회차 보스 목록을 마운트 시 1회 조회한다. useSupportedUnits와 같은 모양이지만
// 에러 상태가 없다 — 회차 데이터가 없으면 피커가 안 그려질 뿐이고 보스 설정은
// 손으로 전부 되므로, 배너를 띄울 실패가 아니다.

import { useEffect, useState } from 'react'
import { getRaidRotations } from '../api/raidRotations'
import type { RaidRotation } from '../types/raidRotation'

export interface RaidRotationsState {
  rotations: RaidRotation[]
  loading: boolean
}

export const useRaidRotations = (): RaidRotationsState => {
  const [rotations, setRotations] = useState<RaidRotation[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    getRaidRotations()
      .then((result) => {
        if (!cancelled) setRotations(result)
      })
      .catch(() => {
        if (!cancelled) setRotations([])
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  return { rotations, loading }
}
