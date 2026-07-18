# Reference captures

In-game screenshots kept as evidence for things the APIs and CDN tables do not
state outright. Each one is cited from `docs/insights.md`; keep them in sync if
you replace a capture.

## `additional-stats-{attacker-elysion,supporter-missilis,defender-tetra}.png`

The "추가 능력치" (additional stats) popup, captured 2026-07-18 for one unit of
each class and three different corporations. **These decided the shape of the
ATK flat term** in `backend/app/stat_assembly.py`.

They show the flat contribution broken out by source, which is what let two
misreadings be corrected:

| Source shown | Contributes | What the capture proves |
|---|---|---|
| 호감도 RANK n | ATK | RANK 40 attacker reads **2340**, exactly the affinity table's `attacker_attack_rate` cell — so that column is **flat ATK, not a percentage**, despite the `_rate` name. Reading it as 23.4% is why the numbers would not close. |
| 화력형 / 지원형 / 방어형 RANK n | HP only | RANK 176 → 132,000 HP = 176 × 750, matching `recycle_research` Class rows (`attack: 0`, `hp: 750`) — so those values are **per rank**, not totals. |
| 엘리시온 / 미실리스 / 테트라 RANK n | ATK | RANK 170 → 4,250 = 170 × 25, matching `recycle_research` Corporation rows (`attack: 25`). |

Corporation rank is per **account**, not per unit, which is why two otherwise
identical units of different corporations do not share a flat term. The live
values come from `GetUserProfileOutpostInfo.recycle_room_researches`
(tid 1001 = Personal, 1101-1103 = Class, 1201-1205 = Corporation).

The numbers are one account's progression at one point in time; they are
evidence of the *formula*, not constants to hardcode.

**No account identifiers appear in these images** (no player name, UID or
token) - checked before committing.
