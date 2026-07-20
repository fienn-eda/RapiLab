# 신규 니케 출시 자동 탐지 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 매일 19시 blablalink 공개 디렉토리를 무인으로 받아 커밋된 스냅샷과 비교하고, 새 SSR 니케가 있거나 점검이 실패하면 Windows 토스트로 알린다.

**Architecture:** `collect.js`에 계정 없이 도는 `--headless` 모드를 더해 디렉토리를 스크래치 경로로 덤프하고, 파이썬 스크립트가 커밋된 스냅샷과 `resource_id`로 비교해 토스트를 띄운다. 순수 비교 로직은 오케스트레이션과 분리해 단위 테스트한다. 리포지토리 파일은 절대 수정하지 않는다.

**Tech Stack:** Node 24 + `playwright-core` 1.61.1 (신규 의존성 없음), Python 3 + pytest, PowerShell 5.1 (WinRT 토스트), Windows 작업 스케줄러

## Global Constraints

- **스크립트는 리포지토리를 수정하지 않는다.** 신선한 디렉토리는 `data/cache/new-nikke-check/`에만 쓴다(`.gitignore`에 `data/cache/` 존재). 커밋된 `tools/collect-blablalink/nikke-directory.json`은 건드리지 않는다.
- **종료 코드:** `0` 신규 없음 · `1` 신규 SSR 있음 · `2` 실패.
- **토스트는 신규 SSR이 있을 때, 그리고 실패했을 때만** 띄운다. 신규 R/SR은 로그에만 남긴다(레이드는 SSR 전용).
- **실패는 시끄럽게.** 어떤 예외든 토스트 + 종료 코드 `2`. 조용히 죽지 않는다.
- **`--headless`는 `--directory`와 함께일 때만 유효**하며, 단독으로 주면 오류로 거부한다. 로스터 수집 모드는 로그인 세션이 필요하므로 `connectOverCDP`를 유지한다.
- 토스트 본문은 신규 SSR의 `name_en`을 쉼표로 나열하되 **3명 초과 시 앞 3명 + `외 N명`**.
- Chrome 경로는 환경변수 `CHROME_PATH`가 있으면 우선하고, 없으면 알려진 경로를 순서대로 시도한다. **어디서도 못 찾으면 시도한 경로를 모두 나열하며 실패**한다.
- 스냅샷에 `element`는 없다. 보고 필드는 `resource_id` · `name_en` · `class` · `corporation` · `original_rare`.
- 기존 테스트를 약화시키지 않는다. 백엔드 전체 스위트는 계속 초록이어야 한다.

**베이스라인 (구현 시작 전 측정할 것):** 백엔드 `pytest`와 `node --test`의 현재 통과 수를 각 태스크 시작 전에 기록하고, 끝난 뒤 늘어난 수가 그 태스크가 추가한 테스트 수와 일치하는지 확인한다. 이 계획에 특정 숫자를 적지 않는 이유는 병렬 세션이 테스트를 추가하고 있어 계획 작성 시점의 숫자가 실행 시점에 이미 낡기 때문이다.

---

## File Structure

| 파일 | 책임 |
|---|---|
| `tools/collect-blablalink/directory.js` (신규) | 디렉토리 스냅샷 순수 변환: 트림, `corporation_sub_type` 승계, 승계 안 된 id 목록 |
| `tools/collect-blablalink/directory.test.js` (신규) | 위의 `node --test` 단위 테스트 |
| `tools/collect-blablalink/capture.js` (수정) | 헤드리스 자체 실행 브라우저 `launch()` 추가 |
| `tools/collect-blablalink/collect.js` (수정) | `--headless` 배선, 승계 적용, `--deep`을 미승계 id로 한정 |
| `scripts/notify_toast.ps1` (신규) | WinRT 토스트 발사 |
| `scripts/check_new_nikkes.py` (신규) | 본체: 덤프 실행 → 비교 → 토스트 → 종료 코드 |
| `backend/tests/test_check_new_nikkes.py` (신규) | 비교 로직 + 페이크 오케스트레이션 테스트 |
| `scripts/schedule_new_nikke_check.ps1` (신규) | 작업 스케줄러 등록/해제/상태 |

---

## Task 1: 디렉토리 순수 변환 모듈 분리 + `corporation_sub_type` 승계

`collect.js`는 require 시 `main()`을 실행하므로 테스트에서 import할 수 없다. `parse.js` / `parse.test.js` 쌍의 기존 관례대로 순수 함수를 별도 모듈로 뺀다.

**해결하는 결함:** `trimDirectory`는 엔트리를 필드 6개로 새로 만들며 `corporation_sub_type`을 버린다. 이 필드는 돌파 코어당 flat ATK를 결정하고 현재 스냅샷의 **27/194 엔트리**에 있다. 따라서 `--deep` 없이 갱신하면 27개 유닛의 ATK가 조용히 틀어진다. `collect.js:219`의 "the field is otherwise carried over from the previous one" 주석은 **존재하지 않는 코드를 설명한다**(`collect.js`에는 `readFileSync`도 `existsSync`도 없다).

**Files:**
- Create: `tools/collect-blablalink/directory.js`
- Create: `tools/collect-blablalink/directory.test.js`
- Modify: `tools/collect-blablalink/collect.js` (193-213행의 `nameOf` / `trimDirectory` 제거 후 require)

**Interfaces:**
- Produces:
  - `nameOf(entry) -> string|null`
  - `trimDirectory(rawDir) -> Entry[]` — `resource_id` 오름차순 정렬
  - `carryOverSubTypes(entries, previous) -> Entry[]` — 새 배열 반환, 입력 비변경
  - `missingSubTypeIds(entries) -> number[]`
  - `Entry = { resource_id, name_code, name_en, original_rare, class, corporation, corporation_sub_type? }`

- [ ] **Step 1: 실패하는 테스트 작성**

`tools/collect-blablalink/directory.test.js`:

```js
const { test } = require('node:test')
const assert = require('node:assert/strict')
const { trimDirectory, carryOverSubTypes, missingSubTypeIds } = require('./directory')

const raw = (id, name, extra = {}) => ({
  resource_id: id,
  name_code: 3000 + id,
  name_localkey: { name },
  original_rare: 'SSR',
  class: 'Attacker',
  corporation: 'ELYSION',
  ...extra,
})

test('trimDirectory keeps the six snapshot fields and sorts by resource_id', () => {
  const out = trimDirectory([raw(20, 'Bravo'), raw(10, 'Alpha')])
  assert.deepEqual(out.map((e) => e.resource_id), [10, 20])
  assert.deepEqual(Object.keys(out[0]).sort(), [
    'class', 'corporation', 'name_code', 'name_en', 'original_rare', 'resource_id',
  ])
})

test('trimDirectory drops entries with no name', () => {
  const nameless = { resource_id: 30, name_code: 3030, name_localkey: null }
  assert.equal(trimDirectory([raw(10, 'Alpha'), nameless]).length, 1)
})

test('carryOverSubTypes restores corporation_sub_type from the previous snapshot', () => {
  const fresh = trimDirectory([raw(10, 'Alpha'), raw(20, 'Bravo')])
  const previous = [{ resource_id: 10, corporation_sub_type: 'OVERSPEC' }]
  const out = carryOverSubTypes(fresh, previous)
  assert.equal(out[0].corporation_sub_type, 'OVERSPEC')
  assert.equal('corporation_sub_type' in out[1], false)
})

test('carryOverSubTypes does not mutate its input', () => {
  const fresh = trimDirectory([raw(10, 'Alpha')])
  carryOverSubTypes(fresh, [{ resource_id: 10, corporation_sub_type: 'OVERSPEC' }])
  assert.equal('corporation_sub_type' in fresh[0], false)
})

test('carryOverSubTypes passes through when there is no previous snapshot', () => {
  const fresh = trimDirectory([raw(10, 'Alpha')])
  assert.deepEqual(carryOverSubTypes(fresh, null), fresh)
  assert.deepEqual(carryOverSubTypes(fresh, []), fresh)
})

test('carryOverSubTypes does not resurrect a null previous value', () => {
  const fresh = trimDirectory([raw(10, 'Alpha')])
  const out = carryOverSubTypes(fresh, [{ resource_id: 10, corporation_sub_type: null }])
  assert.equal('corporation_sub_type' in out[0], false)
})

test('missingSubTypeIds lists only the ids the carry-over left empty', () => {
  const fresh = trimDirectory([raw(10, 'Alpha'), raw(20, 'Bravo')])
  const out = carryOverSubTypes(fresh, [{ resource_id: 10, corporation_sub_type: 'OVERSPEC' }])
  assert.deepEqual(missingSubTypeIds(out), [20])
})
```

- [ ] **Step 2: 실패 확인**

Run: `cd tools/collect-blablalink && node --test directory.test.js`
Expected: FAIL — `Cannot find module './directory'`

- [ ] **Step 3: 모듈 구현**

`tools/collect-blablalink/directory.js`:

```js
// Pure transforms over the public nikke directory snapshot. Split out of
// collect.js so they can be unit-tested: requiring collect.js runs main().

const nameOf = (entry) => (entry.name_localkey && entry.name_localkey.name) || null

// Reduce the raw directory to the public identity fields the repo commits as a
// snapshot: enough to prove a resource_id names the unit its slug claims, and to
// look one up for a not-yet-owned unit. Nothing here is account-specific.
const trimDirectory = (dir) =>
  dir
    .filter((d) => nameOf(d))
    .map((d) => ({
      resource_id: d.resource_id,
      name_code: d.name_code,
      name_en: nameOf(d),
      original_rare: d.original_rare,
      // Base ATK/HP are a function of (level, class), so the class is what the
      // stat calculator looks up - it cannot be derived from the other fields.
      class: d.class,
      // Corporation research is ranked per account and adds flat ATK to that
      // corporation's units, so a unit's corporation is part of its stat inputs.
      corporation: d.corporation,
    }))
    .sort((a, b) => a.resource_id - b.resource_id)

// corporation_sub_type ("OVERSPEC") decides how much flat ATK each breakthrough
// core is worth, but the directory payload does not carry it - it lives in the
// per-character stat file, one page load away. Carrying it over from the previous
// snapshot is what keeps a plain --directory refresh from silently dropping it.
const carryOverSubTypes = (entries, previous) => {
  const known = new Map(
    (previous || [])
      .filter((e) => e.corporation_sub_type)
      .map((e) => [e.resource_id, e.corporation_sub_type]),
  )
  return entries.map((e) =>
    known.has(e.resource_id)
      ? { ...e, corporation_sub_type: known.get(e.resource_id) }
      : e,
  )
}

// Ids still without a sub type after the carry-over: newly released units, the
// only ones --deep needs to visit.
const missingSubTypeIds = (entries) =>
  entries.filter((e) => !e.corporation_sub_type).map((e) => e.resource_id)

module.exports = { nameOf, trimDirectory, carryOverSubTypes, missingSubTypeIds }
```

- [ ] **Step 4: 통과 확인**

Run: `cd tools/collect-blablalink && node --test directory.test.js`
Expected: PASS — 7 tests

- [ ] **Step 5: `collect.js`에서 중복 제거**

`collect.js` 193-213행의 `const nameOf = ...`와 `const trimDirectory = ...` 정의를 **삭제**하고, 28행 부근의 require 블록에 다음 줄을 추가한다:

```js
const { nameOf, trimDirectory, carryOverSubTypes, missingSubTypeIds } = require('./directory')
```

`nameOf`는 `collect.js` 120·122·327행에서도 쓰이므로 require로 계속 제공되어야 한다.

- [ ] **Step 6: 회귀 확인**

Run: `cd tools/collect-blablalink && node --test`
Expected: PASS — `parse.test.js`와 `directory.test.js` 전부 통과. `node -e "require('./directory')"`가 오류 없이 끝나는지도 확인.

- [ ] **Step 7: 커밋**

```bash
git add tools/collect-blablalink/directory.js tools/collect-blablalink/directory.test.js tools/collect-blablalink/collect.js
git commit -m "refactor(collect): extract directory transforms and carry corporation_sub_type

trimDirectory rebuilt each entry from six fields and dropped
corporation_sub_type, so a --directory refresh without --deep silently
wiped it from the 27 entries that have it. The comment claiming the field
was carried over from the previous snapshot described code that did not
exist."
```

---

## Task 2: `--headless` 모드 배선

`--directory`는 계정이 필요 없다(`collect.js:271` 주석). Chrome이 필요한 것은 인증이 아니라 **CDN 파일명이 해시라 회전해서 네트워크 응답을 엿봐야 URL을 찾기 때문**이다. 따라서 이 모드만 자체 브라우저를 띄우면 무인 실행이 가능해진다. 실측으로 194 엔트리 캡처를 확인했다.

**Files:**
- Modify: `tools/collect-blablalink/capture.js` (17행 `connect` 옆에 `launch` 추가)
- Modify: `tools/collect-blablalink/collect.js` (인자 파싱, `main()`의 브라우저 획득과 `--directory` 분기)

**Interfaces:**
- Consumes: Task 1의 `trimDirectory` / `carryOverSubTypes` / `missingSubTypeIds`
- Produces: `launch() -> Promise<Browser>` (capture.js), CLI 플래그 `--headless`

- [ ] **Step 1: `capture.js`에 `launch` 추가**

`capture.js`의 `const connect = () => chromium.connectOverCDP(CDP)` 바로 아래에 추가하고, 파일 끝 `module.exports`의 목록에 `launch`를 더한다:

```js
// Known install locations, tried in order; CHROME_PATH overrides. The directory
// dump is public game data and needs no account, so it can run in a browser we
// launch ourselves instead of attaching to the user's logged-in Chrome.
const CHROME_PATHS = [
  process.env.CHROME_PATH,
  'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
  'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
  'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
  'C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe',
].filter(Boolean)

const launch = () => {
  const exe = CHROME_PATHS.find((p) => fs.existsSync(p))
  if (!exe) {
    throw new Error(
      `no Chrome/Edge executable found; set CHROME_PATH. Tried:\n  ${CHROME_PATHS.join('\n  ')}`,
    )
  }
  return chromium.launch({ executablePath: exe, headless: true })
}
```

`capture.js` 상단에 `const fs = require('fs')`가 없으면 추가한다(구현자가 파일을 열어 확인할 것 — 있으면 중복 선언하지 말 것).

- [ ] **Step 2: `collect.js` 인자 파싱**

`const DEEP = args.includes('--deep')` 아래에 추가:

```js
const HEADLESS = args.includes('--headless')
```

require 줄을 다음으로 교체:

```js
const { connect, launch, findPage, captureUnit } = require('./capture')
```

- [ ] **Step 3: 잘못된 조합 거부**

`const main = async () => {` 바로 다음 줄에 추가:

```js
  if (HEADLESS && !DIRECTORY_ONLY) {
    throw new Error('--headless only applies to --directory; the other modes need your logged-in session')
  }
```

- [ ] **Step 4: 브라우저 획득과 페이지 선택 분기**

`main()`의 다음 세 줄을

```js
  const browser = await connect()
  const ctx = browser.contexts()[0]
  const page = findPage(ctx)
```

다음으로 교체한다:

```js
  const browser = HEADLESS ? await launch() : await connect()
  const page = HEADLESS
    ? await browser.newPage()
    : findPage(browser.contexts()[0])
```

- [ ] **Step 5: `--directory` 분기에 승계 적용, `--deep`을 미승계 id로 한정**

`if (DIRECTORY_ONLY) { ... }` 블록 전체를 다음으로 교체한다:

```js
  if (DIRECTORY_ONLY) {
    let entries = RAW ? dir : trimDirectory(dir)
    if (!RAW) {
      const previous = fs.existsSync(OUT)
        ? JSON.parse(fs.readFileSync(OUT, 'utf8'))
        : null
      entries = carryOverSubTypes(entries, previous)
      if (DEEP) {
        const missing = missingSubTypeIds(entries)
        log(`collecting corporation_sub_type for ${missing.length} unit(s) without one…`)
        const subTypes = await collectSubTypes(page, entries.filter((e) => !e.corporation_sub_type))
        entries = entries.map((e) =>
          subTypes.has(e.resource_id)
            ? { ...e, corporation_sub_type: subTypes.get(e.resource_id) }
            : e,
        )
      }
    }
    fs.writeFileSync(OUT, `${JSON.stringify(entries, null, 2)}\n`)
    log(`wrote ${OUT}: ${entries.length} nikkes`)
    await browser.close()
    return
  }
```

- [ ] **Step 6: 사용법 주석 갱신**

`collect.js` 상단 주석의 `--deep` 항목을 다음으로 교체하고, `--headless` 항목을 더한다:

```
//   --deep      with --directory, fetch corporation_sub_type for units that do
//               not already have one carried over from the previous snapshot
//               (i.e. newly released units). One page load each.
//   --headless  with --directory, launch our own browser instead of attaching to
//               yours. The directory is public game data, so this needs no
//               account - it is what lets the scheduled check run unattended.
```

- [ ] **Step 7: 헤드리스 덤프가 도는지 검증**

승계는 `--out`이 가리키는 **그 파일**의 이전 내용에서 이루어진다. 따라서 커밋된 스냅샷을 먼저 스크래치로 복사해두고 그 위에 덤프해야 승계가 실제로 일어난다. 리포지토리 파일은 어느 단계에서도 쓰이지 않는다.

```bash
mkdir -p data/cache/new-nikke-check
cp tools/collect-blablalink/nikke-directory.json data/cache/new-nikke-check/probe.json
cd tools/collect-blablalink && node collect.js --directory --headless --out "../../data/cache/new-nikke-check/probe.json"
```

Expected: `wrote ...: N nikkes` (N은 실행 시점의 실제 니케 수). 로그인 프롬프트나 CDP 오류가 없어야 한다.

- [ ] **Step 8: 승계가 실제로 값을 보존했는지 확인**

```bash
python -c "
import json
a=json.load(open('tools/collect-blablalink/nikke-directory.json',encoding='utf-8'))
b=json.load(open('data/cache/new-nikke-check/probe.json',encoding='utf-8'))
sub=lambda d:{e['resource_id']:e.get('corporation_sub_type') for e in d if e.get('corporation_sub_type')}
print('committed:',len(sub(a)),'after refresh:',len(sub(b)),'identical:',sub(a)==sub(b))
"
```

Expected: `committed: 27 after refresh: 27 identical: True` (27은 현재 값이며, 요점은 **양쪽이 같다**는 것이다). 승계 이전 코드였다면 `after refresh: 0`이 나온다 — 이것이 이 태스크가 고치는 결함이다.

- [ ] **Step 9: 리포지토리 미변경 확인**

Run: `git status --short`
Expected: `tools/collect-blablalink/nikke-directory.json`이 목록에 **없어야** 한다. 수정된 파일은 이 태스크가 편집한 소스뿐이다.

- [ ] **Step 10: 회귀 확인**

Run: `cd tools/collect-blablalink && node --test`
Expected: PASS — 기존 테스트 전부 초록

- [ ] **Step 11: 커밋**

```bash
git add tools/collect-blablalink/capture.js tools/collect-blablalink/collect.js
git commit -m "feat(collect): add --headless for the account-free directory dump

The directory is public game data; Chrome was only needed to discover the
rotating hash-named CDN url, not to authenticate. Launching our own browser
for this one mode is what makes an unattended scheduled check possible."
```

---

## Task 3: 토스트 헬퍼

**Files:**
- Create: `scripts/notify_toast.ps1`

**Interfaces:**
- Produces: `powershell -ExecutionPolicy Bypass -File scripts/notify_toast.ps1 -Title <string> -Body <string>`

- [ ] **Step 1: 스크립트 작성**

`scripts/notify_toast.ps1`:

```powershell
<#
.SYNOPSIS
Show a Windows toast notification.

.DESCRIPTION
Used by scripts/check_new_nikkes.py to surface its result. Uses the WinRT
notification API directly, so no BurntToast module install is required
(verified on this machine 2026-07-21). Toasts are the signal for the daily
scheduled check: silence means nothing was found.

.EXAMPLE
powershell -ExecutionPolicy Bypass -File scripts/notify_toast.ps1 -Title "신규 니케" -Body "Alpha, Bravo"
#>
param(
  [Parameter(Mandatory = $true)][string]$Title,
  [Parameter(Mandatory = $true)][string]$Body
)

$ErrorActionPreference = 'Stop'

[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null
[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] > $null

# PowerShell's own AUMID: a registered app id is required, and this one always
# exists on Windows, so the toast needs no shortcut of our own.
$AppId = '{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\WindowsPowerShell\v1.0\powershell.exe'

$esc = {
  param($s)
  $s.Replace('&', '&amp;').Replace('<', '&lt;').Replace('>', '&gt;')
}

$xml = @"
<toast><visual><binding template="ToastGeneric"><text>$(& $esc $Title)</text><text>$(& $esc $Body)</text></binding></visual></toast>
"@

$doc = New-Object Windows.Data.Xml.Dom.XmlDocument
$doc.LoadXml($xml)
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($AppId).Show(
  (New-Object Windows.UI.Notifications.ToastNotification $doc)
)
```

- [ ] **Step 2: 육안 검증**

Run: `powershell -ExecutionPolicy Bypass -File scripts/notify_toast.ps1 -Title "테스트" -Body "토스트 확인 <&> 이스케이프"`

Expected: 화면에 토스트가 뜨고, 본문에 `<&>`가 깨지지 않고 그대로 보인다. 오류 출력 없음.

- [ ] **Step 3: 커밋**

```bash
git add scripts/notify_toast.ps1
git commit -m "feat(scripts): add WinRT toast helper

The scheduled check has no console to print to, so the toast is its only
signal. WinRT is used directly because BurntToast is not installed."
```

---

## Task 4: 탐지 본체

**Files:**
- Create: `scripts/check_new_nikkes.py`
- Create: `backend/tests/test_check_new_nikkes.py`

**Interfaces:**
- Consumes: `collect.js --directory --headless --out <path>` (Task 2), `scripts/notify_toast.ps1` (Task 3)
- Produces:
  - `new_entries(committed: list[dict], fresh: list[dict]) -> list[dict]`
  - `new_ssr(entries: list[dict]) -> list[dict]`
  - `toast_body(entries: list[dict]) -> str`
  - `describe(entry: dict) -> str`
  - `run(fresh_path: str | None, dry_run: bool, notify) -> int` — 종료 코드 반환. `notify` 는 `(title, body) -> None` 콜러블이라 테스트가 주입할 수 있다.

- [ ] **Step 1: 실패하는 테스트 작성**

`backend/tests/test_check_new_nikkes.py`:

```python
"""Tests for scripts/check_new_nikkes.py (pure comparison logic and
orchestration with a fake notifier - the headless dump is exercised only by
real runs)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import check_new_nikkes as chk


def _entry(rid, name, rare="SSR"):
    return {"resource_id": rid, "name_code": 3000 + rid, "name_en": name,
            "original_rare": rare, "class": "Attacker", "corporation": "ELYSION"}


def test_new_entries_finds_ids_absent_from_the_committed_snapshot():
    committed = [_entry(10, "Alpha")]
    fresh = [_entry(10, "Alpha"), _entry(20, "Bravo")]
    assert [e["name_en"] for e in chk.new_entries(committed, fresh)] == ["Bravo"]


def test_new_entries_is_empty_when_nothing_was_added():
    committed = [_entry(10, "Alpha"), _entry(20, "Bravo")]
    assert chk.new_entries(committed, list(committed)) == []


def test_new_entries_ignores_a_rename_of_an_existing_resource_id():
    # A renamed unit is not a release; only unseen resource_ids are.
    committed = [_entry(10, "Alpha")]
    fresh = [_entry(10, "Alpha Renamed")]
    assert chk.new_entries(committed, fresh) == []


def test_new_entries_ignores_entries_removed_from_the_directory():
    committed = [_entry(10, "Alpha"), _entry(20, "Bravo")]
    fresh = [_entry(10, "Alpha")]
    assert chk.new_entries(committed, fresh) == []


def test_new_ssr_filters_out_non_ssr_releases():
    entries = [_entry(20, "Bravo"), _entry(21, "Charlie", rare="SR")]
    assert [e["name_en"] for e in chk.new_ssr(entries)] == ["Bravo"]


def test_toast_body_lists_every_name_up_to_three():
    entries = [_entry(20, "Bravo"), _entry(21, "Charlie"), _entry(22, "Delta")]
    assert chk.toast_body(entries) == "Bravo, Charlie, Delta"


def test_toast_body_truncates_past_three_names():
    entries = [_entry(20 + i, n) for i, n in
               enumerate(["Bravo", "Charlie", "Delta", "Echo", "Foxtrot"])]
    assert chk.toast_body(entries) == "Bravo, Charlie, Delta 외 2명"


def test_run_offline_returns_zero_and_stays_silent_when_nothing_is_new(tmp_path):
    fresh = tmp_path / "fresh.json"
    fresh.write_text(json.dumps(chk.load_committed()), encoding="utf-8")
    sent = []
    assert chk.run(str(fresh), dry_run=False, notify=lambda t, b: sent.append((t, b))) == 0
    assert sent == []


def test_run_offline_returns_one_and_notifies_when_a_new_ssr_appears(tmp_path):
    committed = chk.load_committed()
    fresh = tmp_path / "fresh.json"
    fresh.write_text(json.dumps(committed + [_entry(999999, "Zulu")]), encoding="utf-8")
    sent = []
    assert chk.run(str(fresh), dry_run=False, notify=lambda t, b: sent.append((t, b))) == 1
    assert len(sent) == 1 and "Zulu" in sent[0][1]


def test_run_stays_silent_for_a_new_non_ssr(tmp_path):
    committed = chk.load_committed()
    fresh = tmp_path / "fresh.json"
    fresh.write_text(json.dumps(committed + [_entry(999999, "Zulu", rare="SR")]),
                     encoding="utf-8")
    sent = []
    assert chk.run(str(fresh), dry_run=False, notify=lambda t, b: sent.append((t, b))) == 0
    assert sent == []


def test_dry_run_does_not_notify_but_still_reports_the_finding(tmp_path):
    committed = chk.load_committed()
    fresh = tmp_path / "fresh.json"
    fresh.write_text(json.dumps(committed + [_entry(999999, "Zulu")]), encoding="utf-8")
    sent = []
    assert chk.run(str(fresh), dry_run=True, notify=lambda t, b: sent.append((t, b))) == 1
    assert sent == []
```

- [ ] **Step 2: 실패 확인**

Run: `cd backend && python -m pytest tests/test_check_new_nikkes.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'check_new_nikkes'`

- [ ] **Step 3: 스크립트 구현**

`scripts/check_new_nikkes.py`:

```python
"""Detect nikkes released since the committed directory snapshot.

A newly released Nikke is dropped silently by the roster pipeline: it is not
in tools/collect-blablalink/nikke-directory.json, so assemble_roster skips it
and the frontend never gets a name to warn about. The only existing signal is
an unknown_name_codes counter in the server log that nobody reads, and it only
counts units you already own. This script watches the public directory instead,
so a release is noticed whether or not you pulled the unit.

It never modifies the repository: the fresh dump goes to data/cache/, and
refreshing the committed snapshot stays a deliberate step of onboarding.

Findings are reported with a Windows toast because the scheduled run has no
console anyone reads. Failures toast too - a check that dies quietly is worse
than no check, because you would believe you were covered.

When to use: automatically, from the daily scheduled task registered by
scripts/schedule_new_nikke_check.ps1. Run it by hand to check right now.

Usage:
    python scripts/check_new_nikkes.py                  # fetch + compare + toast
    python scripts/check_new_nikkes.py --offline FILE    # compare FILE, no fetch
    python scripts/check_new_nikkes.py --dry-run         # print, never toast

Exit: 0 nothing new, 1 new SSR found, 2 the check itself failed.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT = ROOT / "tools" / "collect-blablalink" / "nikke-directory.json"
COLLECT_DIR = ROOT / "tools" / "collect-blablalink"
SCRATCH = ROOT / "data" / "cache" / "new-nikke-check"
FRESH = SCRATCH / "fresh-directory.json"
LOG = SCRATCH / "last-run.log"
TOAST = ROOT / "scripts" / "notify_toast.ps1"

# Raid content is SSR-only - assemble_roster filters the same way - so a new
# R/SR is not something to act on.
RAID_RARITY = "SSR"
TOAST_NAME_LIMIT = 3


def load_committed():
    return json.loads(SNAPSHOT.read_text(encoding="utf-8"))


def new_entries(committed, fresh):
    """Entries whose resource_id is absent from the committed snapshot.

    Keyed on resource_id, not name: a rename is not a release, and an entry
    disappearing from the directory is not something we act on."""
    known = {e["resource_id"] for e in committed}
    return [e for e in fresh if e["resource_id"] not in known]


def new_ssr(entries):
    return [e for e in entries if e.get("original_rare") == RAID_RARITY]


def describe(entry):
    return (f"{entry['resource_id']:>5}  {entry.get('name_en')}  "
            f"[{entry.get('original_rare')} {entry.get('class')} "
            f"{entry.get('corporation')}]")


def toast_body(entries):
    names = [e.get("name_en") for e in entries]
    if len(names) <= TOAST_NAME_LIMIT:
        return ", ".join(names)
    shown = ", ".join(names[:TOAST_NAME_LIMIT])
    return f"{shown} 외 {len(names) - TOAST_NAME_LIMIT}명"


def toast(title, body):
    subprocess.run(
        ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(TOAST),
         "-Title", title, "-Body", body],
        check=True,
    )


def fetch_directory():
    """Dump the live public directory to the scratch path. Never writes to the
    committed snapshot: --out points into data/cache/."""
    SCRATCH.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["node", "collect.js", "--directory", "--headless", "--out", str(FRESH)],
        cwd=str(COLLECT_DIR), check=True,
    )
    return FRESH


def run(fresh_path=None, dry_run=False, notify=toast):
    path = Path(fresh_path) if fresh_path else fetch_directory()
    fresh = json.loads(Path(path).read_text(encoding="utf-8"))
    committed = load_committed()

    added = new_entries(committed, fresh)
    ssr = new_ssr(added)
    for e in added:
        print(("NEW  " if e in ssr else "new (non-SSR, ignored)  ") + describe(e))
    print(f"{len(fresh)} nikkes live, {len(committed)} in the snapshot, "
          f"{len(added)} new ({len(ssr)} SSR)")

    if not ssr:
        return 0
    print("\nOnboarding: refresh the snapshot with\n"
          "  cd tools/collect-blablalink && node collect.js --directory --headless --deep\n"
          "then /collect-nikke <name>, encode with the nikke-skill-encoding skill\n"
          "(test_resource_id_slug_map.py will force the slug-map entry).")
    if not dry_run:
        notify("신규 니케 감지", toast_body(ssr))
    return 1


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--offline", metavar="FILE",
                   help="compare this directory dump instead of fetching a fresh one")
    p.add_argument("--dry-run", action="store_true",
                   help="print what would be reported, never show a toast")
    args = p.parse_args()
    try:
        return run(args.offline, args.dry_run, toast)
    except Exception as exc:
        SCRATCH.mkdir(parents=True, exist_ok=True)
        LOG.write_text(f"{type(exc).__name__}: {exc}\n", encoding="utf-8")
        first_line = str(exc).splitlines()[0] if str(exc) else type(exc).__name__
        if not args.dry_run:
            try:
                toast("신규 니케 점검 실패", first_line[:200])
            except Exception:
                pass  # a failing toast must not hide the original failure
        print(f"FAILED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: 통과 확인**

Run: `cd backend && python -m pytest tests/test_check_new_nikkes.py -v`
Expected: PASS — 11 tests

- [ ] **Step 5: 실제 실행 검증 (신규 없음 경로)**

Run: `python scripts/check_new_nikkes.py --dry-run`
Expected: `... nikkes live, ... in the snapshot, 0 new (0 SSR)`, 종료 코드 0, 토스트 없음. `git status`로 리포지토리 미변경 확인.

Run: `echo $?` (bash) — `0`

- [ ] **Step 6: 실패 경로 검증**

Run: `python scripts/check_new_nikkes.py --offline nonexistent.json`
Expected: 토스트 "신규 니케 점검 실패"가 뜨고, `data/cache/new-nikke-check/last-run.log`에 예외가 기록되며, 종료 코드 `2`.

- [ ] **Step 7: 전체 스위트 회귀**

Run: `cd backend && python -m pytest -q`
Expected: 기존 통과 수 + 11

- [ ] **Step 8: 커밋**

```bash
git add scripts/check_new_nikkes.py backend/tests/test_check_new_nikkes.py
git commit -m "feat(scripts): detect nikkes released since the committed snapshot

The pipeline drops an unknown name_code silently and the only signal was a
server log counter nobody reads that also only counts owned units. This
watches the public directory instead and toasts on a new SSR, on failure,
and never otherwise."
```

---

## Task 5: 작업 스케줄러 등록 + 문서 갱신

**Files:**
- Create: `scripts/schedule_new_nikke_check.ps1`
- Modify: `docs/roadmap.md` (To-Do "디렉토리 스냅샷 갱신 루틴")

**Interfaces:**
- Consumes: `scripts/check_new_nikkes.py` (Task 4)

- [ ] **Step 1: 등록 스크립트 작성**

`scripts/schedule_new_nikke_check.ps1`:

```powershell
<#
.SYNOPSIS
Register, remove, or inspect the daily new-nikke check.

.DESCRIPTION
Runs scripts/check_new_nikkes.py every day at 19:00 local time. Patches land
on Thursdays every two to three weeks and finish at 15:00 or 18:00 KST, but
the interval is irregular and maintenance can overrun, so a Thursday-only run
risks missing a release for a whole week. A daily run costs one page load and
stays silent unless something is found.

The task is registered against this repository's path, so run this from the
main checkout - not from a worktree, which is temporary.

.EXAMPLE
powershell -ExecutionPolicy Bypass -File scripts/schedule_new_nikke_check.ps1 -Action register
powershell -ExecutionPolicy Bypass -File scripts/schedule_new_nikke_check.ps1 -Action status
powershell -ExecutionPolicy Bypass -File scripts/schedule_new_nikke_check.ps1 -Action unregister
#>
param(
  [Parameter(Mandatory = $true)]
  [ValidateSet('register', 'unregister', 'status')]
  [string]$Action
)

$ErrorActionPreference = 'Stop'

$TaskName = 'NikkeDeckBuilder-NewNikkeCheck'
$Repo = Split-Path -Parent $PSScriptRoot
$Script = Join-Path $Repo 'scripts\check_new_nikkes.py'

if (-not (Test-Path $Script)) { throw "not found: $Script" }

switch ($Action) {
  'register' {
    $python = (Get-Command python).Source
    $action = New-ScheduledTaskAction -Execute $python -Argument "`"$Script`"" -WorkingDirectory $Repo
    $trigger = New-ScheduledTaskTrigger -Daily -At 19:00
    # Exit code 1 means "new nikke found", not failure, so do not let the
    # scheduler retry or treat it as an error condition.
    $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopIfGoingOnBatteries -AllowStartIfOnBatteries
    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
      -Settings $settings -Description 'Daily check for newly released NIKKEs' -Force | Out-Null
    "registered '$TaskName': daily 19:00, repo $Repo"
  }
  'unregister' {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    "removed '$TaskName'"
  }
  'status' {
    $t = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if (-not $t) { "'$TaskName' is not registered"; break }
    $i = Get-ScheduledTaskInfo -TaskName $TaskName
    "state      : $($t.State)"
    "last run   : $($i.LastRunTime)  result=$($i.LastTaskResult)"
    "next run   : $($i.NextRunTime)"
    "(LastTaskResult 0 = nothing new, 1 = new SSR found, 2 = the check failed)"
  }
}
```

- [ ] **Step 2: 등록·상태·해제 검증**

```bash
powershell -ExecutionPolicy Bypass -File scripts/schedule_new_nikke_check.ps1 -Action register
powershell -ExecutionPolicy Bypass -File scripts/schedule_new_nikke_check.ps1 -Action status
```

Expected: `registered ...` 출력 후 status가 `state : Ready`와 다음 실행 시각(내일 19:00 또는 오늘 19:00)을 보여준다.

**주의:** 등록은 메인 체크아웃에서 해야 한다. 워크트리에서 실행했다면 검증 후 반드시 `-Action unregister`로 해제하고, 최종 등록은 Fienn이 메인 체크아웃에서 수행하도록 보고한다.

- [ ] **Step 3: 로드맵 갱신**

`docs/roadmap.md`의 To-Do "디렉토리 스냅샷 갱신 루틴" 항목을 완료 표시하고, 다음 내용을 반영한다: 매일 19시 작업 스케줄러가 공개 디렉토리를 헤드리스로 받아 커밋된 스냅샷과 비교하며, 신규 SSR 또는 실패 시에만 토스트를 띄운다. 등록은 `scripts/schedule_new_nikke_check.ps1 -Action register`.

- [ ] **Step 4: 커밋**

```bash
git add scripts/schedule_new_nikke_check.ps1 docs/roadmap.md
git commit -m "feat(scripts): register the daily new-nikke check

Daily rather than Thursday-only: the patch interval is irregular and
maintenance can overrun, so aligning to Thursday risks missing a release for
a full week, while a daily run costs one page load and stays silent."
```

---

## Self-Review

**1. Spec coverage**

| 스펙 요구 | 태스크 |
|---|---|
| `collect.js --headless` (`--directory` 전용, 조합 거부, Chrome 경로 탐색·실패 시 나열) | Task 2 Step 1·3·4 |
| `corporation_sub_type` 승계 + `--deep` 한정 + 거짓 주석 수정 | Task 1, Task 2 Step 5·6 |
| `directory.js` 분리, `directory.test.js` 4가지 케이스 | Task 1 (승계됨 / 이전 없음 / 신규 미승계 / null 미부활 전부 포함) |
| `check_new_nikkes.py` 스크래치 경로, 리포 미변경, 보고 필드, SSR 한정 토스트 | Task 4 |
| 종료 코드 0/1/2 | Task 4 (테스트 3건) |
| `--offline` / `--dry-run` | Task 4 |
| `notify_toast.ps1`, 3명 초과 truncation, 실패 시 첫 줄 | Task 3, Task 4 |
| 실패 시 토스트 + `last-run.log` | Task 4 Step 3·6 |
| 작업 스케줄러 등록 스크립트, 매일 19시, 메인 체크아웃 | Task 5 |
| 온보딩 체크리스트를 출력으로 제공(새 문서 안 씀) | Task 4 `run()`의 안내 출력 |

빠진 요구 없음.

**2. Placeholder scan**

"TBD" / "적절히 처리" / "테스트를 작성하라"류 없음. 모든 코드 단계에 실제 코드가 있다. 단 Task 2 Step 1의 `const fs = require('fs')`는 구현자가 파일을 확인해야 하는 조건부 지시인데, 중복 선언 시 즉시 `SyntaxError`로 드러나므로 허용 가능한 확인 단계로 남긴다.

**3. Type consistency**

- Task 1이 export하는 이름(`nameOf` · `trimDirectory` · `carryOverSubTypes` · `missingSubTypeIds`)을 Task 2 Step 2의 require와 Step 5의 호출이 그대로 쓴다. ✅
- Task 2가 만드는 `launch()`를 Task 2 Step 4가 쓴다. ✅
- Task 3의 인자 이름 `-Title` / `-Body`를 Task 4의 `toast()`가 그대로 넘긴다. ✅
- Task 4의 `run(fresh_path, dry_run, notify)` 시그니처를 테스트 4건이 키워드로 호출한다. ✅
- Task 4가 만드는 `check_new_nikkes.py` 경로를 Task 5가 참조한다. ✅

**주의로 남기는 사항:** `test_run_offline_*`는 실제 커밋된 스냅샷을 읽는다. 병렬 세션이 스냅샷을 갱신해도 테스트는 "커밋된 것과 동일 → 0건" 관계만 단언하므로 깨지지 않는다. `resource_id: 999999`는 실제 니케와 충돌하지 않는 값으로 골랐다.
