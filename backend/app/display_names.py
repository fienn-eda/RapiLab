"""한국어 표시 이름 — 화면에 보이는 유닛 이름의 유일한 출처.

캐릭터 데이터(lootandwaifus)의 `name`은 영문이고, 그보다 나쁘게는 **캐릭터를**
가리킨다. 변형을 구분하는 정보는 슬러그에만 있어서, 카탈로그 96개 중 17개 이름이
서로 겹쳤다 — 벤치에 "Bready, Bready"가 나란히 뜨는 이유다.

**이름은 음차가 아니라 한국 서버 공식 표기다.** 표기는 ShiftyPad가 로케일마다 따로
서빙하는 캐릭터 목록에서 오고, `tools/collect-blablalink/korean-names.js`가 그것을
`nikke-directory.json`의 `name_ko`로 받아 둔다 — 추측할 일이 없다는 뜻이다. 실제로
`dolla`는 "돌라"가 아니라 **"도라"**이고 `moran`은 "모란"이 아니라 **"목단"**이다.
표 자체를 자동 생성하지 않는 이유는 아래 두 규칙(모드 변형·애장품) 때문이며, 그
판단만 손으로 한다. 구분자는 원문의 " : "가 아니라 이 표의 관례인 ": "로 적는다.

**빈 문자열은 "아직 안 채움"이다** — 그 슬러그는 영문 이름으로 떨어진다. 표가 부분적인
것이 정상 상태이고, 한 줄씩 채우는 동안 화면이 비는 일은 없다.

**모드 변형만 서로 다르게 쓴다.** 접미사→한글 매핑 같은 파생 로직은 없다. 한 캐릭터의
후보들은 **로스터에 동시에 실려** 벤치에 나란히 뜰 수 있으므로, 각 줄에 통째로 다르게
쓴다 (예: "브래디(지딜)" / "브래디(분배)"). 같은 이름을 쓰면 test_display_names.py가
잡는다.

**애장품(`-signature`)은 base와 같은 이름으로 쓴다.** 로스터는 둘 중 하나로만 해석하므로
`helm`과 `helm-signature`가 함께 뜨는 일이 없다 — 둘 다 "헬름"이 맞고, 어느 빌드인지는
UI가 초상화 뱃지와 이름 옆 하트로 말한다. 유일성은 **캐릭터 단위로만** 요구된다:
서로 다른 캐릭터가 같은 이름을 가지면(오타) 그때 테스트가 잡는다.

설계: docs/superpowers/specs/2026-07-25-korean-display-names-design.md
"""

DISPLAY_NAMES = {
    # --- 모드 변형: 같은 캐릭터가 여러 슬러그로 나뉜다. 반드시 서로 다르게 ---
    # Bready
    "bready": "브래디",
    "bready-lingering": "브래디(지딜)",
    "bready-recommended": "브래디(분배)",

    # Diesel: Winter Sweets
    "diesel-winter-sweets": "디젤: 윈터 스위츠",
    "diesel-winter-sweets-intro": "디젤: 윈터 스위츠(선버)",
    "diesel-winter-sweets-highlight": "디젤: 윈터 스위츠(후버)",

    # Cinderella: Crystal Wave
    "cinderella-crystal-wave": "신데렐라: 크리스탈 웨이브",
    "cinderella-crystal-wave-mg": "신데렐라: 크리스탈 웨이브(MG)",
    "cinderella-crystal-wave-snipe": "신데렐라: 크리스탈 웨이브(SR)",

    # Rapi: Red Hood
    "rapi-red-hood": "라피: 레드후드",
    "rapi-red-hood-b1": "라피: 레드후드(1버)",

    # --- Burst 1 ---
    "anis-star":             "아니스: 스타",      # Anis: Star
    "d-killer-wife":         "D: 킬러 와이프",      # D: Killer Wife
    "emma-tactical-upgrade": "엠마: 택티컬 업",      # Emma: Tactical Upgrade
    "liter":                 "리타",      # Liter
    "little-mermaid":        "리틀 머메이드",      # Little Mermaid
    "miranda":               "미란다",      # Miranda
    "miranda-signature":     "미란다",      # Miranda
    "moran":                 "목단",      # Moran
    "moran-signature":       "목단",      # Moran
    "rosanna":               "로산나",      # Rosanna
    "rosanna-signature":     "로산나",      # Rosanna
    "rouge":                 "루주",      # Rouge
    "soline-frost-ticket":   "솔린: 프로스트 티켓",      # Soline: Frost Ticket
    "tove":                  "토브",      # Tove
    "tove-signature":        "토브",      # Tove
    "volume":                "볼륨",      # Volume
    "zwei":                  "츠바이",      # Zwei
    "zwei-signature":        "츠바이",      # Zwei

    # --- Burst 2 ---
    "ade-agent-bunny":           "에이드: 에이전트 바니", # Ade: Agent Bunny
    "anchor-innocent-maid":      "앵커: 이노센트 메이드", # Anchor: Innocent Maid
    "arcana":                    "아르카나", # Arcana
    "arcana-fortune-mate":       "아르카나: 포츈 메이트", # Arcana: Fortune Mate
    "blanc":                     "블랑", # Blanc
    "brid-silent-track":         "브리드: 사일런트 트랙", # Brid: Silent Track
    "centi":                     "센티",   # Centi
    "centi-signature":           "센티",    # Centi
    "crown":                     "크라운", # Crown
    "delta-ninja-thief":         "델타: 닌자 시프", # Delta: Ninja Thief
    "dolla":                     "도라", # Dolla
    "eunhwa-tactical-upgrade":   "은화: 택티컬 업", # Eunhwa: Tactical Upgrade
    "flora":                     "플로라", # Flora
    "flora-signature":           "플로라", # Flora
    "grave":                     "그레이브", # Grave
    "helm-aquamarine":           "헬름: 아쿠아마린", # Helm: Aquamarine
    "leona":                     "레오나", # Leona
    "mast-romantic-maid":        "마스트: 로망틱 메이드", # Mast: Romantic Maid
    "maxwell-ordinary-mechanic": "맥스웰: 오디너리 미케닉", # Maxwell Ordinary Mechanic
    "mint":                      "민트", # Mint
    "naga":                      "나가", # Naga
    "nayuta":                    "나유타", # Nayuta
    "prika":                     "프리카", # Prika
    "rosanna-chic-ocean":        "로산나: 시크 오션", # Rosanna: Chic Ocean
    "takina-inoue":              "타키나", # Takina Inoue
    "velvet":                    "벨벳", # Velvet

    # --- Burst 3 ---
    "ada-wong":                      "에이다", # Ada Wong
    "anis-sparkling-summer":         "아니스: 스파클링 서머", # Anis: Sparkling Summer
    "ark-ranger-black":              "아크레인저 블랙", # Ark Ranger Black
    "asuka-shikinami-langley-wille": "아스카: WILLE", # Asuka Shikinami Langley: Wille
    "chisato-nishikigi":             "치사토", # Chisato Nishikigi
    "cinderella":                    "신데렐라", # Cinderella
    "dorothy-serendipity":           "도로시: 세렌디피티", # Dorothy: Serendipity
    "drake":                         "드레이크", # Drake
    "drake-signature":               "드레이크", # Drake
    "ein":                           "아인", # Ein
    "elegg-boom-and-shock":          "일레그: 붐 앤 쇼크", # Elegg: Boom and Shock
    "eve":                           "이브", # EVE
    "guillotine-winter-slayer":      "길로틴: 윈터 슬레이어", # Guillotine: Winter Slayer
    "helm":                          "헬름", # Helm
    "helm-signature":                "헬름", # Helm
    "isabel":                        "이사벨", # Isabel
    "jill-valentine":                "질", # Jill Valentine
    "julia":                         "율리아", # Julia
    "julia-signature":               "율리아", # Julia
    "laplace":                       "라플라스", # Laplace
    "laplace-signature":             "라플라스", # Laplace
    "laplace-ultimate-hero":         "라플라스: 얼티밋 히어로", # Laplace Ultimate Hero
    "liberalio":                     "리버렐리오", # Liberalio
    "ludmilla-winter-owner":         "루드밀라: 윈터 오너", # Ludmilla: Winter Owner
    "maiden-ice-rose":               "메이든: 아이스 로즈", # Maiden: Ice Rose
    "mana":                          "마나", # Mana
    "marciana-marine-study":         "마르차나: 마린 스터디", # Marciana: Marine Study
    "maxwell":                       "맥스웰", # Maxwell
    "mihara-bonding-chain":          "미하라: 본딩 체인", # Mihara: Bonding Chain
    "milk-blooming-bunny":           "밀크: 블루밍 바니", # Milk: Blooming Bunny
    "modernia":                      "모더니아", # Modernia
    "neon-vision-eye":               "네온: 비전 아이", # Neon: Vision Eye
    "noir":                          "누아르", # Noir
    "phantom":                       "팬텀", # Phantom
    "phantom-signature":             "팬텀", # Phantom
    "privaty":                       "프리바티", # Privaty
    "privaty-signature":             "프리바티", # Privaty
    "queen-makoto-nijima":           "퀸(마코토)", # Queen (Makoto)
    "quency-escape-queen":           "퀀시: 이스케이프 퀸", # Quency: Escape Queen
    "raven":                         "레이븐", # Raven
    "red-hood":                      "레드 후드", # Red Hood
    "rei-ayanami":                   "레이", # Rei Ayanami
    "rei-ayanami-tentative-name":    "레이(가칭)", # Rei Ayanami (Tentative Name)
    "sakura-bloom-in-summer":        "사쿠라: 블룸 인 서머", # Sakura: Bloom in Summer
    "scarlet-black-shadow":          "홍련: 흑영", # Scarlet: Black Shadow
    "snow-white":                    "스노우 화이트", # Snow White
    "snow-white-heavy-arms":         "스노우 화이트: 헤비암즈", # Snow White: Heavy Arms
    "soda-twinkling-bunny":          "소다: 트윙클링 바니", # Soda: Twinkling Bunny
    "sugar":                         "슈가", # Sugar
    "sugar-signature":               "슈가", # Sugar
    "yukiko-amagi":                  "유키코", # Yukiko
}
