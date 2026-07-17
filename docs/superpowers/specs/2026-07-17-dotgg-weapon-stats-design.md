# dotgg 무기 스탯 공백 해소 — 설계

날짜: 2026-07-17 · 승인: Fienn

## 배경 / 문제

- 엔진은 유닛별 `charge_time`(dotgg `chargeTime`)을 그대로 사용한다
  (`attack_rate.py`, `user_roster.py:_weapon_stats`). 무기 종류별 기본값이
  아니므로 Liberalio(1.5s), Scarlet: Black Shadow(0.3s) 같은 비표준 차지
  속도는 **데이터만 있으면** 이미 정확히 시뮬레이션된다.
- 수집 워크플로가 lootandwaifus 우선으로 바뀐 뒤, lootandwaifus로만 수집된
  유닛은 dotgg 무기 스탯 파일(`data/dotgg/char_<slug>.json`)이 없어서
  `load_nikke_spec`이 로스터에서 제외한다(알려진 공백, user_roster.py
  docstring).
- lootandwaifus에는 무기 종류(RL/SR/…)만 있고 세부 스탯(chargeTime,
  maxAmmo, reloadTime, damage, chargeDamage)이 없다.
- dotgg는 2026년 5월경 이후 갱신이 중단된 것으로 확인됨(라이브 캐릭터 목록
  190명 대조): 그 이전 유닛은 지금도 API로 받을 수 있으나
  (scarlet-black-shadow chargeTime 0.3 확인), 이후 신규 유닛
  (ark-ranger-black, cinderella-crystal-wave, marciana-marine-study,
  prika)은 어떤 이름으로도 없다.

## 결정 (검토한 대안: 제3소스 스크레이핑 → 보류, YAGNI)

엔진·로더 코드는 변경하지 않는다. 데이터 공백을 두 갈래로 메운다:

1. dotgg에 있는 유닛 → 재사용 가능한 수집 스크립트로 자동 수집
2. dotgg에 없는 신규 유닛 → Fienn이 확인한 값을 같은 스키마의 수동
   파일로 작성 (신규 유닛은 월 1–2명 수준이라 부담이 작다)

## 구성요소

### 1. `scripts/collect_dotgg_weapons.py` (~120줄)

- `data/lootandwaifus/char_*.json`을 스캔, 대응 dotgg 파일이 없는 유닛을
  찾는다. 인코딩된 유닛은 registry manifest의 `dotgg_slug`/`data_slug`
  별칭도 확인해 기존 별칭 파일(char_ada.json 등)을 중복 수집하지 않는다.
- dotgg 슬러그 해석: 라이브 캐릭터 목록(`fetch_character_list`)에서
  ① 슬러그 일치 → ② 이름 일치(대소문자 무시) → ③ 실패 시 "dotgg에 없음"
  으로 보고.
- 수집: 기존 `dotgg_client.fetch_character` 재사용(디스크 캐시 포함),
  `data/dotgg/char_<dotgg슬러그>.json`으로 저장. 로더는 파일명이 아니라
  파일 안의 `url` 필드로 dotgg 데이터를 색인하므로
  (`skill_values.py:_dotgg_path_for`), dotgg 슬러그가 lootandwaifus
  슬러그와 달라도 `url`이 manifest의 `data_slug`(기본값 = 인코딩 슬러그)와
  일치하면 찾는다. 다르면 스크립트가 manifest에 `dotgg_slug` 별칭이
  필요하다고 보고한다.
- `--stub`: dotgg에 없는 유닛에 대해 수동 입력 템플릿을 생성한다.
  `url`·`name`·`weapon`·`"source": "manual"`은 lootandwaifus에서 프리필,
  탄창 무기(AR/MG/SMG/SG)는 `chargeTime: 0`·`chargeDamage: "0%"`도
  프리필한다. Fienn이 손으로 넣을 값은 차지 무기(RL/SR) 5개
  (maxAmmo, damage, reloadTime, chargeTime, chargeDamage), 탄창 무기
  3개(maxAmmo, damage, reloadTime)뿐이다 — 스킬·버스트·속성 등 나머지는
  전부 lootandwaifus 파일에서 오므로 수동 입력 대상이 아니다. 미입력
  필드는 빈 값으로 넣지 않고 **생략**한다(`"_todo"` 키에 채울 필드 목록을
  적어둠) — 필드가 없으면 `_weapon_stats`의 존재 검사에서 None이 되어
  깔끔하게 제외되지만, 빈 문자열이 들어 있으면 존재 검사를 통과한 뒤
  `int("")`에서 예외가 나기 때문이다.
- 재실행 가능(이미 있는 파일은 건너뜀), 유닛별 네트워크 오류 보고 후 계속
  진행, `--help`와 실행 결과 요약(수집/건너뜀/없음) 제공.

### 2. 수동 파일 규약

dotgg에 없는 유닛은 `data/dotgg/char_<slug>.json`을 손으로 작성한다.
필수 필드는 `_weapon_stats`가 읽는 여섯 개(`weapon`, `maxAmmo`, `damage`,
`reloadTime`, `chargeTime`, `chargeDamage`)이고 `"source": "manual"`로
출처를 표시한다. 로더 코드 변경 없음.

### 3. 워크플로 갱신

`collect-nikke` 스킬 지침에 추가: lootandwaifus 수집 후 이 스크립트를
실행해 dotgg 무기 스탯도 확보하고, dotgg에 없으면 Fienn에게 측정값을
요청해 수동 파일을 작성한다.

### 4. 문서

- `docs/roadmap.md` To-Do 갱신.
- `/document`로 dotgg 갱신 중단 사실과 수동 파일 규약을 insights/decisions에
  기록.

## 오류 처리

- 캐릭터 목록/상세 API 실패: 해당 유닛만 오류로 보고하고 계속 진행.
- 이름 매칭 실패: 조용히 넘어가지 않고 "dotgg에 없음" 목록으로 출력.
- 수동 스텁의 빈 값: 로더가 기존 필드 검사로 제외하므로 부분 데이터가
  시뮬레이션에 흘러들지 않는다.

## 테스트

- 스크립트의 순수 함수(누락 판정, 슬러그/이름 해석, 스텁 생성)에 단위
  테스트를 추가한다. 네트워크 호출부는 목 데이터로 검증.
- 엔진은 변경하지 않으므로 기존 스위트 통과 확인만 한다.

## 완료 기준

- 스크립트 실행으로 scarlet-black-shadow 등 dotgg 보유 유닛의 무기 스탯
  파일이 생성된다 (SBS chargeTime 0.3).
- dotgg에 없는 4유닛이 스텁과 함께 보고되고, 값 입력 시 로스터 로딩에
  포함된다 (인코딩된 ark-ranger-black·marciana-marine-study·prika가
  실사용 가능해짐).
- 전체 테스트 스위트 통과.
