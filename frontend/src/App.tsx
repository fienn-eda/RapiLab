// ShiftyPad investment-data input: the user builds their roster by entering one
// UserNikkeState per owned Nikke. Fully client-side — no backend calls yet.

import { useMemo } from 'react'
import './App.css'
import { useRoster } from './hooks/useRoster'
import { validateDraft } from './types/nikkeDraft'
import { NikkeCard } from './components/NikkeCard'

function App() {
  const { drafts, addNikke, updateNikke, removeNikke } = useRoster()

  const readyCount = useMemo(
    () => drafts.filter((draft) => validateDraft(draft).value).length,
    [drafts],
  )

  return (
    <div className="app">
      <header className="app__header">
        <h1 className="app__title">NIKKE Deck Builder</h1>
        <p className="app__subtitle">
          Enter each owned Nikke&rsquo;s investment data from ShiftyPad.
        </p>
      </header>

      <main className="app__main">
        {drafts.length === 0 ? (
          <div className="empty">
            <p className="empty__text">Your roster is empty.</p>
            <button type="button" className="btn btn--primary" onClick={addNikke}>
              + Add your first Nikke
            </button>
          </div>
        ) : (
          <>
            <div className="roster">
              {drafts.map((draft, index) => (
                <NikkeCard
                  key={draft.id}
                  draft={draft}
                  index={index}
                  onChange={(next) => updateNikke(draft.id, next)}
                  onRemove={() => removeNikke(draft.id)}
                />
              ))}
            </div>
            <button type="button" className="btn btn--primary" onClick={addNikke}>
              + Add Nikke
            </button>
          </>
        )}
      </main>

      <footer className="app__footer">
        {readyCount} of {drafts.length}{' '}
        {drafts.length === 1 ? 'Nikke' : 'Nikkes'} ready
      </footer>
    </div>
  )
}

export default App
