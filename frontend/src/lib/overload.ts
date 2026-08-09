// 오버로드 옵션의 이름 규칙. 표시(오버로드 줄)와 정렬(필터 툴바)이 같은 목록을
// 봐야 하므로 컴포넌트가 아니라 lib에 둔다.

// Overload names are long enough to set the width of anything they sit in
// ("우월코드 대미지 증가"), and there are only seven of them, so the player
// reads them as symbols rather than sentences. Abbreviate to the forms used at
// the table (Fienn, 2026-07-25). The trailing "증가" is dropped first: every
// type carries it, so it distinguishes nothing.
const ABBREVIATIONS: Record<string, string> = {
  '우월코드 대미지': '우코',
  '최대 장탄 수': '장탄',
  공격력: '공',
  '차지 대미지': '차댐',
  '차지 속도': '차속',
  '크리티컬 확률': '크확',
  '크리티컬 대미지': '크댐',
  // OVERLOAD_KEYS에는 없다 - 정렬 메뉴가 아니라 표시만 줄인다(Fienn, 2026-08-09).
  명중률: '명중',
}

// The order Fienn reads them in (2026-07-25), not the order blablalink happens
// to return. A fixed order is what lets two units be compared down the column
// instead of line by line - and it doubles as the order of the sort menu.
export const OVERLOAD_KEYS = ['우코', '공', '장탄', '차속', '크댐', '크확', '차댐'] as const

export type OverloadKey = (typeof OVERLOAD_KEYS)[number]

/** Short label for an overload line. An unrecognised name (a new effect type,
 * or another locale) keeps its full text rather than being mangled. */
export const abbreviateOverload = (name: string): string => {
  const stripped = name.replace(/\s*증가$/, '')
  return ABBREVIATIONS[stripped] ?? stripped
}

/** Sorts overload lines into OVERLOAD_KEYS order. An unrecognised effect sorts
 * after all the known ones, keeping its incoming order among its peers - a new
 * type should appear, not disappear or displace a known one. */
export const sortOverload = <T extends { name: string }>(options: T[]): T[] => {
  const rank = (option: T) => {
    const index = OVERLOAD_KEYS.indexOf(abbreviateOverload(option.name) as OverloadKey)
    return index === -1 ? OVERLOAD_KEYS.length : index
  }
  return [...options].sort((a, b) => rank(a) - rank(b))
}
