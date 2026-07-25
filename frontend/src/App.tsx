// ShiftyPad investment-data input: the user syncs their roster from
// blablalink per account (profile), then requests deck recommendations
// against a boss profile (POST /api/recommend, via RecommendPanel).

import { useMemo, useState } from 'react'
import './App.css'
import { useProfiles } from './hooks/useProfiles'
import { usePortraitManifest } from './hooks/usePortraitManifest'
import { getValidRoster } from './types/nikkeDraft'
import { getResult } from './types/profile'
import { useSupportedUnits } from './hooks/useSupportedUnits'
import { ProfileSwitcher } from './components/ProfileSwitcher'
import { RosterGrid } from './components/RosterGrid'
import { RecommendPanel } from './components/RecommendPanel'
import { SyncRosterPanel } from './components/SyncRosterPanel'
import type { NikkeDraft } from './types/nikkeDraft'

// A stable reference so useMemo below doesn't see a "new" roster every render
// when there's no active profile (a fresh `?? []` literal would).
const NO_ROSTER: NikkeDraft[] = []

type Tab = 'roster' | 'recommend'

const TABS: { id: Tab; label: string }[] = [
  { id: 'roster', label: 'Roster' },
  { id: 'recommend', label: 'Recommend' },
]

function App() {
  const { state, activeProfile, upsertProfile, switchProfile, deleteProfile, saveResult } =
    useProfiles()
  const { portraitFor } = usePortraitManifest()
  // The Roster tab needs names, elements and the supported/unsupported split.
  // RecommendPanel loads the same list for itself: making it a prop instead
  // would rewrite 22 of its test's render sites to save one GET of a small
  // static endpoint.
  const supportedUnits = useSupportedUnits()
  const [tab, setTab] = useState<Tab>('roster')

  const drafts = activeProfile?.roster ?? NO_ROSTER
  const validRoster = useMemo(() => getValidRoster(drafts), [drafts])

  // Breakthrough/core and the Favorite Item heart, for the palette chips and
  // the names in a result. It rides alongside the roster rather than in it:
  // validRoster is UserNikkeState, which mirrors the backend model, and none
  // of these fields exist there.
  const investmentFor = useMemo(() => {
    const bySlug = new Map(
      drafts.map((draft) => [
        draft.character_slug,
        { grade: draft.grade, core: draft.core, favoriteItem: draft.favorite_item },
      ]),
    )
    return (slug: string) => bySlug.get(slug) ?? {}
  }, [drafts])

  return (
    <div className="app">
      <header className="app__header">
        <h1 className="app__title">NIKKE Deck Builder</h1>
        <p className="app__subtitle">
          Sync your roster from blablalink, then have the engine build decks
          from it.
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

      {activeProfile === null ? (
        <main className="app__main">
          <SyncRosterPanel onImport={upsertProfile} />
          <div className="empty">
            <p className="empty__text">
              No synced account yet. Sync from blablalink above to get started.
            </p>
          </div>
        </main>
      ) : (
        <>
          <div className="tabs" role="tablist" aria-label="Sections">
            {TABS.map(({ id, label }) => (
              <button
                key={id}
                type="button"
                role="tab"
                id={`tab-${id}`}
                aria-controls={`panel-${id}`}
                aria-selected={tab === id}
                className={tab === id ? 'tabs__tab tabs__tab--active' : 'tabs__tab'}
                onClick={() => setTab(id)}
              >
                {label}
              </button>
            ))}
          </div>

          <main className="app__main">
            {/* Both panels stay mounted: a raid run takes 1-2 minutes, and
                unmounting RecommendPanel to switch tabs would abandon a request
                already in flight along with its unsaved result. */}
            <div
              role="tabpanel"
              id="panel-roster"
              aria-labelledby="tab-roster"
              hidden={tab !== 'roster'}
              className="panel"
            >
              <SyncRosterPanel onImport={upsertProfile} />
              {supportedUnits.error && <p className="field__error">{supportedUnits.error}</p>}
              <RosterGrid
                drafts={drafts}
                supportedUnits={supportedUnits.units}
                portraitFor={portraitFor}
              />
            </div>

            <div
              role="tabpanel"
              id="panel-recommend"
              aria-labelledby="tab-recommend"
              hidden={tab !== 'recommend'}
              className="panel"
            >
              <RecommendPanel
                // Keying on the active profile forces a full remount (and thus
                // a reset of useRecommendRaid/useRecommend hook state) on
                // profile switch. Without this, a raid/draft request that
                // outlives a switch (1-2 min) would land against the shared
                // hook instance and leak its result/error into whichever
                // profile happens to be active when the response arrives.
                key={state.activeOpenId ?? 'none'}
                roster={validRoster}
                investmentFor={investmentFor}
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
            </div>
          </main>
        </>
      )}

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
