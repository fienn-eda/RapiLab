// 릴리스마다 엔진 응답이 무슨 필드를 갖고 있었는지의 표.
//
// 왜 필요한가: 저장한 결과(SavedRun)는 그때의 응답을 그대로 박제한 기록이고,
// 캐시와 달리 로스터 재동기화에도 앱 업데이트에도 살아남는다. 그래서 앱을
// 업데이트하면 **옛 모양이 새 화면으로 들어온다.** 2026-08-22의 검은 화면이
// 정확히 그것이었고, 그 전에도 한 번 같은 일이 있었다. 화면이 새 필드를 무가드로
// 읽는 순간 릴리스가 나가야 알 수 있었다 - 이 표가 그것을 스위트로 옮긴다.
//
// **새 릴리스를 낼 때 이 표에 한 줄 더할 것.** 필드 목록은 손으로 세지 말고
// 그 태그에서 뽑을 것:
//   git show <tag>:frontend/src/types/recommend.ts
//
// 태그만으로는 부족하다는 것도 이 표가 말한다: 「개발 빌드」 행은 어느 태그와도
// 맞지 않는데, Fienn의 저장소에 실제로 그 모양으로 남아 있었다. 릴리스 사이에
// 저장된 것이 있으므로 관측된 모양도 같이 싣는다.

export interface LegacyShape {
  /** 이 모양을 낸 빌드. 태그가 아닌 것은 실제 보관물에서 읽어낸 것이다. */
  label: string
  /** 그때 DeckRecommendation이 갖고 있던 필드 이름. */
  deckFields: string[]
  /** 그때 BossProfile이 갖고 있던 필드 이름. */
  bossFields: string[]
}

const DAMAGE = ['deck', 'total_damage', 'burst_damage', 'normal_attack_damage', 'skill_damage']

const BOSS_V0 = [
  'element',
  'core_hittable',
  'enemy_def',
  'fight_duration',
  'part_destructible',
  'effective_range_band',
]

const BOSS_OBSERVED = [
  ...BOSS_V0,
  'pierce_hits_body_behind_core',
  'core_diameter_px',
  'elemental_interrupt_required',
]

const BOSS_V012 = [...BOSS_OBSERVED, 'spawns_adds', 'part_destruction_times']

export const LEGACY_SHAPES: LegacyShape[] = [
  {
    label: 'v0.1.0 · v0.1.1',
    deckFields: DAMAGE,
    bossFields: BOSS_V0,
  },
  {
    // 어느 태그와도 안 맞는다 - 릴리스 사이의 개발 빌드로 저장된 유니온 결과에서
    // 읽어냈다(2026-08-10). hold_burst_slugs만 있고 나머지 플레이 지시는 없다.
    label: '개발 빌드 (2026-08-10 관측)',
    deckFields: [...DAMAGE, 'hold_burst_slugs'],
    bossFields: BOSS_OBSERVED,
  },
  {
    label: 'v0.1.2 · v0.1.3 · v0.1.4',
    deckFields: [
      ...DAMAGE,
      'hold_burst_slugs',
      'tap_fire_slugs',
      'partial_charge_slugs',
      'partial_charge_full_rounds',
      'seating',
    ],
    bossFields: BOSS_V012,
  },
  {
    label: 'v0.1.5',
    deckFields: [
      ...DAMAGE,
      'hold_burst_slugs',
      'tap_fire_slugs',
      'partial_charge_slugs',
      'partial_charge_full_rounds',
      'hold_fire_slugs',
      'seating',
      'gauge_delay_seconds',
      'gauge_bound_cycles',
      'total_cycles',
    ],
    bossFields: [...BOSS_V012, 'hold_fire_despite_adds'],
  },
]

/** 필드마다 하나씩의 표본 값. **비어 있지 않은 값을 쓰는 것이 요점이다** - 빈
 * 배열이면 화면이 그 분기를 아예 안 그려서, 있는 필드와 없는 필드가 섞인 조합을
 * 못 밟는다(예: tap_fire_slugs는 있는데 partial_charge_slugs가 없는 모양). */
const SAMPLE: Record<string, unknown> = {
  deck: ['a', 'b', 'c', 'd', 'e'],
  total_damage: 1_000_000,
  burst_damage: 500_000,
  normal_attack_damage: 400_000,
  skill_damage: 100_000,
  hold_burst_slugs: ['d'],
  tap_fire_slugs: ['b'],
  partial_charge_slugs: ['b'],
  partial_charge_full_rounds: { b: 2 },
  hold_fire_slugs: ['c'],
  seating: { a: { allies: ['b', 'c'], seats: [2, 4] } },
  gauge_delay_seconds: 4.3,
  gauge_bound_cycles: 11,
  total_cycles: 14,

  element: 'Fire',
  core_hittable: true,
  pierce_hits_body_behind_core: false,
  enemy_def: 31784,
  fight_duration: 180,
  part_destructible: true,
  spawns_adds: true,
  hold_fire_despite_adds: false,
  part_destruction_times: [30],
  effective_range_band: 'mid',
  core_diameter_px: 120,
  elemental_interrupt_required: true,
}

const pick = (names: string[]): Record<string, unknown> =>
  Object.fromEntries(names.map((name) => [name, SAMPLE[name]]))

/** 그 릴리스가 실제로 보냈을 모양의 덱. 타입 단언이 필요한 것이 이 표의 요점이다 -
 * 저장된 JSON은 오늘의 타입을 지킬 의무가 없다. */
export const legacyDeck = (shape: LegacyShape): Record<string, unknown> =>
  pick(shape.deckFields)

export const legacyBoss = (shape: LegacyShape): Record<string, unknown> =>
  pick(shape.bossFields)
