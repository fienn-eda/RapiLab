# Laplace: Ultimate Hero 인코딩 보완 (+ 지원 엔진 작업)

- 날짜: 2026-07-24
- 브랜치: `wip/skill-encoding`
- 상태: 설계 승인 대기

## 배경 / 목표

`laplace-ultimate-hero`(Burst-3 Wind RL 어태커, MISSILIS)는 현재 **thin
stub**이다 — 버스트 넉(2953.84%)과 자기버프 몇 개만 모델링돼 있고, 핵심 DPS인
**차지-카운트 기반 무기변형 루프**가 통째로 deferred(engine-gap #13)라 덱 탐색이
그녀를 저평가한다.

Fienn 인게임 실측(2026-07-24)으로 이 루프를 red-hood식 **앵커 기반 모델**로 접을
수 있게 됐다. 실측 검토 과정에서 두 가지 부수 작업이 파생됐다: 전 유닛에 영향을
주는 **버스트 사이클 타이밍 검증/문서화**(point 0)와, 다수 소비자가 기다리는
**라이브 Max HP 스탯**(point 4).

이 스펙은 그 셋을 3단계로 나눠 순차 진행한다: **A(감사·문서화) → B(Max HP
엔진 확장) → C(Laplace 변신 루프)**. C는 B에 의존한다.

### 핵심 제약: 엔진을 무겁게 하지 않는다

덱 최적화 시뮬레이션이 이미 무겁다(Fienn). 따라서 gap #13용 **일반 차지-카운트
트리거 프리미티브는 만들지 않는다**(발사 추적을 시뮬 핫패스에 얹게 됨). 대신
**이미 존재하는 opt-in weapon-mode 세그먼트 경로**(`attack_rate.
generate_segmented_shots` + `simulate_raid(..., weapon_mode_schedules=)`)를
재사용한다 — red-hood가 이미 이 경로로 마이그레이션했고, 빈 세그먼트면 기존 출력과
비트 동일이라 다른 덱 평가 비용에 영향이 없다.

## 실측 데이터 (Fienn, 2026-07-24)

측정 전제: 오버로드 옵션 없음, 무기변형 시 최대 장탄 **120발** 환경([최대 장탄 수
증가] 효과 없음). 육성 상태에 따라 최대 장탄이 달라질 수 있음.

### Skill 1 (Warm Up / 무기변형)
- Warm Up 5회 차지 소요: 각 **1.0, 0.9, 0.8, 0.7, 0.6초**(합 4.0초, 스킬설명 일치).
  발사 사이 딜레이 없음, **4초 후 무기 변경**.
- 변형 무기 `[Electric Power, Full Full Charge]`: 변경 즉시 최대 탄창. **SMG fire
  rate(20/sec)**. 유지시간은 [최대 장탄 수 증가]에 직접 영향받음(탄창 다 비우면 종료).
- SMG 모드에서 120발 전부 소모 → 재장전 → 기존 RL 모드 복귀.
- **SMG 데미지에 차지대미지 미적용**(9.45%/샷이 곧 per-shot 최종 배수).

### Skill 2 (Over Energy)
- 오버 에너지 단계는 스킬설명대로: **변신 2회마다 단계 +1**(120발×2 = 240 노멀 =
  Over Energy 100% = 1단계). 단계 최대 4(Max HP +2/+3/+7/+10.5%).
- `[버스트 3단계 진입 시]` = 'B2 스킬 발동 이후, B3 스킬 발동 이전' 상태 →
  결론적으로 skill의 공격대미지 **52.14%가 B3 버스트딜에 적용됨**(Phase A에서 검증).

### 변신 주기
- 120발 기준 **약 12.5초마다 변신**. 단 주기는 [최대 장탄] 오버로드에 따라 변하므로
  **고정 금지 — 라이브 max ammo에서 유도**한다(Phase C).

## 확인된 엔진 사실 (사전 조사)

- `effects.py:238` — 버프 active-window는 **시작 시각 포함**(`applied_at <= now <
  applied_at + duration`).
- `burst_cycle.py` — 한 사이클에서 `on_tier_fire`가 tier 1→2→3 순서로 호출되고
  (auto gap 0, manual gap 0.1), `on_full_burst_enter(tier3_fire_time)`이 그 뒤에
  호출된다. **`full_burst_enter` 시각 == B3 발동 시각 == B3 버스트 넉 시각.**
- `raid_simulator.py` — `on_tier_fire`(line 585)에서 `own_burst_activate` 룰이
  먼저 발동되고, 그 다음 버스트 넉이 기록된다(line 632). record-then-compute라
  넉 데미지는 2단계에서 넉 시각의 라이브 버프를 읽어 계산한다.
- Max HP: `flat_max_hp` Effect 스탯은 존재하나(Rouge가 미리 등록) **딜에서 소비하는
  경로가 없다**. caster-Max-HP 스케일 ATK 버프는 전부 정적 `caster_max_hp`(고정
  캐릭터정보값)를 쓴다. 소비자: `laplace_ultimate_hero`, `maxwell_ordinary_mechanic`,
  `cinderella`, `maiden_ice_rose`, `rouge`, `crown`.

---

## Phase A — 버스트 사이클 타이밍 감사 + 문서화

**목적:** `게이지 충전 → B1진입 → B1사용 → B2진입 → B2사용 → B3진입 → B3사용 →
풀버스트 10초` 구조가 엔진에서 올바르게 동작하는지 실증 검증하고, 버프 트리거가
버스트 넉에 대해 어떻게 착지하는지 문서화한다. 전 유닛에 영향.

**작업:**
1. **실증 테스트** — 실제 `simulate_raid`로 B3 유닛의 `full_burst_enter` 버프가
   자기 버스트 넉에 곱해지는지, `own_burst_activate` 버프도 그런지 확인하는 회귀
   테스트를 추가한다(합성 미니 덱). auto·manual 두 모드.
2. **문서화** (`docs/insights.md`, 엔진 gotcha):
   - 엔진엔 "버스트 단계 진입"과 "BN 사용"이 **별도 이벤트가 아니다** —
     `on_tier_fire`가 곧 "BN 사용"이고, 스킬텍스트의 `[버스트 N단계 진입 시]`는
     해당 tier 유닛의 `own_burst_activate`로 매핑된다.
   - `full_burst_enter` 시각 == tier3 발동 시각. 시작 포함 window라 그 버프는
     **동시각 B3 넉에 적용**된다.
   - **수동모드 미묘점:** `full_burst_enter` 버프는 B1/B2 유닛의 *자기* 버스트
     넉에는 미적용(그 넉은 0.1~0.2초 먼저 발동). auto모드는 전 tier 동시각이라 적용.
     → B1/B2 자기 버스트딜에 걸려야 하는 버프는 `own_burst_activate`를 써야 한다.
3. **Laplace 트리거 수정** — Over Energy 52.14% 공격대미지를
   `full_burst_enter` → `own_burst_activate`로 변경. 숫자는 동일하나(동시각) **자기
   버스트 게이팅이 정확**해진다(다른 B3가 대신 버스트한 사이클엔 미지급이 옳음).
   기존 테스트의 트리거 이름도 갱신.
4. **스윕** — 다른 인코딩 유닛 중 `[버스트 N단계 진입 시]`를 `full_burst_enter`로
   건 것이 자기 버스트딜에 곱해져야 하는 케이스가 있는지 확인(있으면 별도 보고,
   이번 스코프에선 Laplace만 수정하고 나머지는 목록화).

**위험:** 낮음. 대부분 문서화 + Laplace 1건 트리거 변경(숫자 불변).

**완료 기준:** 신규 타이밍 테스트 그린, `docs/insights.md` 갱신, Laplace 테스트
그린, 전체 스위트 그린.

---

## Phase B — 라이브 Max HP 스탯 (엔진 확장)

**목적:** "ATK ▲ Max HP의 X%" 버프가 적용 시점의 **라이브 Max HP**(base_stats
max_hp + `flat_max_hp` 버프)를 읽게 한다. 다수 소비자가 대기 중이며(point 4),
Over Energy 단계의 Max HP 부여가 Laplace ATK에 환류되게 하려면 Phase C의 선행조건.

**설계 방향(구현 시 확정):**
- caster-Max-HP 스케일 ATK 버프를 **빌드 시점 정적 계산에서 적용 시점 동적 계산으로
  전환**한다. 두 후보:
  - (B1) 버프 적용 액션이 그 시점 `registry.total_for("flat_max_hp", caster, now)`을
    더한 라이브 Max HP로 flat_atk를 계산해 등록. per-unit, 국소적.
  - (B2) 신규 파생 스탯 훅 — `flat_atk_percent_of_live_max_hp` 같은 스펙을
    raid_simulator가 2단계에서 해석(`extra_flat_atk_percent_of_max_hp` 선례,
    단 라이브 Max HP 사용). 재사용성 높음.
  - **추천: B2 계열** — 이미 `extra_flat_atk_percent_of_max_hp`(정적 Max HP)
    배선이 있으니, 그 해석을 라이브 Max HP로 확장하거나 라이브 변형 필드를 추가하는
    최소 변경으로 소비자 전체를 한 경로로 통일. 구현 착수 시 기존 배선을 읽고 확정.
- **크로스유닛 딜 영향**: Max HP 스케일 유닛 전부의 숫자가 바뀔 수 있다("엔진을
  조용히 바꾸지 않는다" 케이스지만 Fienn 승인됨). engine-test-runner로 회귀
  스냅샷을 잡고, 변화가 의도된 방향(라이브 Max HP 반영)인지 검증한다.

**소비자 마이그레이션:** `laplace_ultimate_hero`, `maxwell_ordinary_mechanic`,
`cinderella`, `maiden_ice_rose`, `rouge`, `crown` — 정적 `caster_max_hp` 경로에서
라이브 경로로. 각 유닛의 기존 테스트가 정적값을 하드코딩하고 있으면 라이브 계산에
맞게 갱신(픽스처가 아니라 기대값 재계산).

**Max HP 부여 버프 배선:**
- Maxwell Sequential Limit Release: Max HP +1%/풀차지, 캡 30(squad) — 트리거가
  풀차지 카운트(미지원)라 **정착 캡 30스택(+30%)** 근사로 `flat_max_hp` 부여
  (settle 가정 문서화). 이로써 Maxwell의 Output Switching "squad ATK = Max HP의 1%"가
  버프된 Max HP를 반영.
- Laplace Over Energy 단계 Max HP: Phase C에서 escalating 부여(아래).

**위험:** 중간(크로스유닛). 회귀 테스트 필수.

**완료 기준:** 라이브 Max HP 소비 경로 + 테스트, 소비자 마이그레이션 그린,
engine-test-runner 회귀 검토 완료, 전체 스위트 그린.

---

## Phase C — Laplace 변신 루프 (weapon-mode 세그먼트)

**목적:** 핵심 DPS인 변신 루프를 세그먼트 앵커로 모델링한다.

**데이터 선행:** `data/shiftypad/laplace-ultimate-hero.json`이 gitignore로 부재 →
`tools/collect-blablalink`에서 `collect.js --nikke 103 --headless` 후
`normalize_shiftypad_raw.py 103:laplace-ultimate-hero`로 재수집(무기 스탯 —
RL 재장전·차지·기본 배수 확보).

**모델링:**
1. **변신 창 = weapon-mode 세그먼트.** 각 변신 시각에서 시작, 기본 RL 침묵,
   프로필: `weapon="SMG"`(또는 상응), `rate_of_fire=20`, `damage_percent=9.45`,
   **charge_damage_percent 없음**, `until_shots = 라이브 SMG max ammo`.
2. **라이브 max ammo 유도.** 변형 SMG 기본 120발 × 유닛의 [최대 장탄] 배율. 세그먼트
   스케줄 함수(`schedule(context, fight_duration)`)가 라이브 max ammo에 접근할 수
   있는지 확인하고, 없으면 최소 플러밍 추가(context에 유닛 max-ammo 배율 노출).
   **하드코딩 금지.**
3. **변신 주기 유도.** 주기 `P = 빌드시간 + SMG창 + 재장전`:
   - 빌드시간: 실측 4.0초(Warm Up 5차지). 오버로드 없음 전제의 앵커.
   - SMG창: `라이브 max ammo / 20`초.
   - 재장전: 재수집한 RL 무기 스탯의 reload_time.
   - 120발 기준 P ≈ 12.5초와 대조 검증(4.0 + 6.0 + reload ≈ 12.5 → reload ≈ 2.5s
     범위면 정합). 어긋나면 빌드/재장전 앵커를 실측과 재대조.
   - 변신 시각 `tₙ = 4.0 + (n-1)·P`, `tₙ < fight_duration`까지.
4. **Over Energy 단계 → Mjolnir 추가딜.** 단계 = `min(4, floor(그 시각까지 변신
   횟수 / 2))`. Mjolnir 버스트마다 `934.76% × 버스트시점 단계`를 **추가 히트**로
   기록(시점별 정확 단계 — 변신·버스트 시각 모두 결정론적). 버스트 시각은
   `context.burst_times["laplace-ultimate-hero"]`.
5. **Over Energy 단계 Max HP 부여.** 각 단계 진입 시각에 해당 Max HP %를
   `flat_max_hp`로 self 부여(Phase B 경로로 Electric Power ATK에 환류). 단계값
   2/3/7/10.5%는 누적이 아니라 단계별 대체인지 누적인지 스킬설명 대조 후 확정
   (기본 가정: 단계 도달 시 해당 값, 이전 단계 대체 — 구현 시 확인).

**계속 deferred(문서화):**
- Warm Up 차지속도 버프 자체(소모형, 상시 유지 안 됨) — 세그먼트 케이던스 실측에
  이미 반영됨.
- Over Energy의 노멀공격 카운트 트리거 세부(12회) — 세그먼트 2회 = 1단계 앵커로
  대체 표현.

**위험:** 중간. 세그먼트 케이던스가 실측 앵커에 맞는지 E2E 대조 필요.

**완료 기준:** 변신 세그먼트 + 단계 추가딜 + Max HP 환류 테스트, E2E 총딜이 실측
케이던스와 정합, docstring의 modeled/deferred 목록 갱신, 전체 스위트 그린.

---

## 테스트 전략

- **Phase A:** 합성 덱 타이밍 회귀 테스트(auto/manual, full_burst_enter vs
  own_burst_activate가 B3/B1 넉에 착지하는지). Laplace 기존 테스트 트리거 갱신.
- **Phase B:** 라이브 Max HP 소비 유닛 테스트(Max HP 버프가 ATK를 실제로 움직이는지),
  engine-test-runner 크로스유닛 회귀 스냅샷.
- **Phase C:** 세그먼트 발수·데미지타입·주기 유도 단위 테스트, 단계별 추가딜
  정확값 테스트, E2E 케이던스 대조.
- 각 단계 종료 시 `PYTHONIOENCODING=utf-8 python -m pytest tests/ -q` 그린 확인 후
  커밋.

## 비목표 (YAGNI)

- 일반 차지-카운트 트리거 프리미티브(엔진 부하). 세그먼트 재사용으로 대체.
- Pierce/관통 범위, 버스트게이지 fill(딜 무관·inert).
- Maxwell 자기 무기변형(서포터 자기딜 미미, deferred 유지).

## 열린 항목

- 변형 SMG의 무기종 표기(`SMG` 프로필이 세그먼트 생성기에서 유효한지) — Phase C
  착수 시 `generate_segmented_shots` 계약 확인.
- Over Energy 단계 Max HP가 누적/대체인지 — 스킬설명 원문 대조.
- Phase B 라이브 Max HP 배선 후보(B1 vs B2) 최종 선택 — 기존
  `extra_flat_atk_percent_of_max_hp` 코드 확인 후 확정.
