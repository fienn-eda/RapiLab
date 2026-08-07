# ShiftyPad scrape recipe (confirmed live 2026-07-18)

How the collector reads a NIKKE roster's stats from ShiftyPad
(`blablalink.com/shiftyspad`) over CDP against the user's logged-in Chrome.
Every selector/procedure below was confirmed against the real page, not guessed.

## Prerequisites

- Chrome started with `--remote-debugging-port=9222` and a **logged-in
  blablalink session**. Launch from PowerShell — the `&` call operator is
  required, because a command starting with a quoted string is parsed as a
  string expression and the following `--` becomes an operator
  (`'--' 연산자는 변수 또는 속성에서만 동작합니다`):

  ```powershell
  & "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir=C:\Users\<you>\bl-debug https://www.blablalink.com/
  ```

  `--user-data-dir` names a SEPARATE Chrome profile, so log in to blablalink
  once inside the window it opens; your everyday profile's session is not
  visible there.
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

**Slug mapping — RESOLVED 2026-07-18 (this section previously described the gap as open).**
The name→slug mismatches found in the 159-unit E2E (base-vs-variant collisions for
Soline/Marciana, three units displaying as "Rei", Julia's base-vs-signature) are fixed.
The fix keys by **`resource_id`**, not `name_code` as originally planned — `roster.json`
already carries `resource_id`, so no extra collection was needed.

Downstream owner: `frontend/src/lib/resourceIdSlugMap.ts` maps `resource_id → **base**
encoded slug. **The collector needs no change for this** — it already emits the
unambiguous `name_en` + `resource_id`, which is exactly what the mapping consumes.

Two things worth knowing if you touch the collector's output shape:
- **Keep emitting `resource_id` for every unit.** It is the mapping's only key; a unit
  without one falls back to a raw name-derived slug and is reported as unsupported.
- **`resource_id` cannot distinguish base from signature.** A unit with a Favorite Item
  (애장품) shares ONE `resource_id` across both encoded forms — Drake is 101 either way —
  so ownership travels as a per-unit `favorite_item` flag, not in the map. The sync
  endpoint derives that flag from `favorite_item_tid` (2xxxxx = 애장품). **This
  collector cannot**: it reads ShiftyPad pages, which show the collectible's name but
  not its grade, so a scraped roster.json omits the flag and every dual-slot unit
  stays on its base slug. Capturing the **Collection tab** (`favorite_rare`) would
  close that gap; until then, scrape users edit the slug by hand.

Details: `docs/superpowers/specs/2026-07-18-roster-resource-id-slug-map-design.md`,
`docs/decisions.md`.

### Exporting the app's synced roster (`roster-drafts.json`)

The measurement scripts (`scripts/measure_record_calibration.py`,
`scripts/audit_collectible_coverage.py`, everything through
`scripts/roster_fixture.py`) read `roster-drafts.json` — the app's own synced
roster, already slug-resolved. **Syncing in the app does not write this file**:
the sync lands in the browser's localStorage, and the file is lifted out of it by
hand. A sync without this step leaves every script reading the previous snapshot,
which looks exactly like "the change had no effect".

A profile is one **(open_id, area)** pair, not one account: an account can hold a
roster on several game servers and those must never mix, so the store is keyed
`"<open_id>:<area>"` (`frontend/src/types/profile.ts`). List what is stored before
copying anything — in the browser console (F12) with the app open:

```js
const s = JSON.parse(localStorage.getItem('nikke-profiles'))
console.table(Object.entries(s.profiles).map(([key, p]) =>
  ({ key, openId: p.openId, area: p.area, nickname: p.nickname, units: p.roster.length })))
```

Then copy one profile's roster (`s.activeKey` is whichever is on screen):

```js
copy(JSON.stringify(s.profiles['<open_id>:<area>'].roster, null, 2))
```

`copy()` puts it on the clipboard; paste over `tools/collect-blablalink/roster-drafts.json`.

Several accounts (or one account on two servers) each get their own file —
`roster-drafts-<label>.json`, all gitignored. The scripts that read a roster take
`--roster PATH`, so a second export is measured without swapping files:

```
python3 scripts/measure_record_calibration.py --roster tools/collect-blablalink/roster-drafts-kr.json
```

Confirm the fields that matter actually arrived before measuring anything. Charge
speed is the one that fails silently: it rounds per gear roll, so a roster whose
overload rows carry no `lines` is *estimated* from the total rather than computed
(`docs/measurements/prika-charge.md`).

```
python3 -c "import json,sys; d=json.load(open(sys.argv[1],encoding='utf-8')); r=[o for x in d for o in x.get('overload_options',[]) if o['name']=='차지 속도 증가']; print(sum(1 for x in d if x.get('collectible_tid')),'/',len(d),'with a collectible;',sum(1 for o in r if o.get('lines')),'/',len(r),'charge-speed rows with per-gear rolls')" tools/collect-blablalink/roster-drafts.json
```

Zero rolls against a non-zero row count means the sync ran against a backend from
before the rolls were carried — re-sync after updating it, or the re-sync will
look like it did nothing.

Gitignored — personal investment data, local only.

### Static game tables — computed CDN paths, not interception (`resource-url.js`)

ShiftyPad serves its static tables from `sg-tools-cdn.blablalink.com` under obfuscated
paths, but the obfuscation is a **pure function of the logical path**, not a rotating
manifest: djb2 (a different prime per directory depth) names the directory segments,
md5 of the whole path names the file. `resource-url.js` transcribes it from the app
bundle, so any table is a plain HTTP GET — **no browser, no session**:

```js
const { fetchResource } = require('./resource-url')
await fetchResource('/equip/favorite_rare_map.json')
```

Logical paths are string literals in the bundle (search it for `getGameJsonResource`).

**Prefer this to response interception.** Interception waits for the SPA to request a
file, so it cannot reach one the SPA only requests behind a logged-in view — that is
why the collectible table came back empty even with `--headless` (the browser launched
and the directory resolved; the record was simply never requested). Only `spine/`
paths use a different scheme; the resolver refuses them rather than mis-hashing.

### Collectibles (`node collect.js --collectibles`)

Writes every 소장품/애장품 record to `collectibles.json` (gitignored scratch): R and SR
per weapon group, plus one SSR favorite item per unit that has one — 33 today.
`/equip/favorite_rare_map.json` names the ids, `/equip/{ko|en}/favorite_<id>.json` is
each record. Opens no browser. Merge into the committed table with
`python3 scripts/update_collectible_table.py`, which keeps only what the engine reads
(the raw records are 272 KB, larger than all of `tables.json`).

### Directory snapshot (`nikke-directory.json`)

`node collect.js --directory` writes the directory's public identity fields
(`resource_id` / `name_code` / `name_en` / `original_rare`, one entry per nikke) to
`nikke-directory.json`, then stops — no roster, no capture. **This mode needs no
account**: it returns before the `game_openid` lookup, so only a ShiftyPad page load
is required, and `trimDirectory` keeps no ownership or stat fields. That is why the
file is committed while `roster.json` is gitignored.

The snapshot is the evidence `backend/tests/test_resource_id_directory.py` checks the
slug map against: it proves each mapped `resource_id` really names the unit its slug
claims. Without it, a *wrong-but-valid* id (Soline's base 71 in place of her Frost
Ticket variant 74) leaves every slug encoded and mis-maps the unit silently.

Refresh it when new nikkes release — a `resource_id` absent from the snapshot fails
the guard, which is also how you look up the id for a unit nobody owns yet.

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

## (f) Overload labels — English → Korean (backend's 8)

**ShiftyPad writes every one of these two ways**, and `parse.js` maps both. The
pages captured in July read `Increase X`; the page as served on 2026-08-07 reads
`Increased X`, and Element Damage Dealt became Elemental Advantage Dmg. Same
rows, same values, same gear — only the wording moved.

**An unmapped label drops its row silently**, so this rewording cost every unit
its entire overload while `npm test` stayed green on the July fixtures: a live
`node collect.js` returned 159 units with `overload: []` and nothing failed.
Two things catch it — `--details` (option ids, independent of any label) and
the `rapi-red-hood-relabelled` fixture, which is the same unit and gear under
the newer wording and must parse identically to `rapi-red-hood`.

| English label (ShiftyPad)                                    | Korean (backend `overload_effects.py`) | status |
|--------------------------------------------------------------|----------------------------------------|--------|
| Increase ATK / Increase**d** ATK                              | 공격력 증가                            | both confirmed |
| Increase Element Damage Dealt / Increase**d** Elemental Advantage Dmg | 우월코드 대미지 증가          | both confirmed |
| Increase(**d**) Max Ammunition Capacity                       | 최대 장탄 수 증가                      | both confirmed |
| Increase(**d**) Critical Rate                                 | 크리티컬 확률 증가                     | both confirmed |
| Increase(**d**) Critical Damage                               | 크리티컬 대미지 증가                   | both confirmed |
| Increase(**d**) Charge Speed                                  | 차지 속도 증가                         | both confirmed |
| Increase(**d**) Charge Damage                                 | 차지 대미지 증가                       | **unconfirmed** — no captured or observed unit has carried it; both spellings follow the pattern of the rows that were observed |
| Increase(**d**) Hit Rate                                      | 명중률 증가                            | both confirmed — collected since 2026-08-07 |

**Collected since 2026-08-07:** `Increase Hit Rate` (명중률 증가) used to be
dropped for the same reason as DEF below — no engine consumer — but the engine
gained one (`accuracy.core_hit_rate`: hit rate narrows a normal attack's
bullet spread against the boss's core), so the parser now maps the label. No
value table was needed for the label itself — blablalink gives the summed
percentage as text, same as the other 7 rows; fitting the overload's own
level curve (which `option_id` it is, what each level is worth) still needs a
roster resync (`docs/roadmap.md` To-Do).

**Dropped by design:** ShiftyPad also shows `Increase DEF` (방어력). The engine
consumes enemy DEF only, never an ally's, so this stays an inert stat and the
parser drops it — the only label still dropped for that reason.

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
overload), `blanc` (Defender, per-tab pluck, Hit Rate overload row (parsed since
2026-08-07) alongside a dropped DEF overload, distinct skill levels 4/7/9, no
cube), `rapi-red-hood-relabelled` (2026-08-07 — same unit and same gear as
`rapi-red-hood` under the newer `Increased X` wording; the pair is what proves
both spellings parse to the same rows). Re-capture with
`node capture.js <resource_id> <slug>`.
