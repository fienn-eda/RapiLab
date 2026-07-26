// Korean display names for a Nikke/boss element (Fienn's call, 2026-07-26 —
// see docs/superpowers/specs/2026-07-26-ui-chrome-korean-localization-design.md).
// Shared by BossProfileField (static element picker) and UnitPalette (per-unit
// display) so the two never drift.

import type { NikkeElement } from '../types/supportedUnit'

const ELEMENT_LABELS: Record<NikkeElement, string> = {
  Fire: '작열',
  Water: '수냉',
  Wind: '풍압',
  Iron: '철갑',
  Electric: '전격',
}

export const elementLabel = (element: NikkeElement): string => ELEMENT_LABELS[element]
