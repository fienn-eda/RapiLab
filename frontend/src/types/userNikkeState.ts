// TypeScript mirror of backend/app/models.py (Pydantic).
// SOURCE OF TRUTH: backend/app/models.py — keep these in sync; never diverge.
// Note the trailing underscore in `def_`, matching the Python field name.

export interface SkillLevels {
  skill1: number // int, 1–10
  skill2: number // int, 1–10
  burst: number // int, 1–10
}

/** One aggregated overload stat line, summed across all 4 gear pieces. */
export interface OverloadOption {
  name: string
  value: number // float
}

/** The PVE (combat) cube equipped. PVP/arena cubes are out of scope. */
export interface PveCube {
  name: string
  level: number // int, 1–10
}

export interface UserNikkeState {
  character_slug: string
  level: number // int, ≥ 1
  core_level: number // int, ≥ 0
  hp: number // float, ≥ 0
  atk: number // float, ≥ 0
  def_: number // float, ≥ 0 (trailing underscore matches the Python model)
  actual_hp?: number // float, ≥ 0 (real level, for future union raid)
  actual_atk?: number
  actual_def?: number
  skill_levels: SkillLevels
  overload_options: OverloadOption[] // may be empty
  pve_cube: PveCube | null // PVE cube only
}

// Constraint bounds, mirrored from the Pydantic Field(...) declarations so the
// client-side validation and the backend agree on exactly one set of rules.
export const CONSTRAINTS = {
  level: { min: 1 },
  core_level: { min: 0 },
  hp: { min: 0 },
  atk: { min: 0 },
  def_: { min: 0 },
  skill: { min: 1, max: 10 },
  cubeLevel: { min: 1, max: 15 },
} as const
