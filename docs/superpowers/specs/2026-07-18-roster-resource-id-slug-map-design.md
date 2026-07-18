# resource_id 권위 맵 — 수집기 로스터를 인코딩 slug로 정확히 해석

- 날짜: 2026-07-18
- 상태: 설계 (스펙 리뷰 대기)
- 범위: 프론트 `frontend/src/lib` — blablalink 수집기 `roster.json` 임포트 경로만.
  ExiaInvasion export 경로·백엔드·수집기는 무변경.

## 문제

Phase B 수집기가 `roster.json`을 뽑는 것까진 됐지만, 그 데이터가 추천기까지
흘러가려면 게임 유닛을 백엔드의 인코딩 slug로 정확히 매핑해야 한다. 현재 두 임포트
경로(`exiaImport`·`rosterImport`)가 **같은 이름 기반 `resolveSlug`/`SLUG_ALIASES`
테이블을 공유**하는데, 두 경로의 이름 관례가 다르다:

- ExiaInvasion export = **짧은 이름** ("Soline"). alias 테이블이 이 관례로 만들어짐.
- blablalink `roster.json` = 디렉토리 **풀네임** ("Soline: Frost Ticket"). 여기선
  base "Soline"도 별도 owned 유닛으로 등장한다.

같은 이름 테이블로 둘을 동시에 만족시킬 수 없어 `roster.json` 경로에서 오매핑이 난다.
Fienn 실제 로스터 기준 구체적 파손:

| resource_id | 게임 이름 | 현재 결과 | 문제 |
|---|---|---|---|
| 71 | Soline | alias → `soline-frost-ticket` | base 미인코딩인데 variant로 오매핑 → 74와 **중복 병합** |
| 74 | Soline: Frost Ticket | `soline-frost-ticket` | (정상) |
| 321 | Marciana | alias → `marciana-marine-study` | 위와 동일, 322와 중복 |
| 322 | Marciana: Marine Study | `marciana-marine-study` | (정상) |
| 392 | Rei (KR: 라이) | → `rei-ayanami` | **별개 캐릭터**인데 이름만 같음 → 오매핑 |
| 831 | Rei (KR: 레이) | → `rei-ayanami` | 392와 같은 slug로 감 |
| 834 | Rei (Tentative Name) | `rei-ayanami-tentative-name` | (정상) |
| 101 | Drake | → `drake` | 인코딩엔 `drake`+`drake-signature`, 애장품 보유 여부로 갈림 |
| 150 | Julia | → `julia` | `julia`+`julia-signature`, 위와 동일 |

중복 병합이 특히 나쁘다: `mergeImportedDrafts`가 `character_slug`를 병합 키로 쓰므로
base Soline(오매핑)과 진짜 variant가 한 슬롯으로 뭉개져 **정확한 스탯이 base 값으로
덮어써진다**. 이름만으로는 Rei 3중 중복(별개 캐릭터 포함)을 원천적으로 못 가른다.

## 해법 — resource_id 권위 맵

`roster.json`이 이미 담고 있는 안정적 게임 ID `resource_id`로 키잉해 이름 alias에서
완전히 분리한다. (Fienn 결정 2026-07-18: "resource_id 권위 맵 전면".)

### 컴포넌트

**신규 `frontend/src/lib/resourceIdSlugMap.ts`**
- `RESOURCE_ID_TO_SLUG: Record<number, string>` — 인코딩된 60 유닛의
  `resource_id → 인코딩 slug` 권위 테이블. 인코딩 slug 신원의 유일한 진실의 소스.
- 맵에 없는 `resource_id` = 미인코딩 유닛 = **추천에선 제외되지만 draft엔 유지**
  (아래 rosterImport 참조).
- 테이블은 `roster.json`의 owned 유닛(159)에서 resource_id를 추출해 저술한다
  (owned가 인코딩 60을 사실상 전부 덮음). 그 파일은 gitignore이므로 맵은 **커밋되는
  소스 코드**로 하드코딩하되, 값의 출처를 주석으로 남긴다.

**`frontend/src/lib/rosterImport.ts` 변경**
- 지금 버리는 `u.resource_id`를 읽는다.
- `RESOURCE_ID_TO_SLUG[u.resource_id]`로 slug 결정.
- **맵 히트** → 권위 slug로 정상 draft.
- **맵 미스**(미인코딩 owned 유닛) → **draft는 유지하되** slug는 alias 없는
  `deriveSlug`(raw kebab)로. 백엔드 `load_nikke_spec`이 `ENCODED_SLUGS` 밖이라
  자연히 제외하고 `excluded_slugs`로 표시한다. **오매핑 버그의 원인이던
  `SLUG_ALIASES`는 이 경로에서 안 쓴다** — raw 파생은 인코딩 slug와 충돌하지 않는다
  (예: base "Soline" → `soline` ≠ 인코딩 `soline-frost-ticket`; 라이 "Rei" → `rei`
  ≠ `rei-ayanami`).
- 미인코딩 유닛을 draft에 남기는 비용은 사실상 0: 백엔드가 시뮬 진입 전(`load_nikke_spec`
  첫 줄 O(1) 집합 체크)에 걸러 `specs`에 안 넣으므로 **덱 탐색 정확도·속도에 무영향**.
  애정 캐릭 등 저기용 유닛의 "보유 가시성"을 보존한다(Fienn 2026-07-18).
- 반환 `warnings`에 **집계 경고 1건**(선택): `"N개 owned 유닛이 아직 미지원(추천 제외):
  <name_en 목록>"`. 유닛당 개별 경고는 노이즈(미인코딩 owned ~99명)라 하지 않는다.
  (백엔드가 이미 `excluded_slugs`로 표시하므로 프론트 경고는 얇게 유지.)

**ExiaInvasion 경로 (`exiaImport.ts`) — 무변경.** 짧은 이름 alias 테이블은 그쪽
테스트(97/97)가 검증한 대로 유지. 두 경로가 이제 서로 다른 해석기를 쓰므로 alias
충돌이 근본적으로 사라진다.

### 모호한 엔트리 (확정값)

Fienn 게임 지식으로 확정(2026-07-18):

- **71 Soline · 321 Marciana** → 맵에 없음(base 미인코딩) → 제외. variant(74·322)만
  각자 slug로.
- **392 Rei(라이)** → 맵에 없음(별개 캐릭터, 미인코딩) → 제외.
- **831 Rei(레이)** → `rei-ayanami`.
- **834 Rei (Tentative Name)** → `rei-ayanami-tentative-name`.
- **101 Drake** → `drake-signature` (Fienn 애장품 보유).
- **150 Julia** → `julia` (미육성, 애장품 없음).

drake/julia 두 엔트리는 **투자 의존**이라 현재 Fienn 로스터 기준으로 고정하고, 맵
주석에 그 사실과 근본 해법(아래 후속)을 남긴다.

## 후속으로 미룸 (이번 범위 밖)

**SSR-애장품 자동 판정.** drake/julia base-vs-signature를 정책 고정 대신 실제 신호로
읽는 근본 해법: 유닛의 장착 애장품 등급이 SSR이면 signature. 게임 메커니즘상 타당하나
지금 안 만든다 —
1. 수집기가 **Collection 탭을 캡처하지 않는다**(Equipment/Skill/Cube만). 확장 필요.
2. 로컬 데이터로 "signature = SSR `favorite_rare`" 필드값을 **검증 불가**(SR 샘플
   1개뿐, Collection 탭은 v-if라 fixture에 미포함).
3. Fienn 로스터에서 실제로 갈리는 건 **Drake 1명**(Julia 미육성) — ROI 낮음.

확정하려면 Fienn 로그인 브라우저로 signature 보유 유닛의 Collection 탭을 1개 캡처해
`favorite_rare`/`favorite_type` 필드를 확인하면 된다. `docs/engine-gaps.md` 또는
수집기 `RECIPE.md`에 후속 항목으로 기록.

**must-include(핀) 추천.** 유저가 "꼭 포함시킬 니케"를 지정하면 그 유닛을 포함한
조합만 탐색하는 기능(Fienn 미래 방향 2026-07-18). 별도 후속 스펙 =
`search_best_decks(specs, boss, must_include=[slugs])` 제약 + 프론트 핀 UI. **지금
안 만든다(YAGNI).** 이번 설계가 그 기능의 토대와 잘 맞물린다:
- 미인코딩 유닛을 draft에 유지 → 유저가 핀 후보를 로스터에서 볼 수 있음(핀 UI 전제).
- resource_id 맵 → 각 유닛에 안정적 신원 → 핀을 이름이 아닌 그 신원 위에 얹으면 깔끔.
- **핀은 인코딩된 유닛 한정**: 엔진이 시뮬 못 하는 유닛은 핀으로도 딜 계산이 안 되므로,
  애정 캐릭을 실제로 핀하려면 그 유닛 인코딩이 선행돼야 한다(= Phase 3 커버리지가
  이 기능의 실질 동력). 핀 UI는 loadable 유닛만 선택 가능하게 하거나 경고로 게이팅.

## 테스트

- **맵 drift 테스트** (`resourceIdSlugMap.test.ts`): 맵의 모든 slug가 백엔드
  `ENCODED_SLUGS`에 존재하고(오타/삭제 잡기), 모든 인코딩 slug가 맵에 정확히 1개
  resource_id로 존재한다(누락 잡기). 인코딩 slug 목록은 테스트 픽스처로 복제하거나
  백엔드에서 생성한 JSON을 소비 — 구현 시 결정.
- **`rosterImport.test.ts` 확장**: (a) 맵 히트 유닛이 올바른 slug로 매핑, (b) base
  Soline/Marciana·Rei(라이)가 제외되고 집계 경고에 이름이 뜸, (c) Drake→signature·
  Julia→base, (d) 정확 스탯(raid400/actual)·오버로드·스킬레벨·큐브 매핑은 회귀 없음.
- **`ImportRosterButton` 회귀**: `units` 형식 감지·병합이 그대로 동작, base+variant
  중복 병합이 사라졌는지 확인.
- 기존 프론트 스위트(97) 그린 유지, `tsc -b` 클린.

## 열린 항목 / 가정

- 맵은 owned(159)에서 저술 → 인코딩 60을 전부 덮는지 drift 테스트가 강제. owned에
  없는 인코딩 유닛이 있으면(가능성 낮음) 디렉토리 CDN에서 그 resource_id를 별도 확보.
- **미인코딩 owned 유닛은 draft에 유지**(Fienn 결정 2026-07-18) — 추천 성능(정확도·
  속도) 영향 0(백엔드가 탐색 진입 전 제외)이고 애정 캐릭 등 보유 가시성을 지킨다.
  raw 파생 slug가 두 미인코딩 유닛에서 우연히 겹치면 병합 충돌이 가능하나(코스메틱,
  둘 다 어차피 제외됨) 실질 무해 — 필요 시 병합 키에 resource_id 병용은 후속.
