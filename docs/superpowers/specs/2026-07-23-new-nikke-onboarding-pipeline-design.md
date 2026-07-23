# 신규 니케 온보딩 파이프라인 — 감지에서 추천 노출까지 하나의 흐름

신규 니케 출시 시 **감지 → 데이터 수집 → 인코딩 → 덱 추천 후보 등록**까지의 전 과정을
단일 명령 `/onboard-new-nikkes`로 묶는다. 감지는 이미
[`2026-07-21-new-nikke-release-detection-design.md`](2026-07-21-new-nikke-release-detection-design.md)로
자동화됐고, 그 뒤 "사람이 하는 일"(수집·인코딩·문서·머지)이 매번 손으로 반복되는 것을
오케스트레이션 스킬 하나로 잇는다.

## 핵심 제약 — 인코딩은 완전 자동화 불가

효과별 model/approximate/defer 판단은 게임 지식과 맥락이 필요하고, 틀리면 가짜/틀린
인코딩이 조용히 들어간다(엔진 갭 오분류 전례: `docs/engine-gaps.md`의 Elegg·Mihara·Milk).
따라서 이 파이프라인은 **순수 스크립트가 아니라, Claude 에이전트가 인코딩을 수행하고
Fienn이 한 지점에서 승인하는 오케스트레이션**이다. 무인 에이전트는 승인을 위해 대화형으로
멈춰 기다릴 수 없으므로, 흐름은 승인 게이트에서 **국면 1 / 국면 2**로 자연히 갈린다.

## 설계 결정 (2026-07-23, Fienn 승인)

| 결정 | 선택 | 근거 |
|---|---|---|
| 인코딩 자동화 수준 | 수집·플랜 자동 → **승인** → 자동 마무리 | 판단만 사람, 나머지 전부 자동 |
| 국면 1 시작 방식 | **단일 명령** `/onboard-new-nikkes` (토스트=리마인더) | 가장 단순·견고, 승인 게이트 현실과 일치. 무인 헤드리스 구동/클라우드 루틴은 2~3주 주기 대비 과설계 |
| 최종 게이트 | **플랜 승인 = 최종 승인**, 머지까지 자동 | 유일한 사람 개입은 플랜 승인 하나 |

## 형태

새 스킬 `.claude/skills/onboard-new-nikkes/SKILL.md` 하나가 오케스트레이터다. 기존 조각을
**순서대로 구동**할 뿐 인코딩 로직을 복제하지 않는다. 매일 19:00 감지 토스트는
"`/onboard-new-nikkes` 실행" 리마인더로 문구만 한 줄 갱신한다.

```
감지(기존 daily 토스트) ──리마인더──▶ Fienn: /onboard-new-nikkes 실행
                                          │
          ┌───────────────── 국면 1 (자동) ─────────────────┐
          │ 신규 식별 → 데이터 수집 → 효과 분류 → 인코딩 플랜 초안 │
          └──────────────────────┬──────────────────────────┘
                                 ▼
                        ◆ 게이트: Fienn 플랜 승인/수정 (유일한 개입)
                                 │
          ┌───────────────── 국면 2 (자동) ─────────────────┐
          │ 구현 → 테스트(pristine) → 문서 → 스냅샷 커밋 → FF 머지 │
          └──────────────────────┬──────────────────────────┘
                                 ▼
                    덱서치가 즉시 후보 포함 (추천 노출) · 토스트 정지
```

## 국면 1 — 자동 (감지 → 수집 → 플랜 초안)

1. **신규 식별.** `scripts/check_new_nikkes.py --dry-run`을 **라이브로 실행**해 최신
   디렉토리를 받아 신규 SSR을 식별한다(`--dry-run`이라 토스트는 다시 띄우지 않음; 명령 실행
   시점을 기준으로 항상 최신 — 마지막 daily 캐시에 의존하지 않는다). 이 단계는 읽기전용이라
   워크트리가 필요 없으니 격리보다 먼저 수행해 신규가 없으면 셋업 전에 즉시 종료("신규 없음",
   무행동).
2. **워크트리 격리.** 전용 워크트리/브랜치에서 진행하고 `scripts/sync_worktree_data.py`를
   선행한다(`data/`가 gitignore라 동기화 전엔 비어 있음).
3. **디렉토리 스냅샷 갱신.** `cd tools/collect-blablalink && node collect.js --directory
   --headless --deep`로 커밋되는 `nikke-directory.json`을 갱신(신규 유닛의 resource_id가
   맵 가드 검증에 필요).
4. **유닛별 데이터 수집.** 감지된 각 유닛에 대해:
   - **비-시그니처(기본):** `node collect.js --nikke <rid> --headless`(공개 데이터,
     로그인 불필요, playwright-core 내장) → `python scripts/normalize_shiftypad_raw.py
     <rid>:<slug>` → `data/shiftypad/<slug>.json` (무기 스탯 + 스킬 베이스 값,
     manifest `source: "shiftypad"`).
   - **효과 서술 + 초상화:** lootandwaifus 캐릭터 페이지를 curl(브라우저 UA)로 fetch.
     ShiftyPad 값 슬롯이 뜻하는 바를 읽는 서술 텍스트와 초상화 경로가 여기서 온다.
     페이지가 아직 없으면 초상화는 칩 폴백으로 두고 기록한다.
5. **분류 + 플랜 초안.** `nikke-skill-encoding` 스킬 3~4단계로 효과를 분류하고, **감지된
   전 유닛을 한 배치의 인코딩 플랜**으로 작성한다. 각 유닛에 대해:
   - 스킬별 효과의 model/approximate/defer/skip 요약.
   - 판단 필요 항목(추천 해석 + 근거 + 인코딩 방법).
   - **시그니처 무기 보유 유닛**이면 "어느 빌드(`skills` vs `dollskills`)?"를 플랜에 포함.
   - **얇은 스텁**이 될 유닛이면 그 사실과 무엇이 보류되는지 명시.
6. **플랜 제시 후 대기.**

## 게이트 — 사람 (유일한 개입)

Fienn이 배치 플랜을 승인/수정한다. 이것이 **최종 승인**이며, 이후 머지까지 위임된다.
(엔진 확장이 필요한 얇은 스텁도 이 자리에서 "스텁으로 진행" 승인을 받는다 — 데이터-우선
전략대로 갭은 `engine-gaps.md`에 등록만 하고 나중에 별도 처리.)

## 국면 2 — 자동 (구현 → 검증 → 머지)

승인된 각 유닛에 대해 `nikke-skill-encoding` 스킬 5~12단계를 그대로 수행한다:
- 모듈 `backend/app/skill_rules/<slug>.py` + 테스트 + registry `_BUILDERS` 엔트리
- `frontend/src/lib/resourceIdSlugMap.ts` resource_id 행 (가드가 강제)
- `SKILL_VALUE_MANIFESTS`(`source: "shiftypad"`) + 조립 하네스 통과
- 초상화 `python scripts/download_portraits.py`(신규 슬러그가 `-nikke` 접미사면
  `SLUG_ALIASES` 한 줄 추가)
- 모듈 docstring의 Modeled / Not modeled 목록
- 문서 갱신: `docs/encoded-nikkes.md`(행 + Burst 카운트 + 갱신 노트); 얇은 스텁이면
  `docs/engine-gaps.md`에 갭 등록
- 갱신된 디렉토리 스냅샷 커밋
- **전체 스위트 실행(`pytest tests/ -q`, `PYTHONIOENCODING=utf-8`) — 반드시 pristine.**
- 통과 시 메인 클린 확인 후 `wip/scaffolding`에 **fast-forward 머지**(`git -C <메인>`,
  cwd는 워크트리 유지) → 갱신된 스냅샷이 메인에 반영돼 **감지 토스트 정지**. registry
  등록 즉시 `deck_search`가 후보로 포함(추천 노출 완료).

## 실패 · 엣지 처리 (기본값)

- **수집 실패(collect.js/네트워크/정규화):** 국면 1에서 중단·보고, 부분 상태를 커밋하지
  않는다.
- **lootandwaifus 페이지 부재:** 초상화만 칩 폴백으로 두고, 인코딩은 ShiftyPad 값으로
  진행(효과 의미는 ShiftyPad 슬롯 + dotgg 형태 서술로 최대한 해석, 불명확하면 플랜의
  판단 항목으로 올려 승인 때 확인).
- **국면 2 테스트 실패 / 머지 충돌:** 중단, 브랜치 보존, 수동 처리하도록 보고.
  **실패 상태로는 절대 머지하지 않는다.**
- **여러 유닛 동시 출시:** 한 번의 플랜 · 한 번의 승인으로 배치 처리(2026-07-23의 Maxwell +
  Laplace 2명 온보딩과 동일).
- **재실행 멱등:** 이미 인코딩된 슬러그(registry `ENCODED_SLUGS`)는 자동 skip — 감지가
  "디렉토리에 있으나 미인코딩"만 신규로 보므로 재실행해도 중복 온보딩이 없다.

## 재사용 vs 신규

**재사용(수정 없음):**
- `scripts/check_new_nikkes.py` — 신규 식별
- `tools/collect-blablalink/collect.js` — 디렉토리 갱신 + `--nikke` 수집
- `scripts/normalize_shiftypad_raw.py` — raw → dotgg 형태 정규화
- `scripts/download_portraits.py` — 초상화 + manifest
- `nikke-skill-encoding` 스킬 — 분류·플랜·구현의 권위 절차 (국면 1의 3~4단계, 국면 2의
  5~12단계를 그대로 호출)

**신규:**
- `.claude/skills/onboard-new-nikkes/SKILL.md` — 위 조각을 국면 1/게이트/국면 2로 잇는
  오케스트레이션 절차. 인코딩 방법론은 담지 않고 `nikke-skill-encoding`으로 위임한다
  (경계: 이 스킬은 "무엇을 언제 어떤 순서로"만, 인코딩 "어떻게"는 기존 스킬).
- 토스트 문구 한 줄 갱신(`scripts/notify_toast.ps1` 호출부 또는 `check_new_nikkes.py`의
  온보딩 안내) — "`/onboard-new-nikkes` 실행"을 명시.

## 컴포넌트 경계 (한 가지 목적씩)

| 컴포넌트 | 하는 일 | 의존 |
|---|---|---|
| `onboard-new-nikkes` 스킬 | 순서·게이트·실패 정책만 (오케스트레이션) | 아래 전부 |
| `check_new_nikkes.py` | 신규 SSR 식별 | 디렉토리 스냅샷 |
| `collect.js --nikke` | ShiftyPad raw 번들 수집 | playwright-core(내장) |
| `normalize_shiftypad_raw.py` | raw → dotgg 형태 | `shiftypad_normalize.py` |
| lootandwaifus fetch | 효과 서술 + 초상화 경로 | curl + 브라우저 UA |
| `nikke-skill-encoding` 스킬 | 효과 분류·플랜·모듈/테스트/registry 구현 | 엔진 capability 카탈로그 |
| `download_portraits.py` | 초상화 다운로드 + manifest | lootandwaifus HTML |

각 조각은 독립적으로 실행·검증 가능하며, 오케스트레이터는 이들을 순서와 게이트로만 묶는다.

## 범위 밖 (YAGNI)

- **완전 무인 구동 / 클라우드 루틴** — 승인 게이트가 어차피 사람을 요구하고 출시가 2~3주
  주기라, 헤드리스 Claude 자동 기동이나 스케줄 클라우드 에이전트는 인프라 대비 이득이
  작다. 단일 명령으로 충분.
- **시그니처(dollskills) 자동 판별** — ShiftyPad가 dollskills를 노출하지 않으므로 시그니처
  빌드는 기존 lootandwaifus/dotgg + 무기 스텁 경로. 파이프라인은 플랜에서 "어느 빌드?"를
  물을 뿐 자동 결정하지 않는다.
- **엔진 확장 자동화** — 얇은 스텁이 필요로 하는 엔진 갭(예: 차지-카운트 무기변환 #13)은
  등록만 하고 별도 처리. 파이프라인이 엔진을 확장하지 않는다.

## 테스트

- 오케스트레이터 스킬은 절차 문서(마크다운)라 단위 테스트 대상이 아니다. 검증은 그것이
  구동하는 기존 스크립트/스킬의 자체 테스트로 커버된다:
  - `check_new_nikkes.py` — 기존 감지 테스트(detection 스펙 참고).
  - `normalize_shiftypad_raw.py` — `test_shiftypad_normalize.py` / `test_shiftypad_parity.py`.
  - 인코딩 산출물 — 유닛별 `test_skill_rules_<slug>.py` + `test_skill_value_assembly.py`
    + resource_id 가드(`nikke-skill-encoding` 스킬이 강제).
- 국면 2의 "전체 스위트 pristine" 게이트가 회귀 방어의 최종 관문이다.

## 후속 참고

- 온보딩 운영 가이드 `docs/new-nikke-detection.md`에 이 파이프라인 실행법을 반영(감지
  토스트가 뜨면 `/onboard-new-nikkes` 한 번 실행 → 플랜 승인 → 끝).
