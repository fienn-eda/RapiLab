import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { ChargeWindowPanel } from './ChargeWindowPanel'

const outcome = (low: number, high: number, highProbability: number) => ({
  low_shots: low, low_probability: 1 - highProbability,
  high_shots: high, high_probability: highProbability,
})

const WIRE = {
  interval: 0.53,
  magazine: 22,
  charge_speed_percent: 0,
  current: outcome(18, 19, 0.868),
  thresholds: [{ charge_speed_percent: 0, interval: 0.53, outcome: outcome(18, 19, 0.868) }],
  notes: [],
}

const ROSTER = [
  { character_slug: 'scarlet-black-shadow', atk: 100000 },
  { character_slug: 'liberalio', atk: 90000 },
]

const stubFetch = () => {
  const mock = vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve(WIRE) })
  vi.stubGlobal('fetch', mock)
  return mock
}

afterEach(() => vi.unstubAllGlobals())

describe('ChargeWindowPanel', () => {
  it('offers only the three units the calculator covers', () => {
    stubFetch()
    render(<ChargeWindowPanel roster={ROSTER} />)
    const select = screen.getByLabelText('유닛')
    expect(within(select).getAllByRole('option')).toHaveLength(3)
  })

  it('requests the ladder and renders it', async () => {
    const fetchMock = stubFetch()
    render(<ChargeWindowPanel roster={ROSTER} />)
    await userEvent.click(screen.getByRole('button', { name: '계산' }))
    await waitFor(() => expect(fetchMock).toHaveBeenCalled())
    expect(await screen.findByText(/19타 87%/)).toBeInTheDocument()
  })

  it('hides the Liberalio toggle when Liberalio is the subject', async () => {
    stubFetch()
    render(<ChargeWindowPanel roster={ROSTER} />)
    expect(screen.getByLabelText('리버렐리오 동반')).toBeInTheDocument()
    await userEvent.selectOptions(screen.getByLabelText('유닛'), 'liberalio')
    expect(screen.queryByLabelText('리버렐리오 동반')).not.toBeInTheDocument()
  })

  it('sends the typed overrides instead of the roster values', async () => {
    const fetchMock = stubFetch()
    render(<ChargeWindowPanel roster={ROSTER} />)
    await userEvent.clear(screen.getByLabelText(/차지속도 합계/))
    await userEvent.type(screen.getByLabelText(/차지속도 합계/), '12.18')
    await userEvent.click(screen.getByRole('button', { name: '계산' }))
    await waitFor(() => expect(fetchMock).toHaveBeenCalled())
    const body = JSON.parse(fetchMock.mock.calls[0][1].body)
    expect(body.overrides.charge_speed_lines).toEqual([12.18])
  })

  it('reports an error instead of a ladder when the request fails', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(
      { ok: false, status: 422, json: () => Promise.resolve({ detail: 'nope' }) }))
    render(<ChargeWindowPanel roster={ROSTER} />)
    await userEvent.click(screen.getByRole('button', { name: '계산' }))
    expect(await screen.findByRole('alert')).toBeInTheDocument()
  })

  it('says the magazine is assumed full at window start', () => {
    stubFetch()
    render(<ChargeWindowPanel roster={ROSTER} />)
    expect(screen.getByText(/탄창은 가득/)).toBeInTheDocument()
  })
})
