import { afterEach, describe, expect, it, vi } from 'vitest'
import { postChargeWindow } from './chargeWindow'

const WIRE = {
  interval: 0.53,
  magazine: 22,
  charge_speed_percent: 0.0286,
  current: { low_shots: 18, low_probability: 0.132, high_shots: 19, high_probability: 0.868 },
  thresholds: [
    {
      charge_speed_percent: 0,
      interval: 0.53,
      outcome: { low_shots: 18, low_probability: 0.132, high_shots: 19, high_probability: 0.868 },
    },
  ],
  notes: ['탄창이 창 안에서 비어 재장전이 걸립니다'],
}

afterEach(() => vi.unstubAllGlobals())

describe('postChargeWindow', () => {
  it('maps the snake_case wire shape to camelCase', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(
      { ok: true, json: () => Promise.resolve(WIRE) }))
    const result = await postChargeWindow({
      slug: 'scarlet-black-shadow', roster: [], withLiberalio: true,
      overrides: { chargeSpeedLines: null, maxAmmoPercent: null, reloadSpeedPercent: null },
    })
    expect(result.current.highShots).toBe(19)
    expect(result.current.highProbability).toBeCloseTo(0.868)
    expect(result.thresholds[0].chargeSpeedPercent).toBe(0)
    expect(result.thresholds[0].outcome.lowShots).toBe(18)
    expect(result.notes).toHaveLength(1)
    // The ladder's summary line and its current-row marker read these three;
    // a typo in any of them prints "탄창 undefined발" with nothing failing.
    expect(result.interval).toBe(0.53)
    expect(result.magazine).toBe(22)
    expect(result.chargeSpeedPercent).toBe(0.0286)
  })

  it('sends snake_case field names to the backend', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve(WIRE) })
    vi.stubGlobal('fetch', fetchMock)
    await postChargeWindow({
      slug: 'neon-vision-eye', roster: [], withLiberalio: false,
      overrides: { chargeSpeedLines: [4.33, 4.33], maxAmmoPercent: null, reloadSpeedPercent: null },
    })
    const body = JSON.parse(fetchMock.mock.calls[0][1].body)
    expect(body.with_liberalio).toBe(false)
    expect(body.overrides.charge_speed_lines).toEqual([4.33, 4.33])
  })

  it('throws RecommendApiError on a non-ok response', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(
      { ok: false, status: 422, json: () => Promise.resolve({ detail: 'nope' }) }))
    await expect(postChargeWindow({
      slug: 'liter', roster: [], withLiberalio: false,
      overrides: { chargeSpeedLines: null, maxAmmoPercent: null, reloadSpeedPercent: null },
    })).rejects.toMatchObject({ status: 422 })
  })
})
