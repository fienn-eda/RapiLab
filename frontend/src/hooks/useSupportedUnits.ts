// Fetches the engine-supported unit list once (frontend/README.md "GET
// /api/supported-units") and exposes it to the draft palette. No request body
// and no mutation, so unlike useRecommend/useRecommendRaid this is a
// fetch-on-mount hook rather than a submit-driven one.

import { useEffect, useState } from 'react'
import { getSupportedUnits } from '../api/supportedUnits'
import type { SupportedUnit } from '../types/supportedUnit'

export interface SupportedUnitsState {
  units: SupportedUnit[]
  loading: boolean
  error?: string
}

const FALLBACK_ERROR_MESSAGE = '지원 유닛 목록을 불러오지 못했어요.'

export const useSupportedUnits = (): SupportedUnitsState => {
  const [units, setUnits] = useState<SupportedUnit[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string>()

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    getSupportedUnits()
      .then((result) => {
        if (cancelled) return
        setUnits(result)
        setError(undefined)
      })
      .catch(() => {
        if (cancelled) return
        setError(FALLBACK_ERROR_MESSAGE)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  return { units, loading, error }
}
