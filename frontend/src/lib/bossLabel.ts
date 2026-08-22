// 보스와 회차를 한 줄로 부르는 이름. 유니온 저장 이름, 덱 라벨, 접힌 보스 설정
// 머리, 시즌 가이드 카드 제목이 같은 낱말을 써야 해서 여기 한 곳에서 만든다.

import { weaknessFor } from './elementAdvantage'
import { elementLabel } from './elementName'
import { WEAKNESS_ICON } from './elementIcon'
import type { BossElement } from '../types/recommend'
import type { RaidRotation } from '../types/raidRotation'
import type { NikkeElement } from '../types/supportedUnit'

/** 이 보스의 약점 속성 이름. 속성을 안 고른 보스도 자리를 지켜야 하는 곳
 * (유니온 저장 이름의 덱 나열)이 있어서 빈 문자열이 아니라 낱말을 준다. */
export const weaknessLabelOf = (element: BossElement): string =>
  element === null ? '약점없음' : elementLabel(weaknessFor(element))

export interface BossHeading {
  text: string
  /** 약점 속성 아이콘. 부를 이름이 폴백뿐이면 null. */
  iconSrc: string | null
  /** 아이콘이 가리키는 바로 그 약점 속성. 화면이 이 이름을 속성 색으로 켤 때
   * 쓴다(덱 라벨) - 아이콘 경로에서 속성을 되짚는 대신 같이 들고 다닌다.
   * iconSrc가 null이면 이것도 null이다. */
  weakness: NikkeElement | null
}

/** 보스를 부르는 이름 세 단계: 고른 보스 이름 → 약점 이름 → 부르는 쪽이 준
 * 폴백. 이름은 속성이 있을 때만 쓴다 - 속성이 없으면 그 이름이 가리키던 보스도
 * 없다. */
export const bossHeading = (args: {
  bossName: string | null
  element: BossElement
  fallback: string
}): BossHeading => {
  if (args.element === null) return { text: args.fallback, iconSrc: null, weakness: null }
  const weakness = weaknessFor(args.element)
  return {
    text: args.bossName ?? weaknessLabelOf(args.element),
    iconSrc: WEAKNESS_ICON[weakness],
    weakness,
  }
}

/** 시즌 가이드 카드의 제목. 「솔로 레이드 40시즌」에서 회차만 뽑는 이유는 그
 * 카드가 솔로 탭 안에만 서기 때문이다 - 「솔로 레이드」는 탭이 이미 말하고
 * 있다. 형식이 다른 회차(「유니온 레이드 7/31」)는 뽑을 것이 없으므로 제목을
 * 통째로 쓴다. */
export const guideTitle = (rotation: RaidRotation | null): string => {
  if (rotation === null) return '보스 가이드'
  const season = /\d+시즌/.exec(rotation.title)
  return `${season === null ? rotation.title : season[0]} 가이드`
}
