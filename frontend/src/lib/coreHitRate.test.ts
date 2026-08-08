import { describe, it, expect } from 'vitest'
import {
  WEAPON_SPREAD_DIAMETER,
  ZERO_SPREAD_HIT_RATE,
  coreHitRate,
  coreHitRateGroups,
} from './coreHitRate'

describe('coreHitRate', () => {
  it('탄착군이 코어보다 작거나 같으면 전부 든다', () => {
    // SR의 기본 탄착군은 10이라 웬만한 코어 안에 통째로 들어간다.
    expect(coreHitRate('SR', 0, 33.33)).toBe(1)
    expect(coreHitRate('AR', 0, 75)).toBe(1)
  })

  it('그 밖에는 두 원의 면적비다', () => {
    // 코어 50 · AR 75 -> (50/75)^2. 설계문서 §6의 「기본 p 44.4%」와 같은 값이다.
    expect(coreHitRate('AR', 0, 50)).toBeCloseTo(0.4444, 4)
    expect(coreHitRate('SMG', 0, 50)).toBeCloseTo(0.2066, 4)
    expect(coreHitRate('SG', 0, 50)).toBeCloseTo(0.04, 4)
  })

  it('명중이 탄착군을 좁힌다', () => {
    // 명중 55%면 탄착군이 절반이 되고, 면적비라 p는 네 배가 된다.
    const half = coreHitRate('AR', ZERO_SPREAD_HIT_RATE / 2, 25)
    expect(half).toBeCloseTo(coreHitRate('AR', 0, 50), 10)
  })

  it('명중이 특이점을 넘어도 음수 지름이 되지 않는다', () => {
    // 도로시: 세렌디피티가 두 버프를 겹쳐 실제로 110%를 넘는다.
    expect(coreHitRate('SG', 1.5, 10)).toBe(1)
  })

  it('명중이 음수면 탄착군이 넓어진다', () => {
    // 마스트: 로맨틱 메이드의 Drunken.
    expect(coreHitRate('AR', -1.1, 50)).toBeCloseTo(coreHitRate('AR', 0, 25), 10)
  })
})

describe('coreHitRateGroups', () => {
  it('지름이 같은 무기를 한 줄로 묶고 탄착군 넓은 순으로 낸다', () => {
    // MG·SR·RL은 셋 다 탄착군 10이라 언제나 같은 값이다 - 따로 적으면 같은 말을
    // 세 번 하는 셈이고, 늘 100%라 앞에 서면 갈리는 값을 뒤로 민다.
    expect(coreHitRateGroups(33.33).map((g) => g.label)).toEqual([
      'SG', 'SMG', 'AR', 'MG·SR·RL',
    ])
  })

  it('코어 크기가 달라져도 순서가 뛰지 않는다', () => {
    // 명중률이 아니라 지름으로 정렬하는 이유 - 타이핑하는 동안 줄이 춤추면
    // 읽을 수 없다. AR이 100%에 닿아도 자리는 그대로다.
    const order = (c: number) => coreHitRateGroups(c).map((g) => g.label)
    expect(order(5)).toEqual(order(33.33))
    expect(order(200)).toEqual(order(33.33))
  })

  it('실측 코어의 값을 낸다', () => {
    // docs/measurements/accuracy-circle-and-core-px.md의 mid 33.33 행.
    const byLabel = Object.fromEntries(
      coreHitRateGroups(33.33).map((g) => [g.label, g.rate]),
    )
    expect(byLabel['AR']).toBeCloseTo(0.1975, 4)
    expect(byLabel['SMG']).toBeCloseTo(0.0918, 4)
    expect(byLabel['SG']).toBeCloseTo(0.0178, 4)
    expect(byLabel['MG·SR·RL']).toBe(1)
  })

  it('여섯 무기를 하나도 빠뜨리지 않는다', () => {
    // 화면이 「나머지는 100%」를 하드코딩하지 않으려면 그룹이 전수여야 한다.
    const covered = coreHitRateGroups(33.33).flatMap((g) => g.label.split('·'))
    expect(covered.sort()).toEqual(Object.keys(WEAPON_SPREAD_DIAMETER).sort())
  })
})
