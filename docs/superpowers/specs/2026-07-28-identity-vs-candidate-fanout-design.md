# 정체성 그룹과 후보 팬아웃의 분리 — 설계

- Date: 2026-07-28
- Status: 승인됨 (Fienn, 2026-07-28)
- 관련: `docs/roadmap.md`의 To-Do "정체성 그룹과 후보 팬아웃을 분리",
  `docs/superpowers/specs/2026-07-18-weapon-transform-design.md`(MODE_VARIANTS 도입),
  `docs/superpowers/specs/2026-07-25-korean-display-names-design.md`(애장품 쌍의 표기)

## 배경

`registry.MODE_VARIANTS`는 무기변형 계획 2에서 "한 소유 캐릭터가 여러 덱 후보를
낳는다"를 표현하려고 생겼다. 그런데 그 표 하나가 지금 성격이 다른 두 질문에
답하고 있다.

- **(a) 누가 같은 캐릭터인가** — 한 소유 유닛을 두 자리에 앉히지 못하게 막는다.
  `deck_search._VARIANT_GROUP` → `variant_base` · `_no_variant_clash`,
  그리고 이를 통해 `deck_allocation`(5덱 전체에서 재사용 금지)과 `surrogate`.
- **(b) 엔진이 무엇을 고를 수 있는가** — 소유 상태 하나를 후보 여러 개로 펼친다.
  `user_roster.load_roster`의 팬아웃, `api._variant_alternatives`,
  `supported_units`의 `candidates` 필드.

애장품(`-signature`) 13쌍은 **(a)는 필요하지만 (b)는 절대 아니다.** 애장품 보유
여부는 이미 정해진 사실이지 엔진이 고를 선택지가 아니다. (b)에 들어가면 애장품이
없는 유저에게 엔진이 `-signature` 인코딩을 골라줄 수 있다 — 없는 아이템의 효과를
얻는다. 그래서 "`MODE_VARIANTS`에 애장품 쌍을 추가한다"는 처방은 틀렸고, 표를
둘로 나눠야 한다.

### 실측한 결함

```
variant_base('miranda-signature')                      -> 'miranda-signature'
_no_variant_clash([miranda, miranda-signature])        -> True   # 서로 다른 캐릭터로 봄
_no_variant_clash([bready-lingering, bready-recommended]) -> False  # 모드 쌍은 정상
```

엔진이 `miranda`와 `miranda-signature`를 다른 캐릭터로 본다. **지금은 실제 로스터로
닿지 않는다** — `rosterImport.ts`가 `favorite_item` 플래그로 캐릭터당 슬러그를 하나만
만들기 때문이다. 손으로 고친 `roster.json`, 낡은 임포트, 수집기 변경으로 둘 다
들어오면 한 캐릭터가 두 덱에 앉아, 유니온 5덱의 "재사용 불가" 전제가 깨진다.

이번 브랜치가 만든 결함이 아니라 원래 있던 빈틈이다.

## 결정

### 1. 정체성의 출처 — 매니페스트의 `data_slug`에서 파생

세 안을 놓고 골랐다.

- **A. `data_slug` 그룹핑에서 파생** ← 채택
- B. `CHARACTER_GROUPS` 17그룹을 손으로 작성
- C. `MODE_VARIANTS` 파생 + "`-signature`로 끝나면 base와 같은 캐릭터" 규칙

A를 고른 이유는 **데이터가 이미 정답을 갖고 있어서**다. 인코딩된 93개 슬러그를
매니페스트의 `data_slug`로 묶으면 정확히 17그룹이 나오고, 그게 MODE_VARIANTS
4그룹 + `-signature` 13쌍과 **완전히 일치한다. 오탐이 하나도 없다.**

```
bready                  -> bready-lingering, bready-recommended
cinderella-crystal-wave -> ...-mg, ...-snipe
diesel-winter-sweets    -> ...-intro, ...-highlight
rapi-red-hood           -> rapi-red-hood, rapi-red-hood-b1
drake / flora / helm / julia / laplace / miranda / moran /
phantom / privaty / rosanna / sugar / tove / zwei
                        -> 각각 base + base-signature
```

`data_slug`가 슬러그와 다른 경우는 20건뿐이고, 그 20건이 전부 "같은 캐릭터의 다른
빌드"다. 즉 이 필드는 이미 사실상 캐릭터 식별자로 쓰이고 있다.

B는 애장품을 새로 인코딩할 때마다 추가해야 하고, 빠뜨리면 같은 버그가 조용히
재발한다. C는 표가 없는 대신 명명 규칙에 의존하는데, A와 달리 그 규칙이 데이터로
검증되지 않는다.

**A가 지불하는 비용**: `data_slug`는 원래 "어느 파일에서 데이터를 읽나"라는 데이터
출처 필드다. 거기에 정체성 의미를 얹으면, 나중에 데이터 출처 사정으로 `data_slug`가
바뀔 때 정체성이 조용히 따라 바뀐다. **이 결합은 기대 그룹핑을 고정하는 테스트로
방어한다** — 그룹 수와 구성이 달라지면 테스트가 먼저 깨진다.

### 2. 새 API — `registry.character_map()`

```python
def character_map() -> dict[str, str]:
    """슬러그 -> 그 슬러그가 어느 소유 캐릭터의 빌드인가."""
```

- **빌드가 2개 이상인 캐릭터의 슬러그만 담는다.** 솔로 캐릭터는 `.get(slug, slug)`로
  자기 자신이 되므로 넣을 필요가 없고, `_no_character_clash`가 지금과 똑같이
  "표에 없으면 건너뛴다"는 싼 모양을 유지한다(덱 탐색 최내곽 루프다).
- `get_skill_value_manifest`가 `pkgutil` 지연 스캔이므로 이 맵도 같은 캐시 패턴으로
  **지연 생성**한다. `registry` 임포트 시점에 만들면 패키지 자기 자신을 스캔하게 된다.
- `deck_search`는 모듈 임포트 시점에 `_CHARACTER_OF = character_map()`으로 받아
  모듈 상수로 둔다. 테스트가 지금처럼 monkeypatch할 수 있어야 하기 때문이다.
  `deck_search`를 임포트하는 skill_rules 모듈은 없으므로 순환은 생기지 않는다.

`MODE_VARIANTS`는 **(b) 팬아웃 전용으로 남는다.** 내용은 그대로고, 독스트링만
"이 표는 정체성 표가 아니다 — 정체성은 `character_map()`이다"로 정정한다.

### 3. 이름 — `variant`에서 `character`로

두 개념을 분리하는 게 이 작업의 요점인데 이름에 `variant`가 남으면 다시 섞인다.

| 기존 | 새 이름 |
|---|---|
| `deck_search._VARIANT_GROUP` | `deck_search._CHARACTER_OF` |
| `deck_search.variant_base` | `deck_search.character_of` |
| `deck_search._no_variant_clash` | `deck_search._no_character_clash` |

영향 범위: 소스 4개(`deck_search`·`deck_allocation`·`surrogate`·`bready.py`의 주석),
테스트 2개(`test_deck_search`·`test_resource_id_slug_map`), 스크립트 1개
(`measure_thin_draft.py`). 기계적 치환 22곳 + 주석 문구 정리.

`VARIANT_BURST_TIERS`와 `SOLE_TIER1_SLUGS`는 **그대로 둔다.** 이 둘은 진짜로 모드
변형에 대한 얘기지 정체성이 아니다.

## 결과

새 맵은 기존 `_VARIANT_GROUP`의 **정의역 위에서 값이 완전히 동일한 순수 확장**이다.

- `bready-lingering` → `bready` (기존과 동일 — base가 인코딩되어 있지 않아도
  `data_slug`가 `bready`라 키가 맞는다)
- `rapi-red-hood` → `rapi-red-hood` (`data_slug` 미지정이라 자기 자신)
- 여기에 `miranda-signature` → `miranda` 등 13쌍이 **추가**된다

그래서 기존 네 모드(단일 덱 추천 · 레이드 분배 · 드래프트 · 고정 편성 평가)의 동작은
변하지 않아야 하고, 변하지 않음을 회귀로 확인한다.

애장품 쌍이 둘 다 든 로스터가 들어오면(손으로 고친 `roster.json` 등) 엔진은 이제 둘을
한 캐릭터로 보고 **둘 중 점수가 높은 쪽만 앉힌다.** 팬아웃에는 넣지 않으므로,
애장품이 없는 유저에게 엔진이 `-signature`를 골라주는 일은 여전히 일어나지 않는다.

## 테스트

- **drift 방어**: `character_map()`이 `data_slug` 그룹핑과 일치하고 17그룹임을 고정.
  `data_slug`에 정체성을 얹은 결합의 방어선이다.
- **결함 회귀**: `character_of('miranda-signature') == 'miranda'`,
  `_no_character_clash([miranda, miranda-signature])`가 `False`.
- **역방향 회귀(핵심)**: 애장품 쌍이 (b)로 새어들어가지 않음을 못박는다 —
  `load_roster`가 miranda 1기에 스펙 1개만 내놓는다 · `supported_units`의 miranda에
  `candidates`가 없다 · `_variant_alternatives`에 `-signature` 키가 없다.
- **분배**: 애장품 쌍이 든 로스터로 `deck_allocation`이 두 덱에 같은 캐릭터를
  앉히지 않는다.
- **기존 모드 불변**: 백엔드 전체 스위트(기준선 1413 passed / 3 skipped).

## 검증

전체 스위트 + 실제 로스터 픽스처로 네 모드 회귀 + `/verify`로 라이브 확인.
