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
    if (window.confirm(`"${activeLabel}" 프로필을 삭제할까요? 동기화된 로스터와 캐시된 결과가 함께 삭제돼요.`)) {
      onDelete(activeOpenId)
    }
  }

  return (
    <div className="profile-switcher">
      <label className="field__label" htmlFor="profile-select">
        계정
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
        aria-label={`${activeLabel} 프로필 삭제`}
        onClick={handleDelete}
      >
        삭제
      </button>
    </div>
  )
}
