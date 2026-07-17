// Owns the list of Nikke drafts the user is editing (their roster) and the
// add / update / remove operations over it.
//
// The roster is mirrored to localStorage: entering it costs ~35 fields per
// Nikke (overload alone is up to 24), so losing it to a page reload is the
// difference between a usable tool and an unusable one.

import { useCallback, useEffect, useRef, useState } from 'react'
import {
  makeEmptyDraft,
  mergeCollectorDrafts,
  mergeRosterDrafts,
  type NikkeDraft,
} from '../types/nikkeDraft'

export interface Roster {
  drafts: NikkeDraft[]
  addNikke: () => void
  updateNikke: (id: string, next: NikkeDraft) => void
  removeNikke: (id: string) => void
  importDrafts: (
    incoming: NikkeDraft[],
    source?: 'exia' | 'collector',
  ) => { added: number; updated: number }
}

const STORAGE_KEY = 'nikke-roster'

const readStoredRoster = (initial: NikkeDraft[]): NikkeDraft[] => {
  const raw = localStorage.getItem(STORAGE_KEY)
  if (raw === null) return initial
  try {
    return JSON.parse(raw) as NikkeDraft[]
  } catch {
    // Unparseable means unrecoverable, but start usable rather than dead -
    // never let a bad key keep the form from opening.
    console.warn(`Discarding an unreadable stored roster (${STORAGE_KEY}).`)
    return initial
  }
}

export const useRoster = (initial: NikkeDraft[] = []): Roster => {
  const [drafts, setDrafts] = useState<NikkeDraft[]>(() =>
    readStoredRoster(initial),
  )

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(drafts))
  }, [drafts])

  const draftsRef = useRef(drafts)
  useEffect(() => {
    draftsRef.current = drafts
  }, [drafts])

  const importDrafts = useCallback(
    (incoming: NikkeDraft[], source: 'exia' | 'collector' = 'exia') => {
      const merge = source === 'collector' ? mergeCollectorDrafts : mergeRosterDrafts
      const result = merge(draftsRef.current, incoming)
      setDrafts(result.drafts)
      return { added: result.added, updated: result.updated }
    },
    [],
  )

  const addNikke = useCallback(() => {
    setDrafts((current) => [...current, makeEmptyDraft()])
  }, [])

  const updateNikke = useCallback((id: string, next: NikkeDraft) => {
    setDrafts((current) =>
      current.map((draft) => (draft.id === id ? next : draft)),
    )
  }, [])

  const removeNikke = useCallback((id: string) => {
    setDrafts((current) => current.filter((draft) => draft.id !== id))
  }, [])

  return { drafts, addNikke, updateNikke, removeNikke, importDrafts }
}
