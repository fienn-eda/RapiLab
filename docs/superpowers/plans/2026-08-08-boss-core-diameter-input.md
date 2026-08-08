# 보스 코어 지름 입력 — 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 실측한 보스 코어 지름이 회차 데이터 → 보스 카드 → 보스 폼 → 엔진까지
닿게 한다. 지금은 백엔드 끝단만 뚫려 있고 그 앞이 전부 비어 있다.

**Architecture:** 저장하는 값은 **엔진 단위**(환산은 판독하는 쪽 일), 원본 px와
해상도는 `stated`에 원문 기록으로, `range_band`는 안 건드린다. 폼에서는
「코어 피격 가능」이 켜졌을 때만 보이는 옵션 칸이고, 비어 있으면 `null`이라
오늘 동작과 1비트도 다르지 않다.

**Tech Stack:** Python 3.14.6 / pytest 9.1.1 / React + Vite + TypeScript / vitest

설계문서: `docs/superpowers/specs/2026-08-08-boss-core-diameter-input-design.md`
실측 근거: `docs/measurements/accuracy-circle-and-core-px.md`
브랜치: `wip/core-diameter-measurement` (실측 `858f26d0` · 설계 `b16e37b1`)

**기준선 (2026-08-08 실측):**
- 백엔드 `cd backend && python -m pytest -q` → **2082 passed** / 33초
  (반드시 `backend/`에서. 루트에서는 `No module named 'app'`으로 수집이 깨진다)
- 프론트 `cd frontend && npm test` → **601 passed / 61 files** / 35초

## Global Constraints

- **저장값은 엔진 단위.** 환산 `게임단위 = 화면px × (화면 가로 / 1920)`은 스킬이
  판독 시점에 한다. 앱은 해상도를 모른다.
- **`range_band`는 이 작업에서 읽지도 쓰지도 않는다.**
- **`scripts/raid_record.py`(`RECORD_BOSS`)를 건드리지 않는다** — 실기록에 켜는
  것은 별개 결정이다(`docs/decisions.md`).
- **빈 값 = `null` = 오늘 동작.** 0과 음수는 거부(백엔드 `Field(gt=0)`과 같은 경계).
- 주석·docstring은 한국어로 「무엇을·왜」만. 「예전엔 이랬다」를 쓰지 않는다.
- 커밋은 태스크마다 한 번씩.

## File Structure

| 파일 | 책임 | 변경 |
|---|---|---|
| `data/raid-rotations.json` | 회차 보스 사실 | 보스 6기에 `core_diameter_px: null` |
| `backend/app/raid_rotations.py` | 파일 검증 | 관용적 검증 1블록 |
| `backend/app/api.py` | 와이어 모델 | `RotationBoss`에 필드 1줄 |
| `backend/tests/test_raid_rotations.py` | 검증 규칙 못박기 | 테스트 3개 |
| `frontend/src/types/raidRotation.ts` | 회차 wire 타입 | 필드 1줄 |
| `frontend/src/types/recommend.ts` | 보스 wire 타입 | 필드 1줄 |
| `frontend/src/types/bossProfileDraft.ts` | draft·검증·왕복 | 헬퍼 1개 + 4곳 |
| `frontend/src/components/BossProfileField.tsx` | 입력 칸·카드 반영 | ~25줄 |
| `frontend/src/lib/helpText.ts` | 설명 문구 | 새 항목 1 + **기존 2건 정정** |
| `.claude/skills/update-raid-bosses/SKILL.md` | 판독 절차 | 절 1개 + 필드 설명 |

---

### Task 1: 회차 데이터가 코어 지름을 싣는다 (백엔드)

**Files:**
- Modify: `data/raid-rotations.json` (보스 6기)
- Modify: `backend/app/raid_rotations.py` (`validate_rotations`, 61-69행)
- Modify: `backend/app/api.py` (`RotationBoss`, 91-94행)
- Test: `backend/tests/test_raid_rotations.py`

**Interfaces:**
- Produces: 회차 보스 dict의 `core_diameter_px` 키 — `None` 또는 양수(엔진 단위).
  Task 2의 `RotationBoss` TS 타입이 이 이름과 타입을 그대로 미러링한다.

- [ ] **Step 1: 실패 테스트를 쓴다**

`backend/tests/test_raid_rotations.py` 맨 끝에 붙인다.

```python
def test_a_non_positive_core_diameter_is_rejected():
    # 0은 「코어가 없다」가 아니다 - 그건 BossProfile.core_hittable이 표현한다.
    # 여기 0이 들어오면 판독이 값을 못 읽고 자리만 채운 것이다.
    boss = [{"name": "보스", "weakness": "Iron", "range_band": None,
             "core_diameter_px": 0, "stated": {}}]
    with pytest.raises(ValueError, match="보스"):
        validate_rotations(a_doc(a_rotation(bosses=boss)))


def test_a_measured_core_diameter_is_allowed():
    boss = [{"name": "보스", "weakness": "Iron", "range_band": None,
             "core_diameter_px": 33.33, "stated": {}}]
    assert validate_rotations(a_doc(a_rotation(bosses=boss)))


def test_a_boss_with_no_core_diameter_key_is_allowed():
    # 코어는 재야만 존재하는 값이라 weakness/range_band와 성격이 다르다 - 안 잰
    # 보스의 dict에는 키 자체가 없을 수 있다. 번들 파일에 키가 빠지는 것은
    # test_api_raid_rotations.test_the_route_serves_the_file_as_is가 막는다.
    boss = [{"name": "보스", "weakness": "Iron", "range_band": None, "stated": {}}]
    assert validate_rotations(a_doc(a_rotation(bosses=boss)))
```

- [ ] **Step 2: 실패를 확인한다**

```bash
cd backend && python -m pytest tests/test_raid_rotations.py -q
```

기대: `test_a_non_positive_core_diameter_is_rejected`만 FAIL
(`DID NOT RAISE ValueError`). 나머지 둘은 검증기가 아직 이 키를 안 보므로 통과 —
정상이다. 그 둘은 회귀 방지용이고, 이 단계에서 빨간 것은 하나뿐이어야 한다.

- [ ] **Step 3: 검증을 추가한다**

`backend/app/raid_rotations.py`의 `validate_rotations` 안, `range_band` 검사
바로 뒤에 붙인다.

```python
            # 대괄호가 아니라 .get인 것은 의도다: 코어는 재야만 존재하는 값이라
            # 공지가 반드시 답을 주는 weakness/range_band와 성격이 다르다.
            # 번들 파일에 키가 빠지는 것은 라우트가 파일과 완전히 같은지 보는
            # test_the_route_serves_the_file_as_is가 막는다.
            core = boss.get("core_diameter_px")
            if core is not None and not (isinstance(core, (int, float)) and core > 0):
                raise ValueError(
                    f"{rid}/{boss['name']}: 코어 지름은 양수여야 한다 {core!r}")
```

모듈 docstring의 「기계가 읽는 필드는 보스마다 `weakness`와 `range_band` 둘이다」도
셋으로 고친다. 이어지는 문장(「둘 다 공지가 그 단어로 적은 것을…」)이 코어에는
해당하지 않으므로 한 문장을 덧붙인다:

```
기계가 읽는 필드는 보스마다 `weakness` · `range_band` · `core_diameter_px` 셋이다.
앞의 둘은 공지가 그 단어로 적은 것을 엔진 어휘로 옮긴 값이고, 판독 시점에 스킬이
채운다 — 앱이 `stated`의 한글 산문을 파싱하는 일은 없다. 코어 지름만 출처가
다르다: 공지에 없고 Fienn이 그 보스와 싸우며 화면에서 잰 값을 엔진 단위로 환산해
적는다(docs/measurements/accuracy-circle-and-core-px.md). 나머지(부위파괴·스쿼드
추천 등)는 대응이 확인되지 않아 `stated`에 원문 그대로만 남는다
(docs/superpowers/specs/2026-08-07-raid-boss-rotation-import-design.md D3).
```

- [ ] **Step 4: API 모델과 번들 파일**

`backend/app/api.py`의 `RotationBoss`에서 `range_band` 바로 아래에 붙인다.

```python
    # 그 보스와 싸우며 화면에서 잰 코어 지름을 엔진 단위로 환산한 값. 안 잰
    # 보스는 None이고, 그때 코어히트율은 모델링되지 않는다(적격 평타가 전부
    # p=1.0을 받는 지금 동작 그대로).
    core_diameter_px: float | None = None
```

`data/raid-rotations.json`의 보스 6기 전부에 `"core_diameter_px": null,`을
`range_band` 바로 뒤에 넣는다(solo-39의 아일랜드 이터 1기, union-2026-07-31의
선바스·플레이트·토커티브·리빌드 핑거즈·마테리얼 H 5기).

- [ ] **Step 5: 통과를 확인한다**

```bash
cd backend && python -m pytest tests/test_raid_rotations.py tests/test_api_raid_rotations.py -q
```

기대: 전부 PASS. `test_the_route_serves_the_file_as_is`가 통과한다는 것이
번들 파일 6기에 키가 다 들어갔다는 증거다 — 하나라도 빠뜨리면 여기서 걸린다.

- [ ] **Step 6: 스위트 전체**

```bash
cd backend && python -m pytest -q
```

기대: **2085 passed**(2082 + 3).

- [ ] **Step 7: 커밋**

```bash
git add data/raid-rotations.json backend/app/raid_rotations.py backend/app/api.py backend/tests/test_raid_rotations.py
git commit -F - <<'EOF'
회차 보스가 코어 지름을 싣는다 — 엔진 단위로 저장

공지에 없고 실측으로만 생기는 값이라 검증이 키 없음을 허용한다. 번들 파일의
완전성은 라우트가 파일과 완전히 같은지 보는 기존 테스트가 지킨다.
EOF
```

---

### Task 2: 프론트 타입과 검증 (화면 없이 값만)

**Files:**
- Modify: `frontend/src/types/raidRotation.ts` (`RotationBoss`, 13-22행)
- Modify: `frontend/src/types/recommend.ts` (`BossProfile`, 15-35행)
- Modify: `frontend/src/types/bossProfileDraft.ts`
- Test: `frontend/src/types/bossProfileDraft.test.ts`

**Interfaces:**
- Consumes: Task 1의 `core_diameter_px`(number|null) 이름과 타입
- Produces: `BossProfileDraft.core_diameter_px: string`(빈 문자열 = 안 잼),
  `BossProfile.core_diameter_px: number | null`. Task 3이 둘 다 쓴다.

- [ ] **Step 1: 실패 테스트를 쓴다**

`frontend/src/types/bossProfileDraft.test.ts` 맨 끝에 붙인다.

```typescript
describe('core diameter', () => {
  it('빈 칸은 오류가 아니라 null이다 — 안 잰 보스가 기본이다', () => {
    const draft = { ...makeDefaultBossProfileDraft(), core_diameter_px: '' }
    const { errors, value } = validateBossProfileDraft(draft)
    expect(errors.core_diameter_px).toBeUndefined()
    expect(value!.core_diameter_px).toBeNull()
  })

  it('양수는 숫자로 통과한다', () => {
    const draft = { ...makeDefaultBossProfileDraft(), core_diameter_px: '33.33' }
    expect(validateBossProfileDraft(draft).value!.core_diameter_px).toBe(33.33)
  })

  it('0과 음수는 거부한다 — 0은 「코어 없음」이 아니다', () => {
    for (const raw of ['0', '-1']) {
      const draft = { ...makeDefaultBossProfileDraft(), core_diameter_px: raw }
      expect(validateBossProfileDraft(draft).errors.core_diameter_px).toBeDefined()
    }
  })

  it('왕복해도 값이 남는다', () => {
    const draft = { ...makeDefaultBossProfileDraft(), core_hittable: true,
                    core_diameter_px: '58.67' }
    const { value: boss } = validateBossProfileDraft(draft)
    const restored = validateBossProfileDraft(bossProfileToDraft(boss!))
    expect(restored.value).toEqual(boss)
  })

  it('이 필드가 없던 시절 저장된 프로필도 복원된다', () => {
    const old = { ...validateBossProfileDraft(makeDefaultBossProfileDraft()).value! }
    delete (old as { core_diameter_px?: unknown }).core_diameter_px
    expect(bossProfileToDraft(old).core_diameter_px).toBe('')
  })
})
```

- [ ] **Step 2: 실패를 확인한다**

```bash
cd frontend && npm test -- bossProfileDraft
```

기대: 새 describe 블록이 전부 FAIL(타입에 필드가 없다 / `value.core_diameter_px`가
`undefined`).

- [ ] **Step 3: wire 타입 둘**

`frontend/src/types/raidRotation.ts`의 `RotationBoss`, `range_band` 바로 아래:

```typescript
  /** 그 보스와 싸우며 화면에서 잰 코어 지름을 엔진 단위로 환산한 값. 안 잰
   *  보스는 null이고, 그때 코어히트율은 모델링되지 않는다. */
  core_diameter_px: number | null
```

`frontend/src/types/recommend.ts`의 `BossProfile`, `effective_range_band` 주석
블록 뒤:

```typescript
  core_diameter_px: number | null // default null — 코어 지름(엔진 단위). 무기 탄착군과의
  // 면적비가 코어히트율을 정한다. null이면 모델링하지 않고 적격 평타가 전부 코어에
  // 든다고 본다(엔진이 오래 모델해 온 상한). core_hittable이 거짓이면 무시된다.
```

- [ ] **Step 4: draft 타입·기본값·검증·역변환**

`frontend/src/types/bossProfileDraft.ts`를 네 곳 고친다.

인터페이스에 (`effective_range_band` 위):
```typescript
  /** 빈 문자열 = 안 쟀다. 필수가 아니라서 다른 숫자 칸과 파싱 규칙이 다르다. */
  core_diameter_px: string
```

`makeDefaultBossProfileDraft`에:
```typescript
  core_diameter_px: '',
```

`BossProfileDraftErrors`에:
```typescript
  core_diameter_px?: string
```

`bossProfileToDraft`에 (`enemy_def` 근처):
```typescript
  // 이 필드가 생기기 전에 저장된 프로필은 undefined이고, null은 「안 쟀다」다.
  // 둘 다 빈 칸으로 돌아간다.
  core_diameter_px: boss.core_diameter_px == null ? '' : String(boss.core_diameter_px),
```

`parseFloatField` 바로 아래에 헬퍼를 새로 만든다 — `parseFloatField`는 빈 값을
오류로 보므로 재사용할 수 없다:

```typescript
/** 안 재도 되는 양수 칸. 빈 칸은 오류가 아니라 `null`이다. */
const parseOptionalPositive = (raw: string): ParsedNumber => {
  const trimmed = raw.trim()
  if (trimmed === '') return {}
  const value = Number(trimmed)
  if (!Number.isFinite(value)) return { error: '숫자를 입력하세요' }
  if (value <= 0) return { error: '0보다 커야 해요' }
  return { value }
}
```

`validateBossProfileDraft`의 `fightDuration` 검사 뒤:
```typescript
  const coreDiameter = parseOptionalPositive(draft.core_diameter_px)
  if (coreDiameter.error) errors.core_diameter_px = coreDiameter.error
```

그리고 `value` 객체에:
```typescript
    core_diameter_px: coreDiameter.value ?? null,
```

- [ ] **Step 5: 통과를 확인한다**

```bash
cd frontend && npm test -- bossProfileDraft
```

기대: 전부 PASS.

- [ ] **Step 6: 타입 체크와 스위트 전체**

```bash
cd frontend && npx tsc -b --noEmit && npm test
```

기대: 타입 에러 0. 다른 테스트 파일이 `BossProfile` 리터럴을 만드는 자리가 여럿
있으므로(`DeckCard.test.tsx`, `useRecommend.test.ts` 등) **여기서 컴파일이 깨지면
그 리터럴들에 `core_diameter_px: null`을 채워 넣는다** — 필드를 옵셔널로 바꿔
피하지 말 것. `BossProfile`은 백엔드 계약의 거울이고 옵셔널로 두면 빠뜨린 자리를
타입이 못 잡는다.

- [ ] **Step 7: 커밋**

```bash
git add frontend/src/types frontend/src
git commit -F - <<'EOF'
프론트 타입이 코어 지름을 안다 — 빈 칸은 오류가 아니라 null

안 재도 되는 칸이라 parseFloatField(빈 값 = 필수 오류)를 재사용하지 않고
parseOptionalPositive를 따로 뒀다. 0과 음수는 거부한다 - 0은 「코어 없음」이
아니고 그건 core_hittable이 표현한다.
EOF
```

---

### Task 3: 입력 칸과 카드 반영

**Files:**
- Modify: `frontend/src/components/BossProfileField.tsx`
- Test: `frontend/src/components/BossProfileField.test.tsx`

**Interfaces:**
- Consumes: Task 2의 `BossProfileDraft.core_diameter_px: string`,
  `BossProfileDraftErrors.core_diameter_px`, `RotationBoss.core_diameter_px`

- [ ] **Step 1: 실패 테스트를 쓴다**

`frontend/src/components/BossProfileField.test.tsx` 맨 끝에 붙인다. 이 파일의
관용구를 따른다: `userEvent.setup()` → `user.click(...)`, 기본 draft가 아닐
때는 `render(<BossProfileField value={{...}} onChange={vi.fn()} />)`를 인라인으로.

```tsx
describe('BossProfileField 코어 지름', () => {
  it('코어 피격이 꺼져 있으면 칸이 없다', () => {
    render(<BossProfileField value={makeDefaultBossProfileDraft()} onChange={vi.fn()} />)

    expect(screen.queryByLabelText(/코어 지름/)).not.toBeInTheDocument()
  })

  it('코어 피격을 켜면 칸이 나온다', () => {
    render(
      <BossProfileField
        value={{ ...makeDefaultBossProfileDraft(), core_hittable: true }}
        onChange={vi.fn()}
      />,
    )

    expect(screen.getByLabelText(/코어 지름/)).toBeInTheDocument()
  })

  it('코어 피격을 끄면 값도 지운다 — 폼에 모순 상태를 만들지 않는다', async () => {
    // 값을 남겨 두면 화면에서 사라진 칸이 계산에는 남는다.
    const user = userEvent.setup()
    const onChange = vi.fn()
    render(
      <BossProfileField
        value={{ ...makeDefaultBossProfileDraft(), core_hittable: true,
                 core_diameter_px: '33.33' }}
        onChange={onChange}
      />,
    )

    await user.click(screen.getByLabelText('코어 피격 가능'))

    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ core_hittable: false, core_diameter_px: '' }),
    )
  })
})
```

카드가 코어를 얹는지도 확인한다. 이 파일에는 이미 `RaidRotation` 픽스처를 쓰는
회차 카드 테스트가 있으므로(`import type { RaidRotation }`) 그 픽스처를 그대로
쓰되 보스에 `core_diameter_px: 33.33`을 준다. 카드를 누르면 `onChange`가
`core_diameter_px: '33.33'`과 `core_hittable: true`를 **함께** 받아야 한다 —
코어 피격을 같이 켜지 않으면 엔진이 값을 무시해 카드를 눌러도 아무 일이 없다.

- [ ] **Step 2: 실패를 확인한다**

```bash
cd frontend && npm test -- BossProfileField
```

기대: 새 describe가 FAIL(칸이 없다).

- [ ] **Step 3: 입력 칸을 그린다**

`BossProfileField.tsx`의 「코어 피격 가능」 체크박스 `div.checkbox-row` 바로
뒤에 넣는다.

```tsx
      {value.core_hittable && (
        <NumberField
          label="코어 지름"
          hint="엔진 단위"
          value={value.core_diameter_px}
          error={errors?.core_diameter_px}
          min={0}
          help={HELP.boss.coreDiameter}
          onChange={(core_diameter_px) => onChange({ ...value, core_diameter_px })}
        />
      )}
```

`core_hittable` 체크박스의 `onChange`에 한 줄을 더한다 —
`pierce_hits_body_behind_core`가 이미 같은 자리에서 같은 이유로 꺼진다:

```tsx
                // 코어를 못 때리면 크기도 의미가 없다. 값을 남겨 두면 화면에서
                // 사라진 칸이 계산에는 남는다.
                core_diameter_px: event.target.checked ? value.core_diameter_px : '',
```

`pickRotationBoss`에 한 줄:
```tsx
      core_diameter_px:
        boss.core_diameter_px === null ? '' : String(boss.core_diameter_px),
      core_hittable: boss.core_diameter_px !== null,
```

`core_hittable`을 같이 켜는 이유를 주석으로 적는다 — 코어 지름이 적혀 있다는
것은 그 보스를 코어로 때릴 수 있다는 뜻이고, 켜지 않으면 엔진이 값을 무시해
카드를 눌러도 아무 일이 없다.

- [ ] **Step 3b: 이 변경이 거짓으로 만드는 도움말 둘을 고친다**

`frontend/src/lib/helpText.ts`의 `HELP.boss`에서 **기존 문구 두 개가 이 작업으로
틀린 말이 된다.** 새 항목을 넣기 전에 그 둘을 먼저 고친다.

`coreHittable`(35-36행) — 「모든 평타가 코어에 명중한다고 가정」은 코어 지름을
비워 뒀을 때만 참이 된다:

```typescript
    coreHittable:
      '보스에 코어가 있어요. 코어 지름을 비워 두면 **모든 평타가 코어에 명중한다고 가정**하고, 평타 비중이 큰 유닛이 실제보다 높게 평가될 수 있어요.',
```

`rotationPicker`(31-32행) — 회차 카드가 이제 셋을 채운다:

```typescript
    rotationPicker:
      '회차 보스를 고르면 **약점 속성과 적정거리**가 채워지고(코어 지름이 기록돼 있으면 코어 설정도 함께), **나머지 보스 설정은 전부 기본값으로 되돌아가요.**',
```

그리고 새 항목을 `corePierce` 앞에 넣는다:

```typescript
    coreDiameter:
      '코어와 **탄착군의 면적비**가 평타의 코어 명중률을 정해요. 명중률 버프가 탄착군을 좁혀서, 이 값이 있으면 명중 스탯이 실제로 계산에 들어와요. 비워 두면 모든 평타가 코어에 맞는다고 봐요. 화면 픽셀이 아니라 **엔진 단위**로 적은 실측값이에요.',
```

`HELP`의 기존 문체(해요체 + `**강조**`)를 그대로 따른다. 두 수정은 이 태스크의
커밋에 함께 들어간다 — 코드와 같은 사실을 말하는 문장이라 따로 커밋하면 그
사이 커밋에서 화면이 거짓말을 한다.

- [ ] **Step 4: 통과를 확인한다**

```bash
cd frontend && npm test -- BossProfileField
```

기대: 전부 PASS.

- [ ] **Step 5: 프론트 스위트 전체 + 타입**

```bash
cd frontend && npx tsc -b --noEmit && npm test && npm run lint
```

기대: 전부 통과.

- [ ] **Step 6: 앱을 띄워서 눈으로 본다**

CSS 결함은 테스트가 못 잡는다(`vitest`가 `css: false`). `/run` 스킬 또는
`docs/insights.md`의 로컬 개발 절차(Vite :5173 → FastAPI :8000 프록시)로 띄워
확인할 것:
- 「코어 피격 가능」이 꺼져 있을 때 칸이 안 보이고, 켜면 나타난다
- 칸에 `0`을 넣으면 오류 문구가 뜨고 제출이 막힌다
- 레이아웃이 깨지지 않는다(체크박스 줄들 사이에 숫자 칸이 끼어드는 자리다)

- [ ] **Step 7: 커밋**

```bash
git add frontend/src
git commit -F - <<'EOF'
보스 폼이 코어 지름을 받는다 — 코어 피격을 켰을 때만

엔진이 core_hittable이 거짓이면 이 값을 무시하므로 칸도 그때만 그린다. 체크를
끄면 값을 지워 화면에서 사라진 칸이 계산에 남지 않게 한다. 회차 카드가 코어를
싣고 있으면 코어 피격도 같이 켠다 - 안 켜면 값이 무시돼 카드를 눌러도 아무
일이 없다.
EOF
```

---

### Task 4: 스킬이 코어를 묻는다

**Files:**
- Modify: `.claude/skills/update-raid-bosses/SKILL.md`

- [ ] **Step 1: 3단계(사람 확인)에 묻는 절을 넣는다**

현재 3단계는 「판독 결과를 표로 보여주고 확인받는다」 한 줄이다. 여기에 코어를
묻는 대목을 더한다. 핵심은 **안 물으면 영영 안 들어온다**는 것 — 공지에 없으므로
판독으로는 절대 안 나온다. Fienn이 값을 안 주면 `null`로 두고 넘어간다.

- [ ] **Step 2: 4단계 필드 목록에 `core_diameter_px`를 추가한다**

`range_band` 항목 바로 뒤에 넣는다. 적을 것:

- 이 값만 **공지가 아니라 실측**에서 온다. 판독으로 채우지 않는다.
- 환산: **게임단위 = 화면px × (화면 가로 해상도 / 1920)**. 게임 데이터의
  `accuracy_circle_scale`이 1920×1080 화면 픽셀이기 때문이다
  (`docs/measurements/accuracy-circle-and-core-px.md`). 2560×1440이면 ×4/3.
- **환산한 값을 적는다.** 한글 거리를 `near`로 옮기는 것과 같은 이유 — 옮기는
  것은 판독하는 쪽 일이다.
- 원본은 `stated`에 `"코어 측정": "25px @2560x1440"` 형태로 남긴다.
- 안 잰 보스는 `null`. **키는 반드시 적는다** —
  `test_the_route_serves_the_file_as_is`가 파일과 응답의 완전 일치를 본다.
- **`range_band`를 여기서 유추하지 않는다.** 코어를 그 보스와 싸우며 재면 거리는
  자동으로 맞으므로 밴드를 따로 적을 이유가 없고, `range_band`는 평타에 +30%를
  붙이는 값이라 근거 없이 채우면 비싸다.

- [ ] **Step 3: 「번역하지 않는 것」 절에 예외를 명시한다**

그 절의 규칙(「공지가 그 단어로 적지 않은 것은 채우지 않는다」)과 코어가 겉보기
충돌하므로, 왜 충돌이 아닌지를 한 문단으로 적는다: 그 규칙이 막는 것은 공지의
다른 항목에서 **없는 근거를 유추**하는 것이고(「스쿼드 추천: 머신건」 →
`range_band: mid`), 코어는 Fienn이 화면에서 잰 관측값이라 유추가 아니다.

- [ ] **Step 4: 검증**

스킬 문서는 코드가 아니므로 테스트가 없다. 대신 **문서가 가리키는 사실이 맞는지**
확인한다:

```bash
cd backend && python -m pytest tests/test_raid_rotations.py tests/test_api_raid_rotations.py -q
```

그리고 4단계에 적은 환산식이 실측 문서의 식과 글자 그대로 같은지 대조한다.

- [ ] **Step 5: 커밋**

```bash
git add .claude/skills/update-raid-bosses/SKILL.md
git commit -F - <<'EOF'
스킬이 코어 지름을 묻는다 — 공지에 없으니 안 물으면 안 들어온다

판독으로는 절대 안 나오는 값이라 사람 확인 단계에서 묻는다. 「공지에 없는 것을
채우지 않는다」와 충돌하지 않는 이유(유추가 아니라 관측)를 그 절에 적었다.
EOF
```

---

## 완료 조건

- `cd backend && python -m pytest -q` → **2085 passed**, 0 failed
- `cd frontend && npx tsc -b --noEmit && npm test && npm run lint` → 전부 통과
- 앱을 띄워 칸이 보이고/숨고/오류를 내는 것을 눈으로 확인
- `data/raid-rotations.json`의 보스 6기 전부에 `core_diameter_px` 키가 있다
- `scripts/raid_record.py`는 변경 없음(`git diff`로 확인)
