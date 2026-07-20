# 하모니 큐브 — 전원 Resilience Lv.15 가정 + 효과 배선

- 날짜: 2026-07-20
- 상태: 설계 확정 (구현 대기)
- 관련: `docs/engine-gaps.md` 갭 #12, `docs/decisions.md`

## 문제

큐브의 부가효과가 **전 로스터에 대해 한 번도 시뮬에 반영된 적이 없다.**

`cube_effects.cube_to_effects`는 `reload_speed_percent` /
`superior_code_damage_percent`를 받아 Effect를 만들지만, `roster.py:62`가
`spec.cube.get(...)`으로 넘기는 그 키들이 `PveCube`(`models.py:23` — 필드는
`name` / `level` 둘뿐)에 존재하지 않는다. 항상 `None`이 넘어가고 항상 빈 리스트가
돌아온다. 평탄 ATK/HP만 `harmony_cube_lv` → `cube_atk`/`cube_hp`로 정상 배선된
**반쪽 상태**였다.

수집 시점의 착용 상태를 그대로 쓰는 것도 실제 전투와 어긋난다. 실측 로스터 159명
중 **128명이 미착용**으로 잡히는데, 이는 게임 규칙 때문이다 — 같은 큐브를 동시에
12명까지만 장착할 수 있어(실제로 Resilience가 정확히 12개로 상한에 붙어 있었다)
평소에는 대부분이 미착용이지만, **덱마다 장착 → 전투 → 해제 → 다음 덱에 장착을
반복할 수 있으므로 솔로 레이드에서는 25명 전원이 큐브를 낀 상태로 싸운다**(Fienn
확인). 즉 스냅샷의 착용/미착용은 실제 전투 양상과 무관한 노이즈다.

## 결정

**모든 유닛이 Resilience 큐브(렐릭 베어) Lv.15를 착용한 것으로 가정한다.**
수집된 착용 상태는 사용하지 않는다.

큐브는 자유 재장착이 가능하므로 원리적으로는 "엔진이 유닛마다 최적 큐브를
고르는" 결정변수 모델이 가장 정확하다. 그러나 그것은 큐브 카탈로그 전수 수집과
평가 비용 배수를 요구한다. 지금 필요한 것은 **효과가 아예 안 들어가는 상태를
끝내는 것**이고, 나중에 유닛별 큐브 선택 UI로 확장할 계획이므로 전역 1종 고정이
현 단계의 올바른 크기다. (`docs/decisions.md`에 기록)

## 검증된 데이터

`tables.json`의 `cube_sample`(id 1000303, 렐릭 베어 큐브 = Resilience Cube)의
구조를 해독했다.

- `level1` / `level2` / `level3` 배열은 스탯이 아니라 **큐브 레벨(1~15) → 각 스킬
  슬롯의 스킬 레벨** 사다리다. Lv.15에서 `level1=3`, `level2=6`, `level3=0`
  (슬롯 3은 전 레벨 0 — 이 큐브의 효과는 정확히 두 개다).
- 슬롯별 퍼센트는 `harmonycube_skill_group[i].description_value_list[0]
  .description_value[skill_level - 1]`.
  - 슬롯 1 **퀵 리로드 HC** → `[14.84, 22.27, 29.69, ...]`, 스킬 레벨 3 → **29.69%**
  - 슬롯 2 **안티 코드 HC** → `[8.48, 10.6, 12.72, 14.84, 16.96, 19.09, ...]`,
    스킬 레벨 6 → **19.09%**
- **인게임 툴팁과 대조 완료 (Fienn, 2026-07-20): 재장전 속도 29.69% / 우월 코드
  공격 대미지 19.09% — 일치.**

이전 세션이 "값 인덱싱이 불연속이라 지어내면 안 된다"고 기록한 것은 슬롯 1의 값
리스트가 `29.69` 뒤에 `17.5, 20, 22.5…`로 이어지기 때문이었다. 슬롯 1의 스킬
레벨이 3에서 캡되므로 **뒷부분은 이 슬롯이 도달할 수 없는 구간**이고, 앞 3개는
등차(+7.42)다. 인덱싱은 해소됐다.

따라서 퍼센트를 상수로 박지 않고 **커밋된 테이블에서 유도한다.**

## 설계

### 백엔드

**1. `cube_effects.py` — 테이블 유도 방식으로 전환**

```
CUBE_SKILL_STATS = {            # 큐브 스킬 이름 → 엔진 스탯 이름
    "퀵 리로드 HC": "reload_speed_percent",
    "안티 코드 HC": "other_elemental_bonus",
}
ASSUMED_CUBE_LEVEL = 15
```

- `cube_skill_percents(tables, cube_level) -> dict[str, float]` — 위 사다리를
  따라 스탯 이름 → 퍼센트를 만든다. 스킬 레벨 0인 슬롯은 건너뛴다. 매핑에 없는
  스킬 이름은 **경고 후 건너뛴다** (`overload_decode`의 미지 effect_type 처리와
  같은 패턴).
- `assumed_cube_effects(tables, source_slug) -> list[Effect]` —
  `cube_skill_percents(tables, ASSUMED_CUBE_LEVEL)`을 `self` 스코프 · 무기한
  Effect로 변환.
- 기존 `cube_to_effects(name, source_slug, reload_speed_percent=…,
  superior_code_damage_percent=…)`는 **제거**한다. 호출자가 하나뿐이고 그 호출이
  바로 이 갭의 원인이었다.

**2. `roster.py` — `_passive_effects`가 가정 큐브를 싣는다**

`spec.cube` 분기를 없애고 항상 `assumed_cube_effects`를 더한다. `NikkeSpec.cube`
필드도 제거한다 (읽는 곳이 여기뿐이었다).

**3. `user_roster.py:92` — `pve_cube` 전달 제거**

수동 입력 경로와 동기화 경로가 모두 이 한 곳을 지나므로, 여기서 큐브 입력을 끊으면
가정이 전 경로에 일관되게 적용된다.

**4. `models.py` — `PveCube` 클래스와 `UserNikkeState.pve_cube` 필드 제거**

**5. `roster_assembly.py` — 평탄 스탯도 Lv.15 고정**

`extract_inputs`의 `harmony_cube_lv`를 수집값이 아니라 `ASSUMED_CUBE_LEVEL`로
둔다. 동기화 ATK/HP는 표시값을 읽는 게 아니라 `assemble_atk(base + grade/core +
extra_flat)`로 **바닥부터 계산**하므로 이중계산이 생기지 않는다.

**6. `tables.json`의 `cube_sample` 키를 `resilience_cube`로 개명**

더 이상 "샘플"이 아니라 우리가 의존하는 특정 큐브다. 소비처는
`stat_assembly.cube_atk` / `cube_hp` 및 신규 `cube_skill_percents` 세 곳.
`cube_atk`의 "큐브 ATK는 종류 무관, 레벨 의존" 실측 주석은 유지한다(가정이 전역
1종이라 이제 그 사실에 의존하지도 않는다).

### 우월 코드 대미지 게이팅 수정 (같은 작업에 포함)

`damage_formula.py:96`이 이렇다:

```python
element_bonus_damage = element_multiplier + other_elemental_bonus
```

`element_multiplier`는 속성 우위일 때만 `1.1`, 아니면 `1.0`인데
(`elements.py`), `other_elemental_bonus`는 **우위 여부와 무관하게 더해진다.**
인게임의 "우월 코드 공격 대미지 ▲"는 우위일 때만 적용된다.

개별 유닛 스킬들은 이 사실을 알고 스스로 게이팅해 왔지만
(`maiden_ice_rose`·`marciana_marine_study`·`guillotine_winter_slayer`가
`boss_is_element` 조건 사용), **오버로드의 "우월코드 대미지 증가"
(`overload_effects.py:15`)는 게이팅 없이 무조건 적용된다.** 이는 큐브와 무관하게
이미 존재하는 오차이며, 비우위 유닛의 딜을 체계적으로 부풀린다.

가정 큐브의 안티 코드 +19.09%를 배선하면 이 오차가 **전 유닛으로 확대**되므로,
같은 작업에서 고친다.

```python
has_element_advantage = element_multiplier > 1.0
element_bonus_damage = element_multiplier + (
    other_elemental_bonus if has_element_advantage else 0.0
)
```

새 파라미터가 필요 없다 — `element_multiplier`가 이미 우위 지시자다.

- 자체 게이팅하는 스킬들은 **이중 게이팅**이 되지만 조건이 동일하므로 무해하다.
  기존 게이트를 걷어내는 것은 이 작업과 무관한 변경이므로 하지 않는다.
- **기존 테스트 중 `element_multiplier` 기본값 1.0으로 두고
  `other_elemental_bonus` 효과를 검증하던 것들이 깨진다. 그것이 이 수정의
  요점이다** — 깨진 테스트는 우위 상황을 명시하도록 고친다.

### 프론트엔드 (대부분 삭제)

- `components/PveCubeField.tsx` 제거, `NikkeCard.tsx`의 배선 제거.
- `types/nikkeDraft.ts`의 `hasCube` / `cubeKnown` 제거. `cubeKnown`은 동기화
  페이로드가 큐브를 안 실을 때 기존 입력을 보존하려고 직전 세션에 넣은 것인데,
  가정이 고정되면 **보존할 상태 자체가 없어지므로** 병합 로직도 함께 제거한다.
- `lib/exiaImport.ts` / `lib/rosterImport.ts`에서 큐브 필드 생성 제거.
- 로스터 화면에 안내: **"모든 니케가 Resilience 큐브 Lv.15를 착용한 것으로
  계산합니다."**

## 테스트

- `cube_skill_percents(tables, 15)` → `{"reload_speed_percent": 29.69,
  "other_elemental_bonus": 19.09}` **핀 고정**(인게임 대조값).
- 중간 레벨 한 점(예: Lv.5 → `level1=2`, `level2=1` → 22.27 / 8.48)으로 사다리
  해석 자체를 검증. 레벨 0 슬롯이 생략되는지 확인.
- 매핑에 없는 큐브 스킬 이름이 경고와 함께 건너뛰어지는지 (로그 캡처 검증 — 테스트
  출력은 pristine해야 하므로 경고를 삼키지 말고 잡아서 단언한다).
- **종단 검증: 가정 큐브가 실제로 딜을 움직인다.** 재장전 +29.69%가 매거진 무기의
  발사 수를 늘려 `total_damage`가 증가하는지. 이 테스트가 없으면 갭 #12를 그대로
  재현하게 된다(배선은 있는데 값이 안 들어가는 상태가 조용히 통과).
- **게이팅 회귀:** 동일 유닛·동일 `other_elemental_bonus`에 대해 우위 보스에서는
  딜이 오르고 비우위 보스에서는 오르지 않는다.
- `pve_cube` 제거 후 기존 로스터 JSON(그 필드를 담고 있는 저장본)이 계속 파싱되는지
  — 프론트 `parseRosterJson`은 모르는 필드를 무시해야 한다.
- 프론트: 안내 문구 렌더링, 큐브 입력란 부재.

## 범위 밖 (하지 않는 것)

- 큐브 카탈로그 전수 수집 (Resilience 하나만 필요하다).
- 유닛별 큐브 선택 UI, 엔진의 큐브 최적화 — Fienn의 다음 단계 계획이지만 이번이
  아니다. 위 설계는 `assumed_cube_effects`가 유일한 진입점이라 그때 입력을
  받도록 바꾸면 된다.
- 자체 게이팅하는 스킬들의 중복 게이트 정리.

## 알려진 한계

**수동 입력 ATK 경로.** 사용자가 ShiftyPad에서 읽어 직접 입력한 ATK는 그 시점의
실제 착용 큐브(또는 미착용)를 반영한 값이고, 우리는 거기에 아무것도 더하지 않는다.
따라서 그 경로에서는 평탄 스탯이 Lv.15 가정과 어긋난다(미착용 유닛이면 ATK
2,780 · HP 83,400만큼 과소). 동기화가 주 경로가 된 지금 이것은 기록만 하고 두되,
수동 입력이 계속 쓰인다면 별도 작업으로 다룬다.
