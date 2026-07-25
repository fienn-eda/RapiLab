"""한국어 표시 이름 — 화면에 보이는 유닛 이름의 유일한 출처.

캐릭터 데이터(lootandwaifus)의 `name`은 영문이고, 그보다 나쁘게는 **캐릭터를**
가리킨다. 변형을 구분하는 정보는 슬러그에만 있어서, 카탈로그 96개 중 17개 이름이
서로 겹쳤다 — 벤치에 "Bready, Bready"가 나란히 뜨는 이유다.

blablalink에는 한글 이름이 없다(디렉토리·캐릭터 데이터 모두 영문 전용이며,
Accept-Language·쿠키·`/ko/` 경로 셋 다 196행 전부 영문을 돌려준다). 그래서 이 표는
손으로 쓴다.

**빈 문자열은 "아직 안 채움"이다** — 그 슬러그는 영문 이름으로 떨어진다. 표가 부분적인
것이 정상 상태이고, 한 줄씩 채우는 동안 화면이 비는 일은 없다.

**모드 변형만 서로 다르게 쓴다.** 접미사→한글 매핑 같은 파생 로직은 없다. 한 캐릭터의
후보들은 **로스터에 동시에 실려** 벤치에 나란히 뜰 수 있으므로, 각 줄에 통째로 다르게
쓴다 (예: "브레디 (잔류)" / "브레디 (권장)"). 같은 이름을 쓰면 test_display_names.py가
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
    "bready": "",
    "bready-lingering": "",
    "bready-recommended": "",

    # Diesel: Winter Sweets
    "diesel-winter-sweets": "",
    "diesel-winter-sweets-intro": "",
    "diesel-winter-sweets-highlight": "",

    # Cinderella: Crystal Wave
    "cinderella-crystal-wave": "",
    "cinderella-crystal-wave-mg": "",
    "cinderella-crystal-wave-snipe": "",

    # Rapi: Red Hood
    "rapi-red-hood": "",
    "rapi-red-hood-b1": "",

    # --- Burst 1 ---
    "anis-star":           "",      # Anis: Star
    "d-killer-wife":       "",      # D: Killer Wife
    "liter":               "",      # Liter
    "little-mermaid":      "",      # Little Mermaid
    "miranda":             "",      # Miranda
    "miranda-signature":   "",      # Miranda
    "moran":               "",      # Moran
    "moran-signature":     "",      # Moran
    "rosanna":             "",      # Rosanna
    "rosanna-signature":   "",      # Rosanna
    "rouge":               "",      # Rouge
    "soline-frost-ticket": "",      # Soline: Frost Ticket
    "tove":                "",      # Tove
    "tove-signature":      "",      # Tove
    "volume":              "",      # Volume
    "zwei":                "",      # Zwei
    "zwei-signature":      "",      # Zwei

    # --- Burst 2 ---
    "ade-agent-bunny":           "", # Ade: Agent Bunny
    "anchor-innocent-maid":      "", # Anchor: Innocent Maid
    "arcana":                    "", # Arcana
    "arcana-fortune-mate":       "", # Arcana: Fortune Mate
    "blanc":                     "", # Blanc
    "brid-silent-track":         "", # Brid: Silent Track
    "crown":                     "", # Crown
    "flora":                     "", # Flora
    "flora-signature":           "", # Flora
    "grave":                     "", # Grave
    "helm-aquamarine":           "", # Helm: Aquamarine
    "mast-romantic-maid":        "", # Mast: Romantic Maid
    "maxwell-ordinary-mechanic": "", # Maxwell Ordinary Mechanic
    "mint":                      "", # Mint
    "nayuta":                    "", # Nayuta
    "prika":                     "", # Prika
    "rosanna-chic-ocean":        "", # Rosanna: Chic Ocean
    "takina-inoue":              "", # Takina Inoue
    "velvet":                    "", # Velvet

    # --- Burst 3 ---
    "ada-wong":                      "", # Ada Wong
    "anis-sparkling-summer":         "", # Anis: Sparkling Summer
    "ark-ranger-black":              "", # Ark Ranger Black
    "asuka-shikinami-langley-wille": "", # Asuka Shikinami Langley: Wille
    "chisato-nishikigi":             "", # Chisato Nishikigi
    "cinderella":                    "", # Cinderella
    "dorothy-serendipity":           "", # Dorothy: Serendipity
    "drake":                         "", # Drake
    "drake-signature":               "", # Drake
    "ein":                           "", # Ein
    "elegg-boom-and-shock":          "", # Elegg: Boom and Shock
    "eve":                           "", # EVE
    "guillotine-winter-slayer":      "", # Guillotine: Winter Slayer
    "helm":                          "", # Helm
    "helm-signature":                "", # Helm
    "isabel":                        "", # Isabel
    "jill-valentine":                "", # Jill Valentine
    "julia":                         "", # Julia
    "julia-signature":               "", # Julia
    "laplace":                       "", # Laplace
    "laplace-signature":             "", # Laplace
    "laplace-ultimate-hero":         "", # Laplace Ultimate Hero
    "liberalio":                     "", # Liberalio
    "ludmilla-winter-owner":         "", # Ludmilla: Winter Owner
    "maiden-ice-rose":               "", # Maiden: Ice Rose
    "mana":                          "", # Mana
    "marciana-marine-study":         "", # Marciana: Marine Study
    "maxwell":                       "", # Maxwell
    "mihara-bonding-chain":          "", # Mihara: Bonding Chain
    "milk-blooming-bunny":           "", # Milk: Blooming Bunny
    "modernia":                      "", # Modernia
    "neon-vision-eye":               "", # Neon: Vision Eye
    "noir":                          "", # Noir
    "phantom":                       "", # Phantom
    "phantom-signature":             "", # Phantom
    "privaty":                       "", # Privaty
    "privaty-signature":             "", # Privaty
    "quency-escape-queen":           "", # Quency: Escape Queen
    "raven":                         "", # Raven
    "red-hood":                      "", # Red Hood
    "rei-ayanami":                   "", # Rei Ayanami
    "rei-ayanami-tentative-name":    "", # Rei Ayanami (Tentative Name)
    "sakura-bloom-in-summer":        "", # Sakura: Bloom in Summer
    "scarlet-black-shadow":          "", # Scarlet: Black Shadow
    "snow-white":                    "", # Snow White
    "snow-white-heavy-arms":         "", # Snow White: Heavy Arms
    "soda-twinkling-bunny":          "", # Soda: Twinkling Bunny
    "sugar":                         "", # Sugar
    "sugar-signature":               "", # Sugar
}
