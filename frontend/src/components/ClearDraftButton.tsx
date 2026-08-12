// 편성을 통째로 비우는 버튼. 되돌릴 수 없으므로 확인을 한 번 묻고, 비울 것이
// 없으면 아예 눌리지 않는다.
//
// 비우는 것은 편성뿐이다 - 보스 설정도 덱 개수도 건드리지 않는다. 좌석이
// 사라지므로 잠금은 함께 사라진다.

import { HELP } from '../lib/helpText'
import type { Draft } from '../types/draft'

interface ClearDraftButtonProps {
  /** 비활성 판정에만 쓴다 - 무엇으로 비울지는 부모가 안다(덱 개수를 쥔 쪽이다). */
  draft: Draft
  onClear: () => void
}

export function ClearDraftButton({ draft, onClear }: ClearDraftButtonProps) {
  const isEmpty = draft.decks.every((seats) => seats.length === 0)

  return (
    <button
      type="button"
      className="btn btn--danger draft-actions__clear"
      disabled={isEmpty}
      onClick={() => {
        if (window.confirm(HELP.draftActions.confirmClear)) onClear()
      }}
    >
      전체 초기화
    </button>
  )
}
