# 인코딩 전수 점검 (2026-08-17)

옆 세션이 아스카: WILLE의 인코딩 버그(원문의 발동 시점을 잘못 읽어 효과가 9초
일찍 걸리던 것, 트렁크 `381e2396`)를 잡은 뒤, **같은 부류가 다른 유닛에도 있는지**
인코딩된 103개 슬러그 전부를 스킬 원문과 대조했다.

- 대상: `registry._BUILDERS`의 **103 슬러그** (캐릭터 파일 기준 90개)
- 방법: 각 슬러그의 max-level 원문 + 조립된 슬롯 값 + 모듈 소스를 나란히 읽고
  트리거 / 조건 / 스코프 / 슬롯 번호 / 지속시간 / 미모델 기재를 대조
- 기준선: 백엔드 2428 passed / 3 skipped (skip 3건은 워크트리에 없는 로스터 덤프,
  회귀 아님), 기계 audit 6종 전부 exit 0

## 요약

| | 건수 | 상태 |
|---|---|---|
| **실제 결함** | 2 | 수정 완료 (F1 noir · F2 quency) |
| **판정 보류 — Fienn 확인 필요** | 1 | 미수정 (M1 mana) |
| **문서 결함** (코드는 옳고 서술이 틀림) | 7 | 6건 수정, 1건 기록만 |
| 원문과 일치 | 100 | — |

**아스카와 같은 「지연 발동 오독」은 다른 곳에 없었다.** 상태 이름을 참조하는
발동 문구(“when X takes effect / ends”)를 가진 유닛 12개를 개별 확인했고
(laplace-ultimate-hero · neon-vision-eye · grave · mast · crown · nayuta ·
ark-ranger-black · arcana-fortune-mate · cinderella-crystal-wave · prika ·
queen/yukiko · soda), 전부 올바른 시점에 걸려 있었다. 특히 laplace: Ultimate
Hero의 “Electric Power, Fully Full Charge가 끝날 때 탄약 100% 제거”는 아스카와
구조가 같은데, 변형 창이 끝나는 지점에 정확히 놓여 있다.

---

## F1. Noir — 「같은 부대 아군」 조건이 게이트 없이 항상 걸렸다 ★수정

**원문** (Finale, skills[2] 세 번째 불릿):

> ■ Activates **with an ally from the same squad still on the battlefield**.
> Affects all allies.
> Hit Rate ▲ 11.61% for 30 sec. / Damage to Interruption Parts ▲ 19.36% for 30 sec.

노아의 인게임 부대는 **777**이고 그 구성원은 Blanc · Noir · Rouge 셋뿐이다
(ShiftyPad raw 번들 `detail.squad`, rid 270/271/272 — 셋 다 인코딩되어 있다).
덱에 Blanc도 Rouge도 없으면 이 불릿은 발동하지 않아야 하는데,
`buff_rule("own_burst_activate", ...)`로 **무조건** 걸리고 있었다.

- **같은 문구를 가진 Blanc은 처음부터 옳게 게이트되어 있었다**
  (`deck_contains(TWIN_SLUGS={rouge, noir})`). 같은 절이 한 유닛에선 지켜지고
  다른 유닛에선 빠진 형태다.
- 원문에서 “same squad” 문구를 쓰는 유닛은 전체 5곳이고, 나머지 넷은 모두
  정상이었다: anchor(힐 불릿, 미모델) · blanc(게이트됨) ·
  emma/eunhwa(`ABSOLUTE_SQUAD_SLUGS` 스코프로 정확히 해석).

**영향.** `hit_rate`는 엔진이 소비하는 스탯이다. 부대원 없는 덱에서 노아(SG)의
코어 명중률이 부풀어 있었다 — 코어 지름 48.89 기준:

| | 탄착군 | 코어 명중률 |
|---|---|---|
| 부대원 있음 (13.93 + 11.61) | 191.95px | 0.0649 |
| 부대원 없음, 수정 후 (13.93만) | 218.34px | 0.0501 |

같은 불릿의 `damage_to_interruption_parts_up` 절반은 엔진이 소비하지 않으므로
(저지 부위는 이 시뮬이 만들지 않는 표적) 데미지에 영향이 없다.

**수정.** `noir.py`에 `SQUAD_777_SLUGS = {"blanc", "rouge"}`를 두고 세 번째
불릿의 두 항을 `deck_contains_any`로 함께 게이트했다. 두 번째 불릿(SG 대상)의
parts 항은 그 불릿 소속이므로 게이트하지 않는다.
회귀 테스트: `test_noir_finale_squad_bullet_needs_a_777_squadmate`.

**⚠ 스윕으로는 이 수정이 0으로 보인다.** `sweep_slug_damage.py`의 보스는
`core_hittable=False`라 명중률이 데미지에 닿지 않는다
(docs/insights.md의 「스윕 보스는 보스 축이 전부 중립이다」). 실제 크기는
실기록 캘리브레이션에서만 읽힌다.

## F2. Quency: Escape Queen — 스킬 값이 만렙으로 박혀 있었다 ★수정

`Explore Route`(skills[1])가 **매니페스트에 아예 없었고**, 그 스킬의 스택 값이
모듈에 리터럴로 적혀 있었다:

```python
STEADY_STATE_ATK = 2.45 * 10 + 4.9 * 10 + 7.36 * 5      # 110.3
STEADY_STATE_HIT_RATE = 1.36 * 10 + 2.71 * 10 + 4.08 * 5  # 61.1
```

이 여섯 숫자는 **스킬 레벨에 따라 변한다**. 로스터 조립 계층은 사용자의 실제
스킬 레벨로 값을 만드는데, 이 스킬만 그 경로 밖에 있어서 **스킬 2가 몇이든
언제나 10레벨로 시뮬레이션**됐다. 매니페스트에 없으니 조립 검증 하네스
(`test_skill_value_assembly`)도 볼 수 없었다.

| Explore Route | ATK 합 | 명중률 합 | SMG 탄착군 | 코어 명중률 |
|---|---|---|---|---|
| 스킬 10 | 110.3% | 61.1% | 48.90px | 0.9996 |
| 스킬 1 | 64.8% | 35.9% | 74.10px | 0.4353 |

명중률 쪽이 결정적이다 — 61.1%는 SMG의 110px 탄착군을 50px 코어 **안으로**
집어넣고 35.9%는 그러지 못한다. 스킬 1인 로스터에서 그녀의 코어 명중률이
0.4353이어야 할 자리에 0.9996이 들어가 있었다.

**수정.** 매니페스트에 `"explore_route": ("skills", 1)`을 추가하고, 상수 둘을
슬롯에서 읽는 `steady_state_atk(values)` / `steady_state_hit_rate(values)`로
바꿨다. 세 단계가 각각 (값 슬롯, 스택 캡 슬롯) 쌍이라 합은
`_ATK_STAGES = ((6,7),(14,15),(22,23))` / `_HIT_RATE_STAGES = ((3,4),(11,12),(19,20))`
로 표현된다. 회귀 테스트: `test_explore_route_scales_with_skill_level`.

**만렙 로스터에서는 숫자가 안 바뀐다** — Fienn의 로스터가 이 스킬 10이면 캘리는
그대로다. 고친 것은 그 아래 레벨에서 조용히 틀리던 부분이다.

**같은 형태를 전수로 찾는 스크립트를 만들었다** —
`scripts/audit_hardcoded_skill_values.py`. 모듈의 숫자 리터럴 중 그 유닛의
원문이 max 레벨에는 갖고 있고 1레벨에는 갖고 있지 않은 값(= 레벨에 따라 움직이는
값)을 AST로 찾아낸다. 전체 103 슬러그에서 실제 적중은 quency 하나였고, 나머지
셋(julia/julia-signature의 `DECRESCENDO_COOLDOWN = 20.0`,
scarlet의 `FULL_MAGAZINE_RELOAD_PERCENT = 100.0`)은 정수 우연 일치인 오탐이다.

---

## M1. Mana — Metal σ 재획득 해석 (판정 보류, **Fienn 확인 필요**)

**원문** (Metal o, skills[1]):

> ■ Activates when entering Full Burst **in Metal σ status**. Affects self.
> Attack Damage ▲ 21.12% / ATK ▲ 63.36% for 10 sec. **Removes Metal σ.**
> …
> ■ Activates **if the skill user has cast Burst Skill before Full Burst ends**.
> Affects self. Metal σ: … continuously.

모듈은 이것을 `full_burst_enter` + `own_burst_fired_this_cycle()`로 근사하고,
docstring은 “이 엔진이 시뮬레이션할 수 있는 어떤 덱에서도 동등하다(티어당
공격수 한 명)”고 적었다. **그 전제가 사실이 아니다** — `burst_cycle`의
`chosen = eligible[0]`은 같은 티어 2인을 실제로 번갈아 발사시킨다.

두 해석이 갈린다(그녀가 매 사이클 버스트하는 단일 B3 덱에서는 **둘 다 모듈과
같다**. 갈리는 건 B3가 둘인 덱뿐이다):

- **해석 A — 재획득 판정이 Full Burst 종료 시점**: σ 보유가 사이클을 건너
  이월되므로 게임은 1·2·4·6… 사이클에 버프를 받는다. 즉 그녀가 **직접 쏘는**
  사이클(1·3·5…)에는 버프가 없고, 모듈은 정반대로 그 사이클에 준다.
- **해석 B — 재획득이 캐스트 시점**: 모듈과 일치한다.

원문만으로는 정해지지 않고 게임 지식이 필요하다(CLAUDE.md의 “불분명한 메커니즘은
추측하지 말고 물어볼 것”). **B3를 둘 앉힌 덱에서 마나의 Metal σ 버프가 그녀가
버스트한 사이클에 붙는지, 아니면 그 다음 사이클에 붙는지** 한 번 확인하면
닫힌다. 그때까지 코드는 손대지 않았다.

---

## 문서 결함 (코드는 옳고 서술이 틀린 것)

값과 배선은 맞는데 옆에 적힌 설명이 틀린 경우다. 낡은 근거는 다음 세션이
그대로 믿기 때문에 고쳤다.

| # | 유닛 | 내용 | 조치 |
|---|---|---|---|
| D1 | ade-agent-bunny | 버스트의 `Minimum Effective Range ▲55.56%`가 미모델인데 “Not modeled” 목록에 없었다 (미모델 자체는 옳다 — 엔진에 그 스탯이 없고, 유효사거리 보너스는 인카운터가 정한다) | 기재 추가 |
| D2 | nayuta | “`description_value_02` == `_03` == 30”이라 적었으나 실제로는 `_03`(캡) == `_11`(3단계 임계) == 30. `_02`는 1.4(명중률) | 수정 |
| D3 | laplace-ultimate-hero | `_over_energy_stage_rule` docstring이 “누적이 아니라 단계별 대체”라고 **코드와 반대로** 서술 (코드·상단 docstring·인라인 주석은 모두 누적) | 수정 |
| D4 | privaty | 매니페스트 위 주석이 “매니페스트는 dollskills를 읽는다”고 단언 — dual-slot 분리 이전 서술 | 수정 |
| D5 | rosanna | 매니페스트 키 이름 `capo_dei_capi`가 base의 skills[1](= Frenzy)을 가리킨다. 값은 쓰이지 않아 무해 | 기록만 |
| D6 | snow-white-heavy-arms | “Modeled” 목록만 Burst Stage 3 버프를 `own_burst_activate`라 적었다. 같은 docstring 윗단락과 코드는 `ally_burst_activate` + `burst_stage_entered(3)`로 옳다 | 수정 |
| D7 | phantom-signature, julia-signature | 2026-07-28에 폐기된 「as additional damage → Full Burst 보너스」 텍스트 규칙을 여전히 근거로 인용 (“the project's standing rule”). 코드는 타이밍 기반이라 옳다 | 수정 |

---

## 점검을 반복하기 위해 만든 것

| 스크립트 | 무엇을 하나 |
|---|---|
| `scripts/dump_skill_text.py` | 인코딩 슬러그의 max-level 원문 + 슬롯 테이블 + **빌더가 실제로 받는 조립값**을 함께 출력. 슬롯 번호를 눈으로 세면 틀린다 — 추출기는 값 슬롯이 아닌 숫자(“Activates once per battle”의 1)를 세지 않는다 |
| `scripts/audit_trigger_phrases.py` | 원문의 `■ Activates …` 문구를 모듈이 등록한 트리거 집합과 나란히 출력. 아스카 버그가 정확히 이 축이었고, 기존 `audit_burst_stage_triggers.py`는 “Burst Stage N” 한 문구만 본다 |
| `scripts/audit_hardcoded_skill_values.py` | 레벨에 따라 움직이는 스킬 값이 모듈에 리터럴로 박힌 곳을 찾는다 (F2를 잡은 것) |

세 스크립트 모두 exit 0인 체크리스트다 — 판단은 사람이 한다.

## 이 점검이 커버하지 못한 것

- **게임 지식이 필요한 판정.** 원문이 애매한 곳은 기존 인코딩의 판단을 그대로
  받아들였다(M1이 예외적으로 드러난 경우다). Fienn의 실측이 근거로 적힌 항목은
  재검증하지 않았다.
- **덱 조합에서의 상호작용.** 유닛 단위 대조라, 두 유닛의 인코딩이 각각 옳지만
  함께 놓였을 때 어긋나는 경우는 범위 밖이다.
- **수치의 실전 크기.** F1·F2 모두 명중률을 통해 데미지에 닿는데, 스윕 셸의
  보스는 코어가 없어 두 수정 다 스윕에서는 0으로 보인다. 실제 크기는 실기록
  캘리브레이션에서 읽어야 한다.

## 검증

- 백엔드 **2430 passed / 3 skipped** (기준선 2428 + 신규 회귀 테스트 2건)
- 기계 audit 6종 재실행 전부 exit 0
