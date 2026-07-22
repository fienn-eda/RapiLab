// ShiftyPad investment-data input: the user syncs their roster from
// blablalink per account (profile), then requests deck recommendations
// against a boss profile (POST /api/recommend, via RecommendPanel).

import { useMemo } from 'react'
import './App.css'
import { useProfiles } from './hooks/useProfiles'
import { getValidRoster } from './types/nikkeDraft'
import { getResult } from './types/profile'
import { NikkeCard } from './components/NikkeCard'
import { ProfileSwitcher } from './components/ProfileSwitcher'
import { RecommendPanel } from './components/RecommendPanel'
import { SyncRosterPanel } from './components/SyncRosterPanel'
import type { NikkeDraft } from './types/nikkeDraft'

// A stable reference so useMemo below doesn't see a "new" roster every render
// when there's no active profile (a fresh `?? []` literal would).
const NO_ROSTER: NikkeDraft[] = []

function App() {
  const { state, activeProfile, upsertProfile, switchProfile, deleteProfile, saveResult } =
    useProfiles()

  const drafts = activeProfile?.roster ?? NO_ROSTER
  const validRoster = useMemo(() => getValidRoster(drafts), [drafts])

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

      <ProfileSwitcher
        profiles={Object.values(state.profiles)}
        activeOpenId={state.activeOpenId}
        onSwitch={switchProfile}
        onDelete={deleteProfile}
      />

      <main className="app__main">
        <SyncRosterPanel onImport={upsertProfile} />

        {activeProfile === null ? (
          <div className="empty">
            <p className="empty__text">
              No synced account yet. Sync from blablalink above to get started.
            </p>
          </div>
        ) : (
          <>
            <div className="roster">
              {drafts.map((draft, index) => (
                <NikkeCard
                  key={draft.id ?? draft.character_slug}
                  draft={draft}
                  index={index}
                />
              ))}
            </div>
            <RecommendPanel
              // Keying on the active profile forces a full remount (and thus
              // a reset of useRecommendRaid/useRecommend hook state) on
              // profile switch. Without this, a raid/draft request that
              // outlives a switch (1-2 min) would land against the shared
              // hook instance and leak its result/error into whichever
              // profile happens to be active when the response arrives.
              key={state.activeOpenId ?? 'none'}
              roster={validRoster}
              activeOpenId={state.activeOpenId}
              getCached={(hash) => (activeProfile ? getResult(activeProfile, hash) : null)}
              onResult={(args) => {
                if (state.activeOpenId) saveResult({ openId: state.activeOpenId, ...args })
              }}
              restoreInputs={activeProfile?.lastInputs ?? null}
              restoreResult={
                activeProfile && activeProfile.lastResultHash
                  ? getResult(activeProfile, activeProfile.lastResultHash)
                  : null
              }
            />
          </>
        )}
      </main>

      {activeProfile !== null && (
        <footer className="app__footer">
          {validRoster.length} of {drafts.length}{' '}
          {drafts.length === 1 ? 'Nikke' : 'Nikkes'} ready
        </footer>
      )}
    </div>
  )
}

export default App
