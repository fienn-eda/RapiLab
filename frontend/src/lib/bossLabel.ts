// 보스를 한 줄로 부르는 이름. 유니온 저장 이름, 덱 라벨, 접힌 보스 설정 머리가
// 같은 낱말을 써야 해서 여기 한 곳에서 만든다.

import { weaknessFor } from './elementAdvantage'
import { elementLabel } from './elementName'
import { WEAKNESS_ICON } from './elementIcon'
import type { BossElement } from '../types/recommend'

/** 이 보스의 약점 속성 이름. 속성을 안 고른 보스도 자리를 지켜야 하는 곳
 * (유니온 저장 이름의 덱 나열)이 있어서 빈 문자열이 아니라 낱말을 준다. */
export const weaknessLabelOf = (element: BossElement): string =>
  element === null ? '약점없음' : elementLabel(weaknessFor(element))

export interface BossHeading {
  text: string
  /** 약점 속성 아이콘. 부를 이름이 폴백뿐이면 null. */
  iconSrc: string | null
}

/** 보스를 부르는 이름 세 단계: 고른 보스 이름 → 약점 이름 → 부르는 쪽이 준
 * 폴백. 이름은 속성이 있을 때만 쓴다 - 속성이 없으면 그 이름이 가리키던 보스도
 * 없다. */
export const bossHeading = (args: {
  bossName: string | null
  element: BossElement
  fallback: string
}): BossHeading => {
  if (args.element === null) return { text: args.fallback, iconSrc: null }
  const iconSrc = WEAKNESS_ICON[weaknessFor(args.element)]
  return { text: args.bossName ?? weaknessLabelOf(args.element), iconSrc }
}
