// 유저들이 실제로 부르는 이름. 공식 표기와 다른 별명으로 검색해도 찾아지게
// 한다 — 「홍련: 흑영」을 흑련으로, 「리틀 머메이드」를 세이렌으로 부르는 식이다.
//
// helpText.ts와 같은 규율이다: 코드를 몰라도 고칠 수 있는 것이므로 한곳에
// 모은다. 여기 오는 것은 **부르는 이름**이고, 오지 않는 것은 공식 표기의
// 변형(띄어쓰기·문장부호)이다 — 그쪽은 이미 검색이 처리한다. 「홍련 흑영」처럼
// 콜론만 뺀 것을 적을 필요가 없는 이유는 부분일치가 이미 맞히기 때문이고,
// 영문명은 슬러그가 그 노릇을 한다.
//
// **채우는 법:** 지원하는 슬러그를 전부 미리 적어 두었으니 배열만 채우면 된다.
// 옆의 주석이 그 슬러그의 한글 이름이다. 별명이 없으면 빈 배열로 그대로 둔다 -
// 지우지 않는 이유는, 목록이 곧 "무엇을 아직 안 채웠는지"를 보여주는 표이기
// 때문이다.
//
//     'scarlet-black-shadow': ['흑련', '흑스칼'],  // 홍련: 흑영
//
// 새 니케를 인코딩하면 여기에도 줄을 추가한다(nikke-skill-encoding 스킬의
// 마무리 단계). 빠뜨리면 그 니케만 별명 검색이 안 되는데, 화면에는 아무 표시도
// 나지 않는다.
//
// 키는 슬러그다. 오타가 나면 그 별명은 조용히 아무것도 안 맞히므로,
// nikkeAliases.test.ts가 모든 키가 실재하는 슬러그인지 확인한다.

export const NIKKE_ALIASES: Record<string, readonly string[]> = {
  'ada-wong':                       ['웡', '아다'],  // 에이다
  'ade-agent-bunny':                ['바이드', '바니에이드'],  // 에이드: 에이전트 바니
  'anchor-innocent-maid':           ['메앵커'],  // 앵커: 이노센트 메이드
  'anis-sparkling-summer':          ['수니스'],  // 아니스: 스파클링 서머
  'anis-star':                      ['돌니스', '별니스'],  // 아니스: 스타
  'arcana':                         ['알카'],  // 아르카나
  'arcana-fortune-mate':            ['교르카나'],  // 아르카나: 포츈 메이트
  'ark-ranger-black':               ['아크블랙', '아블'],  // 아크레인저 블랙
  'asuka-shikinami-langley-wille':  ['풍스카'],  // 아스카: WILLE
  'blanc':                          [],  // 블랑
  'bready':                         ['빵순이'],  // 브래디
  'bready-lingering':               ['빵순이'],  // 브래디(지딜)
  'bready-recommended':             ['빵순이'],  // 브래디(분배)
  'brid-silent-track':              ['클리드', '클브리드'],  // 브리드: 사일런트 트랙
  'centi':                          [],  // 센티
  'centi-signature':                [],  // 센티
  'chisato-nishikigi':              ['치토스'],  // 치사토
  'cinderella':                     ['렐루'],  // 신데렐라
  'cinderella-crystal-wave':        ['수렐루'],  // 신데렐라: 크리스탈 웨이브
  'cinderella-crystal-wave-mg':     ['수렐루'],  // 신데렐라: 크리스탈 웨이브(MG)
  'cinderella-crystal-wave-snipe':  ['수렐루'],  // 신데렐라: 크리스탈 웨이브(SR)
  'crown':                          [],  // 크라운
  'd-killer-wife':                  ['동디'],  // D: 킬러 와이프
  'delta-ninja-thief':              ['닌닌', '닌델타'],  // 델타: 닌자 시프
  'diesel-winter-sweets':           ['클디젤', '퉁젤'],  // 디젤: 윈터 스위츠
  'diesel-winter-sweets-highlight': ['클디젤', '퉁젤'],  // 디젤: 윈터 스위츠(후버)
  'diesel-winter-sweets-intro':     ['클디젤', '퉁젤'],  // 디젤: 윈터 스위츠(선버)
  'dolla':                          [],  // 도라
  'dorothy-serendipity':            ['수로시'],  // 도로시: 세렌디피티
  'drake':                          [],  // 드레이크
  'drake-signature':                [],  // 드레이크
  'ein':                            [],  // 아인
  'elegg-boom-and-shock':           ['수레그'],  // 일레그: 붐 앤 쇼크
  'emma-tactical-upgrade':          ['택엠마'],  // 엠마: 택티컬 업
  'eunhwa-tactical-upgrade':        ['택은화'],  // 은화: 택티컬 업
  'eve':                            [],  // 이브
  'flora':                          [],  // 플로라
  'flora-signature':                [],  // 플로라
  'grave':                          ['에이브'],  // 그레이브
  'guillotine-winter-slayer':       ['클로틴'],  // 길로틴: 윈터 슬레이어
  'helm':                           [],  // 헬름
  'helm-aquamarine':                ['수헬름'],  // 헬름: 아쿠아마린
  'helm-signature':                 [],  // 헬름
  'isabel':                         [],  // 이사벨
  'jill-valentine':                 [],  // 질
  'julia':                          [],  // 율리아
  'julia-signature':                [],  // 율리아
  'laplace':                        [],  // 라플라스
  'laplace-signature':              [],  // 라플라스
  'laplace-ultimate-hero':          [],  // 라플라스: 얼티밋 히어로
  'leona':                          [],  // 레오나
  'liberalio':                      [],  // 리버렐리오
  'liter':                          [],  // 리타
  'little-mermaid':                 ['세이렌'],  // 리틀 머메이드
  'ludmilla-winter-owner':          ['클루드'],  // 루드밀라: 윈터 오너
  'maiden-ice-rose':                ['클이든'],  // 메이든: 아이스 로즈
  'mana':                           [],  // 마나
  'marciana-marine-study':          ['르나린디'],  // 마르차나: 마린 스터디
  'mast-romantic-maid':             ['메스트'],  // 마스트: 로망틱 메이드
  'maxwell':                        [],  // 맥스웰
  'maxwell-ordinary-mechanic':      [],  // 맥스웰: 오디너리 미케닉
  'mihara-bonding-chain':           [],  // 미하라: 본딩 체인
  'milk-blooming-bunny':            ['바밀크'],  // 밀크: 블루밍 바니
  'mint':                           [],  // 민트
  'miranda':                        [],  // 미란다
  'miranda-signature':              [],  // 미란다
  'modernia':                       ['모앵', '뫵', '마리안'],  // 모더니아
  'moran':                          ['공룡', '짱룡'],  // 목단
  'moran-signature':                ['공룡', '짱룡'],  // 목단
  'naga':                           [],  // 나가
  'nayuta':                         [],  // 나유타
  'neon-vision-eye':                [],  // 네온: 비전 아이
  'noir':                           [],  // 누아르
  'phantom':                        [],  // 팬텀
  'phantom-signature':              [],  // 팬텀
  'prika':                          [],  // 프리카
  'privaty':                        [],  // 프리바티
  'privaty-signature':              [],  // 프리바티
  'queen-makoto-nijima':            [],  // 퀸(마코토)
  'quency-escape-queen':            [],  // 퀀시: 이스케이프 퀸
  'rapi-red-hood':                  [],  // 라피: 레드후드
  'rapi-red-hood-b1':               [],  // 라피: 레드후드(1버)
  'raven':                          [],  // 레이븐
  'red-hood':                       ['레후'],  // 레드 후드
  'rei-ayanami':                    [],  // 레이
  'rei-ayanami-tentative-name':     [],  // 레이(가칭)
  'rosanna':                        [],  // 로산나
  'rosanna-chic-ocean':             [],  // 로산나: 시크 오션
  'rosanna-signature':              [],  // 로산나
  'rouge':                          [],  // 루주
  'sakura-bloom-in-summer':         ['수쿠라'],  // 사쿠라: 블룸 인 서머
  'scarlet-black-shadow':           ['흑련'],  // 홍련: 흑영
  'snow-white':                     ['백설', '스화'],  // 스노우 화이트
  'snow-white-heavy-arms':          ['각설', '수화'],  // 스노우 화이트: 헤비암즈
  'soda-twinkling-bunny':           ['바소다'],  // 소다: 트윙클링 바니
  'soline-frost-ticket':            ['클솔린'],  // 솔린: 프로스트 티켓
  'sugar':                          [],  // 슈가
  'sugar-signature':                [],  // 슈가
  'takina-inoue':                   ['사카나'],  // 타키나
  'tove':                           [],  // 토브
  'tove-signature':                 [],  // 토브
  'velvet':                         [],  // 벨벳
  'volume':                         [],  // 볼륨
  'yukiko-amagi':                   [],  // 유키코
  'zwei':                           ['쯔바이'],  // 츠바이
  'zwei-signature':                 ['쯔바이'],  // 츠바이
}

/** 이 슬러그의 별명들. 없으면 빈 배열 - 호출부가 분기하지 않게 한다. */
export const aliasesFor = (slug: string): readonly string[] =>
  NIKKE_ALIASES[slug] ?? []
