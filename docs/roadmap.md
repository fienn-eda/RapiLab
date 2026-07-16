# NIKKE Deck Builder — 로드맵 & 진행 현황

우리가 뭘 만들고 있고, 어디까지 왔고, 다음에 뭘 할지 한눈에 보는 문서.
큰 그림은 **로드맵(단계)**, 작은 단위 작업은 **To-Do**에서 관리한다.
결정의 배경은 `docs/decisions.md`, 엔진 함정/패턴은 `docs/insights.md`,
인코딩된 니케 목록(Burst 단계별)은 `docs/encoded-nikkes.md`,
엔진 갭 인벤토리(확장 우선순위)는 `docs/engine-gaps.md`,
스킬 인코딩 방법은 `nikke-skill-encoding` 스킬 참고.

- 마지막 갱신: 2026-07-16
- 브랜치: `wip/scaffolding`
- 테스트: **524 passed** (2026-07-16, **Phase B gap #5 완료** — `boss_is_element` 조건 +
  `enemy_def_percent` 배선; Brid/Helm Electric·Wind 디버프 + Marciana 신규 + 상호작용/
  회귀 테스트; was 511)
- 인코딩된 니케: **55명** (Marciana: Marine Study[gap #5, 신규] +1;
  Brid: Silent Track ⚠→✅, Helm: Aquamarine ⚠→✅) — 상세는 [`docs/encoded-nikkes.md`](encoded-nikkes.md)
- **Phase B gap #5 완료 (2026-07-16):** `SquadContext.boss_element` +
  `boss_is_element(element)` 조건 헬퍼(+`buff_rule`/`refreshing_buff_rule`/
  `instant_nuke_pulse_rule`에 옵셔널 condition) + `enemy_def_percent` 배선(DEF▼ 디버프,
  기존 inert). 소비: **Brid**(Wind Damage Taken 디버프 → ✅) · **Helm: Aquamarine**
  (Electric Damage Taken 정상상태 + Overload 추가딜, Burst2라 FB보너스 미적용 → ✅) ·
  **Marciana: Marine Study**(신규 Iron AR B3; Fienn 가정 rapture=1/Flagged=보스/
  High-Risk=Electric 게이팅; Whistle 자ATK·Elemental Advantage AD·DEF 디버프·Flagged
  3789% 풀버스트 넉·High-Risk 20노멀 넉). **Phase S 완료(이전):** attack/charge speed 배선
  + Dorothy: Serendipity. **다음:** Phase B 잔여(#8 자원-fill-트리거 타 유닛 버프[Maiden])
  또는 Phase C(#3 arcana 대형, #6 ada, little-mermaid).

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
| Phase 3 | 캐릭터 스킬 인코딩 | 🔄 진행 중 (55명) |
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
- **다음:** **eb3+ 백로그**(Pattern B 게이지·상태머신·무기변형) + **막힌
  나머지 per-shot 유닛 재인코딩 배치** + Phase B 잔여(gap #8)/Phase C가 최대 실질 가치.
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
- [ ] **eb3+ 백로그** — 대부분 **자원 유닛(gap #2 Pattern A 잔여/Pattern B)·상태머신·
      무기변형**. 배치 착수 전 유닛별 검증 필수.
  - **Pattern A 자원 유닛 (named-resource로 인코딩 가능, 잔여)**: `rei-ayanami`·
    `rei-ayanami-tentative-name`(Anti A.T.), `neon-vision-eye`.
  - **Pattern B 게이지·변신 (잔여, gap #2)**: `ark-ranger-black`(배터리 시간감쇠·부위파괴
    fill)·`mihara-bonding-chain`(체인)·`elegg-boom-and-shock`·`red-hood`(charge speed·딜 아님).
  - **상태머신/특수 트리거**: `diesel-winter-sweets`(Intro/Highlight+지속딜),
    `bready`(Taste), `dorothy-serendipity`(펠릿 카운터), `eve`(크리티컬-히트 카운터 —
    Julia 시그니처 인코딩 중 확인됨: 기대값 크리 모델과 구조적으로 불가, **영구 defer**
    가능성 높음, 착수 전 재확인),
    `ada-wong`(풀버스트창 주기딜=gap #6 + True), `marciana-marine-study`(boss-element=gap #5),
    `milk-blooming-bunny`·`scarlet-black-shadow`(distributed)
  - **무기 변형**(버스트/평타가 다른 무기모드로 전환 = 핵심 딜, 미지원): `snow-white`,
    `snow-white-heavy-arms`, `maxwell`, `cinderella-crystal-wave`(MG/Snipe 모드
    전환이 FB 넉을 게이팅 — 자원 primitive로 안 풀림, 2026-07-12 eb4 검증 중 재분류)
  - ✱ = 애장품(dollskills) 보유, base/시그니처 별도 slug로 인코딩(Julia로 확정된 패턴):
    `drake`, `laplace` (julia는 완료: `julia` + `julia-signature`)
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
