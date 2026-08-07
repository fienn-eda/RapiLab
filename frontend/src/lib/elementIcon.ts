// 속성 아이콘 경로. blablalink의 코드 아이콘을 scripts/download_element_icons.py로
// 받아둔 것이다. 보스 설정의 약점 선택과 회차 보스 카드가 같이 쓴다.

import type { NikkeElement } from '../types/supportedUnit'

export const WEAKNESS_ICON: Record<NikkeElement, string> = {
  Fire: '/elements/fire.png',
  Water: '/elements/water.png',
  Wind: '/elements/wind.png',
  Iron: '/elements/iron.png',
  Electric: '/elements/electric.png',
}
