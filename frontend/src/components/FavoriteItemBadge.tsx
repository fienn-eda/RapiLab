// Marks a unit the player has her Favorite Item (애장품) equipped on.
//
// Not derivable from the slug: only 13 units have a distinct "-signature"
// encoding, so for everyone else the equipped item changes stats without
// changing the slug. The flag comes from the sync and rides on NikkeDraft
// (see nikkeDraft.ts), the same way breakthrough and core do.
//
// A heart rather than a word, because it sits on the portrait next to the
// breakthrough stars - a label there would crowd the art the badges are drawn
// over. The colour lives in CSS, like InvestmentBadge's stars.

interface FavoriteItemBadgeProps {
  /** Undefined when the roster never reported it - drawn as nothing, not as "no". */
  equipped?: boolean
}

export function FavoriteItemBadge({ equipped }: FavoriteItemBadgeProps) {
  if (!equipped) return null
  return (
    <span className="favorite-item" title="애장품 장착">
      ♥
    </span>
  )
}
