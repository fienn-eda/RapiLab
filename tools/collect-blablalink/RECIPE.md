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

## (b) Surfaces — visit each tab, pluck each surface

The tab bar is `Equipment | Skill | Collection | Cube`, and the tabs are **`v-if`, not
`v-show`**: only the active tab's markup is in the DOM, and the main stat panel is a
**separate DOM branch** from all of them — there is no single container that holds
everything. (A pre-implementation manual spike saw the tabs appear to coexist because
the SPA caches recently-viewed tab state; that is not reproducible from a fresh load.)
Skill markup in particular only renders after the Skill tab is actually opened.

So `captureUnit` visits `Equipment` (overload), `Skill`, and `Cube` in turn and, on
each, plucks each parseable surface by its own local anchor (`pluckSurfaces`):

- stat rows — each `div` with two `<p>` children whose label is HP/ATK/DEF and whose
  value cell is `"<actual> <signed delta>"` (the delta distinguishes the main panel
  from equipment/cube stat displays, which are bare numbers);
- overload — the `div` whose header child is exactly `Equipment Effects`;
- skills — the `div.w-40…` rows matching `\d+min`;
- cube — the compact `Battle…Arena` div.

The stat-panel fragment repeats on every tab and is de-duped. The plucked fragments
(~5–24 KB, vs ~415 KB for the full page) exclude the account panel — the account name,
`game_uid`/UID, and tokens live in a different branch and are never matched.

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

**Known slug limitation (E2E 2026-07-18, full 159-unit collection):** `resolveSlug`'s
alias table was built for ExiaInvasion's *short* names, but the directory gives *full*
names, so a few units mismatch the backend's encoded slugs and are silently excluded
from recommendation:
- A base unit and its variant collide when an alias maps the base to the variant's slug:
  "Soline" + "Soline: Frost Ticket" both → `soline-frost-ticket`; likewise "Marciana".
- Two units share a display name: both "Rei" → `rei-ayanami` (base vs tentative-name are
  indistinguishable by name — needs `name_code`/`resource_id`).
- The encoded slug carries info absent from the game name: game "Julia" → `julia`, but the
  encoded character is `julia-signature`.
The collected `roster.json` itself is correct (it stores the unambiguous `name_en` +
`resource_id`); this is a downstream name→slug mapping gap. A robust fix keys encoded
characters by `name_code` rather than name-derived slug — deferred as its own task.

## (e) Parser DOM structure (drives parse.js)

- **Main stats** — find the stat rows directly: each is a `div` with two `<p>` children,
  label (`HP`/`ATK`/`DEF`) and value `"<actual> <signed delta>"` (e.g. `"418862 -275319"`
  or `"5097 +89718"`). The signed-delta value cell is what identifies the main panel
  (equipment/cube stat displays are bare numbers), so this is LV-position-independent —
  do **not** rely on the LV element's position (the responsive layout does not always
  nest LV with the rows). `raid400 = actual + delta`; delta is negative when the real
  level is above 400 and positive when a level-1 unit is stepped up; `actual` is the
  real-level value. jsdom's `textContent` has **no** newlines and `\bATK\b` fails on
  concatenated text like `"ATK240903"`, so match structure/label, not lexemes.
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

`__fixtures__/<slug>.page.html` — sanitized, plucked surfaces, level 400. Captured:
`rapi-red-hood` (Attacker, cube), `liter` (Supporter, no Battle cube), `moran`
(Defender, Bastion cube, charge-speed overload), `maxwell` (Attacker, low investment
1/1/1, no cube), `neon-blue-ocean` (uninvested lv1 stepped up → positive delta, empty
overload), `blanc` (Defender, per-tab pluck, dropped Hit Rate/DEF overloads, distinct
skill levels 4/7/9, no cube). Re-capture with `node capture.js <resource_id> <slug>`.
