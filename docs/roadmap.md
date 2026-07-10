# NIKKE Deck Builder — 로드맵 & 진행 현황

우리가 뭘 만들고 있고, 어디까지 왔고, 다음에 뭘 할지 한눈에 보는 문서.
큰 그림은 **로드맵(단계)**, 작은 단위 작업은 **To-Do**에서 관리한다.
결정의 배경은 `docs/decisions.md`, 엔진 함정/패턴은 `docs/insights.md`,
인코딩된 니케 목록(Burst 단계별)은 `docs/encoded-nikkes.md`,
엔진 갭 인벤토리(확장 우선순위)는 `docs/engine-gaps.md`,
스킬 인코딩 방법은 `nikke-skill-encoding` 스킬 참고.

- 마지막 갱신: 2026-07-10
- 브랜치: `wip/scaffolding`
- 테스트: **264 passed** (마지막 전체 실행 기준)
- 인코딩된 니케: **31명** — 상세는 [`docs/encoded-nikkes.md`](encoded-nikkes.md)

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
| Phase 3 | 캐릭터 스킬 인코딩 | 🔄 진행 중 (28명) |
| Phase 4 | 단일 최적 덱 추천 | ✅ 완료 |
| Phase 5 | 5덱(25니케) 분배 최적화 | ⬜ 예정 |
| Phase 6 | 유저 데이터 입력 UI (React) | ⬜ 예정 |
| Phase 7 | 자동화 (ShiftyPad 연동, 수집 파이프라인) | ⬜ 지연/후속 |

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
- **인코딩 완료:** Rosanna: Chic Ocean, Takina Inoue, Brid: Journey Ahead 승급,
  Mint(Here I Go!), Prika(Encore + 풀차지 버프).
- **다음:** **막힌 ~30명 재인코딩 배치**(데이터 수집→per-shot 룰 추가)가 최대 실질 가치.
  남은 gap은 `engine-gaps.md` 우선순위 참고.

### Phase 4 — 단일 최적 덱 추천 ✅
- `deck_search.py` — `BossProfile`, feasible_orderings, evaluate_deck, find_best_decks.
- 덱 좌우 순서 = 버스트 역할 배정 → 같은 5인이라도 순서에 따라 딜 33% 차이 확인.

### Phase 5 — 5덱 분배 최적화 ⬜
- 25명(5덱×5)을 골라 총합 딜을 최대화하는 조합 레이어. 단일 덱 평가기를 빌딩블록으로 사용.

### Phase 6 — 유저 데이터 입력 UI ⬜
- React 폼으로 ShiftyPad 투자 데이터 수동 입력 (돌파/스킬레벨/오버로드/큐브).
- FastAPI 엔드포인트로 엔진 노출.

### Phase 7 — 자동화 ⬜ (후속)
- ShiftyPad 로그인 세션 스크래핑 / API 리버싱, dotgg 자동 수집 파이프라인.

---

## To-Do (작은 단위)

로드맵보다 잘게 쪼갠 실행 항목. 끝나면 `[x]`로 체크.

### 지금/다음
- [ ] 2·3버스트 니케 인코딩 (딜러 중심으로 후보 선정)
- [x] `damage_taken_up` / `other_core_damage_sources` 엔진 연결
      — 완료. squad 스코프 적 디버프, 코어 데미지는 `core_hittable` 게이팅.
- [ ] `NikkeSpec`에 스킬별 유저 레벨 필드 추가 → 조립 시 `levels[level-1]` 선택 일반화
      (지금은 빌더가 단일 레벨 dict만 받음)

### 정리/보강
- [ ] `docs/decisions.md`의 "180s", "tech stack" 항목에 `Consequences:` 필드 보강
      (docs-keeper 지적)

### 나중 (Phase 5~7)
- [ ] 5덱 25니케 분배 최적화 레이어
- [ ] React 입력 폼 (ShiftyPad 수동 입력)
- [ ] FastAPI 백엔드 엔드포인트
- [ ] ShiftyPad 연동 자동화 조사

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
