// Typed client for GET /api/supported-units. Backed by a dev mock unless
// VITE_RECOMMEND_API=live (frontend/README.md "GET /api/supported-units").
// Mirrors recommendRaid.ts: this is the only module that decides which
// implementation runs, so callers never depend on which one is active.

import type { SupportedUnit } from '../types/supportedUnit'
import { fetchSupportedUnits } from './supportedUnitsClient.live'
import { mockSupportedUnits } from './supportedUnitsClient.mock'

const useLiveApi = import.meta.env.VITE_RECOMMEND_API === 'live'

export const getSupportedUnits = (): Promise<SupportedUnit[]> =>
  useLiveApi ? fetchSupportedUnits() : mockSupportedUnits()
