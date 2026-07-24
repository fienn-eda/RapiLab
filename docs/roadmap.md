# NIKKE Deck Builder — 로드맵 & 진행 현황

우리가 뭘 만들고 있고, 어디까지 왔고, 다음에 뭘 할지 한눈에 보는 문서.
큰 그림은 **로드맵(단계)**, 작은 단위 작업은 **To-Do**에서 관리한다.
결정의 배경은 `docs/decisions.md`, 엔진 함정/패턴은 `docs/insights.md`,
인코딩된 니케 목록(Burst 단계별)은 `docs/encoded-nikkes.md`,
엔진 갭 인벤토리(확장 우선순위)는 `docs/engine-gaps.md`,
스킬 인코딩 방법은 `nikke-skill-encoding` 스킬 참고.

- 마지막 갱신: 2026-07-19
- 브랜치: `wip/scaffolding` (`worktree-plans-frontend3-encoding` 머지 완료)
- 테스트: **906 passed** (2026-07-19, **무기변형 계획 2 착지** — v1이 백로그로 남겨둔
  세 항목을 전부 닫음: **cinderella-crystal-wave**가 `registry.MODE_VARIANTS`로
  `-mg`/`-snipe` 두 정적 슬러그로 확장(로스터가 소유 유닛 1개를 후보 여러 개로
  fan-out, 덱 탐색은 `_no_variant_clash`로 두 모드 동시 편성을 금지) · **rapi-red-hood**의
  120노멀 프로젝타일 발사기가 `SquadContext.full_burst_windows` + `boss_core_hittable()`
  노출로 완성(부착 누적 → 다음 FB 진입에서 일괄 폭발) + 새 슬러그 `rapi-red-hood-b1`
  (Combat Assist를 실제 B1 후보로 편성, `VARIANT_BURST_TIERS`로 B3와 다른 티어에
  착석) · **snow-white-heavy-arms**는 검증 결과 신규 상태머신 없이 세그먼트 +
  `every_during_segment`/`every_outside_segment` per-shot 게이팅만으로 풀림(스펙의
  검증 패스 종결). 신규 `projectile_attachment` 데미지 타입(projectile_explosion과
  나란히). 상세는 `engine-gaps.md`·`docs/superpowers/specs/2026-07-18-weapon-
  transform-design.md`(상태: 계획 2 착지 완료) 참고. was 862(계획 2 착수 직전 —
  774 이후 gap #10 배치·아군 총탄 카운터·Ein/Raven/Sakura 인코딩·무기변형 v1·
  red-hood 재검증 등 여러 배치가 이 로그에 반영되지 못한 채 누적돼 있었음, 그 구간
  상세는 `encoded-nikkes.md`/`engine-gaps.md` 로그 참고).
- 이전: **774 passed** (2026-07-18, **스킬 수치 드리프트 감지** — 머지 후 실측,
  wip/roster-import 합류분 +6 포함.
  `scripts/check_skill_value_drift.py`: dotgg-소스 매니페스트 22개(21유닛+
  drake-signature)의 스킬 수치를 라이브 lootandwaifus와 대조(매 실행 전체 재수집,
  `--offline`/`--slug` 지원, DRIFT 시 exit 1). 비교는 설명 템플릿이 참조하는
  슬롯만(브리드 잔여 슬롯 오탐 수정, Fienn 승인) + curl `-sS --fail` + fetch 실패
  경고를 해당 매니페스트에 귀속(낡은 파일 비교가 OK로 위장 불가). **라이브 실측:
  22 OK, 0 DRIFT** — 현재 dotgg-소스 유닛 중 패치로 어긋난 유닛 없음. 부수 효과로
  lootandwaifus 데이터 18유닛 신규 확보. SBS 사례(dotgg 동결로 패치 수치 미반영,
  `insights.md`)가 계기. was 746+4(블라블라링크 수집기 배치).)
- 이전: **746 passed** (2026-07-17, **`worktree-plans-frontend3-encoding` →
  `wip/scaffolding` 머지** — Ein·Raven·Sakura 인코딩 + `scheduled_nukes`/`shot_times`
  확장 + 워크트리 데이터 동기화 스크립트·훅이 dotgg weapon 스탯 수집 작업과 합류.
  충돌은 `docs/decisions.md` 위치 충돌 1건뿐, 양쪽 항목 모두 보존. **머지 후 실측:
  60명 인코딩, 매니페스트 56/60, API 로더블 56/60** — 상충하던 두 주장(56/60 vs
  53/57) 중 56/60이 사실로 확인됨(53/57은 3유닛 인코딩 전의 값). 잔여 미로더블 4 =
  픽스처 재배열 대기(anis-star·asuka-shikinami-langley-wille·neon-vision-eye·
  privaty). was 730+16.)
- 이전: **730 passed** (2026-07-17, **Raven Shock Wave 모델 정정** — Fienn 지적:
  스택은 풀차지마다 독립 DoT가 겹치는 게 아니라 **카운터 1개가 +1씩 누적(상한 10)**
  하고, `lasts for 5 sec`는 **카운터 수명이 풀차지마다 갱신**되는 것. 그녀의 최대 공백이
  3초(재장전)라 5초 창을 넘지 않아 **카운터가 전투 내내 안 죽고 10스택 고정** — 최초
  구현의 정상상태 5스택 대비 정확히 2배. Shock Wave 1.28억→**2.92억**, 총 1.81억→
  **3.45억(1.9배)**. 틱-발사 동시각 경계는 엔진 관례(각 틱이 자기 시각의 count 조회)로
  통일. 회귀 테스트 4종 추가(스택 누적·캡·창 안 갱신·창 초과 리셋). was 726.)
- 이전: **726 passed** (2026-07-17, **Raven·Sakura 인코딩 배치** — 검증 배치가
  "인코딩 가능"으로 판정한 둘을 인코딩. 착수해보니 판정이 절반만 맞았음: **Sakura는
  확장 불필요**가 맞았지만(Full Glory가 배틀스타트 강제발동+cd30이라 Sakura Petals
  스케줄이 전투 전 확정 → `scheduled_nukes`가 그대로 맞음), **Raven은 소규모 확장 1건
  필요**했음 — Shock Wave가 풀차지마다 DoT를 까는데 schedule 함수가 발사 시각을 볼 수
  없었음. `context.shot_times`로 노출(엔진이 이미 `shot_times_by_slug`로 갖고 있어
  신규 계산 없음, Ein 시그니처 무변경). Raven 실측: RL이 1초마다 풀차지라 5초 창 최대
  동시 5스택 → **상한 10 미도달로 자원 모델링 불필요**. Single Point Attack은 부위파괴
  트리거라 Ark Ranger식 floor/ceiling 브래킷(Fienn 판정), Vital Attack은 inert라 defer.
  Sakura 버스트 DoT는 10연타가 각각 1스택 → 351.6%/초×10틱(Fienn 판정). E2E: Raven
  Shock Wave 1.28억(최대 소스, ceiling 1.844억 > floor 1.809억), Sakura 총 2.397억.
  **60명, 매니페스트 56/60, API 로더블 56/60.** was 708.)
- 이전: **708 passed** (2026-07-17, **미검증 5유닛 검증 배치 + Ein 인코딩** —
  로드맵 백로그가 "미검증"으로 남겨둔 5명을 실제 스킬 텍스트로 검증: **ein 언블록
  → 인코딩 완료**, **raven·sakura-bloom-in-summer도 인코딩 가능**(부위파괴만 defer,
  다음 배치), **scarlet-black-shadow(gap #10)·milk-blooming-bunny(gap #11)는 신규 갭
  기록**. Ein은 Near Feather 소환체가 딜의 대부분인데 개체 수가 공격 주기를 바꿔
  `periodic_nukes`(고정 간격)로 표현 불가 → 신규 옵트인 확장 **`scheduled_nukes`**
  (유닛이 결정론적 시각 리스트를 계산, 엔진은 방출만). Fienn의 클라 데이터마이닝
  (6기 상한·개체별 수명·8초 쿨에서 기수당 -16% 합연산) + **영상 실측**(FB 진입 0.8초
  후 첫 타격, 0.3초 간격, 총 31회)으로 모델 확정 — 실측 31회를 정확히 재현하는
  0.3초 스로틀을 가정으로 명시하고 회귀 테스트로 고정. 곱연산은 관측의 절반이라 배제.
  **58명, 매니페스트 54/58, API 로더블 50→54/58** — 검증 중 ein이 로더블이 아닌 걸로
  나왔으나 이는 **워크트리 함정**이었음: `data/dotgg/`는 gitignore 대상이라 워크트리로
  복사되지 않아 메인(71개)보다 18개 적은 상태였고, ein·ark-ranger-black·prika·
  marciana-marine-study의 weapon 파일이 거기 있었다(Fienn 지적, 2026-07-17). 동기화 후
  넷 다 로더블 — **prika 로더블화로 mint+prika Encore 시너지가 덱 탐색에서 처음 효력**.
  Ein E2E: 180초에 페더 280타 9212만(본인 평타 5101만 상회, 최대 딜 소스).
  정정: engine-gaps의 "true의 DEF 무시 여부 확인 대기"는 이미 해결·배선된 낡은 메모였고,
  이게 ein을 불필요하게 막고 있었음. was 692.)
- 이전: **692 passed** (2026-07-17, **ProcessPool 시뮬 병렬화 + Rapi 인코딩 완성** —
  ① `SimPool`(지연 스폰 ProcessPoolExecutor, 워커 초기화 1회에 specs+boss 전달,
  태스크는 슬러그 튜플, 배치 32건 미만은 인라인): `search_best_decks`(canonical
  스코어링·순열 정련·prune 측정)·`allocate_decks`(+폴리시)의 맵 구간을 병렬화,
  스왑 언덕오르기는 순차 유지(수락된 스왑이 다음 판단의 상태를 바꿈). 직렬 경로
  비트 동일(패리티 테스트 3종). **실측: 로더블 50유닛 5덱 분배 97.25초**(16코어,
  워커 15) — 42유닛 282.17초 베이스라인 대비 더 큰 로스터로 2.9×↑, **5덱 전부
  생성**(leftover 25, 합계 31.0B, Electric 보스). 1분 예산 잔여 초과분은 순차
  스왑 단계(≤45초 캡)가 지배 — 후속 레버는 스왑 후보 배치평가 또는 스왑 예산
  축소(품질 트레이드오프, Fienn 판단). ② rapi-red-hood Attachable Projectiles
  배틀스타트 상시 self 2건(PE Damage ▲100.6% + Electric 한정 원소우위 0.1)
  인코딩, E2E로 Electric 보스에서 버스트 딜 정확히 ×1.100 확인. was 684/682.)
- 이전: **682 passed** (2026-07-17, **매니페스트 예외 8유닛 배치** — crown·helm·
  liter·miranda·moran·soline-frost-ticket·volume·zwei에 dotgg-소스
  `SKILL_VALUE_MANIFESTS` 추가(전 유닛 픽스처=dotgg 네이티브 슬롯 정확 일치,
  drop_tokens 0건) + 배치 테스트 파일 픽스처 별칭 + `KNOWN_MANIFEST_EXCEPTIONS`
  12→4. **매니페스트 53/57, API 로더블 50/57, 로더블 B1 4→10명** — 5덱 분배가
  3덱에서 멈추던 B1 부족이 해소됨. Fienn 결정 3건 반영(처리량 레버=ProcessPool
  병렬화 / evaluate_deck 최적화는 103.43ms에서 중단 / 이 배치를 최우선 —
  `decisions.md` 참고). was 674.)
- 이전: **674 passed** (2026-07-17, **Phase 5 Task 6 — `POST /api/recommend-raid`
  + `/api/recommend`가 `search_best_decks`로 전환** — 기존 `/api/recommend` 테스트
  전부 그린 유지(회귀 없음). +1은 계획 외 회귀 테스트: 실측정(전체 57유닛 로스터
  분배) 도중 `_build_cinderella`가 이미 언랩된 `sv["flawless_glass"]`를 다시
  `["flawless_glass"]`로 인덱싱하던 기존 버그(KeyError, 유닛 테스트 픽스처는
  잡지 못함)를 발견해 즉시 수정 + 회귀 테스트 추가. 실측(최종 리뷰 픽스 2건 반영
  후 재측정): 로더블 42유닛 전량을 `allocate_decks`로 5덱 분배 — **282.17초,
  3덱 생성**(로더블 B1이 4명뿐이라 4/5번째 덱을 채울 티어 조합이 남지 않음),
  leftover 27유닛, 합계 5.18B. 최초 측정 103.92초는 데드라인 버그로 **스왑 단계가
  실행되지 않은 순수 탐욕 수치**였음 — 픽스 후 수치는 박리+스왑(≤45초)+폴리시
  전체. 수초~1분 예산을 크게 초과 — 타이어 캡 튜닝/병렬화는 Fienn 결정 대기.
  참고: prika는 2026-07-17 dotgg weapon 파일 수집으로 로더블이 됨 — mint+prika
  시너지가 이제 실로스터 탐색에서 효력을 가진다. was 673 (671+2, Task 6 신규 API 테스트).)
- 이전: **659 passed** (2026-07-17, **Stage 0 EffectRegistry 성능 패스** —
  total_for를 버전-무효화 세그먼트 테이블로 교체(비트 동일 출력, 패리티 넷 2건
  추가). evaluate_deck 180초 시뮬 ~2410ms → 133.66ms → 103.43ms (Stage 0.5 epoch memo, 2026-07-17 — phase-1 normal_attack_type 회귀 수정: 번들 대신 직접 단일-스탯 조회로 복귀). was 656 — 목표 50ms 미달(2.1×), 잔여는 평탄한 호출 오버헤드. 추가 최적화는 여기서 중단으로 결정(Fienn, 2026-07-17 — 부족분은 ProcessPool 병렬화로 흡수, `decisions.md` 참고))
- 이전: **654 passed** (2026-07-17 후속 배치 — 매니페스트 배치 2(29유닛, 45/57
  커버) + dotgg weapon 스탯 39파일 수집 + `dotgg_slug` 브리지 + 오버로드 옵션명
  422 검증 + 매니페스트 가드 테스트(`KNOWN_MANIFEST_EXCEPTIONS`). **API 로더블
  42/57**. was 622 통합 직후)
- 이전: **622 passed** (2026-07-17, **프론트 3단계 + Phase C 병렬 배치 통합** —
  Phase C: gap #3 member-subset scope·#6 during-FB periodic·#8 자원-fill-트리거
  아군 버프·#9 first-bullet 마커 엔진 확장 4건 + 소비자 7유닛(Ark·Arcana·Tove·
  Ada Wong[신규]·Little Mermaid·Maiden·Jill) / 프론트 3단계: 스킬값 조립 파서·
  매니페스트 하니스·roster 로더·`POST /api/recommend`. 통합 시 하니스가
  little-mermaid Bubble Wave 슬롯 오번호(lootandwaifus 좌→우 카운트 vs 모듈의
  dotgg 네이티브 컨벤션) 1건을 잡아 교정함; was 547 배치 시작 시점)
- 인코딩된 니케: **60명** (Raven[shot_times 확장 소비, 신규 ⚠] · Sakura: Bloom in Summer[신규 ⚠] +2) —
  상세는 [`docs/encoded-nikkes.md`](encoded-nikkes.md)
- **Phase C 배치 완료 (2026-07-16):** 엔진 갭 #3(member-subset scope:
  `SquadMember.weapon`+`member_subset_buff_rule`, 신규 Effect scope 없이 `slugs:`
  해석)·#6(`periodic_nukes` `during_full_burst`/`hit_count`/`own_burst_interval`)·
  #8(`resource_fill_triggered_buffs`)·#9(first-bullet 마커+`normal_attack_damage_
  multiplier`+RoundGrant 2차 패스) 4건을 닫고 즉시 소비: Ark Ranger Black(Wind-AR
  아군 지속댐)·Arcana ⚠→✅·Tove(SG 아군, 데이터 재수집)·**Ada Wong 신규 인코딩**
  (Covert Support/Flash Grenade/Secret Agent — Special Modification은 매거진-경계
  검증 후 net +2.75 근사)·Little Mermaid(Bubble Wave FB넉)·Maiden ⚠→✅(Blessings
  fill-버프)·Jill Valentine ⚠→✅(Magnum/Acid). Fienn 판정 3건(Ada 차지속도 ▼300%=
  차지시간 ×4·Flash Grenade own-burst 1초 틱·Acid refresh→정상상태 DoT) 반영.
  **다음:** Pattern B 일반 프리미티브 / 상태머신·무기변형 / 아군 총탄 카운터 /
  not-in-FB 창 필터 / dotgg 스탯 수집.
- **Ark Ranger Black floor/ceiling 브래킷 완료 (2026-07-16):** 배터리로 구동되는
  Transformation 상태(딜의 대부분)를 일반 게이지 프리미티브 없이, 신규 보스 플래그
  `BossProfile.part_destructible`로 **floor**(파츠파괴 없음 — 변신은 버스트당 10초 창)
  /**ceiling**(파츠파괴 있음 — 변신 영구) 두 갈래로 모델링. `evaluate_deck`/
  `simulate_raid`가 플래그를 `SquadContext.part_destructible`로 스레딩, DoT 스펙의
  옵셔널 `requires_part_destructible`로 브랜치별 게이팅. 엔드투엔드로 ceiling
  total_damage > floor total_damage 검증. 부위파괴 게이지 fill 자체는 여전히 미모델
  (이 유닛 전용 우회, 일반 Pattern B 프리미티브 아님) — 상세는
  `docs/superpowers/specs/2026-07-16-ark-ranger-black-transformation-design.md`,
  `docs/engine-gaps.md`(gap #2) 참고.
- **이전: Phase B gap #5 완료 (2026-07-16):** `SquadContext.boss_element` +
  `boss_is_element(element)` 조건 헬퍼(+`buff_rule`/`refreshing_buff_rule`/
  `instant_nuke_pulse_rule`에 옵셔널 condition) + `enemy_def_percent` 배선(DEF▼ 디버프,
  기존 inert). 소비: **Brid**(Wind Damage Taken 디버프 → ✅) · **Helm: Aquamarine**
  (Electric Damage Taken 정상상태 + Overload 추가딜, Burst2라 FB보너스 미적용 → ✅) ·
  **Marciana: Marine Study**(신규 Iron AR B3; Fienn 가정 rapture=1/Flagged=보스/
  High-Risk=Electric 게이팅; Whistle 자ATK·Elemental Advantage AD·DEF 디버프·Flagged
  3789% 풀버스트 넉·High-Risk 20노멀 넉). **Phase S 완료(이전):** attack/charge speed 배선
  + Dorothy: Serendipity. **다음(당시):** Phase C — 완료됨(아래).

---

## 목표

유저가 보유한 니케 중에서 **솔로 레이드(3분/180초) 총 딜량을 최대화하는 덱 구성**을
추천한다. 재료: (1) nikke.gg 데미지 공식, (2) 캐릭터별 스킬 데이터
(lootandwaifus.com 우선, dotgg 대체), (3) 유저의 실제 투자 데이터(ShiftyPad,
초기엔 수동 입력).

---

## 한눈에 보기 (단계별 현황)

| 단계 | 내용 | 상태 |
|---|---|---|
| Phase 0 | 데이터 소스 확보 + 리포 인프라 | ✅ 완료 |
| Phase 1 | 데미지 공식 엔진 | ✅ 완료 |
| Phase 2 | 레이드 시뮬레이터 (버스트·효과·공속) | ✅ 완료 |
| Phase 3 | 캐릭터 스킬 인코딩 | 🔄 진행 중 (68명, `docs/encoded-nikkes.md` 표 기준) |
| Phase 4 | 단일 최적 덱 추천 | ✅ 완료 |
| Phase 5 | 5덱(25니케) 분배 최적화 | ✅ 완료 — greedy+swap + ProcessPool 병렬화(50유닛 97초), `/api/recommend-raid`, 프론트 레이드 모드 배선까지 |
| Phase 6 | 유저 데이터 입력 UI (React) | 🔄 진행 중 (입력 폼 + 결과 UI + 라이브 API 완료) |
| Phase 7 | 자동화 (ShiftyPad 연동, 수집 파이프라인) | 🔄 Phase A 임포터 + Phase B 수집기 완료 (159/159 E2E) |

---

## 로드맵 (단계 상세)

### Phase 0 — 데이터 소스 & 인프라 ✅
- 데이터 소스 = **lootandwaifus.com 우선**, `api.dotgg.gg`(무인증 JSON, nikke.gg
  백엔드) 대체. 최신 니케(dotgg 미등재분)는 lootandwaifus로만 수집. → `dotgg_client.py`
- git 초기화, `wip/scaffolding` 브랜치, TDD 규칙(`.claude/CLAUDE.md`).
- 보조 도구: `nikke-skill-encoding` 스킬, 서브에이전트 3종
  (docs-keeper / nikke-data-collector / engine-test-runner) + 슬래시 명령어
  (`/document`, `/collect-nikke`, `/test-engine`).

### Phase 1 — 데미지 공식 엔진 ✅
- `damage_formula.calculate_damage` — Base Damage(방어 차감) × Final ATK ×
  Major(크리 포함) × 원소 × 차지 × Damage Up × Damage Taken.
- 계수(attack_coefficient)는 방어 차감 후 Base Damage 전체에 곱함 (버그 수정 완료).
- 크리 = 기대값 모델 (기본 15% / 크뎀 +50%).
- 원소 상성 +10% (`elements.py`).

### Phase 2 — 레이드 시뮬레이터 ✅
- `raid_simulator.simulate_raid` — 시간 기반 3분 전투.
- `burst_cycle.py` — 버스트 1→2→3, Full Burst 10s, 가장 느린 티어 쿨다운에 맞춰 사이클.
- `attack_rate.py` — 60fps 발사율(AR12/MG60/SMG20/SG1.5, RL·SR=차지).
- `effects.py` / `squad_engine.py` — Effect/Pulse 레지스트리, 스코프·트리거.
- `roster.py` — 유저 스탯 + 오버로드 + 큐브 조립.

### Phase 3 — 캐릭터 스킬 인코딩 🔄
- 인코딩된 28명:
  - 실전 덱 5: `anis-star`, `crown`, `rapi-red-hood`, `helm`, `privaty`
  - 버스트1 배치 10: `liter`, `little-mermaid`, `miranda`, `moran`, `rouge`,
    `d-killer-wife`, `tove`, `volume`, `zwei`, `soline-frost-ticket`
  - 버스트2 배치: `anchor-innocent-maid`, `mast-romantic-maid`,
    `ade-agent-bunny`, `blanc`, `arcana`, `arcana-fortune-mate`,
    `grave`, `brid-silent-track`, `nayuta`, `mint`, `prika`,
    `helm-aquamarine`, `velvet`
- 각 니케 = `skill_rules/<name>.py` 빌더, `registry.py`에 등록.
- 요청받은 버스트2 배치 전부 인코딩 완료. (Crown은 이미 인코딩됨.)
- 니케 데이터 수집 소스가 lootandwaifus.com 우선으로 전환됨(→ 아래 Phase 0).
- 새 엔진 갭 발견 사례들 (`references/special-mechanics.md` 참고):
  ~~본인 풀차지샷 트리거 부재~~(해결: per_shot_rules), ~~교차 유닛 트리거
  부재(Prika→Mint)~~(해결: ally_burst_activate), ammo pouch 자원 메커니즘
  (Velvet, 자원 트래킹 없음 — 잔여).
- **주기적 자동발동 스킬 엔진 확장 완료** (Fienn 승인, 2026-07-10): 버스트
  사이클과 무관하게 자체 쿨다운으로 반복 발동하는 스킬(Helm: Aquamarine
  Aegis Cannon Suppression Fire, 4초마다) — `simulate_raid`의 `periodic_nukes`
  파라미터로 지원. 기존 25개 인코딩엔 영향 없음(옵트인, 기본값 `{}`).
- **전략 전환 (2026-07-10, Fienn):** 인코딩을 하나씩 하다 갭에 부딪히는 반응적
  방식 대신, **데이터를 먼저 벌크 수집 → 갭을 집계 → ROI 순으로 엔진 최소 확장 →
  풀린 유닛 배치 인코딩**. 완전 표현 가능한 서포터는 그때그때 인코딩(동결 안 함).
  갭 집계는 [`docs/engine-gaps.md`](engine-gaps.md). 후보 44유닛 스캔 결과 **최우선
  확장 = per-shot 트리거+발사 카운터(노멀/풀차지 카운터 ~30유닛 통합)**.
- 데이터 수집 완료(미인코딩, 보류): Ada Wong, Ark Ranger Black, Asuka:Wille, Bready
  (오늘 분석 — 4명 모두 딜이 엔진 갭 뒤에 있어 보류) + 벌크 35유닛
  (`data/lootandwaifus/`, gitignore).
- **엔진 확장 완료 — 데미지 타입 모델링 (gap #4, 2026-07-10):** sustained/
  distributed/true/projectile_explosion 버프를 인스턴스 타입에 게이팅(블랭킷 배선의
  과대평가 회피). Mint의 projectile explosion 버프가 RL 아군에 적용, Rapi 버스트 넉
  태깅. Takina용 "노멀→진댐 변환" 포함. 상세 `decisions.md`·`engine-capabilities.md`.
  (미결: true의 DEF 무시 여부 / attack_damage_up 전역 여부 — Fienn 확인 대기.)
- **엔진 확장 완료 — periodic 스킬 트리거 (2026-07-11):** 자체 쿨다운 있는 Skill1/2가
  t=cd,2cd…에 버프/디버프 반복 발동(범용 전투 규칙). `simulate_raid`의 `periodic_rules`
  (버스트 사이클 前 사전 패스 — 버프는 딜 입력이므로). Rosanna·Takina 인코딩 완료.
- **엔진 확장 완료 — per-shot 트리거 + record-then-compute (gap #1, 2026-07-11):**
  발사 카운트 트리거(`per_shot_rules`, after/every N) + 모든 넉을 "버프 적용 후" 일괄
  계산(per-shot 스쿼드 버프가 버스트 넉까지 반영). 첫 소비자 Brid: Journey Ahead
  (5발마다 675% 넉). "마지막 탄"만 잔여.
- **엔진 확장 완료 — 교차 유닛 트리거 (2026-07-11, Fienn 승인):** 한 유닛이 다른
  유닛의 버스트에 반응하는 `ally_burst_activate` 트리거(`context.last_burst_slug` +
  `ally_bursted(slug)`/`all_conditions`). 첫 소비자 Prika Encore(Mint 버스트 시 발동).
  Mint·Prika를 per-shot(풀차지 스쿼드 버프) + Encore 시너지까지 인코딩 완료(🔶→⚠/✅).
  (부산물 버그픽스: Mint의 첫 버스트 前 Singing 오판정 수정 — `count>0` 게이트.)
- **버그픽스 — per-shot 버프 중첩 (2026-07-11):** `total_for`가 활성 이펙트를 합산해서,
  풀차지마다 재적용되는 다초 버프가 중첩(SR ~2배, AR ~13배)되던 문제. NIKKE는 refresh
  (중첩 아님)이므로 `EffectRegistry.add_refreshing` + `refreshing_buff_rule` 추가(직전
  동일 stat·source·scope 인스턴스를 새 적용 시각에서 truncate). Prika S1 커밋본 수치가
  정확히 하향 교정됨.
- **Mint Here I Go! 단독 구현 완료 (2026-07-11):** 시각 인덱싱(`context.burst_times`
  패리티 + `status_since` 핀)으로 단독(Dancing/Singing 교대)과 Prika 조합(Encore 핀
  시각) 모두 정확. 조합의 핀-이전 과대적용도 제거. → Mint ✅.
- **인코딩 완료:** Rosanna: Chic Ocean, Takina Inoue, Brid: Journey Ahead 승급,
  Mint(Here I Go! 단독+조합), Prika(Encore + 풀차지 버프).
- **엔진 확장 완료 — 탄수("N round") 지속시간 + 최고ATK top-N 타겟팅 (2026-07-12, Fienn 승인):**
  "for N round(s)"는 초가 아니라 대상 아군의 다음 N발로 만료(`RoundGrant`+`round_buff_rule`
  → 샷 루프가 정확 N발만 덮는 Effect로 변환, squad는 아군별 개별 소모). "N ally unit(s)
  with the highest final ATK"는 적용 시점 실시간 랭킹으로 정확 대상 지정
  (`top_atk_slugs`+`slugs:` 스코프+`highest_atk_buff_rule`). Miranda(✅ 승급: Health Up
  자ATK per_shot·top-2 ATK/크리댐·top-1 크리율 1-round)·Zwei(1-round Pierce) 재인코딩.
- **eb1/eb2 + 자원 primitive beachhead + count-스케일 넉 + eb3 Pattern-A 배치 완료
  (2026-07-12):** Noir·Isabel·Liberalio·Ludmilla·Chisato·Jill·Modernia·Guillotine:
  Winter Slayer·Julia(base+시그니처)·Cinderella·Quency·Soda·Maiden. 상세는 To-Do의
  eb 체크리스트 참고. eb3 Pattern-A 배치에서 6개 신규 엔진 확장(자원 reset·
  `resource_gated_buffs`·FB창 한정 fill·squad-burst-cycle-conditional fill·
  `dynamic_hit_count_nukes`·`extra_flat_atk`) + 신규 갭 2건(#7 FB창 한정 per-shot
  트리거, #8 자원-fill-트리거 타 유닛 버프) 발견.
- **eb4 배치 (2026-07-12, Fienn 승인):** Asuka Shikinami Langley: Wille ⚠ ·
  Mana ⚠ — 4개 신규 엔진 확장: `fire_delay`+`own_burst_delayed`(버스트 후 지연
  발동 넉/리셋, Asuka의 Annihilation이 첫 소비자) · `("per_shot_every_during_own_
  status_window", n, duration)` fill(자기 버스트 앵커 상태창 한정 fill, Anti A.T.
  Field가 첫 소비자) · `full_burst_bonus_eligible`(스킬 텍스트 "as additional
  damage" 옵트인 배선 — Fienn의 새 판정 규칙: "burst skill 대미지 설명에 'as
  additional damage' 표현이 있으면 full burst bonus 받음, 그 외엔 캐스트 시점
  효과만 적용되며 받지 않음") · `resource_scaled_nukes`의 `resource` 필드 선택화
  (순수 반복틱 DoT, Mana의 Fatal Error!가 첫 소비자). 배치 검증 중 `cinderella-
  crystal-wave`가 실제로는 Pattern-A 자원 유닛이 아니라 무기-모드(MG/Snipe) 전환
  상태머신 유닛으로 밝혀져 배치에서 제외·재분류(Fienn 결정, 교체 없이 2명 진행).
  gap #7(FB창/자기상태창 한정 per-shot **트리거**)에 2번째 소비자(Asuka의 15.62%
  상태게이팅 넉) 발견.
- **gap #1 "마지막 탄" 잔여 해소 + 재인코딩 배치 (2026-07-12, Fienn 승인):**
  `attack_rate.py`에 `magazine_last_bullet_times`/`charge_last_bullet_times`/
  `last_bullet_shot_times`(매거진 실제 마지막 발사 마킹, `max_ammo_percent_at`
  라이브 재계산이라 유저의 최대 장탄 수 증가 오버로드/버프 자동 반영, attack/charge
  speed는 매거진 용량에 무관해 모델링 불필요) + `per_shot_rules`의 `"last_bullet"`
  모드 + `ResourceSpec`의 `("on_last_bullet",)` fill kind 완료. 즉시 재인코딩:
  Julia(base) ✅(Crescendo 라스트불릿 자원 + Climax 게이팅 추가딜, 이 갭의 원래
  동기 유닛) · Helm(애장품) ⚠(Frontline Command, 죽은 `on_last_bullet_hit`
  트리거를 실제 배선으로 교체) · Privaty(애장품) ✅(LD Assault, Designated Target
  조건부 중첩 넉 — AK Missile 버스트 시각 기준 10초 시간창 체크).
- **엔진 확장 완료 — gap #7 FB창/자기상태창 한정 per-shot 트리거 (2026-07-15):**
  `per_shot_rules`에 창 한정 모드 `"every_during_full_burst"`/
  `"every_during_own_status_window"` 추가(자원 fill 한정 경로와는 별개, 버프/넉을
  직접 발동) — `raid_simulator.py`, 기존 after/every/last_bullet 모드와 나란한 순수
  추가. 첫 소비자로 Soda: Twinkling Bunny(Lucky Golden Chip 공동발동 최고ATK버프)·
  Asuka Shikinami Langley: Wille(Anti A.T. Field 15.62% 상태게이팅 넉) 잔여 메커니즘
  재인코딩(둘 다 기존 ⚠ 유지 — 이 갭 외 잔여 항목 있음). 같은 날 기존 per-shot
  능력만으로 신규 Phase A1 두 건 인코딩: Helm: Aquamarine(Admire Accompaniment
  노멀30회마다 131.34% 넉)·Anis: Sparkling Summer(Sparkling Missile 라스트불릿
  382.42% 넉 + 자기 부위딜 refresh). 검증 중 재분류/신규 발견: grave·velvet은
  gap #7로 부분 언블록 가능함이 확인돼 다음 배치 후보로 이동(grave의 Overheat
  II/III는 Prediction 상태창 한정 노멀 카운터, Overheat I은 별개의 재장전게이팅
  토글+에스컬레이션 체이닝; velvet의 Bullets of Love/Sticky Fingers 일부는 FB창
  안/밖 한정 카운터, 무기변형·탄약주머니 자원은 여전히 별도 갭) · jill-valentine은
  Magnum의 "재장전으로 최대 장탄 도달 시" 트리거에 **신규 소규모 갭**이 필요함을
  확인(기존 "마지막 탄" 마커의 거울상인 "reload 후 첫 발" 마커, gap #9로 기록,
  미착수) · rapi-red-hood는 120-노멀 카운터가 버프/넉 직접 발동이 아니라 프로젝타일
  발사 후 FB진입 시 폭발하는 상태머신(+2단계 버스트)이라 gap #7·#9 어느 것으로도
  안 풀림을 확인, 보류 유지. 상세는 `engine-gaps.md`(gap #7/#9) 참고.
- **gap #7 후속 소비 배치 (2026-07-15, 같은 날):** Grave ⚠(Overheat II/III — 자기
  버스트 상태창(Prediction) 한정 노멀30/60회마다 자ATK+20.66%/자AD+30.8%,
  `every_during_own_status_window`; "continuously"를 언락-후-영구로 해석하는 가정
  하나 Fienn에 플래그) · Velvet 🔶→⚠(Bullets of Love — 풀버스트 한정 풀차지마다
  스쿼드 flat ATK/Charge Damage + 노멀50회마다 자AD+400.92% 넉,
  `every_during_full_burst`; ammo pouch는 소모량 대비 압도적으로 커서 비제약 처리,
  자원 모델링 불필요) 재인코딩 완료. gap #7 소비자는 이제 Soda·Asuka·Grave·Velvet
  4명 — 남은 후보는 modernia 하나(검증 전). 새 발견: velvet의 Sticky Fingers가
  gap #7의 거울상(not-in-Full-Burst per-shot 창 필터, 미구현)에 막혀 잔여로 남음
  — 상세는 `engine-gaps.md`(gap #7) 참고. 471 tests pass (was 465).
- **엔진 확장 완료 — gap #5 enemy-element 조건 + enemy_def_percent 배선 (2026-07-16):**
  `SquadContext.boss_element`(raid_simulator 주입) + `boss_is_element(element)` 조건
  헬퍼로 "적이 X Code일 때만" 발동하는 디버프/추가딜을 게이팅(`buff_rule`/
  `refreshing_buff_rule`/`instant_nuke_pulse_rule`에 옵셔널 `condition` 추가). 함께
  `enemy_def_percent`(DEF▼ 디버프, damage_formula가 이미 지원하나 inert였음)를
  `_damage_instance`에 한 줄 배선(squad 스코프 적 디버프, `damage_taken_up`과 동형).
  소비: **Brid: Silent Track ⚠→✅**(Ignition/Journey Ahead Wind Damage Taken 디버프) ·
  **Helm: Aquamarine ⚠→✅**(Suppression Fire Electric Damage Taken 정상상태 28.2% +
  Overload Electric 추가딜 164.83%; 추가딜은 Burst2라 FB창 직전 발동으로 FB보너스
  미적용, Fienn 판정) · **Marciana: Marine Study(신규 ⚠, Iron AR B3)** — Fienn 확정
  솔로레이드 가정(rapture 수=1, Flagged Target=보스, High-Risk 불릿=Electric 게이팅)
  하에 Whistle 자ATK·Elemental Advantage AD·High-Risk DEF 디버프·Flagged 3789% 풀버스트
  넉·High-Risk 20노멀 넉을 인코딩. Flagged Target ATK(스코프 모호)·적처치 넉·6+rapture
  넉은 defer. 엔드투엔드 스모크로 Electric/비-Electric 보스 딜 차 확인.
- **엔진 확장 완료 — Ark Ranger Black floor/ceiling 브래킷 (gap #2 Pattern B, 개별
  우회, 2026-07-16):** 신규 보스 플래그 `part_destructible`(`BossProfile`→
  `evaluate_deck`/`simulate_raid`→`SquadContext`)로 Transformation 상태를
  floor(파츠파괴 없음, 변신=버스트당 10초 창)/ceiling(파츠파괴 있음, 변신=영구) 두
  갈래로 모델링. DoT 스펙에 옵셔널 `requires_part_destructible` 필드 추가. Transform!
  자ATK+156.19%·Ark Black Collider 45.87% 지속딜(floor: 버스트-앵커 10틱 / ceiling:
  전투 내내 1초 주기)·Ultimate! Meteor 266.69%×10틱 지속딜 + 자 Sustained
  Damage+135.83%/10초(양쪽 공통)·노멀30회마다 자 Sustained Damage+59.6%/5초 모델됨.
  엔드투엔드 `test_ark_ranger_bracket.py`로 ceiling>floor + 기본 보스=floor + 지속딜
  타입 배선 검증(544 tests pass, was 541). 보류: 부위파괴 배터리 충전(플래그의 존재
  이유, 일반 Pattern B 프리미티브는 여전히 미착수)·skill2 Wind-AR Sustained Damage
  버프(gap #3 필요)·Damage to Parts.
- **다음:** **eb3+ 백로그**(Pattern B 일반 프리미티브·상태머신·무기변형) + **막힌
  나머지 per-shot 유닛 재인코딩 배치** + Phase B 잔여(gap #8)/Phase C가 최대 실질 가치.
  남은 gap은 `engine-gaps.md` 우선순위 참고.

### Phase 4 — 단일 최적 덱 추천 ✅
- `deck_search.py` — `BossProfile`, feasible_orderings, evaluate_deck, find_best_decks.
- 덱 좌우 순서 = 버스트 역할 배정 → 같은 5인이라도 순서에 따라 딜 33% 차이 확인.

### Phase 5 — 5덱 분배 최적화 🔄 백엔드 완료
- 25명(5덱×5)을 골라 총합 딜을 최대화하는 조합 레이어. 단일 덱 평가기를 빌딩블록으로 사용.
- **백엔드 완료 (2026-07-17):** `search_best_decks`(예산 인지 단일 덱 탐색 — 후보풀
  컷 + top-K 순열 정련) + `allocate_decks`(greedy peeling으로 5덱 초기 분배 후
  같은-티어 스왑 언덕오르기로 교정, 같은 보스라 총합=덱별 합이라는 성질 이용) +
  `POST /api/recommend-raid`(roster/boss + 선택적 `num_decks`(기본5) → decks/
  combined_total_damage/excluded_slugs/leftover_slugs). 기존 `POST /api/recommend`도
  `find_best_decks`(전수조사) → `search_best_decks`로 전환(동일 인자, 소규모
  로스터에서는 결과 불변 — 예산 컷은 로스터가 클 때만 개입). 로더블 42유닛 전량
  분배 실측(픽스 반영 재측정) **282.17초, 3덱**(leftover 27, 합계 5.18B) — 스왑
  단계 포함 수치(최초 103.92초는 스왑 미실행 탐욕 전용). 수초~1분 예산 초과가
  실측으로 확인됨 → **처리량 레버 = 시뮬 병렬화(ProcessPool)로 결정**(Fienn,
  2026-07-17 — 타이어 캡 축소는 탐색 품질을 깎아 기각, `decisions.md` 참고).
  3덱 원인이던 로더블 B1 부족(4명)은 매니페스트 예외 배치로 해소(B1 10명).
- **ProcessPool 병렬화 완료 (2026-07-17):** `app/sim_pool.py`의 `SimPool` —
  지연 스폰(배치 32건 미만 인라인, 소형 요청/테스트 무비용), 워커 초기화 1회에
  로스터 specs+boss 전달(태스크 = 슬러그 튜플), `search_best_decks`/
  `prune_candidate_pool`/`allocate_decks` 폴리시의 맵 구간 소비, API 두
  엔드포인트 `workers="auto"`. 직렬 경로(기본값)는 비트 동일 + SimPool 미생성
  (테스트 스텁 보존). **실측 50유닛 97.25초, 5덱**(합계 31.0B) — 상세는 위 요약.
  플랜: `docs/superpowers/plans/2026-07-17-processpool-parallelism.md`.
- **프론트 레이드 모드 배선 완료 (2026-07-17, frontend-builder):** RecommendPanel에
  모드 스위치(단일 덱 / 레이드 분배) + `num_decks` 셀렉터(1–5), `RaidResults`가
  분배 결과를 파티션으로 렌더(Deck 1..N 동시 편성 + 합계 + bench/제외 목록),
  라이브 클라이언트는 무타임아웃(~1–2분 대기 안내 + 재제출 잠금), mock은 ~1초
  지연. 공유 조각 추출(useAsyncRequestStatus·DeckCard·ExcludedSlugsNote·
  formatDamage). Vitest 71/71 · `tsc -b` 클린 · 빌드 클린 · vite 프록시 경유
  실백엔드 E2E 확인. 부수 픽스: 루트 tsconfig가 references 셸이라 bare
  `tsc --noEmit`이 no-op이던 함정(README 교정 + 숨어 있던 테스트 타입에러 3건).
  97초→1분 미만 후속 최적화(스왑 배치평가/예산 축소)는 **유저 피드백 생길 때까지
  보류 확정**(Fienn, 2026-07-17 — `decisions.md` 참고). Phase 5 종결.
- **초안 기반 5덱 최적화 완료 (2026-07-23):** 유저가 초안(부분/완성 편성)을 넣으면
  엔진이 빈 자리를 채우고 순서를 교정. 유닛은 **잠금(반드시 그 덱 유지)** 또는 **유연
  (warm-start 힌트)**. 백엔드: 완성 프리미티브 `best_completions`(고정 유닛 포함 최선의
  덱, 전 티어·전 shape) + `allocate_decks(draft, locked)`(시드 완성 + 스왑 락 마스크,
  `draft=None`이면 비트 동일) + `recommend_from_draft`(3단: baseline ≤ within_draft ≤
  recommended를 **구조적으로 보장** — from-scratch도 락 존중, within_draft를 recommended
  max에 접음) + `/api/recommend-raid`에 `draft` 배선(additive: `pinned_slugs`·
  `within_draft`·`baseline_total_damage`, 완성 draft에서만 non-null) + `GET
  /api/supported-units`(팔레트용, registry+manifest 조립으로 **0/77 스킵**). 프론트:
  팔레트(보유∩지원, B1/B2/B3 그룹, 초상화/칩) + 5×5 편성기(락 토글·재사용금지) + 3단
  결과(덱 diff는 슬러그 겹침 매칭). 초상화는 lootandwaifus `data-default-src`에서 로컬
  다운로드(`scripts/download_portraits.py`, manifest 계약). **실측(TestClient, 실데이터):
  단조 2.20B ≤ 2.66B ≤ 4.07B, 77/77 usable, 완성-draft 5덱 202초**(최대 4회 할당 경로).
  `gauge_charge_time`/`mode`는 CDR-누수없음·수동 가정으로 미노출. spec/plan:
  `docs/superpowers/{specs,plans}/2026-07-22-*draft*`. 백엔드 1183 · 프론트 Vitest 208.
  **후속(성능) — 백로그 (2026-07-23 논의, 미착수):** 완성-draft 202초의 지배 비용은
  spawn이 아니라 **전체 로스터 ~97초 패스를 scratch+warm 두 번 직렬로 도는 것**(단일
  전체 패스 ≈97초, 초안 30명 부분집합 패스는 저렴). 방안을 효과×위험 순으로:
  - **0. 프로파일 우선(~20 LOC).** `recommend_from_draft` 한 호출을 cProfile+구간
    타이머로 감싸 scratch/warm/greedy/swap/summary 실측 분해 — 아래 어느 걸 고르든
    잘못된 병목 최적화를 막는 선행 단계. (위 202초·97초는 구조 추정치이지 실측 분해 아님.)
    **✅ 완료 (2026-07-23, `scripts/profile_recommend_allocation.py`, 78유닛 실 로스터,
    workers=auto): 가설 반증.** 완성-draft **총 797초**(≠202초). 호출별: scratch(draft
    무시, 78)=**597초**, warm(draft 시드, 78)=50초, within.warm(25)=23초,
    within.scratch(25)=126초. **draft-무시 from-scratch 탐색이 지배(scratch=warm의 ~12배);
    두 scratch 패스 합 723초 = 90%.** cProfile: 그 597초 = 병렬 sim 대기 ~444초(수만 후보
    덱) + 부모측 후보 생성 핫루프(`_intra_tier_orderings` 1억 회·`_buffer_seat_valid`
    8800만 회, `_all_intra_tier_orderings` cumtime 202초) + swap ~57초. **spawn은 무시 수준.**
    ⇒ 아래 1(공유 SimPool)·2(메모)는 spawn/중복을 겨냥해 이제 **부차적**. 진짜 레버는
    (a) 중복 from-scratch 패스 축소/조건부 생략(구조적, 최대·품질 트레이드), (b) from-scratch
    탐색 내부 최적화(후보 풀 prune 강화·top-K 축소로 sim 수↓, 핫루프 가속; zero-base raid
    모드=scratch만 597초도 직접 단축). **방향은 Fienn과 논의 필요(품질↔속도).**
  - **✅ scratch 품질기여 측정 (2026-07-23, `scripts/measure_scratch_delta.py`, 41유닛
    스탯편차 seed=7, 3 draft 시나리오): full-scratch는 잉여로 판명.** scratch(전체 전역)
    vs warm(초안+벤치 스왑): perfect −0.28% / scrambled −1.44% / weak-swap +0.79% — **세
    시나리오 모두 warm의 ±1.5% 안, 대개 warm보다 나쁨.** 비싼 전역 탐색이 warm이 이미
    도달하는 걸 못 넘어섬(최대 기여 +0.79%). 진짜 가치는 **within-draft `s`(warm 대비 최대
    +5.5%, 고정 유닛의 더 나은 분할)**와 warm의 벤치 스왑(baseline +23~55% 복구)에서 나옴.
    핵심 부산물: **`s`(25명 재탐색)=8.30B > scratch(41유닛 전역)=7.85B — greedy-peel이 큰
    풀에서 초반 덱 결정을 나쁘게 함("greedy 고전적 실수").** ⇒ **주력 최적화: 완성-draft에서
    full-roster scratch 패스 제거**(`recommended = max(warm, within_draft)`), **797초→~200초
    (~4배), 품질 손실 ≤0.8%**(lock·단조보장 유지). 부차(당시): zero-base raid는 "선택→좁은
    분할" 2단계 여지 — **캐스케이드로 대체됨**. **1(공유 SimPool)·2(메모)는 폐기
    수준**(제거할 패스가 지배비용이므로 무의미). 착수 전 seed/size 1~2개 추가 확인 권장.
  - **✅ 재확인 (2026-07-23, seed 42@42u·seed 99@51u): 정정된 최악 손실 ~2.2%(≤0.8% 아님).**
    "full-scratch 제거 시 recommended=max(warm,within_draft) 손실"은 **현실적 draft(perfect/
    scrambled) 8케이스 중 6개 = 0%**(warm 또는 s가 항상 scratch≥). **손실은 weak-swap(최강 유닛
    벤치)에서만 0.76%(seed7)·2.17%(seed99)**, seed42 weak-swap조차 0%. 병적 draft 한정 ~2.2%,
    현실 0%. 4배 속도(797→~200초)와의 교환 — Fienn이 ~2.2% 병적-케이스 손실 수용 확인.
  - **✅ 구현·검증 완료 (2026-07-23, 커밋 03f77ca):** `recommend_from_draft`가 draft 있을 때
    full-roster scratch 호출 제거(`recommended = max(warm, within_draft)`), zero-base는 scratch
    유지, within_draft의 focused `s`도 유지. 단조보장·lock 존중 유지(warm의 swap 마스크가
    lock 존중), 완성-draft가 4콜→3콜임을 고정하는 회귀 테스트 추가. **실측 78유닛 완성-draft
    797→215.8초 (3.7배).** 남은 최대 비용은 유지한 within `s`(25유닛 focused scratch)=139초 →
    **후속 타깃**(당시): `s`·zero-base scratch를 "선택→좁은 분할" 2단계로 — **캐스케이드로 대체됨**.
    백엔드 1184 passed/3 skipped, 리뷰 Approved. **1(공유 SimPool)·2(evaluate 메모)는 착수 안 함
    (지배 비용이던 full-scratch 제거로 무의미해짐).**
  - **✅ 유저 풀 선택(제외) 착지 (2026-07-23):** 세 추천 모드(single/raid/draft)에
    "사용할 니케" 화이트리스트(기본 전체, 안 쓸 유닛만 토글 오프) 추가 — 프론트가
    `보유∩지원−제외`로 로스터를 필터링해 요청 전 전송(백엔드 무변경). 탐색 풀을
    근원에서 줄여 raid-from-scratch를 유저가 뺀 만큼 단축. 휘발성(프로필 전환 리셋),
    `DraftPalette`→`UnitPalette` 일반화. spec/plan:
    `docs/superpowers/{specs,plans}/2026-07-23-unit-pool-selection*`. **2단계 탐색
    (선택→좁은 분할)은 백로그에서 제거(2026-07-25)** — 캐스케이드가 같은 목적(후보를
    값싸게 좁히기)을 달성했다(아래 Phase 2 항목, 78유닛 20.2배).
  - **✅ 캐스케이드 대리모델 Phase 1 측정 완료 (2026-07-24):** 프로파일이
    raid-from-scratch 비용의 ~66%가 "모든 후보 시뮬"임을 확인 → 값싼 필터로 랭킹하고
    top-K만 정밀평가하는 캐스케이드가 채택 가능한지 실측했다(41유닛, holdout 300, 5시드).
    **결론: 캐스케이드는 유효하되 "유닛 단독 피처 + top-K 실시뮬" 형태로만.**
    · **닫힌 수식 기각** — `backend/app/closed_form.py`(fit 0, 덱당 0.79ms, 시뮬 대비
    140x)는 Spearman 0.54에 그치고 top-100까지 시뮬해도 최적을 못 찾는다. 원인 실측:
    정적 스코어러가 값을 매길 수 있는 건 데미지의 60%뿐이고 못 보는 40%가 덱마다
    6~62%로 요동(`scripts/measure_unmodeled_damage_share.py`).
    · **페어 피처 기각** — recall 최고(top-20 전 시드 100%)지만 fit 비용이 대체 대상과
    맞먹는다: 41유닛 오늘 **7,659 시뮬** vs 페어 캐스케이드 **6,257** = **1.22x**
    (`scripts/measure_cascade_budget.py`).
    · **유닛 단독 채택** — 예산이 로스터 크기와 거의 무관(41/61/78유닛 1,461/1,434/1,348)
    한데 오늘의 탐색 비용은 급증(41유닛 7,659 → **78유닛 49,891** 시뮬, 직렬 70분) →
    이득이 **41유닛 5.2x → 78유닛 37x**(같은 78유닛에서 페어는 2.5x). top-20 시뮬로
    4/5 시드에서 최적 100%(1개는 95.7%).
    · **"시뮬 없는 즉시 모드"는 불가** — 대리모델 1픽의 실제 데미지가 시드별 44~100%.
    결정 근거는 `docs/decisions.md`, spec/plan:
    `docs/superpowers/{specs,plans}/2026-07-23-cascade-surrogate*`.
  - **✅ 캐스케이드 Phase 2 착지 (2026-07-24):** 유닛 단독 대리모델을 `search_best_decks`에
    통합. `prune` ∪ 계수 상위로 넓힌 풀(`WIDE_TIER_CAPS`)을 대리모델이 랭킹하고 **top-20만
    진짜 시뮬**한다. `deck_search`는 `cascade`를 임포트하지 않고 주입받는다(순환 회피).
    적합은 요청당 1회, greedy-peel 전 반복이 공유(가산 모델이라 부분집합에 그대로 유효).
    · **게이트 통과:** 78유닛·풀 분포·5시드에서 진짜 최적이 순위 0~4 — K=10만으로 5/5가
    최적 100% 회수. 채택 K=20(여유).
    · **실측 이득(5덱 직렬):** 41유닛 8,071 → **2,146 시뮬(3.8x)**, 948 → **230초(4.1x)**;
    **78유닛 49,891 → 2,464 시뮬(20.2x)**, 4,224 → **219초(19.3x)**. 타깃이던 search는
    41유닛에서 7,385 → 537(**13.8x**), 비중 91.5% → 25.0%.
    · **핵심: 비용이 로스터 크기와 사실상 무관해졌다.** 전에는 41→78유닛에서 비용이 6.2배로
    뛰었는데(8,071→49,891) 이제 1.15배(2,146→2,464). 최대 비용인 fit이 고정비이기 때문.
    · **핵심 발견:** prune 안전망을 빼면 최적의 **90.6%**, 넣으면 **100%** — 안전망이
    장식이 아님이 실측됨. 자세한 근거는 `docs/decisions.md`·`docs/insights.md`.
    spec/plan: `docs/superpowers/{specs,plans}/2026-07-24-cascade-surrogate-phase2*`.
  - **✅ swap 힐클라임 배치 병렬화 착지 (2026-07-25):** 캐스케이드 이후 유일한 비병렬
    단계였던 `_swap_pass`를 재측정하니 전제가 뒤집혀 있었다 — swap은 합계 데미지를
    **+48.6%** 올리는 **품질의 주력**인데 한 패스 후보 679개 중 **52%만 보고 잘리고**,
    잘리는 순간에도 이득이 오르는 중이었다(deck 3·4는 leftover 후보를 한 번도 못 봄).
    예산 300초면 160.9초에 +54.83%로 수렴 ⇒ **45초가 버리던 총딜 4.0%**.
    · **원인 판정:** "캐스케이드가 풀을 좁혀 swap에 떠넘긴 것" 가설을 실측 기각 —
    캐스케이드 peel이 기존 pruned-exhaustive peel의 **105.1%**(`measure_peel_quality.py`).
    범인은 greedy peel 고유의 고전적 실수. 풀은 안 건드림.
    · **구현:** 의미 보존 배치 채점(순회 순서·채택 규칙 불변, 채택 시 재배치). 새
    프로세스 0개 — peel이 만든 SimPool 재사용이라 **피크 CPU 불변**.
    · **1차 시도가 1.9배에 그친 함정:** `SPAWN_THRESHOLD=32`가 executor 재사용까지
    막아 덱-덱 배치(~22덱)가 인라인으로 떨어졌다 → 임계값이 **생성만** 지키도록 수정.
    · **결과:** swap 452 → **3,734 시뮬(8.4x)**, +48.60% → **+54.83%**(직렬 300초판
    수렴값과 자릿수까지 일치). 할당 전체 직렬 216초 → **프로덕션 81초**.
    · **`auto` = `cpu_count // 2`로 하향** (유저 디바이스 배려, Fienn 요구). 8워커와
    15워커의 데미지가 **동일** — 절반은 타협이 아니라 공짜(4워커 99.6%, 2워커 98.3%).
    신설 계측: `scripts/measure_swap_phase.py`, `scripts/measure_peel_quality.py`.
  - **1. SimPool 공유(~30 LOC).** 4회 호출이 SimPool 하나를 공유(전체 로스터로 초기화
    → 30명 부분집합도 `_WORKER_SPECS[s]` 유효). spawn wave 4→1. **결과 불변.** 단
    sim 작업량 2×97초는 그대로 — spawn이 지배 비용이 아니면 체감 작음(0번이 판정).
  - **2. evaluate 메모(요청 내, ~40 LOC) — 효과 큼.** `evaluate_deck`은 (정렬 슬러그
    튜플, boss) 순수·결정론적. scratch·warm이 같은 전체 로스터/boss라 동일 덱 정렬을
    대량 중복 평가하고 swap hill-climb은 되돌린 상태를 재평가 → 부모 측 `{튜플:total}`
    캐시로 제거. 공유 SimPool(1)에 캐시를 얹으면 1+2가 자연 결합.
  - **3. scratch·warm 동시 실행(~50 LOC).** 두 전체 패스는 독립 → 한쪽 직렬 swap 구간과
    다른쪽 병렬 greedy 구간 중첩(swap은 직렬이라 코어 유휴 발생). 이론상 194→~97초. 단
    같은 코어풀 경합 시 이득은 "직렬 유휴 비중"에 달림(0번이 판정). **2번과 택일**(동시
    실행하면 warm이 scratch 결과 재사용 불가).
  - **4. 서버 수명 상주 pool(~40 LOC).** 모듈 싱글턴 executor를 기동 시 1회 spawn, 요청
    간 재사용. 워커가 요청별 로스터를 initargs가 아니라 첫 배치로 받도록 재설계 필요
    (pickle 비용↑와 배치). 반복 요청 UX에 큼. 단일 로컬 유저엔 과할 수 있음(YAGNI).
  - **5a. warm 축소/생략(~10 LOC, 품질 트레이드).** scratch는 이미 락 존중. warm이 더
    주는 건 flexible 초안 유닛의 warm-start 힌트뿐 → 개선폭 실측해 미미하면 warm에 작은
    `time_budget_sec` 부여/생략(최대 97초 절감). **결과 품질과 직접 교환 — Fienn 판단 사안.**
  - **6. swap hill-climb 병렬화(~80+ LOC) — 비권장.** 순차 의존성(채택 swap이 다음 기준
    변경)을 깨면 결과가 달라짐 = 알고리즘 교체. 복잡도 대비 이득 불확실, YAGNI.
  - **결과 영속/재활용(별도 트랙, 다계정 B 위에 얹힘).** 엔진 결정론적이라 결과 캐싱은
    정확. **핵심 통찰: scratch는 초안-독립**(락 부분집합에만 의존) → 같은 로스터·boss면
    세션 내내 동일 → 캐시하면 재요청이 warm+within_draft만 재계산. 계층:
    L1 전체 응답(로스터+boss+초안 해시), L2 scratch 캐시(로스터+boss+락 집합; 초안
    flexible만 바꿔도 히트), L3 evaluate 메모(요청 간). 무효화 키에 **투자 데이터 전체
    해시 + boss 필드**를 넣어야 정확(계정 재동기화 시 stale 자동 회피). 저장은 인메모리
    LRU(로컬 앱에 적합) — 클라 측 영속은 다계정 프로필(B)에 프로필별로 얹는다.
    첫 콜드 요청은 여전히 느림(캐시는 2번째+만 구제) — 1~5와 상호보완.
  - 부수: README "~1–2분" 지연 안내는 zero-base 기준 → 완성-draft 경로(30유닛 202초,
    큰 로스터 5분+)에 맞게 갱신. 추천 중 CPU 전코어 포화는 의도된 동작(요청 버스트,
    유휴 0), 완화 필요 시 `workers` 축소로 벽시계와 맞바꿈.
- **다계정 프로필 + 결과 영속(클라측) 완료 (2026-07-23):** 한 브라우저에서 여러 NIKKE
  계정을 **`open_id`로 격리된 프로필**로 보관(localStorage `nikke-profiles`, 서로 다른
  open_id 절대 병합 금지). 로스터 소스를 **blablalink sync 하나로 확정**하고 ExiaInvasion
  파일 import·수동 입력 폼은 코드/UI 제거(`decisions.md` 2026-07-23). sync가 `nickname`
  (`GetUserProfileBasicInfo`)·`open_id`를 캡처하되 **클라 전용**(어떤 백엔드 호출에도
  미전송, 백엔드로 가는 유일 식별자는 `clientId`). 프론트: `useProfiles`(upsert/switch/
  delete·legacy `nikke-roster` 폐기) + `ProfileSwitcher` + 읽기전용 `NikkeCard` + 결과
  영속(`inputHash` FNV-1a 결정론 해시[로스터+boss+draft+num_decks], 프로필별 LRU 20,
  재오픈/전환 시 `key={activeOpenId}` 리마운트로 복원·프로필 격리). raid/draft만 캐시,
  single 미대상. 재-sync로 로스터 변경 시 그 프로필 결과 무효화. **SDD 8태스크 + opus
  전체리뷰 "Mergeable: yes"**, 프론트 220 테스트·`tsc -b` 클린, 백엔드 무변경.
  spec/plan: `docs/superpowers/{specs,plans}/2026-07-23-multi-account-profiles*`.
  **배포 전 후속:** ① `GetUserProfileBasicInfo` 닉네임 응답 경로 라이브 실측+픽스처(방어적
  fallback이라 무해하나 미확정 시 라벨이 openId), ② 프라이버시 정책에 "open_id/닉네임/
  로스터/결과 브라우저 로컬 저장" 명시. **주의:** 위 draft-allocation 후속의 L1/L2/L3
  "결과 영속/재활용"은 **서버측 연산 캐시**(scratch 캐시·evaluate 메모)로 SimPool 성능
  트랙에 별도로 남아있음 — 이번 다계정 작업은 **클라측 프로필별 영속**이라 서로 다른 층.

### Phase 6 — 유저 데이터 입력 UI 🔄
- React 폼으로 ShiftyPad 투자 데이터 수동 입력 (돌파/스킬레벨/오버로드/큐브). ✅
- FastAPI 엔드포인트로 엔진 노출. ✅ (`POST /api/recommend`, 2026-07-16 —
  스킬값 매니페스트 + 검증 하니스 + 로스터 로더 경유; 프론트는
  `VITE_RECOMMEND_API=live` + Vite 프록시로 연결, `excluded_slugs` 표시)
- 매니페스트 백필 배치 2 ✅ + dotgg weapon 스탯 수집 ✅ (2026-07-17, Opus 병렬
  배치): 매니페스트 45/57(예외 12은 `KNOWN_MANIFEST_EXCEPTIONS` 가드 테스트 +
  encoded-nikkes.md 예외 표기), dotgg 파일 14→53개, `dotgg_slug` 매니페스트
  키로 소스 간 슬러그 불일치 브리지(ada-wong·chisato·jill·takina). **API 로더블
  42/57.**
- 매니페스트 예외 8유닛 배치 ✅ (2026-07-17): crown·helm·liter·miranda·moran·
  soline-frost-ticket·volume·zwei에 dotgg-소스 매니페스트(helm·miranda·moran·
  zwei는 시그니처 완성이라 `dollskills` 배열). **매니페스트 53/57, API 로더블
  50/57, 로더블 B1 4→10명.** 잔여: 픽스처 재배열 4유닛(anis-star·asuka·privaty·
  neon-vision-eye)은 픽스처 검증 후 재작성 필요; marciana-marine-study·
  ark-ranger-black·prika·cinderella-crystal-wave(dotgg 부재, 2026-05 갱신
  중단)는 `scripts/collect_dotgg_weapons.py --stub` 수동 스텁에 Fienn이
  무기 스탯 기입 완료(2026-07-17) — **API 로더블 53/57** (잔여 4 = 픽스처
  재배열 유닛).
- dotgg 무기 스탯 수집 자동화 ✅ (2026-07-17): `scripts/collect_dotgg_weapons.py`
  — lootandwaifus 유닛 대비 누락 dotgg 파일 스캔·수집(슬러그→이름 정확 매칭),
  dotgg 부재 유닛은 `--stub`으로 수동 입력 템플릿. collect-nikke 워크플로에 편입.
- 스킬 수치 드리프트 감지 ✅ (2026-07-18): `scripts/check_skill_value_drift.py`
  — dotgg-소스 매니페스트 22개를 라이브 lootandwaifus와 대조, 밸런스 패치로
  낡은 유닛을 자동 검출(현재 22 OK, 0 DRIFT). 게임 패치 후 실행해서 DRIFT가
  뜨는 유닛부터 lootandwaifus 소스로 이관하는 게 후속 단계(→ `decisions.md`
  2026-07-18 단계적 소스 이관 결정). 두 데이터 폴더의 파일 단일화는 이관 완료
  후에만 싸게 가능(보류).
- ShiftyPad 자동화는 Phase 7.

### Phase 7 — ShiftyPad 데이터 적재 🔄 조사 단계 (2026-07-17 재정의)
- **원안의 절반은 폐기됨.** "dotgg 자동 수집 파이프라인"은 dotgg가 2026-05에 갱신을
  멈춰(→ `decisions.md`) 스크래퍼 대신 수동 스텁으로 가기로 이미 결정했고,
  `scripts/collect_dotgg_weapons.py`가 자동화 가능분을 처리했다. **실행 대상 아님.**
- **남은 절반(ShiftyPad)은 구현이 아니라 조사다.** 아는 게 "로그인 필요, 공개 질의 불가"
  한 줄뿐 — 인증·엔드포인트·스키마·샘플이 전무하다. API 형태를 가정한 구현 계획은
  CLAUDE.md 최상위 규칙("기술적 세부사항을 지어내지 말 것") 위반이라, 발견 후 게이트에서
  판단하는 단계별 조사 계획으로 진행한다.
- **동기:** 니케 1명당 약 35개 필드(오버로드만 최대 24개) × 로더블 56명 ≈ **2,000개 값**.
  편의가 아니라 채택 블로커(Fienn, 2026-07-17).
- [x] **Stage 0-b: 로스터 영속화** — `useRoster`가 localStorage로 미러링(2026-07-17).
      경로와 무관하게 필요했다: import를 만들어도 영속화가 없으면 새로고침마다 로그인을
      다시 때린다. 이걸로 "스펙업마다 재입력"이 **바뀐 필드만 수정**으로 줄어든다.
- [x] **Stage 0-a: 큐브 질문 — 해소됨(Fienn, 2026-07-17).** ShiftyPad 표시 hp/atk/def에
      **장착한 큐브가 이미 포함**된다(미장착이면 순수 캐릭터 스탯). 따라서 큐브를 위에
      다시 더하지 않는다 — **오버로드와 정반대**(그쪽은 별도 표시이고 가산).
      **엔진 동작 변경 없음**: `cube_to_effects`는 원래 reload speed와 superior code
      damage만 내보냈고 둘 다 hp/atk/def가 아니라 이미 옳았다. 다만 이제 우연이 아니라
      명시된 이유로 옳다. **가드: 큐브가 atk/def/max_hp에 기여하면 이중 계산이다.**
      → `decisions.md` · `insights.md` 기록 완료.
- [x] **Stage 1 정찰 + Phase A: ExiaInvasion 임포터 구현 완료 (2026-07-18).** 정찰 결과 진짜
      소스는 ShiftyPad 껍데기가 아니라 **blablalink**이고, 오픈소스 확장 **ExiaInvasion**이
      로스터를 JSON으로 export한다(→ `phase-7-sprightly-manatee.md`, spec/plan
      `docs/superpowers/{specs,plans}/2026-07-18-exia-roster-importer*`). **Phase A** = 그 export를
      프론트에서 파싱→로스터로 임포트(오버로드 `function_type`별 합산→한글 7종·스킬·돌파·synchro
      레벨), **슬러그별 병합으로 수동 ATK/큐브 보존**(재임포트가 손입력 ATK를 안 지움).
      실측 확정: export에 ATK도 캐릭터별 큐브도 없음 → 둘 다 **수동 유지**. `cookie`/`game_uid`는
      읽지 않음. 프론트 스위트 **97/97**, `wip/scaffolding` 병합 완료. **Phase B(ATK 자동 계산)는
      분리** — blablalink CDN이 캐릭터 레벨별 기초 스탯표 + 큐브/소장품 스탯 배열을 제공함을 확인
      (공식 재구현이 아니라 **데이터 소비**로 디리스크), 잔여 발견거리는 CDN 해시 매니페스트 ·
      조립공식 1회 대조검증(→ plan §10).
- [x] **Phase B1 — blablalink/ShiftyPad 정확 스탯 수집기 구현 완료 (2026-07-18).**
      ("Phase B"가 수집기와 ATK 자동계산 둘을 함께 가리켜 혼선이 있어 B1/B2로 분리한다 —
      **B2 = ATK 자동 계산**, spec `2026-07-18-stat-assembly-calculator-design.md`.)
- [x] **Phase B2 — ATK 자동 계산 (2026-07-19, 159/159 오차 0).** 육성 데이터만으로 솔로레이드
      ATK를 계산 → **다른 유저의 로스터도 추천기에 넣을 수 있게 되는 sync의 전제조건**
      (API가 육성 데이터는 다 주지만 ATK는 어디에도 없음, 응답 270개 전수 확인).
      `backend/app/stat_assembly.py` + 커밋된 정답지 159유닛×2레벨. 공식·검증 상세는
      spec 하단 "구현 결과". 이전 세션의 순가산 초안이 틀렸음을 밝히고, 게임 테이블의
      값 3개(`_rate` 컬럼·`attack:25`·`core_attack:200`)가 이름과 다르게 동작함을 확정.
      **부수 해결:** 애장품 tid 블록(2xxxxx)이 곧 signature 보유 신호 → `SIGNATURE_OWNED`
      손 갱신 제거 가능(Phase 7 잔여 ③).
      **26유닛 편차 해소 (2026-07-19):** 작은 항이 하나 더 있는 게 아니라 **코어당 flat이
      클래스 상수가 아니었다** — `delta/core`가 클래스별 3~4개 이산 티어로 뭉친다.
      PILGRIM(+20%)은 `corporation`으로 판정되고, OVERSPEC 3기(Rapi:RH·Neon:VE·Anis:Star)는
      CDN 캐릭터파일의 `corporation_sub_type` 필드가 원인임을 diff로 확인했다. 미설명 3기
      (Vesti·Rosanna·Nero)는 측정값으로 나열. `core_flat_atk()`가 유닛>기업>클래스 순으로
      해석하고, 미측정 조합(코어 있는 PILGRIM 서포터)은 얼버무리지 않고 `KeyError`.
      **OVERSPEC 규칙 승격 (2026-07-19 후속):** `collect.js --directory --deep`이 194유닛의
      `corporation_sub_type`을 스냅샷에 담아(유닛당 1로드, opt-in; 194/194 무경고) OVERSPEC이
      하드코딩 목록에서 게임 필드 기반 규칙이 됐다 — 스냅샷 OVERSPEC 27기라 미측정 유닛
      (Mihara: Bonding Chain 등)까지 자동 커버. `stat_enhance_id` 가설은 **반증**(같은 id에
      94.23과 118.9 공존). 미설명 3기는 캐릭터파일 전 범주형 필드 자동탐색에서 **가르는 필드 0개**로
      CDN 경로가 막혔음이 확정 — 다음 단서는 인게임 코어 화면 캡처.
      **잔여:** 미설명 3기 정체 · 코어 있는 PILGRIM/OVERSPEC 서포터 미측정(`KeyError`로 거부) ·
      HP 미구현 · 수집기 교체 미착수.
      `tools/collect-blablalink/` Node 수집기 = playwright-core로 CDP(Fienn 로그인 Chrome, 포트 9222)에
      붙어 유닛별 `?nikke=<resource_id>` 페이지에서 **솔로레이드 400레벨 + 실제레벨** 스탯·오버로드·
      스킬·큐브를 스크랩→`roster.json`. **핵심 교정: 솔로레이드 레벨400 고정** → `hp/atk/def`=400레벨
      의미(엔진 무변경), `actual_*` 옵셔널 추가(유니온레이드 후속, 백엔드 `PveCube.level` cap 10→15).
      프론트 `rosterImport.ts`가 raid400→hp/atk/def·actual→actual*로 매핑, `mergeCollectorDrafts`(Exia와
      달리 정확 스탯을 덮어씀), `ImportRosterButton`이 `units`/`elements`로 형식 감지.
      **E2E 전체 수집 실측: 159/159 SSR 무실패**(육성 135 + 미육성 lv1 24, Fienn "모두 수집" → 양방향
      레벨링·양수 델타 파싱). 스파이크 산출: 유닛당 픽스처 1개로 전 surface 커버, ShiftyPad 탭은 v-if라
      탭별 조각 추출(capture.js), 파서는 스탯행 "값 부호델타" 직접탐지(LV 위치 무관). 보유목록 = nikke
      디렉토리 CDN(resource_id↔name_code↔영문명) × `GetUserCharacters` 조인(SSR 필터). 자격증명 미저장
      (game_openid 쿠키는 읽기전용 API 재생만), 픽스처 정제(PII 0). spec/plan
      `docs/superpowers/{specs,plans}/2026-07-18-blablalink-stat-collector*`.
      ~~**잔여(후속):** 게임명↔인코딩-slug 간극 소수 — name_code 키잉으로 별도 해결 예정.~~
      → **해결됨 (2026-07-18, resource_id 권위 맵).** name_code가 아니라 **resource_id 키잉**으로
      풀었다(roster.json이 이미 담고 있어 추가 수집 불필요). base vs 변형 충돌(Soline·Marciana)·
      동명 유닛("Rei" 3개: 831 레이=`rei-ayanami` / 392 라이=별개 캐릭터 미인코딩 / 834 tentative)이
      전부 해소. Drake/Julia의 base vs signature는 **resource_id가 같아 ID로 구분 불가**임이 밝혀져
      신원(`RESOURCE_ID_TO_SLUG`→base)과 투자(`SIGNATURE_OWNED`)를 분리하는 구조로 해결.
      백엔드 drift 테스트가 맵·dual-slot 페어를 `ENCODED_SLUGS`와 대조해 인코딩 확장 시 자동 감지.
      spec/plan `docs/superpowers/{specs,plans}/2026-07-18-roster-resource-id-slug-map*`.
      ①② **해결됨 (2026-07-18, 디렉토리 스냅샷).** `collect.js --directory`가 공개 디렉토리
      194유닛(`resource_id`/`name_code`/영문명/등급)을 `nikke-directory.json`으로 덤프 —
      소유·스탯 필드가 없어 커밋 가능(`roster.json`은 여전히 gitignored). 계정 불필요
      (`game_openid` 조회 전 반환). `test_resource_id_directory.py`가 맵을 이 스냅샷과 대조해
      **잘못된-but-유효 배정**을 차단(Soline 74→71 스왑 주입으로 검증: 신규 가드는 지목, 기존
      가드는 통과 — 사각지대 실재 확인). 기존 57개 항목 전부 정확함이 독립 확인됐고,
      `jill-valentine`은 디렉토리 근거(841 'Jill', Ada 840과 인접 RE 콜라보)로 매핑되어
      `KNOWN_UNMAPPED`는 이제 빈 집합 — 신규 인코딩은 면제 대신 id를 조회함.
      **잔여:** ③ SSR-애장품 자동판정으로 `SIGNATURE_OWNED` 손 갱신 제거(애장품 해금 니케는
      계속 추가됨) · ④ 신규 니케 출시 시 스냅샷 재덤프 필요(미등재 id는 가드가 실패시킴).
- [x] **Stage 1: 정찰 — 완료 (2026-07-19). "공개 질의 불가" 가정이 뒤집혔다.**
      **핵심 결과: ShiftyPad 공개 공유 URL만으로 타 유저 로스터를 읽을 수 있다.**
      실측 검증(Fienn 두 번째 계정 B, 공개 상태, 메인 세션 A에서 조회):
      - 공유 URL `blablalink.com/shiftyspad?uid=<base64>`의 uid = `<shiftypad_area>-<intl_open_id>`
        (예: `29080-8223...`). **앞자리 29080은 ShiftyPad 리전 id지 API의 `nikke_area_id`가
        아니다** — API area는 **81**(인터내셔널 서버; A·B 모두 81, 검색 예시 uid도 29080).
        이 함정으로 첫 조회가 `param invalid` 났다가, area 81로 고치니 통과.
      - **크로스계정 3콜 전부 `code 0`:** `GetUserCharacters(B)` 182보유 ·
        `GetUserCharacterDetails(B)` 육성입력(`arm_equip_*`·`attractive_lv`·`harmony_cube_*`
        =계산기 소비 필드) · `GetUserProfileOutpostInfo(B)` 기업연구 9행. **B2 계산기(159/159)와
        합치면 페이지 스크래핑 0회로 전 로스터 레벨400 ATK 산출** = 동기화 데이터 파이프라인 성립.
      - **무인증(세션 없는 curl)은 `game not login`으로 거부** — 진짜 공개 API는 아니다.
        읽으려면 **호출자 측 유효 세션**이 필요(대상 유저 자격증명은 불필요).
      함의: read에는 소유권 증명이 불필요하나 **귀속(로스터를 "이 유저 것"으로 저장·공유)에는
      필요**하다 — Fienn: 첫 sync 1회 증명 → open_id 바인딩 → 이후 재sync(육성 반영) 무인증.
      악용(타인의 공개 URL을 자기 것으로 제출한 허위 귀속·대량 수집) 차단이 목적.
      **소유권 증명 채널 확인 (2026-07-19):** 게임 프로필엔 free-text 자기소개 필드가 없다
      (`GetUserProfileBasicInfo(B)` 전체 덤프로 확인 — nickname·lv·profile_team·icon만).
      대신 크로스계정 읽기+유저 편집이 모두 되는 채널 둘: (a) `nickname` = 자유텍스트·고엔트로피지만
      **닉변 재화 소모**, (b) **`profile_team`(전시 5유닛 slot별 name_code) = 무료 편집**.
      → **채널 (b)가 우수**: 우리가 이미 보유 로스터를 읽으므로 "보유한 이 N유닛을 이 슬롯 순서로
      전시하라" 챌린지를 내고 `profile_team` 재조회로 확인 — 무료·항상수행가능·인게임접근 증명.
      엔드포인트 진짜 이름은 `GetUserProfileBasicInfo`(Base 아님; 추측 이름들은 `220000 not permission`).
      edenpj가 쓴 "자기소개란"은 커뮤니티 프로필이거나 닉네임이었을 것 — 우리는 게임 프로필 무료 채널로 됨.
      **설계 단계 미해결:** ① 대상이 비공개(방패 off)면 조회가 막히는지 — B는 공개라 "공개는 읽힘"만
      확인(비공개 게이팅이 곧 동의 메커니즘일 것; 어차피 sync엔 공개 필요) · ② **호출자 세션을
      누가 공급하나** — 호스티드면 서비스용 blablalink 계정 세션 필요(대상 아닌 *운영자* 자격증명
      저장 문제, 기존 "자격증명 저장 금지" 원칙과 충돌 소지 → 재결정) · ③ 타 리전 유저 `nikke_area_id`
      발견/기본값 · ④ 정찰 당시 edenpj.com 502는 **서버 점검**(운영자 공지), 폐쇄 아님 —
      참조 OOB 패턴 유효하나 위 결과로 그 경로 자체가 불필요. nikkemimir.xyz 생존, `/sync` 미해독(SPA).
- [x] **서브프로젝트 1+2: 페치+조립 슬라이스 구현 완료 (2026-07-19).** `(open_id, area, 주입세션)`
      → collector `roster.json` 형태(레벨400 hp/atk·오버로드·스킬). `backend/app/{blablalink_api,
      roster_assembly,overload_decode}.py` + `stat_assembly.py` HP 추가. **HP 실측 피팅 159/159**
      (measured HP로, PILGRIM+OVERSPEC HP는 한 티어 병합·장비 half-up), **오버로드 재구성 77/77**
      (option_id=700+타입+레벨 디코드 → 값 테이블 로제타 역산). 프론트 `parseRosterJson` 재사용
      (slug·병합 포팅 0). 6 TDD 태스크·최종 리뷰 ready-to-merge·전체 804 passed. spec/plan
      `docs/superpowers/{specs,plans}/2026-07-19-roster-sync-fetch-assemble*`. **잔여(멀티유저 전제):**
      조립 경로 KeyError 4곳(미관측 오버로드 레벨·미등록 타입명·research tid·outpost)이 Fienn 계정
      밖 입력에 실패 → CDN 오버로드 전체 커브+완전 타입명표+방어적 lookup 필요(서브3~7 전). HP 반올림
      slope 검증 부산물: 티어 상수는 장비 모델과 자기일관 분해라 slope 값 직접 교체 불가(insights 기록).
- [x] **멀티유저 전제조건 해결 (2026-07-19).** 위 "잔여" 4곳 전부 방어. 오버로드 미관측 레벨은
      **선형 채움**(타입별 등차수열, 관측 전 구간 오차 <0.01pp, 타입8/9 lv15 교차검증) — 즉
      **CDN 전체 커브 스냅샷은 불필요**했음(과거 계획 폐기). 미등록 타입은 경고 후 해당 라인만
      스킵, `research_ranks` 미연구=rank 0, outpost 방어적 lookup. 추가로 affinity 조회를
      lookup 지점에서 클램프(실측: `attractive_lv` 키 누락 0건 vs 명시적 0이 9건 — 원래 전제가
      반대였음). 남은 미지수는 미관측 효과 *타입명*뿐.
- [x] **서브프로젝트 4: 세션 전략 결정 + 북마크릿 sync 구현 (2026-07-19).** **운영자 세션 기각,
      유저 본인 세션 채택.** 실측으로 확정: blablalink 페이지에서 북마크릿이 CSP에 막히지 않고
      실행되며 `credentials:'include'` fetch가 CORS를 통과해 `code:0`과 완전한 데이터를 반환
      (연구 랭크가 테스트 ground truth와 일치). `game_openid`는 HttpOnly라 open_id는 공유 URL로
      받아 북마크릿에 각인. 저장 모델 **A(서버 저장 없음)** — 로스터는 localStorage, 백엔드
      `POST /api/assemble-roster`는 무상태. 익명 클라이언트 ID는 분석 전용(우리 백엔드에만 동봉).
      **서브프로젝트 3(소유권 증명)은 이 결정으로 불필요해져 소멸** — 자기 세션으로 자기 데이터를
      제출하므로 증명 대상이 없음. 9개 TDD 태스크, 백엔드 819 / 프론트 158 passed.
      spec/plan `docs/superpowers/{specs,plans}/2026-07-19-roster-sync-bookmarklet*`.
      **비목표(설계 명시):** 모바일 미지원(북마크릿 설치가 현실적으로 불가) · 기기 간 동기화 ·
      로그인/회원가입. **미완:** 실계정 브라우저 스모크 1회(팝업 차단 동작 확인) · 개인정보
      처리방침 · 디렉토리 스냅샷 갱신 루틴 · 배포 인프라(현재 리모트 없음).
- **원칙:** 자격증명 저장 금지(토큰은 Fienn 공급) · 인증이 httpOnly 쿠키뿐이면 세션
  자동화는 거부하고 반수동 브리지로 강등 · **폴백은 언제나 "기존 수동 폼"**(서드파티는
  죽는다 — dotgg가 두 달 전에 그랬다).
- 계획 전문: `C:\Users\fienn\.claude\plans\phase-7-sprightly-manatee.md`

---

## To-Do (작은 단위)

로드맵보다 잘게 쪼갠 실행 항목. 끝나면 `[x]`로 체크.

### 로스터 동기화 후속 (2026-07-19 병합 직후 열림)

- [x] **하모니 큐브 효과 배선 + lv15 정규화 — 완료 (2026-07-20).** 전원 Resilience 큐브
      Lv.15 착용 가정(전역 1종)으로 배선 — 재장전 속도 29.69% / 우월 코드 대미지 19.09%,
      `tables.json`에서 유도해 인게임 툴팁과 대조 완료. 미결이던 "전역 1종 / 유닛별 /
      엔진이 선택" 쟁점은 전역 1종으로 결정, 유닛별 선택은 다음 확장으로 defer. 부수로
      `other_elemental_bonus`(우월 코드 대미지) 원소 우위 게이팅 버그도 수정. 상세는
      `docs/engine-gaps.md` 갭 #12, `docs/decisions.md`, `docs/superpowers/specs/
      2026-07-20-harmony-cube-assumed-lv15-design.md` 참고.
- [x] **북마크릿 탭 재사용 — 완료.** `window.open(appOrigin, 'nikke-deck-builder')`로 창 이름을
      줘 재동기화 때 기존 탭을 재사용(`frontend/src/lib/bookmarklet.ts`).
- [x] **표시 개선: `core_level`이 임포트 시 항상 0으로 보인다 — 완료.** grade/core 배지
      (`InvestmentBadge`, Task 3)가 실제 투자 표시를 맡고, 아무도 읽지 않던 입력
      `core_level`은 제거(Task 4, `docs/decisions.md` 참고).
- [x] **애장품 소유 자동 판정 — 완료 (2026-07-24).** 듀얼 슬롯 유닛이 base로 싸울지
      `-signature`로 싸울지는 유저별 투자인데, `resolveSlugForUnit`이 개발자 계정을 담은
      손관리 상수 `SIGNATURE_OWNED`(Laplace·Drake 2개)로 답하고 있었다. 모든 유저가 그
      둘을 애장품 보유로 승격받고, 나머지 듀얼 슬롯 5쌍(flora·julia·phantom·rosanna·
      sugar)은 도달 불가였다. 블라블라링크 페이로드가 이미 유닛별 `favorite_item_tid`를
      싣고 `roster_assembly`가 스탯에 쓰고 있었으므로, `assemble_unit`이
      `owns_favorite_item()`을 `favorite_item` 플래그로 함께 내보내고 프론트가 그걸
      따른다. **`SIGNATURE_OWNED`는 완전히 삭제**(Fienn 결정 2026-07-24: 손관리 폐기) —
      로스터가 침묵하면 base로 두는 게 기본값이다. 잘못 승격하면 추천이 부풀지만
      승격을 놓치면 저평가에 그치고, 슬러그는 UI에서 직접 고칠 수 있다. 수집기
      스크레이프 경로는 ShiftyPad가 수집품 **이름**만 보여주고 등급은 안 보여줘
      플래그를 못 만든다 — Collection 탭(`favorite_rare`) 캡처가 그 갭의 해법.
- [x] **애장품 빌드가 base 슬러그에 박힌 6유닛 분리 — 완료 (2026-07-24).** `helm` ·
      `miranda` · `moran` · `privaty` · `tove` · `zwei` 전부 base + `-signature`
      쌍으로 분리. 감사 스크립트 BAKED 6 → **0**, PAIRED 7 → **13**, 종료코드 0.
      각 유닛이 애장품 미보유 유저에게 잘못 주던 것: Helm 버스트 8236.8%(base
      1237.5%, 6.7배) + 풀차지 넉 + 차지댐 라이더 · Miranda의 Wake Up! 자버프
      전체와 top-2 버스트(base는 top-1) · Zwei의 스택형 Pierce와 10초 크리창(base
      5초) · Privaty의 Designated Target 1687%와 버스트 1407.64%(base 457.87%) ·
      Moran의 버퍼 역할 전체(버스트 쿨감 + 스쿼드 flat ATK) · Tove의 크리율
      10.08%(base 3.32%)와 15초 창(base 10초).
      **부수 성과:** Moran의 Bring It On! 라이더를 신규 인코딩(`every_during_segment`
      — "무기 변경 중 노멀 5회마다", Snow White: Heavy Arms 선례) · 무기변형 스케줄
      2건이 슬러그를 하드코딩하고 있던 것을 파라미터화(안 고쳤으면 signature 빌드가
      버스트 시각을 못 찾아 변형이 조용히 사라짐) · lootandwaifus 소스의 애장품
      스킬 제목 오류 수정(Tove).
      **Fienn 룰링(2026-07-24):** 보스는 스턴 불가 → Privaty의 "Stun 시 1089%"는
      defer · Tove의 5% 확률 트리거는 기대값(20발마다 1스택, 60발≈5초에 만렙)으로
      풀스택 가정을 유도 · flat 최대탄약은 프리미티브 부재로 defer.
      **남은 갭(분리 이전부터 있던 것, 문서화만):** Moran 애장품의 "Fervor: 버스트
      쿨 ▼20초 상시" 미모델 · Tove의 Emergency-Crafted Bullets 전체 미모델.
- [x] **애장품 판정 불가 2유닛 — 해소 (2026-07-24).** `laplace-ultimate-hero` ·
      `maxwell-ordinary-mechanic`은 ShiftyPad 소스라 `dollskills` 키가 없고 동일
      슬러그의 lootandwaifus 파일도 없어 데이터로는 답할 수 없었다. **Fienn 룰링:
      둘 다 게임에 애장품이 출시되지 않았다** → 감사 스크립트의
      `NO_FAVORITE_ITEM_RELEASED`에 근거와 함께 기록. 출시되면 항목을 지워야 한다.
- [ ] **개인정보 처리방침** — 공개 배포 전 필요(설계 스펙에 명시, 법률 검토는 범위 밖).
- [x] **디렉토리 스냅샷 갱신 루틴 — 완료.** 매일 19시 작업 스케줄러가 공개 디렉토리를
      헤드리스로 받아 커밋된 스냅샷과 비교하며, 신규 SSR 또는 실패 시에만 토스트를 띄운다.
      등록은 `scripts/schedule_new_nikke_check.ps1 -Action register`(메인 체크아웃에서 실행).
      **운영·문제 대응:** `docs/new-nikke-detection.md`.
- [x] **무기+기본스킬 데이터원 ShiftyPad 전환 (go-forward) — 완료.** dotgg(2026-05 사망)의
      신규 유닛 무기 스탯 수동 스텁을 없앴다. `collect.js --nikke`로 받은 ShiftyPad 상세
      페이로드를 `normalize_shiftypad`가 dotgg 모양으로 정규화 → `source:"shiftypad"` manifest는
      dotgg와 동일 모양이라 하위 파싱 전부 재사용. dotgg 정답지 대조 패리티 하니스(6무기타입,
      불일치 0)로 검증. 기존 71유닛 불변. dollskills(시그니처 9유닛)·skill1/2 쿨다운은 ShiftyPad
      미노출 → 기존 경로 유지. `docs/decisions.md`·`docs/insights.md` 참고.
- [ ] **배포 인프라** — 현재 리모트도 배포도 없음. 저장 모델 A는 정적 호스팅 + 기존 API로 충분.

### Burst 3 어태커 인코딩 배치 (eb) — least-blocked 우선

수집된 Burst 3 니케 39명(어태커 37 + 디펜더 2, +기존 인코딩 anis:ss) 중 미인코딩
어태커를 3명 단위 배치(eb)로 인코딩. 각 배치 전 해당 유닛 스킬을 직접 확인해 blocker
검증. (Fienn 방침 2026-07-12.)

- [x] **eb1** (2026-07-12): Noir ✅ · Isabel ✅ · Liberalio ✅
- [x] **eb2** (2026-07-12): Ludmilla: Winter Owner ✅ · Chisato Nishikigi ✅ · Jill Valentine ⚠
- [x] **자원 primitive beachhead** (gap #2 Pattern A, 2026-07-12): Modernia ⚠ ·
      Guillotine: Winter Slayer ⚠ — named-resource/캡 스택 카운터 엔진 확장 + 첫 소비자.
- [x] **count-스케일 넉 + multi-hit 버스트 + periodic fill** (2026-07-12): Julia ⚠ ·
      Julia(시그니처, 별도 slug `julia-signature`) ⚠ · Cinderella ⚠ + Guillotine의
      Extermination Hero-Level DoT 완성. `resource_scaled_nukes`/`burst_hit_counts`/
      periodic 자원 fill 엔진 확장 + 소비자. base/시그니처 별도 slug 패턴 확정
      (Fienn 결정) — drake/laplace 인코딩 시 동일 패턴 적용.
- [x] **eb3 Pattern-A 자원 유닛 배치** (2026-07-12): Quency: Escape Queen ✅ ·
      Soda: Twinkling Bunny ⚠ · Maiden: Ice Rose ⚠ — 6개 신규 엔진 확장 소비자:
      자원 **reset**(`SquadContext.reset_resource`/`resource_count_before_reset`,
      Soda의 Golden Chip이 버스트에서 17로 리셋) · `("per_shot_every_during_full_burst",
      N)` fill(FB창 안의 발사만 세는 자원 채우기) · `ResourceSpec.resets`를 통한 시간순
      fill+reset 리플레이(resolution 패스) · `resource_gated_buffs`(버스트 시점 자원
      count 게이팅 **버프**, resolution 패스 안에서 처리 — 넉과 달리 phase 2가 없음) ·
      `_resolve_squad_burst_cycle_resource`(스쿼드 전체 버스트-사이클 이벤트 + 자원 자신의
      값으로 조건 거는 fill, Maiden의 MP) · `dynamic_hit_count_nukes`(버스트 넉 히트수
      자체가 자원 값, Maiden의 Diamond Dust) + `extra_flat_atk` 파라미터(넉 전용
      flat_atk 보너스). 신규 갭 2건 발견: **#7 FB창 한정 per-shot 트리거**(Soda 잔여
      공동발동 버프)·**#8 자원-fill-트리거 타 유닛 버프**(Maiden 잔여 MP-회복 아군 버프)
      — `engine-gaps.md` 참고.
- [x] **eb4** (2026-07-12): Asuka Shikinami Langley: Wille ⚠ · Mana ⚠ — 4개
      신규 엔진 확장(`fire_delay`+`own_burst_delayed`·own-status-window fill·
      `full_burst_bonus_eligible`·`resource_scaled_nukes`의 `resource` 선택화)
      소비. `cinderella-crystal-wave`는 무기-모드 상태머신 유닛으로 재분류되어
      배치에서 제외(아래 무기 변형 항목으로 이동).
- [x] **매니페스트 예외 4유닛 해소** (2026-07-18): anis-star(dotgg 소스+drop_tokens)·
      asuka-wille(픽스처 재전사+빌더 재번호, dotgg url `asuka-wille` 브리지)·
      privaty(dollskills 네이티브 순서로 스왑)·neon-vision-eye(전사 오류 2슬롯 교정)
      → `KNOWN_MANIFEST_EXCEPTIONS` 빈 집합, **매니페스트·API 로더블 61/61(전원)**.
      Phase 6의 "픽스처 재배열 4유닛 잔여" 기록은 이걸로 종결(그 섹션은 병렬 세션
      규칙상 이 배치에서 편집하지 않음 — 병합 후 정리).
- [x] **정리 배치 (2026-07-18)**: SG 스코프 정밀화(drake-signature·arcana-fortune-mate
      — squad 근사 제거, arcana의 except-self 과대적용 제거) + Little Mermaid
      Bubble Barrage(아군 총탄 500 카운터)를 `scheduled_nukes`+전 유닛
      `context.shot_times` 병합으로 인코딩(⚠→✅, 엔진 확장 불필요).
- [x] **red-hood 재검증 + 인코딩** (2026-07-18): Pattern B 판정이 Phase S 이전의
      낡은 것임을 확인(charge speed는 이제 딜 스탯). Glaring Eyes 정상상태 10스택
      +38.1% 상시·초과분→차지댐 변환·Wild Tooth 자ATK·Step 3 무기변형(Fienn 실측
      33발/10초·무한탄창 앵커, `scheduled_nukes` 이중계상 정적 차감) — 엔진 확장
      없음. E2E: 변형이 본인 포함 덱 총딜의 30%.
- [ ] **eb3+ 백로그** — 대부분 **자원 유닛(gap #2 Pattern A 잔여/Pattern B)·상태머신·
      무기변형**. 배치 착수 전 유닛별 검증 필수.
  - ~~**Pattern A 자원 유닛**: `rei-ayanami`·`rei-ayanami-tentative-name`·
    `neon-vision-eye`~~ — **전부 2026-07-16에 인코딩 완료**(이 백로그가 갱신 누락된
    상태로 남아 있었음, 2026-07-17 정정). Pattern A는 이제 소진.
  - ~~**검증 완료, 인코딩 대기 (2026-07-17 검증 배치)**: `raven`·`sakura-bloom-in-summer`~~
    → **둘 다 인코딩 완료**(2026-07-25 확인, 이 줄이 갱신 누락된 채 남아 있었음).
  - ~~검증 완료, 갭 확인 (2026-07-17): `scarlet-black-shadow`(gap #10)~~ →
    **인코딩 완료 (2026-07-18)** — `per_shot_rules` `"sequence"` 모드 확장 +
    Pulse `damage_type` 배선. 같은 배치에서 velvet Sticky Fingers
    (`every_outside_full_burst`) · modernia Giant Leap(Fienn 정정: 상태창 무관
    전투시작 200히트 — gap #7 후보 소진) 잔여 메커니즘도 인코딩.
    `milk-blooming-bunny`(gap #11 — 강제재장전/탄약제거 상태머신, 중~대)는 여전히
    미착수.
  - ~~**Pattern B 게이지·변신 (일반 프리미티브 잔여, gap #2)**: `mihara-bonding-chain`
    (체인)·`elegg-boom-and-shock`.~~ → **둘 다 인코딩 완료 (2026-07-19), gap #2
    Pattern B 소진.** 검증 결과 **애초에 Pattern B가 아니었음**(감쇠 게이지·변신 없음,
    결정론적 fill의 Pattern A 자원 유닛 — red-hood와 같은 낡은 분류). 엔진 확장 4건
    소비: reset `value_fn` · `hit_count_fn` · 다중 소스 fill · `scheduled_nukes`의
    `resource_gate`. 상세는 `engine-gaps.md`/`encoded-nikkes.md` 참고. (~~`red-hood`(charge speed·딜 아님)~~ →
    **2026-07-18 재검증으로 판정 정정·인코딩 완료**: Phase S 이후 charge speed는
    딜 스탯이고, Step 1/2/3은 버스트 슬롯 선택이라 B3 고정 시 Step 3만 유효,
    무기변형 창은 Fienn 실측 33발 앵커 `scheduled_nukes` — 엔진 확장 없음.
    `ark-ranger-black`은 2026-07-16 `part_destructible` 보스 플래그 브래킷으로
    개별 인코딩 완료 — 일반 프리미티브 소비는 아님, `engine-gaps.md` gap #2 참고.)
  - **상태머신/특수 트리거**: ~~`diesel-winter-sweets`(Intro/Highlight+지속딜)~~ →
    **2026-07-19 완료** — `MODE_VARIANTS`로 `-intro`/`-highlight` 2슬러그. 상태가
    첫 풀버스트에 확정되어 전투 내내 고정(Fienn 판정)이고, **엔진이 실제
    시뮬레이션하는 버스트 스케줄로 갈리므로** Highlight에 `burst_delay
    {"skip_cycles": 1}`을 실제로 걸었다(정적 슬러그만으론 과대평가). 같은 확장으로
    Elegg의 캡 대기 운용도 해결 — `docs/engine-gaps.md`의 "유닛별 버스트 스케줄
    정책" 참고.
    `bready`(Taste), `dorothy-serendipity`(펠릿 카운터), `eve`(크리티컬-히트 카운터 —
    Julia 시그니처 인코딩 중 확인됨: 기대값 크리 모델과 구조적으로 불가, **영구 defer**
    가능성 높음, 착수 전 재확인),
    (`ada-wong`은 2026-07-16 Phase C에서 인코딩 완료 — gap #6 during_full_burst 소비,
    `scarlet-black-shadow`는 2026-07-18 gap #10으로 인코딩 완료),
    `milk-blooming-bunny`(gap #11)
  - ~~**무기 변형**(버스트/평타가 다른 무기모드로 전환 = 핵심 딜, 미지원): `snow-white`,
    `snow-white-heavy-arms`, `maxwell`, `cinderella-crystal-wave`~~ →
    **v1 엔진 프리미티브 착지 완료 (2026-07-19, `weapon_mode_schedules` 세그먼트)**
    — 설계 `docs/superpowers/specs/2026-07-18-weapon-transform-design.md`(상태:
    구현 완료). snow-white ✅·maxwell ✅ 신규 인코딩, laplace-signature 신규 슬러그
    신설(변형 10초 창을 세그먼트로 모델), red-hood는 기존 `scheduled_nukes` 근사에서
    세그먼트로 마이그레이션(정적 차감/상수 접기 제거, 덱 차지댐 버프가 변형샷에
    곱해짐, 총딜 ~+1.6%). ~~**남은 무기변형은 계획 2 백로그**: `cinderella-crystal-wave`
    → `-mg`/`-snipe` 듀얼슬러그(정적 프로필 2벌 + 모드별 FB 넉/버프 + 덱 탐색 상호
    배제, Snipe 프로필 세부는 인코딩 시 Fienn 확인) · `rapi-red-hood`(세그먼트 대상
    아님 — `scheduled_nukes` context에 FB창 노출만 필요) · `snow-white-heavy-arms`
    (차지 루프 상태머신, 기존 per-shot+multi-hit 프리미티브로 풀리는지 검증 패스
    대기)~~ → **계획 2 착지 완료 (2026-07-19).** `cinderella-crystal-wave`는
    `registry.MODE_VARIANTS`로 `cinderella-crystal-wave-mg`/`-snipe` 두 정적 슬러그로
    갈라짐(전투 전 모드 고정 — 상태머신 아님, 로스터가 소유 유닛 1개를 후보 여러 개로
    fan-out, `_no_variant_clash`가 두 모드 동시 편성을 덱 탐색에서 금지). `rapi-red-hood`는
    신규 `SquadContext.full_burst_windows` + `boss_core_hittable()` 노출로 120노멀
    프로젝타일 발사기가 완성(부착 누적 → 다음 FB 진입에서 일괄 폭발, 신규
    `projectile_attachment` 데미지 타입) + 신규 슬러그 `rapi-red-hood-b1`(Combat
    Assist를 실제 B1 후보로 편성, 원래 이번 배치 범위엔 없었으나 착수 중 추가된 항목).
    `snow-white-heavy-arms`는 검증 결과 **신규 상태머신이 필요 없었음** — Auto Fire는
    기존 per-shot 룰을 타고, Seven Dwarves Fully Active는 세그먼트(3.2초 차지 2발,
    +528% 차지댐을 프로필에 접어 덱 차지댐 버프가 계속 곱해짐)이며, 신규
    `every_during_segment`/`every_outside_segment` per-shot 모드가 강화/평시 Auto
    Fire의 이중계상을 구조적으로 막는다. velvet 변형딜(저가치, 보류 확정) · laplace
    base의 5초 변형(실측 없음, 보류)만 잔여. 상세는 `docs/engine-gaps.md`,
    `docs/superpowers/specs/2026-07-18-weapon-transform-design.md`(상태: 계획 2
    착지 완료).
  - ~~✱ = 애장품(dollskills) 보유, base/시그니처 별도 slug: `drake`, `laplace`~~ —
    **drake는 2026-07-16, laplace는 2026-07-19 완료** — drake는 base+signature
    듀얼슬롯, laplace도 이제 듀얼슬롯(`laplace-signature`, 세그먼트 무기변형).
    "시그니처는 무기변형이라 듀얼슬롯 없음"이라던 2026-07-17 정정은 **틀렸음** —
    2026-07-19 세그먼트 프리미티브 착지로 뒤집힘(위 항목 참고). base laplace의
    5초 변형은 여전히 보류(실측 없음).
- [x] `damage_taken_up` / `other_core_damage_sources` 엔진 연결
      — 완료. squad 스코프 적 디버프, 코어 데미지는 `core_hittable` 게이팅.
- [x] `NikkeSpec`에 스킬별 유저 레벨 필드 추가 → 조립 시 `levels[level-1]` 선택 일반화
      — 로더 쪽으로 흡수 완료 (2026-07-16): `user_roster.load_nikke_spec`이
      유저 스킬레벨로 `assemble_skill_values`를 호출해 NikkeSpec을 조립.

### gap #5 후속 (2026-07-16 배치 중 발견, 미착수)
- [x] **`rei-ayanami`** (2026-07-16): Preemptive Subdual의 "Elemental Advantage Attack
      Damage +30.23%/3s"(노멀100회마다)를 `other_elemental_bonus` +
      ~~`boss_is_element("Iron")` 게이팅(Fire>Iron)~~, 넉과 같은 every-100 트리거에
      refresh 버프로 인코딩. ⚠→✅ (비-DPS 실드만 잔여). **2026-07-20 정정: "Fire>Iron"은
      틀린 원소 주장임** — `elements.py`의 순환은 Water>Fire>Wind>Iron>Electric>Water이라
      Fire는 Iron이 아니라 Wind를 이김. 스킬 원문도 원소를 특정하지 않음. 이후 착지한
      damage_formula의 원소우위 게이트와 이 Iron 게이팅이 상호배타적이 되어 버프가 어떤
      보스에서도 발동 못 하는 버그로 이어짐(gap #5 자체는 정상 해소, 게이팅 로직이
      문제). 게이팅 제거, damage_formula의 우위 게이트만으로 판정하도록 수정
      (commit `9079710`, `rei_ayanami.py`).
- [x] **`anis-sparkling-summer`** (2026-07-16): Sparkling Wave의 "Elemental Advantage
      Attack Damage +42.24%"를 `other_elemental_bonus`(element bonus damage) +
      `boss_is_element("Water")` 게이팅(Electric>Water)으로 인코딩. 이 유닛의 잔여
      deferred DPS 효과 없음(✅ 완결).

### Phase 5 선행 소작업 (2026-07-17, 설계 중 발견)
- [x] **Prika Encore 자기 버스트쿨 +21초 인코딩** — 현재 미인코딩이라 시뮬에서
      Prika가 3사이클째 재버스트해 Mint의 버스트(→Encore)를 밀어냄 =
      Mint+Prika 세트 과소평가. 기존 버쿨감 펄스 경로에 음수 값(−21)으로 태우면
      `last_used_at`이 뒤로 밀려 "첫 사이클만 Prika, 이후 Mint 전담" 로테이션이
      재현됨(Fienn 확인 2026-07-17). 음수 펄스의 `on_full_burst_end` 통과 검증 +
      Encore 슬롯 값 추출 포함. Stage 1(한계기여도 측정) 착수 전 완료 필요.

### Phase 3 검증 배치 (2026-07-17)
- [x] **미검증 5유닛 검증** — ein ✅(인코딩 완료) · raven·sakura-bloom-in-summer
      (인코딩 가능, 대기) · scarlet-black-shadow(gap #10) · milk-blooming-bunny(gap #11).
- [x] **Ein 인코딩** — `scheduled_nukes` 확장 + Fienn 실측 기반 페더 스케줄.
- [x] **raven·sakura-bloom-in-summer 인코딩** (2026-07-17) — sakura는 확장 불필요가
      맞았고, raven은 `context.shot_times` 소규모 확장 1건 필요했음(판정 정정).
- [x] **무기변형 v1 착지 (2026-07-19)** — 설계 논의 완료 후 `weapon_mode_schedules`
      세그먼트 프리미티브 구현: snow-white ✅·maxwell ✅ 신규 인코딩, laplace-signature
      신규 슬러그, red-hood 세그먼트 마이그레이션. (gap #10 scarlet·red-hood는
      2026-07-18에 이미 인코딩 완료.)
- [x] **무기변형 계획 2 착지 (2026-07-19)** — v1이 남긴 잔여 3건을 닫음:
      cinderella-crystal-wave → `-mg`/`-snipe` 듀얼슬러그(`MODE_VARIANTS`) ·
      rapi-red-hood FB창 노출(`full_burst_windows`+`boss_core_hittable`, 120노멀
      발사기 완성) + 신규 `rapi-red-hood-b1`(Combat Assist B1 후보, 착수 중 범위
      추가) · snow-white-heavy-arms(신규 상태머신 불필요, 세그먼트+
      `every_during_segment`/`every_outside_segment`로 해결). **남은 미인코딩
      6명**: Pattern B 게이지(mihara-bonding-chain·elegg-boom-and-shock) ·
      상태머신(~~diesel-winter-sweets~~ 2026-07-19 완료·~~bready~~ 완료·
      ~~eve~~ 2026-07-20 완료) · ~~gap #11(milk-blooming-bunny)~~ 2026-07-20 완료.
      **미인코딩 0명 — 수집된 유닛 전원 인코딩 완료.**
- [x] **ein weapon 스탯** — 이미 `data/dotgg/char_ein.json`에 존재했음(SR·장탄6·
      재장전2.0s·차지1.0s·차지댐250%). "부재" 판정은 워크트리에 gitignore된 데이터가
      복사되지 않아 생긴 오진이었음 — 아래 함정 항목 참고.
- [x] **워크트리 데이터 동기화 함정** — `data/dotgg/`·`data/lootandwaifus/`가 gitignore
      대상이라 새 워크트리엔 안 따라오고, 거기서 로더블/커버리지를 측정하면 **거짓 음성**이
      나온다(2026-07-17, Fienn이 ein 오진을 잡아내며 발견). **`scripts/sync_worktree_data.py`로
      자동화 완료** — 워크트리 작업 시작 시 확인 없이 바로 실행할 것(Fienn 지시).
      메인에선 no-op, 없는 파일만 복사, 재실행 안전. `docs/insights.md`에도 기록.

### 통합 완료 — `worktree-plans-frontend3-encoding` → `wip/scaffolding` (2026-07-17)
- [x] **머지 완료.** 예상대로 `docs/decisions.md` 위치 충돌 1건만 발생 — 양쪽 항목을
      모두 살려 해결. 머지 결과에서 **746 passed**.
- [x] **로더블 수치 실측 정리 완료** — 상충하던 56/60 vs 53/57 중 **56/60이 사실**
      (`ENCODED_SLUGS` × `load_nikke_spec` 실측). 53/57은 Ein·Raven·Sakura 인코딩
      이전 값이라 낡은 것이었음. 아래 과거 로그 항목의 53/57은 그 시점 기록이라 유지.
- [x] **SessionStart 훅 전파** — `.claude/settings.json`이 머지되어 이후 새 워크트리엔
      데이터 동기화가 자동 적용된다.

### 완성도 배치 (2026-07-20, 2회차 감사)

같은 날 1회차 배치가 "남은 구조적 보류는 4가지"라 결론냈으나 그 감사가 불완전했다.
2회차 전수 재감사에서 **STALE 17건**(엔진이 이미 지원하는데 defer로 남은 것)을 확인.

- [x] **배치 ① 프리미티브 재활용 (7유닛)** — anis-star(Shooting Stars +
      차지시간 고정, 개인딜 +80.5%) · helm(애장품 풀차지 178.98% + Aegis 10라운드
      차지댐, +72.9%, ⚠→✅) · ludmilla(Snowstorm 코어60넉, 코어 보스 +21.4%) ·
      cinderella(Flawless Glass 차지속도, 발수 +144%) · crown(Royal Attire,
      힐러 명단 유도 스크립트 신설) · liberalio(차지속도 면역) · mana(보류 사유만 정정).
      엔진 확장 2건: `deck_contains_any` · `EffectRegistry.set_external_stat_immunity`.
      `nikke-skill-encoding` SKILL.md의 "차지속도는 inert"(Phase S 이전 기술) 정정 포함.
- [x] **배치 ② 무기변형 잔여 (완료 2026-07-22)** — 2026-07-19에 `weapon_mode_schedules` 세그먼트가
      착지했는데도 "무기변형 미지원"을 근거로 defer된 유닛들. 인코딩 5(nayuta·zwei·laplace·
      takina·moran) + 편성상 제외 2(modernia·velvet).
      **`nayuta` 완료(2026-07-21, E2E +18.07%, ⚠→✅)** — 탄약 무한이라 세그먼트의
      no-reload 제약이 무효였고, "Fixed at 1.8 sec"은 `rate_of_fire`로 표현.
      dotgg→lootandwaifus 소스 이관 필요했음.
      **`zwei` 완료(2026-07-21, E2E +0.82%)** — "Max Ammo 1"이 곧 단발 변형이라는 뜻이라
      Maxwell 선례 그대로 `until_shots: 1`. 지속시간이 원문에 없던 이유가 이것이었다.
      **`laplace` base 완료(2026-07-21, E2E −0.07%)** — Fienn 확인: base Buster 발사속도 =
      시그니처(실측 9.3/초)와 동일. 5초 창 `end` 방식 ~46틱, `BUSTER_RATE_OF_FIRE` 공유.
      시그니처와 달리 Hero Vision 미모델이라 true 변환 안 함. base RL 5초분과 거의 동등.
      **`modernia`는 세그먼트를 넣지 않기로 확정(Fienn 2026-07-21)** — 보스전에서 Modernia
      버스트는 DPS 손해(Destroy Mode 평타 2.24% << base MG 7.71%, 멀티타겟 auto-aim은 단일
      보스에서 무가치). 그래서 실전은 **버스트 미사용 평타 딜러**((1,1,3) 맨 오른쪽). 세그먼트를
      넣으면 엔진이 버스트를 강제해 ~12% 저평가(스윕 확인). 현재 base MG 평타 유지가 오히려
      버스트 미사용을 정확히 근사(Destroy Mode·무한탄약·FB+5s 전부 안 쓰는 버스트에서만 발동).
      **`takina-inoue` 완료(2026-07-22)** — Fienn 실측 FB 10초 25타 → `until_shots: 25`
      (end 방식이면 마지막 발이 t+10 경계로 떨어져 24발). 변형샷을 `damage_type="true"`로
      고정(같은 버스트 bullet이 평타를 진댐 변환, 이 샷들이 곧 그 평타) → 자35%·아군140%
      진댐 버프가 여기 실림. 이제 잉여가 된 self `normal_attacks_deal_true` 제거.
      **`moran` 완료(2026-07-22, E2E +5.54%)** — AR→무한탄창 SMG, 14.7%/발, 10초. 무한탄창이라
      인게임 발수 측정 불가·가이드도 없음 → Fienn 승인 하에 **엔진 표준 SMG 발사속도(20/초)**를
      앵커로(변형이 SMG이므로 실측 무기클래스 상수 재사용, 발명 아님). `end` 방식 ~200발.
      dotgg dollskills[2]에 전 슬롯 존재해 소스 이관 불필요.
      **`velvet`는 세그먼트를 넣지 않기로 확정(Fienn 2026-07-22)** — 실전은 버스트 미사용
      **토템**(Skill 1/2 버프만), 버스트 변형(7%/발, 저가치)은 발동 안 함. Modernia와 동류.
      "무기변형 미지원" defer 사유가 stale이었으므로 사유를 편성 결정으로 정정.
      **주의: 세그먼트는 재장전을 하지 않는다** — 창 길이 > 탄창 지속이면 과대평가
      (Nayuta·moran처럼 무한탄약이 걸린 변형은 이 함정이 없다).
- [x] **후속: Modernia·Velvet 버스트 미사용 편성 (2026-07-22 완료)** — `burst_delay` skip이
      아니라 **deck_search 좌석 제약**으로 구현. `_BUFFER_SEAT_SLUGS = {modernia, velvet}`이
      각 유닛을 자기 tier의 **마지막 좌석**으로 고정(burst_cycle이 leftmost eligible를 쏘므로
      tier-mate가 버스트를 가져감). shape는 하드 제약 안 함 — 검토 중 **shape 강제는 얇은
      로스터(modernia+B3<3 등)를 편성 불가(422)로 만드는 회귀**가 발견됨(API 테스트가 잡음).
      좌석만 걸면: 리치 로스터는 시뮬이 (1,1,3)/(1,2,2)를 상위로 뽑아 버스트 0회(측정 확인),
      커버 불가한 얇은 덱에서만 fallback 버스트(Full Burst를 살리는 실전 동작). `skip_cycles:
      inf`(스윕 셸 붕괴 이슈가 있던)보다 fallback을 보존해 더 충실. 상세 `docs/decisions.md`.
      B3 항상 ≥2 규칙(cd 40초라 2명 번갈아야 매 사이클 커버) 근거는 Fienn 지적으로 정정됨 —
      Modernia는 (1,2,2)/(2,1,2)에서 토템 불가, (1,1,3) 전용.
- [x] **배치 ③ `rosanna-chic-ocean` (2026-07-21 완료)** — Spina di Rosa 전체 인코딩.
      예상대로 `scheduled_nukes`의 스케줄 콜백으로 듀티사이클을 표현했고, 버프 절반은
      `periodic_rules`. 실제 값은 약 6300%가 아니라 **5280%/180초** — 강제발동이 없어
      첫 캐스트가 t=30이므로 5캐스트(6캐스트 아님)다. 자기 sustained 버프도 함께 실효화,
      고정 셸 E2E **+7.75%**.
- [x] **애장품 4인방 온보딩 (Sugar · Flora · Rosanna · Phantom) — 인코딩 완료(2026-07-24).**
      넷 다 base + `-signature` 듀얼 슬롯으로 올라갔고 레지스트리·테스트까지 들어갔다.
      **단, 네 `-signature` 슬러그는 아직 추천기에 노출되지 않는다 — 아래 노출 버그 항목 참고.** 설계
      `docs/superpowers/specs/2026-07-24-favorite-item-quartet-design.md`, 계획
      `docs/superpowers/plans/2026-07-24-favorite-item-quartet.md`.
      **선행 배선 완료**: 매니페스트 `weapon_source` 키 — 스킬값은 lootandwaifus
      (dollskills), 무기 스탯은 base의 ShiftyPad 파일에서 읽는다(dotgg API 사망 확인,
      4유닛 모두 200+빈 본문). 무기 손입력 0.
  - [x] **Sugar (2026-07-24 완료)** — `sugar` + `sugar-signature`. SG 아군 최대탄약
        +83.8%와 Water·Iron SG 아군 원소우위딜을 `member_subset_buff_rule`로 **근사
        없이** 모델(레퍼런스 문서가 "표현 불가"라 적고 있었으나 Tove 선례로 반증 —
        문서 3건 정정). 애장품 전용: 엄폐물 온전 시 공격데미지 +19.98% 상시 +
        Fire코드 상대 원소우위 부여(`boss_is_element`). 엄폐 피격 트리거는 Fienn 판단
        으로 두 빌드 모두 defer → 신규 gap #14, 둘 다 floor.
  - [x] **Flora (2026-07-24 완료)** — `flora` + `flora-signature`. 스윕 366.2M →
        563.6M(**+53.9%**)로 배치 최대폭. 애장품이 순수 힐러를 ATK 버퍼로 바꾸는데,
        그 핵심이 **적 공격에 의존하지 않는 자기완결 콤보**(힐 없는 Max HP 증가 →
        HP 비율 90% 하락 → 자기 실드 → ATK +45.12%)라는 Fienn의 해석 덕에 defer를
        면했다. 신규 조건 `burst_stage_entered(tier)` — "Burst Stage N 진입"은
        스테이지의 속성이라 다른 동티어 아군이 슬롯을 가져간 사이클에도 발동해야 한다.
  - [x] **Rosanna (2026-07-24 완료)** — `rosanna` + `rosanna-signature`, 스윕 +40.9%.
        `rosanna-chic-ocean`과 별개 유닛(rid 280 vs 283). Concealment 라이더를 버스트
        퍼센트에 합침(120발=2.0초 사격분마다 10초 재갱신 → 상시, Fienn 승인).
  - [x] **Phantom (2026-07-24 완료)** — `phantom` + `phantom-signature`, 스윕 +46.5%
        (701.3M → **1027.1M**, 전체 최고 딜). base는 Thief's Dagger가 자기 Calling
        Card와 지속이 같아 **영원히 1스택**이라 S2가 통째로 발동 불가(Fienn 확인);
        애장품의 "노멀 30발마다 대거 +1" 한 줄이 그 교착을 풀어 S2 전체를 켠다.
- [x] **애장품 4인방 온보딩 완료 (2026-07-24)** — 8슬러그 전부 등록. 배치 결산:
      Sugar +9.5% · Rosanna +40.9% · Phantom +46.5% · Flora +53.9%. 공통 교훈은
      **애장품이 수치를 키우는 게 아니라 "엔진이 발동시킬 수 있는 트리거"를 붙여준다**는
      것 — Flora(자기완결 실드 콤보) · Rosanna(500발 Frenzy 소스) · Phantom(30발 대거
      소스)이 모두 같은 형태다. 신규 engine-gap #14(엄폐물 피격) · #15(아군 행동불능).
- [x] **차지속도 공식 수정 (2026-07-20, Fienn 승인)** — `charge_time_with_speed`로
      집약, 5개 호출 지점 교체. `÷(1+속도)` → `×(1−속도)`. 감속도 같은 식으로 처리
      (bready −20%가 1.25배 → 1.2배). 버프 0이면 로스터의 모든 기본 차지시간에 대해
      **엄밀한 no-op**이라 미수혜 유닛 타임라인은 비트 동일.
      **하한**: 차지시간이 0에 닿으면 뭔가가 케이던스를 묶어야 하므로 Cinderella
      실측(+100%에서 10초에 29~30발)에 앵커, 보수적으로 29 채택. 메커니즘은 **추정**
      (최소 간격 vs 차지속도 자체 캡을 데이터 1점으로는 구분 불가)이고 값은 RL에서
      나왔다는 점을 코드에 명시.
      **실측 영향(180초, 유닛별 딜, 구공식 대비)**: cinderella +11.8% ·
      red-hood +0.9% · bready −20% 완화 +0.6% · **scarlet·neon·maxwell·raven·ein·
      helm·liberalio는 0.0%**(애초에 차지속도 버프를 안 받음).
      → **B3 RL/SR 전반에 큰 영향'은 아니었다**: 재장전 공백이 작은 탄창 차지무기의
      이득을 크게 상쇄하고(red-hood는 SR 6발 + 변형 세그먼트가 명시 rate라 케이던스
      버프 미적용), 애초에 차지속도를 **주는** 유닛이 로스터에 6명뿐이며 그중 5명이
      자기 자신에게만 준다. 큰 탄창 차지유닛(cinderella 24발)에서만 유의미.
- [x] **Scarlet 인게임 실측으로 공식 확정 + 차지시간 대형 오류 발견 (2026-07-20)**
      Fienn이 60fps 프레임 단위로 FB 10초 창을 측정(차지속도 오버로드 없음):
      버프 없음 **14타/9.52초 = 0.7323초 간격**, Liberalio 버프 시 **18타 = 0.5424초**.
      ① **공식 확정**: 측정 비율 0.7407을 두 가설에 대입하면, Liberalio의
      "캐스터 Charge Speed의 12.74%"를 기본 차지속도 200% 기준 25.48%p로 읽을 때
      `×(1−s)`는 오차 **0.61%**, `÷(1+s)`는 **7.60%**. 프레임 정밀도(~0.017초)상
      전자는 노이즈 안, 후자는 명백히 밖 → **`×(1−s)` 확정.**
      ② **차지시간 오류**: 수집 데이터의 0.30초는 10초에 33발을 의미하는데 실제는
      14발 — **2.4배 과다**였다. 그녀 딜의 대부분이 풀차지 카운터(Fleetly Fading
      3/6/9 시퀀스)라 발수 오류가 최대 딜 소스를 직접 배수한다.
      `_WEAPON_PROFILE_OVERRIDE_BUILDERS`로 측정값 0.7323초 적용(override가 이제
      수집 프로필을 함께 받아 한 필드만 교정 가능). **E2E: 그녀 딜 6,404M →
      2,930M(−54.2%), 덱 총딜 −45.3%.** 하한 우려도 해소 — 실제 기본값이 하한보다
      느려서 클램프에 안 걸린다.
- [x] **Liberalio Calm Depths 인코딩 완료 (2026-07-21).** "200% 기본 차지속도"
      가정은 **틀렸고 불필요했다** — 자료 조사 결과 "시전자 기준"은 퍼센트가
      **캐스터의 차지시간**에 곱해져 절대 초로 전달되는 별개 메커니즘이었다
      (12.74% × 그녀의 SR 1.5초 = 0.1911초). 신규 `lowest_atk_slugs` +
      `charge_time_reduction_sec`로 인코딩.
- [x] **표본 측정 완료 (2026-07-21) — 계통 오류 아님, '검 쓰는 RL' 한정.**
      Fienn 60fps 실측(재장전 버프 100% 초과로 재장전 배제): **Raven** 5타/8.11초 =
      **2.03초 간격**(데이터 1.0초, 차지속도 오버로드 0%) → 교정. **Neon: Vision Eye**
      0.918초 간격(차지속도 오버로드 9.47%) → 기본 ≈1.0초로 **데이터와 일치, 교정 불필요**.
      Neon이 핵심이다 — 29개 차지무기 전체의 계통 오류 가능성을 배제한다. 오류는
      **검을 쓰는 "RL" 두 명**(Scarlet·Raven)에 한정되고, 커뮤니티 가이드도 정성적으로
      같은 말을 한다(nikke.gg: Scarlet은 0.3초 표기에도 "auto로 두면 ~0.7초마다 1발,
      charge delay를 겪는다" / prydwen: Raven은 "느린 아이, 2초 재장전에 animation lock").
      **딜 영향은 구조에 따라 정반대**: Raven은 발수 −45%인데 딜 −10.9%뿐(Shock Wave가
      캡 10에서 포화하는 스택 DoT이고 2.03초 간격이 5초 카운터 수명보다 짧아 고점이
      안 내려감), Scarlet은 같은 성격의 교정으로 **−54.2%**(그녀 딜은 풀차지 시퀀스
      트리거라 발수에 직결).
- [x] **차지속도 공식 확정 + 캐스터 기준 버프 구현 (2026-07-21)**
      자료 조사로 두 미결이 모두 풀렸다.
      ① **프레임 양자화**: 차지속도 n%는 "적용 대상 차지시간의 n%"를 **정수 프레임
      단위로** 깎는다(커뮤니티 실험: "3초는 180프레임, 180프레임의 10.28%는 약
      18.5프레임"). Neon 실측 0.9178초를 5프레임 내림이 **0.07프레임** 오차로 재현
      (연속값은 0.75프레임 어긋남). Alice 등에서 "99%+ 차지속도"를 권하는 이유도
      이걸로 설명된다 — **100%가 차지시간을 완전히 없애는 지점**이라 나눗셈 공식으론
      표현 자체가 불가능하다.
      ② **"시전자 기준"은 변형이 아니라 다른 메커니즘**: 퍼센트를 **캐스터의**
      차지시간에 곱해 **절대 초**로 전달한다. Liberalio는 SR 1.5초라
      12.74%×1.5 = **0.1911초**이고, 이는 커뮤니티 서술("약 0.19초 줄어든다")과
      Fienn의 Scarlet 실측(0.7323→0.5424초)을 **0.07프레임**으로 재현한다.
      퍼센트로 인코딩했으면 틀렸을 것 — 등가 퍼센트가 Scarlet 0.73초엔 26.1%,
      1.0초 유닛엔 19.1%로 갈린다.
      신규 스탯 `charge_time_reduction_sec`(attack_rate에 배선, 퍼센트 적용 후 차감).
      소비자 2명: **Liberalio** Calm Depths(신규 `lowest_atk_slugs`, **캐스터 미제외** —
      커뮤니티가 "리버렐리오 공격력이 흑련보다 높아야"라 하는 건 그녀가 후보 풀에
      있다는 뜻이고, 자기가 받는 게 곧 가이드가 경고하는 편성 실수다. 그녀의 차속
      면역도 두 스탯 모두로 확장 — 스킬은 엔진 필드가 아니라 **개념**에 면역을 준다)
      · **Mana** Metal sigma −0.18초(신규 `longest_charge_time_slugs`, 컨텍스트에
      기본 차지시간 적재). Mana docstring이 예언했던 "두 번째 소비자가 생기면
      특수처리 말고 그걸 만들라"가 그대로 실현됐다.
      **E2E(180초, Scarlet+Liberalio)**: Scarlet 발수 214 → **285(+33.2%)**,
      자체딜 +23.0%, 덱 총딜 +13.0%.

### 정리/보강
- [ ] **`supported_units()`가 `weapon_source`를 무시해 애장품 4인방의 `-signature`
      빌드가 추천기에서 안 보인다** (2026-07-25 발견). `user_roster.load_nikke_spec`은
      `manifest.get("weapon_source", manifest["source"])`를 존중하는데
      (`user_roster.py:63`) `supported_units._load_meta`는 `manifest["source"]`만 보고
      (`supported_units.py:26`) 죽은 dotgg를 찾다 `FileNotFoundError` → `continue`로
      **조용히 탈락**시킨다. `sugar/flora/rosanna/phantom-signature` 넷 다 해당.
      `_load_meta` 독스트링이 "load_nikke_spec의 해석을 정확히 미러링"이라 주장하는데
      더 이상 사실이 아니다. 조용한 `continue`가 이런 누락을 감추는 것 자체도 재검토 대상.
- [ ] `docs/decisions.md`의 "180s", "tech stack" 항목에 `Consequences:` 필드 보강
      (docs-keeper 지적, 2026-07-25 확인 — 둘 다 여전히 누락)
- [ ] **swap 힐클라임이 정규 순서 하나로만 후보를 채점한다** (2026-07-25 발견).
      `search_best_decks` 독스트링은 그 방식이 실측 **최대 78% 낮게** 나온다고 명시하고,
      `_swap_pass`에 들어오는 덱은 이미 **최적 순서**라 교체 후보만 불리하게 채점된다 —
      오차가 상쇄되지 않고 **후보 쪽으로 편향**된다. 최종 `_best_ordering_summary`가
      순서를 다시 잡으므로 보고 숫자는 정직하지만, **판정은 저평가된 점수 위에서** 끝난다.
      먼저 잴 것: 후보를 전 intra-tier 순서로 채점하면 swap 판정이 몇 % 뒤집히는가
      (시뮬 ~27배 — 배치 병렬화가 끝난 지금에야 감당 가능해진 실험).

### 나중 (Phase 5~7)
- [x] 5덱 25니케 분배 최적화 레이어 (Phase 5에서 착지 — `allocate_decks`의 greedy-peel +
      same-tier swap 힐클라임 + draft/lock, 2026-07-24 캐스케이드로 78유닛 20.2배 가속)
- [x] React 입력 폼 (ShiftyPad 수동 입력)
- [x] FastAPI 백엔드 엔드포인트 (`POST /api/recommend`, 2026-07-16)
- [x] 로스터 영속화 (localStorage, 2026-07-17) — 새로고침에 2,000개 값이 증발하던 문제
- [x] ShiftyPad 연동 자동화 조사 — **종결**: Phase 7이 blablalink sync를 유일한 로스터
      소스로 확정하며 대체됨(`docs/decisions.md`, "로스터 소스를 blablalink sync 하나로 확정").

---

## 백로그 — 지연된 엔진 항목

정확도를 위해 언젠가 다뤄야 하지만 지금은 근사/보류한 것들 (각 모듈에 주석).

- **미연결 stat(나머지):** `sustained_damage_up`, `true_damage_up`, `shield_damage_up`,
  `projectile_explosion_damage_up`, `distributed_damage_up` 등은 공식엔 있으나 아직
  `raid_simulator`가 안 읽음. 필요한 유닛 인코딩 시 해당 버킷만 한 줄로 연결, 가짜 금지.
  (`damage_taken_up`·`other_core_damage_sources`는 연결 완료.)
- **근사 처리:** `pierce_damage_up`는 모든 히트에 적용(실제 관통 히트 게이팅 X),
  스택/에스컬레이션 버프는 정상상태(최댓값) 근사.
- **미구현 메커니즘:** 노멀어택 횟수 트리거, 위치/최고ATK 아군 타겟팅,
  무기 변형, 공격속도 변화.

---

## 이 문서 관리 방법

- 작업이 한 단계 끝나거나 To-Do가 소화되면 여기부터 갱신 (커밋에 포함).
- 큰 결정이 새로 내려지면 → `/document` (docs-keeper)로 `decisions.md`에 기록하고,
  로드맵 단계 상태도 여기서 갱신.
- 테스트 수/인코딩 수는 상단 요약 줄에서 최신값으로 유지.
