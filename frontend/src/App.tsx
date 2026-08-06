// ShiftyPad investment-data input: the user syncs their roster from
// blablalink per account (profile), then requests deck recommendations
// against a boss profile (POST /api/recommend, via RecommendPanel).

import { useMemo, useState } from 'react'
import './App.css'
import { useProfiles } from './hooks/useProfiles'
import { usePortraitManifest } from './hooks/usePortraitManifest'
import { useEngineVersion } from './hooks/useEngineVersion'
import { getValidRoster } from './types/nikkeDraft'
import { getResult, runsForTab } from './types/profile'
import { restorableResult } from './lib/restorableResult'
import { useSupportedUnits } from './hooks/useSupportedUnits'
import { nameFromSlug } from './lib/unitName'
import { burstTiersFor } from './types/supportedUnit'
import { ProfileSwitcher } from './components/ProfileSwitcher'
import { RosterGrid } from './components/RosterGrid'
import { RecommendPanel } from './components/RecommendPanel'
import { SyncRosterPanel } from './components/SyncRosterPanel'
import { UnionRaidPanel } from './components/UnionRaidPanel'
import { ChargeWindowPanel } from './components/ChargeWindowPanel'
import { PrivacyNotice } from './components/PrivacyNotice'
import { HELP } from './lib/helpText'
import type { NikkeDraft } from './types/nikkeDraft'
import type { SavedRun } from './types/profile'

// A stable reference so useMemo below doesn't see a "new" roster every render
// when there's no active profile (a fresh `?? []` literal would).
const NO_ROSTER: NikkeDraft[] = []
const NO_SAVED_RUNS: SavedRun[] = []

type Tab = 'roster' | 'recommend' | 'union' | 'calculator' | 'sync'

const TABS: { id: Tab; label: string }[] = [
  { id: 'roster', label: '니케 풀' },
  { id: 'recommend', label: '솔로 레이드' },
  { id: 'union', label: '유니온 레이드' },
  // Named for the section rather than for its one occupant: more
  // calculators are going here (Fienn, 2026-07-31).
  { id: 'calculator', label: '계산기' },
  // Last because syncing is occasional: the front of the row belongs to the
  // tabs used every session. Switching accounts stays reachable from the
  // header dropdown either way.
  { id: 'sync', label: '동기화' },
]

function App() {
  const {
    state,
    activeProfile,
    upsertProfile,
    switchProfile,
    deleteProfile,
    saveResult,
    saveRun,
    renameRun,
    deleteRun,
  } = useProfiles()
  const { portraitFor } = usePortraitManifest()
  // The Roster tab needs names, elements and the supported/unsupported split.
  // RecommendPanel loads the same list for itself: making it a prop instead
  // would rewrite 22 of its test's render sites to save one GET of a small
  // static endpoint.
  const supportedUnits = useSupportedUnits()
  const engineVersion = useEngineVersion()
  const [tab, setTab] = useState<Tab>('roster')

  const drafts = activeProfile?.roster ?? NO_ROSTER
  const validRoster = useMemo(() => getValidRoster(drafts), [drafts])

  // 마지막 제출 결과를 다시 올릴 수 있을 때만 올린다. 엔진 버전은 마운트 뒤
  // 늦게 도착하므로, 그 전까지는 판단이 "아직 아니오"이고 도착한 뒤 유효해진다.
  const restorableRaidResult = useMemo(
    () => (activeProfile ? restorableResult(activeProfile, validRoster, engineVersion) : null),
    [activeProfile, validRoster, engineVersion],
  )

  // 탭마다 자기 몫의 보관물만 본다 - 솔로와 유니온이 섞이지 않는 것은 이
  // 필터가 전부다. useMemo인 이유는 runsForTab이 매번 새 배열을 낸다는 것뿐이다.
  const soloSavedRuns = useMemo(
    () => (activeProfile ? runsForTab(activeProfile, 'solo') : NO_SAVED_RUNS),
    [activeProfile],
  )
  const unionSavedRuns = useMemo(
    () => (activeProfile ? runsForTab(activeProfile, 'union') : NO_SAVED_RUNS),
    [activeProfile],
  )

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

  // Union raid draws its deck slots the same way DraftEditor draws them
  // anywhere else: a name and a burst-tier badge, both looked up from
  // /api/supported-units - same fallback RecommendPanel's own unitIndex uses
  // for a slug the list doesn't know.
  const unitIndex = useMemo(
    () => new Map(supportedUnits.units.map((unit) => [unit.slug, unit])),
    [supportedUnits.units],
  )
  const nameFor = (slug: string) => unitIndex.get(slug)?.name ?? nameFromSlug(slug)
  const burstTiersResolver = (slug: string) => burstTiersFor(slug, unitIndex)

  return (
    <div className="app">
      <header className="app__header">
        <div className="app__masthead">
          <h1 className="app__title">RapiLab</h1>
          <p className="app__subtitle">
            blablalink에서 로스터를 동기화하면 엔진이 덱을 구성해줘요.
          </p>
          <p className="app__note">
            덱 추천은 모든 니케가 재장전 큐브 15레벨을 착용한 것으로 계산합니다.
            계산기 탭에서는 큐브를 직접 고릅니다.
          </p>
        </div>

        {/* Top right of the page, opposite the title: which account is loaded
            is a property of the whole screen, not of the tab below it. */}
        <ProfileSwitcher
          profiles={Object.values(state.profiles)}
          activeKey={state.activeKey}
          onSwitch={switchProfile}
          onDelete={deleteProfile}
        />
      </header>

      {activeProfile === null ? (
        <main className="app__main">
          <SyncRosterPanel onImport={upsertProfile} defaultHelpOpen />
          <div className="empty">
            <p className="empty__text">
              아직 동기화된 계정이 없어요. 위에서 blablalink 동기화를
              시작해보세요.
            </p>
          </div>
        </main>
      ) : (
        <>
          <div className="tabs" role="tablist" aria-label="섹션">
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
                key={state.activeKey ?? 'none'}
                roster={validRoster}
                investmentFor={investmentFor}
                engineVersion={engineVersion}
                activeKey={state.activeKey}
                getCached={(hash) => (activeProfile ? getResult(activeProfile, hash) : null)}
                onResult={(args) => {
                  if (state.activeKey) saveResult({ key: state.activeKey, ...args })
                }}
                restoreInputs={activeProfile?.lastInputs ?? null}
                restoreResult={restorableRaidResult}
                savedRuns={soloSavedRuns}
                onSaveRun={(run) =>
                  state.activeKey ? saveRun({ key: state.activeKey, run }) : false
                }
                onRenameRun={(id, name) => {
                  if (state.activeKey) renameRun({ key: state.activeKey, id, name })
                }}
                onDeleteRun={(id) => {
                  if (state.activeKey) deleteRun({ key: state.activeKey, id })
                }}
              />
            </div>

            <div
              role="tabpanel"
              id="panel-union"
              aria-labelledby="tab-union"
              hidden={tab !== 'union'}
              className="panel"
            >
              <UnionRaidPanel
                // Same reasoning as RecommendPanel's key: an evaluate request
                // outliving a profile switch must not land against the
                // previous profile's hook instance.
                key={state.activeKey ?? 'none'}
                roster={validRoster}
                supportedUnits={supportedUnits.units}
                portraitFor={portraitFor}
                nameFor={nameFor}
                burstTiersFor={burstTiersResolver}
                investmentFor={investmentFor}
                savedRuns={unionSavedRuns}
                onSaveRun={(run) =>
                  state.activeKey ? saveRun({ key: state.activeKey, run }) : false
                }
                onRenameRun={(id, name) => {
                  if (state.activeKey) renameRun({ key: state.activeKey, id, name })
                }}
                onDeleteRun={(id) => {
                  if (state.activeKey) deleteRun({ key: state.activeKey, id })
                }}
              />
            </div>

            <div
              role="tabpanel"
              id="panel-calculator"
              aria-labelledby="tab-calculator"
              hidden={tab !== 'calculator'}
              className="panel"
            >
              <ChargeWindowPanel
                // Same reasoning as RecommendPanel's key: a ladder computed for
                // one profile must not stay on screen after a switch, and the
                // panel's own state is the only place it lives.
                key={state.activeKey ?? 'none'}
                roster={validRoster}
                nameFor={nameFor}
              />
            </div>

            <div
              role="tabpanel"
              id="panel-sync"
              aria-labelledby="tab-sync"
              hidden={tab !== 'sync'}
              className="panel"
            >
              {/* 북마크릿이 로스터를 보내오면 이 탭을 앞으로 가져온다. 여러
                  서버에 로스터가 있는 계정은 "어느 서버를 가져올까요?"에
                  답해야 넘어가는데, 그 질문이 감춰진 패널에 뜨면 유저에게는
                  동기화가 멈춘 것으로만 보인다. */}
              <SyncRosterPanel onImport={upsertProfile} onActivity={() => setTab('sync')} />
            </div>
          </main>
        </>
      )}

      {/* 푸터는 프로필이 없을 때도 나온다. 개인정보 안내를 가장 읽고 싶은
          때가 바로 아직 아무것도 동기화하지 않은 때 - 계정을 맡길지 정하는
          순간이기 때문이다. 준비 완료 수만 프로필이 있을 때 붙는다. */}
      <footer className="app__footer">
        {activeProfile !== null && (
          <span>
            니케 {validRoster.length}/{drafts.length}기 준비 완료
          </span>
        )}
        <PrivacyNotice />

        {/* 출처 고지는 접지 않는다 - 펼쳐야 보이는 고지는 고지가 아니다. */}
        <p className="app__attribution">
          {HELP.attribution.map((line) => (
            <span key={line} className="app__attribution-line">
              {line}
            </span>
          ))}
        </p>
      </footer>
    </div>
  )
}

export default App
