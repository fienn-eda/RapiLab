# 클립형 재장전 (engine-gap #19) — 설계

- 날짜: 2026-07-31
- 상태: 설계 승인 대기
- 관련: `docs/engine-gaps.md` #19 · `backend/app/skill_rules/centi.py` · `backend/app/attack_rate.py`

## 문제

일부 니케는 탄창을 한 번에 채우지 않는다. 센티는 6발 탄창을 2발씩 세 번,
0.5초(30프레임)씩 장전한다(Fienn 실측, 2026-07-30). 엔진은 "탄창을 다 쓰면
`reload_time` 한 번"이라는 단일 모델이라 그녀의 케이던스가 발당 1.45초로 나온다 —
실제는 1.617초, **약 11% 낙관**이다.

순수한 케이던스 오차로 보이지만 버프 가동률로 전파된다. `centi-signature`의
유효 쿨다운은 그녀의 발당 간격에서 유도되므로, 간격이 낙관적이면 그녀의 스쿼드
ATK 버프 가동률도 낙관적이다.

## 갭 문서의 전제가 틀렸다 — 분할 횟수는 데이터에 있다

갭 #19는 "분할 수가 데이터에 없어 실측 상수 테이블이 필요하다"고 적혀 있었다.
`data/shiftypad/raw/*.json`의 `shot_detail.reload_bullet`이 바로 그 필드다 —
**10000 = 탄창의 100%를 한 번에**, 그보다 작으면 그 비율만큼만 채운다.

수집된 77유닛 중 10000이 아닌 것은 여섯이다:

| 유닛 | 무기 | 탄창 | `reload_bullet` | 클립 | 파일 재장전 | 총 재장전 | 분할 |
|---|---|---:|---:|---:|---:|---:|---:|
| Centi | RL | 6 | 3300 (33%) | 2발 | 0.5초 | 1.5초 | 3 |
| Drake | SG | 9 | 3300 | 3발 | 0.5초 | 1.5초 | 3 |
| Sugar | SG | 9 | 3300 | 3발 | 0.67초 | 2.01초 | 3 |
| Soda: Twinkling Bunny | SG | 9 | 3300 | 3발 | 0.67초 | 2.01초 | 3 |
| Noir | SG | 9 | 3300 | 3발 | 0.23초 | 0.69초 | 3 |
| Grave | **AR** | 60 | **5000 (50%)** | 30발 | 1.0초 | 2.0초 | 2 |

**데이터가 실측을 그대로 재현한다**: 6 × 33% = 2발, 3회, 0.5초 — Fienn이 화면에서
읽은 것과 같다. 이 일치가 필드 해석의 근거다.

두 가지가 같이 정정된다:

- 갭 제목의 "런처·샷건"은 불완전하다. **Grave는 AR인데 클립**이다.
- 막힌 슬러그는 2개가 아니라 **9개**다(시그니처 포함). 전부 이미 인코딩돼 있다.

분할 수는 `ceil(max_ammo / round(max_ammo × 비율))`로 유도되며, Max Ammo 버프가
탄창을 키워도 값이 변하지 않는다(비율이 함께 커진다). 예: 33%는 탄창 6·8·12
어디서나 3분할. 그래서 비율이 아니라 **분할 수를 그대로 저장**해도 안전하다.

## 재장전이 언제 일어나는가 (Fienn, 2026-07-31)

**탄창을 다 비운 뒤 n회 연속**이다. 2발 쏘고 장전하고를 반복하는 형태가 아니다.
장전 n회가 끝난 뒤 재장전 모션 딜레이가 **1회** 붙는다 — 클립마다가 아니다.

그 1회는 엔진이 이미 표현하고 있다. `generate_charge_shot_times`는 재장전 후 첫
샷을 `charge + motion_delay` 뒤에 놓는다. 센티 사이클이 이를 검산한다:

```
6발 × (차지 1.0초 + 모션 딜레이 22프레임)  = 8.200초
+ 3회 × 0.5초                              = 1.500초
                                    사이클  = 9.700초   → 발당 1.6167초 ✓
```

Fienn의 1.617초와 일치하고, 별도 딜레이가 들어갈 자리가 산술적으로 없다. 클립마다
모션 딜레이가 붙는 모델이었다면 사이클이 10.8초가 된다.

따라서 필요한 변경은 **재장전 길이 하나뿐**이고, 타임라인 구조는 그대로다.

## 설계

### 1. 값의 위치 — 레지스트리 코드 테이블

```
backend/app/skill_rules/registry.py

CLIP_RELOAD_SPLITS = {...}          # 9개 슬러그
get_clip_reload_splits(slug) -> int # 기본 1
```

`_CHARGE_MOTION_DELAY`와 같은 자리·같은 모양이다. 테이블 주석이 출처를
`shiftypad shot_detail.reload_bullet`로 명시한다.

**왜 런타임에 데이터에서 읽지 않나.** `data/` 전체가 gitignore다. 그리고 이 필드는
shiftypad에만 있다 — dotgg·lootandwaifus의 캐릭터 파일은 무기 스탯 6종(weapon,
damage, maxAmmo, reloadTime, chargeTime, chargeDamage)만 담는다. 클립 9슬러그 중
drake·drake-signature·noir·soda-twinkling-bunny·grave는 무기 출처가 shiftypad가
아니므로, 데이터에서 읽으려면 이들을 shiftypad로 옮겨야 하고 그러면
`data/shiftypad/<slug>.json` 4개가 새로 필요한데 **그 파일은 git에 안 들어간다.**
없는 환경에서는 `load_nikke_spec`이 `None`을 반환해 유닛이 조용히 로스터에서
빠진다.

"shiftypad 1순위" 방침(Fienn)은 값의 **출처** 규칙이지 런타임 읽기 방식이 아니다.
`_CHARGE_MOTION_DELAY`도 출처는 Fienn 실측이고 위치는 코드다.

**범위 밖:** 그 4명의 `weapon_source`를 shiftypad로 옮기는 것. 6개 필드가 이미
shiftypad와 완전히 동일함을 확인했으므로 얻는 것이 없고, 위의 유실 위험만 진다.

### 2. 배선 — 깔때기 한 곳

`user_roster.load_nikke_spec`에서 무기 프로필 오버라이드 직후:

```
reload_time ← reload_time × get_clip_reload_splits(slug)
```

`NikkeSpec.weapon_stats`가 단일 출처라 소비자 넷이 전부 자동으로 고쳐진다:

| 소비자 | 경로 |
|---|---|
| 덱 시뮬레이션 | `roster.py` → `raid_simulator` → `attack_rate` |
| 해석 경로 (덱 탐색) | `closed_form.py:176,181` → `generate_shot_times` |
| 차지창 계산기 | `charge_window_inputs.py:134` |
| 스킬값 | `roster.py:135` `caster_weapon_stats` → 센티 유효 쿨다운 |

**`attack_rate.py`는 손대지 않는다.** `reload_time_with_speed` 호출부 9곳이 모두
`reload_time`을 그대로 읽고, 그 함수는 양의 가지(`rt / (1+s)`)와 음의
가지(`rt × (1-s)`) 모두 `reload_time`에 대해 선형이라 곱셈 순서가 결과를 바꾸지
않는다.

`weapon_stats["reload_time"]`의 의미는 "탄창을 다시 채우는 데 걸리는 시간"이 된다.
소비자 전원이 이미 그 뜻으로 쓰고 있으므로 도메인 이름이 더 정확해지는 쪽이다.

**남겨둘 주석:** 재장전 아핀 모델(`파일값 × (1−s) + 0.148초`, `engine-gaps.md` ★)이
나중에 착륙하면 고정 0.148초 구간이 클립마다 붙는지 재장전당 한 번인지 다시
갈라야 한다. 여기서 접어 넣는 것은 현행 곱셈 모델에서만 정확하다.

### 3. 드리프트 방지 — 기존 감사 스크립트 확장

`scripts/audit_weapon_data.py`는 이미 인코딩된 전 슬러그의 무기 6필드를 shiftypad
raw와 대조한다. `reload_bullet`을 **일곱 번째 필드**로 추가해, raw가 말하는 분할
수와 `CLIP_RELOAD_SPLITS`를 대조한다. 신규 니케가 클립인데 테이블에 없으면
MISMATCH로 잡힌다.

새 스크립트를 만들지 않는 이유: 같은 raw 파일을 같은 슬러그 집합에 대해 이미 읽고
있다. 두 번째 스크립트는 같은 로딩을 복제한다.

### 4. 인코딩 워크플로 체크리스트

`.claude/skills/nikke-skill-encoding`의 데이터 확인 단계에 한 줄: 수집한 shiftypad
번들의 `shot_detail.reload_bullet`이 10000이 아니면 클립 무기이므로
`CLIP_RELOAD_SPLITS`에 등록할 것.

사람이 보는 쪽과 자동 검출 쪽 둘 다 두는 이유: 감사 스크립트는 raw 번들이 수집된
뒤에만 답할 수 있고, 인코딩은 그보다 먼저 시작된다.

## 테스트

- `get_clip_reload_splits` — 클립 9슬러그가 각자의 값, 미등록 슬러그는 1
- **센티 앵커**: 그녀의 샷 타임라인에서 7번째 샷이 11.0667초(현행 10.0667초)에
  오고, 12번째가 17.9초(현행 16.9초)이며, 정상상태 발당 간격이 사이클 9.7초 ÷ 6 =
  **1.6167초**(현행 8.7 ÷ 6 = 1.45초)로 Fienn 실측과 일치. 60초 발수 41 → 37
- Grave(탄창 무기 경로, 2분할) — 60발마다 2.0초
- 비클립 유닛의 타임라인 불변 (회귀)
- 재장전 속도 버프와의 상호작용: 분할 곱셈이 `reload_time_with_speed`의 양·음
  가지 모두에서 선형임을 고정
- `centi.field_discussion_effective_cooldown`이 새 간격을 반영해 늘어남

실기록 5덱에는 클립 유닛이 하나도 없으므로 **캘리브레이션 합계 1.010x는 불변**이다.
검증 앵커는 센티 실측 하나뿐이라는 뜻이기도 하다.

## 문서 갱신

- `docs/engine-gaps.md` #19 — 해소. 전제 정정("데이터에 없다" → `reload_bullet`),
  Grave(AR) 추가, 9슬러그
- `docs/insights.md` — 문서가 "데이터에 없다"고 단정하면 원본 페이로드를 직접 열어
  확인할 것. 갭 #19는 그 단정 때문에 실측 캠페인이 필요한 작업으로 분류돼 있었다
- `docs/decisions.md` — 값의 출처(shiftypad)와 위치(코드)를 가른 결정, gitignore 제약
- `backend/app/skill_rules/centi.py` docstring — 보류 사유 삭제

## 조사 중 발견한 별건 — 이번 범위 밖

`closed_form._shot_count`(덱 탐색의 해석 경로)는 `generate_shot_times`를 부르는데,
그 함수에는 **차지 모션 딜레이를 받는 인자가 없다**. 캐시 키도 무기·탄창·재장전·
차지시간뿐이다. 즉 덱 탐색이 세는 발수는 모션 딜레이를 가진 차지 유닛
(`TIMED_CHARGE_MOTION_DELAY` 13슬러그)에서 낙관적이다 — 센티라면 60초에 41발 대
실제 37발. 시뮬레이션 경로(`_base_shot_records`)는 딜레이를 제대로 접는다.

이 클립 수정은 `reload_time`을 통하므로 두 경로에 **모두** 닿는다(캐시 키에
`reload_time`이 있다). 위 모션 딜레이 누락은 그와 독립된 선행 결함이고, 고치면
덱 탐색의 순위가 움직이므로 별도 작업으로 둔다.

## 예상 영향

센티 발당 1.45 → 1.617초. 나머지 8슬러그도 총딜이 내려가는 방향이며,
`centi-signature`는 케이던스와 버프 가동률 양쪽으로 내려간다.
