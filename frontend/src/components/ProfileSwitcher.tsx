// Switches between synced blablalink accounts (profiles). Each profile is
// keyed by (open_id, area) and holds its own roster/results - switching never
// merges them. With no profiles yet, App shows its own empty state instead,
// so this renders nothing.

import { profileKey, type Profile } from '../types/profile'

interface ProfileSwitcherProps {
  profiles: Profile[]
  activeKey: string | null
  onSwitch: (key: string) => void
  onDelete: (key: string) => void
}

const UNNAMED = '이름 없는 계정'

/** A profile goes by its nickname; a sync that could not read one leaves the
 * open_id to stand in. A sync that arrived without either leaves a profile with
 * nothing to show, which must still be nameable so it can be picked out of the
 * dropdown and removed. */
const labelFor = (profile: Profile): string =>
  profile.nickname || profile.openId || UNNAMED

export function ProfileSwitcher({
  profiles,
  activeKey,
  onSwitch,
  onDelete,
}: ProfileSwitcherProps) {
  if (profiles.length === 0) return null

  const active = profiles.find((p) => profileKey(p.openId, p.area) === activeKey)
  const activeLabel = active ? labelFor(active) : activeKey || UNNAMED

  const handleDelete = () => {
    // The empty string is a real profile key - a sync that arrived without an
    // open_id files itself under it - and that profile is the one most in need
    // of removing. Only null means no account is selected, so only null returns.
    if (activeKey === null) return
    if (window.confirm(`"${activeLabel}" 프로필을 삭제할까요? 동기화된 로스터와 캐시된 결과가 함께 삭제돼요.`)) {
      onDelete(activeKey)
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
        value={activeKey ?? ''}
        onChange={(e) => onSwitch(e.target.value)}
      >
        {profiles.map((profile) => {
          const key = profileKey(profile.openId, profile.area)
          return (
            <option key={key} value={key}>
              {labelFor(profile)}
            </option>
          )
        })}
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
