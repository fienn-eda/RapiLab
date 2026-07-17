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
      screen.getByLabelText(/import from exiainvasion/i),
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
      screen.getByLabelText(/import from exiainvasion/i),
      file('{ not json'),
    )

    expect(await screen.findByText(/could not read/i)).toBeInTheDocument()
    expect(onImport).not.toHaveBeenCalled()
  })

  it('shows an error when the JSON is not an export', async () => {
    const onImport = vi.fn(() => ({ added: 0, updated: 0 }))
    render(<ImportRosterButton onImport={onImport} />)

    await userEvent.upload(
      screen.getByLabelText(/import from exiainvasion/i),
      file('{"foo": 1}'),
    )

    expect(await screen.findByText(/elements/i)).toBeInTheDocument()
    expect(onImport).not.toHaveBeenCalled()
  })
})
