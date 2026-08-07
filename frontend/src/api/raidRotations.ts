// Typed client for GET /api/raid-rotations. 회차 보스 카드 피커가 쓴다.
// 와이어가 이미 프론트가 쓰는 모양이라 supportedUnits.ts와 달리 매핑 함수가 없다.

import type { RaidRotation, RaidRotationsWire } from '../types/raidRotation'
import { RecommendApiError } from './recommendApiError'

export const getRaidRotations = async (): Promise<RaidRotation[]> => {
  const response = await fetch('/api/raid-rotations')
  if (!response.ok) {
    const detail: unknown = await response.json().catch(() => null)
    throw new RecommendApiError(response.status, detail)
  }
  const wire = (await response.json()) as RaidRotationsWire
  return wire.rotations
}
