# 서버별 로스터 동기화

날짜: 2026-07-29

## 왜

`nikke_area_id`가 북마크릿에 `81`로 박혀 있다. 81은 **일본**이고(권위 목록:
`GET api/lip/direct/commodity/Game/GetRegionList?game_id=29080` → 81 Japan ·
82 NA · 83 Korea · 84 Global · 85 SEA), 그동안 테스트된 두 계정이 우연히 둘 다
JP였기 때문에 "인터내셔널"로 오인된 채 동작해 왔다. 한국 서버 계정을 동기화하면
실패한다.

증상은 원인을 가린다. `GetUserCharacters`가 실패해도 결과를 `.characters||[]`로
읽어 빈 로스터로 뭉개고, 다음 호출이 `name_codes: []`로 나가 `1303001 param
invalid`를 낸다. 사용자는 **두 번째 호출의 이름**을 본다.

## 실측으로 확정된 사실

두 계정 × 5 서버 전수 조회(2026-07-29, Fienn):

| open_id | 81 Japan | 82 NA | 83 Korea | 84 Global | 85 SEA |
|---|---|---|---|---|---|
| A (본계) | **code 0, 186기** | 1302125 | **code 0, 10기** | 1302125 | 1302125 |
| B (부계) | code 0, 0기 | 1302125 | **code 0, 181기** | 1302125 | 1302125 |

- **`intl_open_id`는 전역 유일하고, 서버마다 별개의 게임 데이터를 갖는다.** 한
  사람이 여러 서버에 캐릭터를 만들 수 있으므로 **여러 서버가 `code 0`인 것이
  정상이다.** 남의 계정을 물어올 위험은 없다 — 어느 area로 물어도 같은 사람이다.
- 대신 **내 여러 서버 계정 중 엉뚱한 것을 고를 위험**이 있다. A를 자동 판정하면
  186기 JP 대신 10기 KR을 집을 수 있다.
- `1302125 "get info list err"` = 그 서버에 이 계정이 없다.
- **`1303002 "proxy.GetUserShiftyspadPrivacy error"`는 간헐적이다.** 같은
  (B, 81) 조합이 한 번은 1303002, 다음엔 `code 0, 0기`였다. 서버 하나의 일시적
  오류가 동기화 전체를 죽여선 안 된다.

## 결정 (Fienn 확정)

1. **탐색 후, 모호할 때만 묻는다.** 북마크릿이 5개 서버를 조회해 니케가 있는
   서버만 고른다. 하나면 그대로 진행하고(대부분의 유저), 둘 이상이면 앱이
   `JP 186기 / KR 10기`를 보여주고 고르게 한다. 짐작하지 않고, 유저가
   서버 번호를 알 필요도 없다.
2. **프로필 식별자를 `(open_id, area)` 쌍으로 바꾼다.** 지금은 `open_id`만
   키라서, 같은 open_id의 다른 서버 로스터를 동기화하면 조용히 덮어쓴다.

## 설계

### 서버 상수

**화면에 쓰는 말은 "서버"다.** "리전"은 blablalink API의 용어(`nikke_area_id`,
`GetRegionList`)이므로 코드 주석과 이 문서의 API 설명에만 남기고, 사용자에게
보이는 문구에는 쓰지 않는다.

```ts
// blablalink의 GetRegionList가 주는 다섯 서버. API가 부르는 이름은
// Japan/NA/Korea/Global/SEA이고, 화면에는 짧은 코드로 쓴다.
// 하드코딩인 이유: 목록이 바뀌는 일은 새 서버가 열릴 때뿐이고, 그때는 이 표에
// 한 줄 더하는 것이 라이브 조회를 유지하는 것보다 싸다.
export const SERVERS = [
  { area: 81, label: 'JP' },
  { area: 82, label: 'NA' },
  { area: 83, label: 'KR' },
  { area: 84, label: 'GL' },
  { area: 85, label: 'SEA' },
] as const
```

### 북마크릿 프로토콜

지금은 4개 호출 후 payload 하나를 보낸다. 바뀌는 흐름:

1. 5개 서버에 `GetUserCharacters`. **`code !== 0`이거나 캐릭터가 0기면 그 서버는
   후보에서 제외하되, 예외를 던지지 않는다** (간헐적 오류 내성).
2. 후보가 0개면 그 자리에서 멈추고 사람이 읽을 문구를 낸다 — 지금처럼 다음
   호출의 `param invalid`로 원인을 가리지 않는다.
3. 후보마다 `GetUserCharacterDetails` · `GetUserProfileOutpostInfo` ·
   `GetUserProfileBasicInfo`(실패는 지금처럼 삼킨다)를 호출한다. 후보는 보통
   1개, 최대 5개다.
4. payload를 보낸다:

```js
{ open_id, servers: [ { area, nickname, owned, character_details, recycle_room_researches } ] }
```

**구 payload도 계속 받는다.** 기존에 설치된 북마크릿은 `{open_id, nickname,
owned, character_details, recycle_room_researches}`를 보내는데, 그것은 area 81로
조회한 데이터이므로 `servers: [{area: 81, ...}]`으로 승격해 받으면 정확하다.
이렇게 하면 이번 변경이 즉시 재설치를 강제하지 않는다.

북마크릿 헤더의 "얇게 유지" 원칙은 지킨다 — 추가되는 것은 서버 루프와 후보
필터뿐이고, 판단(어느 서버를 쓸지)은 앱이 한다.

### 서버 선택 UI

`SyncRosterPanel`이 payload를 받았을 때:

- `servers.length === 1` → 지금과 동일하게 바로 `assembleRoster` → `onImport`.
- `servers.length >= 2` → 후보를 `JP (186기)` 형태로 보여주고 선택을 기다린다.
  묻는 문구는 "어느 서버의 계정을 가져올까요?"다. 고른 것 하나만
  `assembleRoster`에 넘긴다 — 나머지는 버린다(백엔드 왕복을 낭비하지 않는다).

여러 서버를 한 번에 프로필로 만들지 않는다. 한 번의 동기화 = 한 서버.
다른 서버도 원하면 다시 동기화하면 되고, `(open_id, area)` 키라서 둘이 공존한다.

### 프로필 저장소

- `Profile`에 `area: number` 추가.
- `ProfilesState.profiles`의 키를 `` `${openId}:${area}` `` 로 바꾼다.
  `activeOpenId` → `activeKey`로 이름을 바꾼다(값의 의미가 달라지므로 이름도
  바뀌어야 한다).
- **마이그레이션**: 기존 엔트리는 전부 area 81로 조회된 것이므로, 키가 `:`를
  포함하지 않으면 `` `${openId}:81` `` 로 옮기고 `area: 81`을 채운다.
  `activeOpenId`도 같은 규칙으로 변환한다. 읽기 시점에 1회 수행한다.
- 드롭다운 라벨에 서버를 붙인다: `FIENN (JP)`. 같은 사람의 두 서버 계정이
  구분돼야 하므로 닉네임만으로는 부족하다. 닉네임도 open_id도 없는 프로필은
  기존 `이름 없는 계정` 폴백에 서버가 붙어 `이름 없는 계정 (KR)`이 된다.
- `RecommendPanel`의 `activeOpenId` prop은 프로필 정체성을 나타내는 식별자로만
  쓰이므로(리마운트 키 + 복원 effect), `activeKey`로 기계적으로 바꾼다.

## 범위 밖

- `GetRegionList`를 라이브로 조회하기 — 하드코딩으로 충분하다(YAGNI).
- 여러 서버를 한 번에 여러 프로필로 만들기 — 한 번에 하나면 된다.
- 백엔드 `blablalink_api.py` / `collect.js`의 `area` 기본값 81 — 이미 파라미터로
  받으므로 동작은 옳다. 기본값 변경은 별개 판단이고 지금 필요 없다.

## 테스트

이 워크트리 기준선 **47 파일 / 423 passed**. 줄이지 않는다.

- `buildBookmarklet`: 생성된 소스가 5개 area를 모두 담고, `code !== 0`인 서버를
  건너뛰며, 후보 0개일 때 사람이 읽을 문구를 내는지.
- payload 수신: 신 shape(`servers`)와 구 shape(area 81 승격) 양쪽.
- 서버 1개면 선택 UI 없이 바로 임포트, 2개 이상이면 선택 전에는 임포트하지 않음.
- 프로필 저장소: `(openId, area)` 키로 두 서버가 공존하고 서로 덮어쓰지 않음.
- 마이그레이션: 구 스키마(`profiles[openId]`, `activeOpenId`)가 `:81` 키로
  옮겨지고 `area: 81`이 채워짐. 이미 새 스키마면 건드리지 않음(멱등).
- 드롭다운이 같은 닉네임의 두 서버를 구분해 보여줌.
