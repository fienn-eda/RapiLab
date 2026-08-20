// 회차 보스마다 Fienn이 직접 쓰는 가이드. 지금은 localStorage에만 산다.
//
// localStorage는 빌드 산출물이 아니라 기기에 붙는다 - 개발 브라우저에 쓴 글은
// 설치본에서 보이지 않고 릴리즈 zip에 실리지도 않는다. 릴리즈에 실리는 쪽은
// 2단계에서 data/raid-rotations.json이 맡고(그 파일은 packaging/rapilab.spec의
// datas를 타고 번들에 들어간다), 이 훅은 그 위를 덮는 층이 된다.
//
// guideFor가 fallback을 받는 이유가 그것이다: 지금은 언제나 ''이지만 자리는
// 그때 것이고, 시그니처를 나중에 바꾸면 호출부를 다시 훑어야 한다.
//
// 키가 (회차, 보스)인 것은 data/raid-rotations.json과 같은 규칙이다 - 같은 보스가
// 다음 시즌에 다른 속성으로 나오면 가이드도 다른 칸이다.

import { useCallback, useState } from 'react'

const STORAGE_KEY = 'nikke-boss-guides'

interface GuidesFile {
  guides: Record<string, string>
}

/** 저장된 가이드. 읽기가 막혀 있거나(사생활 모드 등) 저장된 것이 깨져 있으면
 * 빈 것으로 시작한다 - 가이드가 없다고 화면이 못 도는 것은 아니다. */
const readGuides = (): Record<string, string> => {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw === null) return {}
    return (JSON.parse(raw) as GuidesFile).guides ?? {}
  } catch {
    return {}
  }
}

export interface BossGuides {
  /** 저장된 글. 없으면 fallback. */
  guideFor: (key: string, fallback: string) => string
  setGuide: (key: string, text: string) => void
}

export const useBossGuides = (): BossGuides => {
  const [guides, setGuides] = useState<Record<string, string>>(readGuides)

  const setGuide = useCallback((key: string, text: string) => {
    setGuides((current) => {
      const next = { ...current, [key]: text }
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify({ guides: next }))
      } catch {
        // 쓰기가 막혀도 이번 세션 동안은 고쳐 쓸 수 있어야 한다.
      }
      return next
    })
  }, [])

  const guideFor = useCallback(
    (key: string, fallback: string) => guides[key] ?? fallback,
    [guides],
  )

  return { guideFor, setGuide }
}
