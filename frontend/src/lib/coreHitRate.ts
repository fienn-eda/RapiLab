// 코어 지름 하나가 무기별 코어 명중률로 무엇을 뜻하는지. 보스 폼이 「58.67」
// 옆에 「AR 61% · SMG 28% · SG 6%」를 적어, 값이 opaque하지 않고 틀린 값이
// 눈에 띄게 한다.
//
// SOURCE OF TRUTH: backend/app/accuracy.py
//   지름 = 기본지름 × (1 − 명중/1.10) · p = min(1, (코어/지름)²)
//
// 상수를 여기 옮겨 적는 것은 elementAdvantage.ts와 같은 관례다. 다만 원소
// 상성과 달리 이 표는 수집 데이터(`shot_detail.start_accuracy_circle_scale`)에서
// 파생돼 실제로 바뀐 적이 있으므로, 표류는
// backend/tests/test_frontend_mirrors_accuracy.py가 잡는다.

export type WeaponClass = 'AR' | 'SG' | 'SMG' | 'MG' | 'SR' | 'RL'

/** 탄착군이 한 점으로 수렴하는 명중률. 무기별 상수가 아니라 게임 전체의 상수다. */
export const ZERO_SPREAD_HIT_RATE = 1.1

/** 명중 0%에서 각 무기가 그리는 탄착군의 지름. */
export const WEAPON_SPREAD_DIAMETER: Record<WeaponClass, number> = {
  AR: 75,
  SG: 250,
  SMG: 110,
  MG: 10,
  SR: 10,
  RL: 10,
}

/** 이 무기가 이 명중률에서 그리는 탄착군의 지름. 명중이 특이점을 넘어도 음수가
 * 되지 않고, 음수 명중이면 반대로 넓어진다. */
export const spreadDiameter = (weapon: WeaponClass, hitRate: number): number =>
  WEAPON_SPREAD_DIAMETER[weapon] * Math.max(0, 1 - hitRate / ZERO_SPREAD_HIT_RATE)

/** 조준점이 코어 중심에 있을 때 코어에 드는 발의 비율. */
export const coreHitRate = (
  weapon: WeaponClass,
  hitRate: number,
  coreDiameter: number,
): number => {
  const diameter = spreadDiameter(weapon, hitRate)
  if (diameter <= coreDiameter) return 1
  return (coreDiameter / diameter) ** 2
}

export interface CoreHitRateGroup {
  /** 지름이 같아 값도 같은 무기들, `·`로 이어 붙인 것. */
  label: string
  rate: number
}

/** 무버프 기준으로 이 코어가 무기별로 무엇을 뜻하는지, **탄착군이 넓은 순**.
 *
 * 지름이 같은 무기(MG·SR·RL은 셋 다 10)를 한 줄로 묶는 이유는 따로 적으면 같은
 * 값을 세 번 적게 되어서고, 전수를 내는 이유는 화면이 「나머지는 100%」를
 * 하드코딩하지 않게 하기 위해서다 — 코어가 10보다 작으면 그 말이 거짓이 된다.
 *
 * 넓은 순으로 두면 값이 낮은 무기가 먼저 오고, 탄착군 10이라 웬만한 코어에서
 * 늘 100%인 MG·SR·RL이 규칙 하나로 맨 뒤에 놓인다 — 그 셋이 앞에 서면 정작
 * 갈리는 값을 뒤로 민다. 명중률이 아니라 지름으로 정렬하므로 값이 바뀌어도
 * 순서가 뛰지 않는다. */
export const coreHitRateGroups = (coreDiameter: number): CoreHitRateGroup[] => {
  const byDiameter = new Map<number, WeaponClass[]>()
  for (const weapon of Object.keys(WEAPON_SPREAD_DIAMETER) as WeaponClass[]) {
    const diameter = WEAPON_SPREAD_DIAMETER[weapon]
    byDiameter.set(diameter, [...(byDiameter.get(diameter) ?? []), weapon])
  }
  return [...byDiameter.entries()]
    .sort(([a], [b]) => b - a)
    .map(([, weapons]) => ({
      label: weapons.join('·'),
      rate: coreHitRate(weapons[0], 0, coreDiameter),
    }))
}
