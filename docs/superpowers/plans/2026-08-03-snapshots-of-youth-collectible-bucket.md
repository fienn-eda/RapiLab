# 청춘의 기록 복구와 소장품 버킷 통합 — 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 아르카나: 포츈메이트의 Snapshots of Youth(청춘의 기록)를 되살리고, SG·SMG 소장품이 올리는 「일반 공격 대미지 배율」을 그것과 같은 가산 버킷으로 옮긴다.

**Architecture:** 인게임에서 두 소스는 **같은 스탯 이름**을 올린다(`damage-formula-reference.md:75`). 엔진은 소장품 쪽만 무기 스탯을 곱하는 자리에 두어 둘이 곱셈으로 붙어 있었다. 소장품을 `normal_attack_damage_multiplier` 영구 self Effect로 옮기면 `raid_simulator._normal_attack_percent`의 `1 + Σ`가 곧 가산 버킷이 된다. 그 위에서 청춘의 기록은 스킬 데이터 슬롯의 10%를 그대로 쓰면 된다.

**Tech Stack:** Python 3.13, pytest, 기존 `ResourceSpec` / `Effect` / `linear_resource_buff`

## Global Constraints

- **두 수정은 한 커밋에 간다.** 어느 한쪽만 적용하면 그녀의 3스택 데미지가 2.0% 틀어진다 — 소장품만 옮기면 `1+0.0946+0.091354×3 = 1.368662`(1.9% 미달), 청춘의 기록만 살리면 `1.0946×1.3 = 1.42298`(2.0% 과대). 정답은 `1+0.0946+0.3 = 1.3946`.
- **RL·SR의 `charge_damage_percent` 매핑(711301·712301)은 건드리지 않는다.** 에이드: 에이전트 바니 사격장 판독 7개가 그 배치를 확정했고, 그 계열에는 같은 버킷을 쓰는 스킬 소스가 아직 없다.
- **방어 스탯 슬롯은 계속 `None`이다.** 매핑 표의 두 번째 자리(방어력)와 `712002`는 그대로 둔다.
- 근거 문서: `docs/superpowers/specs/2026-08-03-snapshots-of-youth-collectible-bucket-design.md`
- 실측 기준값: 소장품 15레벨 SG = **9.46%** → 배율 1.0946, 스택당 한계효과 `0.1/1.0946 = 0.0913576`. Fienn의 2026-07-28 판독 첫 스택 기울기 **0.0913573**.

---

## File Structure

| 파일 | 책임 | 변경 |
| --- | --- | --- |
| `backend/app/collectible_effects.py` | 소장품 → 엔진 스탯 | `COLLECTIBLE_SKILL_STATS`의 SG·SMG 4항목 배치 변경 + 배치 규칙 주석 |
| `backend/app/skill_rules/arcana_fortune_mate.py` | 그녀의 스킬 인코딩 | 자원 이름·값 교체, 피팅 상수 삭제, 독스트링 재작성 |
| `backend/app/roster.py` | 패시브 조립 | `_passive_effects` 독스트링 정정 (배율이 전부 무기 스탯으로 가지는 않는다) |
| `backend/app/user_roster.py` | 무기 스탯 조립 | 같은 이유의 주석 정정 |
| `backend/tests/test_collectible_effects.py` | 소장품 해석기 테스트 | SG tid 핀 + 배치 테스트 추가 |
| `backend/tests/test_skill_rules_arcana_fortune_mate.py` | 그녀의 인코딩 테스트 | 자원 테스트 교체, 결정적 통합 테스트 추가, 헬퍼에 `extra_rules` |
| `docs/encoded-nikkes.md` · `docs/engine-gaps.md` | 지식 베이스 | 완성도·갭 갱신 |

---

## Task 1: 소장품과 청춘의 기록을 하나의 가산 버킷으로

**Files:**
- Modify: `backend/app/collectible_effects.py:52-80`
- Modify: `backend/app/skill_rules/arcana_fortune_mate.py:21-82, 100-117, 168-194`
- Modify: `backend/app/roster.py:71-75`
- Modify: `backend/app/user_roster.py:107-109`
- Test: `backend/tests/test_collectible_effects.py`
- Test: `backend/tests/test_skill_rules_arcana_fortune_mate.py`

**Interfaces:**
- Consumes: `collectible_modifiers(tid, level, source_slug, weapon) -> (dict[str, float], list[Effect])`, `skill_percents(record, item_level, is_favorite) -> dict[tuple[str, str], float]`, `Effect(stat, value, scope, duration, source_slug)`, `roster._battle_start_effects_rule(effects) -> SkillRule`
- Produces: 자원 이름이 `"happy_memories"` → **`"snapshots_of_youth"`**. 모듈 상수 `HAPPY_MEMORIES_DAMAGE_PER_STACK`은 **사라진다**. `HAPPY_MEMORIES_FIRST`(=4)와 `ROTATION_PERIOD`(=6)는 로테이션 스텝을 가리키는 이름이므로 **그대로 남는다**. 테스트 헬퍼 `arcana_deck_result(fight_duration=40.0, extra_rules=())`.

- [ ] **Step 1: 기준선을 기록한다**

Run: `cd backend && python -m pytest -q`

기대: `1788 passed, 3 skipped` 부근. **실제로 나온 수를 적어둔다** — 마지막 단계에서 이 수보다 줄면 안 된다.

> 앱이 켜져 있으면 `test_pick_port_steps_past_one_that_is_taken`이 포트 충돌로 깨진다. 회귀가 아니라 환경 요인이니, 그 하나만 실패하면 앱을 끄고 다시 돌린다.

그리고 **코드를 고치기 전에** 추천 구성을 떠 둔다. Task 2가 이 파일을 새 코드로 다시 채점해서 「추천이 나빠졌나, 점수만 바뀌었나」를 가른다 — 변경 후에는 이 스냅샷을 만들 수 없다.

```bash
python scripts/measure_engine_change_delta.py --dump "$CLAUDE_JOB_DIR/tmp/before-snapshots-bucket.json"
```

> `$CLAUDE_JOB_DIR/tmp`는 여러 세션이 함께 쓰는 스크래치패드다. 위 파일명 그대로 쓰고, 그 안의 다른 파일은 지우거나 덮어쓰지 않는다.

- [ ] **Step 2: 소장품 배치 테스트를 쓴다 (실패해야 한다)**

`backend/tests/test_collectible_effects.py`의 핀 상수 블록(`R_SR_COLLECTIBLE_TID = 100601` 다음 줄)에 tid를 하나 더 핀하고, `test_ades_charge_damage_matches_her_range_test` 바로 앞에 테스트 둘을 넣는다.

```python
SG_COLLECTIBLE_TID = 100402   # SR rarity, SG group - 포츈메이트가 실제로 낀 것


def test_the_pinned_sg_collectible_tid_is_still_in_the_committed_table():
    from app.stat_assembly import load_stat_tables

    table = load_stat_tables()["collectibles"]
    assert table[str(SG_COLLECTIBLE_TID)]["weapon_type"] == "SG"
    assert table[str(SG_COLLECTIBLE_TID)]["favorite_rare"] == "SR"


def test_an_sg_collectible_grants_the_normal_attack_multiplier_not_a_weapon_scale():
    """SG·SMG 소장품이 올리는 것은 「일반 공격 대미지 배율」이고, 그것은 청춘의
    기록 같은 스킬이 주는 것과 **같은 스탯**이다(damage-formula-reference.md:75).
    같은 스탯이면 같은 가산 버킷에 들어가야 한다 - 무기 스탯을 따로 곱하면 두
    소스가 곱셈으로 붙어 포츈메이트 실측(스택당 0.0913573)과 0.87% 어긋난다."""
    weapon_multipliers, effects = collectible_modifiers(
        SG_COLLECTIBLE_TID, 15, "arcana-fortune-mate", weapon="SG")

    assert weapon_multipliers == {}
    assert [(e.stat, round(e.value, 6), e.scope, e.duration) for e in effects] == [
        ("normal_attack_damage_multiplier", 0.0946, "self", None)]
```

- [ ] **Step 3: 실패를 확인한다**

Run: `cd backend && python -m pytest tests/test_collectible_effects.py -q -k "sg_collectible"`
기대: FAIL — `assert {'damage_percent': 1.0946} == {}`

- [ ] **Step 4: 청춘의 기록 자원 테스트를 쓴다 (실패해야 한다)**

`backend/tests/test_skill_rules_arcana_fortune_mate.py:236-246`의 `test_happy_memories_carries_the_cap_and_the_full_burst_end_reset`을 통째로 아래로 **교체**한다(뒤따르는 `precious = ...` 블록은 그대로 둔다).

```python
def test_snapshots_of_youth_carries_the_cap_and_the_full_burst_end_reset():
    snapshots = next(s for s in build_memories_and_moments_resources({
        "memories_and_moments": MEMORIES_AND_MOMENTS, "keepsake_album": KEEPSAKE_ALBUM,
    }) if s.name == "snapshots_of_youth")
    # 「Happy Memories가 발동할 때」 붙으므로 채움은 로테이션의 HM 스텝과 같고,
    # 「Full Burst 종료 시 Snapshots of Youth 제거」가 리셋이다. 상한과 리셋이
    # 4번째 로테이션 스텝(22번째 평타 - Tove를 앉힌 Fienn이 도달한 지점)을 4번째
    # 스택으로 만들지 않게 막고, 창 사이에 카운터를 비운다.
    assert snapshots.cap == 3
    assert snapshots.resets == [{"trigger": "full_burst_end", "value": 0}]
    assert snapshots.fill == ("per_shot_cycle_in_own_status_window", 4, 6, FULL_BURST_DURATION)
    # 값은 스킬 데이터 슬롯에서 온다 - 피팅된 상수가 아니다.
    assert round(snapshots.buffs[0].value_fn(3), 6) == 0.3
```

`HAPPY_MEMORIES_DAMAGE_PER_STACK` import는 **아직 지우지 않는다** — 200줄이 그 이름을 아직 쓰고 있어서, 지금 지우면 모듈이 중간 상태로 깨진다. Step 11에서 둘을 같이 정리한다.

- [ ] **Step 5: 실패를 확인한다**

Run: `cd backend && python -m pytest tests/test_skill_rules_arcana_fortune_mate.py -q -k "snapshots_of_youth"`
기대: FAIL — `StopIteration` (아직 `snapshots_of_youth`라는 자원이 없다)

- [ ] **Step 6: 결정적 통합 테스트를 쓴다 (실패해야 한다)**

먼저 `arcana_deck_result` 헬퍼(같은 파일 161줄)가 규칙을 더 받을 수 있게 시그니처를 바꾼다.

```python
def arcana_deck_result(fight_duration=40.0, extra_rules=()):
```

그리고 그 안의 `rules_by_slug` 인자를 이렇게 바꾼다.

```python
        {"ally-b1": [], "sg-ally": [],
         "arcana-fortune-mate": build_fortune_mate_rules(values) + list(extra_rules)},
```

파일 끝에 테스트를 추가한다.

```python
def test_snapshots_stacks_additively_with_the_sg_collectible_bucket():
    """Fienn의 2026-07-28 사격장 판독을 재현한다. 소장품이 이미 9.46%를 넣어 둔
    버킷에 청춘의 기록 +10%가 가산되면 스택당 한계효과는 0.1/1.0946 = 0.0913576이고,
    실측 첫 스택 기울기가 0.0913573이었다. 두 소스가 곱셈으로 붙으면 1.1이 나오는데
    그것은 실측과 0.87% 어긋난다 - 그 0.87%가 이 테스트가 지키는 값이다."""
    from app.effects import Effect
    from app.roster import _battle_start_effects_rule

    collectible = Effect("normal_attack_damage_multiplier", 0.0946, "self",
                         None, "arcana-fortune-mate")
    result = arcana_deck_result(
        extra_rules=[_battle_start_effects_rule([collectible])])
    in_window = [e for e in her_normal_attacks(result) if 5.0 <= e["time"] < 15.0]

    def step(n):
        return in_window[n - 1]["damage"] / in_window[n - 2]["damage"]

    assert round(step(4), 7) == round(1.1946 / 1.0946, 7)
    assert round(step(10), 7) == round(1.2946 / 1.1946, 7)
    assert round(step(4), 4) != 1.1
```

- [ ] **Step 7: 실패를 확인한다**

Run: `cd backend && python -m pytest tests/test_skill_rules_arcana_fortune_mate.py -q -k "additively"`
기대: FAIL — `step(4)`가 `1.0913576`이 아니라 **`1.0834587`**로 나온다. 그것이 `(1 + 0.0946 + 0.091354) / 1.0946`, 즉 피팅된 상수를 소장품 버킷 위에 한 번 더 얹은 값이다.

- [ ] **Step 8: 소장품 매핑을 옮긴다**

`backend/app/collectible_effects.py`의 네 줄을 바꾼다.

```python
    711501: [("normal_attack_damage_multiplier", "effect"), None],  # 일반 공격 대미지 배율 (SG)
    711901: [("normal_attack_damage_multiplier", "effect"), None],  # 일반 공격 대미지 배율 (SMG)
```
```python
    712501: [("normal_attack_damage_multiplier", "effect"), None],  # 일반 공격 대미지 배율 (SG)
    712901: [("normal_attack_damage_multiplier", "effect"), None],  # 일반 공격 대미지 배율 (SMG)
```

같은 파일의 배치 설명 주석(`#   "weapon" - a 배율:` 문단) 아래에 왜 SG·SMG만 다른 자리로 가는지를 적는다.

```python
#
# 배율이라고 전부 "weapon"은 아니다. 무엇이 결정하느냐는 **게임이 그 스탯을 뭐라
# 부르느냐**다. SG·SMG의 「일반 공격 대미지 배율」은 스킬이 주는
# Normal Attack Damage Multiplier와 같은 이름이고, 같은 이름은 같은 가산 버킷을
# 뜻한다 - 그래서 "effect"로 가서 registry의 1 + Σ 안에 들어간다. RL·SR의 차지
# 대미지에는 그 버킷을 함께 쓰는 스킬 소스가 없어 "weapon"으로 남는다.
```

- [ ] **Step 9: 청춘의 기록을 복구한다**

`backend/app/skill_rules/arcana_fortune_mate.py`:

상수 블록(100~117줄)을 이렇게 만든다.

```python
MAKING_MEMORIES_STATUS = "making_memories"
PRECIOUS_MOMENTS_RESOURCE = "precious_moments"
SNAPSHOTS_RESOURCE = "snapshots_of_youth"

# The rotation: one effect per 2nd normal attack, three effects in order, so
# each lands every 6th normal starting at its own step. The reload phase (step
# 2) has no engine representation - see the docstring's deferred note.
ROTATION_PERIOD = 6
HAPPY_MEMORIES_FIRST = 4
PRECIOUS_MOMENTS_FIRST = 6
```

`build_memories_and_moments_resources`의 두 번째 `ResourceSpec`을 이렇게 바꾼다.

```python
        ResourceSpec(
            name=SNAPSHOTS_RESOURCE,
            # Snapshots of Youth is granted "when Happy Memories takes effect",
            # so it rides the Happy Memories rotation step 1:1 and shares its
            # cap. Full Burst's end removes it, hence the reset.
            fill=("per_shot_cycle_in_own_status_window",
                  HAPPY_MEMORIES_FIRST, ROTATION_PERIOD, FULL_BURST_DURATION),
            cap=int(float(keepsake["description_value_04"])),
            buffs=[linear_resource_buff(
                "normal_attack_damage_multiplier",
                float(keepsake["description_value_03"]) / 100, "self")],
            resets=[{"trigger": "full_burst_end", "value": 0}],
        ),
```

그리고 모듈 독스트링의 `RANGE-TESTED` 블록(44~69줄)을 통째로 아래로 바꾼다.

```
RANGE-TESTED (Fienn, 2026-07-28 - Tove + her + Dorothy: Serendipity + Drake
(favorite item) + Solin: Frost Ticket, non-crit per-pellet readings)
--------------------------------------------------------------------
Reading CONSECUTIVE pairs isolates one stack gain at a time, cancelling ATK and
every deck buff:

- Precious Moments is exactly what the data slot says. The three PM steps read
  1.009247 / 1.009164 / 1.009080, and ATK +2.49% into one additive bucket
  reproduces all three from a single fitted bucket total, to 0.007%.
- Snapshots of Youth lands at 0.0913573 per stack, not 0.1, because her SG
  COLLECTIBLE already holds 9.46% of the same "일반 공격 대미지 배율" bucket:
  0.1 / 1.0946 = 0.0913576. The readings pick her collectible rung out of the
  ladder's four - 4.73/6.30/7.88/9.46 predict 0.0955/0.0941/0.0927/0.0914 and
  only the last is within reading precision.
- Happy Memories' pellet does NOT add shot damage. Per-pellet damage falls by
  exactly the pellet-count ratio (1.091357/1.1 = 0.992143, measured 0.992143;
  same at 2 and 3 stacks), i.e. the same shot total is split across more
  pellets. Pellet count buys hit consistency and core coverage, not damage -
  which is why the engine having no per-pellet model costs nothing here.
```

`Modeled (DPS-relevant)` 목록의 Keepsake Album 줄에 Snapshots를 더한다.

```
- Keepsake Album (skills[0]): when Full Burst ends, all shotgun-wielding allies
  (exact SG member filter, self included) gain flat ATK = 13% of the caster's
  ATK PER Precious Moments stack, for 15 sec. Clears the `making_memories`
  status so the next cycle's burst re-arms it. Also grants Snapshots of Youth
  (Normal Attack Damage Multiplier +10%, cap 3) each time Happy Memories fires.
```

`Not modeled / deferred` 목록에 한 줄을 더한다.

```
- Happy Memories' pellet count itself: it moves no damage (see above), and the
  engine has no per-pellet shotgun model to hang hit-consistency on.
```

- [ ] **Step 10: 헛도는 배관 주석 둘을 고친다**

`backend/app/roster.py:71-75`의 `_passive_effects` 독스트링에서 배율에 대한 문장을 이렇게 바꾼다.

```python
    """Overload, this unit's harmony cube, and the collectible it actually has
    equipped. A collectible's charge-damage 배율 is NOT here - it scales a
    weapon stat and is applied in user_roster - but its normal-attack 배율 IS,
    because that one shares a buff bucket with skills. A cube that hands back
    rounds instead of moving a stat contributes nothing here - see the weapon
    stats below."""
```

`backend/app/user_roster.py:107-109`의 주석을 이렇게 바꾼다.

```python
    # A collectible's charge-damage 배율 scales the WEAPON's own base stat, so
    # it lands here rather than in the buff registry - and after any mode
    # override, so a unit whose weapon profile swaps mid-kit still carries it.
    # Its normal-attack 배율 goes to the buff registry instead (collectible_effects).
```

- [ ] **Step 11: 남은 기존 테스트를 맞춘다**

`backend/tests/test_skill_rules_arcana_fortune_mate.py:200`을 바꾸고, 5번째 줄의 `HAPPY_MEMORIES_DAMAGE_PER_STACK,` import 줄을 지운다. 둘은 같이 움직여야 한다 — 이 편성에는 소장품이 없으므로 한계효과가 곧 슬롯값 0.1이다.

```python
    h, p = 0.1, 0.0249
```

같은 파일 217줄의 테스트 이름과 224줄 주석을 바꾼다.

```python
def test_keepsake_album_reads_the_live_stack_count_and_snapshots_is_wiped():
```
```python
    # further x1.1, and the old per-cycle model as 13% x 1 instead of x 2.
```

- [ ] **Step 12: 전체 통과를 확인한다**

Run: `cd backend && python -m pytest -q`
기대: Step 1에 적어둔 수 **이상**, 실패 0. 새 테스트 3개가 늘어 있어야 한다.

- [ ] **Step 13: 중복 정의 검사를 돌린다**

Run: `cd backend && python -m pytest tests/test_no_duplicate_definitions.py -q`
기대: PASS. 상수를 지우고 이름을 바꿨으므로 잔재가 없는지 확인한다.

- [ ] **Step 14: 커밋**

```bash
git add backend/app/collectible_effects.py backend/app/skill_rules/arcana_fortune_mate.py \
        backend/app/roster.py backend/app/user_roster.py \
        backend/tests/test_collectible_effects.py \
        backend/tests/test_skill_rules_arcana_fortune_mate.py
git commit -m "Put SG/SMG collectibles and Snapshots of Youth in one additive bucket"
```

---

## Task 2: 5덱 합계와 캘리브레이션을 다시 잰다

**Files:**
- Modify: `docs/measurements/` 아래 기존 캘리브레이션 기록이 있으면 그것, 없으면 이 태스크는 수치를 보고만 한다

**Interfaces:**
- Consumes: Task 1이 끝난 엔진
- Produces: 새 5덱 합계와 캘리브레이션 배수. 다음 태스크의 문서에 들어갈 숫자.

- [ ] **Step 1: 캘리브레이션 표를 뽑는다**

Run: `python scripts/measure_record_calibration.py`

기대: 합계 배수가 **거의 안 움직인다**. `0.091354`가 소장품 15레벨 조건에 맞춰 피팅된 값이라 그녀의 총딜이 그 투자 수준에서는 1e-5 안에서 같기 때문이다. 움직이지 않는 것이 **이 태스크의 성공**이다 — 움직이면 Task 1이 뭔가 더 건드린 것이다.

- [ ] **Step 2: 추천이 바뀌었는지 본다**

Task 1 Step 1에서 떠 둔 구성을 새 코드로 다시 채점한다.

```bash
python scripts/measure_engine_change_delta.py --score "$CLAUDE_JOB_DIR/tmp/before-snapshots-bucket.json"
```

기대: `deck_search._prior`가 SG·SMG 유닛에 대해 소폭 내려가므로 탐색 경로가 달라질 수 있다. `_prior`는 라운드 0 시드 전용이고 swap 측정이 교정하므로 **옛 구성의 점수가 유의하게 나빠지지 않으면 통과**다.

- [ ] **Step 3: 두 숫자를 적어둔다**

캘리브레이션 배수와 5덱 합계를 다음 태스크의 문서 갱신에 쓴다. 커밋할 파일은 없다.

---

## Task 3: 지식 베이스를 갱신한다

**Files:**
- Modify: `docs/encoded-nikkes.md` (아르카나: 포츈메이트 항목)
- Modify: `docs/engine-gaps.md` (펠릿 관련 갭)
- Modify: `docs/roadmap.md` (To-Do에 이 작업이 올라 있으면)

**Interfaces:**
- Consumes: Task 2가 낸 캘리브레이션·합계 숫자

- [ ] **Step 1: `encoded-nikkes.md`의 그녀 항목을 고친다**

「청춘의 기록 미반영」이 deferred 사유로 적혀 있으면 지운다. 이제 인코딩돼 있다. Happy Memories의 펠릿은 **데미지가 아니므로 deferred가 아니라 해당 없음**이다.

- [ ] **Step 2: `engine-gaps.md`의 펠릿 항목을 다시 센다**

「펠릿 수 증가」가 데미지 갭으로 잡혀 있으면 성격을 바꾼다 — 데미지에는 영향이 없고(2026-07-28 판독), 남는 것은 명중 안정성·코어 커버리지와 도로시: 세렌디피티의 **펠릿 개수 트리거**(「80/160 펠릿 명중 시」)뿐이다. 막힌 유닛 수가 줄어든다.

- [ ] **Step 3: `/document`로 결정과 인사이트를 남긴다**

`/document`에 넘길 내용:

- **결정**: SG·SMG 소장품의 「일반 공격 대미지 배율」은 무기 스탯이 아니라 `normal_attack_damage_multiplier` 버킷으로 간다. 대안은 무기 스탯 유지였고, 실측이 두 소스의 가산성을 보여 기각됐다. 결과: 소장품과 스킬이 한 유닛에서 겹치면 값이 달라진다(오늘은 포츈메이트뿐).
- **인사이트**: 「배율」이라고 전부 무기 스탯이 아니다. **게임이 그 스탯을 뭐라 부르는지가 버킷을 정한다.** 이름이 같으면 같은 가산 버킷이다.
- **인사이트**: 실측에서 나온 값을 상수로 굳히기 전에, 그 값이 **측정 당시 투자 상태를 품고 있는지** 확인할 것. `0.091354`는 상수처럼 보였지만 `0.1/1.0946`이었고, 소장품 15레벨이라는 조건이 그 안에 숨어 있었다.
- **인사이트**: 스킬 설명에 있는 효과가 "실측상 안 나온다"고 결론 내리기 전에, **그 스탯의 선행 버킷을 이미 채우고 있는 소스**를 먼저 찾을 것. 한계효과가 작아 보이는 것과 효과가 없는 것은 다르다.

- [ ] **Step 4: 커밋**

```bash
git add docs/
git commit -m "Record the collectible-bucket finding in the knowledge base"
```

---

## Self-Review

**스펙 커버리지**

| 스펙 절 | 태스크 |
| --- | --- |
| 설계 1 — SG·SMG 소장품을 버킷으로 | Task 1 Step 8 |
| 설계 2 — 청춘의 기록 복구 | Task 1 Step 9 |
| 설계 3 — 상수 삭제 | Task 1 Step 9 (상수 블록 교체) |
| 설계 4 — `_prior` 시드값 | Task 2 Step 2 |
| 검증 — 소장품 15레벨 그녀 | Task 2 Step 1 (캘리 불변이 곧 이 검증) |
| 검증 — 소장품 없는 그녀 | Task 1 Step 11 (`h = 0.1`인 기존 E2E가 정확히 이 조건이다) |
| 검증 — NADM 소스 없는 SG 유닛 | Task 1 Step 12 (전체 스위트에 회귀가 없어야 함) |
| 검증 — 5덱·캘리브레이션 | Task 2 |
| 남은 확인 측정 (선택) | 계획에 넣지 않음 — 코드와 무관한 인게임 작업이고 스펙이 선택으로 표시했다 |

**미해결로 남기는 것**

- SG 소장품 사다리의 아래 세 칸(4.73/6.30/7.88)은 검증되지 않았다. 낮은 레벨 소장품을 낀 계정이 없다.
- SMG는 SG와 같은 매핑을 받지만 SMG 유닛으로 실측한 적이 없다.
