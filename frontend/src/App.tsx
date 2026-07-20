// ShiftyPad investment-data input: the user builds their roster by entering one
// UserNikkeState per owned Nikke, then requests deck recommendations against
// a boss profile (POST /api/recommend, via RecommendPanel).

import { useMemo } from 'react'
import './App.css'
import { useRoster } from './hooks/useRoster'
import { getValidRoster } from './types/nikkeDraft'
import { NikkeCard } from './components/NikkeCard'
import { RecommendPanel } from './components/RecommendPanel'
import { ImportRosterButton } from './components/ImportRosterButton'
import { SyncRosterPanel } from './components/SyncRosterPanel'

function App() {
  const { drafts, addNikke, updateNikke, removeNikke, importDrafts } =
    useRoster()

  const validRoster = useMemo(() => getValidRoster(drafts), [drafts])
  const readyCount = validRoster.length

  return (
    <div className="app">
      <header className="app__header">
        <h1 className="app__title">NIKKE Deck Builder</h1>
        <p className="app__subtitle">
          Enter each owned Nikke&rsquo;s investment data from ShiftyPad.
        </p>
        <p className="app__note">
          All Nikkes are simulated wearing a Resilience Cube Lv.15.
        </p>
      </header>

      <main className="app__main">
        <ImportRosterButton onImport={importDrafts} />
        <SyncRosterPanel onImport={importDrafts} />

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

        <RecommendPanel roster={validRoster} />
      </main>

      <footer className="app__footer">
        {readyCount} of {drafts.length}{' '}
        {drafts.length === 1 ? 'Nikke' : 'Nikkes'} ready
      </footer>
    </div>
  )
}

export default App
