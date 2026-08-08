# 보스 코어 지름을 회차 데이터로 받는다

날짜: 2026-08-08

`BossProfile.core_diameter_px`는 2026-08-07에 opt-in으로 들어왔지만 **값을 넣을
길이 없었다** — 백엔드 끝단(`deck_search.py:213` → `simulate_raid`)과 API
(`api.py:70`)는 뚫려 있는데 그 앞이 전부 비어 있어, `frontend/src` 전체에서
`core_diameter_px` 검색 결과가 0건이다. 오늘 값을 쓰려면 API에 직접 POST하거나
스크립트에서 `BossProfile`을 손으로 만드는 수밖에 없다.

2026-08-08 실측(`docs/measurements/accuracy-circle-and-core-px.md`)이 코어를 잴
방법을 확정했으므로, 잰 값이 앱에 닿는 길을 만든다.

## 1. 무엇을 저장하는가 — 엔진 단위

> **정정 (2026-08-08, 같은 날 늦게).** 아래 환산식은 **철회됐다.** 게임이
> 창모드였고 실제 렌더 폭이 2560이 아니라 2333이었다는 것이 뒤늦게 확인되면서,
> 이 식은 녹화본 크기를 넣었을 때만 맞는 우연이었음이 드러났다. 쓸 수 있는
> 환산은 비율뿐이다 — `코어_엔진 = 코어_px × (조준원_엔진 / 조준원_px)`.
> 상세는 `docs/measurements/accuracy-circle-and-core-px.md` §해석.
> **이 설계의 나머지는 영향받지 않는다**: 저장 단위가 엔진 단위라는 것, 환산이
> 판독하는 쪽 일이라는 것, 배선 8곳이 모두 그대로다. 바뀐 것은 환산식 하나다.

실측이 확정한 환산은 이렇다: ~~`게임단위 = 화면px × (화면 가로 해상도 / 1920)`~~
(위 정정 참조). Fienn의 화면에서 경험적 인자는 ×1.336이었다.

**타입 필드에는 환산이 끝난 엔진 단위를 넣는다.** 스킬의 기존 관례 그대로다 —
공지의 「근거리」를 `near`로 옮겨 적는 것이 판독하는 쪽 일인 것과 같다
(`raid_rotations.py:23-26`, "한글을 그대로 적으면 로더가 거부한다"). 앱이
해상도를 알 필요가 없고, 나중에 다른 모니터에서 잰 값이 조용히 섞이지 않는다.

**원본 px와 해상도는 `stated`에 문자열로 남긴다** — `"코어 측정": "25px @2560x1440"`.
`stated`는 이미 「엔진 필드로 옮기지 않는 원문 기록」 자리이고, 환산을 나중에
되짚을 유일한 근거다.

## 2. 왜 공지 판독 스킬이 공지에 없는 값을 받는가

`update-raid-bosses`는 자기 규칙을 명시한다 — 「공지가 **그 단어로 적지 않은
것**은 채우지 않는다. 틀린 매핑은 값 검증을 전부 통과하고 조용히 초록으로
남는다.」 코어 크기는 공지에 없다.

그래도 이 스킬이 받는다. **그 규칙이 막는 것은 추측이지 관측이 아니다.** 금지된
예로 적힌 둘(「스쿼드 추천: 머신건」 → `range_band: mid`, 「저지 부위」 →
`part_destructible`)은 공지의 다른 항목에서 **없는 근거를 유추**하는 것이다.
코어 지름은 Fienn이 그 보스와 싸우면서 화면에서 잰 값이라 유추가 아니다.

배치도 맞다: 스킬에 이미 사람 확인 단계(3단계, 유일한 중단점)가 있어서 물을
자리가 있고, 값을 안 주면 `null`로 남기면 된다.

## 3. `range_band`는 건드리지 않는다

코어는 거리에 종속이다(실측 문서: near/far가 2.44배). 그런데 **밴드를 따로 적을
필요가 없다** — Fienn이 그 보스와 싸우면서 재므로 값은 이미 그 전투의 거리에서
나온 것이다. 스칼라 하나로 충분하고, 밴드별 코어 테이블은 YAGNI다.

특히 `range_band`를 코어 측정에서 역으로 채우지 않는다. 그 필드는 평타에 +30%를
붙이는 값이라 근거 없이 채우면 비싸고, 스킬이 이미 「공지에 없는 거리를 추측해
채우지 않는다」로 막아 둔 자리다. 두 필드는 출처가 다른 채로 나란히 산다.

## 4. 배선

| 파일 | 변경 |
|---|---|
| `data/raid-rotations.json` | `bosses[]`에 `core_diameter_px`(number\|null) |
| `backend/app/raid_rotations.py` | 검증: `None`이거나 양수 |
| `backend/app/api.py` | `RotationBoss.core_diameter_px: float \| None = None` |
| `frontend/src/types/raidRotation.ts` | `RotationBoss`에 필드 |
| `frontend/src/types/recommend.ts` | `BossProfile`에 필드 |
| `frontend/src/types/bossProfileDraft.ts` | draft 필드·기본값·검증·역변환 |
| `frontend/src/components/BossProfileField.tsx` | `pickRotationBoss`가 얹기 + 입력 칸 |
| `.claude/skills/update-raid-bosses/SKILL.md` | 3단계에서 묻기 + 환산 |

`data/raid-rotations.json`의 기존 보스 6기에는 `core_diameter_px: null`을 적는다.
키를 통째로 빼면 안 되는 선례가 이미 있다 — `stated`가 그래서 `{}`라도 적힌다
(스킬 4단계, `test_the_route_serves_the_file_as_is`).

### 4.0 검증은 키가 없어도 통과한다

`validate_rotations`는 `boss["range_band"]`처럼 대괄호로 읽지 않고
`boss.get("core_diameter_px")`로 읽는다. 이유가 둘이다.

**성격이 다르다.** `weakness`·`range_band`는 공지가 답을 주거나 명시적으로 안 주는
항목이라 판독하면 반드시 결정된다. 코어는 측정을 안 하면 애초에 존재하지 않는
값이다.

**대괄호로 읽으면 기존 테스트 픽스처 열 개가 한꺼번에 깨진다** — 이 필드와 아무
상관 없는 검증 규칙들을 못박는 픽스처들이다(`test_raid_rotations.py`의
`a_rotation()`과 각 테스트의 인라인 보스 dict).

그래도 **번들 파일에 키가 빠지는 것은 막힌다**: `test_the_route_serves_the_file_as_is`가
`get() == load_rotations()`로 완전 일치를 보는데, pydantic이 응답에 기본값
`None`을 채워 넣으므로 파일에 키가 없으면 그 자리에서 걸린다. 검증기의 관용과
번들 파일의 완전성을 각각 다른 장치가 지킨다.

### 4.1 입력 칸은 「코어 피격 가능」에 딸린다

엔진이 `core_hittable`이 거짓이면 이 값을 무시한다(`deck_search.py:212`,
"코어가 없으면 크기를 물을 수 없다"). 그래서 체크가 꺼져 있으면 **칸을 감춘다** —
속성저지가 유니온 탭에서 통째로 사라지는 것과 같은 이유다("켤 수는 있는데 아무
일도 안 일어나는 것이 더 나쁘다", `BossProfileField.tsx:47-49`).

체크를 끄면 값도 지운다. `pierce_hits_body_behind_core`가 이미 그렇게 동작한다
("폼에서 모순 상태를 아예 만들지 않는 편이 화면이 정직하다",
`BossProfileField.tsx:195-199`).

### 4.2 빈 칸 = `null` = 지금 동작

opt-in 성질을 폼까지 그대로 가져온다. 빈 문자열은 `null`로 검증되고, 0이나 음수는
거부한다 — 백엔드의 `Field(default=None, gt=0)`과 같은 경계다. 「0을 넣으면 코어가
없는 것」이라는 해석을 만들지 않는다: 그건 `core_hittable`이 이미 표현한다.

### 4.3 캐시와 옛 저장물

결과 캐시 키는 `canonicalize(boss)`가 키를 재귀 순회하므로(`lib/inputHash.ts:28-39`)
필드가 늘면 자동으로 해시에 들어간다. 배선할 것이 없다.

이 필드가 생기기 전에 저장된 프로필은 값이 `undefined`라, `bossProfileToDraft`가
`?? ''`로 받는다 — `pierce_hits_body_behind_core ?? false`,
`effective_range_band ?? null`과 같은 관용구다(`bossProfileDraft.ts:47-58`).

## 5. 이 작업이 바꾸지 않는 것

**빈 칸이면 오늘과 1비트도 다르지 않다.** 값을 넣어야만 문다.

- **실기록 캘리브레이션(`RECORD_BOSS`)에 켜는 것은 여전히 별개 결정**이다
  (`docs/decisions.md`, "`BossProfile.core_diameter_px`는 opt-in"). 이 작업은
  `scripts/raid_record.py`를 안 건드린다.
- **`p_조준`(gap #21)은 그대로 미모델**이다. 이 값이 정하는 것은 `p_탄착` 하나이고
  둘은 직교한다.
- **균등 원판 분포 가정**도 그대로다.

그리고 정직하게 적어 둔다: 실측 코어를 넣으면 AR·SMG·SG 평타의 코어 보너스가
크게 깎이고 MG/SR/RL(탄착군 10이 이미 코어 안)은 안 움직이므로 **덱 순위가
무기군 쪽으로 기운다.** 실기록과 맞으려면 코어가 AR 기준 약 67 · SMG 기준 약
95여야 하는데 둘이 서로 다르므로(같은 결정문), 실측값이 그보다 작으면 앱이
AR/SMG 덱을 과소평가하게 된다. 그건 이 배선의 결함이 아니라 잔차에 다른 항이
있다는 이미 알려진 사실이고, 이 작업으로 풀리지 않는다.

## 6. 테스트

- `backend/tests/test_raid_rotations.py` — `core_diameter_px`가 0·음수면 거부,
  `None`과 양수는 통과. 번들 파일이 그대로 로드되는지는 기존 테스트가 본다.
- `backend/tests/test_api_raid_rotations.py` — 라우트가 필드를 그대로 실어 보낸다.
- `frontend/src/types/bossProfileDraft.test.ts` — 빈 칸 → `null`, 양수 → 숫자,
  0·음수 → 오류, 왕복(draft → boss → draft)이 값을 보존.
- `frontend/src/components/BossProfileField.test.tsx` — `core_hittable`이 꺼져
  있으면 칸이 없고, 켜면 나타나고, 다시 끄면 값이 지워진다. 카드를 고르면 회차의
  코어 값이 얹힌다.

## 규모

프로덕션 ~90줄, 테스트 ~70줄, 스킬 문서 ~20줄.
