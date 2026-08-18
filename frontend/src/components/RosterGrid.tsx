// The Roster tab's contents: everything the active profile synced, split by
// whether the engine can actually simulate it.
//
// A player owns far more Nikkes than the engine supports (159 vs 70 on the
// roster this was built against). Drawing both alike made more than half the
// tab units that can never enter a deck, at the same size and weight as the
// ones that can. The supported units get the grid; the rest get a collapsed
// list, present so a missing Nikke is explained rather than simply absent.
//
// The supported half is grouped by burst tier, the way the recommend palette
// groups it - a roster is read to answer "what can I field", and that
// question is always asked one tier at a time.

import { useEffect, useState } from 'react'
import type { NikkeDraft } from '../types/nikkeDraft'
import { BURST_TIERS, type SupportedUnit } from '../types/supportedUnit'
import { displayName } from '../lib/unitName'
import {
  EMPTY_FILTER,
  filterAndSort,
  type UnitFacets,
  type UnitFilterState,
} from '../lib/unitFilter'
import { HELP } from '../lib/helpText'
import { HelpText } from './HelpText'
import { HelpTip } from './HelpTip'
import { NikkeCard } from './NikkeCard'
import { UnitFilterBar } from './UnitFilterBar'

const OVERLOAD_DETAIL_KEY = 'nikke-overload-detail'

/** 저장된 상세 모드 선택. 읽기가 막혀 있으면(사생활 모드 등) 요약이 기본이다 -
 * 요약은 어떤 로스터에서도 그려지는 쪽이라 물러설 자리로 안전하다. */
const readOverloadDetail = (): boolean => {
  try {
    return localStorage.getItem(OVERLOAD_DETAIL_KEY) === 'true'
  } catch {
    return false
  }
}

interface RosterGridProps {
  drafts: NikkeDraft[]
  supportedUnits: SupportedUnit[]
  portraitFor: (slug: string) => string | null
  /** Benched Nikkes — the recommender may not field these. Account-wide, so
   * this tab is where they are decided; the raid tabs only read it. */
  excludedSlugs?: string[]
  onToggleExclude?: (slug: string) => void
}

export function RosterGrid({
  drafts,
  supportedUnits,
  portraitFor,
  excludedSlugs = [],
  onToggleExclude,
}: RosterGridProps) {
  const excludedSet = new Set(excludedSlugs)
  const bySlug = new Map(supportedUnits.map((unit) => [unit.slug, unit]))
  const supported = drafts.filter((draft) => bySlug.has(draft.character_slug))
  const unsupported = drafts.filter((draft) => !bySlug.has(draft.character_slug))
  const names = new Map(supportedUnits.map((unit) => [unit.slug, unit.name]))

  const [filter, setFilter] = useState<UnitFilterState>(EMPTY_FILTER)
  // 탭 전체가 한꺼번에 바뀐다. 카드마다 따로 펴면 같은 열에서 유닛을 비교하는
  // 이 탭의 용도가 깨지고, 카드 높이도 제각각이 된다. 선택이 세션을 넘어 남는
  // 것은 사이드바 접힘과 같은 이유다 - 매번 다시 켜게 만들면 잔소리가 된다.
  const [overloadDetail, setOverloadDetail] = useState(readOverloadDetail)

  useEffect(() => {
    try {
      localStorage.setItem(OVERLOAD_DETAIL_KEY, String(overloadDetail))
    } catch {
      // 저장이 막힌 브라우저에서도 모드 자체는 동작해야 한다.
    }
  }, [overloadDetail])

  // Only the supported half has an element and a burst tier to filter on; the
  // unsupported list is not in `supportedUnits` at all, so a half-applied
  // toolbar would just look broken there.
  const facetsFor = (draft: NikkeDraft): UnitFacets => {
    const unit = bySlug.get(draft.character_slug)!
    return {
      slug: unit.slug,
      name: unit.name,
      element: unit.element,
      burstTier: unit.burstTier,
      overload: draft.overload_options,
      excluded: excludedSet.has(draft.character_slug),
    }
  }

  // Sorted once across the whole roster, then partitioned by tier - a
  // partition preserves relative order, so each group is already in sort
  // order.
  const visible = filterAndSort(supported, facetsFor, filter)

  return (
    <div className="roster">
      {supported.length > 0 && (
        <>
          <UnitFilterBar
            value={filter}
            onChange={setFilter}
            shown={visible.length}
            total={supported.length}
            excludable
          />
          {/* 필터 툴바가 아니라 여기에 있다 - 툴바는 추천 팔레트와 공유하는데,
              장비 격자는 로스터 카드에만 있는 표시다.

              체크박스가 아니라 눌린 상태를 가진 버튼이다. 켜고 끄는 것이 폼에
              제출할 값이 아니라 화면을 바꾸는 동작이라, 눌러 둔 버튼 쪽이 지금
              무엇을 보고 있는지를 더 곧게 말한다. 상태는 색으로도 보이지만
              aria-pressed가 진짜 답이다 - 색만으로는 상태가 없는 사람이 있다. */}
          <div className="roster__mode">
            <button
              type="button"
              className="roster__mode-toggle"
              aria-pressed={overloadDetail}
              onClick={() => setOverloadDetail(!overloadDetail)}
            >
              오버로드 옵션 상세
            </button>
            {/* 격자의 빨간 수치와 흰 행이 무슨 뜻인지는 화면 어디에도 안 적혀
                있다. 버튼 안이 아니라 옆에 둔다 - 버튼 안의 버튼은 무효다. */}
            <HelpTip label="오버로드 옵션 상세">
              <HelpText>{HELP.roster.gearTierLegend}</HelpText>
            </HelpTip>
          </div>
        </>
      )}

      {BURST_TIERS.map((tier) => {
        const units = visible.filter(
          (draft) => bySlug.get(draft.character_slug)!.burstTier === tier,
        )
        if (units.length === 0) return null
        return (
          <section key={tier} className="roster__group">
            {/* The game's own burst icon carries the tier. Its alt is what
                names the heading, so the section is still "B1" to a reader
                who never sees the image. */}
            <h2 className="roster__heading">
              <img
                className="burst-heading__icon"
                src={`/elements/icon-burst-${tier}.png`}
                alt={`B${tier}`}
              />
            </h2>
            {/* 상세 모드의 타일은 장비 넷과 그 옵션 행들을 담아야 해서 요약
                타일보다 훨씬 넓다 - 열 최소 폭이 같이 움직이지 않으면 격자가
                카드 안에서 짓눌린다. */}
            <div className={`roster__grid${overloadDetail ? ' roster__grid--detail' : ''}`}>
              {units.map((draft, index) => {
                const unit = bySlug.get(draft.character_slug)!
                return (
                  <NikkeCard
                    key={draft.id ?? draft.character_slug}
                    draft={draft}
                    index={index}
                    name={unit.name}
                    element={unit.element}
                    portrait={portraitFor(draft.character_slug)}
                    excluded={excludedSet.has(draft.character_slug)}
                    overloadDetail={overloadDetail}
                    onToggleExclude={
                      onToggleExclude
                        ? () => onToggleExclude(draft.character_slug)
                        : undefined
                    }
                  />
                )
              })}
            </div>
          </section>
        )
      })}

      {unsupported.length > 0 && (
        <details className="roster__unsupported">
          <summary className="roster__unsupported-summary">
            엔진 미지원 ({unsupported.length}기)
          </summary>
          <ul className="roster__unsupported-list">
            {unsupported.map((draft) => (
              <li key={draft.id ?? draft.character_slug}>
                {displayName(draft.character_slug, names)}
              </li>
            ))}
          </ul>
        </details>
      )}
    </div>
  )
}
