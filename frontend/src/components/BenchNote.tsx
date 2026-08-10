// The bench line shared by both raid-result views (RaidResults and
// DraftResults): units the allocation left out of every deck.

import { HELP } from '../lib/helpText'
import { HelpText } from './HelpText'

interface BenchNoteProps {
  leftoverSlugs: string[]
  nameFor: (slug: string) => string
}

export function BenchNote({ leftoverSlugs, nameFor }: BenchNoteProps) {
  if (leftoverSlugs.length === 0) return null
  return (
    <p className="raid-results__leftover">
      <HelpText>{HELP.results.bench(leftoverSlugs.map(nameFor).join(', '))}</HelpText>
    </p>
  )
}
