// Owns the list of Nikke drafts the user is editing (their roster) and the
// add / update / remove operations over it.

import { useCallback, useState } from 'react'
import { makeEmptyDraft, type NikkeDraft } from '../types/nikkeDraft'

export interface Roster {
  drafts: NikkeDraft[]
  addNikke: () => void
  updateNikke: (id: string, next: NikkeDraft) => void
  removeNikke: (id: string) => void
}

export const useRoster = (initial: NikkeDraft[] = []): Roster => {
  const [drafts, setDrafts] = useState<NikkeDraft[]>(initial)

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

  return { drafts, addNikke, updateNikke, removeNikke }
}
