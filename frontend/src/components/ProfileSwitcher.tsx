// Switches between synced blablalink accounts (profiles). Each profile is
// keyed by (open_id, area) and holds its own roster/results - switching never
// merges them. With no profiles yet, App shows its own empty state instead,
// so this renders nothing.

import { useEffect, useId, useState } from 'react'
import { profileKey, type Profile } from '../types/profile'
import { serverLabel } from '../types/server'

interface ProfileSwitcherProps {
  profiles: Profile[]
  activeKey: string | null
  onSwitch: (key: string) => void
  onDelete: (key: string) => void
  /** 계정 이름은 유저의 라벨이다 - 동기화가 못 읽어 오면 여기서 붙인다. */
  onRename: (key: string, name: string) => void
}

const UNNAMED = '이름 없는 계정'

/** 프로필은 닉네임으로 불리고, 닉네임을 못 읽은 동기화는 open_id가 대신 선다.
 * 둘 다 없는 동기화가 남긴 프로필도 골라내 지울 수 있어야 하므로 이름이 필요하다.
 * 서버를 뒤에 붙이는 이유: 한 사람이 두 서버에 같은 닉네임으로 있을 수 있고,
 * 그러면 닉네임만으로는 어느 쪽인지 알 수 없다. 이름은 유저가 직접 붙일 수
 * 있다 - 동기화가 못 읽어 오는 경우가 정상 경로다. */
const labelFor = (profile: Profile): string =>
  `${profile.nickname || profile.openId || UNNAMED} (${serverLabel(profile.area)})`

export function ProfileSwitcher({
  profiles,
  activeKey,
  onSwitch,
  onDelete,
  onRename,
}: ProfileSwitcherProps) {
  const [renaming, setRenaming] = useState(false)
  const [renameValue, setRenameValue] = useState('')
  const renameFieldId = useId()

  // 계정을 바꾸면 이름 바꾸기를 닫는다 - 열어 둔 채 두면 저장이 지금 보이는
  // 계정이 아니라 새로 바뀐 activeKey에 실려, 편집하던 계정과 다른 계정의
  // 이름이 바뀐다.
  useEffect(() => {
    setRenaming(false)
  }, [activeKey])

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

  const startRename = () => {
    setRenameValue(active?.nickname ?? '')
    setRenaming(true)
  }

  const commitRename = () => {
    const name = renameValue.trim()
    if (name === '' || activeKey === null) return
    onRename(activeKey, name)
    setRenaming(false)
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
      {activeKey !== null && (
        <button
          type="button"
          className="btn btn--icon"
          aria-label="계정 이름 바꾸기"
          onClick={startRename}
        >
          이름 바꾸기
        </button>
      )}
      {renaming && (
        <div className="profile-switcher__rename">
          <label className="field__label" htmlFor={renameFieldId}>
            계정 이름
          </label>
          <input
            id={renameFieldId}
            className="field__input"
            value={renameValue}
            onChange={(e) => setRenameValue(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') commitRename()
              if (e.key === 'Escape') setRenaming(false)
            }}
          />
          <button type="button" className="btn btn--primary" onClick={commitRename}>
            저장
          </button>
          <button type="button" className="btn" onClick={() => setRenaming(false)}>
            취소
          </button>
        </div>
      )}
    </div>
  )
}
