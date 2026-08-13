# 강제 재장전 적용 + MG 예열 속도 (2026-08-14)

두 갈래를 한 설계로 묶는다. 묶는 이유는 하나다 — **아스카의 Emergency Repair 한
스킬이 둘을 동시에 갖는다.** 한쪽만 하면 그 유닛은 절반만 맞는다.

## 무엇이 막혀 있나

`scripts/census_deferred_bullets.py`를 다시 돌렸다(95모듈 · 137불릿 = 갭 95 / 스코프
42). 그 결과 **두 갈래가 성격이 전혀 다르다**는 것이 드러났다.

### 갈래 1 — 강제 재장전: 엔진 갭이 아니라 카탈로그 누락

갭 #11(「강제 재장전 / 탄약 제거 상태머신」)은 **밀크: 블루밍 버니가 2026-07-20에 이미
닫았다.** 관용구는 `milk_blooming_bunny.py` 독스트링이 적고 있는 그대로다:

> "Removes 100% of ammo" + "Forced Reload" is what a weapon-mode SEGMENT
> boundary already does: `_base_shot_records` restarts each stretch with a
> fresh magazine at the stretch's start.

스칼렛: 블랙 섀도우는 같은 관용구의 **길이 0** 변형으로 즉시 완전 재장전을 쓴다.
재장전 속도 「고정」도 이미 구현돼 있다 — `_forced_reload_seconds`가 **자기 무기의
재장전 시간과 고정값만** 보고 라이브 버프를 보지 않으므로, 「고정 = 덮어쓰기」가 코드로
표현돼 있다. `reload_time_with_speed`의 음의 방향은 밀크의 실측(2초 파일값 → 3초)이
직접 앵커다.

**그런데 `engine-capabilities.md`에 이 관용구가 한 글자도 없다.** `forced reload` ·
`zero-length` · `empty a magazine` · `discard the magazine` 전부 0건이고,
`weapon_mode_schedules`는 「무기 변형」으로만 적혀 있다. 그래서 네 모듈이 「엔진이 못
한다」를 들고 있다:

| 슬러그 | 독스트링이 적고 있는 것 | 실제 |
|---|---|---|
| `jill-valentine` | "the engine has no way to empty a magazine mid-fight" | **낡은 보류** |
| `asuka-shikinami-langley-wille` | "ammo removal … not damage, not consumed" | **오분류** |
| `grave` | 무한탄약·탄약제거 둘 다 "not modeled" | 짝이 통째로 빠짐 |
| `laplace-ultimate-hero` | "resumes … with a fresh magazine and **no reload**" | 항을 알고도 미적용 |

[[stale-defers-need-the-catalog-not-the-docstring]]의 **네 번째** 사례다. 능력을 만든
날 카탈로그에 안 적으면 그 능력은 없는 것과 같다.

### 갈래 2 — MG 예열 속도: 진짜 엔진 확장

`attack_rate._SPINUP_BY_WEAPON`은 모듈 상수이고 `spinup_for_weapon(weapon)`은 무기
클래스만 받는다. **스킬이 예열을 건드릴 통로가 없다.**

게임에는 그 문구가 실재한다(수집 데이터 전수 확인, `heating up speed`를 쓰는 유닛은
정확히 둘):

- `rei-ayanami-tentative-name` Maintenance and Resupply — 풀버스트 진입 시,
  **「Machine Gun을 든, 버스트 스킬을 이미 쓴 아군」** 대상 `▲N% for M sec`
- `asuka-shikinami-langley-wille` Emergency Repair — Annihilation 사용 시 자기
  `▼100% for 3 sec`

**둘 다 실기록 덱3에 앉아 있다**(`rapi-red-hood-b1` · `crown` · `rei` · `asuka` ·
`helm-signature`, 그 중 MG가 셋). 예열은 탄창당 **1.4833초**의 실비용이므로
(`docs/measurements/mg-spinup.md`, `MG_SPINUP = Spinup(intervals=48, seconds=137/60)`)
±100%는 실제 숫자다.

### census가 드러낸 부수 사실 둘

1. **스코프 필터가 아스카를 삼켰다.** 그녀의 불릿은 같은 문장에 `HP recovery`가 있어
   스코프 통으로 걸러졌는데, **완전히 같은 메커니즘인 질 발렌타인은 갭 통에 있다.**
   스크립트 독스트링이 경고한 그 겹침이 이번엔 짝을 갈라놨다.
2. **갭 통의 95는 열린 갭 95가 아니다.** `deferred_bullets()`가 보류 절 헤딩을 찾은 뒤
   **독스트링 끝까지** 모든 불릿을 담아, 보류 절 **뒤에** 오는 절이 통째로 갭으로 세어진다.
   최악은 `laplace` — 독스트링이 `Not modeled / deferred (most of her kit):` 다음에
   `Modeled (weapon transform, 2026-07-21):`가 오는 구조라 **모델된 항목이 갭으로
   세어졌다.** 같은 이유로 `liberalio` 감사 5줄 · `snow_white_heavy_arms` 실측 4줄 ·
   `anis_star` 이력 2줄 · "Nothing outstanding" 3줄 등이 섞여 있다. 20 남짓이 열린 갭이
   아니다.

## 이 설계가 다루지 않는 것

- **census 스크립트의 과대계상 수정.** 위 사실 2는 이 작업에 필요하지 않다. 별도로
  기록·수정한다.
- **벨벳의 「Removes 5% of ammo」** — 문맥 확인 결과 `Affects all enemies`, 즉 **적의**
  탄약 탈취다. 이 갈래가 아니다.
- **아스카의 HP 회복**, 그레이브의 HP 드레인 — 생존기이고 딜 개념이 아니다. 계속 보류.
- **밀크: 블루밍 버니** — 이미 인코딩돼 있다. 손대지 않는다.
- **예열의 램프 모양** — `Spinup`은 총량 모델이고(측정이 못박은 것이 총량이다) 이
  설계는 그 총량에 배수를 걸 뿐, 모양을 바꾸지 않는다.
- **레이의 나머지 보류** — Anti A.T. Field 크로스유닛 타깃 상태(590.64%)와 Annihilation
  State 게이트는 그대로 남는다. 이 설계는 그녀의 예열 불릿 하나만 연다.

## Fienn 판정 (2026-08-14)

1. **예열 속도는 소요시간 배율로 본다.** `▼100%` → 예열 구간 ×2 · `▲100%` → ÷2.
   Ada의 「차지속도 ▼300% = 차지시간 ×4」와 같은 모양이다. **구간의 발수(48)는 안
   바뀐다** — 48발 구간이 길어지거나 짧아질 뿐이다.
2. **「Removes 100% of ammo」만 있고 「Forced Reload」 줄이 없어도 즉시 재장전이 돈다.**
   밀크·질과 동일하게 취급한다. 따라서 아스카·그레이브·라플라스UH도 대상이다.
3. **그레이브는 짝으로 간다** — 무한탄약과 탄약 제거를 같이 넣는다.

## 왜 갈래 1이 엔진 확장이 아닌가 — 세그먼트 경계의 의미론

`generate_segmented_shots`는 세그먼트 경계에서 **탄창을 버리고 새 탄창으로 재개**한다
(변형 후 resume 의미론). 그러므로:

- 재장전 길이만큼의 **무발사 세그먼트** = 「탄창 버림 · 재장전 중 · 새 탄창」
- **길이 0** 세그먼트 = 「즉시 완전 재장전」(스칼렛)

밀크가 쓰는 정확한 형태:

```python
{
    "start": start,
    "end": min(start + reload_seconds, fight_duration),
    "profile": {
        "weapon": weapon,
        "damage_percent": 0.0,
        "rate_of_fire": 1.0 / (reload_seconds * 2),
    },
}
```

`charge_time`이 아니라 **명시적 `rate_of_fire`** 를 쓰는 이유는 계약이다 — 명시적 연사
프로필은 측정 앵커라 **어떤 cadence 버프도 받지 않는다.** 차지 프로필로 쓰면 아군의
차지속도 버프에 창이 줄어들어 유령 발사가 샌다. `damage_percent: 0.0`이 두 번째
안전장치다.

## 갈래 1 — 유닛별 설계

네 유닛 모두 **엔진 코드 0줄**이다.

### 질 발렌타인 — 관용구의 가장 단순한 적용

Supercop(자기 버스트): `재장전 속도 79.8% 증가 고정` + `Removes 100% of ammo` +
`Forced Reload`, 그리고 10초 버프(명중 ▲66.09% · 공뎀 ▲60.52% · 평타 트루뎀).

- 세그먼트 `[bt, bt + reload_time_with_speed(자기 무기 재장전, +0.798)]`
- 이후 **새 탄창**이 10초 버프 창을 온전히 받는다
- 「the engine has no way to empty a magazine mid-fight」 문장 삭제

**방향은 예측하지 않는다.** 재장전 비용이 생기지만, 지금 엔진은 그녀가 버프 창 **안에서**
평소 속도의 느린 재장전을 맞을 수 있다. 순 효과는 돌려봐야 안다.

### 아스카 — 갈래 1과 2를 동시에 받는 유일한 유닛

Emergency Repair(Annihilation = 자기 버스트 시 발동), 효과 넷 중 **셋이 딜 항**이다:

| | 효과 | 처리 |
|---|---|---|
| 1 | `MG heating up speed ▼100% for 3 sec` | 갈래 2 |
| 2 | `Removes 100% of ammo` | 갈래 1 (세그먼트) |
| 3 | HP 회복 | 계속 보류(생존기) |
| 4 | `Reload speed is fixed at a 60% increase` | 갈래 1 (세그먼트 길이) |

세그먼트 `[bt, bt + reload_time_with_speed(자기 무기 재장전, +0.60)]`. 세그먼트가
끝나면 새 탄창이 시작되므로 **예열도 재무장한다** — 이는 기존 모델 그대로다(재장전은
발사가 아니다). 그 새 탄창의 예열이 ▼100%를 맞는다: 두 효과가 **같은 순간에 맞물린다.**

독스트링의 「HP and bookkeeping, not damage」를 정정한다.

### 그레이브 — 짝으로 (이 설계에서 가장 큰 조각)

그녀 독스트링: *"Her self HP drain and the **unlimited ammunition** (both Prediction)
are not modeled."* 즉 Prediction 10초 동안 **무한탄약(이득)**, 끝날 때 **탄약 제거(비용)**
가 둘 다 빠져 있다. **비용만 넣으면 그녀는 이유 없이 나빠진다** —
[[deferred-approximation-hides-in-code]]와 같은 모양이다.

세그먼트 둘로 짝을 표현한다:

1. `[bt, bt + PREDICTION_DURATION]` — 기저 무기와 같은 프로필이되 **재장전이 안 일어날
   만큼 큰 탄창**. 이것이 무한탄약이다. 이 세그먼트의 **끝 경계가 곧 탄약 제거**다.
2. `[bt + PREDICTION_DURATION, + 재장전]` — 무발사 세그먼트.

Prediction 창은 이미 모델돼 있다(`PREDICTION_DURATION = 10.0`, 자기 버스트가 부여,
`build_overheat_per_shot_rules`가 이미 그 창을 읽는다). 새 타임라인을 발명하지 않는다.

**확인이 필요한 것:** 그녀의 `Heat Emission: Reload Ratio ▼ 50%`가 이 재장전에 걸리는
「고정」인지, 별개 항인지. 문구가 질·아스카·밀크의 `Reload speed is fixed at`과 **다르다.**
구현 시 원문을 다시 읽고, 불확실하면 Fienn에게 묻는다 —
[[ask-fienn-on-unclear-skill-mechanics]].

### 라플라스: 얼티메이트 히어로 — 이미 적어둔 항을 닫는다

그녀 독스트링이 이미 적고 있다: *"resumes the base weapon at the segment's end with a
fresh magazine and **no reload**, so she fires ~2 extra base shots during the 2.5s reload
the real cycle spends."* 이것이 정확히 `Removes 100% of ammo`(Fully Full Charge 종료
시)다.

기존 `build_laplace_transform_schedule`가 만든 변형 세그먼트 **뒤에** 무발사 세그먼트를
붙인다. 이 유닛이 **세그먼트 합성의 검증 사례**다 — 나머지 셋은 세그먼트를 처음 갖는다.
그녀 독스트링의 「rounding error」 평가는 실측 후 갱신한다.

## 갈래 2 — MG 예열 속도 엔진 확장

### 자료구조

새 스탯 **`mg_heating_speed_percent`**. 스탯 이름에 화이트리스트는 없다 —
`registry.total_for(stat, target, t)`가 이름으로 합산할 뿐이다. 발행은
`Effect("mg_heating_speed_percent", ...)`.

`attack_rate`에 순수 함수 하나를 더한다:

```python
def spinup_with_speed(spinup, heating_speed_percent, rate_of_fire):
    """예열 구간의 길이를 버프로 조정한 새 Spinup. 발수(intervals)는 안 바뀐다."""
```

- `s ≥ 0` → `seconds / (1 + s)`
- `s < 0` → `seconds * (1 - s)`
- 그리고 **클램프**: 램프 간격이 공칭 간격보다 짧아질 수 없다
  (`seconds >= intervals / rate_of_fire`). 예열은 느려지는 구간이지 가속 장치가 아니다.

**양의 방향이 `reload_time_with_speed`의 `(1 - s)`와 일부러 다르다.** 그 식을 쓰면
▲100%에서 예열이 통째로 사라진다(×0). Fienn 판정이 「÷2」이므로 이 갈라짐은 의도이며,
독스트링에 그렇게 적는다. 음의 방향은 두 식이 일치한다(둘 다 ▼100% → ×2).

숫자로: `MG_SPINUP.seconds = 137/60 = 2.2833초`
→ ▼100%에서 **4.5667초**, ▲100%에서 **1.1417초**.
클램프가 무는 지점은 `s > 185.4%`이므로 ▲100%는 닿지 않는다.

### 배선 — 호출부는 넷이다

`spinup_for_weapon`의 호출부는 `attack_rate.py`의 **네 곳**이다(643 · 773 · 865 ·
1064줄): 발사 시각 생성기, last-bullet 마커, first-bullet 마커, 세그먼트
`_base_shot_records`. 네 곳 전부가 이미 `magazine_start`에서 `shot_interval`과
`capacity`를 샘플링하므로, 예열도 **같은 시점에 같은 방식으로** 샘플링한다:

```python
spinup = spinup_with_speed(base_spinup, heating_at(magazine_start), rate)
```

`magazine_shot_offset`은 **무변경**이다 — 스케일된 `Spinup`을 받을 뿐이다. 이것이
「탄창 타임라인을 만드는 곳이 둘이고 세그먼트가 없을 때 비트 동일이 계약」이라는 기존
성질을 지키는 방법이다.

`raid_simulator.py`는 `attack_speed_percent_at`와 **동형인 람다** 하나를 더해 넷에
넘긴다:

```python
heating_speed_percent_at = lambda t, target=target: registry.total_for(
    "mg_heating_speed_percent", target, t)
```

기본값은 `_zero`이므로 **버프가 없으면 지금과 바이트 동일**이다.

### 소비자 둘

**레이** — `member_subset_buff_rule`이 이미 「Burst 3 아군 중 버스트를 이미 쓴」 같은
부분집합을 지원하고 `burst_used_this_cycle`을 트리거 시점에 읽는다. 대상 필터는
`m.weapon == "MG" and 버스트 사용함`. 그녀의 Maintenance and Resupply는 이미
인코딩돼 있으므로 불릿 하나를 얹는 모양이다.

**아스카** — 자기 버스트에 `▼1.0`을 3초. 세그먼트와 같은 순간에 맞물린다.

### 슬롯 번호를 세지 않는다

**두 유닛 모두 매니페스트 `source`가 `lootandwaifus`다.** 그 소스는 슬롯이 **토큰
순서**로 정해지므로, dotgg 템플릿에서 읽은 `description_value_01/_02` 같은 번호를 그대로
쓰면 안 된다. 「불릿의 두 번째 숫자」를 `_02`로 적어 세 태스크 연속 틀린 그 함정이다
([[slot-02-is-the-duration]]). **구현 시 파일을 열어 센다.**

## 짚어둔 근사

- **예열 버프는 탄창 시작 시점에 샘플링된다.** 탄창 도중에 버프가 들어오거나 끊기면 그
  탄창의 램프는 시작 시점 값을 유지한다. `shot_interval`·`capacity`가 이미 같은 규약이라
  새 근사가 아니다. 아스카는 세그먼트가 그녀의 새 탄창을 ▼ 시작과 같은 순간에 열어주므로
  이 근사에 걸리지 않는다.
- **제거된 탄약이 아군 소모탄 카운터에 잡히는지는 모른다.** 리틀 머메이드의 Bubble
  Barrage가 「1발 = 1라운드」를 가정한다는 것은 이미 그녀 독스트링에 적혀 있다. 이
  설계는 그 카운터를 건드리지 않는다 — 즉 버려진 탄약은 안 세어진다. 명시적 가정으로
  남긴다.
- **그레이브의 무한탄약을 「재장전이 안 일어날 만큼 큰 탄창」으로 근사한다.** 진짜
  무한이 아니라 창 길이 안에서 구별 불가능한 값이다.

## 테스트

각 항목마다 **가드를 직접 떼서 빨개지는지** 확인한다. 「어떻게 망가뜨리면 이게
빨개지나」에 답 못 하는 테스트는 아무것도 재지 않는다
([[guard-tests-are-green-before-the-guard-exists]], [[plan-tests-pass-on-absent-data]]).

**갈래 2 엔진:**
- `spinup_with_speed`의 두 방향과 클램프 — `s=0`이 항등인지, ▼100%가 ×2인지,
  ▲100%가 ÷2인지, `s=200%`가 클램프에 걸리는지
- **버프 없는 유닛이 트렁크와 바이트 동일**인지(회귀 방지의 핵심)
- 예열이 실제로 발사 시각을 미는지 — 스탯을 켜고 끄며 MG 유닛의 발사 수 차이 확인
- 네 호출부가 **전부** 배선됐는지: 마커 생성기 둘이 빠지면 first/last-bullet 트리거가
  실제 탄창과 어긋난다(과거 배선 지점이 넷이었던 이유가 그것이다)

**갈래 1 유닛:**
- 네 유닛 각각 세그먼트가 기대 시각·길이로 나오는지
- 세그먼트 창 안에서 **딜이 0**인지(유령 발사가 안 새는지)
- 세그먼트 뒤 첫 발이 **새 탄창의 첫 발**인지
- 그레이브: 무한탄약 창 안에서 **재장전이 없는지**, 그리고 창 끝에서 재장전이 도는지
- 라플라스UH: 변형 세그먼트와 재장전 세그먼트가 **겹치지 않는지**

**전체:**
- `test_no_duplicate_definitions.py` 포함 백엔드 전 스위트(기준선 2299 passed)
- `scripts/measure_record_calibration.py` — 아스카·레이가 덱3에 있어 움직인다
- 스윕으로 네 유닛 델타

## 구현 순서

1. **A — 카탈로그 기재.** B의 네 독스트링이 전부 이 문장을 근거로 삼으므로 먼저 간다.
2. **B — 질 발렌타인.** 관용구의 가장 단순한 적용, 첫 증명.
3. **B — 라플라스 UH.** 기존 세그먼트와의 합성 검증.
4. **B — 그레이브.** 무한탄약 + 재장전 짝. 가장 크다.
5. **C — 엔진.** `spinup_with_speed` + 네 호출부 + 람다. 소비자 없이 테스트로 검증.
6. **C — 레이.** 첫 소비자.
7. **B+C — 아스카.** 둘을 동시에 받는다. 5·6 이후여야 한다.
8. **측정과 문서.** 캘리브레이션 · 스윕 · `engine-gaps.md` 정정(위 「census가 드러낸
   부수 사실」 포함) · `encoded-nikkes.md` 갱신.
