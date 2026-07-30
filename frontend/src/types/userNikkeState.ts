// TypeScript mirror of backend/app/models.py (Pydantic).
// SOURCE OF TRUTH: backend/app/models.py — keep these in sync; never diverge.
// Note the trailing underscore in `def_`, matching the Python field name.

export interface SkillLevels {
  skill1: number // int, 1–10
  skill2: number // int, 1–10
  burst: number // int, 1–10
}

/** One overload roll on one gear piece, before same-type rolls are summed.
 *  `slot` is head / torso / arm / leg. Nothing renders it yet — it is carried so
 *  a per-piece view can label the rolls without another sync. */
export interface OverloadLine {
  slot: string
  value: number // float
}

/** One aggregated overload stat line, summed across all 4 gear pieces. */
export interface OverloadOption {
  name: string
  value: number // float
  /** The rolls `value` is the sum of, when the sync supplied them. Charge speed
   *  rounds per roll rather than on the total and a total cannot be decomposed
   *  back, so the backend needs the rolls to be exact. Absent means "not known"
   *  — the backend estimates from the total and says so. */
  lines?: OverloadLine[]
}

export interface UserNikkeState {
  character_slug: string
  level: number // int, ≥ 1
  hp: number // float, ≥ 0
  atk: number // float, ≥ 0
  def_: number // float, ≥ 0 (trailing underscore matches the Python model)
  actual_hp?: number // float, ≥ 0 (real level, for future union raid)
  actual_atk?: number
  actual_def?: number
  skill_levels: SkillLevels
  overload_options: OverloadOption[] // may be empty
  collectible_tid?: number // int, ≥ 0 (equipped collectible's weapon-group skill)
  collectible_level?: number // int, ≥ 0
}

// Constraint bounds, mirrored from the Pydantic Field(...) declarations so the
// client-side validation and the backend agree on exactly one set of rules.
export const CONSTRAINTS = {
  level: { min: 1 },
  hp: { min: 0 },
  atk: { min: 0 },
  def_: { min: 0 },
  skill: { min: 1, max: 10 },
} as const
