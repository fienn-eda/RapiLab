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

// Scoped to the input: a field's HelpTip button is named "<label> 설명", so a
// bare label regex now matches both.
const numberField = (label: RegExp) => screen.getByRole('spinbutton', { name: label })

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
    await userEvent.clear(numberField(/차지속도 합계/))
    await userEvent.type(numberField(/차지속도 합계/), '12.18')
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
    await userEvent.type(numberField(/차지속도 합계/), '5.51')
    await userEvent.type(numberField(/최대장탄 오버로드/), '85.37')
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
    expect(screen.getByText(/합계만 알고 있어/).closest('.help-tip__bubble')).not.toBeNull()
  })

  it('hangs each standing caveat off the field it is about', () => {
    // Three paragraphs above the button pushed 계산 off a short screen, and
    // they are read once. The boss form already solved this with HelpTip.
    stubFetch()
    renderPanel()
    for (const label of ['하모니 큐브', '차지속도 합계', '최대장탄 오버로드']) {
      expect(screen.getByRole('button', { name: `${label} 설명` })).toBeInTheDocument()
    }
  })

  it('reports an error instead of a ladder when the request fails', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(
      { ok: false, status: 422, json: () => Promise.resolve({ detail: 'nope' }) }))
    renderPanel()
    await userEvent.click(screen.getByRole('button', { name: '계산' }))
    expect(await screen.findByRole('alert')).toBeInTheDocument()
  })

  it('defaults to the harmony cube the rest of the app assumes', async () => {
    const fetchMock = stubFetch()
    renderPanel()
    await userEvent.click(screen.getByRole('button', { name: '계산' }))
    await waitFor(() => expect(fetchMock).toHaveBeenCalled())
    expect(JSON.parse(fetchMock.mock.calls[0][1].body).cube).toBe('resilience')
  })

  it('sends the Tactical Bear when that is the cube picked', async () => {
    // Its rounds decide whether a reload lands inside the window, which is two
    // different shot counts on identical gear - so it is a question here rather
    // than the app-wide assumption it is everywhere else.
    const fetchMock = stubFetch()
    renderPanel()
    await userEvent.selectOptions(screen.getByLabelText('하모니 큐브'), 'tactical_bear')
    await userEvent.click(screen.getByRole('button', { name: '계산' }))
    await waitFor(() => expect(fetchMock).toHaveBeenCalled())
    expect(JSON.parse(fetchMock.mock.calls[0][1].body).cube).toBe('tactical_bear')
  })

  it('says the magazine is assumed full at window start', () => {
    stubFetch()
    renderPanel()
    expect(screen.getByText(/탄창은 가득/).closest('.help-tip__bubble')).not.toBeNull()
  })

  it('says the Tactical Bear refund counter is assumed to start at zero', () => {
    // Weaker than the magazine assumption beside it - that counter is
    // cumulative over the fight and Asura's reload does not touch it - so it
    // belongs on the cube, not buried in the magazine's sentence.
    stubFetch()
    renderPanel()
    expect(screen.getByText(/환급 카운터/).closest('.help-tip__bubble')).not.toBeNull()
  })
})
