# ShiftyPad scrape recipe (confirmed live 2026-07-18)

How the collector reads a NIKKE roster's stats from ShiftyPad
(`blablalink.com/shiftyspad`) over CDP against the user's logged-in Chrome.
Every selector/procedure below was confirmed against the real page, not guessed.

## Prerequisites

- Chrome started with `--remote-debugging-port=9222` and a **logged-in
  blablalink session**. Launch (Windows):
  `"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\Users\<you>\bl-debug" "https://www.blablalink.com/"`
- Connect with `playwright-core` `chromium.connectOverCDP('http://localhost:9222')`.
- The session stays in the user's browser. We read the `game_openid` cookie only to
  replay two read-only game APIs; nothing is persisted except sanitized HTML.

## (a) Level 400 (solo-raid normalization)

Solo raid fights every account at character **level 400**. The nikke page shows the
character's real-level stats plus a **negative delta to the slider level**; with the
slider at 400, `level-400 value = actual + delta`.

- Page: `https://www.blablalink.com/shiftyspad/nikke?nikke=<resource_id>`.
- The level control is **custom buttons**, not an `input[type=range]`: a
  `div.upgrade-btns` whose four `<a>` children are `-10 / -1 / +1 / +10`. Only the
  level row carries a `-10`, so `page.locator('div.upgrade-btns',{hasText:'-10'})`
  uniquely scopes past the grade/core `-1/+1` rows.
- Read the current level from the leaf element matching `^LV\s*\d+`, then click `-10`
  while `level-400 >= 10` else `-1`, re-reading after each click, until `LV400`.
  (No single "-263" jump button exists; step down. ~29 clicks from LV663.)

## (b) Surfaces — one capture per unit

While the **Equipment** tab is active, the character-detail container already renders
every surface we parse in the DOM (hidden panels included). One `page.content()` /
container capture per unit yields main stats + overload + all three skills + cube +
collection. The tab bar is `Equipment | Skill | Collection | Cube`; switching tabs is
**not** required for capture (jsdom sees the full subtree regardless of CSS visibility).

The capture is the **smallest `div` whose textContent has `LV<n>` + `Equipment
Effects` + `min`** (a skill-row marker). Extracting it (~50-62 KB vs ~415 KB full
page) also drops the account panel — the account name, `game_uid`/UID, and tokens all
live outside this subtree.

## (c) Owned units + (d) resource_id

Two IDs coexist: the game API uses `name_code` (Rapi = 5129); ShiftyPad's URL uses
`resource_id` (Rapi = 16). Join them with the nikke **directory**:

1. **Directory** — a CDN array of 194 nikkes, each `{ id, resource_id, name_code,
   original_rare, class, element_id, is_visible, name_localkey.name (English name),
   use_burst_skill, ... }`. Served from
   `sg-tools-cdn.blablalink.com/<shard>/<hash>.json` (hash rotates, so discover the URL
   at run time: on a ShiftyPad load, pick the JSON response that is an array whose items
   have both `resource_id` and `name_code`). `name_localkey.name` gives the English
   name directly — no separate locale table needed.
2. **Owned** — `POST api.blablalink.com/api/game/proxy/Game/GetUserCharacters`
   `{ intl_open_id:<game_openid cookie>, nikke_area_id:81 }` → `data.characters[]` with
   `{ name_code, lv, core, grade }` (186 owned; the raw `combat` field is combat power).
3. **Join** owned `name_code` → directory entry → `resource_id`, English name, rarity.
   Filter `original_rare === 'SSR'` (raid content is SSR-only; 166 SSR of 194).
   `GetNikkesOrder` returns only the favourites list, not the owned roster — do not use
   it for enumeration.

Slugs come from the English name via Phase A `resolveSlug` (e.g. "Rapi: Red Hood" →
`rapi-red-hood`).

## (e) Parser DOM structure (drives parse.js)

- **Main stats** — climb from the `LV<n>` leaf to the ancestor whose textContent has
  `HP`+`ATK`+`DEF` and length < 400 (the stat panel). Each stat row is a `div` with two
  `<p>` children: label (`HP`/`ATK`/`DEF`) and value `"<actual> <-delta>"` (e.g.
  `"418862 -275319"`). `raid400 = actual + delta`; `actual` is the real-level value.
  jsdom's `textContent` has **no** newlines, so split the value cell on whitespace — do
  not rely on line splitting.
- **Overload** — the summed block is the `div.nikkes-detail-box` whose header child is
  exactly `Equipment Effects` (per-piece blocks read `Change Equipment Effects`). Its
  second child is a flex-wrap of rows; each row text is `"<English label><NN.NN>%"`
  (label and value concatenated). Parse `/^(.+?)\s*(\d+(?:\.\d+)?)%$/`.
- **Skills** — three `div.w-40…` rows whose text matches `\d+min`, in DOM order
  skill1 / skill2 / burst. Level is the integer immediately before `min`
  (`"Battlefield Assessment10min-1+1max"` → 10). Levels differ per skill
  (e.g. Liter 10/4/10, Moran 7/10/10).
- **Cube** — the compact `div` whose text starts `Battle` and contains `Arena`. Take
  the substring before `Arena` (the Battle/PvE loadout = solo raid). If it reads
  `No data available`, the unit has no PvE cube → `null`. Else name = `…Cube` match,
  level = `LV.<n>` (max is 15).

## (f) Overload labels — English → Korean (backend's 7)

Confirmed against real units (Rapi, Liter, Moran, Maxwell):

| English label (ShiftyPad)             | Korean (backend `overload_effects.py`) | status |
|---------------------------------------|----------------------------------------|--------|
| Increase ATK                          | 공격력 증가                            | confirmed |
| Increase Element Damage Dealt         | 우월코드 대미지 증가                   | confirmed |
| Increase Max Ammunition Capacity      | 최대 장탄 수 증가                      | confirmed |
| Increase Critical Rate                | 크리티컬 확률 증가                     | confirmed |
| Increase Critical Damage              | 크리티컬 대미지 증가                   | confirmed |
| Increase Charge Speed                 | 차지 속도 증가                         | confirmed |
| Increase Charge Damage                | 차지 대미지 증가                       | **unconfirmed** — no captured unit had it; label follows the observed pattern, verify when a charge-damage unit is captured |

**Dropped by design:** ShiftyPad also shows `Increase Hit Rate` (명중률) and
`Increase DEF` (방어력). The engine models only the 7 damage-relevant overloads above,
so the parser drops any unmapped label. This is intentional data reduction, not a bug.

## (g) Sanitization

Extraction already excludes the account panel. `capture.js` additionally scrubs any
`game_uid` / account name / `uin` passed to it, as a safety net. Verify fixtures carry
no identifiers:
`grep -rliE '78550796|FIENN|game_openid|access_token|Bearer|cookie' __fixtures__` → 0.

## Fixtures

`__fixtures__/<slug>.page.html` — sanitized, extracted detail container, level 400.
Captured: `rapi-red-hood` (Attacker, cube), `liter` (Supporter, no Battle cube),
`moran` (Defender, Bastion cube, charge-speed overload), `maxwell` (Attacker, low
investment 1/1/1 skills, no cube). Re-capture with `node capture.js <resource_id> <slug>`.
