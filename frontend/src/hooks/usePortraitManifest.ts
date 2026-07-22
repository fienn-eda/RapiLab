// Loads the static portrait manifest (frontend/README.md "Portraits") and
// resolves a slug to its icon path. Fetched directly (not through src/api/ —
// there's no live/mock split here, it's a static public asset, not a backend
// endpoint). A missing manifest entry, or a manifest that fails to load
// entirely, both resolve to null so callers can fall back to a chip; the
// editor must work identically either way.

import { useEffect, useState } from 'react'

interface PortraitManifestFile {
  portraits: Record<string, string>
}

export interface PortraitManifestState {
  portraitFor: (slug: string) => string | null
}

export const usePortraitManifest = (): PortraitManifestState => {
  const [portraits, setPortraits] = useState<Record<string, string>>({})

  useEffect(() => {
    let cancelled = false
    fetch('/portraits/manifest.json')
      .then((response) => (response.ok ? (response.json() as Promise<PortraitManifestFile>) : null))
      .then((data) => {
        if (!cancelled && data) setPortraits(data.portraits ?? {})
      })
      .catch(() => {
        // No manifest available - every slug falls back to the chip display.
      })
    return () => {
      cancelled = true
    }
  }, [])

  const portraitFor = (slug: string): string | null => {
    const filename = portraits[slug]
    return filename ? `/portraits/${filename}` : null
  }

  return { portraitFor }
}
