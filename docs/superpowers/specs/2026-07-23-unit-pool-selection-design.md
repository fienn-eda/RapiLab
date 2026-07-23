# "사용할 니케" 풀 선택 설계 (Unit Pool Selection)

**Goal:** 유저가 추천 실행 전에 **탐색 후보 풀에서 쓰지 않을 니케를 빼서** 풀을
근원에서 줄인다. 탐색 대상이 줄어 solo-raid from-scratch가 뺀 만큼 빨라지고
(현재 78유닛 greedy-peel = ~597초가 지배 비용), 결과가 유저가 실제 편성할 유닛으로
좁혀진다. 유저 선호(엔진이 뽑을 유닛을 굳이 뺌)도 표현할 수 있다.

**Architecture:** 전적으로 프론트엔드. 후보 풀 = `보유 ∩ 지원 − 유저가 끈 유닛`을
클라이언트에서 계산해, 요청을 보내기 전에 로스터를 필터링한다. 백엔드는 필터된
로스터만 받으므로 **API 계약 변경이 없다**(제외된 유닛은 애초에 payload에 없음).
프레이밍은 **화이트리스트("사용할 니케 선택")** — 기본 전체 켜짐이라 저마찰이고,
draft의 "쓸 유닛을 고른다" 멘탈모델과 일관적이다.

**전제:** 세 추천 모드(single / raid / draft) 모두 같은 로스터를 자유 탐색하거나
(single·raid) 배치+벤치스왑(draft)에 쓰므로, 풀 선택기를 **세 모드 모두**에 붙여
일관성을 유지한다(Fienn, 2026-07-23).

---

## Non-goals

- **2단계 탐색 알고리즘 아님.** greedy-peel을 "선별→좁은 분할"로 바꾸는 성능
  최적화는 `docs/roadmap.md` Phase 5 후속 백로그의 별도 트랙. 이번 스펙은
  **유저가 풀을 줄이는** 근원 레버만 다룬다. 제외로 실사용 속도가 충분해지는지
  본 뒤 2단계 필요성을 재판단(Fienn, 2026-07-23 "제외만 먼저, YAGNI").
- **영속 아님.** 제외 집합은 요청 단위 휘발성(React state). localStorage에
  저장하지 않고, 프로필 전환 시 리셋한다(Fienn, 2026-07-23 "요청 단위 임시 선택").
- **자동 제외 아님.** 육성/레벨로 "쓸 만한지"를 엔진이 추론하지 않는다 — 전적으로
  유저가 토글한다(잘못 추론하면 유저가 원하는 유닛을 지울 위험).
- **백엔드 요청 파라미터 아님.** `excluded_slugs`를 요청 필드로 받지 않는다. 응답의
  기존 `excluded_slugs`(인코딩 미지원으로 자동 제외된 유닛)와 의미가 충돌하고,
  클라이언트 로스터 필터가 더 단순하다(YAGNI).

---

## 후보 풀 모델

- **풀 = `보유 ∩ 지원 − excluded`.** `보유 ∩ 지원`은 팔레트가 이미 보여주는
  집합(`ownedSlugs` ∩ `GET /api/supported-units`).
- **`excludedSlugs: Set<string>`** — RecommendPanel의 휘발성 state. 세 모드가 공유.
- **`effectiveRoster = roster.filter(n => !excluded.has(n.character_slug))`** — 이걸
  요청·해시·검증에 쓴다:
  - single 요청 `roster`
  - raid 요청 `roster`
  - draft 요청 `roster`
  - `hashRecommendInputs(effectiveRoster, boss, draft, numDecks)` — 풀별로 캐시가
    정확히 분리된다(다른 제외 집합 = 다른 해시).
  - `rosterTooSmall = effectiveRoster.length < MIN_DECK_ROSTER_SIZE`
- **팔레트가 보여주는 목록은 여전히 전체 `보유 ∩ 지원`** — 제외된 유닛도 dim
  상태로 남겨 다시 켤 수 있게 한다. `effectiveRoster`는 오직 "무엇을 보내느냐"에만
  쓰인다.

---

## 컴포넌트: `DraftPalette` → `UnitPalette`

기존 `DraftPalette`를 일반화해 세 모드가 공유하는 tier별(B1/B2/B3) 초상화/칩 그리드로
만든다(리네임: 더 이상 draft 전용이 아니므로 도메인명 `UnitPalette`).

**Props:**
- `ownedSlugs: string[]`, `supportedUnits: SupportedUnit[]` — 그리드 대상(기존과 동일).
- `excludedSlugs: string[]`, `onToggleExclude: (slug: string) => void` — 풀 멤버십(세 모드 공통).
- `usedSlugs?: string[]`, `onPick?: (slug: string) => void` — 배치(draft 전용; 없으면 배치 없음).

**유닛별 렌더/상호작용:**
- **제외됨(excluded):** dim + 취소선, `aria-pressed`/체크 해제 상태. 토글 다시
  누르면 재포함. 배치 불가.
- **포함됨(included):**
  - **배치 가능(`onPick` 제공, draft):** 유닛 본체 버튼 = 배치(기존 동작, `usedSlugs`면
    disabled), **코너에 별도 "사용" 토글**(체크박스)로 풀 온/오프.
  - **배치 없음(single·raid):** 카드 본체 클릭 = 풀 토글(별도 코너 컨트롤 불필요).
- **헤더 요약** "N/M 사용" + "전체 사용" 리셋 액션.

**배치와 제외 충돌:** 이미 덱에 배치된 유닛을 제외하면 **draft에서 자동 해제**한다
(`onToggleExclude`가 excluded에 넣을 때 draftValue에서도 그 slug를 제거). slug로
언플레이스하는 얇은 헬퍼 `removeUnitBySlug(draft, slug)`를 `DraftEditor`에 추가
(기존 위치 기반 `removeUnit` 재사용). 결과적으로 배치 유닛은 항상 풀 안이라, draft가
풀 밖 유닛을 seed할 일이 구조적으로 없다.

**배치 위치:** 세 모드 모두 boss 입력 위에 노출.
- single·raid: 큰 그리드이므로 접이식 `<details>` "사용할 니케 (기본 전체)", 요약에
  "N/M 사용".
- draft: 배치의 주 상호작용 표면이므로 펼친 상태(기존 draft 팔레트 자리 그대로).

---

## RecommendPanel 변경

- `excludedSlugs` state 추가(휘발성, 세 모드 공유).
- `effectiveRoster` 계산(`useMemo`), 위 4곳에 적용.
- `toggleExclude(slug)`: excluded 토글; 제외로 넣을 때 배치돼 있으면 draftValue에서
  `removeUnitBySlug`.
- **프로필 전환 리셋:** `activeOpenId` 변경 시 `excludedSlugs`를 빈 집합으로
  (기존 restore effect에 한 줄). 복원된 결과는 캐시 표시일 뿐이고, 제외는 휘발성이라
  재제출은 현재(전체 포함) 기준으로 재계산된다 — 의도된 동작.
- `ownedSlugs`는 전체 `roster` 기준 유지(팔레트가 제외 유닛도 dim으로 보여줘야 함).

---

## 엣지 케이스

- **과다 제외:** `effectiveRoster.length < MIN_DECK_ROSTER_SIZE` → 기존
  `rosterTooSmall` 가드가 제출을 막고 기존 메시지를 재사용.
- **draft 완성-분배 불가:** 제외로 특정 tier가 부족해 draft를 채울 수 없으면
  백엔드가 기존대로 422/InfeasibleDraft. 프론트 `rosterTooSmall`은 필요조건만
  검사(기존 주석대로 충분조건 아님).
- **캐시:** 풀별 다른 해시로 정확히 분리. 같은 제외 집합 재실행은 히트.

---

## 테스트 (프론트만; 백엔드 무변경)

- **`UnitPalette`:**
  - 사용 토글 on/off → `onToggleExclude` 호출, 제외 유닛 dim/취소선.
  - draft(배치 병존): 포함 유닛 클릭 = `onPick`, 코너 토글 = `onToggleExclude`,
    `usedSlugs`는 배치 버튼 disabled.
  - `onPick` 없을 때(single·raid): 카드 클릭 = 풀 토글.
- **`RecommendPanel`:**
  - 제외 유닛이 single·raid·draft 제출 요청 `roster`에서 빠짐.
  - 같은 제외로 hash가 전체-로스터 hash와 다름(캐시 분리).
  - 과다 제외 시 `rosterTooSmall`(제출 disabled).
  - 배치된 유닛 제외 시 draft에서 자동 해제.
  - `activeOpenId` 변경 시 excluded 리셋.
- **`removeUnitBySlug`** 단위 테스트(배치된 slug 제거, 미배치 slug no-op).
