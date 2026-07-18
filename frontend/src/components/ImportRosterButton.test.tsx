import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ImportRosterButton } from './ImportRosterButton'
import type { NikkeDraft } from '../types/nikkeDraft'

const exportJson = () =>
  JSON.stringify({
    synchroLevel: 663,
    elements: {
      Electronic: [
        {
          name_en: 'Ada',
          skill1_level: 10,
          skill2_level: 10,
          skill_burst_level: 10,
          limit_break: { grade: 0, core: 0 },
          equipments: { '0': [], '1': [], '2': [], '3': [] },
        },
      ],
    },
  })

const file = (contents: string) =>
  new File([contents], 'FIENN.json', { type: 'application/json' })

describe('ImportRosterButton', () => {
  it('parses the chosen file, calls onImport, and shows a summary', async () => {
    const onImport = vi.fn((_drafts: NikkeDraft[]) => ({ added: 1, updated: 0 }))
    render(<ImportRosterButton onImport={onImport} />)

    await userEvent.upload(
      screen.getByLabelText(/import roster/i),
      file(exportJson()),
    )

    await waitFor(() => expect(onImport).toHaveBeenCalledTimes(1))
    expect(onImport.mock.calls[0][0][0].character_slug).toBe('ada-wong')
    expect(await screen.findByText(/1 added/i)).toBeInTheDocument()
  })

  it('shows an error and does not call onImport when the file is not JSON', async () => {
    const onImport = vi.fn(() => ({ added: 0, updated: 0 }))
    render(<ImportRosterButton onImport={onImport} />)

    await userEvent.upload(
      screen.getByLabelText(/import roster/i),
      file('{ not json'),
    )

    expect(await screen.findByText(/could not read/i)).toBeInTheDocument()
    expect(onImport).not.toHaveBeenCalled()
  })

  it('shows an error when the JSON is not an export', async () => {
    const onImport = vi.fn(() => ({ added: 0, updated: 0 }))
    render(<ImportRosterButton onImport={onImport} />)

    await userEvent.upload(
      screen.getByLabelText(/import roster/i),
      file('{"foo": 1}'),
    )

    expect(await screen.findByText(/elements/i)).toBeInTheDocument()
    expect(onImport).not.toHaveBeenCalled()
  })

  it('imports a collector roster.json (units) with raid-400 stats', async () => {
    const onImport = vi.fn((_d: NikkeDraft[], _s: 'exia' | 'collector') => ({ added: 1, updated: 0 }))
    render(<ImportRosterButton onImport={onImport} />)
    const json = JSON.stringify({
      synchroLevel: 663,
      units: [
        {
          resource_id: 16,
          name_en: 'Rapi: Red Hood',
          raid400: { hp: 3532402, atk: 143543, def: 20986 },
          skill_levels: { skill1: 10, skill2: 10, burst: 10 },
          pve_cube: null,
        },
        {
          resource_id: 999999,
          name_en: 'Not Encoded Unit',
          raid400: { hp: 1, atk: 2, def: 3 },
          skill_levels: { skill1: 10, skill2: 10, burst: 10 },
          pve_cube: null,
        },
      ],
    })
    await userEvent.upload(screen.getByLabelText(/import roster/i), file(json))
    await waitFor(() => expect(onImport).toHaveBeenCalledTimes(1))
    expect(onImport.mock.calls[0][1]).toBe('collector')
    expect(onImport.mock.calls[0][0][0].character_slug).toBe('rapi-red-hood')
    expect(onImport.mock.calls[0][0][0].atk).toBe('143543')
    // Unencoded units are kept, and the user is told which ones are unsupported.
    expect(await screen.findByText(/Not Encoded Unit/)).toBeInTheDocument()
  })
})
