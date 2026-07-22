// Switches between synced blablalink accounts (profiles). Each profile is
// keyed by open_id and holds its own roster/results - switching never merges
// them. With no profiles yet, App shows its own empty state instead, so this
// renders nothing.

import type { Profile } from '../types/profile'

interface ProfileSwitcherProps {
  profiles: Profile[]
  activeOpenId: string | null
  onSwitch: (openId: string) => void
  onDelete: (openId: string) => void
}

export function ProfileSwitcher({
  profiles,
  activeOpenId,
  onSwitch,
  onDelete,
}: ProfileSwitcherProps) {
  if (profiles.length === 0) return null

  const activeLabel =
    profiles.find((p) => p.openId === activeOpenId)?.nickname || activeOpenId

  const handleDelete = () => {
    if (!activeOpenId) return
    if (window.confirm(`Delete profile "${activeLabel}"? This removes its synced roster and cached results.`)) {
      onDelete(activeOpenId)
    }
  }

  return (
    <div className="profile-switcher">
      <label className="field__label" htmlFor="profile-select">
        Account
      </label>
      <select
        id="profile-select"
        className="field__input"
        value={activeOpenId ?? ''}
        onChange={(e) => onSwitch(e.target.value)}
      >
        {profiles.map((profile) => (
          <option key={profile.openId} value={profile.openId}>
            {profile.nickname || profile.openId}
          </option>
        ))}
      </select>
      <button
        type="button"
        className="btn btn--icon"
        aria-label={`Delete profile ${activeLabel}`}
        onClick={handleDelete}
      >
        Delete
      </button>
    </div>
  )
}
