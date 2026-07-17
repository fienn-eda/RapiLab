// Imports an ExiaInvasion export file into the roster: read file -> parse ->
// merge (via onImport) -> show a summary. Parse/format failures surface as a
// user-facing error rather than crashing. ATK/HP/DEF and cube stay manual.

import { useState } from 'react'
import {
  parseExiaExport,
  type ImportWarning,
} from '../lib/exiaImport'
import { parseRosterJson } from '../lib/rosterImport'
import type { NikkeDraft } from '../types/nikkeDraft'

interface ImportRosterButtonProps {
  onImport: (
    drafts: NikkeDraft[],
    source: 'exia' | 'collector',
  ) => { added: number; updated: number }
}

const summarise = (
  added: number,
  updated: number,
  warnings: ImportWarning[],
): string => {
  const parts = [`${added} added`, `${updated} updated`]
  const dropped = warnings.filter((w) => w.kind === 'dropped-overload').length
  if (dropped > 0) parts.push(`${dropped} had unsupported overload lines dropped`)
  const skipped = warnings.filter((w) => w.kind === 'skipped-character').length
  if (skipped > 0) parts.push(`${skipped} skipped`)
  return parts.join(', ')
}

export function ImportRosterButton({ onImport }: ImportRosterButtonProps) {
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const handleChange = async (
    event: React.ChangeEvent<HTMLInputElement>,
  ) => {
    const file = event.target.files?.[0]
    event.target.value = '' // allow re-importing the same file
    if (!file) return

    setError(null)
    setMessage(null)

    let raw: unknown
    try {
      raw = JSON.parse(await file.text())
    } catch {
      setError('Could not read the file as JSON.')
      return
    }

    try {
      if (raw && typeof raw === 'object' && 'units' in raw) {
        const { drafts, warnings } = parseRosterJson(raw)
        const { added, updated } = onImport(drafts, 'collector')
        const parts = [`${added} added`, `${updated} updated`]
        if (warnings.length > 0) parts.push(`${warnings.length} skipped`)
        setMessage(parts.join(', '))
      } else {
        const { drafts, warnings } = parseExiaExport(raw)
        const { added, updated } = onImport(drafts, 'exia')
        setMessage(summarise(added, updated, warnings))
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Import failed.')
    }
  }

  return (
    <div className="import">
      <label className="btn btn--ghost">
        Import roster
        <input
          type="file"
          accept="application/json,.json"
          className="import__input"
          aria-label="Import roster"
          onChange={handleChange}
        />
      </label>
      {message && <p className="import__message">{message}</p>}
      {error && (
        <p className="import__error" role="alert">
          {error}
        </p>
      )}
    </div>
  )
}
