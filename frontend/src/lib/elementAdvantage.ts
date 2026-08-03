// 약점 속성 ↔ 보스 본인 속성. 화면은 약점으로 말하고, 와이어는 보스 본인 속성을
// 실어 나른다 — boss_is_element 조건부 스킬(브리드의 풍압코드 피해량 증가)이
// 후자를 읽기 때문이다. 변환은 이 파일 하나를 통해서만 일어난다.
//
// SOURCE OF TRUTH: backend/app/elements.py
//   Water > Fire > Wind > Iron > Electric > Water

import type { NikkeElement } from '../types/supportedUnit'

/** 공격 속성 -> 그 속성이 이기는 속성. */
const STRONG_AGAINST: Record<NikkeElement, NikkeElement> = {
  Water: 'Fire',
  Fire: 'Wind',
  Wind: 'Iron',
  Iron: 'Electric',
  Electric: 'Water',
}

const WEAK_TO = Object.fromEntries(
  Object.entries(STRONG_AGAINST).map(([attacker, beaten]) => [beaten, attacker]),
) as Record<NikkeElement, NikkeElement>

/** 이 속성이 약점인 보스의 본인 속성. 'Water'(수냉 약점) -> 'Fire'(작열 보스) */
export const bossElementFor = (weakness: NikkeElement): NikkeElement =>
  STRONG_AGAINST[weakness]

/** 이 보스를 이기는 속성. 'Fire'(작열 보스) -> 'Water'(수냉이 약점) */
export const weaknessFor = (boss: NikkeElement): NikkeElement => WEAK_TO[boss]
