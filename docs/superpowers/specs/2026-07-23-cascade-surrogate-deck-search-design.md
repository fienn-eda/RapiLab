# 캐스케이드 대리모델 덱-탐색 가속 설계 (Phase 1: 대리모델 + recall 검증)

**Goal:** 덱 탐색의 지배 비용인 "모든 후보를 사이클-정확 시뮬"을 걷어내기 위한
**캐스케이드**(값싼 근사 필터로 조합 랭킹 → 진짜 `simulate_raid`는 top-K에만)를
도입하되, **먼저 근사 스코어러의 recall을 실측**해 채택 가능성을 데이터로 검증한다.
이 spec은 **Phase 1(표본-회귀 대리모델 + 검증 하네스)** 까지만 다룬다.

**Architecture:** 백엔드(Python) 실험. 대리모델은 **reference-free 표본 회귀** —
무작위 feasible 덱 표본을 실제 시뮬해 `damage ≈ β0 + Σβ_i·x_i + Σβ_ij·x_i·x_j`
(x=유닛 멤버십 지시자)를 ridge로 피팅하고, 이후 모든 조합을 계수 합산으로 랭킹한다.
검증은 hold-out 조합 집합에서 **참 top-K recall + Spearman 순위상관**을 측정하고
사전 정의한 **Go 기준**으로 캐스케이드 착수 여부를 판정한다.

**측정이 답할 질문:** 값싼 대리모델로 조합을 랭킹했을 때 **진짜 최적 조합이
대리모델 top-K 안에 드는가, 그리고 필요한 K는 얼마인가?** Go면 Phase 2(캐스케이드
통합)로, No면 피처/표본/상한(B&B) 재설계로 간다.

---

## 배경 (왜 이 방향인가)

- **프로파일 실측(2026-07-23, `profile_recommend_allocation.py --phase-a-only`,
  78유닛):** zero-base raid ~692초 중 **병렬 시뮬 ~66%**, 부모측 후보 생성 ~23%.
  즉 지배 비용은 "**모든 후보 덱을 시뮬**"하는 것.
- **조사(2026-07-23):** 빠른 경쟁 도구(Genshin Optimizer, NIKKE Synergy 등)는
  탐색에 **닫힌 수식**을 쓰고 시뮬을 안 돌려 "즉시·브라우저·클라측"을 달성. 진짜
  사이클 시뮬(gcsim)은 오프라인/사전연산. 우리 엔진만 후보마다 시뮬 → 이례적.
- **문헌 정석 = 캐스케이드(2-stage ranking):** 값싼 coarse 필터 → top-K에만 정밀
  평가. `docs/decisions.md`(이 결정 기록) 참조.
- **정확도 보존:** 프로젝트는 의도적으로 사이클-정확 시뮬을 택했다(steady-state
  수식은 버프 겹침·버스트 창·CDR 사이클 변화를 오판 — [[prefer-cycle-accurate-escalation]],
  `references/damage-formula-reference.md`). 그래서 근사는 **순위 필터로만** 쓰고
  시뮬을 top-K의 **최종 심판**으로 남긴다 — 근사는 "대충 맞는 순위"만 주면 된다.

---

## Non-goals (Phase 1)

- **캐스케이드 통합 아님.** `search_best_decks`/`allocate_decks`에 배선, K 확정,
  사전연산 캐싱, `recommend_from_draft` 경로 반영은 **검증 통과 시 Phase 2**. K와
  통합 형태는 recall 데이터로 정하므로 지금 spec하지 않는다(무-플레이스홀더 원칙).
- **순서(버스트 오더) 대리모델 아님.** 대리모델은 **조합(멤버십)만** 랭킹한다.
  버스트 순서(누가 버스트/버퍼냐)는 캐스케이드가 top-K 조합에 대해 **진짜 시뮬로**
  탐색한다. 대리모델의 학습 타깃은 조합의 **best-ordering 달성 딜**로 정의한다.
- **워커 캡·브라우저 이식(Pyodide) 아님.** 종착지(클라측 인-브라우저)와 워커 캡은
  별 트랙. 캐스케이드로 연산이 충분히 싸진 뒤 검토.
- **프로덕션 최적 대리모델 튜닝 아님.** Phase 1은 "채택 가능한가"를 답하는
  스파이크다. 아래 기본값은 *초기 인스턴스*이며 recall이 미달이면 피처/표본을 조정한다.

---

## 대리모델 정의 (표본 회귀, reference-free)

**표본 생성**
- 대상: 실 로스터(`load_roster`) + 실 보스. 검증 비용을 위해 **중간 크기(기본 ~40유닛)**.
- feasible 조합을 **무작위 추출**: `ALLOWED_SHAPES` 중 하나를 균등 선택 → 각 tier에서
  필요한 수만큼 무작위 유닛 선택 → `_no_variant_clash`·`_tier1_seating_valid` 통과분만
  채택. 고정 seed로 결정론적.
- **학습 타깃 `y`**: 각 조합의 **best-ordering 딜**
  (`_intra_tier_orderings`로 순서 열거 → `evaluate_deck` 최대). 조합의 *달성 가능*
  값이라 캐스케이드가 top-K에 실제로 뽑아낼 값과 정합. (비용 상한을 위해 표본 수 M을
  조절; 순서 열거는 조합당 한 자릿수.)

**피처 (지시자)**
- `x_i` = 유닛 i 포함 여부(멤버십). 상수항 β0 포함.
- 페어 `x_i·x_j` — **피처 폭발(순수 N²/2)을 막기 위해 초기엔 tier-pair 유형으로 제한**:
  버퍼-어태커 시너지를 담는 B1-B3·B2-B3, 버퍼-버퍼 B1-B2, 어태커간 B3-B3. (해당
  tier 쌍에 속한 모든 유닛 쌍의 곱을 피처로.) recall 미달 시 3-way 등으로 확장.

**피팅**
- **Ridge 회귀**(numpy, `(XᵀX + λI)⁻¹Xᵀy` 또는 `numpy.linalg.lstsq` + 정규화).
  λ는 소량(교차검증 없이 고정 기본값에서 시작). 표본 수 M ≥ 피처 수가 되도록 M·페어
  제한을 맞춘다.
- 산출: 계수 β. 조합 랭킹 = `β0 + Σβ_i·x_i + Σβ_ij·x_i·x_j` (테이블 합산, 시뮬 없음).

---

## 캐스케이드 (Phase 2 개요 — 참고용, 이번 범위 아님)
- 대리모델로 전체 조합 랭킹 → **top-K 조합**만 `simulate_raid`로 순서까지 탐색해
  최종 점수·최적 덱 산출. K는 Phase 1 recall이 정함.
- `allocate_decks`의 greedy-peel 각 단계도 동일 캐스케이드로 후보를 좁힌다.
- 사전연산(표본+피팅)은 **로스터+보스당 1회** 캐시(엔진 결정론적).

---

## 검증 (Phase 1의 핵심 산출)

**하네스** (`scripts/validate_surrogate_recall.py`):
1. 로스터+보스 로드(기본 ~40유닛, `--units`).
2. feasible 조합을 표본 추출해 **fit 집합**과 **hold-out 집합**으로 분리(seed 고정).
3. 두 집합 모두 best-ordering 딜을 시뮬(진짜 값=ground truth).
4. fit 집합으로 ridge 피팅 → 계수 β.
5. **hold-out** 조합을 β로 랭킹하고, 진짜 딜 랭킹과 대조.

**지표**
- **Top-K recall:** hold-out에서 진짜 top-1(및 top-5)이 대리모델 top-K에 드는가,
  K = 10/20/50/100에 대해.
- **Spearman 순위상관**(대리모델 vs 진짜, hold-out 전체).
- 참고: 진짜 top-1의 대리모델 랭크 백분위.

**Go 기준(초기 제안, 실측 후 Fienn과 확정):**
- 진짜 **top-1이 대리모델 top-20** 안 **그리고** 진짜 **top-5가 대리모델 top-K(작은 K)**
  안 → 그 K로 캐스케이드 안전(top-K 시뮬로 진짜 최적 회수).
- Spearman ≳ 0.8 이면 순위 신뢰 가능 신호.
- 미달 시: 페어 피처 확장/3-way, M↑, 또는 무손실 상한(B&B)로 전환.

**비용 통제:** 검증은 중간 로스터+제한된 M으로 수천 시뮬 규모(수 분). `--units`·표본
수 인자로 조절.

---

## 산출물 (Phase 1)
- `backend/app/surrogate.py` (또는 유사): 표본 생성·피처화·ridge 피팅·조합 스코어링
  함수. 엔진 코드(`deck_search`·`deck_allocation`)는 **읽기 전용 참조**(캐스케이드
  배선은 Phase 2).
- `scripts/validate_surrogate_recall.py`: 위 검증 하네스(이름·문서·`--units`/`--samples`
  인자, Go 지표 표 출력).
- 측정 결과 요약 → `docs/roadmap.md`(Phase 5 perf) + 필요 시 `docs/decisions.md`.

## 테스트 (Phase 1)
- 대리모델 단위 테스트: 표본 추출이 feasible 조합만 내는지, 피처화가 멤버십/페어를
  올바로 인코딩하는지, ridge 피팅이 알려진 소형 입력에서 기대 계수를 내는지(결정론적
  소형 케이스), 조합 스코어링이 피처·계수 합과 일치하는지.
- 검증 하네스는 **측정 도구**(재현성 위해 seed 고정)이며, 통과/실패는 recall 결과가
  아니라 하네스가 지표를 정확히 계산하는지로 테스트한다.
- 백엔드 시뮬 엔진 무변경 → 기존 스위트 회귀 없음 확인.
