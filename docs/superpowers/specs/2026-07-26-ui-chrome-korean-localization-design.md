# UI 크롬 한글화 — 설계

- Date: 2026-07-26
- Status: 승인됨 (Fienn)
- 관련: `docs/superpowers/specs/2026-07-25-korean-display-names-design.md`
  ("후속으로 분리"의 "UI 크롬 한글화" 항목을 여기서 착수)

## 배경

한국 유저 대상 서비스로 가기로 이미 결정된 상태(위 관련 스펙 참고)에서, 유닛
표시 이름은 한글화됐지만 UI 크롬(레이블·버튼·헤더·안내문 등, 화면을 감싸는
"틀" 부분)은 여전히 영문이다. 이 스펙은 그 나머지를 한글로 치환하는 작업의
범위와 방식을 정한다.

## 결정

### 1. i18n 라이브러리 없이 직접 치환

`react-i18next` 같은 프레임워크를 도입하지 않고, JSX/TS 안의 영문 문자열을
한글로 직접 바꾼다. 다국어 전환 요구가 없는(한국 유저 전용으로 이미 결정된)
서비스에 다국어 인프라는 YAGNI다. `overload_effects.py`가 이미 한글 문자열을
코드에 직접 박아두는 것과 같은 패턴이라 일관적이다.

### 2. 보스 속성명

Fienn이 직접 지정: `Fire`=작열, `Water`=수냉, `Wind`=풍압, `Iron`=철갑,
`Electric`=전격. `BossProfileField.tsx`의 원소 select 옵션과
`UnitPalette.tsx`의 유닛 메타 표시(`B{tier} · {element}`) 둘 다 반영한다.

## 범위

**포함** — `frontend/src` 전수 조사(Explore 서브에이전트, 2026-07-26) 기준
사용자에게 노출되는 모든 영문 문자열:

- `App.tsx`: 제목, 부제, 안내문, 탭 레이블(Roster/Recommend), 빈 상태 메시지,
  footer의 "N of M Nikke(s) ready" 문구
- `BossProfileField.tsx`: legend, 필드 레이블, 체크박스 레이블, 힌트, 속성
  select 옵션
- `RecommendPanel.tsx`: 제출/취소 버튼(로딩 상태 포함), 모드 라디오 3종 설명,
  진행중 상태 메시지, 검증 에러
- `SyncRosterPanel.tsx`, `ProfileSwitcher.tsx`, `DraftEditor.tsx`,
  `DraftResults.tsx`, `RaidResults.tsx`, `DeckCard.tsx`, `DeckResults.tsx`,
  `RosterGrid.tsx`, `ExcludedSlugsNote.tsx`, `InvestmentBadge.tsx`,
  `NikkeCard.tsx`, `UnitPalette.tsx`: 나머지 헤딩/레이블/힌트/빈상태/
  aria-label/title
- 프론트 자체 fallback 에러 메시지: `hooks/useAsyncRequestStatus.ts`,
  `useRecommendRaid.ts`, `useSupportedUnits.ts`, `api/recommendApiError.ts`,
  `api/assembleRosterApiError.ts`, `lib/rosterImport.ts`, `lib/shareUrl.ts`
- `types/bossProfileDraft.ts`의 실사용 검증 에러 메시지
- `types/nikkeDraft.ts`의 검증 에러 — 현재 이 타입을 편집하는 UI가 없어 미사용
  (dead code)이지만, 치환 비용이 거의 없고 나중에 편집 폼이 붙을 때 영문이
  섞여 나오는 걸 막기 위해 같이 치환한다.

**제외**:

- 백엔드가 그대로 내려주는 FastAPI/Pydantic 검증 원문(422 응답의 raw `msg`,
  예: `field required`). 프론트 자체 fallback 메시지만 이번 범위이고, 백엔드
  검증 메시지 매핑은 범위가 더 크고 백엔드 작업이 필요해 별도 작업으로 분리.
- `lib/bookmarklet.ts` — 이미 한글로 작성돼 있어 변경 불필요.
- `S1`/`S2`/`B`, `B1`/`B2`/`B3` 같은 게임 표준 약어 — 번역 대상 아님(기존
  오버로드 축약 표기 `공`·`크댐`과 같은 결의 표기).
- `SyncRosterPanel.tsx`의 placeholder 예시 URL — 문장이 아니라 URL 리터럴.

## 테스트

문자열이 바뀌면 대응하는 `getByText`/`getByRole(name: ...)` 단언도 같이
깨지므로, 영향받는 `*.test.tsx`/`*.test.ts`를 새 한글 문자열에 맞춰 함께
수정한다. 새 텍스트에 대한 신규 단언을 추가하진 않는다(기존 커버리지를
유지하는 것이 목적이지, 이번 작업으로 커버리지를 넓히는 게 목적이 아니다).

완료 기준: `npm test -- --run` 그린 (치환 전 기준선 289 passed와 동일한
테스트 수 유지, 문자열만 한글로 교체).
