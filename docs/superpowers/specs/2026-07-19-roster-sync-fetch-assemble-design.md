# 로스터 동기화 — 페치+조립 슬라이스 설계 (Phase 7)

작성 2026-07-19. 상태: **구현 완료 (2026-07-19).** 6개 TDD 태스크로 구현, 전체 백엔드
804 passed, 최종 브랜치 리뷰(opus) "ready to merge". 계획·경과: `docs/superpowers/plans/
2026-07-19-roster-sync-fetch-assemble.md`. 산출: `backend/app/{blablalink_api,roster_assembly,
overload_decode}.py` + `stat_assembly.py`에 HP 추가(measured HP로 159/159 피팅) + `tables.json`에
오버로드 값 테이블. parity: 스탯 159/159(<1.0)·오버로드 77/77(정확). **DEF=0**(시뮬레이터 미소비).

**타 유저 sync 전 반드시 해결할 전제조건 (이 슬라이스는 Fienn 계정 parity만 검증):** 조립
경로에 never-invent 원칙상 옳지만 Fienn이 안 굴린 입력에 KeyError를 내는 지점 4곳 —
① `overload_value` 미관측 `(타입,레벨)` · ② `assemble_overload` 미등록 타입명 · ③
`corporation_atk`/`research_hp`의 `research_ranks[tid]` 직접 인덱싱 · ④ `blablalink_api`
outpost 직접 인덱싱. 멀티유저엔 **CDN 오버로드 1~15 전체 커브 + 완전 타입명표 + 방어적
research lookup**이 필요(아래 "값 테이블" 소스 (b)). 서브프로젝트 3~7 사안.

## 위치와 범위

Phase 7 정찰(Stage 1, 2026-07-19 완료)이 **ShiftyPad 공개 공유 URL로 타 유저 로스터를
크로스계정 조회 가능**함을 실측 확인했다(`docs/decisions.md`, `docs/roadmap.md` Stage 1).
대상은 **일반 유저 대상 호스티드 멀티유저 sync**(Fienn 결정, audience A).

호스티드 sync 전체는 독립 서브시스템 여럿으로 분해된다:

1. **blablalink API 클라이언트** — `(open_id, area)` + 주입 세션 → 원시 로스터 페치
2. **스탯 조립 통합** — 1의 출력 → 레벨400 스탯 + 오버로드 → 프론트 소비 형태
3. 소유권 증명 플로우 (profile_team 챌린지 → open_id 바인딩)
4. 운영자 세션 관리 ⚠️ (서비스 세션 확보·갱신 — "자격증명 저장 금지" 원칙 재결정 필요)
5. 유저 계정·바인딩 저장소
6. 프론트 sync UI
7. 배포 (현재 리모트·배포 없음)

**이 문서는 1+2만 다룬다.** 세션 주입식이라 4·5·7의 무거운 결정과 무관하게 지금 만들고
테스트할 수 있으며, 어느 sync 경로로 가든 재사용되는 핵심이다. 3·5·6·7은 별도 spec.

## 목표

`(intl_open_id, nikke_area_id)` + 인증된 세션 → **collector `roster.json`과 동일 형태의
계산된 로스터**(레벨400 hp/atk/def · 스킬레벨 · 오버로드 · 큐브 · 애장품 보유). 프론트의
**기존 `parseRosterJson`이 그대로 소비**하므로 slug 매핑·draft 병합은 재사용(포팅 0).

이 슬라이스가 완성되면 collector의 유닛별 페이지 스크래핑(159회 로드)이 **API 3콜 + 계산**으로
대체되고, 그 위에 3·4·5가 붙으면 타 유저 로스터를 추천기에 넣을 수 있다.

## 비목표

- 운영자/유저 세션 확보 — 세션은 **주입**받는다(`SessionCaller` 인터페이스). 실제 세션은 서브4.
- 소유권 증명·유저계정·프론트 UI·배포 — 별도 슬라이스.
- collector 자체 삭제 — 이 슬라이스는 collector `roster.json`을 **parity 정답지**로 쓰므로
  공식이 확증될 때까지 collector는 남는다(스탯 계산기 검증 때와 같은 논리).

## 정찰로 확정된 API 사실 (2026-07-19)

- 엔드포인트 3개, 전부 크로스계정 `code 0`:
  - `GetUserCharacters {intl_open_id, nikke_area_id}` → 보유 목록(`name_code`/`lv`/`core`/`grade`)
  - `GetUserCharacterDetails {..., name_codes:[...]}` → 유닛별 투자(장비4슬롯·옵션·큐브·애장품·호감도·스킬레벨)
  - `GetUserProfileOutpostInfo {...}` → 기업연구 랭크(`recycle_room_researches`)
- **`nikke_area_id = 81`** (인터내셔널 서버). 공유 URL uid의 앞자리(예 29080)는 ShiftyPad
  리전 id지 API area가 아니다 — 29080으로 부르면 `1303001 param invalid`.
- 무인증(세션 없음)은 `300001 game not login`으로 거부 → **호출자 세션 필요**(서브4).
- **오버로드 option_id 구조: `700 + TT(효과타입 2자리) + LL(레벨 2자리, 1~15)`.** 슬롯별
  `{slot}_equip_option{1,2,3}_id` (4슬롯×3 = 최대 12옵션). ShiftyPad는 타입별로 합산 표시.
  로컬 페어링(details.json 옵션 vs roster.json 파싱라인 77유닛)으로 디코드·타입명 역산 실증.
  타입 6·13은 "장비 효과" 라인이 아니라 기초 스탯으로 접혀 표시됨(스탯 때의 "이름≠동작" 패턴).

## 구조

두 계층으로 나눈다. 각 계층은 단독 이해·테스트 가능하다.

```
backend/app/blablalink_api.py    페치 계층: SessionCaller 프로토콜 + fetch_roster
backend/app/roster_assembly.py   조립 계층: 원시 dict → 유닛별 레벨400 스탯+오버로드 (순수)
backend/app/stat_assembly.py     (기존) 순수 공식 — assemble_hp 신규 추가
backend/app/overload_decode.py   option_id → (타입,레벨) → 값 → 타입별 합산 → 이름
data/nikke-stat-tables/tables.json  (기존 스냅샷) + HP 곡선 + 오버로드 값 테이블 추가
```

### 페치 계층 `blablalink_api.py`

```python
class SessionCaller(Protocol):
    def call(self, endpoint: str, body: dict) -> dict: ...   # code!=0이면 raise

def fetch_roster(caller: SessionCaller, open_id: str, area: int = 81) -> dict:
    """collect.js --details가 쓰는 그 형태로 반환:
       {owned:[...], character_details:[...], recycle_room_researches:[...]}"""
```

반환 형태를 **`collect.js --details` 출력과 일치**시킨다 → `build_stat_ground_truth.py`와
녹화 픽스처가 이미 그 형태라, 조립 계층이 collector 경로와 sync 경로에서 동일하게 동작하고
녹화 응답으로 목킹된다. 세션(`SessionCaller`)은 주입 — 이 슬라이스는 세션 확보 방법을 모른다.

### 조립 계층 `roster_assembly.py`

`build_stat_ground_truth.py`와 `test_stat_assembly.py`에 **중복된** "details 필드 → 계산기
입력 → 레벨400 스탯" 로직을 여기로 끌어올려 하나로 통합한다. 빌더·테스트·sync 셋이 한 경로를
공유한다(중복 제거는 이 슬라이스의 targeted 개선).

```python
def assemble_unit(tables, directory_entry, owned, detail, research_ranks) -> UnitStats
    # 조인: owned(grade/core/lv) + detail(투자) + directory(resource_id/class/corp/sub_type)
    # 스탯: assemble_atk + assemble_hp (extra_flat = affinity+corp+Σequip+cube+collectible)
    # 오버로드: overload_decode로 4슬롯 옵션 → 합산 {name, value} 라인
    # 캐리: 스킬레벨·큐브·애장품 보유

def assemble_roster(tables, directory, raw) -> list[UnitStats]

def to_roster_json(units) -> dict
    # collector roster.json 형태: {units:[{name_en, resource_id, raid400{hp,atk,def},
    #   actual?, skill_levels, overload:[{name,value}], pve_cube, ...}]}
```

### HP (신규)

`assemble_hp`를 `assemble_atk`와 동형으로 추가한다(HP 기초곡선은 스냅샷에 이미 있음).
**HP 계수는 실측 확정한다** — collector `roster.json`이 측정 HP(`raid400.hp`)를 담으므로,
ATK 때와 똑같이 159유닛×2레벨로 피팅·전수대조한다. 정답지 fixture에 측정 HP를 추가한다.
장비 레벨업 HP 라인이 half-up이 아닌 관측(24590.5→24590)이 있어 **HP 반올림 규칙을 먼저
피팅에서 확정**한다. DEF는 시뮬레이터가 소비하지 않음이 확인돼(`raid_simulator.py`는
`base_stats[slug]["atk"]`와 `["max_hp"]`만 읽음) **0으로 둔다**. (`max_hp`는 HP비례 ATK
메커니즘 1기 Maiden: Ice Rose가 사용 → HP 정확도가 그 유닛에 필요.)

### 오버로드 `overload_decode.py`

```python
def decode_option(option_id: int) -> tuple[int,int] | None   # 700TTLL -> (타입,레벨)
def overload_value(tables, effect_type, level) -> float       # (타입,레벨) -> %
def assemble_overload(tables, detail) -> list[dict]           # 타입별 합산 {name, value}
```

**값 테이블 `(타입,레벨)→%`** 는 두 독립 소스로 확정한다:
- (a) 로제타: `roster.json`의 파싱된 오버로드 값(77유닛) — 같은 타입이 단일 슬롯·단일 레벨로
  나오는 유닛으로 per-level 값을 역산, 나머지는 합산식으로 검증.
- (b) CDN 오버로드 테이블 — equipment/affinity처럼 스냅샷 가능한지 구현 시 확인(`collect.js
  --tables` 확장). 있으면 (a)는 검증용.

타입→한글이름 맵도 로제타로 확정(정찰서 6/~10 타입 역산됨: 7=최대장탄·9=차지대미지·
10=차지속도·11=크리확률·12=크리대미지·5/8=우월코드/공격력). 타입 6·13은 기초 스탯으로
접히므로 오버로드 라인에서 제외하고 해당 스탯에 반영할지 구현 시 결정.

## 출력 형태

프론트 `rosterImport.ts`의 `RosterUnit` 계약을 그대로 낸다(단일 진실):

```
{ name_en, resource_id,
  raid400: {hp, atk, def(=0)}, actual?: {hp, atk, def},
  skill_levels: {skill1, skill2, burst}, overload: [{name, value}],
  pve_cube: {name, level} | null }
```

- **스킬 매핑**: API `skill1_lv`/`skill2_lv`/`ulti_skill_lv` → `{skill1, skill2, burst}`
  (ulti→burst).
- **서명(signature)은 이 출력에 담지 않는다.** 현재 프론트는 손유지 `SIGNATURE_OWNED`
  집합으로 서명 보유를 판정한다(`resourceIdSlugMap.ts`). API details의 애장품 tid(2xxxxx
  블록)로 이를 자동판정하는 건 **별개 이연 항목**(Phase 7 잔여 ③)이며 이 슬라이스 밖이다.
  애장품 tid는 조립 계층 내부에서 계산기의 `collectible_atk`에는 쓰이지만 출력 계약에는
  넣지 않는다.

`parseRosterJson` → `mergeCollectorDrafts`가 slug 매핑·서명·병합을 이미 처리한다. sync는
스탯·오버로드에 대해 authoritative이므로 덮어쓰기가 올바른 동작(`mergeCollectorDrafts`가
이미 그렇게 함 — 오버로드 포함으로 클로버링 리스크 해소).

## 테스트 전략

- **parity (핵심)**: 조립 계층 출력을 collector `roster.json`과 유닛별 대조 — 스탯
  159유닛(hp+atk), 오버로드 77유닛(타입별 합산값). B2가 ATK 159/159이므로 이 대조가
  통과하면 HP·오버로드 모델까지 실측 확증된다. `roster.json`은 gitignored라 이 테스트는
  로컬 데이터 의존(정답지 fixture 방식으로 커밋 가능한 부분은 커밋).
- **HP 모델 피팅**: `test_stat_assembly.py`의 ATK 테스트와 대칭으로 HP를 159×2레벨 전수대조.
- **오버로드 값 피팅**: 로제타 77유닛에 대해 `(타입,레벨)→값` 테이블 전수대조.
- **페치 계층**: 녹화 응답(픽스처)으로 `fetch_roster`가 3콜을 올바른 body로 부르고
  `collect.js --details` 형태로 합치는지. `SessionCaller` 목킹.
- **디코드 단위**: `decode_option(7000811)==(8,11)` 등 경계·0(빈 슬롯) 케이스.
- 회귀: `build_stat_ground_truth.py`가 통합된 조립 계층을 쓰도록 바뀌어도 fixture가 동일 산출.

## 위험

- **오버로드 값 테이블 도출**: 합산 라인이라 per-level 값이 가려질 수 있음 — 단일-슬롯·단일-레벨
  유닛이 충분한지(77유닛), 부족하면 CDN 테이블(b)로 보강. 두 소스 병행이 안전장치.
- **HP 반올림**: ATK와 다를 수 있음(관측된 half-up 아님 사례) — 피팅에서 먼저 확정.
- **리전**: `nikke_area_id=81`만 확인(Fienn 두 계정+공개샘플 전부 81=인터내셔널). 타 리전
  유저 area 발견은 서브3/5 사안 — 이 슬라이스는 area를 인자로 받으므로 무관.
- **세션 만료·레이트리밋**: 서브4 사안. 이 슬라이스는 주입 세션이 유효하다고 가정.
- **collector 형태 drift**: 출력이 `roster.json` 형태에 결합됨 — `parseRosterJson`의
  `RosterUnit` 계약을 단일 진실로 삼고 양쪽 테스트가 지킨다.
