// ShiftyPad investment-data input: the user syncs their roster from
// blablalink per account (profile), then requests deck recommendations
// against a boss profile (POST /api/recommend, via RecommendPanel).

import { useEffect, useMemo, useState } from 'react'
import './App.css'
import { useProfiles } from './hooks/useProfiles'
import { usePortraitManifest } from './hooks/usePortraitManifest'
import { useEngineVersion } from './hooks/useEngineVersion'
import { getValidRoster } from './types/nikkeDraft'
import { getResult, runsForTab } from './types/profile'
import { restorableResult } from './lib/restorableResult'
import { useSupportedUnits } from './hooks/useSupportedUnits'
import { useRaidRotations } from './hooks/useRaidRotations'
import { nameFromSlug } from './lib/unitName'
import { burstTiersFor } from './types/supportedUnit'
import { ProfileSwitcher } from './components/ProfileSwitcher'
import { RosterGrid } from './components/RosterGrid'
import { RecommendPanel } from './components/RecommendPanel'
import { SyncRosterPanel } from './components/SyncRosterPanel'
import { UnionRaidPanel } from './components/UnionRaidPanel'
import { CalculatorPanel } from './components/CalculatorPanel'
import { PrivacyNotice } from './components/PrivacyNotice'
import { Wordmark } from './components/Wordmark'
import { HELP } from './lib/helpText'
import { HelpText } from './components/HelpText'
import type { NikkeDraft } from './types/nikkeDraft'
import type { SavedRun } from './types/profile'

// A stable reference so useMemo below doesn't see a "new" roster every render
// when there's no active profile (a fresh `?? []` literal would).
const NO_ROSTER: NikkeDraft[] = []
const NO_SAVED_RUNS: SavedRun[] = []
const NO_EXCLUSIONS: string[] = []

type Tab = 'roster' | 'recommend' | 'union' | 'calculator' | 'sync'

const SIDEBAR_KEY = 'nikke-sidebar-collapsed'

/** 저장된 접힘 상태. 읽기가 막혀 있으면(사생활 모드 등) 펼친 쪽이 기본이다 -
 * 탭이 보이는 것이 이 사이드바의 존재 이유이기 때문이다. */
const readSidebarCollapsed = (): boolean => {
  try {
    return localStorage.getItem(SIDEBAR_KEY) === '1'
  } catch {
    return false
  }
}

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
    renameProfile,
    saveResult,
    saveRun,
    renameRun,
    deleteRun,
    toggleExcluded,
  } = useProfiles()
  const { portraitFor } = usePortraitManifest()
  // 미사용 니케는 계정 하나로 정해진다 - 니케 풀 탭에서 고르고, 솔로·유니온이
  // 그것을 읽는다. 탭마다 따로 두면 「이 니케를 뺐다」가 어느 화면 이야기인지
  // 매번 되물어야 한다. 프로필에 붙어 저장되므로 앱을 다시 켜도 남고, 계정을
  // 바꾸면 그 계정 몫으로 갈아탄다 - 지워야 할 상태가 아니라 읽는 자리가 바뀔
  // 뿐이다.
  const excludedSlugs = activeProfile?.excludedSlugs ?? NO_EXCLUSIONS
  const toggleExclude = (slug: string) => {
    if (state.activeKey) toggleExcluded({ key: state.activeKey, slug })
  }
  // The Roster tab needs names, elements and the supported/unsupported split.
  // RecommendPanel loads the same list for itself: making it a prop instead
  // would rewrite 22 of its test's render sites to save one GET of a small
  // static endpoint.
  const supportedUnits = useSupportedUnits()
  // 두 탭 패널이 동시에 마운트되므로 훅을 패널마다 부르면 같은 파일을 두 번
  // 받는다. 한 번 받아 내려보낸다.
  const raidRotations = useRaidRotations()
  const engineVersion = useEngineVersion()
  const [tab, setTab] = useState<Tab>('roster')
  // 탭 목록은 사이드바에 고정돼 스크롤을 따라온다. 접는 것은 가로가 필요할 때의
  // 예외라 선택이 세션을 넘어 남는다 - 매번 다시 접게 만들면 접기가 기능이
  // 아니라 잔소리가 된다.
  const [sidebarCollapsed, setSidebarCollapsed] = useState(readSidebarCollapsed)
  useEffect(() => {
    try {
      localStorage.setItem(SIDEBAR_KEY, sidebarCollapsed ? '1' : '0')
    } catch {
      // 저장이 막힌 브라우저에서도 접기 자체는 동작해야 한다.
    }
  }, [sidebarCollapsed])

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
  // 이 open_id에 대해 이미 아는 것. 아는 서버만 조회하는 것은 속도 이득이고
  // (다섯 서버를 다 훑지 않는다), 이미 아는 이름을 다시 묻지 않는 것은
  // 거절될 조회(code 1300015)를 아예 안 하는 것이다.
  const knownFor = (openId: string) => {
    const mine = Object.values(state.profiles).filter((p) => p.openId === openId)
    return {
      areas: mine.map((p) => p.area),
      namedAreas: mine.filter((p) => p.nickname !== '').map((p) => p.area),
    }
  }

  const nameFor = (slug: string) => unitIndex.get(slug)?.name ?? nameFromSlug(slug)
  const burstTiersResolver = (slug: string) => burstTiersFor(slug, unitIndex)

  return (
    <div className="app">
      <header className="app__header">
        <div className="app__masthead">
          <h1 className="app__title">
            <Wordmark />
            <span className="visually-hidden">RapiLab</span>
          </h1>
          <p className="app__subtitle">
            <HelpText>{HELP.app.subtitle}</HelpText>
          </p>
          <p className="app__note">
            <HelpText>{HELP.app.cubeAssumption}</HelpText>
          </p>
        </div>

        {/* Top right of the page, opposite the title: which account is loaded
            is a property of the whole screen, not of the tab below it. */}
        <ProfileSwitcher
          profiles={Object.values(state.profiles)}
          activeKey={state.activeKey}
          onSwitch={switchProfile}
          onDelete={deleteProfile}
          onRename={(key, name) => renameProfile({ key, name })}
        />
      </header>

      {activeProfile === null ? (
        <main className="app__main">
          <SyncRosterPanel onImport={upsertProfile} knownFor={knownFor} defaultHelpOpen />
          <div className="empty">
            <p className="empty__text">
              <HelpText>{HELP.app.noProfiles}</HelpText>
            </p>
          </div>
        </main>
      ) : (
        <div
          className={
            sidebarCollapsed ? 'app__body app__body--collapsed' : 'app__body'
          }
        >
          {/* 세로 스크롤이 화면 여러 개 길이라, 탭이 맨 위에만 있으면 옮겨 가려고
              매번 위로 올라가야 했다(Fienn, 2026-08-11). 사이드바는 스크롤을
              따라온다. */}
          <nav className="app__sidebar" aria-label="섹션">
            <button
              type="button"
              className="app__sidebar-toggle"
              onClick={() => setSidebarCollapsed((collapsed) => !collapsed)}
              aria-expanded={!sidebarCollapsed}
              aria-label={sidebarCollapsed ? '탭 목록 펼치기' : '탭 목록 접기'}
            >
              {sidebarCollapsed ? '»' : '«'}
            </button>
            {/* 접었을 때 tablist를 DOM에서 빼지 않고 감춘다: 지금 어느 탭인지는
                패널의 aria-labelledby가 가리키는 사실이라, 그 대상이 사라지면
                화면낭독기에게 패널이 이름 없는 상자가 된다. */}
            <div
              className="tabs tabs--side"
              role="tablist"
              aria-label="섹션"
              hidden={sidebarCollapsed}
            >
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
          </nav>

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
                excludedSlugs={excludedSlugs}
                onToggleExclude={toggleExclude}
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
                rotations={raidRotations.rotations}
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
                excludedSlugs={excludedSlugs}
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
                rotations={raidRotations.rotations}
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
                excludedSlugs={excludedSlugs}
              />
            </div>

            <div
              role="tabpanel"
              id="panel-calculator"
              aria-labelledby="tab-calculator"
              hidden={tab !== 'calculator'}
              className="panel"
            >
              <CalculatorPanel
                // Same reasoning as RecommendPanel's key: a result computed for
                // one profile must not stay on screen after a switch, and the
                // panels' own state is the only place it lives.
                key={state.activeKey ?? 'none'}
                roster={validRoster}
                supportedUnits={supportedUnits.units}
                portraitFor={portraitFor}
                nameFor={nameFor}
                burstTiersFor={burstTiersResolver}
                investmentFor={investmentFor}
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
              <SyncRosterPanel
                onImport={upsertProfile}
                knownFor={knownFor}
                onActivity={() => setTab('sync')}
              />
            </div>
          </main>
        </div>
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
              <HelpText>{line}</HelpText>
            </span>
          ))}
        </p>
      </footer>
    </div>
  )
}

export default App
