# 무기 + 기본스킬 ShiftyPad 전환 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 신규 니케가 ShiftyPad에서 무기+기본스킬을 받아 dotgg 무기 스탯 수동 입력 없이 온보딩되게 한다.

**Architecture:** ShiftyPad 캐릭터 상세 페이로드를 **dotgg 모양의 파일로 정규화**한다. 그러면 하위 파싱(스킬 슬롯·무기 스탯·메타)이 전부 기존 코드로 재사용되고, `source: "shiftypad"` manifest는 dotgg 유닛과 동일한 모양이 된다. 수집(JS)은 원시 페이로드만 덤프하고, 정규화(Python 순수 함수)는 커밋된 픽스처로 검증하며, 패리티 하니스가 기존 유닛의 dotgg 정답지와 대조해 파서를 증명한다.

**Tech Stack:** Node 24 + `playwright-core`(collect.js, 신규 의존성 없음), Python 3 + pytest.

## Global Constraints

- **범위는 go-forward.** 신규 유닛만 ShiftyPad로. 기존 71유닛의 데이터·로딩·시뮬 결과는 **불변**이어야 한다(백엔드 전체 스위트가 계속 초록).
- **인터프리터는 `python3`.** 이 머신의 맨 `python`은 pytest 없는 다른 설치본이다.
- **정규화기는 순수 함수**(네트워크·파일시스템 부작용 없음). 수집(JS)만 네트워크를 만진다.
- **고정소수점 관례(÷100):** `damage`/`full_charge_damage`는 퍼센트 문자열(`557`→`"5.57%"`, `10000`→`"100%"`), `reload_time`/`charge_time`는 초(÷100), `skill_cooltime`는 초(÷100). `max_ammo`는 정수 그대로.
- **스킬 전치:** ShiftyPad `description_value_list[슬롯].description_value[레벨]` → dotgg `skills[i].levels[레벨][description_value_NN]`. 스킬 순서 skill1→skill2→ulti = dotgg `skills[0..2]`.
- **커밋 픽스처는 `backend/tests/fixtures/shiftypad/`.** `data/`는 gitignore라 테스트 픽스처를 둘 수 없다. 런타임 데이터만 `data/shiftypad/`(gitignore)로 간다.
- **dollskills/시그니처 무기는 범위 밖**(ShiftyPad에 없음). 기본 무기+기본 스킬만 담당.

**베이스라인(구현 시작 전 측정):** `cd backend && python3 -m pytest -q`와 `cd tools/collect-blablalink && node --test`의 현재 통과 수를 각 태스크 시작 전 기록하고, 끝난 뒤 증가분이 그 태스크가 추가한 테스트 수와 일치하는지 확인한다. 계획에 절대 숫자를 박지 않는 이유는 병렬 세션이 테스트를 추가 중이기 때문이다.

**데이터 동기화 선결:** `data/`는 gitignore이므로 워크트리에서 `python3 scripts/sync_worktree_data.py`가 이미 돌아 dotgg 데이터가 존재해야 한다(패리티 하니스가 `data/dotgg/`를 정답지로 읽는다).

---

## File Structure

| 파일 | 책임 |
|---|---|
| `tools/collect-blablalink/collect.js` (수정) | `--nikke <rid|name>` 유닛 상세 모드: 디렉토리 항목 + 상세 페이로드를 원시 번들로 덤프 |
| `backend/app/shiftypad_normalize.py` (신규) | 원시 ShiftyPad 번들 → dotgg 모양 dict (순수 함수) |
| `backend/tests/test_shiftypad_normalize.py` (신규) | 정규화기 단위 테스트 (커밋 픽스처) |
| `backend/tests/test_shiftypad_parity.py` (신규) | 패리티 하니스: 정규화 출력 == `data/dotgg/` 정답지 |
| `backend/tests/fixtures/shiftypad/*.json` (신규) | 선별 유닛의 원시 ShiftyPad 번들 (커밋) |
| `backend/app/skill_values.py` (수정) | `load_character_data`·`assemble_skill_values`에 `shiftypad` 소스 |
| `backend/app/user_roster.py` (수정) | 무기·메타 읽기를 소스별로 분기 |
| `backend/tests/test_user_roster_shiftypad.py` (신규) | shiftypad 소스 유닛의 로더 통합 |
| `docs/new-nikke-detection.md` (수정) | 온보딩 절차에서 무기 스텁 단계를 ShiftyPad 수집으로 교체 |

---

## Task 1: 수집 — `collect.js --nikke` 유닛 상세 모드

한 유닛의 원시 ShiftyPad 번들(디렉토리 항목 + 캐릭터 상세 페이로드)을 헤드리스로 덤프하고, 후속 태스크의 픽스처가 될 선별 유닛들을 수집·커밋한다.

**Files:**
- Modify: `tools/collect-blablalink/collect.js` (인자 파싱, `main()` 분기)
- Create: `backend/tests/fixtures/shiftypad/*.json` (수집 결과 커밋)

**Interfaces:**
- Produces: `data/shiftypad/raw/<resource_id>.json` 형태의 원시 번들
  `{ "directory": <디렉토리 항목 객체>, "detail": <캐릭터 상세 페이로드> }`
  - 디렉토리 항목: `shot_id.weapon_type`, `element_id.element.element`, `use_burst_skill`, `resource_id`, `name_localkey` 등을 포함(디렉토리 원본 항목 그대로).
  - 상세 페이로드: `shot_detail`, `skill1_detail`, `skill2_detail`, `ulti_skill_detail`, `resource_id`를 포함.

- [ ] **Step 1: 인자 파싱 추가**

`tools/collect-blablalink/collect.js`의 `const HEADLESS = args.includes('--headless')` 아래에 추가:

```js
const NIKKE = args.includes('--nikke') ? args[args.indexOf('--nikke') + 1] : null
```

`--nikke`는 계정이 필요 없으므로(공개 데이터) 헤드리스와 함께 쓸 수 있어야 한다. `main()`의 기존 헤드리스 가드를 `--nikke`도 허용하도록 바꾼다 — `const main` 첫 줄의:

```js
  if (HEADLESS && !DIRECTORY_ONLY) {
    throw new Error('--headless only applies to --directory; the other modes need your logged-in session')
  }
```

를 다음으로 교체:

```js
  if (HEADLESS && !DIRECTORY_ONLY && !NIKKE) {
    throw new Error('--headless applies to --directory or --nikke; other modes need your logged-in session')
  }
```

- [ ] **Step 2: 상세 페이로드 캡처 헬퍼 추가**

`collectDirectory` 정의 아래에 추가한다. 캐릭터 상세 페이로드는 `resource_id`가 일치하고 `shot_detail`을 가진 JSON 응답이다(탐지 작업에서 확인).

```js
// The character detail payload is the JSON response for this resource_id that
// carries shot_detail (weapon) and skill{1,2}/ulti details. It is public data,
// so this needs no login - same as the directory dump.
const collectNikkeDetail = async (page, resourceId) => {
  let hit = null
  const onResp = async (r) => {
    if (hit) return
    const u = r.url()
    if (!u.includes('blablalink.com') || !u.split('?')[0].endsWith('.json')) return
    try {
      const j = await r.json()
      if (j && !Array.isArray(j) && String(j.resource_id) === String(resourceId) && j.shot_detail) hit = j
    } catch {}
  }
  page.on('response', onResp)
  await page
    .goto(`${SHIFTYPAD}${resourceId}`, { waitUntil: 'networkidle', timeout: 60000 })
    .catch(() => {})
  for (let i = 0; i < 30 && !hit; i++) await page.waitForTimeout(300)
  page.off('response', onResp)
  return hit
}
```

- [ ] **Step 3: `main()`에 `--nikke` 분기 추가**

`main()`의 `if (DIRECTORY_ONLY) { … }` 블록 **바로 다음**에 추가한다. `dir`은 그 앞에서 이미 수집돼 있다(`collectDirectory`).

```js
  if (NIKKE) {
    const entry = /^\d+$/.test(NIKKE)
      ? dir.find((d) => String(d.resource_id) === NIKKE)
      : dir.find((d) => nameOf(d) === NIKKE)
    if (!entry) throw new Error(`no directory entry for --nikke ${NIKKE}`)
    const detail = await collectNikkeDetail(page, entry.resource_id)
    if (!detail) throw new Error(`no detail payload for resource_id ${entry.resource_id}`)
    const out = OUT !== DEFAULT_OUT ? OUT : `../../data/shiftypad/raw/${entry.resource_id}.json`
    fs.mkdirSync(require('path').dirname(out), { recursive: true })
    fs.writeFileSync(out, `${JSON.stringify({ directory: entry, detail }, null, 2)}\n`)
    log(`wrote ${out}: ${nameOf(entry)} (rid=${entry.resource_id})`)
    await browser.close()
    return
  }
```

- [ ] **Step 4: 사용법 주석 추가**

`collect.js` 상단 주석의 `--details` 항목 아래에 추가:

```
//   --nikke <rid|name>  dump one unit's raw ShiftyPad bundle (directory entry +
//               character detail payload) to data/shiftypad/raw/<rid>.json.
//               Public data, so combine with --headless for an unattended run.
```

- [ ] **Step 5: 실제 수집으로 검증 (Rapi)**

Run: `cd tools/collect-blablalink && node collect.js --nikke 16 --headless`
Expected: `wrote ../../data/shiftypad/raw/16.json: Rapi: Red Hood (rid=16)`

번들 구조 확인:
```bash
python3 -c "
import json
b=json.load(open('data/shiftypad/raw/16.json',encoding='utf-8'))
print('keys:', sorted(b))
print('weapon_type:', b['directory']['shot_id']['weapon_type'])
print('shot_detail.damage:', b['detail']['shot_detail']['damage'])
print('has skills:', all(k in b['detail'] for k in ('skill1_detail','skill2_detail','ulti_skill_detail')))
"
```
Expected: `keys: ['detail', 'directory']`, `weapon_type: MG`, `shot_detail.damage: 557`, `has skills: True`.

- [ ] **Step 6: 선별 픽스처 수집·커밋**

파서를 구조적으로 덮는 6개 무기타입 대표 + 스킬 구조 다양성 유닛을 수집한다. 각각 `--nikke <rid> --headless`로 받은 뒤 `backend/tests/fixtures/shiftypad/`로 복사한다(파일명은 우리 slug):

| rid | slug | 무기 |
|---|---|---|
| 15 | anis-sparkling-summer | SG |
| 16 | rapi-red-hood | MG |
| 17 | anis-star | RL |
| 32 | miranda | SMG |
| 43 | d-killer-wife | SR |
| 150 | julia | AR |

```bash
cd tools/collect-blablalink
for rid in 15 16 17 32 43 150; do node collect.js --nikke $rid --headless; done
cd ../..
mkdir -p backend/tests/fixtures/shiftypad
cp data/shiftypad/raw/15.json  backend/tests/fixtures/shiftypad/anis-sparkling-summer.json
cp data/shiftypad/raw/16.json  backend/tests/fixtures/shiftypad/rapi-red-hood.json
cp data/shiftypad/raw/17.json  backend/tests/fixtures/shiftypad/anis-star.json
cp data/shiftypad/raw/32.json  backend/tests/fixtures/shiftypad/miranda.json
cp data/shiftypad/raw/43.json  backend/tests/fixtures/shiftypad/d-killer-wife.json
cp data/shiftypad/raw/150.json backend/tests/fixtures/shiftypad/julia.json
```

- [ ] **Step 7: 회귀 확인**

Run: `cd tools/collect-blablalink && node --test`
Expected: 기존 테스트 전부 초록(이 태스크는 JS 단위 테스트를 추가하지 않는다 — 수집은 네트워크).

- [ ] **Step 8: 커밋**

```bash
git add tools/collect-blablalink/collect.js backend/tests/fixtures/shiftypad/
git commit -m "feat(collect): add --nikke unit-detail mode + parity fixtures

Dumps one unit's raw ShiftyPad bundle (directory entry + character detail
payload) headless, no login. Commits six weapon-type representatives as the
fixtures the normalizer and parity harness are proven against."
```

---

## Task 2: 정규화기 — 원시 번들 → dotgg 모양

원시 ShiftyPad 번들을 dotgg 파일과 같은 모양의 dict로 변환하는 순수 함수. 커밋된 픽스처로 검증한다.

**Files:**
- Create: `backend/app/shiftypad_normalize.py`
- Test: `backend/tests/test_shiftypad_normalize.py`

**Interfaces:**
- Produces: `normalize_shiftypad(bundle: dict) -> dict` — 반환 dict는 dotgg 파일과 같은 키를 갖는다: 최상위 `weapon`/`maxAmmo`/`damage`/`reloadTime`/`chargeTime`/`chargeDamage`/`element`/`burst`, 그리고 `skills`: 길이 3의 리스트로 각 원소가 `{"cooldown": <float>, "levels": [<레벨별 description_value_NN dict>, …]}`.

- [ ] **Step 1: 실패하는 테스트 작성**

`backend/tests/test_shiftypad_normalize.py`:

```python
"""Tests for backend/app/shiftypad_normalize.py against committed fixtures."""
import json
from pathlib import Path

from app.shiftypad_normalize import normalize_shiftypad

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "shiftypad"


def _bundle(slug):
    return json.loads((FIXTURES / f"{slug}.json").read_text(encoding="utf-8"))


def test_weapon_fields_use_dotgg_fixed_point():
    out = normalize_shiftypad(_bundle("rapi-red-hood"))
    assert out["weapon"] == "MG"
    assert out["maxAmmo"] == 300
    assert out["damage"] == "5.57%"
    assert out["reloadTime"] == 2.5
    assert out["chargeTime"] == 0
    assert out["chargeDamage"] == "100%"


def test_meta_from_directory():
    out = normalize_shiftypad(_bundle("rapi-red-hood"))
    assert out["element"] == "Fire"
    assert out["burst"] == 3


def test_burst_cooldown_is_centiseconds_over_100():
    out = normalize_shiftypad(_bundle("rapi-red-hood"))
    assert out["skills"][2]["cooldown"] == 40


def test_skill_ladder_is_transposed_to_dotgg_shape():
    out = normalize_shiftypad(_bundle("rapi-red-hood"))
    level1 = out["skills"][0]["levels"][0]
    assert level1["description_value_01"] == "1"
    assert level1["description_value_02"] == "5.34"
    assert level1["description_value_03"] == "59.4"
    # every skill carries all 10 levels
    assert all(len(s["levels"]) == 10 for s in out["skills"])


def test_charge_weapon_full_charge_damage():
    out = normalize_shiftypad(_bundle("anis-star"))  # RL
    assert out["weapon"] == "RL"
    assert out["chargeTime"] == 1
    assert out["chargeDamage"] == "250%"
```

- [ ] **Step 2: 실패 확인**

Run: `cd backend && python3 -m pytest tests/test_shiftypad_normalize.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.shiftypad_normalize'`

- [ ] **Step 3: 정규화기 구현**

`backend/app/shiftypad_normalize.py`:

```python
"""Normalize a raw ShiftyPad bundle into the dotgg file shape.

A raw bundle is {"directory": <public directory entry>, "detail": <character
detail payload>} as dumped by collect.js --nikke. dotgg stores a unit's weapon
stats and per-level skill slots in one file; producing that exact shape lets
every downstream parser (skill_values.dotgg_slots, user_roster._weapon_stats,
the meta reads) be reused unchanged. The fixed-point conventions match dotgg's:
ShiftyPad stores damage/charge as hundredths of a percent and times as
centiseconds; dotgg stores "5.57%" strings and 2.5-second floats.

Pure function: no I/O. The collector fetches; the parity harness proves this
output equals the committed dotgg ground truth field for field.
"""


def _pct(hundredths):
    """6130 -> "61.3%" (dotgg's percent-string convention)."""
    return f"{hundredths / 100:g}%"


def _sec(centiseconds):
    """250 -> 2.5 (dotgg's seconds float)."""
    return centiseconds / 100


def _skill_levels(skill_detail):
    """Transpose ShiftyPad's slot[level] into dotgg's levels[level][slot].

    description_value_list is a list of slots, each {"description_value":
    [<level1>, <level2>, …]}. dotgg stores a list of levels, each a dict of
    description_value_NN. The number of levels is the slot arrays' length.
    """
    slots = [s["description_value"] for s in skill_detail["description_value_list"]]
    num_levels = len(slots[0]) if slots else 0
    levels = []
    for lvl in range(num_levels):
        levels.append(
            {f"description_value_{i + 1:02d}": slot[lvl] for i, slot in enumerate(slots)}
        )
    return levels


def normalize_shiftypad(bundle):
    directory, detail = bundle["directory"], bundle["detail"]
    shot = detail["shot_detail"]
    skills = [
        {"levels": _skill_levels(detail["skill1_detail"])},
        {"levels": _skill_levels(detail["skill2_detail"])},
        {
            "cooldown": _sec(detail["ulti_skill_detail"]["skill_cooltime"]),
            "levels": _skill_levels(detail["ulti_skill_detail"]),
        },
    ]
    return {
        "weapon": directory["shot_id"]["weapon_type"],
        "maxAmmo": int(shot["max_ammo"]),
        "damage": _pct(shot["damage"]),
        "reloadTime": _sec(shot["reload_time"]),
        "chargeTime": _sec(shot["charge_time"]),
        "chargeDamage": _pct(shot["full_charge_damage"]),
        "element": directory["element_id"]["element"]["element"],
        "burst": int(directory["use_burst_skill"].removeprefix("Step")),
        "skills": skills,
    }
```

- [ ] **Step 4: 통과 확인**

Run: `cd backend && python3 -m pytest tests/test_shiftypad_normalize.py -v`
Expected: PASS — 5 tests.

- [ ] **Step 5: 커밋**

```bash
git add backend/app/shiftypad_normalize.py backend/tests/test_shiftypad_normalize.py
git commit -m "feat(shiftypad): normalize raw bundle into the dotgg file shape

Pure function: weapon fields via dotgg's fixed-point conventions, skill
ladders transposed from slot[level] to dotgg's levels[level][slot], burst
cooldown from skill_cooltime/100, meta from the directory entry."
```

---

## Task 3: 패리티 하니스 — dotgg 정답지 대조

정규화기 출력이 커밋된 dotgg 정답지와 필드 단위로 일치함을 증명한다. 백필 없이 파서를 구조적으로 검증하는 핵심 게이트다.

**Files:**
- Test: `backend/tests/test_shiftypad_parity.py`

**Interfaces:**
- Consumes: `normalize_shiftypad` (Task 2), `backend/tests/fixtures/shiftypad/*.json` (Task 1), `data/dotgg/` (동기화된 정답지).

- [ ] **Step 1: 패리티 테스트 작성**

`backend/tests/test_shiftypad_parity.py`:

```python
"""Parity harness: the ShiftyPad normalizer must reproduce dotgg's data.

For each fixture unit, run normalize_shiftypad on its committed raw bundle and
assert the fields that feed the engine match the committed dotgg file exactly.
This proves the parser without backfilling: the fixtures span all six weapon
types, so the structural cases (charge vs magazine, slot counts) are all
covered. Depends on data/dotgg/ being synced (python3 scripts/sync_worktree_data.py).
"""
import json
from pathlib import Path

import pytest

from app.shiftypad_normalize import normalize_shiftypad
from app.skill_values import _dotgg_path_for

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "shiftypad"
DATA_DIR = Path(__file__).resolve().parents[2] / "data"

# fixture slug -> the dotgg "url" that names its ground-truth file
PARITY_UNITS = {
    "anis-sparkling-summer": "anis-sparkling-summer",
    "rapi-red-hood": "rapi-red-hood",
    "anis-star": "anis-star",
    "miranda": "miranda",
    "d-killer-wife": "d-killer-wife",
    "julia": "julia",
}

WEAPON_FIELDS = ("weapon", "maxAmmo", "damage", "reloadTime", "chargeTime", "chargeDamage")


def _normalized(slug):
    bundle = json.loads((FIXTURES / f"{slug}.json").read_text(encoding="utf-8"))
    return normalize_shiftypad(bundle)


def _dotgg(url):
    return json.loads(_dotgg_path_for(url, DATA_DIR).read_text(encoding="utf-8"))


@pytest.mark.parametrize("slug,url", PARITY_UNITS.items())
def test_weapon_fields_match_dotgg(slug, url):
    got, truth = _normalized(slug), _dotgg(url)
    assert {f: got[f] for f in WEAPON_FIELDS} == {f: truth[f] for f in WEAPON_FIELDS}


@pytest.mark.parametrize("slug,url", PARITY_UNITS.items())
def test_meta_matches_dotgg(slug, url):
    got, truth = _normalized(slug), _dotgg(url)
    assert got["element"] == truth["element"]
    assert got["burst"] == truth["burst"]


@pytest.mark.parametrize("slug,url", PARITY_UNITS.items())
def test_skill_ladders_match_dotgg(slug, url):
    got, truth = _normalized(slug), _dotgg(url)
    for i in range(3):
        # dotgg keeps empty trailing slots (""); the normalizer emits exactly
        # the slots ShiftyPad carries, so compare only the slots dotgg fills.
        for lvl_got, lvl_truth in zip(got["skills"][i]["levels"], truth["skills"][i]["levels"]):
            filled = {k: v for k, v in lvl_truth.items() if v != ""}
            assert {k: lvl_got.get(k) for k in filled} == filled


@pytest.mark.parametrize("slug,url", PARITY_UNITS.items())
def test_burst_cooldown_matches_dotgg(slug, url):
    got, truth = _normalized(slug), _dotgg(url)
    assert got["skills"][2]["cooldown"] == float(truth["skills"][2]["cooldown"])
```

- [ ] **Step 2: 실행 — 패리티 검증**

Run: `cd backend && python3 -m pytest tests/test_shiftypad_parity.py -v`
Expected: PASS — 24개(6유닛 × 4테스트). 실패가 나면 정규화기가 dotgg와 어긋난다는 뜻이니, 어긋난 필드를 근본 원인까지 조사한다(값을 맞추려고 정답지를 바꾸지 말 것).

> 참고: `test_skill_ladders_match_dotgg`는 dotgg가 빈 문자열로 채운 미사용 슬롯을 비교에서 제외한다. dotgg 슬롯 수와 ShiftyPad 슬롯 수가 다를 수 있는 유일한 지점이며, 엔진이 읽는 것은 채워진 슬롯뿐이다.

- [ ] **Step 3: 커밋**

```bash
git add backend/tests/test_shiftypad_parity.py
git commit -m "test(shiftypad): parity harness against dotgg ground truth

Proves the normalizer reproduces dotgg's weapon fields, meta, skill ladders
and burst cooldown across all six weapon types, so a new unit can rely on it
without a second source to check against."
```

---

## Task 4: 로더 배선 — `source: "shiftypad"`

정규화된 파일을 shiftypad 소스로 로드하도록 배선한다. dotgg/lootandwaifus 소스 유닛의 동작은 불변이어야 한다.

**Files:**
- Modify: `backend/app/skill_values.py` (`load_character_data`, `assemble_skill_values`)
- Modify: `backend/app/user_roster.py` (`load_nikke_spec`의 무기·메타 읽기)
- Test: `backend/tests/test_user_roster_shiftypad.py`

**Interfaces:**
- Consumes: 정규화된 파일 `data/shiftypad/<slug>.json`(dotgg 모양).
- `load_character_data(source, data_slug, data_dir)`는 `source == "shiftypad"`일 때 `data/shiftypad/<slug>.json`을 읽는다.

- [ ] **Step 1: 실패하는 통합 테스트 작성**

`backend/tests/test_user_roster_shiftypad.py`. 정규화된 파일을 임시 data_dir에 놓고, shiftypad 소스 manifest를 가진 유닛이 무기·스킬·메타를 올바르게 산출하는지 확인한다. Rapi 픽스처를 정규화해 정답 파일을 만든다.

```python
"""shiftypad-source loading: weapon, skill values and meta come from the
normalized data/shiftypad/<slug>.json, not dotgg."""
import json
from pathlib import Path

from app.shiftypad_normalize import normalize_shiftypad
from app.skill_values import assemble_skill_values, load_character_data

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "shiftypad"


def _write_normalized(data_dir, slug):
    bundle = json.loads((FIXTURES / f"{slug}.json").read_text(encoding="utf-8"))
    out = data_dir / "shiftypad"
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{slug}.json").write_text(
        json.dumps(normalize_shiftypad(bundle)), encoding="utf-8"
    )


def test_load_character_data_reads_shiftypad_dir(tmp_path):
    _write_normalized(tmp_path, "rapi-red-hood")
    data = load_character_data("shiftypad", "rapi-red-hood", tmp_path)
    assert data["weapon"] == "MG"
    assert data["skills"][0]["levels"][0]["description_value_02"] == "5.34"


def test_assemble_skill_values_treats_shiftypad_as_native_slots(tmp_path):
    _write_normalized(tmp_path, "rapi-red-hood")
    manifest = {
        "source": "shiftypad",
        "keys": {"battlefield_assessment": ("skills", 0)},
    }
    levels = {"skill1": 1, "skill2": 1, "burst": 1}
    values = assemble_skill_values("rapi-red-hood", manifest, levels, tmp_path)
    # native-slot passthrough, same as dotgg
    assert values["battlefield_assessment"]["description_value_02"] == "5.34"
```

- [ ] **Step 2: 실패 확인**

Run: `cd backend && python3 -m pytest tests/test_user_roster_shiftypad.py -v`
Expected: FAIL — `load_character_data`가 shiftypad를 모르고 lootandwaifus 경로로 가서 `FileNotFoundError`.

- [ ] **Step 3: `skill_values.py` 배선**

`load_character_data`를 다음으로 교체:

```python
def load_character_data(source, data_slug, data_dir=DATA_DIR):
    if source == "dotgg":
        path = _dotgg_path_for(data_slug, data_dir)
    elif source == "shiftypad":
        path = Path(data_dir) / "shiftypad" / f"{data_slug}.json"
    else:
        path = Path(data_dir) / "lootandwaifus" / f"char_{data_slug}.json"
    return json.loads(path.read_text(encoding="utf-8"))
```

`assemble_skill_values`의 슬롯 분기를 shiftypad도 native-slot 경로로:

```python
        if manifest["source"] in ("dotgg", "shiftypad"):
            values[key] = dotgg_slots(raw_level, drop)
        else:
            values[key] = extract_lootandwaifus_slots(raw_level, drop)
```

- [ ] **Step 4: `user_roster.py` 무기·메타 배선**

`load_nikke_spec`에서 무기 데이터를 소스별로 읽도록 바꾼다. 현재:

```python
    try:
        dotgg = load_character_data("dotgg", manifest.get("dotgg_slug", data_slug), data_dir)
    except FileNotFoundError:
        return None
    weapon_stats = _weapon_stats(dotgg)
    if weapon_stats is None:
        return None
    try:
        meta = load_character_data("lootandwaifus", data_slug, data_dir)
    except FileNotFoundError:
        meta = dotgg
```

를 다음으로 교체:

```python
    # Weapon stats and meta come from the manifest's source for shiftypad units;
    # dotgg- and lootandwaifus-source units still read weapon stats from dotgg.
    if manifest["source"] == "shiftypad":
        try:
            weapon_data = load_character_data("shiftypad", data_slug, data_dir)
        except FileNotFoundError:
            return None
    else:
        try:
            weapon_data = load_character_data(
                "dotgg", manifest.get("dotgg_slug", data_slug), data_dir
            )
        except FileNotFoundError:
            return None
    weapon_stats = _weapon_stats(weapon_data)
    if weapon_stats is None:
        return None
    try:
        meta = load_character_data("lootandwaifus", data_slug, data_dir)
    except FileNotFoundError:
        meta = weapon_data
```

(`meta`는 lootandwaifus가 없으면 `weapon_data`로 폴백한다. shiftypad 파일은 `element`/`burst`/`weapon`/`skills[2].cooldown`을 담으므로 메타 읽기가 성립한다.)

- [ ] **Step 5: 통과 확인**

Run: `cd backend && python3 -m pytest tests/test_user_roster_shiftypad.py -v`
Expected: PASS — 2 tests.

- [ ] **Step 6: 전체 회귀 (기존 유닛 불변 증명)**

Run: `cd backend && python3 -m pytest -q`
Expected: 기존 통과 수 + 이 태스크가 추가한 2. dotgg/lootandwaifus 소스 유닛은 전부 그대로 통과해야 한다(go-forward 불변식).

- [ ] **Step 7: 커밋**

```bash
git add backend/app/skill_values.py backend/app/user_roster.py backend/tests/test_user_roster_shiftypad.py
git commit -m "feat(loader): add shiftypad source for weapon, skills and meta

A shiftypad-source unit reads its normalized data/shiftypad/<slug>.json for
weapon stats, native-slot skill values and meta. dotgg/lootandwaifus units
are untouched."
```

---

## Task 5: 온보딩 문서 갱신

신규 유닛 온보딩에서 무기 스텁 수동 입력을 ShiftyPad 수집·정규화로 교체한다.

**Files:**
- Modify: `docs/new-nikke-detection.md` (온보딩 절차)

- [ ] **Step 1: 온보딩 절차 교체**

`docs/new-nikke-detection.md`의 "신규 니케 감지 토스트가 떴을 때 — 온보딩" 절차에서, 무기 스텁 수동 입력 단계(🔴 #3)를 다음으로 교체한다. **비-시그니처 유닛**은 ShiftyPad로 무기+스킬을 받는다:

```markdown
2. **데이터 수집** — 비-시그니처 유닛: `node collect.js --nikke <rid> --headless`로
   ShiftyPad 번들을 받아 `python3 -m app.shiftypad_normalize`(또는 온보딩 스크립트)로
   `data/shiftypad/<slug>.json` 생성. manifest `source`를 `"shiftypad"`로 둔다.
   시그니처 무기(dollskills) 버전은 ShiftyPad가 dollskills를 노출하지 않으므로 기존
   `/collect-nikke`(lootandwaifus/dotgg) 경로 + 수동 스텁을 쓴다(9유닛과 동일).
```

기존 🔴 무기 스탯 수동 입력 항목은 "시그니처 무기 버전에 한해" 남는다는 취지로 축소한다.

- [ ] **Step 2: 참조 정확성 확인**

Run: `grep -n "shiftypad\|--nikke\|shiftypad_normalize" docs/new-nikke-detection.md`
Expected: 새 참조가 실존 파일/모드를 가리킨다(`collect.js --nikke`는 Task 1, `app.shiftypad_normalize`는 Task 2).

- [ ] **Step 3: 커밋**

```bash
git add docs/new-nikke-detection.md
git commit -m "docs(onboarding): new non-signature units source weapon+skills from ShiftyPad

Replaces the manual weapon-stub step with the --nikke collect + normalize
path. Signature-weapon (dollskills) versions keep the old lootandwaifus/dotgg
route, since ShiftyPad does not expose dollskills."
```

---

## Self-Review

**1. Spec coverage**

| 스펙 요구 | 태스크 |
|---|---|
| 수집: collect.js 유닛 상세, 원시 덤프, 헤드리스/로그인 불필요 | Task 1 |
| 정규화기: dotgg 모양, ÷100, 전치, 쿨다운, 메타, 순수 함수 | Task 2 |
| 픽스처 커밋(backend/tests/fixtures/shiftypad) | Task 1 Step 6 |
| 로더 배선: load_character_data + assemble_skill_values + 무기/메타 분기 | Task 4 |
| 패리티 하니스: dotgg 정답지 대조, 6무기타입, hermetic | Task 3 |
| go-forward 불변식(기존 유닛 불변) | Task 4 Step 6 회귀 |
| dollskills 한계 문서화 | Task 5 |
| 온보딩 통합 | Task 5 |

빠진 요구 없음. (선택적 라이브 전수 스윕은 스펙에서 "유지보수 도구"로 선택 항목이며 이 계획의 필수 산출물이 아니다 — YAGNI로 제외, 필요 시 별도.)

**2. Placeholder scan**

"TBD"/"적절히"/"테스트 작성하라"류 없음. 모든 코드 단계에 실제 코드. Task 5 Step 1의 온보딩 스크립트 표현은 "정규화기를 부르는 방법"을 열어두었는데, `normalize_shiftypad`가 순수 함수이므로 이를 부르는 한 줄 wrapper는 온보딩 시 사람이 실행하는 사항이라 문서에 명령형으로 남긴다(계획 산출물 아님).

**3. Type consistency**

- Task 2가 만드는 `normalize_shiftypad(bundle) -> dict`(키: weapon/maxAmmo/damage/reloadTime/chargeTime/chargeDamage/element/burst/skills)를 Task 3(패리티)·Task 4(로더 테스트)가 그대로 소비. ✅
- Task 1의 번들 모양 `{directory, detail}`을 Task 2의 `normalize_shiftypad`가 `bundle["directory"]`/`bundle["detail"]`로 읽음. ✅
- Task 4의 `load_character_data(source="shiftypad")` 경로를 Task 4 테스트가 호출. ✅
- `skills[2]["cooldown"]`(Task 2) ↔ 패리티(Task 3)·user_roster 메타 폴백(Task 4). ✅

**주의로 남기는 사항:** 패리티(Task 3)와 정규화 테스트(Task 2)는 Task 1이 커밋한 픽스처에 의존한다 — 태스크 순서를 지켜야 한다. 패리티는 `data/dotgg/`(동기화된 정답지)도 읽으므로, 실행 환경에 `sync_worktree_data.py`가 선행돼야 한다(Global Constraints에 기재).
