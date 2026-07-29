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

// Stands in for App's /api/supported-units lookup, which falls back to the slug
// for a unit the list has not confirmed yet.
const NAMES: Record<string, string> = { 'scarlet-black-shadow': '홍련: 흑영' }
const nameFor = (slug: string) => NAMES[slug] ?? slug

const renderPanel = () => render(<ChargeWindowPanel roster={ROSTER} nameFor={nameFor} />)

const stubFetch = () => {
  const mock = vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve(WIRE) })
  vi.stubGlobal('fetch', mock)
  return mock
}

afterEach(() => vi.unstubAllGlobals())

describe('ChargeWindowPanel', () => {
  it('offers only the three units the calculator covers', () => {
    stubFetch()
    renderPanel()
    const select = screen.getByLabelText('유닛')
    expect(within(select).getAllByRole('option')).toHaveLength(3)
  })

  it('labels the units from the shared name lookup, falling back to the slug', () => {
    stubFetch()
    renderPanel()
    const options = within(screen.getByLabelText('유닛')).getAllByRole('option')
    expect(options.map((option) => option.textContent)).toEqual(
      ['홍련: 흑영', 'liberalio', 'neon-vision-eye'])
  })

  it('requests the ladder and renders it', async () => {
    const fetchMock = stubFetch()
    renderPanel()
    await userEvent.click(screen.getByRole('button', { name: '계산' }))
    await waitFor(() => expect(fetchMock).toHaveBeenCalled())
    expect(await screen.findByText(/19타 87%/)).toBeInTheDocument()
  })

  it('hides the Liberalio toggle when Liberalio is the subject', async () => {
    stubFetch()
    renderPanel()
    expect(screen.getByLabelText('리버렐리오 동반')).toBeInTheDocument()
    await userEvent.selectOptions(screen.getByLabelText('유닛'), 'liberalio')
    expect(screen.queryByLabelText('리버렐리오 동반')).not.toBeInTheDocument()
  })

  it('sends the typed overrides instead of the roster values', async () => {
    const fetchMock = stubFetch()
    renderPanel()
    await userEvent.clear(screen.getByLabelText(/차지속도 합계/))
    await userEvent.type(screen.getByLabelText(/차지속도 합계/), '12.18')
    await userEvent.click(screen.getByRole('button', { name: '계산' }))
    await waitFor(() => expect(fetchMock).toHaveBeenCalled())
    const body = JSON.parse(fetchMock.mock.calls[0][1].body)
    expect(body.overrides.charge_speed_lines).toEqual([12.18])
  })

  it('leaves an empty override field as null rather than zero', async () => {
    const fetchMock = stubFetch()
    renderPanel()
    await userEvent.click(screen.getByRole('button', { name: '계산' }))
    await waitFor(() => expect(fetchMock).toHaveBeenCalled())
    const body = JSON.parse(fetchMock.mock.calls[0][1].body)
    // A 0 would mean "no charge speed at all"; null means "use the roster".
    expect(body.overrides.charge_speed_lines).toBeNull()
    expect(body.overrides.max_ammo_percent).toBeNull()
  })

  it('sends max ammo as a ratio and charge speed as a percent', async () => {
    const fetchMock = stubFetch()
    renderPanel()
    await userEvent.type(screen.getByLabelText(/차지속도 합계/), '5.51')
    await userEvent.type(screen.getByLabelText(/최대장탄 오버로드/), '85.37')
    await userEvent.click(screen.getByRole('button', { name: '계산' }))
    await waitFor(() => expect(fetchMock).toHaveBeenCalled())
    const body = JSON.parse(fetchMock.mock.calls[0][1].body)
    expect(body.overrides.charge_speed_lines).toEqual([5.51])
    expect(body.overrides.max_ammo_percent).toBeCloseTo(0.8537)
  })

  it('never asks for the Liberalio buff when Liberalio is the subject', async () => {
    const fetchMock = stubFetch()
    renderPanel()
    // The checkbox is on by default and remembers its state while hidden, so
    // the subject check has to happen at request time, not at render time.
    expect(screen.getByLabelText('리버렐리오 동반')).toBeChecked()
    await userEvent.selectOptions(screen.getByLabelText('유닛'), 'liberalio')
    await userEvent.click(screen.getByRole('button', { name: '계산' }))
    await waitFor(() => expect(fetchMock).toHaveBeenCalled())
    expect(JSON.parse(fetchMock.mock.calls[0][1].body).with_liberalio).toBe(false)
  })

  it('carries a standing caveat that the synced roster knows only the total', () => {
    stubFetch()
    renderPanel()
    expect(screen.getByText(/합계만 알고 있어/)).toBeInTheDocument()
  })

  it('reports an error instead of a ladder when the request fails', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(
      { ok: false, status: 422, json: () => Promise.resolve({ detail: 'nope' }) }))
    renderPanel()
    await userEvent.click(screen.getByRole('button', { name: '계산' }))
    expect(await screen.findByRole('alert')).toBeInTheDocument()
  })

  it('says the magazine is assumed full at window start', () => {
    stubFetch()
    renderPanel()
    expect(screen.getByText(/탄창은 가득/)).toBeInTheDocument()
  })
})
