// 회차 보스마다 Fienn이 직접 적는 공략 이벤트. 지금은 localStorage에만 산다.
//
// localStorage는 빌드 산출물이 아니라 기기에 붙는다 - 개발 브라우저에 쓴 글은
// 설치본에서 보이지 않고 릴리즈 zip에 실리지도 않는다. 릴리즈에 실리는 쪽은
// 2단계에서 data/raid-rotations.json이 맡고(그 파일은 packaging/rapilab.spec의
// datas를 타고 번들에 들어간다), 이 훅은 그 위를 덮는 층이 된다.
//
// guideFor가 fallback을 받는 이유가 그것이다: 지금은 언제나 빈 목록이지만 자리는
// 그때 것이고, 시그니처를 나중에 바꾸면 호출부를 다시 훑어야 한다.
//
// 키가 (회차, 보스)인 것은 data/raid-rotations.json과 같은 규칙이다 - 같은 보스가
// 다음 시즌에 다른 속성을 달고 나오면 가이드도 다른 칸이다.

import { useCallback, useState } from 'react'

const STORAGE_KEY = 'nikke-boss-guides'

export interface GuideEvent {
  /** 목록 안에서만 쓰는 식별자. 시각으로 정렬해도 편집 중인 행이 튀지 않게 한다. */
  id: string
  /** 전투 시작으로부터 경과 초. null이면 시각에 매이지 않은 「상시」 항목. */
  at: number | null
  text: string
}

/** 저장된 모양. 값이 문자열인 것은 개정 전(자유 문장 한 덩어리)에 쓴 글이다. */
interface GuidesFile {
  guides: Record<string, GuideEvent[] | string>
}

export const makeGuideEventId = (): string => crypto.randomUUID()

/** 개정 전에 자유 문장으로 쓴 글을 버리지 않는다 - 시각에 매이지 않으므로
 * 「상시」 항목 하나가 된다. */
const fromLegacy = (text: string): GuideEvent[] =>
  text.trim() === '' ? [] : [{ id: makeGuideEventId(), at: null, text }]

/** 저장된 가이드. 읽기가 막혀 있거나(사생활 모드 등) 저장된 것이 깨져 있으면
 * 빈 것으로 시작한다 - 가이드가 없다고 화면이 못 도는 것은 아니다. */
const readGuides = (): Record<string, GuideEvent[]> => {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw === null) return {}
    const stored = (JSON.parse(raw) as GuidesFile).guides ?? {}
    return Object.fromEntries(
      Object.entries(stored).map(([key, value]) => [
        key,
        typeof value === 'string' ? fromLegacy(value) : value,
      ]),
    )
  } catch {
    return {}
  }
}

export interface BossGuides {
  /** 저장된 이벤트들. 없으면 fallback. */
  guideFor: (key: string, fallback: GuideEvent[]) => GuideEvent[]
  setGuide: (key: string, events: GuideEvent[]) => void
}

export const useBossGuides = (): BossGuides => {
  const [guides, setGuides] = useState<Record<string, GuideEvent[]>>(readGuides)

  const setGuide = useCallback((key: string, events: GuideEvent[]) => {
    setGuides((current) => {
      const next = { ...current, [key]: events }
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify({ guides: next }))
      } catch {
        // 쓰기가 막혀도 이번 세션 동안은 고쳐 쓸 수 있어야 한다.
      }
      return next
    })
  }, [])

  const guideFor = useCallback(
    (key: string, fallback: GuideEvent[]) => guides[key] ?? fallback,
    [guides],
  )

  return { guideFor, setGuide }
}
