# 소장품(collectible) 스킬 효과 반영 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 유닛별로 장착한 소장품의 무기군 스킬 효과를 동기화해 시뮬레이터의 대미지 계산에 반영한다.

**Architecture:** `cube_effects.py`를 그대로 본뜬 `collectible_effects.py`가 `(tid, level)`을 커밋된 `tables.json`의 소장품 레코드에 대조해 두 가지를 내놓는다 — 「배율」 스탯은 `NikkeSpec.weapon_stats`의 무기 기본값에 곱해지고, 평범한 % 스탯은 permanent self `Effect`로 큐브 옆에 붙는다. 유닛별 `collectible_tid`/`collectible_level`은 동기화 경로가 이미 받아오는 값(`favorite_item_tid`/`favorite_item_lv`)을 실어 나르기만 하면 된다.

**Tech Stack:** Python 3.13 / pytest / pydantic (backend) · Playwright (collector) · React + TypeScript + Vitest (frontend)

## Global Constraints

- **백엔드 실행은 `python3`** (anaconda). `python`은 의존성이 없다.
- **작업 디렉터리는 워크트리** `C:\Users\fienn\Desktop\NikkeDeckBuilder\.claude\worktrees\deck-damage-breakdown`. 원본 체크아웃으로 `cd` 하지 않는다.
- **기준선: 백엔드 1468 passed / 3 skipped.** 각 태스크 종료 시 이 수치가 유지되거나 늘어야 하며, 줄면 실패다.
- **`collectible_sample` 키는 건드리지 않는다.** `stat_assembly.collectible_atk`/`collectible_hp`가 읽는 자리이고 스탯 공식 골든 테스트가 걸려 있다. 새 데이터는 `collectibles` 키로 **추가**한다.
- **DPS 무관 스탯은 매핑하지 않는다**: 방어력 · 엄폐물 최대 체력 · 받는 대미지 감소. 큐브와 동일한 규칙.
- **소장품 배열은 0-based** (16칸, 단계 0~15). 큐브는 1-based (15칸). 확인됨.
- **최대치는 `record["levelN"][-1]`을 스킬레벨로 써서 사다리를 인덱싱한다. `ladder[-1]`은 금지** — 사다리는 자기 상한을 넘어 도달 불가능한 값이 이어질 수 있다 (`docs/insights.md`, 큐브 전례).
- 커밋 메시지는 영어, 문서/주석의 설명문은 기존 파일의 언어를 따른다.

---

## File Structure

| 파일 | 책임 |
|---|---|
| `tools/collect-blablalink/collect.js` (수정) | `--collectibles` 모드: CDN에서 소장품 레코드 캡처 |
| `data/nikke-stat-tables/tables.json` (수정) | `collectibles` 키 추가 (`id` → 레코드) |
| `backend/app/collectible_effects.py` (신규) | `(tid, level)` → (무기스탯 배수, Effect 목록) |
| `backend/tests/test_collectible_effects.py` (신규) | 해석기 단위 테스트 |
| `backend/app/models.py` (수정) | `UserNikkeState`에 `collectible_tid`/`collectible_level` |
| `backend/app/roster.py` (수정) | `NikkeSpec` 필드 + `_passive_effects`에 소장품 효과 |
| `backend/app/user_roster.py` (수정) | state → spec 전달 + 「배율」을 `weapon_stats`에 적용 |
| `backend/app/roster_assembly.py` (수정) | `build_unit`이 `collectible` 방출 |
| `frontend/src/lib/rosterImport.ts` (수정) | roster.json → NikkeDraft 통과 |
| `frontend/src/types/nikkeDraft.ts` (수정) | Draft 필드 + `UserNikkeState` 방출 |
| `backend/tests/test_damage_formula.py` (수정) | 에이드 테스트를 "정확히 맞음"으로 뒤집기 |

---

### Task 1: 소장품 레코드 수집

**Files:**
- Modify: `tools/collect-blablalink/collect.js`
- Modify: `data/nikke-stat-tables/tables.json`

**Interfaces:**
- Consumes: 없음 (첫 태스크)
- Produces: `tables.json["collectibles"]` — `{ "<id>": <레코드> }`. 각 레코드는 CDN 원본 그대로이며 `weapon_type`, `favorite_rare`, `level1`/`level2` (16칸), `collection_skill_group_data`를 갖는다.

- [ ] **Step 1: 캡처 대상 유닛 목록을 정한다**

무기군 6종을 커버하는 유닛의 `resource_id`가 필요하다. 아래로 확인한다:

```bash
cd "C:/Users/fienn/Desktop/NikkeDeckBuilder/.claude/worktrees/deck-damage-breakdown"
python3 - <<'EOF'
import sys, json
from pathlib import Path
ROOT = Path("C:/Users/fienn/Desktop/NikkeDeckBuilder/.claude/worktrees/deck-damage-breakdown")
sys.path.insert(0, str(ROOT/"backend")); sys.path.insert(0, str(ROOT/"scripts"))
from app.user_roster import load_roster
from roster_fixture import real_roster
directory = {d["name_en"]: d for d in json.load(
    open(ROOT/"tools"/"collect-blablalink"/"nikke-directory.json", encoding="utf-8"))}
seen = {}
for s in real_roster():
    try:
        specs, _ = load_roster([s])
    except Exception:
        continue
    if not specs:
        continue
    seen.setdefault(specs[0].weapon_stats["weapon"], s.character_slug)
print(json.dumps(seen, indent=1))
EOF
```

Expected: `AR/SMG/SG/RL/SR/MG` 여섯 키가 모두 나온다. 슬러그를 `nikke-directory.json`의 `resource_id`로 옮긴다.

- [ ] **Step 2: `--collectibles` 모드를 추가한다**

`collect.js`의 `collectSubTypes`(약 275행) 바로 아래에 다음을 추가한다. 인터셉트 패턴은 그 함수와 동일하다.

```js
// 소장품(collectible) 레코드: 무기군마다 다른 스킬을 담고 있고, 그 스킬 효과는
// 엔진이 여태 못 보던 대미지 소스다(docs/engine-gaps.md #15). 레코드는 유닛
// 페이지를 여는 것만으로 CDN에서 흘러나오므로 stat 파일과 같은 방식으로 줍는다.
// 등급·무기군을 미리 가정하지 않고 보이는 것을 전부 id로 키잉해 담는다 - R 등급이
// 섞여 들어와도 그대로 저장한다.
const collectCollectibles = async (page, entries) => {
  const cdp = await page.context().newCDPSession(page)
  await cdp.send('Network.setCacheDisabled', { cacheDisabled: true })
  const out = {}
  const onResp = async (r) => {
    if (!r.url().includes('cdn') || !r.url().split('?')[0].endsWith('.json')) return
    let j
    try {
      j = await r.json()
    } catch {
      return
    }
    if (j && j.id && j.weapon_type && Array.isArray(j.collection_skill_group_data)) {
      out[String(j.id)] = j
    }
  }
  page.on('response', onResp)
  for (const e of entries) {
    log(`  collectibles: visiting ${e.name_en} (rid=${e.resource_id})`)
    await page
      .goto(`${SHIFTYPAD}${e.resource_id}`, { waitUntil: 'networkidle', timeout: 60000 })
      .catch(() => {})
    await page.waitForTimeout(2500)
  }
  page.off('response', onResp)
  const groups = new Set(Object.values(out).map((c) => c.weapon_type))
  for (const w of ['AR', 'SMG', 'SG', 'RL', 'SR', 'MG']) {
    if (!groups.has(w)) log(`  WARNING: no collectible captured for weapon group ${w}`)
  }
  log(`  captured ${Object.keys(out).length} collectible records: ${[...groups].join(',')}`)
  return out
}
```

플래그를 파싱부(약 47행, `TABLES_ONLY` 옆)에 추가한다:

```js
const COLLECTIBLES_ONLY = args.includes('--collectibles')
```

메인 흐름의 `if (TABLES_ONLY) { … }` 블록 **바로 아래**(약 404행)에 분기를 추가한다. `dir`은 이미 그 스코프에 있다(약 330행 `const dir = await collectDirectory(page)`) — 새로 읽지 않는다. `TABLES_ONLY`와 마찬가지로 **로그인 이전**이어야 한다(정적 게임 데이터라 계정이 필요 없다).

```js
  // Also account-free: collectible records are static game data.
  if (COLLECTIBLES_ONLY) {
    log('collecting collectible records…')
    const picks = COLLECTIBLE_SAMPLE_RIDS.map((rid) =>
      dir.find((d) => String(d.resource_id) === String(rid)),
    ).filter(Boolean)
    const collectibles = await collectCollectibles(page, picks)
    fs.writeFileSync('collectibles.json', `${JSON.stringify(collectibles, null, 2)}\n`)
    log(`wrote collectibles.json: ${Object.keys(collectibles).length} records`)
    await browser.close()
    return
  }
```

`COLLECTIBLE_SAMPLE_RIDS`는 Step 1에서 얻은 여섯 개의 `resource_id` 배열로, 파일 상단 상수부에 둔다. 헤더 주석(23행 부근)의 사용법에도 `--collectibles` 한 줄을 추가한다.

- [ ] **Step 3: 수집을 실행한다**

```bash
cd tools/collect-blablalink && node collect.js --collectibles
```

Expected: `collectibles.json`이 생기고, 로그에 캡처된 무기군이 나열된다.

- [ ] **Step 4: 커버리지를 확인하고, 부족하면 폴백한다**

여섯 무기군이 모두 잡혔으면 Step 5로 간다.

**폴백 (일부/전부 실패 시):** SPA가 요청하지 않는 리소스는 인터셉트로 절대 못 잡는다는 전례가 있다(`docs/insights.md`의 equipment/affinity). 못 잡은 무기군은 아래 확보된 값으로 손수 채운다. **SMG·RL은 아직 값이 없으므로 Fienn에게 최대단계 툴팁을 요청해야 한다** — 그때까지는 그 두 무기군을 `collectibles`에서 **비워 둔다**(해석기가 조용히 0을 반환하므로 안전하다).

| 무기군 | 스탯 | 사다리 (스킬레벨 1→4) | 배율 | 출처 |
|---|---|---|---|---|
| MG | 최대 장탄 수 | 4.74 / 6.32 / 7.91 / 9.5 | 아니오 | 커밋 테이블 (Flora 인게임 확인) |
| SR | 차지 대미지 | 4.74 / 6.31 / 7.89 / 9.47 | **예** | 에이드 5단계 + 헬름 애장품 |
| SG | 일반 공격 대미지 | 4.73 / 6.31 / 7.88 / 9.46 | **예** | 츠바이 애장품 (낮은 단계는 `최대/6×[3,4,5,6]`으로 유도) |
| AR | 코어 대미지 | 8.52 / 11.36 / 14.20 / 17.04 | 아니오 | 토브 애장품 (낮은 단계 유도) |

유도식은 헬름의 9.47에서 에이드의 6.31을 정확히 예측해 한 무기군에서 교차검증됐다. 다만 MG에서 낮은 단계가 0.01 어긋나므로(4.75 예측 vs 4.74 실제) **폴백 전용**이며, 수집 원본이 있으면 항상 그쪽을 쓴다.

- [ ] **Step 5: `tables.json`에 병합한다**

```bash
cd "C:/Users/fienn/Desktop/NikkeDeckBuilder/.claude/worktrees/deck-damage-breakdown"
python3 - <<'EOF'
import json
from pathlib import Path
ROOT = Path("C:/Users/fienn/Desktop/NikkeDeckBuilder/.claude/worktrees/deck-damage-breakdown")
tables_path = ROOT / "data" / "nikke-stat-tables" / "tables.json"
tables = json.loads(tables_path.read_text(encoding="utf-8"))
new = json.loads((ROOT / "tools" / "collect-blablalink" / "collectibles.json")
                 .read_text(encoding="utf-8"))
tables["collectibles"] = new
tables["sources"]["collectibles"] = "collect.js --collectibles (CDN interception)"
tables_path.write_text(json.dumps(tables, ensure_ascii=False, indent=1) + "\n",
                       encoding="utf-8")
print("weapon groups:", sorted({c["weapon_type"] for c in new.values()}))
EOF
```

Expected: 무기군 목록이 출력된다. `collectible_sample` 키는 그대로 남아 있어야 한다.

- [ ] **Step 6: 기존 테스트가 안 깨졌는지 확인한다**

```bash
cd backend && python3 -m pytest -q
```

Expected: `1468 passed, 3 skipped` (테이블에 키만 추가했으므로 변화 없음).

- [ ] **Step 7: 커밋**

```bash
git add tools/collect-blablalink/collect.js data/nikke-stat-tables/tables.json
git commit -m "Capture the collectible records the engine has never seen"
```

---

### Task 2: 소장품 효과 해석기

**Files:**
- Create: `backend/app/collectible_effects.py`
- Test: `backend/tests/test_collectible_effects.py`

**Interfaces:**
- Consumes: `tables.json["collectibles"]` (Task 1), `stat_assembly.load_stat_tables()`, `stat_assembly.FAVORITE_ITEM_TID_BASE`, `effects.Effect`
- Produces: `collectible_modifiers(tid: int, level: int, source_slug: str) -> tuple[dict[str, float], list[Effect]]`. 첫 원소는 `{weapon_stats 키: 곱할 배수}`, 둘째는 permanent self `Effect` 목록. tid가 0이거나 모르는 값이면 `({}, [])`.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/tests/test_collectible_effects.py`:

```python
"""소장품 해석기 - 단계에서 스킬레벨로, 스킬레벨에서 수치로.

수치의 근거는 Fienn의 인게임 확인이다: MG 소장품 최대단계가 최대 장탄 수 9.5%
(Flora, SSR 5단계에서도 동일)이고, SR 소장품 5단계가 차지 대미지 6.31% 배율
(에이드 사격장). docs/engine-gaps.md #15.
"""
import pytest

from app.collectible_effects import collectible_modifiers, skill_percents


MG_RECORD = {
    "id": 100202,
    "weapon_type": "MG",
    # 단계 0~15 -> 스킬레벨. 수치는 0/5/10/15단계에서만 오른다.
    "level1": [1, 1, 1, 1, 1, 2, 2, 2, 2, 2, 3, 3, 3, 3, 3, 4],
    "level2": [1, 1, 1, 1, 1, 2, 2, 2, 2, 2, 3, 3, 3, 3, 3, 4],
    "collection_skill_group_data": [
        {"group_id": 712401, "description_value_list": [
            {"description_value": ["4.74", "6.32", "7.91", "9.5"]},   # 최대 장탄 수
            {"description_value": ["30", "32", "35", "37"]},          # 방어력 (미매핑)
        ]},
        {"group_id": 712002, "description_value_list": [              # 둘 다 방어 스탯
            {"description_value": ["10", "12", "14", "17"]},
            {"description_value": ["12", "18", "24", "30"]},
        ]},
    ],
}


def test_level_five_reads_the_second_rung_not_the_fifth():
    """단계 -> 스킬레벨은 사다리를 한 번 거친다. 배열은 0-based(단계 0이 존재)라
    큐브의 1-based 인덱싱을 그대로 가져오면 한 칸씩 밀린다."""
    percents = skill_percents(MG_RECORD, item_level=5, is_favorite=False)
    assert percents == {("max_ammo_percent", "effect"): 6.32}


def test_level_zero_is_a_real_level_not_an_empty_slot():
    percents = skill_percents(MG_RECORD, item_level=0, is_favorite=False)
    assert percents == {("max_ammo_percent", "effect"): 4.74}


def test_a_favorite_item_reads_the_top_reachable_rung_whatever_its_own_level():
    """애장품은 SR 15단계에서만 승급할 수 있으므로 무기군 스킬은 항상 최대치다.
    자기 SSR 단계는 유닛 스킬 해금만 움직인다 - Flora가 SSR 5단계에서도 9.5%를
    유지하는 것이 실증이다."""
    percents = skill_percents(MG_RECORD, item_level=5, is_favorite=True)
    assert percents == {("max_ammo_percent", "effect"): 9.5}


def test_unknown_skill_group_is_skipped_not_guessed(caplog):
    record = dict(MG_RECORD, collection_skill_group_data=[
        {"group_id": 999999, "description_value_list": [
            {"description_value": ["1", "2", "3", "4"]}]},
    ])
    assert skill_percents(record, item_level=15, is_favorite=False) == {}
    assert "999999" in caplog.text


def test_no_collectible_equipped_contributes_nothing():
    assert collectible_modifiers(0, 0, "ade-agent-bunny") == ({}, [])
```

- [ ] **Step 2: 실패를 확인한다**

```bash
cd backend && python3 -m pytest tests/test_collectible_effects.py -q
```

Expected: FAIL — `ModuleNotFoundError: No module named 'app.collectible_effects'`

- [ ] **Step 3: 해석기를 구현한다**

`backend/app/collectible_effects.py`:

```python
"""The collectible (소장품) a unit has equipped, as damage-relevant modifiers.

A collectible's skill differs by WEAPON GROUP, and until 2026-07-27 nothing
read it: `stat_assembly` takes only the atk/hp curves, so the engine could not
tell a collectible was equipped at all. Ade: Agent Bunny's range test found the
gap - every one of seven readings sat a uniform 1.06x below the model, which
resolved to her SR-group collectible's "차지 대미지 6.31% 배율" (see
docs/engine-gaps.md #15).

Two things here are easy to get wrong, and both have already bitten this
codebase once:

- **The level arrays are 0-based.** A collectible has a level 0, so its arrays
  hold 16 entries for levels 0..15 and are indexed directly. The harmony cube's
  hold 15 for levels 1..15 and are indexed at `level - 1`. Copying
  `cube_effects` verbatim shifts every value by one rung.
- **A value ladder can run past its own reachable cap.** Taking `ladder[-1]`
  for a maxed item can therefore read a rung the item can never reach (this is
  what made an earlier session read the cube table as discontinuous). The top
  is `levelN[-1]` used as a skill level, never the ladder's last element.

A FAVORITE ITEM (애장품, tid >= FAVORITE_ITEM_TID_BASE) always sits at the top
rung regardless of its own level, because promotion REQUIRES the SR collectible
at level 15; the favorite item's own level gates the unit's skill unlocks
instead. Fienn verified this by promoting Flora, who reports the MG ladder's
top 9.5% while sitting at SSR level 5. `stat_assembly.collectible_atk` had
already inferred the same rule from measurement; this is why it holds.
"""
import logging
from typing import Any

from app.effects import Effect
from app.stat_assembly import FAVORITE_ITEM_TID_BASE, load_stat_tables

logger = logging.getLogger(__name__)

# A skill group's `group_id` -> what each of its value slots means, positionally
# (`description_value_01`, `description_value_02`, ...). `None` marks a slot the
# engine has no consumer for - defensive stats (방어력, 엄폐물 최대 체력,
# 받는 대미지 감소) are deliberately unmapped, the same rule cube_effects uses.
#
# The second element of each pair says WHERE the value lands:
#   "effect" - a permanent self Effect, value/100, like any other buff
#   "weapon" - a 배율: it scales the WEAPON's own base stat rather than adding
#              to a buff bucket. The in-game tooltip defines 배율 as "기본 스탯
#              값에 스킬 계수의 비율만큼 계산되어 더해짐", so Ade's charge damage
#              6.31% takes her rocket... her SR's 250% full charge to 265.775%,
#              NOT to 256.31%.
#
# Kept as an explicit table rather than parsed out of the record's description
# text: the description is display markup, and each group only needs deciding
# once. An unmapped group_id is logged and skipped, never guessed.
COLLECTIBLE_SKILL_STATS: dict[int, list[tuple[str, str] | None]] = {
    712401: [("max_ammo_percent", "effect"), None],  # 최대 장탄 수 / 방어력 (MG)
    712002: [None, None],                            # 받는 대미지 / 엄폐물 체력 (MG)
}


def skill_percents(record: dict[str, Any], item_level: int,
                   is_favorite: bool) -> dict[tuple[str, str], float]:
    """`(engine stat, placement) -> percent` for one collectible at one level.

    Slot position is a convention, not a key: the Nth entry of
    `collection_skill_group_data` is driven by the Nth `levelN` array. The data
    carries no explicit slot id (same as the harmony cube - see
    docs/insights.md).
    """
    percents: dict[tuple[str, str], float] = {}
    for slot, group in enumerate(record["collection_skill_group_data"], start=1):
        levels = record.get(f"level{slot}")
        if not levels:
            continue
        skill_level = levels[-1] if is_favorite else levels[min(item_level, len(levels) - 1)]
        if skill_level <= 0:
            continue
        mapping = COLLECTIBLE_SKILL_STATS.get(group["group_id"])
        if mapping is None:
            logger.warning("unknown collectible skill group %r - skipped", group["group_id"])
            continue
        for index, target in enumerate(mapping):
            if target is None:
                continue
            ladder = group["description_value_list"][index]["description_value"]
            percents[target] = float(ladder[skill_level - 1])
    return percents


def collectible_modifiers(tid: int, level: int, source_slug: str
                          ) -> tuple[dict[str, float], list[Effect]]:
    """`(weapon-stat multipliers, permanent self effects)` for one unit.

    An empty slot, or a tid the committed table does not know, contributes
    nothing - a roster collected before the field existed must not silently
    change anyone's damage.
    """
    if not tid:
        return {}, []
    record = load_stat_tables().get("collectibles", {}).get(str(tid))
    if record is None:
        logger.warning("no collectible record for tid %r - contributing nothing", tid)
        return {}, []
    weapon: dict[str, float] = {}
    effects: list[Effect] = []
    for (stat, placement), percent in skill_percents(
        record, level, tid >= FAVORITE_ITEM_TID_BASE
    ).items():
        if placement == "weapon":
            weapon[stat] = weapon.get(stat, 1.0) * (1 + percent / 100)
        else:
            effects.append(Effect(stat, percent / 100, "self", None, source_slug))
    return weapon, effects
```

- [ ] **Step 4: 테스트 통과를 확인한다**

```bash
cd backend && python3 -m pytest tests/test_collectible_effects.py -q
```

Expected: `5 passed`

- [ ] **Step 5: 전체 스위트를 돌린다**

```bash
cd backend && python3 -m pytest -q
```

Expected: `1473 passed, 3 skipped` (신규 5건)

- [ ] **Step 6: 커밋**

```bash
git add backend/app/collectible_effects.py backend/tests/test_collectible_effects.py
git commit -m "Read a collectible's weapon-group skill off the committed table"
```

---

### Task 3: 유닛별 소장품 신원을 엔진까지 실어 나르기

**Files:**
- Modify: `backend/app/models.py:23-37`
- Modify: `backend/app/roster.py:43-52`
- Modify: `backend/app/user_roster.py:85-97`
- Modify: `backend/app/roster_assembly.py:113-131`
- Test: `backend/tests/test_collectible_effects.py` (추가)

**Interfaces:**
- Consumes: Task 2의 `collectible_modifiers`
- Produces: `UserNikkeState.collectible_tid: int` / `.collectible_level: int` (기본 0), `NikkeSpec.collectible_tid` / `.collectible_level` (기본 0), `roster_assembly.build_unit`이 내보내는 `{"collectible": {"tid": int, "level": int}}`

이 태스크는 **동작을 바꾸지 않는다.** 값이 흐르기만 하고 소비는 Task 4에서 한다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/tests/test_collectible_effects.py` 끝에 추가:

```python
def test_the_spec_carries_the_collectible_identity_from_the_state():
    """소장품은 유닛별 투자다 - 큐브처럼 전역 가정으로 뭉갤 수 없다.
    에이드가 5단계인 것이 반례고, 그 5단계가 사격장 실측의 근거다."""
    from app.models import UserNikkeState
    from app.user_roster import load_roster

    state = UserNikkeState.model_validate({
        "character_slug": "ade-agent-bunny", "level": 200,
        "hp": 1_000_000.0, "atk": 305_667.0, "def_": 3_000.0,
        "skill_levels": {"skill1": 10, "skill2": 7, "burst": 10},
        "collectible_tid": 100202, "collectible_level": 5,
    })
    specs, excluded = load_roster([state])
    assert not excluded
    assert specs[0].collectible_tid == 100202
    assert specs[0].collectible_level == 5


def test_a_roster_without_the_field_defaults_to_no_collectible():
    """필드가 없던 시절의 roster.json을 읽어도 아무도 안 변한다."""
    from app.models import UserNikkeState

    state = UserNikkeState.model_validate({
        "character_slug": "ade-agent-bunny", "level": 200,
        "hp": 1_000_000.0, "atk": 305_667.0, "def_": 3_000.0,
        "skill_levels": {"skill1": 10, "skill2": 7, "burst": 10},
    })
    assert state.collectible_tid == 0
    assert state.collectible_level == 0
```

- [ ] **Step 2: 실패를 확인한다**

```bash
cd backend && python3 -m pytest tests/test_collectible_effects.py -q -k collectible_identity
```

Expected: FAIL — `AttributeError: 'NikkeSpec' object has no attribute 'collectible_tid'`

- [ ] **Step 3: `UserNikkeState`에 필드를 추가한다**

`backend/app/models.py`, `overload_options` 줄 바로 아래:

```python
    # The equipped collectible (소장품). Named for what it is rather than for
    # blablalink's `favorite_item_*`, which carries ordinary R/SR collectibles
    # too - the rarity is read off the tid, not the field name. Its weapon-group
    # skill is a real damage source; see collectible_effects.
    collectible_tid: int = Field(default=0, ge=0)
    collectible_level: int = Field(default=0, ge=0)
```

- [ ] **Step 4: `NikkeSpec`에 필드를 추가한다**

`backend/app/roster.py`의 `NikkeSpec`, `overload_options` 줄 아래:

```python
    collectible_tid: int = 0
    collectible_level: int = 0
```

- [ ] **Step 5: `user_roster`가 값을 넘기게 한다**

`backend/app/user_roster.py`의 `NikkeSpec(...)` 생성부, `weapon_stats=weapon_stats,` 아래:

```python
        collectible_tid=state.collectible_tid,
        collectible_level=state.collectible_level,
```

- [ ] **Step 6: 동기화 경로가 값을 내보내게 한다**

`backend/app/roster_assembly.py`의 `build_unit` 반환 dict, `"favorite_item": ...` 줄 아래:

```python
        # The item's flat ATK/HP is already folded into raid400 above; this is
        # its SKILL, which is a separate damage source the engine reads per unit
        # (collectible_effects). `favorite_item` above stays - it answers a
        # different question, namely which skill encoding to use.
        "collectible": {
            "tid": inp["favorite_item_tid"],
            "level": inp["favorite_item_lv"],
        },
```

- [ ] **Step 7: 테스트 통과를 확인한다**

```bash
cd backend && python3 -m pytest -q
```

Expected: `1475 passed, 3 skipped` (신규 2건, 기존 전부 유지 — 동작 변화 없음)

- [ ] **Step 8: 커밋**

```bash
git add backend/app/models.py backend/app/roster.py backend/app/user_roster.py \
        backend/app/roster_assembly.py backend/tests/test_collectible_effects.py
git commit -m "Carry the equipped collectible through to the spec"
```

---

### Task 4: 효과를 적용하고 에이드의 실측에 맞춘다

**Files:**
- Modify: `backend/app/user_roster.py:85-97`
- Modify: `backend/app/roster.py:63-67`
- Modify: `backend/tests/test_damage_formula.py` (에이드 테스트 뒤집기)
- Test: `backend/tests/test_collectible_effects.py` (추가)

**Interfaces:**
- Consumes: Task 2의 `collectible_modifiers`, Task 3의 `NikkeSpec.collectible_tid`/`.collectible_level`
- Produces: 없음 (종단 동작)

- [ ] **Step 1: 실패하는 수용 테스트를 쓴다**

`backend/tests/test_collectible_effects.py` 끝에 추가. **SR 레코드의 실제 tid는 Task 1이 수집한 테이블에서 찾는다** — 하드코딩하지 않는다.

```python
def _tid_for(weapon_type, rare):
    """The committed table's collectible for one weapon group and rarity."""
    from app.stat_assembly import load_stat_tables
    for tid, record in load_stat_tables().get("collectibles", {}).items():
        if record["weapon_type"] == weapon_type and record["favorite_rare"] == rare:
            return int(tid)
    pytest.skip(f"no {rare} collectible collected for {weapon_type}")


def test_ades_charge_damage_matches_her_range_test():
    """사격장 실측: SR 소장품 5단계가 차지 대미지 6.31% 배율을 준다. 「배율」은
    무기 기본 250%에 비례하므로 265.775%가 되어야 한다 - 256.31%가 아니다."""
    from app.models import UserNikkeState
    from app.user_roster import load_roster

    tid = _tid_for("SR", "SR")
    state = UserNikkeState.model_validate({
        "character_slug": "ade-agent-bunny", "level": 200,
        "hp": 1_000_000.0, "atk": 305_667.0, "def_": 3_000.0,
        "skill_levels": {"skill1": 10, "skill2": 7, "burst": 10},
        "collectible_tid": tid, "collectible_level": 5,
    })
    specs, _ = load_roster([state])
    assert specs[0].weapon_stats["charge_damage_percent"] == pytest.approx(265.775, abs=0.01)


def test_a_maxed_mg_collectible_grants_max_ammo_as_a_plain_effect():
    """평범한 %는 무기 스탯이 아니라 버프로 간다. Flora의 MG 최대치 9.5%."""
    from app.collectible_effects import collectible_modifiers

    tid = _tid_for("MG", "SR")
    weapon, effects = collectible_modifiers(tid, 15, "flora")
    assert weapon == {}
    assert [(e.stat, round(e.value, 5)) for e in effects] == [("max_ammo_percent", 0.095)]
```

- [ ] **Step 2: 실패를 확인한다**

```bash
cd backend && python3 -m pytest tests/test_collectible_effects.py -q -k "range_test or max_ammo"
```

Expected: FAIL — `charge_damage_percent`가 250.0으로 나온다.

- [ ] **Step 3: 「배율」을 무기 스탯에 적용한다**

`backend/app/user_roster.py`. 임포트에 추가:

```python
from app.collectible_effects import collectible_modifiers
```

`NikkeSpec(...)` 생성 **직전**에 삽입한다. 위치가 중요하다 — `get_weapon_profile_override`가 무기 프로필을 통째로 갈아끼울 수 있으므로 **그 뒤**에 곱해야 변형된 무기에도 붙는다.

```python
    # A collectible's 배율 scales the WEAPON's own base stat, so it lands here
    # rather than in the buff registry - and after any mode override, so a unit
    # whose weapon profile swaps mid-kit still carries it.
    weapon_multipliers, _ = collectible_modifiers(
        state.collectible_tid, state.collectible_level, slug)
    if weapon_multipliers:
        weapon_stats = dict(weapon_stats)
        for stat, factor in weapon_multipliers.items():
            weapon_stats[stat] = weapon_stats[stat] * factor
```

- [ ] **Step 4: 평범한 %를 permanent effect로 붙인다**

`backend/app/roster.py`. 임포트에 추가:

```python
from app.collectible_effects import collectible_modifiers
```

`_passive_effects`를 교체한다:

```python
def _passive_effects(spec: NikkeSpec):
    """Overload, the harmony cube every unit is assumed to wear, and the
    collectible this unit actually has equipped. The collectible's 배율 stats
    are NOT here - they scale weapon stats and are applied in user_roster."""
    _, collectible = collectible_modifiers(
        spec.collectible_tid, spec.collectible_level, spec.slug)
    return (
        overload_options_to_effects(spec.overload_options, spec.slug)
        + assumed_cube_effects(spec.slug)
        + collectible
    )
```

- [ ] **Step 5: 테스트 통과를 확인한다**

```bash
cd backend && python3 -m pytest tests/test_collectible_effects.py -q
```

Expected: `9 passed` (SMG/RL 미수집이면 일부 skip)

- [ ] **Step 6: 에이드의 포뮬러 테스트를 뒤집는다**

`backend/tests/test_damage_formula.py`의 `test_without_the_collectible_every_reading_is_uniformly_six_percent_low`는 이제 **엔진이 아니라 반사실**을 설명한다. 독스트링을 고쳐 사실관계를 맞춘다:

```python
def test_without_the_collectible_every_reading_is_uniformly_six_percent_low():
    """소장품 항을 빼면 어떻게 보이는지 - 이 결함이 왜 안 보였는지의 기록.

    2026-07-27 이전의 엔진이 계산하던 값이다. 일곱 개가 전부 같은 1.0603으로
    낮으므로 잘못 박힌 무기 수치나 빠진 버프와 구별이 안 된다. major 버킷에
    숨을 수도 없고(사거리 in/out이 어긋난다), ATK 쪽(Agent's Gaze의 flat_atk이
    스파이렌즈 행에만 있다)이나 damage-up(pierce_damage_up이 같은 버킷)도
    아니다 - 셋 다 실제로 넣어보고 기각했다.

    지금은 `collectible_effects`가 이 항을 공급한다. 이 테스트는 그것을 빼면
    무슨 일이 벌어지는지를 고정해, 배선이 조용히 끊기면 짝인
    `test_ade_range_readings_are_reproduced_exactly`와 함께 신호를 준다.
    """
```

- [ ] **Step 7: 전체 스위트를 돌린다**

```bash
cd backend && python3 -m pytest -q
```

Expected: **전부 통과한다.** 기존 테스트는 모두 자기 `UserNikkeState`를 직접 만들고
(`real_roster()`를 쓰는 테스트가 하나도 없다) 새 필드는 기본값 0이므로,
`collectible_modifiers`가 `({}, [])`를 반환해 **기능이 완전히 무효화**된다. 즉 이
태스크는 소장품을 실제로 실은 신규 테스트만 움직인다.

**뭔가 깨지면 그것은 재기준화 대상이 아니라 버그다** — 무효화돼야 할 경로가
무효화되지 않았다는 뜻이므로, 멈추고 원인을 찾는다.

- [ ] **Step 8: 커밋**

```bash
git add backend/app/user_roster.py backend/app/roster.py \
        backend/tests/test_collectible_effects.py backend/tests/test_damage_formula.py
git commit -m "Let a collectible's skill reach the damage it was always dealing"
```

---

### Task 5: 프론트엔드 통과

**Files:**
- Modify: `frontend/src/lib/rosterImport.ts:15-28, 60-78`
- Modify: `frontend/src/types/nikkeDraft.ts:18-41, 155-166`
- Test: `frontend/src/lib/rosterImport.test.ts`

**Interfaces:**
- Consumes: Task 3의 roster.json `collectible` 필드
- Produces: `UserNikkeState`에 실린 `collectible_tid`/`collectible_level`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`frontend/src/lib/rosterImport.test.ts`에 추가:

```ts
it('carries the equipped collectible through to the draft', () => {
  const { drafts } = parseRosterJson({
    units: [{
      resource_id: 531,
      name_en: 'Ade: Agent Bunny',
      raid400: { hp: 1000000, atk: 305667, def: 0 },
      skill_levels: { skill1: 10, skill2: 7, burst: 10 },
      collectible: { tid: 100202, level: 5 },
    }],
  })
  expect(drafts[0].collectible_tid).toBe(100202)
  expect(drafts[0].collectible_level).toBe(5)
})

it('treats a roster without the collectible field as no collectible', () => {
  const { drafts } = parseRosterJson({
    units: [{
      resource_id: 531,
      name_en: 'Ade: Agent Bunny',
      raid400: { hp: 1000000, atk: 305667, def: 0 },
      skill_levels: { skill1: 10, skill2: 7, burst: 10 },
    }],
  })
  expect(drafts[0].collectible_tid).toBeUndefined()
})
```

- [ ] **Step 2: 실패를 확인한다**

```bash
cd frontend && npm test -- rosterImport
```

Expected: FAIL — `collectible_tid` is undefined in the first test.

- [ ] **Step 3: 타입과 파싱을 고친다**

`frontend/src/lib/rosterImport.ts`의 `RosterUnit`에 추가:

```ts
  // The equipped collectible (소장품). Its weapon-group skill is a damage
  // source the backend reads per unit; absent on rosters predating the field.
  collectible?: { tid: number; level: number }
```

같은 파일의 draft push, `favorite_item: u.favorite_item,` 아래:

```ts
      collectible_tid: u.collectible?.tid,
      collectible_level: u.collectible?.level,
```

`frontend/src/types/nikkeDraft.ts`의 `NikkeDraft`, `favorite_item?: boolean` 아래:

```ts
  collectible_tid?: number
  collectible_level?: number
```

같은 파일의 `validateDraft`가 만드는 `value` 객체, `overload_options: overloadOptions,` 아래:

```ts
    ...(draft.collectible_tid != null && {
      collectible_tid: draft.collectible_tid,
      collectible_level: draft.collectible_level ?? 0,
    }),
```

프론트의 `UserNikkeState` 타입 정의(같은 파일 또는 `types/`)에도 두 필드를 선택값으로 추가한다.

- [ ] **Step 4: 테스트 통과를 확인한다**

```bash
cd frontend && npm test -- rosterImport
```

Expected: PASS

- [ ] **Step 5: 프론트 전체 스위트**

```bash
cd frontend && npm test
```

Expected: 기존 통과 수 + 신규 2건

- [ ] **Step 6: 커밋**

```bash
git add frontend/src/lib/rosterImport.ts frontend/src/types/nikkeDraft.ts \
        frontend/src/lib/rosterImport.test.ts
git commit -m "Pass the collectible through the roster import"
```

---

### Task 6: 재기준화 · 재측정 · 문서

**Files:**
- Modify: `backend/tests/test_roster.py` (골든 핀)
- Modify: `docs/engine-gaps.md` (#15을 해소로)
- Modify: `docs/decisions.md`, `docs/roadmap.md`

**Interfaces:**
- Consumes: Task 1–5 전부
- Produces: 없음 (문서/기준선)

- [ ] **Step 1: 캘리브레이션이 어느 방향으로 움직였는지 먼저 본다**

**재기준화보다 이것이 먼저다.** 골든 핀을 먼저 고치면 의도한 변화인지 확인할 기회를 잃는다.

```bash
cd "C:/Users/fienn/Desktop/NikkeDeckBuilder/.claude/worktrees/deck-damage-breakdown"
python3 scripts/measure_record_calibration.py
```

Expected: 합계가 **0.914x보다 올라간다**. 이 갭은 엔진을 낮추던 것이었으므로 오르는 것이 이 작업의 목표 신호다. **내려가면 배선이 거꾸로 붙은 것이니 멈추고 원인을 찾는다.**

측정 전후 값을 기록한다.

- [ ] **Step 2: 로스터가 소장품 없이 측정되고 있음을 확인한다**

현재 `tools/collect-blablalink/roster-drafts.json`에는 소장품 필드가 없다. 즉 Step 1의 상승분은 **아직 0이어야 한다.**

```bash
python3 -c "
import json
d=json.load(open('tools/collect-blablalink/roster-drafts.json',encoding='utf-8'))
print('units with a collectible field:', sum(1 for u in d if 'collectible_tid' in u))
"
```

Expected: `0`. 그렇다면 Step 1의 값은 변하지 않았어야 하며, 이는 **회귀가 없다는 확인**이다. 실제 상승을 보려면 Fienn의 재동기화가 필요하다 — 그 사실을 결과에 명시한다.

- [ ] **Step 3: 깨진 테스트가 없는지 확인한다 (재기준화는 예상하지 않는다)**

```bash
cd backend && python3 -m pytest -q 2>&1 | tail -30
```

Expected: 전부 통과. 로스터가 아직 소장품을 안 실어서 기능이 무효화돼 있기 때문이다
(Step 2에서 확인한다). **깨진 것이 있으면 재기준화하지 말고 버그로 다룬다** — 무효화
경로가 새는 것이다.

Fienn이 재동기화한 뒤에는 실제로 수치가 움직이므로 그때 골든 핀 재기준화가 필요할 수
있다. 그 시점에는 각 변경을 **왜 그 수치가 바뀌었는지 한 줄로 설명할 수 있을 때만** 갱신한다.

- [ ] **Step 4: 전체 스위트가 깨끗한지 확인한다**

```bash
cd backend && python3 -m pytest -q
cd ../frontend && npm test
```

Expected: 백엔드 1475 이상 passed / 3 skipped, 프론트 전량 통과.

- [ ] **Step 5: 문서를 갱신한다**

- `docs/engine-gaps.md`: #15를 **✅ 해소**로 바꾸고, 남은 것(SMG·RL 미수집, R 등급 사다리)을 명시한다.
- `docs/decisions.md`: 「배율」의 의미와 애장품=최대치 규칙(승급 조건에서 따라 나온다는 것), 그리고 이 값이 유닛별 투자라 큐브처럼 전역 가정할 수 없다는 결정을 ADR로 남긴다.
- `docs/roadmap.md`: 캘리브레이션 현황을 갱신하고, **재동기화가 필요하다**는 것을 To-Do로 남긴다.

- [ ] **Step 6: 커밋**

```bash
git add backend/tests docs
git commit -m "Rebaseline for the collectible bonus and record what it settles"
```

---

## Self-Review

**1. 스펙 커버리지**

| 스펙 항목 | 태스크 |
|---|---|
| 데이터 수집 (`--collectibles`, id 키잉, 커버리지 경고, 폴백) | Task 1 |
| `collectible_sample` 불가침 + `collectibles` 추가 | Task 1 Step 5, Global Constraints |
| 유닛별 배선 (roster_assembly / UserNikkeState / 프론트) | Task 3, Task 5 |
| `collectible_effects.py` (group_id 키잉, 위치 규약, 0-based, SSR=최대치) | Task 2 |
| 배율 → weapon_stats / 평범한 % → Effect | Task 4 |
| DPS 무관 스탯 미매핑 | Task 2 (`COLLECTIBLE_SKILL_STATS`의 `None`) |
| 수용 기준 (에이드 7개) | Task 4 Step 1·6 |
| 헬름·Flora 회귀 | Task 2 (`is_favorite` 테스트), Task 4 Step 1 |
| 골든 재기준화 + 캘리브레이션 재측정 | Task 6 |

**2. 플레이스홀더 스캔** — 코드 블록은 전부 실제 내용이다. Task 1의 `COLLECTIBLE_SAMPLE_RIDS`만 Step 1의 출력에 의존하는데, 그 값을 구하는 명령을 그 자리에 넣어 두었다. SMG·RL 사다리는 미상이며, 이는 플레이스홀더가 아니라 **명시적으로 범위에 남긴 데이터 공백**이다(해석기가 조용히 0을 반환하므로 안전하다).

**3. 타입 일관성** — `collectible_modifiers(tid, level, source_slug) -> (dict[str, float], list[Effect])`가 Task 2에서 정의되고 Task 4의 두 호출부에서 같은 시그니처로 쓰인다. `skill_percents(record, item_level, is_favorite) -> dict[tuple[str, str], float]`의 키는 `(stat, placement)`이고 `placement`는 `"weapon" | "effect"` 두 값뿐이며 Task 2 안에서만 소비된다. 필드명 `collectible_tid`/`collectible_level`은 models · NikkeSpec · 프론트 draft에서 동일하고, roster.json 안에서만 중첩 형태(`{"tid", "level"}`)를 쓰며 그 변환은 Task 3 Step 6과 Task 5 Step 3 두 곳에 각각 명시돼 있다.
