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

/** 화면에서 잰 길이를 엔진 단위로 옮길 때 기준자로 쓸 수 있는 무기, 정확한
 * 순서(=조준원이 큰 순).
 *
 * MG·SR·RL은 뺀다 — 탄착군이 10이라 화면에서 몇 px밖에 안 되고, 판독 ±1px이
 * 13%가 된다. 반대로 SG는 250이라 같은 ±1px이 0.5%다. */
export const REFERENCE_WEAPONS = ['SG', 'SMG', 'AR'] as const satisfies readonly WeaponClass[]

/** 같은 프레임(같은 렌더 스케일)에서 잰 코어와 조준원의 픽셀로 코어의 엔진
 * 단위를 낸다.
 *
 *     코어_엔진 = 코어_px × (조준원_엔진 / 조준원_px)
 *
 * **비율만 쓰므로 해상도·창모드·전체화면·레터박스·녹화 업스케일이 전부
 * 약분된다.** 화면 픽셀을 엔진 단위로 옮기는 해상도 기반 일반형은 없다 —
 * 있다고 적었다가 틀렸다(`docs/measurements/accuracy-circle-and-core-px.md` §해석).
 *
 * 이 함수가 못 지켜주는 조건 둘: 조준원이 **무버프**여야 하고(명중 버프가
 * 조준원을 좁혀 코어가 과대로 나온다), 두 길이가 **같은 창 설정**에서 나와야
 * 한다. 잴 수 없는 입력에는 `null`.
 */
export const coreDiameterFromMeasurement = (
  corePx: number,
  reticlePx: number,
  reticleWeapon: WeaponClass,
): number | null => {
  if (!Number.isFinite(corePx) || !Number.isFinite(reticlePx)) return null
  if (corePx <= 0 || reticlePx <= 0) return null
  return corePx * (WEAPON_SPREAD_DIAMETER[reticleWeapon] / reticlePx)
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
