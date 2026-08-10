# 안내 문구를 helpText.ts 한곳으로 모은다

날짜: 2026-08-10

`frontend/src/lib/helpText.ts`는 2026-07-26에 「문구는 코드를 몰라도 고칠 수 있는
것이어야 한다」는 이유로 만들어졌지만, 실제로 흡수한 것은 **툴팁·동기화
도움말·개인정보 안내**뿐이다. 화면에 나오는 나머지 설명은 여전히 컴포넌트 안에
있다 — 앱 부제, 결과 화면 해설, 빈 상태 문구, 진행 중 안내, 미란다 임계값 해설,
차속 사다리 마무리. 문구 한 줄을 고치려면 그것이 어느 컴포넌트에 있는지부터
찾아야 하고, 고치고 나면 그 문구를 하드코딩한 테스트가 빨개진다.

이 설계는 그 나머지를 흡수한다. **문구를 옮기는 작업이지 문구를 바꾸는 작업이
아니다** — 이 변경으로 화면에 보이는 글자는 한 글자도 달라지지 않는다.

## 1. 무엇이 오고 무엇이 안 오는가

오는 것은 **읽고 이해하는 문장**이다. 48개 항목, 사용처 52곳 — 항목 4개는 두
자리에서 같은 글자를 쓴다.

안 오는 것과 그 이유:

| 안 오는 것 | 개수 | 왜 |
|---|---|---|
| 라벨·버튼·셀렉트 옵션 | 약 150 | 문장이 아니라 조작 대상의 이름이다. 옮기면 컴포넌트를 읽을 때 실제 글자 대신 상수 이름만 보인다. |
| 에러·검증 메시지 | 약 25 | `필수 입력이에요`, `덱 추천을 가져오지 못했어요`. 안내가 아니라 그 순간의 실패 보고다. |
| 북마크릿 alert 6개 (`lib/bookmarklet.ts`) | 6 | **함정이 된다.** 이 문구는 북마크릿 코드 안에 직렬화돼 유저 브라우저의 북마크로 들어간다. helpText.ts에서 고쳐도 이미 설치된 북마크릿에는 퍼지지 않고 유저가 다시 깔아야 반영된다 — 「고쳤는데 안 바뀐다」가 여기서만 참이 되면, 그 예외를 아는 사람만 이 파일을 안전하게 쓸 수 있다. |
| 도메인 용어 사전 | — | `elementName.ts`의 속성명(`Fire: '작열'`), `overload.ts`의 약어(`'크리티컬 확률': '크확'`). 문구가 아니라 데이터 매핑이다. |
| 단위 표시 | — | `hint="초"`, `hint="엔진 단위"`. 기존 파일 헤더가 이미 그은 선이고, 그대로 둔다. |

경계에 있어 **가져오기로 정한** 세 묶음:

- **빈 상태 문구**(6) — `아직 추천된 덱이 없어요.` 형태지만 실질은 「다음에 뭘
  하라」는 안내다.
- **진행 중 안내**(5) — `수천 번의 시뮬레이션을 실행하며 보통 2~5분이 걸려요.`
  기대 시간을 말해주는 문장이라 다듬을 여지가 있다. `계산 중…` 같은 **버튼
  라벨은 제외**한다.
- **확인·한도 문구**(4) — 프로필 삭제 confirm, 보관 한도. 사용자가 되돌릴 수
  없는 결정을 내리는 순간에 읽는 글이다.

기존 파일 헤더의 「진행·결과·에러 메시지는 오지 않는다」는 문장은 이에 맞춰
고쳐 쓴다. 지금 경계는 **문장이냐 이름이냐**이지 상태냐 아니냐가 아니다.

## 2. 세 가지 규칙

### 규칙 1 — 값이 끼는 문구는 함수다

```ts
raidSplit: (deckCount: number) =>
  `이 ${deckCount}개 덱을 모두 함께 편성하세요 — 각 니케는 정확히 하나의 덱에만 배정돼요. 이것은 순위별 대안이 아니라 하나의 분할이에요.`,
```

자리표시자 문자열(`'이 {deckCount}개 덱을…'` + 치환 헬퍼)을 쓰지 않는 이유는
**조용히 틀리기 때문**이다. `{deckCount}`를 `{deckCnt}`로 잘못 고쳐도 컴파일러가
아무 말을 하지 않고, 화면에 `{deckCnt}`가 리터럴로 박힌다. 함수는 인자 누락도
이름 오타도 `npx tsc -b --noEmit`이 그 자리에서 잡는다.

인자 타입은 값이 이미 포맷을 거쳤는지로 가른다:

- **포맷 헬퍼를 통과한 값은 문자열로** 받는다. `percent(0.1234)` → `'12.34%'`,
  `formatDamage(...)`. 헬퍼는 컴포넌트 로컬이고, 그것까지 옮기면 문구 파일에
  계산이 들어온다.
- **그 밖의 값은 숫자로** 받고, 자릿수와 단위는 문구가 붙인다.
  `ladderGap: (gapPoints: number) => \`다음 구간까지 ${gapPoints.toFixed(2)}%p 남았습니다.\``
  — 호출부는 `gap * 100`만 넘긴다. 그래야 「%p」를 「퍼센트포인트」로 늘리거나
  「덱 {n}개」로 어순을 바꾸는 수정이 이 파일 안에서 끝난다.

### 규칙 2 — 분기는 컴포넌트에 남는다

세 곳이 「어느 문장을 쓸지」 자체가 로직이다:

| 자리 | 갈래 | 무엇이 정하는가 |
|---|---|---|
| `MirandaTargets.describeThreshold` | 3 | `row.kind`와 `thresholdPercent`의 null·0 여부 |
| `ChargeWindowLadder.closingLine` | 3 | 사다리가 끝난 이유(차지 소멸 / 오버로드 상한 / 마지막 구간) |
| `DraftEditor` 배치 힌트 | 2 | 덱이 여러 개고 호출자가 활성 덱을 들고 있는가 |

**문장만 각각 helpText.ts에 두고, 고르는 로직은 제자리에 남긴다.** 함수째로
옮기면 `row.kind === 'gain'` 같은 조건이 문구 파일로 딸려 와서, 「코드를 몰라도
고칠 수 있다」가 그 자리에서 깨진다.

### 규칙 3 — `**굵게**`가 안 먹는 자리는 표시한다

`HelpText`(`components/HelpText.tsx`)는 `**...**`만 굵게 그리는 인라인
컴포넌트다. Fragment를 반환하므로 기존 `<p className="...">` 안에 그대로 넣을 수
있고 CSS는 영향을 받지 않는다.

문제는 **문자열만 받는 자리**다. 여기서 `**`는 굵게 되지 않고 별표 두 개가
그대로 보인다. 해당 항목 다섯에 「평문 전용 — 별표가 글자 그대로 나온다」는 주석을
단다.

| 항목 | 자리 |
|---|---|
| `results.pinTitle` | `<span title=...>` |
| `savedRuns.confirmDelete` | `window.confirm()` |
| `profile.confirmDelete` | `window.confirm()` |
| `sync.bookmarkletNoAccount` | `setError()` → `<p className="sync__error">`가 평문으로 그린다. 같은 자리에 다른 에러 메시지도 오므로 그 렌더는 `<HelpText>`로 바꾸지 않는다. |
| `charge.rosterFallbackHint` | `NumberField`의 `hint` — `help`와 달리 `<HelpText>`를 거치지 않고 `{hint}`를 그대로 렌더한다. |

옮기는 나머지 문구는 그리는 지점을 `<HelpText>`로 통일한다. 그래야 「어디서
`**`가 먹는가」를 외울 필요가 없다. 로스터 가져오기 경고 둘과 이름 조회 실패
안내는 지금 `SyncRosterPanel:259`가 `<p className="sync__message">{note}</p>`로
평문 렌더링하는데, 이 한 줄을 `<HelpText>`로 바꾸면 셋 다 굵게를 쓸 수 있게 된다.

## 3. 그룹 구조

기존 결(화면 영역 단위: `boss`, `charge`, `sync`)을 그대로 잇는다.

```
HELP = {
  app        (3)   ← 신규
  boss       (7)   ← 기존 그대로
  charge     (4+5) ← 기존 + 사다리 마무리 4 + 칸 힌트 1
  miranda    (9)   ← 신규
  recommend  (5)   ← 신규
  recommendMode (4) ← 기존 그대로
  draft      (4)   ← 신규
  results    (9)   ← 신규
  savedRuns  (4)   ← 신규
  roster     (3)   ← 신규
  profile    (1)   ← 신규
  sync       (4+4) ← 기존 + 서버 선택 · 가져오는 중 · 이름 조회 실패 · 북마크릿 계정 누락
  syncHelp / attribution / privacy ← 기존 그대로
}
```

한 파일로 유지한다(177줄 → 약 370줄). 나눌 이유가 없다 — 이 파일을 여는 사람은
화면에서 본 문구를 찾으러 오고, 그 검색은 파일이 하나일 때 가장 짧다.

## 4. 이동 대상 전체

`✱` = 값이 끼는 함수, `▣` = 평문 전용, `⇄` = 두 곳이 공유.

### app
| 자리 | 이름 |
|---|---|
| `App.tsx:147` | `app.subtitle` |
| `App.tsx:150` | `app.cubeAssumption` |
| `App.tsx:171` | `app.noProfiles` |

### charge (기존 4개에 추가)
| 자리 | 이름 |
|---|---|
| `ChargeWindowLadder.tsx:25` | ✱ `charge.ladderGap(gapPoints)` |
| `ChargeWindowLadder.tsx:28` | `charge.ladderChargeGone` |
| `ChargeWindowLadder.tsx:31` | ✱ `charge.ladderCeiling(ceiling)` |
| `ChargeWindowLadder.tsx:33` | `charge.ladderAtLast` |
| `ChargeWindowPanel.tsx:134,142` | `charge.rosterFallbackHint` ⇄ |

### miranda
| 자리 | 이름 |
|---|---|
| `MirandaCalculatorPanel.tsx:64` | `miranda.notInRoster` |
| `MirandaCalculatorPanel.tsx:93` | `miranda.intro` |
| `MirandaCalculatorPanel.tsx:127` | `miranda.running` |
| `MirandaTargets.tsx:54` | ✱ `miranda.gainCapped(cap)` |
| `MirandaTargets.tsx:57` | ✱ `miranda.gainAt(current, threshold, gapPoints)` |
| `MirandaTargets.tsx:63` | `miranda.keepAlways` |
| `MirandaTargets.tsx:65` | ✱ `miranda.keepAbove(threshold, current, slackPoints)` |
| `MirandaTargets.tsx:114` | ✱ `miranda.targetsChange(cycles)` |
| `MirandaTargets.tsx:119` | ✱ `miranda.burstsFewer(bursts, total)` |

### recommend
| 자리 | 이름 |
|---|---|
| `RecommendPanel.tsx:697` | ✱ `recommend.minRoster(minimum)` |
| `RecommendPanel.tsx:814` | ✱ `recommend.searchRunning(modeLabel)` |
| `RecommendPanel.tsx:821`, `UnionRaidPanel.tsx:244` | `recommend.evaluateRunning` ⇄ |
| `RecommendPanel.tsx:945` | ✱ `recommend.poolNote(included, total)` |
| `RecommendPanel.tsx:948` | ✱ `recommend.poolUnsupported(count)` |

### draft
| 자리 | 이름 |
|---|---|
| `DraftEditor.tsx:238` | `draft.seatHintWithDeckPick` |
| `DraftEditor.tsx:239` | `draft.seatHintSingleDeck` |
| `DraftEditor.tsx:240` | `draft.seatHintCommon` |
| `DraftResults.tsx:132` | `draft.tiersIntro` |

### results
| 자리 | 이름 |
|---|---|
| `DeckResults.tsx:18` | `results.emptyDecks` |
| `RaidResults.tsx:38` | `results.emptyRaid` |
| `RaidResults.tsx:47` | ✱ `results.raidSplit(deckCount)` |
| `RaidResults.tsx:66`, `DraftResults.tsx:199` | ✱⇄ `results.bench(names)` |
| `EvaluationResults.tsx:52` | `results.seatOrder` |
| `SwapConvergenceNote.tsx:15` | `results.swapCutoff` |
| `DeckCard.tsx:99` | ✱ `results.holdBurst(names)` |
| `DeckCard.tsx:85` | ▣ `results.pinTitle` |
| `ExcludedSlugsNote.tsx:16` | ✱ `results.excludedUnsupported(names)` |

### savedRuns
| 자리 | 이름 |
|---|---|
| `RecommendPanel.tsx:922`, `UnionRaidPanel.tsx:326` | `savedRuns.restoreHint` ⇄ |
| `SavedRunList.tsx:40` | `savedRuns.empty` |
| `SavedRunList.tsx:82` | ✱▣ `savedRuns.confirmDelete(name)` |
| `SaveRunButton.tsx:64` | ✱ `savedRuns.capReached(cap)` |

### roster
| 자리 | 이름 |
|---|---|
| `lib/rosterImport.ts:54` | `roster.importMalformedUnit` |
| `UnitFilterBar.tsx:181` | `roster.emptyFilter` |
| `lib/rosterImport.ts:88` | ✱ `roster.importUnsupported(count, names)` |
| `lib/rosterImport.ts:97` | ✱ `roster.importUnmeasured(count, names)` |

### profile
| 자리 | 이름 |
|---|---|
| `ProfileSwitcher.tsx:57` | ✱▣ `profile.confirmDelete(label)` |

### sync (기존 4개에 추가)
| 자리 | 이름 |
|---|---|
| `SyncRosterPanel.tsx:77` | `sync.nameUnavailable` |
| `SyncRosterPanel.tsx:164` | `sync.serverChoice` |
| `SyncRosterPanel.tsx:257` | `sync.importing` |
| `hooks/useBookmarkletImport.ts:177` | ▣ `sync.bookmarkletNoAccount` |

## 5. 테스트도 HELP를 참조한다

문구를 하드코딩한 assertion이 **11개 파일에 39군데** 있다. 그대로 두면 마침표
하나를 고쳐도 테스트가 빨개져서, 중앙화의 목적이 절반만 달성된다.

```ts
// 지금
expect(screen.getByText('아직 추천된 덱이 없어요.')).toBeInTheDocument()
expect(await screen.findByText(/이 1개 덱을 모두 함께 편성하세요/)).toBeInTheDocument()

// 바꾼 뒤
expect(screen.getByText(HELP.results.emptyDecks)).toBeInTheDocument()
expect(await screen.findByText(HELP.results.raidSplit(1))).toBeInTheDocument()
```

이것이 테스트를 약하게 만들지 않는다. **이 assertion들이 재던 것은 원래부터
「이 조건에서 이 안내가 뜬다」이지 「글자가 정확히 이것이다」가 아니다** —
`/2~5분/`처럼 문장 일부만 재던 것들이 그 증거다. HELP 참조로 바꾸면 오히려 문장
전체를 재게 되어 assertion이 강해진다.

**39군데 전부를 바꾸지는 않는다.** 두 종류는 정규식을 유지한다:

- **문장 일부만 재는 자리** — `/9.90% 밑으로 내려가면/`처럼 값 하나를 확인하는
  assertion. 정확 문자열로 바꾸려면 나머지 인자값을 픽스처에서 계산해 넣어야
  하는데, 그 assertion이 재는 것은 값이지 문장이 아니다.
- **문구가 함수인데 「없음」을 재는 자리** — `queryByText(...).not.toBeInTheDocument()`.
  함수에 아무 인자나 넣어 정확 문자열을 만들면, 문구가 바뀌어도 그 특정 조합이
  없다는 이유로 초록이 된다.

문구가 **상수**일 때는 존재/부재 쌍을 함께 바꾼다 — 그래야 문구가 바뀔 때 두
줄이 같이 따라간다.

대상 파일 11개: `App.test.tsx`, `ChargeWindowLadder.test.tsx`,
`DeckResults.test.tsx`, `DraftResults.test.tsx`,
`MirandaCalculatorPanel.test.tsx`, `MirandaTargets.test.tsx`,
`RaidResults.test.tsx`, `RecommendPanel.test.tsx`, `SavedRunList.test.tsx`,
`SyncRosterPanel.test.tsx`, `UnitFilterBar.test.tsx`.

## 6. 부수 이득 — 중복 3쌍

같은 문구가 **서로 다른 컴포넌트에** 따로 박혀 있다. 합치면 한쪽만 고치는 사고가
사라진다.

- `savedRuns.restoreHint` — `RecommendPanel:922` / `UnionRaidPanel:326`
- `recommend.evaluateRunning` — `RecommendPanel:821` / `UnionRaidPanel:244`
- `results.bench` — `RaidResults:66` / `DraftResults:199`

넷째 공유인 `charge.rosterFallbackHint`(`ChargeWindowPanel:134,142`)는 한 파일 안
두 칸이라 여기 세지 않는다 — 고칠 때 놓칠 위험이 애초에 없다.

## 7. 검증

이 변경은 화면 글자를 바꾸지 않으므로, 검증의 목표는 **아무것도 안 바뀌었음**을
보이는 것이다.

1. `npx tsc -b --noEmit` → 0. 함수 인자 누락·이름 오타를 여기서 잡는다.
   (`npm test`는 타입을 보지 않는다.)
2. `cd frontend && npm test` → 719 통과 유지.
3. `dev.ps1`로 앱을 띄워 눈으로 확인. 테스트가 못 잡는 두 가지가 여기서만
   드러난다 — `<p>` → `<HelpText>` 교체가 CSS를 깨뜨렸는지, 그리고 `**`를 못 쓰는
   자리에 별표가 새지 않는지.

백엔드는 건드리지 않으므로 pytest도 앱 빌드 `--selftest`도 이 변경과 무관하다.

## 8. 크기

`helpText.ts` 177줄 → 약 370줄. 컴포넌트 20개 · 라이브러리 2개 · 테스트 8개 수정.
순 증감은 거의 0 — 글자가 자리를 옮길 뿐이다.
