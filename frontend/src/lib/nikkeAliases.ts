// 유저들이 실제로 부르는 이름. 공식 표기와 다른 별명으로 검색해도 찾아지게
// 한다 — 「홍련: 흑영」을 흑련으로, 「리틀 머메이드」를 세이렌으로 부르는 식이다.
//
// helpText.ts와 같은 규율이다: 코드를 몰라도 고칠 수 있는 것이므로 한곳에
// 모은다. 여기 오는 것은 **부르는 이름**이고, 오지 않는 것은 공식 표기의
// 변형(띄어쓰기·문장부호)이다 — 그쪽은 이미 검색이 처리한다. 「홍련 흑영」처럼
// 콜론만 뺀 것을 적을 필요가 없는 이유는 부분일치가 이미 맞히기 때문이고,
// 영문명은 슬러그가 그 노릇을 한다.
//
// 키는 슬러그다. 오타가 나면 그 별명은 조용히 아무것도 안 맞히므로,
// nikkeAliases.test.ts가 모든 키가 실재하는 슬러그인지 확인한다.

export const NIKKE_ALIASES: Record<string, readonly string[]> = {
  'scarlet-black-shadow': ['흑련'],
  'little-mermaid': ['세이렌'],
}

/** 이 슬러그의 별명들. 없으면 빈 배열 - 호출부가 분기하지 않게 한다. */
export const aliasesFor = (slug: string): readonly string[] =>
  NIKKE_ALIASES[slug] ?? []
