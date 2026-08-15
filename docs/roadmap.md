# NIKKE Deck Builder — 로드맵 & 진행 현황

우리가 뭘 만들고 있고, 어디까지 왔고, 다음에 뭘 할지 한눈에 보는 문서.
큰 그림은 **로드맵(단계)**, 작은 단위 작업은 **To-Do**에서 관리한다.
결정의 배경은 `docs/decisions.md`, 엔진 함정/패턴은 `docs/insights.md`,
인코딩된 니케 목록(Burst 단계별)은 `docs/encoded-nikkes.md`,
엔진 갭 인벤토리(확장 우선순위)는 `docs/engine-gaps.md`,
스킬 인코딩 방법은 `nikke-skill-encoding` 스킬 참고.

- 마지막 갱신: 2026-08-15
- **유닛별 연사가 착륙했다 (2026-08-15).** `shot_detail.rate_of_fire`는 유닛별
  (분당 발수)인데 엔진은 무기군 상수를 쓰고 있었다. 인코딩 103슬러그 중 어긋나는
  건 **질: 발렌타인 하나** — 9발 AR을 150발/분(2.5발/초)으로 쏘는데 클래스 720을
  받아 **평타가 4.8배**였고, Fienn 실측이 확정했다(**발 간격 24±1프레임**).
  `ROUNDS_PER_MINUTE` + `rounds_per_second`(60fps 격자) + `weapon_stats`.
  **백엔드 2405 passed / 3 skipped**, 캘리 **1.042x · 19/25 · 무기군 평균 전부
  불변**(그녀가 로스터에 없다).
  - **값어치는 캘리가 아니라 감사다** — `scripts/audit_rate_of_fire.py`가 인코딩
    전 슬러그를 데이터와 대조한다. 아무도 이 필드를 안 보고 있어서 4.8배가 조용히
    살아 있었다.
  - **클래스 상수 넷은 틀리지 않았고 이제 유도가 있다** — `60/ceil(60÷공칭)`이
    AR 12.0 · SG 1.5 · SMG 20.0 · MG 60.0을 재현한다. SMG 24·MG 70이 엔진 값과
    다른 건 격자 올림의 결과다. SG 산탄이 빠진 딜 배수라는 의혹도 같이 기각됐다.
  - 곁가지: `audit_core_damage_rate.py`가 **트렁크에서 이미 깨져 있었다**(페르소나
    콜라보 둘이 별칭 표에 없어 101/103만 검사) — 공유 표를 고쳐 같이 살렸다.
- **차지 무기의 `rate_of_fire`도 착륙했다 — 케이던스가 아니라 바닥값이었다
  (2026-08-15).** 차지가 0이 돼도 남는 가장 짧은 발 간격이고, 수집된 차지 무기 31정 중
  기본값 60발/분을 벗어나는 **다섯**이 정확히 「멈춤 없음」 넷 + 신데렐라다(우연 확률
  0.16%). 옛 전역 `CHARGE_INTERVAL_FLOOR_SECONDS`(10/29)는 신데렐라 무기의 180발/분
  =0.33333초를 한 발 짧게 읽은 값이었다 — 정수 20프레임 대 20.69프레임. 기본값 60은
  바닥값이 **아니다**(스칼렛이 그 값으로 0.7325초마다 쏜다). 신데렐라 0.964x →
  **0.980x**, 나머지 24유닛 불변, 합계 1.043x·19/25, 백엔드 **2407 passed**.
  가르는 건 `shot_detail.input_type`이다 — `UP` 26정(놓을 때 발사 → 멈춤 있음, rpm 60은
  자리채움) 대 `DOWN_Charge` 5정(누른 채 반복 → 멈춤 없음, rpm이 바닥). 상관관계가 아니라
  메커니즘이라 **새 유닛을 재기 전에 분류해 준다.**
- **무기변형 탄착군 갭이 닫혔다 — 20슬러그가 아니라 7이었고, 실측 다섯으로 0 (2026-08-15).**
  탄착군은 세그먼트 라벨이 아니라 **기저** 무기로 찾으므로, 기저가 SR/RL·수렴 MG면 코어율이
  어차피 1.0이라 근사가 아무것도 안 바꾼다(20 중 12). Fienn 인게임 판독: 츠바이·스노우화이트는
  코어 100%라 `always_core_hit`(각 +7.4% · +15.9%), 그레이브·질: 발렌타인은 100%가 아니라
  **현행 근사가 맞다**, 목단은 창모드 조준원을 재서 **신규 선언 `spread_diameter: 150`**
  (같은 프레임 두 판독의 비 100px/50px × AR 75라 화면 스케일도 명중률도 약분된다).
  이어서 창모드 케이던스도 실측 — SMG 클래스 상수 20발/초가 **20% 느렸다**(24발/초, 판독이
  3프레임을 7.4σ로 기각). moran-signature 0.962x → 0.821x(조준원만) → **0.977x**(둘 다).
  **백엔드 2410 passed / 3 skipped**, 캘리 **1.043x · 19/25**.
  원본: `docs/measurements/moran-spear-mode.md`.
- **MG 탄착군의 탄창 내 수렴이 착륙했다 (2026-08-15).** MG는 탄창을 250px로 열어
  발당 7px씩 조여 수렴값 10px에 닿는다(`shot_detail`에 이미 있던 값). 코어 48.89
  앞에서 **앞 29발의 코어율이 0.038 → 1.0**으로 오르므로, 그 구간의 코어 보너스가
  더 이상 공짜가 아니다. `accuracy.SPREAD_CONVERGENCE` + `ShotRecord.magazine_index`가
  발 인덱스를 `_core_hit_rate_at`까지 나른다(`None` = 수렴값 = 세그먼트·프론트 미러).
  **백엔드 2398 passed / 3 skipped**, 캘리 **1.044x → 1.042x · 19/25 불변 ·
  MG 평균 1.176x → 1.164x**(마스트 1.310→1.275가 최대 이동, SR·RL·SMG·AR 불변).
  - **MG 과대의 원인은 코어 관문이고 예열도 재장전도 아니었다.** 예열을 통째로 꺼도
    잔차 순서가 그대로였고, 「재장전이 s>1에서 0초가 되는 것이 틀렸다」는 가설은
    Fienn의 프레임 실측 네 벌이 기각했다(공백 실측 13.75f vs 엔진 13.5f). MG
    타임라인은 이제 전 항이 실측이다.
  - **남은 것은 `p_조준` 하나다**(갭 #21). 코어 항은 MG 딜의 ~28%이고, 실기록에
    맞추면 크라운 0.245 · 마스트 0.269 · 신데렐라CW 0.211로 셋이 뭉친다. 플레이
    조건이라 데이터로는 못 만든다 — Fienn 판정이 필요한 To-Do.
- **강제 재장전 프리미티브 확산 + MG 예열 속도 배선 (2026-08-14)**: 질 발렌타인·
  라플라스: 얼티메이트 히어로·그레이브·아스카에 발사 0개 세그먼트
  (`_helpers.silent_reload_segments`)로 강제 재장전/탄약 제거를 배선하고, 신규
  스탯 `mg_heating_speed_percent`로 레이 아야나미(Tentative Name)의 MG 아군 예열
  가속 버프와 아스카 자신의 예열 감속 디버프를 배선했다. 그레이브는 같은
  배치에서 Heat Emission의 스쿼드 Pierce Damage 버프가 다음 자기 버스트까지
  무기한으로 걸려 있던 기존 결함도 정정(방열이 실제로 꺼지는 조건 — 이중
  재장전 — 에 바운드). 갭 #11(강제 재장전/탄약 제거 상태머신)은 2026-07-20에
  이미 닫혀 있었으나 인코더가 읽는 카탈로그(`engine-capabilities.md`) 누락으로
  세 유닛이 계속 막혀 있었다 — [[stale-defers-need-the-catalog-not-the-docstring]]
  네 번째 사례. 백엔드 **2299 → 2332 passed**(3 skipped 불변; 코어 지름 작업과
  합류 후 **2358**). **캘리브레이션은 코어 지름 착륙과 같은 날 합류해 두 번 쟀다** —
  코어 지름 없이 단독으로는 1.065x·16/25 → 1.062x·16/25였고, 코어 지름 위에 얹은
  합류 후는 **1.036x·20/25 → 1.033x·20/25**다. 두 작업이 건드리는 무기군이 갈라져
  겹치지 않는다: 코어 지름은 SMG·AR만 움직였고, 이 작업의 MG 평균 1.078x → **1.094x**
  (같은 n=6 기준)는 레이의 예열 가속이 덱3의 MG 셋에 얹힌 몫이다. 아스카가 caveat로
  빠진 뒤 스크립트가 보고하는 MG 평균은 **1.125x(n=5)**. 상세: `docs/engine-gaps.md`,
  `docs/encoded-nikkes.md`.
- **MG 램프 곡선과 부분 잔존이 착륙했다 (2026-08-14).** 예열이 **누적 곡선**이 되고
  (콜드 137프레임 중 **56프레임이 첫 2발**), 짧은 재장전이 남긴 예열을 다음 탄창이
  물려받는다(감쇠 **D=66프레임** 선형, 발사 공백에 실측된 **재장전 후 지연 12.5프레임**
  포함). 탄창 워크 넷이 전부 배선됐고, 예열 클램프는 총합이 아니라 **구간별**로 걸린다
  (레이의 ▲100%가 68.5 → **79.5프레임**). 백엔드 **2367 → 2374 passed**(3 skipped 불변).
  **캘리브레이션 1.033x·20/25 → 1.044x·19/25, MG 평균 1.125x → 1.176x(n=5).**
  **캘리가 나빠지는 것이 의도한 결과다** — 크라운은 1.341x인데 램프를 통째로 제거해도
  1.345x였고, 콜드 램프의 과청구가 램프와 무관한 MG 과대항을 우연히 상쇄해 평균을
  눌러 주고 있었다. 상쇄를 걷었으니 **다음 표적은 크라운 1.351x**다. 미하라는
  재장전 1.906초가 감쇠보다 길어 0.902 → 0.900으로 사실상 불변 — 이 배선이 물리는
  곳만 문다는 대조군이다.
  설계: `docs/superpowers/specs/2026-08-14-mg-ramp-curve-and-retention-design.md`,
  계획: `docs/superpowers/plans/2026-08-14-mg-ramp-curve-and-retention.md`.
- **Pattern B 완전 해소 + Hero Vision 인코딩 (2026-08-14, 브랜치
  `worktree-pattern-b-hero-vision`).** 갭 인벤토리 4순위 「시간감쇠 게이지·다중소스
  스택 — 5슬러그」에 착수하려고 다섯의 **원문을 열어** 코드와 대조하니, 그건 한 갭이
  아니라 **서로 다른 네 가지**였고 **다섯 중 엔진 갭이었던 것은 하나도 없었다.** 다중소스
  fill(`_fill_sources`)·fill별 개별 만료(`ResourceBuff.lifetime`)·cap·reset은 엔진에
  **이미 다 있었다** — [[stale-defers-need-the-catalog-not-the-docstring]]의 네 번째 사례.
  - **`neon-vision-eye` — 갭 아님.** 화력 게이지를 원문 그대로 시뮬레이션하면 Fienn의
    1·4·7이 재현되고(6덱), 원문의 「+1」 애매함은 **두 해석 모두 같은 답**을 낸다.
    주기가 2로 떨어지려면 10초 창에 27발(2.7발/초)이 필요한데 그녀는 0.99~1.06발/초라
    **구조적으로 잠겨 있다.** 독스트링의 보류 사유(「+1의 간격을 모른다」)를 산수로 교체.
  - **`phantom`(베이스) — 갭 아님, 스킬의 데드락.** 못 쏘는 불릿엔 되찾을 딜이 없다.
  - **`laplace`·`laplace-signature` — 기존 프리미티브로 해소.** Hero Vision을
    `ResourceSpec`으로 인코딩(신규 fill 종류 하나: `per_shot_every_outside_own_status_window`
    — 변신 중 Buster 틱이 `shot_times`에 평타와 똑같이 들어가서 안 걸러내면 게이지가
    자기를 채운다). 11.9% 트루뎀 라이더를 `resource_gate`로 배선.
    **베이스는 322틱 중 0틱 열린다**(cap엔 1.00발/초 필요, 그녀는 0.68) — 값은 예전
    보류와 같은 0이지만 **유도된 0**이다. **시그니처의 「상시 맥스스택」 가정(2026-07-19)은
    철회**: fill이 변신 10초 동안 멈춰 613틱 중 **506틱(82.5%)**만 열린다.
  - **`phantom-signature` — 갭 아님(2026-08-14 추가 판정).** 대거를 지으라는 승인까지
    받았는데, 설계문서 직전에 walk를 실제 발사 시각에 돌려 보니 **인코딩된 60발 상수가
    근사가 아니라 정확값**이었다 — 베이스를 1스택에 못 박는 대칭이 이 빌드 소스 1에도
    그대로 걸려 애장품의 30발 메트로놈만 누적된다(**30 × (3−1) = 60**, 발사율
    6.1~40발/초 전 구간 불변). **짓지 않는 것이 옳은 결론이 됐다** — 지었다면 딜이
    0.00% 움직였다. 앞서 보고한 「저 한 자리 값어치」는 **철회**(두 시계가 같은 시계임을
    못 본 계산). 남는 보류는 **명중률 하나**(1스택 vs 실제 평균 1.48)이고 그건
    `core_diameter_px` opt-in이라 제품 보스 **0/6**에서 inert다.
  - **검증:** 백엔드 **2328 passed / 3 skipped**(테스트 +6, 삭제 0) · 스윕
    **101 중 1개만 변화**(`laplace-signature` −0.86%; 베이스는 새 빌더가 붙고도 0.00%로
    게이트가 닫힌 증거) · 실기록 캘리 **1.036x · 20/25 불변**(두 빌드 다 실기록 5덱에
    없다). 세 변이(fill 종류 두 가지 오답 + 게이트 상시개방)를 직접 넣어 각각 다른
    빨강이 나오는 것을 확인했다.
  - **남긴 것:** 세그먼트의 트루뎀 **타이핑**은 게이트 못 한다 — 프로필의 `damage_type`은
    세그먼트를 지을 때 고정되는데 그건 발사 타임라인을 만드는 **도중**이라 읽을 자원이
    아직 없다. 남기는 비용 약 0.6%(잰 값). **주의: 스윕 보스는 `enemy_def` 0이라
    트루뎀 타이핑을 재면 언제나 0이 나온다** — 이 항의 수치는 실기록 DEF로 잰 것이다.
- **애니힐리오 코어 지름 실측 — 갭 인벤토리 1순위 해소 (2026-08-14).** Fienn이 전투 중
  코어를 쟀다: 한 화면에서 무버프 SMG 조준원 90px · 코어 40px → 비율로 **48.89**
  (`raid_record.CORE_DIAMETER_PX`). **코드는 손댈 것이 없었고** — `accuracy.core_hit_rate`
  경로는 2026-08-07부터 있었다 — `RECORD_BOSS`에 상수 한 줄이 들어갔다. 기준선
  **백엔드 2299 passed / 3 skipped**, 캘리 **1.065x·16/25 → 1.036x·20/25**.
  - **움직인 무기군은 SMG(1.186x→0.997x)와 AR(1.094x→0.958x) 둘뿐이다.** 탄착군 10인
    MG·SR·RL은 코어 48.89 앞에서 구조적으로 p=1.0이라, 전원 RL/SR/MG인 **덱1은 1.034x
    그대로** 미동이 없다. 손댈 수 없는 덱이 손대지지 않은 것이 배선의 확인이다.
  - **단일 값 하나가 두 무기군을 동시에 1.0 근처로 옮겼다.** 「AR 67 · SMG 95로 서로
    달라 단일 값으로는 못 맞춘다」(2026-08-07)는 철회된다 — 코어가 달라서가 아니라
    그 뒤의 엔진 작업들이 무기군별 잔차를 줄여서다.
  - **`sim/record`가 재는 것이 바뀌었다.** 켜진 항은 `p_탄착`뿐이고 균등 원판은
    조준하지 않았을 때의 값이라 상한이 아니라 **하한**에 가깝다. 남은 `p_조준`은
    gap #21 그대로고, SMG 0.997·AR 0.958이 그 크기를 위에서 눌러 준다.
  - 판독 ±1px(47.14~50.67)에서 1.035~1.037x·20/25로 사실상 불변.
    `docs/measurements/annihilio-core-diameter.md`.
- **페르소나 콜라보 온보딩 (2026-08-13)**: 퀸(마코토 니지마) `queen-makoto-nijima`
  · 유키코 `yukiko-amagi`. `ENCODED_SLUGS` 101→**103**. 기준선 **백엔드 2252 passed ·
  프론트 880 passed / 73 files · 타입에러 0**. 아이기스(872)는 SR이라 대상 외.
  이 배치가 남긴 것 넷:
  - **아군 버스트에 반응하는 즉발 넉이 이제 된다.** `on_tier_fire`가
    `drain_instant_damage`를 `ally_burst_activate` **앞에서** 부르고 있어서, 반응
    넉의 펄스가 그 자리에서 안 빠지고 풀버스트 진입까지 적립됐다 — 히트가 반응한
    버스트에서 떨어져 나갈 뿐 아니라 그 창의 보너스까지 받았다(테스트 3000→4500).
    배출을 두 트리거 뒤로 옮겼고, 기존 101슬러그 출력은 불변이다.
  - **`truncate_open_ended`가 불릿 이름을 받는다.** 한 유닛이 같은 스탯에 계속형
    버프를 둘 들고 나중 트리거가 하나만 끝내는 경우가 처음 나왔다(퀸의 Nuke Boost
    영구 / Nuke Amp 풀버스트 종료까지, 둘 다 Elemental Advantage). 기존 동작은
    영구 쪽까지 지웠다. `add_refreshing`이 이미 같은 이유로 쓰는 `refresh_group`을
    선택 인자로 받는다.
  - **콜라보 「상태」는 시뮬이 추적하는 status가 아니라 명단이다.** 「페르소나 상태의
    standard Burst 3 아군」은 아무도 주거나 뺏지 않으므로 `PERSONA_STATE_SLUGS`
    명단 + `burst_tier`로 정확히 해소된다(squad 근사 불필요). 실질적으로 둘이
    서로 전용이고, 한쪽만 있는 덱에서는 대상이 0명이다.
  - **원소 조건 하나가 킷의 절반을 건다.** 「1 More」는 버스트가 Wind 보스에게만
    **자신에게** 주는 버프라(원문 `Affects self`), 거기 매달린 니크·전달·ATK가
    전부 `boss_is_element("Wind")` 뒤에 있다. 우위가 없는 보스에서 두 유닛의
    추천 순위가 낮게 나오는 건 버그가 아니다.
- **6인 인코딩 배치 (2026-08-08)**: 도라 · 델타: 닌자 시프 · 레오나 · 나가 ·
  은화: 택티컬 업 · 엠마: 택티컬 업. `ENCODED_SLUGS` 95→**101**.
  기준선 **백엔드 2134 passed / 3 skipped · 프론트 626 passed · 타입에러 0**.
  이 배치가 남긴 것 셋:
  - **「같은 스쿼드」는 근사하지 않아도 된다.** 은화TU/엠마TU의 포메이션 버프가
    노리는 Absolute 스쿼드는 ELYSION SSR 43개 번들을 받아보니 Emma·Eunhwa·Vesti의
    기본형+TU **6명뿐**이고, 그중 인코딩된 건 이 둘이다. 그래서 `squad` 근사가
    아니라 `ABSOLUTE_SQUAD_SLUGS` + `member_subset_buff_rule`로 **정확히** 들어갔다.
  - **레오나 Roar에서 레이븐 판정이 다시 결론을 뒤집었다.** 「stacks up to 5 ...
    lasts 5 sec」를 개별 스택 만료로 읽으면 2스택에 묶여 버스트의 최대스택 게이트가
    영영 안 열린다. 그녀의 채움 간격(3.33~4.98초)이 5초를 못 넘긴다는 걸 실제
    케이던스로 확인해 영구 누적으로 넣었다 — 약 19초부터 5스택 고정.
  - **`provider_scan`의 힐 패턴이 소수점을 문장 끝으로 읽고 있었다.** `[^.]*`라
    「Recovers 9.58% ... as HP」가 "Recovers 9"에서 끊긴다. 기존 95슬러그는 전부
    「Restores HP equal to ...」 형식이라 우연히 걸리고 있었고, 나가가 처음으로
    드러냈다. 고친 뒤 잃은 슬러그 0.
- **한글 표시 이름은 이제 받아 온다 (2026-08-08).** ShiftyPad가 캐릭터 목록을
  **로케일마다 따로** 서빙한다 — 인터셉트로 잡히던 건 영문판이었을 뿐이고, 한국
  서버 공식 표기는 `/character/ko/nikke_list_v2.json`에 196개 전부 있다. 위 6인이
  마지막 빈칸이었고, 채우고 나니 **인코딩 101슬러그 중 영문 폴백 0건**.
  `dolla`가 "돌라"가 아니라 **"도라"**여서, 음차로 유추했으면 틀렸을 자리다.
  `tools/collect-blablalink/korean-names.js`가 이 목록을 받아
  `nikke-directory.json`의 `name_ko`로 넣고(브라우저·세션 불필요),
  `test_every_encoded_slug_is_named_in_korean`이 빈칸을 잡으면서 **실패 메시지로
  공식 표기를 알려준다**. 인코딩 스킬의 12단계로 편입.
- **회차 보스 카드 다듬기**(Fienn 요청): 카드에서 공지 원문 표시를 걷어내
  **이름과 약점 아이콘만** 남기고, 카드 아래 문단이던 안내는 「보스 설정」 옆
  **툴팁**으로 옮겼다(5장 밑에 깔려 정작 읽어야 할 때 안 읽혔다). 그리고 유니온
  공지의 **거리를 자동 입력**으로 승격 — `stated`의 한글을 앱이 파싱하는 대신
  `weakness`와 같은 방식으로 `range_band`(`near`/`mid`/`far`) 필드를 두고 판독
  시점에 스킬이 채운다. 자동으로 채워지는 값은 이제 **약점 + 적정거리 둘**이고,
  거리를 안 적는 솔로 공지에서는 적정거리가 「모름」으로 남는다. 게임의 「거리」가
  우리 3단계 밴드와 같은 분류인지는 **여전히 미확인**이며(관측값은 근/원 둘뿐),
  「중거리」가 적힌 회차가 그 첫 증거가 된다. 기준선 **백엔드 2034 passed /
  3 skipped · 프론트 601 passed**, 캘리 불변(엔진 로직 미변경).
- **명중률 → 탄착군 → 코어히트율 착륙** (트렁크 병합 `e1167637`): 코어 히트가
  불리언에서 확률이 됐다. 탄착군 `D = 기본직경 × max(0, 1 − 명중/1.10)`,
  코어히트율 `p = 1.0 if D ≤ 코어 else (코어/D)²`. **opt-in** —
  `BossProfile.core_diameter_px`를 안 주면 예전 상한 그대로라 실기록은 안 움직인다.
  기준선 **백엔드 2031 passed / 3 skipped · 프론트 598 passed**, 캘리
  **1.047x · 19/25 불변**. 움직이는 무기는 SG·SMG·AR뿐이고 MG·SR·RL은 기본 탄착군
  10px가 이미 코어 안이라 실질 항상 1.0이다.
  **명중률 오버로드는 값까지 확정됐다 (2026-08-07 재수집).** 효과 타입은 **6**,
  곡선은 **type 8과 동일**(lv1 4.77 … lv15 14.63, 등차 0.704). 34유닛의
  `option_id`와 스크래이프 합계가 완전히 대응하고, 다중 굴림 8건이 전부
  맞는다(Tia `lv[4,11,11]` → 30.50). 재현: `scripts/fit_overload_curve.py`.
  `base_stat_folded`는 **틀린 이름이었다** — 6도 13도 Equipment Effects 목록에
  멀쩡히 있고, 파서가 버린 뒤의 결과로 fit해서 그 이름이 붙었다. 이제
  `unconsumed_effect_types = [13]`(DEF만)이다.
  **재인코딩 완료 (2026-08-07).** 15유닛 19슬러그 전량이 이제 `hit_rate` Effect를
  등록한다 — 아래 「명중률 착륙의 후속」 참고. 그리고 측정 스크립트가 읽는
  `roster-drafts.json`은 **앱에서 재동기화 후 localStorage에서 손으로 꺼내야**
  갱신된다(`RECIPE.md`의 export 절).
- **수집기가 조용히 죽어 있었다 — 라벨 개편 (2026-08-07 발견·복구).**
  ShiftyPad가 `Increase X`를 `Increased X`로, `Element Damage Dealt`를
  `Elemental Advantage Dmg`로 바꿨다. 매핑에 없는 라벨은 행을 **조용히 버리므로**
  라이브 `node collect.js`가 159유닛 전부 `overload: []`를 냈는데 `npm test`는
  초록이었다 — 픽스처가 7월 문구를 담고 있어서다. **픽스처만 있는 스위트는 페이지
  개편을 못 본다.** 두 철자를 다 매핑했고, 같은 유닛을 새 문구로 재캡처한
  `rapi-red-hood-relabelled` 픽스처가 둘이 같게 파싱되는지 지킨다. 잡아낸 것은
  `--details`(option id)와 스크래이프의 **불일치**였다.
  스펙: `docs/superpowers/specs/2026-08-07-hit-rate-core-accuracy-design.md`,
  플랜: `docs/superpowers/plans/2026-08-07-hit-rate-core-accuracy.md`.
- **레이드 회차 보스 가져오기 착륙**: 솔로/유니온 공지에서 읽은 이번 회차 보스를
  보스 설정 위에 카드로 띄운다. 판독은 `/update-raid-bosses` 스킬이 하고 앱에는
  OCR이 없다. **자동으로 채워지는 것은 약점 속성 하나**이고, 거리·스쿼드 추천·
  저지 부위는 공지 원문으로만 카드에 남는다(설계 D3 — 우리 플래그와 같은 분류인지
  미확인). 2026-07-28 고정 편성 평가 작업이 범위 밖으로 남겨둔 5속성 보스
  프리셋(보스별 부위파괴/코어피격 특성 데이터 미확보)은 **여전히 미확보다** —
  공지가 그 둘을 주지 않는다.
  스펙: `docs/superpowers/specs/2026-08-07-raid-boss-rotation-import-design.md`,
  플랜: `docs/superpowers/plans/2026-08-07-raid-boss-rotation-import.md`.
- 브랜치: `worktree-raid-boss-rotation-import` — 병합 전 최종 리뷰 수정 반영(카드의
  `<label>`이 공지 원문까지 감싸 접근성 이름이 문단 하나가 되고 원문 클릭이
  보스를 선택해 버리던 것을 머리글만 감싸도록 정정, 초기화 안내 문구 보강,
  `GET /api/raid-rotations` 계약 문서화, 빈 `bosses` 목록 거부 등). 기준선
  **백엔드 2001 passed / 3 skipped · 프론트 598 passed**, 캘리 **1.047x · 19/25
  불변**(엔진 로직은 건드리지 않았다). 백엔드 수치는 이 브랜치가 더한 17개와 같은
  날 트렁크에 들어온 머신건 스핀업 작업을 합친 값이다. (캘리 수치는 여기 처음
  적힐 때 1.079x·17/25로 적혔는데, 그건 그 머신건 작업 **이전** 값이다 —
  `measure_record_calibration.py`가 그때도 1.047x·19/25를 냈다.)
- 이전 기준선 (2026-07-16 ~ 08-06) — 상세는 `docs/decisions.md`·`insights.md`·
  `engine-gaps.md`·`encoded-nikkes.md`와 git 이력에 있다:

  | 날짜 | 기준선 | 착륙한 것 |
  |---|---|---|
  | 08-06 | 백 1944 · 캘리 1.079x·17/25 | 무기변형 창 재시전이 시뮬레이터를 죽이던 것 정정(나유타·타키나) |
  | 08-06 | 프론트 573 | 결과 화면 정리와 결과 보관 |
  | 08-05 | — | 소다 풀버스트 확장 · 사이클별 FB 길이 + 아르카나 게이트 정정 |
  | 08-03 | — | 보스 약점·속성저지·코어 2관통 (origin `f8ccf40`) |
  | 08-02 | — | 플랫 발수 장탄 · 배분 탐색 품질 · 창 폭 레이아웃 |
  | 08-01 | 프론트 464 | UI 다듬기 + 동기화 탭 분리 |
  | 07-28 | 백 1529 | 정체성/팬아웃 분리 |
  | 07-28 | 백 1513 · 프론트 380 | 아핀 재장전 · 차지 모션 딜레이 유닛별화 |
  | 07-26 | 프론트 294 | UI 크롬 한글화 |
  | 07-19 | 백 1413 | 로스터 동기화 |
  | 07-18 | 백 774 | 스킬 수치 드리프트 감지 |
  | 07-17 | 백 622 → 774 | 프론트 3단계 통합 · 매니페스트 배치 2 · EffectRegistry 성능 패스 · `POST /api/recommend-raid` · 매니페스트 예외 8유닛 · ProcessPool 병렬화 + Rapi · 검증 배치 + Ein · Raven·Sakura 인코딩 · Raven Shock Wave 정정 |
  | 07-16 | — | Phase C(갭 #3·#6) · Ark Ranger 브래킷 · Phase B 갭 #5 · 인코딩 60명 |

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
| Phase 3 | 캐릭터 스킬 인코딩 | 🔄 진행 중 (100명, `docs/encoded-nikkes.md` 표 기준) |
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
  지연(**mock은 2026-07-24에 삭제됨** — 아래 Phase 6 항목 참조).
  공유 조각 추출(useAsyncRequestStatus·DeckCard·ExcludedSlugsNote·
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
- **UI 시각적 완성도 4단계 완료 (2026-07-25):** 구조 개편(2탭·칩 축소·드래그앤드롭,
  트렁크 `501a26f`)에 이어 외형까지. spec:
  `docs/superpowers/specs/2026-07-25-ui-visual-completeness-design.md`.
  ① **덱 슬롯을 게임 스쿼드 슬롯처럼** — 정사각 얼굴 5칸 상시 표시(빈 칸은 `+`),
  이름 텍스트 제거·버스트 단계만 배지, **슬롯이 드래그 소스**라 덱 간 이동 가능
  (`moveUnit`; 정원 검사를 제거보다 **먼저** 해야 거부된 이동이 유닛을 삭제하지 않음).
  얼굴 크롭은 새 에셋 없이 CSS `object-position: center 18.75%` — lootandwaifus에
  정사각 변형은 없음(`si_`/`ci_`/`fi_`/`icon_`·`.png`·`/assets/nikke/` 전부 404).
  ② **다크 단일 테마** — 라이트 토큰·`prefers-color-scheme` 제거, 표면 3단 + 속성색 5종.
  ③ **Roster 탭 그리드** — 보유 159 중 엔진 지원 70만 카드, 나머지 89는 접힌 목록.
  이름은 `/api/supported-units`, 미지원은 `lib/unitName`이 슬러그에서 유도.
  ④ **결과 화면 초상화 로우** — 모노스페이스 슬러그 목록 → 얼굴 5개 + 이름.
  이어서 ⑤ **오버로드 표시 순서 고정**(우코·공·장탄·차속·크댐·크확·차댐, Fienn 지정;
  모르는 효과는 뒤에 붙고 들어온 순서 유지), ⑥ **돌파/코어 가시성** — 로스터는
  `[★★★ +4]` 단일 불투명 배지(별 금색), 팔레트 칩은 초상화 오른쪽 열을 **5칸**
  (돌파·코어·S1·S2·B)으로. 정직성 수정 2건: 낡은 헤더 문구(수기 입력 → 싱크 전용),
  팔레트 `159/159 in the search pool`(실제 칩 70개) → 보유∩지원 교집합 기준.
  **프론트 234 → 264 passed**, 백엔드 무변경. 결정·함정은 `decisions.md` /
  `insights.md`(Frontend) 참조.
- ~~React 폼으로 ShiftyPad 투자 데이터 수동 입력~~ → **철회**: 로스터는
  blablalink 싱크 전용, 수동 입력 폼은 코드/UI에서 제거됨(`decisions.md` 2026-07-23).
- FastAPI 엔드포인트로 엔진 노출. ✅ (`POST /api/recommend`, 2026-07-16 —
  스킬값 매니페스트 + 검증 하니스 + 로스터 로더 경유; 프론트는 Vite 프록시로 연결,
  `excluded_slugs` 표시). **`VITE_RECOMMEND_API` 스위치는 없어졌다** — dev mock을
  통째로 삭제해서 `src/api/`의 각 모듈이 곧 fetch 클라이언트다(2026-07-24).
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
        아니다** — 당시 A·B 모두 area **81**로 통과했다.
        이 함정으로 첫 조회가 `param invalid` 났다가, area 81로 고치니 통과.
        **⚠ 이때 적었던 "81 = 인터내셔널 서버"는 틀렸다(2026-07-29 정정).** 81은
        **일본**이다. 여기 적힌 A·B는 그 시점에 area 81 조회가 **성공**했을
        뿐 — 즉 두 계정 모두 그때 JP 서버에 로스터를 갖고 있었다는 뜻이지,
        그 계정이 "JP 전용"이라는 근거는 아니다. 한 계정이 서버마다 각각
        로스터를 가질 수 있음이 2026-07-29에 확인됐으므로(아래 서버 지원
        서브프로젝트), 이 결과는 애초에 81이 무엇을 뜻하는지에 대한 증거가
        아니었다. **여기 A·B는 2026-07-29 스펙
        (`docs/superpowers/specs/2026-07-29-sync-region-support-design.md`)의
        예시 표에 나오는 A·B와는 무관한 별개의 라벨** — 글자가 같은 것은
        우연이니 두 쌍을 같은 계정으로 읽지 말 것. 권위 목록은
        `GetRegionList`: 81 Japan · 82 NA · **83 Korea** · 84 Global · 85 SEA.
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
      저장 문제, 기존 "자격증명 저장 금지" 원칙과 충돌 소지 → 재결정) ·
      ③ **해결됨 (2026-07-29).** 타 리전 유저 `nikke_area_id` 발견/기본값 —
      권위 출처는 blablalink 자신의 `GetRegionList`(81 JP · 82 NA · 83 KR ·
      84 GL · 85 SEA); 값을 추측하거나 기본값 하나로 정하는 대신 앱이 다섯
      서버를 모두 조회하고, 로스터를 가진 서버가 둘 이상이면 유저에게
      물어본다 · ④ 정찰 당시 edenpj.com 502는 **서버 점검**(운영자 공지), 폐쇄 아님 —
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

### 오버로드 옵션 상세 모드 (2026-08-15)

- [x] **니케 풀 탭이 인게임 장비 화면을 되돌려 보여준다.** 필터 툴바 아래
      「오버로드 옵션 상세」 체크박스 하나로 탭 전체가 합계 줄 → 부위별 2×2 격자로
      바뀐다(좌상 머리·우상 몸통·좌하 팔·우하 다리, 부위마다 옵션 행 셋, 롤이 없는
      행은 `—`로 자리 유지). 이름은 요약의 축약(`우코`)이 아니라 인게임처럼
      `[우월코드 대미지]`. 강조는 인게임과 같이 **단계**로 — 15단계는 행 반전,
      12~14단계는 수치 강조(색 선택 근거는 `docs/decisions.md`). 선택은
      localStorage에 남는다. 백엔드가 롤마다 `level`·`index`를 싣게 됐다
      (`assemble_overload`). 백엔드 2410 → 2414 passed, 프론트 884 → 916 passed
      (73 files), 타입에러 0·lint 에러 0. Vite dev + FastAPI를 Playwright로 띄워
      실제 브라우저에서 네 경로(전체 롤 / 부분 롤 / 오버로드 없음 / 롤 없는 옛
      로스터) 모두 확인했다.
      **범위 밖(Fienn 결정):** 장비 아이콘·레벨 뱃지, 방어력(타입 13) 롤.
- [ ] **로스터 재동기화 필요 — 롤 단계·행 번호.** 재동기화 전 로스터에는 `level`·
      `index`가 없어 상세 모드가 그 카드만 요약 줄로 남고 「부위별로 보려면 로스터를
      다시 동기화해 주세요」를 단다. 아래 「명중률 오버로드 값 곡선」 항목과 **같은
      재동기화 한 번으로 함께 해결된다.**

### 덱 편성 조작·표기 9건 (2026-08-10)

- [x] **드래그 대신 클릭으로 덱을 짠다 — 9건 착륙.** 패키지 앱에서 WebView2가
      `dragstart`만 내고 드롭은 안 줘 드래그가 죽어 있던 것의 대체다. 니케 풀
      카드는 테두리 안 어디를 눌러도 제외가 토글되고, 팔레트 칩도 테두리 전체가
      표적이라 스킬레벨 칸을 눌러도 배치된다. 좌석은 눌러 들고, 다른 빈자리를
      누르면 이동, 찬 자리를 누르면 교환, 팔레트 유닛을 누르면 교체, 같은 자리를
      다시 누르면 제거, Esc로 취소. 유니온 덱은 보스 이름+약점 아이콘으로 부르고
      저장 이름 기본값은 덱별 약점 나열. 보스 설정은 접히고 오류가 있으면 스스로
      펼친다. 아홉 항목 전부 Vite dev 서버 + FastAPI 백엔드를 Playwright로 띄워
      실제 브라우저 렌더에서 확인했다(jsdom 아님). 프론트 719 → 774 passed
      (68 files), 타입에러 0.
      `docs/superpowers/specs/2026-08-10-deck-ux-batch-design.md`.
      Fienn의 원래 개선 메모 9번째(유니온 기대딜량에 레벨 400 보정 대신 실제
      스탯)는 스탯 모델과 그 검증이 따로 필요해 **범위 밖으로 남긴다** — 이
      스펙에서 그 자리에 대신 들어온 것이 보스 설정 접기다.
      **→ 그 9번째는 아래 「유니온레이드 레벨보정 해제」로 닫혔다(2026-08-11).**

### 화면 정리 6건 (2026-08-11)

Fienn의 사용 보고. 용어 셋은 라벨 교체이고, 나머지 셋은 화면 구조다.

- [x] **탭을 왼쪽 사이드바로 옮기고 접을 수 있게 했다.** 세로 스크롤이 화면 여러
      개 길어서 다른 탭으로 가려면 매번 맨 위로 올라가야 했다. 사이드바는
      `position: sticky`로 스크롤을 따라오고, 접으면 129 → 34px로 줄어 본문이
      95px를 가져간다(접힘은 localStorage에 남는다). 900px 이하에서는 예전처럼
      위에 눕는다.
      **함정 둘을 실제 브라우저에서 잡았다** — ① `hidden` 속성의 `display:none`은
      `.tabs`의 `display:flex`에 우선순위로 밀려, 접어도 자리를 그대로 차지했다.
      ② 미디어쿼리를 `.tabs--side` 정의보다 **앞에** 두었더니 특정도가 같아
      소스 순서에서 지고 좁은 화면에서 탭이 세로로 남았다. 둘 다 Vitest가
      `css: false`라 못 잡는 종류다.
- [x] **니케를 별명으로 찾는다.** 「홍련: 흑영」을 흑련으로, 「리틀 머메이드」를
      세이렌으로 부르는 식이다. 표는 `lib/nikkeAliases.ts`가 helpText와 같은
      규율로 관리하고, 이름과 같은 규칙(부분일치 + 초성)으로 본다.
      **표에는 화면에 뜨는 슬러그 104개를 전부 미리 적고 옆에 한글 이름을 주석**으로
      달았다 — Fienn은 배열만 채우면 되고, 빈 배열은 "아직 안 채움"을 뜻하며 그
      목록 자체가 무엇이 남았는지를 보여준다.
      **표가 낡는 것은 `backend/tests/test_nikke_aliases.py`가 막는다.** 기준을
      `ENCODED_SLUGS`가 아니라 `supported_units()`로 잡은 이유는, 모드 변형의
      base(브래디·신데렐라: 크리스탈 웨이브·디젤: 윈터 스위츠 셋)가 자신은
      인코딩되지 않았는데도 팔레트에 뜨기 때문이다. 줄을 하나 지워 보고 가드가
      `['crown']`을 짚으며 무엇을 해야 하는지까지 말하는 것을 확인했다.
      새 니케 인코딩 시 이 줄을 추가하는 일은 `nikke-skill-encoding` 13단계와
      `onboard-new-nikkes` Phase 2에 넣었다 — 문서만으로는 잊히므로 테스트가
      같은 것을 강제한다.
      **Fienn이 49개를 채웠다**(빵순이·흑련·백설·공룡·수렐루…). 그러면서
      「한 별명이 두 니케를 가리키면 안 된다」는 내 가드가 **틀렸다는 것이
      드러났다** — `-signature`와 모드 변형은 같은 니케의 다른 빌드라 별명이
      겹치는 것이 정상이다(브래디 셋이 다 「빵순이」). 그 관계는
      `MODE_VARIANTS`를 아는 백엔드에서만 판정할 수 있어 검사를 그쪽으로 옮기고,
      가족 판정(`_family`)을 통과시키는 관대함이 아무것이나 통과시키는 수준이
      아님을 별도 테스트로 고정했다. 실제 앱에서 여섯 질의(초성 `ㅃㅅㅇ` 포함)가
      전부 1기로 좁혀지는 것을 확인했다.
- [x] **「아직 미지원(탐색에서 제외됨)」을 결과 화면에서 뺐다.** 니케 풀 탭이
      이미 같은 사실을 말하고 있어, 결과마다 뜨는 배경 소음이었다.
      `ExcludedSlugsNote`와 그 문구를 지우고 소비처 다섯을 정리했다 — 타입이
      호출부를 전부 지목해 줬다.
- [x] **편성 방법을 「사용 방법」 박스로 접었다.** 접힘 36px, 펼침 134px.
      접힌 상태에서는 박스가 곧 summary라 아무 데나 눌러도 열리고, 내용까지
      토글 대상으로 삼지는 않았다 — 읽는 문단이라 클릭을 먹으면 드래그해 읽을
      수가 없다.
- [x] **용어 정리:** 「코어 피격 가능」 → **코어 타격 가능**, 「기준자 무기」 →
      **탄착군 측정한 무기**(드롭다운은 무기군만 표기), 「탄환 환급」 →
      **탄환 충전**. helpText 쪽 문구는 Fienn이 직접 다듬었다.
- [x] **코어 지름은 유저가 넣을 일이 없다(확인).** 회차 보스 데이터에
      `core_diameter_px`가 이미 있고 `BossProfileField`가 회차 선택 시 그 값을
      채우며 「코어 타격 가능」도 함께 켠다. 다만 `raid-rotations.json`의 값이
      아직 전부 `null`이라, 남은 일은 **측정값을 회차 데이터에 넣는 것**이다.
      입력칸과 측정 계산기는 그 값을 만드는 도구 + 회차에 없는 보스용 탈출구로
      남는다.
      프론트 818 → **829 passed**, 타입에러 0.

### 차속 사다리가 답이 바뀌는 행만 낸다 (2026-08-11)

- [x] **5.56% 단위는 자의적 눈금이 아니다 — 프레임 격자다.** Fienn 질문에 대한
      답: 차지 시간은 정수 프레임으로 떨어지므로 0.30초 차지는 18프레임이고,
      차지속도는 1/18 = 5.56% 단위로만 프레임 수를 바꾼다. 그 사이 값은 아무
      수치도 안 바꾼다(`charge_window.charge_speed_steps`).
- [x] **그러나 사다리는 답이 안 바뀌는 행을 내고 있었다.** `thresholds()`가
      「간격이 바뀌는 행」을 냈는데, 탄창이 상한이면 프레임을 사도 발이 늘지
      않는다. 판정을 **답(타수 + 화면에 적히는 정수 퍼센트 확률)** 기준으로
      바꿨다. 실측: 스칼렛 5 → **2행**, 리버렐리오 21 → **16행**, 네온은
      15 → 15행(거기선 매 행이 실제로 다른 답이라 하나도 안 지워진다).
      확률만 오르는 행은 남는다 — 「7발 확률 3%→94%」는 살지 말지의 재료다.
- [x] **그 변경이 마감 문구를 거짓말로 만들어 함께 고쳤다.** 사다리가 일찍
      끝나면 화면이 "오버로드 상한 24%까지만 보여줍니다"라고 적었는데, 상한은
      멀쩡히 남았고 답이 먼저 멈춘 것이었다. 행 목록만으로는 두 경우를 구분할 수
      없어(격자 간격을 알아야 한다) 백엔드가 이유를 실어준다 —
      `ladder_stopped_by: "answer" | "ceiling" | "charge"`.
- [x] **큐브 2종을 확인했다(Fienn 지적).** 실제 브라우저에서 스칼렛으로:
      렐릭 베어는 **1행(18타 고정) + "더 올려도 결과가 같습니다"**, 택티컬
      베어는 **5행(19→22타)**. 탄환 환급이 없으면 차속이 아무것도 못 사고,
      껴야 값을 한다. 테스트도 두 큐브로 각각 돈다.
- [x] **차지속도 합산 규칙 검증(Fienn 요청).** 화면의 「현재 차지속도」는
      `charge_speed_percent_from_lines`(같은 굴림값끼리 합산 → 그룹별 정수
      반올림)를 거친 값이 맞다. 실계정 대조: 네온 굴림 [2.28, 2.86, 4.33] →
      단순합 9.47%가 아니라 **9%**, 리버렐리오 [6.09] → **6%**, API 보고와
      일치. 셋 다 "합계에서 추정" 노트가 안 뜬다 = 재동기화로 부위별 굴림이
      실려 와 추정이 아니라 굴림으로 계산했다는 뜻이다.
      백엔드 2201 → **2209 passed**(3 skipped), 프론트 817 → **818 passed**.

### 결과 카드에서 덱 5명이 4+1로 접혔다 (2026-08-11)

- [x] **트랙 최소폭을 「다섯 얼굴이 한 줄에 선다」에서 거꾸로 계산한다.**
      `.deck-results`가 `minmax(340px, 1fr)`이었는데 한 줄에 필요한 폭은
      유닛 5×64 + 간격 4×12 = 368px, 여기에 카드 좌우 padding 32 + 테두리 2를
      더해 **402px**이다. 그래서 카드가 341~399px로 잡히는 폭에서만 마지막 한
      명이 다음 줄로 내려갔다 — 유니온 3덱처럼 카드가 여러 열로 설 때 딱 그
      구간에 들어간다. 매직넘버 대신 `--deck-unit`에서 계산하는 식으로 바꿔
      유닛 폭·간격이 바뀌면 따라오게 했다.
      **Vitest는 `css: false`라 이 결함을 못 잡는다** — 실제 브라우저에서
      컨테이너 폭 900·1164·1200·1400·1600·2000px으로 재서 수정 전 전부
      2줄이던 것이 수정 후 전부 1줄이 되는 것을 확인했다. Fienn 보고(2026-08-11).

### 코어 지름 칸이 자기 계산기가 채운 값을 거부했다 (2026-08-11)

- [x] **코어 지름 입력에 `step="any"`.** 「화면에서 재서 넣기」가 `toFixed(2)`로
      87.50 같은 값을 채우는데 그 칸만 `step`을 안 넘겨 HTML 기본값(정수)이
      되어 있었다. 제출하면 브라우저가 "유효한 값을 입력해주세요. 가장 근접한
      유효 값 2개는 87 및 88입니다"로 막았다 — 폼이 자기 계산기가 넣은 값을
      거부한 것이다. 백엔드는 처음부터 `core_diameter_px: float | None`을 받고
      있었다. `NumberField`의 `step`은 이제 `number | 'any'`다.
      전수 점검 결과 다른 칸은 멀쩡하다(차지 윈도우 계산기는 이미 `step={0.01}`,
      픽셀·방어력·전투시간은 정수가 맞다). 프론트 815 → **817 passed**.
      jsdom이 `validity.stepMismatch`를 실제로 구현해 테스트가 이 오류를 그대로
      재현하고, 실제 Chromium에서도 확인했다. Fienn 보고(2026-08-11).

### 유니온레이드 레벨보정 해제 (2026-08-11)

- [x] **유니온이 싱크로 레벨 스탯으로 잰다 — 레벨 400 보정은 솔로만의 규칙이다.**
      Fienn: "솔로레이드는 4가지 모드 모두 레벨400 보정을 해야 하고,
      유니온레이드는 레벨 보정 시스템 자체가 없어." 조립기가 유닛마다 스탯 두
      벌(`raid400` + `actual`)을 내고, 요청의 `stat_basis`가 어느 벌로 잴지
      정한다. 실제 스탯이 없으면 422로 거절하고 유니온 탭이 제출을 막는다 —
      400 값으로 폴백하지 않는다.
      **싱크로 레벨은 유도하지 않는다.** `GetUserProfileOutpostInfo`의
      `outpost_info.synchro_level`을 그대로 읽는다(668). 우리는 그 응답에서
      `recycle_room_researches` 하나만 꺼내고 아홉을 버리고 있었다 — Fienn의
      "확인을 해보는 게 좋겠어" 한 줄이 `max(보유 lv)` 유도와 그 한계 문단을
      통째로 지웠다. 옆 필드 `synchro_nonempty_slot_count`(136)가 같은 계정에서
      lv 668인 니케 수 136과 정확히 일치해 서로를 확증한다.
      **`/api/evaluate-decks`는 솔로와 유니온이 공유한다** — 솔로 탭의 네 모드
      중 `evaluate`가 같은 엔드포인트를 부른다. 엔드포인트에 정책을 걸었다면
      솔로 결과가 3배로 부풀었을 것이고, 이 사실은 구현 중 **타입 검사가**
      잡아냈다(설계 초안은 "유니온만 쓴다"고 잘못 적고 있었다).
      **북마크릿은 재설치해야 켜진다** — 설치 시점 소스가 박제되므로 앱을 새로
      빌드해도 안 바뀐다. 안내 문구가 그것까지 말한다.
      실측(159유닛 실계정, 라이브 백엔드): ATK 비율 min 2.786 · median 3.098 ·
      max 3.399, 같은 덱이 5,497,579,377 → 17,040,033,395 = **3.100배**.
      `/api/recommend` 기본값은 evaluate의 raid400과 딜이 정확히 일치(솔로 불변).
      백엔드 2194 → **2201 passed**(3 skipped), 프론트 810 → **815 passed**
      (69 files), 타입에러 0, lint exit 0. Vite dev + FastAPI를 Playwright로
      띄워 실제 브라우저에서 확인했다: 옛 북마크릿 payload면 안내가 뜨고 버튼이
      죽고, 싱크로 레벨을 실은 payload로 재동기화하면 안내가 사라지며 나가는
      요청 본문에 `stat_basis: 'actual'`과 `actual_atk`가 실린다.
      `docs/superpowers/specs/2026-08-11-union-raid-actual-stats-design.md`,
      `docs/superpowers/plans/2026-08-11-union-raid-actual-stats.md`.
      **남은 것:** 실기록 캘리브레이션(그때 1.060x·18/25)은 솔로 기록으로 잰
      상수라, 유니온 실제 스탯에서 유효한지는 이 작업이 답하지 않는다.

### 편성 전체 초기화·저장 결과 가져오기 (2026-08-12)

- [x] **액션 행에 버튼 둘을 더했다 — 편성 칸이 있는 세 화면 전부.** 솔로의
      「빈자리만 최적화」·「기대 딜량 계산」과 유니온 레이드에 `[인카운터!]
      [결과 가져오기] ……… [초기화]`가 선다. **초기화**는 편성만 비운다 —
      보스 설정도 덱 개수도 모드도 건드리지 않고, 확인을 한 번 묻는다.
      **가져오기**는 이름 붙여 남겨 둔 결과의 **결과 덱**을 편성 칸에 앉히고
      그때의 보스·덱 개수를 함께 적용한다(편성에 이미 뭔가 있으면 덮어쓸지
      묻는다). 기존 「이 설정으로 폼 채우기」와 다른 일이다 — 저쪽은 설정만
      되돌리고 결과는 두는 것이고, 이쪽은 최적화가 뽑아 준 덱 구성 자체를
      편집기로 옮겨 한두 명만 바꿔 다시 돌리게 한다.
      **단일 덱 결과만 규칙이 다르다**: 그것은 배분이 아니라 한 덱의 대안
      랭킹이라 덱들이 니케를 공유하므로, 1위 덱만 덱 1에 앉히고 덱 개수는
      건드리지 않는다. 좌석은 전부 잠기지 않은 채로 들어온다 — 가져온 편성은
      「여기서 출발」이지 「이 자리를 고정」이 아니다(Fienn 지정).
      지금 로스터에 없거나 니케 풀 탭에서 미사용으로 돌린 니케는 **자리를
      비운 채** 가져오고 몇 기가 빠졌는지 말한다 — 「제외는 덱에서도 제출
      로스터에서도 빠진다」는 앱의 기존 불변식을 가져오기가 우회하면 안 되기
      때문이다. 프론트 828 → 857 passed (73 files), 타입에러 0, lint exit 0.
      `docs/superpowers/specs/2026-08-12-deck-clear-and-import-design.md`,
      `docs/superpowers/plans/2026-08-12-deck-clear-and-import.md`.
      **라벨은 실제 화면이 정했다.** 계획의 「저장한 결과 가져오기」·「전체
      초기화」로는 세 버튼 합계가 416px이라 384px짜리 sticky 덱 컬럼에서
      초기화가 둘째 줄로 밀렸다. Vitest는 CSS를 보지 않아 스위트는 초록인
      채였고, Playwright로 띄워 재고 나서야 드러났다. 빨강 채움 버튼이
      비활성일 때도 그대로 빨갛던 것(`.btn:disabled`가 이 앱에 없다)도 같은
      자리에서 나왔다.
      **남은 것:** 화면에 지금 떠 있는 결과에서 바로 편성으로 가져오는 길은
      없다(저장한 결과만). 미란다 계산기 화면은 범위 밖 — 그 화면에는 저장한
      결과라는 개념이 없다.
- [x] **편성을 되돌리는 세 경로 전부가 미사용 니케를 존중한다 (2026-08-12).**
      「제외는 덱에서도 제출 로스터에서도 빠진다」는 앱의 불변식을 가져오기만
      지키고 있었다. 나머지 셋 — 솔로·유니온의 「이 설정으로 폼 채우기」와,
      계정을 열 때 마지막 제출을 되돌리는 이펙트 — 은 저장된 편성을 날것으로
      앉혔다. 그러면 덱에는 있고 제출 로스터에는 없는 니케가 생기고, 실행하면
      백엔드가 **「엔진이 쓸 수 없는 슬러그예요」**로 답한다(`api.py`가 `by_slug`를
      제출된 로스터에서 만든다) — 유저는 그저 미사용으로 돌렸을 뿐인데.
      `lib/importRun.ts`에 `seatableOnly`를 더해 세 경로가 같은 판정을 통과한
      좌석만 되돌린다. 잠금은 보존한다(되돌리기의 뜻이 「그때 그대로」다).
      빠진 수는 가져오기와 같은 안내로 말한다.
      **계정 복원 경로는 마운트만 보면 안전해 보인다** — 미사용 니케를 빼는
      이펙트가 그때 함께 돌기 때문이다. 실제로 새는 것은 engineVersion이 한 박자
      늦게 도착해 복원이 **다시** 돌 때이고(실사용에서는 늘 그렇다), 그 두 번째
      실행에는 빼는 이펙트가 따라붙지 않는다. 첫 테스트가 그냥 통과해서 드러났다.
      프론트 873 → 879 passed, 타입에러 0, lint exit 0. 세 수정 모두 가드를 떼서
      빨개지는 것을 확인했고, 실제 앱에서 벤치된 니케가 안 앉는 것까지 봤다.
- [x] **「폼 채우기」가 유저가 짰던 덱 수를 지킨다 (2026-08-12).** 빈자리만
      최적화 보관물은 `numDecks`에 **엔진이 낸 덱 수**를 담고(`displayResult.decks.length`)
      `draft`에는 **유저가 제출한 편성 전부**를 담는데, 백엔드는 로스터가 못 채우면
      요청보다 적은 덱을 돌려준다. 되돌릴 때 덱 수를 결과 쪽에 맞추면 `resizeDraft`
      이펙트가 뒤 덱을 잘라 유저가 짰던 편성이 말없이 사라졌다. 되돌리기의 뜻은
      「그때의 **설정**으로」이고 그때 유저가 짠 것은 그 덱들이므로, 둘 중 넓은 쪽에
      맞춘다 — 같은 화면의 「가져오기」가 이미 쓰던 처리다. 프론트 880 passed.

### 덱 편성 조작 2차 5건 (2026-08-11)

- [x] **표적을 넓히고 자동 전환을 붙였다 — 5건 착륙.** Fienn의 사용 보고
      다섯 가지다. ① 팔레트가 활성 덱부터 앞으로 훑어 빈자리 있는 첫 덱에
      앉히고(끝나면 처음으로 되돌아감), 앉힌 직후로 다시 훑어 활성 표시를
      옮긴다 — 15명을 누르면 덱 3개가 차고, 표시는 5·10번째 클릭에서 넘어간다.
      ② ③ 덱 테두리 안 전체가 표적이 됐다: 든 것이 있으면 이동(그 덱이 활성
      덱이 된다), 없으면 선택. ④ 이름 검색이 초성(`ㅎㄹ`→헬름)과
      영문(`crown`, `ada wong`)도 받는다 — 슬러그가 곧 케밥케이스 영문명이고
      `backend/tests/test_resource_id_directory.py`가 그걸 고정하고 있어
      백엔드 변경이 0줄이다. ⑤ 미란다 계산기에 `onHeldSlugChange` 배선이
      빠져 있어 꽉 찬 덱에서 교환이 안 되던 버그를 고쳤다.
      프론트 778 → 810 passed (69 files), 타입에러 0, lint exit 0.
      다섯 항목 전부 Vite dev + FastAPI를 Playwright로 띄워 실제 브라우저에서
      확인했다. `docs/superpowers/specs/2026-08-11-deck-ux-batch-2-design.md`,
      `docs/superpowers/plans/2026-08-11-deck-ux-batch-2.md`.
      **④는 2026-07-28 스펙(`2026-07-28-roster-search-filter-design.md` §2)이
      "Fienn 지정"으로 기각했던 것을 뒤집은 결정이다** — 자모 유틸 25줄 말고는
      새 비용이 없다는 것이 근거.

### 미란다 계산기 (2026-08-08)

- [x] 미란다 계산기 — 덱 5인 중 누가 파워업!·웨이크업!3을 받는지, 받으려면 오버로드 공격력이 얼마나 필요한지 (2026-08-08)

### 스탯 모델 (2026-08-07)

- [x] **코어 스텝은 「장비 윗줄 전부」에 곱해진다 — 적합 상수 11개 삭제.**
      수집기 대조가 159유닛 중 ATK 75건·HP 79건에서 어긋난 것을 파다가, 코어당
      상수(`CORE_FLAT_ATK`/`_PILGRIM`/`CORE_FLAT_HP`)가 사실 **계정 연구 항의 2%**를
      재고 있었음이 드러났다. PILGRIM 「코어당 +10」은 그 기업 연구 랭크가 20 높은
      것(20×25×0.02), 「게임이 +2 올렸다」는 계정이 4랭크 더 연구한 것, 내가 한때
      만든 「TETRA 행」은 tid 1203만 1랭크 더 오른 것이었다. Fienn의 질문
      (「테트라만 계산방식이 다른 건 납득이 안 된다. 기업/클래스 콘솔 레벨을
      고려했어?」)이 이것을 지목했다. 새 모델:
      `floor(base*(1+0.02g) + g*grade_stat + 호감도 + 연구) * (1+0.02c) + 장비류`.
      **적합 상수 0개**로 159/159가 오차 0.5 이내(ATK·HP, 레벨 400·실제 레벨 모두).
      `math.floor`는 실측이다 — 없으면 15유닛이 최대 1.4 빗나가고 어떤 상수로도
      못 고친다. `scripts/solve_core_flat.py`(그 표를 푸는 도구)도 삭제했다.
- [x] **소장품 레벨 0은 스탯도 낸다 — 2026-07-27 결론을 뒤집었다.** 레벨 0 보유
      31유닛이 커브 index 0(SR 3,029 · R 638)을 요구한다. 리터의 인게임 값이 스크랩과
      일치하는 것으로 확정(Fienn). 스킬 축은 그대로 유효 — 이제 두 축이 같은 규칙을
      따른다. 착용 여부 판별자는 여전히 **tid**이고, `favorite_item_lv`로 판정하던
      테스트 둘을 고쳤다.
- [x] **로스터 재수집 시 ground truth 픽스처도 갱신할 것**
      (`python scripts/build_stat_ground_truth.py`). 이번 결함이 드러난 경위가
      그것을 빠뜨려 두 테스트가 서로 다른 게임 버전을 검증한 것이었다.

### 명중률 착륙의 후속 (2026-08-07)

- [x] **15유닛 19슬러그 재인코딩 완료 (2026-08-07, `wip/hit-rate-encoding`).**
      수집 데이터의 `Hit Rate ▲/▼` 줄이 전부 인코딩됐고,
      `tests/test_hit_rate_bullets_are_encoded.py`가 데이터와 모듈을 대조해 같은
      틈이 다시 벌어지면 실패한다. 코어 50px 고정 셸 기준 20슬러그 중 18이 움직인다
      (`scripts/measure_hit_rate_core_gain.py`): 질 발렌타인 **+15.76%** ·
      퀀시 **+10.60%** · 팬텀 +6.01% · 느와르 +2.11% · 치사토 +1.86% · 나머지 소폭.
      **설계문서 §6 표의 셋이 틀렸다** — 퀀시는 4.08%가 아니라 **61.10%**(3단계
      합산, 50px 코어 안), 마스트는 −35.92%가 아니라 **−60%**(스택당 −20%),
      나유타는 1.4%가 아니라 **+42%**(30스택). 표는 정정했다.
- [x] **도로시: 세렌디피티의 Flash 착륙 — 펠릿 카운터 갭 해소 (2026-08-07).**
      보류 사유였던 「10펠릿 중 몇 발이 맞는지는 플레이 조건」은 Fienn 판정으로
      `p_조준` = 1.0(레이드 보스는 화면을 채우고 SG는 근접). 「주기 상수를 재서
      박는다」는 처방은 기각됐다 — 발당 펠릿이 10/15/1+5로 변하고 그녀가 발의
      58.4%를 자기 버스트 창에서 쏘므로 균일 주기는 편중을 못 잡는다. 대신
      `per_shot_rules`에 `accumulate` 모드(발당 가변 증분 누적, 임계값은 감산)를
      넣었다. 같은 작업에서 원문에 없던 상시 `has_pierce` 제거(단독 −13.44%).
      순 효과 **총딜 +16.35%**, 발동 37회·8.32발마다·그녀 발의 36%. 남은 보류는
      160펠릿의 Pierce 범위 +200% 하나(관통 타격 수 모델 없음).
- [x] **「디젤 Highlight가 어떤 덱에서도 버스트를 안 한다」는 오진이었다 —
      실제 결함은 스케줄러의 조용한 실패 (2026-08-07 해결).** 합법 덱((1,1,3))에서
      그녀는 **짝수 사이클에 정상적으로 버스트한다**(19.5/53.4/87.2초) — 2026-07-19
      E2E 기록 그대로다. 앞선 진단은 **유효 배치가 0개인 4유닛 덱**을 돌려놓고
      빈 루프를 「0회」로 읽은 것이었다.
      진짜 결함은 그 옆에 있었다: **티어의 유일한 멤버가 영구히 못 쏘는 배치를
      `simulate_burst_cycle`이 「전투 종료」와 같은 분기로 처리해 이벤트가 하나도
      없는 결과를 돌려줬다.** `_ready_at`이 `inf`를 주면 `fire_time`이 `inf`가 되고
      `>= fight_duration`에 걸려 break — 「이번 사이클을 거른다」가 아니라 「이 덱은
      영원히 풀 버스트를 못 연다」인데 호출자가 그걸 알 방법이 없었다. 이제 빈
      티어와 같은 `full_burst_missed`를 낸다. `deck_search.never_full_bursts()`로
      두 스윕 스크립트가 그 신호를 읽어 숫자 대신 「측정 불가」를 찍는다 —
      `sweep_slug_damage.py`는 그동안 그녀를 163M(정상 691M 급)으로 재고 있었다.
      추천 경로는 무관하다(`ALLOWED_SHAPES`가 B3를 항상 둘 이상 요구하고 API는
      422로 거절한다). Noise Pollution은 이제 E2E 통합 테스트가 지킨다.
- [x] **슬러그 스윕의 티어 3 셸이 불법 모양이었다 — 교체 후 전량 재측정
      (2026-08-07).** 셸 규칙은 「재는 티어를 셸에 넣지 마라」인데, 모든
      `ALLOWED_SHAPES`가 **Burst 3을 둘 이상 요구**하므로 그 규칙은 티어 3에서만
      성립하지 않는다 — 셸이 `(2,2,1)`이라 두 달간 **제품이 만들 수 없는 덱**을
      재고 있었다. 새 셸은 `liter + crown + blanc + helm` → `(1,2,2)`이고,
      짝으로 helm을 고른 이유는 **자기 딜이 가장 낮은 Burst 3 서포터**라 행을
      덜 희석하기 때문이다.
      **티어 3 전량 재측정: 53슬러그 +20.6% ~ +94.9%(중앙 +39.8%), 티어 1·2는
      39슬러그 전부 바이트 불변.** 디젤 Highlight는 163M → **774M**(Intro 750M
      대비 +3.3%로, 2026-07-19 실측의 「Highlight가 더 강하다」와 같은 방향).
      **2026-08-07 이전에 뜬 티어 3 baseline은 이제 비교 불가** — 다시 뜰 것.
      부수적으로 같이 드러난 것 둘: 스윕이 **대상 슬러그가 안 들어간 배치도
      채점**하고 있었고(라피: 레드후드는 풀이 6개로 확장된다), 셸끼리 유닛
      어휘를 공유해 **두 행이 같은 덱이 되는 조합**이 만들어지기 쉽다.
      `check_shells_are_distinct()` + `tests/test_sweep_slug_damage_shells.py`가
      셋 다 못박는다.
- [x] **로스터 재동기화 완료 (2026-08-07).** `roster-drafts-jp-fienn.json`에 34유닛의
      명중이 부위별 굴림(`lines`)까지 들어왔다. **새 기준선 1.055x · 19/25** —
      1.047x에서 움직인 것은 **로스터가 자란 것이지 명중이 아니다**(159유닛 전부
      hp/atk가 바뀌었다). 명중 34줄을 지운 사본으로 다시 재면 **1.055x·19/25로
      바이트 동일** — `core_diameter_px` 없이 `hit_rate`가 inert라는 계약이
      실데이터에서 확인됐다.
- [x] **blessed 기본값 승격 완료 (2026-08-07).** `roster-drafts.json`이 새 export가
      됐고, 7/31 스냅샷은 `roster-drafts-2026-07-31.json`으로 보존했다. `--roster`
      없이 부른 `measure_record_calibration.py`가 **1.055x·19/25**로 새 데이터를
      읽는 것을 확인. 차지속도 줄 35개가 전부 `lines`를 갖고 있어 재동기화가 낡은
      백엔드를 타지 않았음도 함께 확인했다(`RECIPE.md`의 검증 항목).
- [x] **코어 크기 실측 — 완료 (2026-08-14), 모델을 켰다.** Fienn이 전투 중 애니힐리오
      코어를 쟀다: 한 화면에서 무버프 SMG 조준원 90px · 코어 40px → 비율로 **48.89**
      (`raid_record.CORE_DIAMETER_PX`, `docs/measurements/annihilio-core-diameter.md`).
      캘리 **1.065x·16/25 → 1.036x·20/25**, 무기군은 **SMG 1.186x→0.997x** ·
      **AR 1.094x→0.958x**만 움직이고 SR·MG·RL은 불변. deck1이 정확히 0% 움직인다는
      위 예측은 그대로 맞았다.
      **위의 「약 1.007x」 예측은 빗나갔다** — 코어 50px과 그 시점 엔진을 함께 가정한
      값이었고, 그 뒤의 엔진 작업들이 평타 경로를 바꿔 실제로는 1.036x에 앉는다.
      아래 경고는 여전히 유효하다: 1.036x를 「코어가 48.89다」의 증거로 읽으면 안 된다.
      실측이 코어를 정했고, 남은 잔차가 `p_조준`(gap #21)의 크기를 위에서 눌러 준다.
- [ ] **소장품 lv15 유닛의 스탯이 실측과 어긋난다 (명중과 무관, 새 데이터가 드러냄).**
      `test_assemble_roster_matches_the_collector_scrape`가 159유닛 중 3에서 실패한다 —
      Rapi: Red Hood(atk −12·hp −270) · Anis: Star(atk −2·hp −60) · Neon: Vision
      Eye(atk −2). 전부 **모델이 실측보다 낮다**. 이 테스트는 로컬 수집 덤프가 있을
      때만 도는 조건부라 지금까지 skip이었고, 2026-08-07 재수집으로 처음 깨어났다.

      **좁혀둔 것:**
      - 셋의 공통점은 **소장품 레벨 15**(`favorite_item_lv=15`). lv0(Liter)·lv2(Moran)
        유닛은 전부 통과한다.
      - **소장품 곡선은 무죄다.** 셋이 낀 tid(100202·100302)의 커밋된 레코드는
        `collectible_sample`과 동일하고 `atk[15] = 9688`로 정상. `collectible_atk`도
        `curve[15]`를 제대로 읽는다.
      - 셋 다 **일반 소장품**(1xxxxx)이지 애장품(2xxxxx)이 아니다 — 애장품 분기
        (`curve[-1]`)는 안 탄다.
      - 남은 후보는 **레벨 15에서만 생기는 다른 항**이다. 곡선의 `grade` 배열이
        lv15에서만 3이 된다(lv10~14는 2). 등급이 스탯에 얹히는지 미확인.
      - **`node collect.js --tables` 재수집은 답이 아니었다** (2026-08-07 시도):
        새 덤프의 `equipment`·`affinity`가 **`null`**이다(SPA 앱 캐시라 인터셉션이
        요청을 못 봄 — `collect.js`가 경고만 찍고 없이 쓴다). `classes`는 레벨 상한이
        1200→1400으로 늘었을 뿐 겹치는 값이 전부 동일해 400레벨 계산과 무관하다.
        **그 덤프를 병합하면 테이블이 망가진다.**

### 사이클별 풀 버스트 길이 + 아르카나 수레바퀴 게이트 정정 (2026-08-05, 제보 조사에서 착지)

- [x] **아르카나의 조건부 불릿 셋(Magician/Strength/Death)이 실제로 창을 줄이는
      Burst 3 뒤에서만 발동하도록 정정 — 완료 (`wip/arcana-wheel-gate-review`
      브랜치, 트렁크 미병합).** 스펙
      `docs/superpowers/specs/2026-08-05-per-cycle-full-burst-length-design.md`,
      계획 `docs/superpowers/plans/2026-08-05-per-cycle-full-burst-length.md`,
      구현 커밋 `aa5388a7`~`718fd420`(10개) + 상호작용 테스트·뮤테이션 확인·문서
      정리(Task 8). 풀 버스트 창 길이가 그 사이클을 연 Burst 3에서 읽히도록
      바뀌었다(`FULL_BURST_DURATION_DELTA`, `burst_cycle`), `SkillRule`에 트리거
      자신의 시각을 아는 `time_condition`(`own_burst_status_active`)이 생겼다.
      아르카나의 「운명의 수레바퀴 상태로 FB 종료」게이트는 이제 FB를 실제로
      줄이는 Burst 3(오늘은 이사벨뿐) 뒤에서만 열린다. 이사벨·모더니아의 FB 길이
      변경과 아르카나의 잔여 스킬2 쿨감(-75%, 이사벨의 Pointed Feather로 감)도
      함께 인코딩(gap #22 해소). 실로스터 네온 덱(이사벨 없음,
      `anis-star,arcana,crown,cinderella,neon-vision-eye`) 총딜이
      8,421,587,537 → 6,729,347,469로 **−20.1%**(옛 값은 새 값보다 **+25.1%**
      부풀어 있었다 — 게이트가 늘 열려 있던 대가). 기준선 백엔드
      **1903 passed/3 skipped**, 캘리브레이션 **1.078x·17/25 불변**(기록 덱
      5개 어디에도 이사벨·모더니아·아르카나·소다가 없어 캘리는 그대로 — 이
      변경은 덱 추천만 움직인다).
- [x] Soda: Twinkling Bunny의 FB 확장(+2/+3초)도 해소 — 2026-08-06,
      `wip/soda-full-burst-extension`. 슬러그당 고정 델타가 아니라 **자원 조건부
      델타 + 고정점 반복**이 수단이다. 바로 아래 소다 항목에 측정값이 있다.

### 소다의 골든칩 소비가 감산이 아니라 리셋으로 인코딩됐다 (2026-08-05, 아르카나 검토 중 발견)

- [x] **`soda_twinkling_bunny.py`의 `resets: {"trigger": "own_burst", "value": 17}`
      를 「17만큼 감산」으로 고쳤다 — 완료 (`wip/soda-golden-chip-spend` 브랜치,
      커밋 `17cf56fc`).** 원문 템플릿은
      `Number of Golden Chip stacks ▼ {description_value_01} after the effect applied`
      이고, `▼`는 이 데이터 전체에서 **감산 기호**다(이사벨 `▼ 5 sec`, 아르카나
      `▼ 6 sec`). 옛 인코딩은 **17로 세팅**해서 그녀를 매 버스트 뒤 26~27로
      되돌아오는 정상상태에 가둬 놨다. 엔진 확장은 필요 없었다 — `resets`의
      `value_fn(pre_value)`가 Elegg의 ghost 소비를 위해 이미 있었다.
      **바닥은 1**(Fienn 실측: 16스택에서 버스트하면 1스택이 남는다 — 원문에 없는
      값이라 `CHIP_FLOOR` 상수에 실측으로 기록).
      실측(실로스터 덱 `anis-star,arcana,crown,cinderella,soda-twinkling-bunny`,
      180초): 버스트 직전 스택이 평평한 26~27에서 **50→43→35→28→20→13→10**으로
      바뀌고, ATK +65.25% 게이트(≥30)가 **1회 → 3회** 열린다. 소다 본인 딜
      **+4.97%**(807.9M → 848.0M), 덱 총딜 +0.86%. 예상대로 **과소** 방향이었다.
      기준선 백엔드 **1913 passed/3 skipped**(테스트 1건 추가), 캘리브레이션은
      기록 덱 5개에 소다가 없어 **불변**.
- [x] **Beginner's Rewards의 FB 지속 확장(+2/+3초) 재판단 — 1차 결론은 「계속 보류」였고,
      같은 날 Fienn의 실측이 그 결론을 뒤집었다.** 1차 근거는 소다가 **매 사이클**
      버스트하는 시뮬 궤적이었다(임계 20을 t=141.40에 가로지름 → 사이클마다 값이 달라
      슬러그당 고정값인 `FULL_BURST_DURATION_DELTA`에 못 올림). **실전 운영은 그 궤적이
      아니다** — `docs/measurements/soda-golden-chip-in-play.md` 참고.
- [x] **소다의 FB 확장을 인코딩했다 — 착륙 (2026-08-06, `wip/soda-full-burst-extension`,
      `cc874fb4`..`6d337981`).** 수단은 **자원 조건부 델타 + 고정점 반복**이다.
      원문이 `Activates when entering Burst Stage 3. Affects all allies.`이므로 소다가
      그 사이클의 B3일 필요가 없어, 「사이클을 연 B3」에서 읽는 기존
      `FULL_BURST_DURATION_DELTA`로는 안 되고 덱 보유 + 칩 임계로 판정한다. 같은 칩
      임계에 걸린 **평타당 넉**(Beginner's Rewards 둘째 불릿)도 함께 인코딩했다.
      기준선 백엔드 **1913 → 1935 passed / 3 skipped**(테스트 22건 추가).
      - **실측 대조 — 일치한다.** `scripts/measure_golden_chip.py --deck
        tove-signature,arcana-fortune-mate,soda-twinkling-bunny,dorothy-serendipity,
        drake-signature --hold drake-signature`(격번 로테이션을 재현하는 새 플래그):
        **모든 창이 정확히 15.00초**, 칩이 **50 → 33 → 42 → 50 → 33**으로 순환한다.
        Fienn 판독은 50 → 33 → 40/41 → 49/50 → 33이므로 중간값만 **+1~2 스택** 높고
        밴드의 모양·주기·창 길이는 그대로다. 그 +1~2는 이미 알려진
        「창당 fill 실측 8 vs 시뮬 9」 차이 그대로다(`docs/measurements/` 참고).
        같은 덱을 브랜치 이전 코드로 돌리면 창이 10초이고 칩은
        50 → 33 → 39 → 45 → 28 → … 로 **고갈된다** — 확장이 그 차이를 만든다는 것이
        같은 스크립트 안에서 확인된다.
      - **총딜(180초, 기록 보스, 브랜치 이전 → 이후).** 계획의 예측(+9.3%)은 +5초
        주입만 셌고 넉이 빠져 있었으므로 실제는 그보다 크다:

        | 로테이션 | 이전 | 이후 | 변화 |
        |---|---:|---:|---:|
        | 스케줄러가 고른 대로(소다는 버스트 안 함) | 4.4288B | **5.0810B** | +14.7% |
        | 격번, 드레이크 홀드(소다↔도로시) | 4.3862B | **5.0668B** | +15.5% |
        | 격번, 도로시 홀드(소다↔드레이크) | 4.0626B | **4.6938B** | +15.5% |
        | 소다가 매 사이클(다른 B3 둘 다 홀드) | 2.6059B | **2.8883B** | +10.8% |

        **사이클 수는 줄지 않았다** — 창이 10→15초가 돼도 이 덱의 B3 좌석은 이전과
        같은 9회(매 사이클 운영은 5회)다. 「창이 길어지면 사이클이 줄어 총딜이 내려갈
        수 있다」는 우려는 이 덱·이 길이에서는 나타나지 않는다.
      - **캘리브레이션 불변.** 브랜치 전후 모두 **1.079x · 17/25**로 한 자리도 안
        움직인다(기록 덱 5개에 소다가 없다). 다만 여러 문서에 적힌 **1.078x는 이
        브랜치 이전에 이미 낡은 값**이었다 — 트렁크 `19afe0ac`에서 재보면 1.079x다.
      - **시뮬 비용 불변.** `scripts/bench_evaluate_deck.py`(소다 없는 덱)가 브랜치
        전 157.76ms, 후 157.38ms로 같고 `full_burst_passes`는 `{passes: 1,
        converged: True}`다 — 소다 없는 덱은 고정점 루프를 한 번만 돈다. (브랜치
        계획에 적혀 있던 44.4ms는 이 스크립트·이 기계에서 재현되지 않는다.)
      - **실 로스터 덱의 수렴 패스 수(180초)**: 위 덱 2패스(격번·스케줄러),
        매 사이클 운영 3패스, `anis-star,arcana,crown,cinderella,soda-twinkling-bunny`
        3패스. 상한 32에서 한참 멀다.
      - 남은 미지수는 `docs/measurements/`의 「결론짓지 않는 것」절 — 특히 창당 fill이
        실측 8인데 시뮬 9인 차이(소다의 발수 모델이 빠를 가능성).
- [x] **`MAX_FULL_BURST_PASSES`를 8 → 32로 올렸다 (`c215b738`).** 패스 수는 덱이 아니라
      **전투 길이**의 함수다(격번 픽스처: 200초 3패스 · 400초 5 · 600초 7 · 700초 8,
      이후 평평). `fight_duration`은 폼 필드라 700초가 실제로 들어올 수 있고 거기서
      옛 상한 8은 여유가 정확히 0이었다 — 한 패스 더 필요한 덱은 고정점이 아닌 답을
      `converged: False`만 달고 내놓는데 그 플래그를 읽는 하류가 없다. 상한은 품질
      노브가 아니라 폭주 방지 장치이므로 수렴하는 덱은 상한과 무관하게 실제 패스만
      지불한다.
- [x] **`converged: False`에 소리를 붙였다.** 읽는 하류가 없던 플래그 대신
      `FullBurstConvergenceWarning`을 낸다 — 소비자가 아무것도 안 해도 닿고,
      `backend/pytest.ini`가 `filterwarnings = error`라 **테스트 스위트 전체가
      수정 0줄로 소비자**가 된다. 질의 헬퍼를 안 만든 이유는 선례가 말해준다:
      `scripts/`에서 시뮬 결과를 소비하는 16개 중 `never_full_bursts`를 부르는
      것은 2개뿐이라, 헬퍼는 「읽는 하류가 없다」를 이름만 바꿔 재생산한다.
      수신자는 앱이 아니라 우리로 정했으므로(Fienn, 2026-08-08) API 응답 필드와
      프론트 배너는 만들지 않았다.
      **상한 32의 실제 마진도 같이 쟀다**: 격번 픽스처의 패스 수는 8에서
      평평하고 **7200초 — 게임 최대 180초의 40배 — 까지 안 올라간다**(200초 3 /
      700초 8 / 1800초 8 / 3600초 8 / 7200초 8). 즉 이 경고는 오늘 소다로는
      울릴 수 없고, 진동해서 수렴 안 하는 조합이 미래에 생겼을 때를 위한 것이다.
      700초 평탄부는 0.39초라 테스트로 못박았다.

### 코어 지름 측정·입력 (2026-08-08)

- [x] **조준원 UI가 실제 탄착군이고 화면↔엔진 관계가 순수 스케일임을 확정했다.**
      사격장에서 잰 조준원 셋(SG 187 · AR 57 · SMG 82)이 데이터값 250/75/110에
      **원점을 지나는 하나의 비례식으로 1px 이내**에 얹힌다(k = 0.7485).
      부수 확인 둘: 게임 데이터값이 아카라이브 글의 회귀 절편보다 맞고(SG에서
      −0.5px 대 +7px), **코어는 거리에 종속된다**(near/far 2.44배).
      상세: `docs/measurements/accuracy-circle-and-core-px.md`.
- [x] **「단위는 1920×1080 화면 픽셀」이라는 초판 결론을 철회했다 (2026-08-08).**
      k = 0.7485가 `1920/2560`과 0.2% 차이인 우연에 기댔는데, **2560은 녹화본
      크기이지 게임이 그린 폭이 아니다** — 게임은 창모드였고 클라이언트 렌더는
      2333×1312였다(창 캡처 2333×1343). 실제 렌더 폭을 그 식에 넣으면 0.823이
      나와 안 맞고, 방향도 반대다(렌더가 크면 픽셀도 커야 하므로 AR 조준원이
      100px이어야 하는데 실측 57px). **스케일의 결정 요인은 미확정**이고, 다른 창
      크기에서 조준원을 한 번 더 재야 갈린다. 쓸 수 있는 환산은 **비율**뿐:
      `코어_엔진 = 코어_px × (조준원_엔진 / 조준원_px)`. 코어 값은 비율로
      재계산해도 **0.21%**만 움직여(58.79 / 33.40 / 24.05) 하류 수치는 불변이다.
- [x] **잰 코어가 회차 데이터 → 보스 카드 → 폼 → 엔진까지 닿는 길을 만들었다.**
      `raid-rotations.json`의 `core_diameter_px`(엔진 단위), 원본 px와 해상도는
      `stated`에. `range_band`는 안 건드린다 — 코어를 그 보스와 싸우며 재면 거리는
      자동으로 맞다. 폼에서는 「코어 피격 가능」을 켰을 때만 보이고, 비우면 오늘
      동작 그대로다. `/update-raid-bosses`가 사람 확인 단계에서 묻는다(공지에 없어
      판독으로는 안 나오는 값이다).
- [x] **코어 지름 옆에 그 값이 무엇을 뜻하는지 적는다.** 「58.67」은 사용자에게
      아무 의미가 없고, 틀린 값이 조용히 덱 순위만 바꿨다. 이제
      `무버프 코어 명중 — SG 5.5% · SMG 28.4% · AR 61.2% · MG·SR·RL 100%`가
      칸 아래 붙는다. 계산은 `frontend/src/lib/coreHitRate.ts`가
      `app.accuracy`를 미러링하고(선례: `lib/elementAdvantage.ts`), **표류는
      `backend/tests/test_frontend_mirrors_accuracy.py`가 잡는다** — 탄착군
      지름은 원소 상성과 달리 수집 데이터에서 파생돼 실제로 바뀐 적이 있다.
      정렬은 명중률이 아니라 탄착군 지름 순이라 타이핑 중에 줄이 안 뛴다.
- [x] **화면에서 잰 픽셀을 엔진 단위로 옮기는 계산기를 붙였다.** 칸이 받는
      단위와 사람이 잴 수 있는 단위가 달라 **잰 숫자를 그대로 치면 조용히
      틀렸다**(50px을 재고 50을 넣으면 코어히트율 1.78배 과소). 코어 px ·
      조준원 px · 기준자 무기 셋을 받아 `코어_px × (조준원_엔진 / 조준원_px)`로
      환산하고 「넣기」로 엔진 칸을 채운다. **해상도를 묻지 않는다** — 비율만
      쓰므로 창모드·전체화면·레터박스·녹화 업스케일이 약분된다. 기준자에서
      MG·SR·RL은 뺐다(조준원 10이라 ±1px이 13%). SG가 0.53%로 가장 정확해
      기본값. 남은 오차원은 둘뿐이다: 조준원의 **무버프 여부**와 **판독 정밀도**
      (코어 25px에 ±1px이면 코어히트율이 18.1~21.7%로 흔들린다 — 창을 크게
      할수록 줄어든다).
- [ ] **UX 개선의 본체는 아직 남아 있다 — 회차 데이터를 채우는 것.** 코어는
      사용자 취향이 아니라 보스의 사실이라 `weakness`·`range_band`처럼 사용자가
      타이핑할 값이 아니다. 배선은 이미 카드까지 닿아 있고 **비어 있는 것은
      데이터뿐**이다. 회차마다 한 번 재면 모든 사용자가 카드 한 번으로 받는다.
      스크린샷을 끌어다 앱 안에서 재는 것(~200줄, 이미지 가로폭이 해상도라
      환산이 자동)은 Fienn의 측정 도구로서만 값어치가 있다.
- [x] **수동 칸을 「기타 설정」 안으로 접었다.** 「카드가 채워줄 테니 강등한다」는
      순서가 틀린 논리였고(회차 데이터가 아직 전부 `null`이라 카드가 안 채운다),
      실제 근거는 **전문가용 입력**이라는 것이다 — 값을 채우려면 녹화하고 픽셀을
      재야 하는데 체크박스와 나란히 서 있으면 숙제로 읽힌다. 방어력·전투 시간이
      이미 같은 기준(「거의 바꾸지 않는 값」)으로 그 상자에 있다(Fienn, 2026-08-08).
      접힌 요약에 `· 코어 33.33`이 붙고, 코어를 못 때리는 보스에서는 그 조각이
      빠진다. 출처 표시(「회차 데이터가 준 값」)는 **안 만들었다** — 사용자는 값이
      어디서 왔는지가 아니라 무엇으로 계산되는지를 알고 싶고, 그건 요약이 이미
      답한다. 실제로 카드가 값을 싣기 시작한 뒤에 필요해지면 그때 붙인다.
- [ ] **보스 칸의 오류 문구가 사실상 안 뜬다.** `canSubmit`이 `!!bossProfile`을
      요구하는데 그 값은 어떤 보스 칸이든 유효하지 않으면 `undefined`다 → 버튼
      비활성 → `handleSubmit`이 안 돌고 → `touched`가 false로 남아
      `errors={touched ? errors : {}}`가 빈 객체를 내려준다. **한 번도 제출에
      성공한 적 없는 사용자가 칸을 잘못 채우면 버튼만 죽고 이유는 안 보인다.**
      코어 지름 이전부터 있던 것으로 `적 방어력`으로도 재현된다. 고치려면 「언제
      오류를 보일 것인가」(blur 시 · 첫 편집 후 · 항상)를 정해야 한다.
- [ ] **실기록 캘리브레이션(`RECORD_BOSS`)에 코어를 켤지는 여전히 미정.** 실측
      보스 코어가 생겨도 별개 결정이다(`docs/decisions.md`). 실기록과 맞는 코어는
      AR 기준 약 67 · SMG 기준 약 95로 **서로 다르므로**, 켜는 것만으로는 잔차가
      안 닫힌다.

### 보류 전수 감사 후속 (2026-08-07)

83개 모듈 보류 전수 대조 + 스코프 전수 대조에서 나온 잔여. 상세는
`docs/engine-gaps.md`「보류 전수 감사」.

- [x] **낡은 보류 5건 정정 + 인코딩-원문 불일치 3건 수정.** 루드밀라 탄환환급 배선,
      브리드/D:Killer Wife 스코프, 프리카 Pierce 지속시간. 기준선 1958/3 → **1961/3**,
      캘리 **1.079x·17/25 불변**.
- [x] **`scripts/audit_target_scopes.py` 신설** — 좁은 타게팅 문구를 전수로 나열하고
      좁은 스코프를 하나도 안 내는 모듈을 SUSPECT로 분리한다. 현재 SUSPECT 3건은
      전부 검증 완료(페이로드가 inert/보류 스탯이라 무해).
- [x] **`laplace-ultimate-hero`·`maxwell-ordinary-mechanic` 원문 수집 + 검증 완료
      (2026-08-07).** 감사 3종의 "NOT SCANNED"가 0이 됐고, 읽어보니 각각 결함이
      하나씩 있었다 — 맥스웰의 「Burst Stage 3 진입 시」가 `full_burst_enter`로 배선돼
      B3 자신의 버스트딜에 안 닿았고(슬롯 03이 문자 그대로 `3`이다), 라플라스의
      「Gains Pierce」는 원문상 skills[0]의 변형 무기에 붙는데 그녀의 버스트에 10초로
      걸려 있었다(Mjolnir 원문엔 Pierce가 없다). 원문이 확정한 것 둘: Over Energy는
      「변형 상태 평타 12회마다 +5%, 100%까지」= 스테이지당 240타라 기준 탄창에서
      `2 transforms`가 맞고, **이것이 이 모듈에서 유일하게 최대탄약을 안 따라가는
      단계**임이 드러났다(최대탄약 덱에서 스테이지 램프를 과소평가). Matis Uberbuster의
      스테이지별 차지시간(3/2.5/2/1.5/0.4)도 읽혔다.
- [x] **맥스웰:OM의 Matis Uberbuster 변형 인코딩 (2026-08-07).** 트레이드 걱정은 기우였다 —
      스윕 **+13.71%**(다른 92슬러그 불변). 350%를 300% 풀차지 배율로 때리는 한 발이,
      침묵당하는 몇 발의 ~2.5% 기본샷을 압도한다. **차지시간이 상수가 아니라 Overcurrent
      단계가 고정한다**(3 / 2.5 / 2 / 1.5 / 0.4초, 자기 버스트마다 한 단계·상한 5)는 점에서
      이 엔진의 다른 단발 변형과 다르다 — 세그먼트마다 **자기 프로필**을 싣는 첫 소비자다.
      캘리 불변(그녀는 실기록 25유닛에 없다).
- [x] **라플라스:UH의 Over Energy 스테이지 임계를 발수로 유도 (2026-08-07).** 기준 탄창에서는
      옛 상수(창 2개)와 같은 답이라 안 보였다 — 갈리는 건 최대탄약이 붙을 때고, 한 창이 240발을
      담을 수 있게 되면 재장전 간격을 하나 통째로 건너뛰어 **6.5초 빨라진다**. 스윕 +0.34%.
- [x] **미측정 차지 무기 16유닛을 실측 stand-in(22프레임)으로 전환 (2026-08-07).**
      0은 중립이 아니라 「가장 빠른 자기 자신」이다. 신데렐라는 stand-in이 아니라
      **자기 실측값**(`CHARGE_INTERVAL_FLOOR_SECONDS` = 10/29초가 곧 그녀의 딜레이였다)로
      갔다. 15유닛 −0.40%~−14.73%, **캘리 1.079x·17/25 불변**. 상세는 `docs/engine-gaps.md`.
      (**2026-08-15 정정:** 그 10/29는 딜레이가 아니라 그녀 무기의 180발/분이었다 —
      그녀는 멈춤 0 + 유닛별 바닥값으로 옮겨졌다.)
- [x] **MG 예열 착륙 (2026-08-07, Fienn 프레임 판독).** 최대 연사 60발/초는 맞았고
      엔진이 그걸 **첫 발부터** 주고 있었다 — 예열은 48구간/137프레임, 탄창당 1.4833초
      손실. 합계 1.076x → **1.047x**, ±15% 이내 17/25 → **19/25**, MG 평균 1.193x →
      **1.051x**(RL 1.035 바로 옆, 1.0 아래로 안 내려감). 아스카 +0.449B → **+0.069B**.
      원본 `docs/measurements/mg-spinup.md`.
- [x] **MG 램프 곡선과 부분 잔존 착륙 (2026-08-14).** 예열이 총합 하나에서 **누적
      곡선**이 됐고(콜드 137프레임 중 56이 첫 2발), 짧은 재장전이 남긴 예열을 다음
      탄창이 물려받는다(감쇠 D=66프레임, 발사 공백에 재장전 후 지연 12.5프레임 포함).
      클램프는 **구간별**로 바뀌어 레이의 ▲100%가 68.5 → 79.5프레임. 합계 1.033x →
      **1.044x**, ±15% 이내 20/25 → 19/25, MG 평균 1.125x → **1.176x**.
      **캘리가 나빠진 것이 의도한 결과다** — 콜드 램프의 과청구가 별개의 MG 과대항을
      상쇄하고 있었고(크라운은 램프를 통째로 빼도 1.341 → 1.345로 안 움직인다),
      그것을 걷어내 표적을 드러내는 것이 이 작업의 목적이었다. 미하라 0.902 →
      0.900(대조군, 재장전이 감쇠보다 길어 안 물린다).
- [ ] **크라운 1.342x — MG 과대의 진짜 항, 지금 최대 무기군 항(MG 1.164x).** 램프
      곡선이 상쇄를 걷어낸 뒤 드러난 얼굴이다. 램프 제거 what-if에서 1.341 → 1.345로
      **0.004밖에 안 움직였으므로 원인은 예열이 아니다.** 덱3의 helm-signature
      1.284x가 같은 덱에서 함께 뜬 것도 같이 볼 것. 남은 축은 **코어 비중(갭 #21)**
      하나다 — 예열·재장전·잔존은 전부 기각됐다(`docs/insights.md`).
- [x] **SMG에는 예열이 없다 — 가설 기각 (2026-08-08, Fienn 인게임 확인).** 「heating」은
      게임이 MG에만 쓰는 어휘다 — 수집 데이터에서 이 문구를 쓰는 건 아스카·레이 둘뿐이고
      둘 다 같은 용어 ID(`word_group=10073`)이며, 레이 원문은 대상을 아예 `allies with a
      Machine Gun`으로 못박는다. MG 착륙이 근거도 하나 걷어갔다 — **「잔차가 연사 속도 순」이
      더는 성립하지 않는다**(MG 60발/초 1.066x가 SMG 20발/초 1.148x **아래**). SMG는 공칭
      연사 그대로 두고 `spinup_for_weapon`은 MG만 안다. `docs/measurements/smg-no-spinup.md`.
- [x] ~~**고정 연사 무기(MG·SMG)의 실제 발사 수 실측 — 지금 가장 큰 단일 항.**~~ 2026-08-07
      아스카 조사에서 실기록 잔차가 **무기군으로 정렬**돼 있음이 드러났다(MG 1.193x ·
      SMG 1.149x · SR 1.118x · AR 1.116x · **RL 1.035x**). MG+SMG가 추적 가능한 과대
      +2.574B 중 **+1.706B(66%)** 를 낸다. 엔진은 MG를 스핀업 없는 60발/초 고정으로
      돌리는데 **MG heating은 게임 스킬 원문이 버프/디버프하는 실존 메커니즘**이다.
      **측정: 정지 상태에서 MG 한 탄창을 비우는 데 걸리는 시간**(→ 실효 연사). 차지
      무기가 모션 딜레이 실측 후 1.035x로 가장 정확해진 것과 같은 경로다.
- [x] **아스카 +0.499B는 아스카 버그가 아니다 (2026-08-07).** 인코딩·무기 스탯·오버로드
      ·탄창·재장전 전부 검증했고 원문과 일치한다. 그녀는 위 무기군 항의 최대 인스턴스일
      뿐이다(딜의 54%가 50평타마다 471.86%라 발사 수에 선형).
- [ ] **그 17유닛은 여전히 실측이 필요하다 — 다만 질문이 절반으로 줄었다**
      (`scripts/audit_charge_motion_delay.py`가 `assumed`도 계속 질문하고 exit 1).
      실측값은 0.34~0.43으로 흩어져 있으므로 stand-in(22프레임)은 누군가에게 틀리다.
      **「멈춤이 있는가」는 2026-08-15에 닫혔다** — 17유닛 전부 `input_type`이 `UP`
      (놓을 때 발사)이고, `UP` 26정 중 잰 11명이 전원 멈춤을 갖는다. 남은 건 값뿐이다.
      대상:
      ada-wong · arcana · d-killer-wife · diesel-winter-sweets(2종) · ein · laplace ·
      laplace-signature · maiden-ice-rose(**−14.7%로 가장 크다**) · maxwell ·
      maxwell-ordinary-mechanic · milk-blooming-bunny · red-hood · rouge · takina-inoue.
- [x] **루즈 Card Throw의 Max HP 불릿 인코딩 (2026-08-07).** 승인된 CDR 근사는 안 건드렸다 —
      두 불릿은 트리거는 같아도 **제약이 다르다**. 쿨감은 로테이션이 짜이기 전에 확정돼야 하고
      per-shot 룰은 그 뒤에 돌지만, Max HP는 페이즈 2가 각 인스턴스 시각에 읽는 **딜 입력**이라
      그 제약이 없다. 그래서 Max HP만 진짜 8풀차지 카운터로 옮겼다(측정 셸에는 Max-HP 소비자가
      없어 스윕 불변 — Maiden·신데렐라·맥스웰·라플라스:UH가 같이 앉을 때만 값이 난다).
- [x] **스노우화이트: Determination ATK가 변형 차지샷에 안 붙는다는 Fienn 판정 확인 (2026-08-07).**
      차지가 5초인데 버프도 5초라 샷이 나갈 때는 이미 만료다. **엔진이 이미 그렇게 동작한다** —
      버프를 꺼도 180초 런의 변형샷 6개가 전부 바이트 동일. 코드 변경 없이 그 관계(버프 ≤ 차지)를
      테스트로 못박았다. 잔여: 변형샷이 **자기가 30번째일 때**(약 1/30 사이클) 같은 순간에 자기를
      버프하는 경계는 남아 있다 — 배제하려면 엔진에 없는 카운터 예외가 필요.
- [x] **`normal_attack_crit_rate` 버킷 신설 (2026-08-07).** 헬름 과대·줄리아 시그니처 과소를
      동시에 해소. 줄리아 시그니처 스윕 **+3.61%**, 헬름 시그니처 실기록 1.334x → **1.319x**,
      합계 1.079x → **1.076x**(17/25 불변). 상세는 `docs/engine-gaps.md`.
- [x] **명중률 → 탄착군 → 코어히트율 모델 착륙 (2026-08-07, `wip/hit-rate-core-accuracy`
      브랜치).** `hit_rate`가 `accuracy.core_hit_rate`로 소비자를 얻었다 — 무기별
      탄착군(AR 75·SG 250·SMG 110·MG/SR/RL 10px, 실측 회귀식 셋이 전부 명중 110%에서
      지름 0으로 수렴)이 명중률로 좁아지고, 코어 지름과의 면적비가 코어히트 확률이 돼
      `damage_formula`가 크리티컬과 같은 기대값 항으로 소비한다. 평타에만 적용(코어
      스트라이크·소환물 자체조준은 조준 문제가 아니라 p=1.0 유지). **`BossProfile.
      core_diameter_px`는 opt-in, 기본값 `None`** — `RECORD_BOSS`엔 없어 캘리브레이션은
      1ULP 이내로 불변(1.047x·19/25, 5덱 중 1덱이 8.45e9 중 9.5e-07 차이 — 결합법칙
      때문이라 보고 수치는 안 움직인다). 15유닛 19슬러그의 재인코딩은 같은 날 뒤이어
      완료됐다(「명중률 착륙의 후속」). 자기 무기가 RL/MG인 넷(디젤·마스트·
      모더니아·앵커)도 딜이 0은 아니다 — 셋은 버프 대상이 아군 전체라 덱의
      SG/SMG/AR가 받는다(자기 한정은 마스트뿐). 설계 `docs/superpowers/specs/2026-08-07-hit-rate-core-accuracy-
      design.md`, 상세는 `docs/engine-gaps.md`.
- [ ] **로스터 재동기화 필요 — 명중률 오버로드 값 곡선 미확정.** 수집기가 이제
      「명중률 증가」행을 수집한다(`tools/collect-blablalink/parse.js`)만, 기존
      로스터 드래프트에는 이 행이 없다. **차지속도의 `lines` 신설 때와 같은 성격의
      변경**이다 — 재동기화 전까지는 로스터의 명중 오버로드 값이 전부 비어 있다.
      Fienn이 재동기화 → 재동기화된 드래프트의 `{slot}_equip_option{n}_id`와 HTML
      합계를 대조해 명중의 효과 타입 번호와 값 곡선을 fit(`base_stat_folded =
      [6, 13]`의 정체가 여기서 확정) → `data/nikke-stat-tables/tables.json`의
      `overload.values`/`type_name` 반영.
- [ ] **11슬러그(엔진 블로커 해소 그룹)의 Hit Rate 재인코딩 — 아직 어느 모듈도
      `hit_rate`를 Effect로 등록하지 않는다.** 대상: dorothy-serendipity ·
      jill-valentine · phantom(+시그니처) · chisato-nishikigi · miranda(+시그니처) ·
      quency-escape-queen · nayuta · soda-twinkling-bunny · sugar(+시그니처) ·
      drake(+시그니처) · noir. 도로시: 세렌디피티가 최대 수혜자다 — 2026-08-07
      Flash 착륙으로 두 명중 버프가 실제로 110% 특이점을 넘어, 그녀 발의 36%가
      SG 코어히트 100%가 된다(명중 인코딩이 사는 몫 +18.88%). 상세는
      `docs/encoded-nikkes.md` 각 행.
- [ ] **`core_diameter_px`는 API 전용 — 프론트엔드 미노출.** `BossProfileField.tsx`는
      `core_hittable`과 `pierce_hits_body_behind_core`만 그린다(의도된 스코프,
      설계 §4). 실기록 보스 외의 보스 코어 크기를 실측하기 전까지는 사용자가 입력할
      근거 있는 값이 없다 — 언블록 조건은 그 실측.

### 보스 약점·속성저지·코어 2관통 (2026-08-03, 스펙 착지)

- [x] **보스 약점 선택 · 속성저지 필수 제약 · 코어 2관통 플래그 — 완료
      (`wip/boss-weakness-and-gimmicks` 브랜치, 트렁크 미병합).** 스펙
      `docs/superpowers/specs/2026-08-03-boss-weakness-and-gimmick-fields-design.md`,
      계획 `docs/superpowers/plans/2026-08-03-boss-weakness-and-gimmick-fields.md`,
      커밋 `3f83e0e`~`e72f521`(22개). 셋: (1) 보스 약점을 원소 코드 아이콘
      6개(5속성 + 약점 없음)로 고르면 폼이 보스 본인 속성으로 변환해 보낸다
      (변환은 UI 경계에 갇힌다 — 와이어는 그대로 보스 원소); (2) 「속성저지 필수」를
      켜면 **덱 생성 시점**에 약점 속성 유닛이 없는 덱을 걸러낸다(사후 보수 아님),
      약점유닛이 모자라면 채울 수 있는 덱까지만 만족시키고 경고, 거부하지 않는다;
      (3) 「상시 코어 2관통」(코어 피격 가능에 종속)을 켜면 관통 유닛의 통상딜이
      코어와 본체에 각각 꽂힌다. 기준선 백엔드 **1839 passed/3 skipped**, 프론트
      **485 passed**, 캘리브레이션 **1.082x 불변**(세 플래그 전부 기본값 off —
      머지베이스 `bdb5bf9`에서도 동일값으로 확인). 눈으로 확인: 아이콘 6개 렌더 +
      속성별 테두리 색, 코어 2관통↔코어 피격 가능 체크박스 상호 연동, 「속성저지
      필수」가 솔로 레이드 탭에만 있고 유니온 레이드 탭엔 없음, 1440px에서 오버플로
      없음. 실 로스터로 추천을 돌려 결과까지 보는 것은 못 했다 — 합성 픽스처가
      Burst 2 티어를 못 채워 매번 422(엔진은 정상 응답: "burst tiers 1, 2 and 3 all
      required"). 실 로스터 대조는 다음 세션 몫.
- [ ] 코어 2관통 보스에서 실기록 대조 — 켠 상태의 캘리브레이션이 없다
      (`docs/superpowers/specs/2026-08-03-boss-weakness-and-gimmick-fields-design.md`
      「이 설계가 가르지 못하는 것」)

### 창 폭 레이아웃 (2026-08-02, Fienn 제보)

- [x] **앱이 창 폭을 쓴다 — 완료.** 제보: 세로로만 긴 형식이라 창 넓이가 아깝다.
      `.app`의 `max-width: 1120px`를 없앴다. 1920px 창에서 로스터 그리드가
      **6열 → 10열**이 되고, 이미 `auto-fill`/`flex-wrap`으로 짜인 팔레트·전투
      카드도 함께 따라온다. 레이아웃만 유동이고 **문장은 `--measure: 72ch`가
      따로 잡는다** — 모드 힌트는 인라인 `<span>`이라 `max-width`가 듣지 않아
      `.mode-switch` 컨테이너에 건다.
- [x] **결과가 설정 바로 아래에 선다 — 완료.** 진행·에러·결과 블록이 70여 개
      칩의 팔레트 뒤에 있어 답을 읽으려면 보유 유닛 전부를 스크롤해 지나야 했다.
      솔로·유니온 두 패널 모두 설정 행 바로 뒤로 옮겼다. 실제 실행에서 **설정 →
      실행 버튼 → 결과 #1·#2가 1920px 한 화면에** 들어온다.
- [x] **실행 버튼이 하단 고정 바에서 내려왔다 — 완료.** 단일/전부 최적화 모드만
      해당한다. 그 바가 있던 이유(팔레트가 버튼을 화면 밖으로 밈)가 사라져
      `.recommend-form__actions--sticky`의 음수 마진·`z-index` 처리도 함께 지웠다.
      빈자리·기대 딜량·유니온은 버튼이 sticky 덱 컬럼에 있어 이미 항상 보이므로
      **그대로 뒀다**.
- [ ] **덱 결과 카드가 창 끝까지 늘어난다 — 설계 논의 필요.** 폭 상한을 없앤
      결과, 1920px에서 결과 카드 한 장이 1800px가 되어 왼쪽 초상화 5개와 오른쪽
      총딜 숫자 사이가 크게 빈다. 카드를 가로로 여러 장 배치할지, 카드 폭에
      상한을 줄지는 정하지 않았다. Fienn이 처음 고른 불편 3가지에는 없던 항목이라
      이번 범위 밖으로 뒀다.

### 배분 탐색 품질 (2026-08-02, Fienn 실사용 제보)

- [ ] **배분 탐색의 폭이 ±5%다 — 어느 국소최적에 앉을지는 사실상 설정이 정한다.**
      플랫 발수 장탄을 착륙시키며 드러났다(2026-08-02). 같은 로스터·같은 보스에서
      5덱 합계가 **40.05B ~ 42.28B** 사이를 오간다 — 움직인 것은 엔진이 아니라
      대리 랭킹의 shortlist 크기(`cascade.DEFAULT_TOP_K` 20 vs 100)와 스왑 예산뿐이고,
      **어느 쪽이 좋은지는 엔진마다 다르다**(트렁크는 K=20이, 장탄 엔진은 K=100이 이긴다).
      각 설정은 결정적으로 재현되고, 스왑 예산은 45 → 180 → **500초**를 줘도 141초에
      같은 값으로 수렴하므로 예산 문제가 아니다. 후보 방향 셋: 그리디 peel의 근시안
      (첫 덱을 최선으로 떼면 나머지가 나빠진다) · 대리 모델이 unit-only라 **무기 의존
      시너지**(장탄 +6발 = SR에 +100%, MG에 +2%)를 원리적으로 표현 못 한다 ·
      K와 예산의 교환비(넓은 K는 같은 예산에서 스왑을 덜 한다). **먼저 설계 논의.**
      측정 도구는 `scripts/measure_pool_caps.py --top-k`와
      `scripts/measure_engine_change_delta.py`. 상세는 `docs/insights.md`.
      **스왑 예산 축은 닫혔다(2026-08-05)** — 예산이 후보 교환 수로 바뀌고 등반이
      수렴까지 돌면서, 예산이 더 이상 어느 국소최적에 앉을지를 정하지 않는다
      (`docs/decisions.md`). 남은 축은 그리디 peel의 근시안과 대리모델의
      unit-only 한계, 둘뿐이다.
      **K축도 사실상 닫혔다 — 재측정(2026-08-06).** 위 표의 K=100 손실(−5.29%)은
      원인이 "넓은 K는 **같은 벽시계 예산에서** 스왑을 덜 한다"였고, 그 예산이
      없어졌다. 프로덕션 캡(4/6/12)에서 `python3 scripts/measure_pool_caps.py
      --top-k 20,100`은 이제 **41.056B(K=20) vs 41.228B(K=100), +0.42%**다.
      즉 이 항목의 "±5%"는 낡은 숫자이고, 남은 폭은 아래 풀 폭 항목에 있다.
- [x] **★ 캡·K는 한 쌍이다 — 회귀로 막았다. 그리고 두 번째 보스가 「절벽」의
      정체를 바꿨다 (2026-08-06).**
      `test_the_pool_width_and_the_shortlist_width_are_one_setting`이
      `WIDE_TIER_CAPS`와 `DEFAULT_TOP_K`를 **한 쌍으로** 못박고, 실패 메시지가 두
      보스 표와 `measure_pool_caps.py` 재실행을 지시한다(뮤테이션 확인: 6/9/18에서
      실패). **Fire 보스에서 −11.32%는 재현되지 않았다** — 같은 6/9/18이 **+0.12%**
      이고, 거기서는 **가장 좁은 2/4/8이 +2.27%로 최고**다. 즉 11%는 캡의 성질이
      아니라 **(보스, 캡) 한 칸**이다. Wind에서 최고였던 3/5/10은 Fire에서 −0.53%라
      **양쪽에서 이기는 설정이 없다** — 옮겨갈 값이 없으므로 현행 유지.
      Wind 원본: 4/6/12 41.056B · 6/9/18과 8/12/24가 똑같이 36.408B(K=20) ·
      K=100이면 둘 다 40.846B(−0.51%). 그 한 칸에서 K가 회복시킨다는 것은
      **대리모델이 그 넓은 풀을 잘못 순위 매긴다**는 뜻까지만 말한다 — Fire에서
      같은 넓힘이 무해하므로 「좁은 풀이 품질을 떠받친다」는 일반 명제가 아니다.
      **위 두 항목은 그래도 못 믿는다**: 「후보 풀 캡의 상한 = 0」(2026-08-02)은
      보스 하나에서 이미 반증됐고, 「후보 풀이 CDR 유닛을 못 본다」를 이유로 캡을
      넓히는 것도 그 보스에서 −11%를 낸다. 어느 쪽도 재측정 없이는 못 움직인다.
      **이 항목 자체가 그 교훈의 사례다** — 하루 전 나는 11%를 캡의 성질로 적었고,
      두 번째 보스가 그것을 (보스, 캡) 한 칸으로 되돌렸다.
- [x] **단조성 위반의 크기 — 측정 완료, 0.3%짜리였다 (2026-08-06).** 「앉지 않은
      벤치 3명을 제외해도 답이 바뀐다」를 서로 다른 네 조합으로 쟀다(기준 78유닛
      41.056B, 세 번 재는 동안 한 자리도 안 움직인다):
      **+0.28% · +0.22% · +0.27% · −0.51%**. 기록된 **2.09%보다 한 자릿수 작고**,
      그 쌍의 제외 목록은 어디에도 안 적혀 있어 재현이 안 된다(**다음부터 측정의
      입력을 적을 것**). 같은 자리에서 잰 풀 폭 절벽이 11.32%이므로 **과녁은 그쪽**
      (Fienn 판단, 2026-08-06). 세 번째 조합에서 무기변형 창 겹침 크래시를 밟았고,
      그 크래시는 이 세션에서 고쳤다 — 측정이 크래시를 찾아낸 셈이다.
      **기각된 가설:** 원인은 대리모델 재적합이 아니다 — 적합 기준을 상위집합에
      고정하면 단조성은 "회복"되지만 부분집합 답이 **−12.5%**로 무너지고, 그 런의
      덱2는 현행 런의 덱2보다 **개별적으로도 나쁘다**(6.71B vs 8.57B). 근시안이
      아니라 순위가 틀린 것이다. 도구는 `$CLAUDE_JOB_DIR/tmp/probe_monotonicity_
      pairs.py`(스크래치 — 살릴 거면 `scripts/`로 옮기고 help·문서를 붙일 것).
- [x] **언덕오르기가 버스트 티어를 넘게 했다 — 완료.** 제보: 풍압 보스 5덱
      전부최적화에서 덱4의 이사벨을 솔린: 프로스트 티켓으로 바꾸면 딜이 오르는데
      엔진이 못 찾는다. 확인 결과 **+48.36%**(5,707,643,414 → 8,467,856,810)였고,
      이사벨 B3 / 솔린 B1이라 `_try_swaps`의 `burst_tier ==` 필터가 이 수를 **생성조차
      안 하고 있었다**(형태 (1,1,3) → (2,1,2), 둘 다 합법). 교차-티어일 때만
      `deck_is_valid`를 걸고 후보에 넣었다. Fienn 로스터 재실행에서 **덱1·2·3·5는
      스크린샷과 자릿수까지 동일**, 덱4만 바뀌어 합계 39,857,007,280 →
      **42,617,220,675 (+6.93%)**. 상세·기각안은 `docs/decisions.md`.
- [x] **`measure_swap_phase.py`의 커버리지 분모가 낡아 있었다 — 완료.**
      후보 규칙을 자체 구현해 둬서 교차-티어 도입 후에도 같은-티어만 세고 있었다
      (302% 보고 → 실제 193%). `_swap_is_fieldable`을 물어보게 바꿨다. **이 함정은
      이 저장소에서 두 번째**(앞선 사례: `measure_record_calibration.py`).
- [x] **시너지 쌍 점수의 단위 버그 — 수정 완료.** `scores`는 델타인데 쌍만 **덱 총딜**을
      넣어(1.68B vs 델타 +0.14B~-0.79B) `max()`가 자릿수만으로 항상 쌍을 골랐다 →
      멤버 4명이 **B2 캡 3자리를 독식**. 셸이 원래 앉혔을 두 B2 대비 **델타**로 바꿨다.
      펄링 **+4.07%**, 합계 불변. 상세는 `docs/decisions.md`.
- [x] **후보 풀 캡의 상한 = 0 — 측정 완료(`scripts/measure_pool_caps.py` 신설).**
      캡 4/6/12 · 6/9/18 · 8/12/24 · **10/12/36(전원)** 전부 합계 **42,617,220,675**.
      펄링은 +4.07%까지 오르지만 **스왑이 전부 씻어낸다.** 캡 12 = B2 전원이므로
      **시너지 쌍을 더 넣어도 이 로스터에선 값이 0**이다. 큰 로스터는 미확인.
- [x] **후보 풀이 CDR 유닛을 못 본다 — 점검 완료, 실재하지만 값은 0.** 전체 78유닛
      로스터에서 CDR 룰을 가진 유닛 **15명 중 11명이 풀에 한 번도 안 들어온다**. 갈림이
      선명하다: **딜도 하는 CDR은 티어 최상위**(rapi-red-hood-b1 +1.38B · anis-star
      +0.61B · moran +0.16B), **순수 서포터 CDR은 바닥에 큰 음수**(blanc -0.61B ·
      soline -0.46B · d-killer-wife -0.34B · helm-aquamarine -0.25B · liter -0.21B ·
      prika -0.19B) — 가치가 사이클 수로 **곱해지는** 유닛을 가법 모델이 못 매긴다.
      **그런데 합계는 안 움직인다**: 캡 확대가 55유닛(전원 10/12/36까지)과 전체
      78유닛(캡 2배) **양쪽에서 +0.00%**이고, 풀이 안 보여준 11명 중 **5명이 최종
      배분에 실제로 앉아 있다**(덱2~5에 하나씩). 흡수하는 것이 둘이다 — 캡은
      `remaining`이 줄어드는 **첫 필링에서만** 세게 물고, 언덕오르기는 풀이 아니라
      **전체 벤치**에서 끌어온다. 두 번째 경로는 **교차-티어 스왑이 착지하면서 비로소
      완성됐다**(B1 서포터는 대개 B3 자리를 뺏어야 들어간다). 캐비엇: 로스터 둘 ·
      보스 하나. 원래 근거: 솔린은 `prune_candidate_pool`(11개)
      에도 `widened_pool`(캡 B1=4, 22개)에도 없고, 대리모델 계수가 **B1 중 꼴찌
      -149,955,333**이다. 순수 CDR 유닛이라 가치가 덱 전체에 **곱해지는데** 대리모델은
      설계상 **가법**이라 구조적으로 못 맞힌다. 지금은 벤치 교차-티어 교환이 우회로
      역할을 하지만 **필링 자체는 여전히 눈이 멀어 있다**.
- [x] **`WEAPON_SYNERGY_ANCHORS` — 삭제 완료(고치는 대신).** 앵커가 리터럴 슬러그
      `"tove"`라 **애장품 없는 플레이어에겐 켜지고 있는 플레이어에겐 안 켜졌다**
      (Fienn 로스터는 `tove-signature`라 한 번도 안 돎). `character_of`로 일관되게
      켜보니 펄링은 **+4.0%**인데 **수렴 합계는 -1.02%**(42.617B → 42.185B, 62.7초
      수렴)였고, 앵커가 지키려던 덱은 **가드 없이 이미 찾힌다**(덱4 = 토브 + SG 4명).
      삭제는 Fienn 로스터에서 **무동작**(펄링·합계 자릿수까지 동일). 상세는
      `docs/decisions.md`. **테스트가 통과하던 이유가 버그가 산 이유와 같았다** —
      픽스처가 `FakeSpec("tove")`였다.
- [x] **단조성 위반 — 규명 완료, 고치지 않기로(Fienn).** 재현(현 트렁크): 58유닛
      **41,855,049,807** < 55유닛 **42,617,220,675**(55 ⊂ 58). 예산 문제가 아니다 —
      58유닛은 ~105초에 수렴하고 600초도 같은 값. **추가된 3명은 한 자리도 안 앉는다**;
      그런데도 펄링 덱이 전부 바뀐다(대리모델이 로스터마다 재적합 → 덱1이 디젤 대신
      미하라를 집고, 그 +0.13B가 덱5에서 -2.2B로 증폭). **언덕오르기는 멀쩡하다** —
      58유닛에 부분집합의 답을 완성 드래프트로 주면 **42,730,194,943**까지 올라간다
      (양쪽보다 높음). 즉 넓은 로스터가 더 좋은 답을 **실제로 갖고 있고 도달도 되는데**
      탐색이 나쁜 골짜기에 떨어질 뿐이고, 격차는 **2.09%**다.
      **배제된 수단(전부 실측):** top-4 첫 덱 다중출발 = **4배 비용에 0**(네 후보가
      전부 같은 코어의 변주라 그리디 경로가 같다) · 피팅 표본 200/400/800 = 격차
      6.11%/1.31%/2.59%로 **비단조**이고 어느 크기도 200표본 부분집합 펄링을 못 이김 ·
      풀 확대 = 0(위 항목) · 2:2·3덱순환 = 10배 비용에 1% 미만. 남은 수단은 진짜
      섭동(ILS)뿐인데 ~105초 등반의 배수라 응답성을 깬다. 재현은
      `scripts/measure_swap_budget.py`에 `--exclude` 두 벌.
- [x] **아군 스턴이 엔진에 없었다 — `self_stun` 신설로 완료.** 제보(질문): 마스트는
      앵커가 없으면 주기적으로 스턴에 걸리는데 버스트 턴에 걸리면 사이클이 지연된다,
      반영되나? **절반만이었다** — 스택 리셋(`1→2→3→1`)은 모델링돼 있었지만 **스턴이
      그녀의 버스트를 막는다**는 쪽은 없었고, 엔진 전체에 **아군 행동불능 개념이 없었다**
      (`burst_delay`·`max_bursts`뿐, 다른 `stun` 언급은 전부 적 기절). 실측: 덱 4에서
      마스트 버스트 8회 중 **2회가 스턴 창 안**(77.82s·153.54s). `burst_cycle`에
      `self_stun = {"seconds", "cycles"}` 신설, `_ready_at`이 쿨다운과 max를 취한다.
      스턴 시간은 스킬 데이터에서, 존재 여부는 **덱 의존**(앵커 유무)이라 조립 시점에
      읽는다. 결과: 버스트 8→7회, 스턴 창 안 **2→0**, 77.82s 버스트가 **85.30s로 밀림**
      (= 제보의 사이클 지연), 덱 4 **−9.67%**. 상세는 `docs/decisions.md`.
- [x] **동점 좌석 순서가 자기 딜레이와 모순됐다 — 완료.** 제보: 덱 4의 디젤(후버)이
      티어메이트보다 **왼쪽**이라 게임 규칙으로 읽으면 첫 사이클에 버스트해 Intro가
      걸린다. 시뮬은 옳았고(`skip_cycles`가 좌석과 무관하게 뺀다) **돌려준 순서**가
      틀렸다 — 티어 내부 순열을 전수 채점하니 두 B3 순서가 **자릿수까지 동점**이라
      엔진이 아무거나 골랐다. ① 동점이면 그대로 플레이 가능한 순서를 고르고
      ② 동점이 아니어서 홀드가 이기면 응답의 **`hold_burst_slugs`**로 덱 카드가
      "누구를 아껴야 하는지" 말한다. 선례는 `_buffer_seat_valid`. 상세는
      `docs/decisions.md`.
- [x] **브래디의 Taste를 덱이 유도하는지 안 보고 있었다 — 덱 합법성 규칙으로 완료.**
      제보: 덱 5 [목단, 아르카나, 나유타, 신데렐라, **브래디(지딜)**] — 넷 중 지속딜
      버프를 주는 유닛이 없다. 원문이 *"Activates when gaining a buff that increases
      sustained damage"*이고 Favorite Candy 두 불릿·New Flavor 3분의 2가 그 상태에
      걸려 있으므로, 인게임에선 켜지지 않는다. `bready.py`가 인코딩 때부터 캐비엇으로
      적어둔 갭. 실측 **못 내는 딜 1,066,561,255(덱의 18.7%)**, 게이트 제거 시
      **벤치 B3 27/32가 그녀를 이긴다**(최선 +18.34%) — 숫자만 부푼 게 아니라 추천이
      틀렸다. 힐·쉴드 제공자 목록과 같은 3단 구조(`provider_scan` 유도 →
      `_helpers` 상수 → 대조 테스트)로 유도 버퍼를 데이터에서 뽑고,
      `registry.TASTE_INDUCER_SLUGS` + `deck_search._taste_induced_valid`로 막았다.
      Ark: 레인저 블랙은 Wind AR 한정이라 `SUBSET_...`로 분리(브래디는 Water SR).
      **배선 지점은 넷이었다** — 생성기 3곳 + `deck_is_valid`만으로는 언덕오르기가
      동티어 스왑으로 되돌렸다. 검증: 덱 3에서 빠지고 **마스트 옆 덱 5에
      `bready-recommended`로 재등장**. 상세는 `docs/decisions.md`·`docs/insights.md`.
- [x] **스왑 예산을 벽시계에서 후보 교환 수로 — 재현성 착륙, 완료.** 제보: 같은
      로스터·같은 보스로 추천을 두 번 눌러도 다른 덱이 나온다(45초 3회 =
      28.05/23.86/28.17B). `PYTHONHASHSEED` 1·2 A/B로 실측하니 비결정 요소는
      스왑 단계의 벽시계 데드라인 하나뿐이었다(수렴 배분이 `6089389733.91905`까지
      일치). `SWAP_TIME_BUDGET_SEC`(초 단위, 아래 항목)을 걷어내고
      `SWAP_CANDIDATE_BUDGET = 20_000`(후보 교환 수 단위)으로 교체 — 등반은 수렴까지
      돌고 상한은 품질 노브가 아니라 폭주 방지 장치로만 남는다(배치 폭은 어느
      후보가 채택되는지를 안 바꾸므로 코어 수가 다른 머신도 수렴하면 같은 답).
      Fienn 로스터(78유닛 실사용)로 실측: 속성저지 on **3,331후보·140.6초**,
      off **3,735후보·120.8초** — 두 조건은 후보 수·시간이 **엇갈려** 움직인다
      (기믹 바닥 검사가 후보당 비용이라서). 상한은 후보로 세므로 후보가 더 많은
      쪽(3,735)을 기준으로 **20,000(5.4배)**을 골랐다(배수는 벤치 크기로 어림한
      것 — 3~5배는 측정이 아니라 추정). peel만(예산 0)은 28,990,691,285 —
      등반의 기여는 **+24.3%**. 대기는 나빠지지 않았다 — 전부최적화 182.2초·
      빈자리만 227.1초로 종전 188초·263.5초와 비슷한 폭이면서, 그때는 **잘린 채**
      그 시간을 다 썼고 지금은 **수렴한다**. 대기 문구 "보통 2~5분"은 유지
      (Fienn). 상세·기각안은 `docs/decisions.md`, 재사용 가능한 성질(배치 폭
      불변성)은 `docs/insights.md`. 기준선 백엔드 1905 → **1911 passed / 3
      skipped**, 프론트 522 → **523 passed**. 캐비엇: **로스터 하나**에서
      고른 숫자다.
- [x] **스왑 예산이 덱 1에서 다 새고 있었다 — 공평 배분 + 상한 180초, 완료.** 제보:
      수냉 약점·속성 저지 5덱 전부최적화가 덱 3에 이사벨을 앉히고 **드레이크를 벤치에**
      남겼는데, 바꾸면 **+969,725,138**(그 덱 +18.5%, 벤치 유닛이라 합계도 같은 폭
      **+3.46%**). `_try_swaps` 호출 전수 추적: **15개 작업 항목 중 앞 5개**(전부 덱 1의
      것, 벤치 패스 하나가 25.5초)가 45초를 다 쓰고 **나머지 10개는 데드라인이 지난 채
      진입해 후보를 0개 생성**했다 — 덱 2~5는 스왑을 한 번도 못 받는다. 먼저 기각한
      가설 둘: 캐스케이드 쇼트리스트의 늦은 기믹 필터(상위 20개가 **전부 통과**해 무관) ·
      climb의 좌석 순서 채점(고정=최선이고 climb 자신도 이 교체를 **수락**한다).
      수정 둘 — 항목별 균등 배분(수렴하면 no-op: 300초에서 구·신이 자릿수까지 동일) +
      `SWAP_CANDIDATE_BUDGET = 20_000`(2026-08-05에 폐지된
      `SWAP_TIME_BUDGET_SEC`을 대체 — 단위가 초에서 후보 교환 수로 바뀌었다).
      측정은 `--elemental-interrupt` 신설 후
      **45초 27.90B(잘림) · 120초 30.64B · 300초 30.66B(176.6초 수렴)**, 끝-끝
      112→188초. 상세·기각안은 `docs/decisions.md`, 계측 교훈은 `docs/insights.md`.
- [x] ~~**스왑 예산은 병목이 아니었다 — 측정 완료, 45초 유지.**~~ **→ 위 항목이 뒤집었다**
      (그때 적어 둔 잔여 리스크가 그대로 터졌다: 이 측정은 **풍압 보스 · 속성저지 없음**
      이었고, 속성저지를 켜면 45초는 확실히 잘린다). 원문: 신규
      `scripts/measure_swap_budget.py`(예산을 쓸어가며 **5덱 합계**를 찍는다 —
      `measure_swap_phase.py`가 후보/시뮬 수를 세는 것과 달리 목적함수를 직접 본다).
      Fienn 로스터·풍압 보스: 필링만 **34.84B**, 45초 **42.617B(+22.33%)**, 90·180·360초
      **전부 같은 42.617B**. 언덕오르기는 **~60초에 수렴**하고 45초는 확실히 잘리지만
      **그 15초가 사는 건 0**이다. 추천 품질의 대부분이 필링이 아니라 **스왑에서**
      나온다(+22.33%). 잔여 리스크: 다른 로스터에선 45초가 수렴 전에 자를 수 있다.
- [x] **1:1보다 넓은 이동집합 — 감사 완료, 착수하지 않기로.** 수렴한 배분에서
      세 이동 종류를 전수 감사했다: **2:2 덱↔덱 377개 중 개선 0건**(최고 -0.13B),
      **3덱 순환 1,104개 중 1건 +320,758,019(+0.75%)**, **2:2 벤치 11,185개 중 4건
      +233,762,514(+0.55%)**. 두 양수 클래스는 **더해지지 않는다** — 상위 이동이 전부
      "모더니아를 덱3에서 뺀다"는 **한 문제로 가는 두 경로**다. 비용은 패스당
      ~22,000 시뮬로 **현재 스왑 단계 전체(2,190)의 약 10배**. **10배를 내고 1% 미만**
      이라 기각. 캐비엇: 이건 **수렴점에서의 여지**라 넓은 이동집합을 climb *중에* 쓰면
      다른 골짜기로 샐 수도 있다(하한이지 예측이 아니다) · 로스터 하나·보스 하나.
- [x] **덱3의 모더니아 좌석 — 규명 완료, 고치지 않기로(측정 근거).** 모더니아
      자체가 아니라 **그가 만드는 자리**였다. `_BUFFER_SEAT_SLUGS`가 그를 자기 티어
      맨 뒤에 고정하는데, `_try_swaps`는 들어오는 유닛에게 **나가는 유닛의 좌석
      번호를 물려준다** — 그래서 프리카가 민트 뒤에 앉고, `SYNERGY_SETS`가 명시한
      "프리카가 민트보다 먼저 버스트해야 Encore가 넘어간다"가 깨진다. climb이 본
      값 **-618,171,538**, 실제 최선좌석 **+331,958,564**. 좌석 순서 하나가 그 덱의
      **26%**를 가른다. **저장소 안에 "덱의 값" 정의가 두 개**였던 것(필링·최종정리는
      최선좌석, climb만 임의 좌석). **그런데 네 가지 수정을 5덱 합계로 채점하니 전부
      졌다** — 상세 수치는 `docs/insights.md`. 정확한 채점이 틀린 게 아니라 후보당
      시뮬이 4~6배라 같은 시간에 이동을 1/5밖에 못 밟는다. 숨은 이득은 657개 중
      **2개, +0.78%**로 어떤 수정 비용보다 작다. 캐비엇: 로스터 하나·보스 하나이고
      시도한 네 가지가 설계의 전부는 아니다.
- [x] **형태별 라운드로빈 쇼트리스트 — 측정 후 기각(되돌림).** 가법 대리모델이
      **(2,1,2)를 5번의 필링 중 3번에서 0회 시뮬**로 굶긴다(최고 순위 #115·#68·#20).
      B1은 대개 서포터라 계수가 낮아, B1을 둘 앉히는 형태의 합이 구조적으로 낮게
      나오는 것 — **top-K 상향으론 못 고친다**(필링 1은 K=116 필요). 세 형태를
      돌아가며 K개를 채우게 고쳐보니 **설계대로 작동했다**(솔린 덱을 필링 4가 아니라
      **필링 2에서** 발견). 그런데 **합계는 42.617B → 42.401B로 -0.51%**. 좋은 덱을
      일찍 찾은 대가로 뒤쪽 덱이 쓸 유닛을 먼저 소비했다. **덱 하나의 탐색 품질을
      올리는 것과 합계를 올리는 것은 다른 일이고, 그리디 필링에서는 서로 어긋난다** —
      Fienn이 착수 전에 물어서 걸러냈다.

### 아핀 재장전 착륙 후속 (2026-07-31)

- [x] **아핀 재장전 모델 착륙 — 완료.** `파일값 × (1 − s) + 0.148초`, 분기 없는 한 식.
      s=0이 항등이 아니게 되어(무버프 = 파일값 + 0.148) 역수·거울대칭·항등을 고정하던
      테스트 셋은 삭제했고 실측 6점이 앵커로 들어갔다. 클립은 코드 무변경 —
      `user_roster`의 곱셈이 고정 구간을 탄창당 한 번으로 만든다.
      캘리브레이션 **1.015x → 1.055x · 21/25 → 19/25**(예상된 악화, 되돌리지 않음).
      기준선 백엔드 **1672 passed / 3 skipped**.
- [x] **평타 과대 항을 찾는다 (engine-gap #21) — 완료, 그런 항은 없었다.** 잔차가
      평타 **전용**이라는 것까지는 맞았다(회귀 a=0.85~0.90 · b=1.02, crown은 딜의
      100%가 평타인데 1.225x). 그러나 후보 셋은 전부 배제됐다 — `rate_of_fire`는
      클래스 **내** 분산이 더 크고(MG 혼자 k 0.70~1.24), 발수는 `per_shot_nuke`를
      같이 줄여야 하는데 그렇게 채점하면 악화(sd 0.085 vs 0.078)하며, 평타 FB
      보너스와 발당 데미지는 항목 18의 사격장 실측이 이미 확정했다. 남은 평타 전용
      항은 **코어 히트**뿐이고, 코어히트율은 **그 판의 플레이 조건**이다(파츠를 직접
      때린 좌석은 코어를 놓친다 — Fienn, 2026-07-31). **엔진 변경 없음.**
      바뀌는 것은 해석이다: `sim/record`는 코어 100%라는 **상한**이므로 **1.0보다
      위가 정상**. 진단 도구 `scripts/measure_normal_attack_residual.py` 신설,
      낡은 insight("25유닛이 100%를 지지한다" — 0.936x 기준선의 결론) 갱신.
- [ ] **차지 무기에서 고정 구간을 재측정한다.** 밀크(SR)·센티(RL)가 상수 0으로 읽힌다 —
      무버프 차지 무기 하나의 재장전을 프레임으로 세면 전역/무기군별이 갈린다.
      파일값 그대로면 무기군별, 파일값+9프레임이면 전역.

### 차지 계산기 정리 (2026-07-31)

- [x] **판별 스크립트를 오늘의 질문으로 교체 — 완료.** `find_charge_rule_discriminators.py`는
      규칙을 **자체 구현**해 뒀다가 규칙이 바뀌자 낡았다(옛 생합계를 "엔진"이라 출력).
      `scripts/audit_charge_speed_rolls.py`로 대체 — 엔진 함수(`charge_speed_percent_from_lines`
      · `charge_frames_bought`)를 **직접 부르므로 다시 드리프트할 수 없다**. 묻는 것도
      바뀌었다: "어느 유닛이 규칙을 판정하나"(끝난 질문) → "굴림을 모르면 어느 유닛의
      프레임이 안 정해지나".
- [x] **`sync_worktree_data.py`가 로스터 export를 하나만 옮기던 것 — 수정.** `SYNCED_FILES`가
      blessed 이름만 복사해서, 워크트리에서는 **굴림이 실린 최신 export가 아예 안 보였다.**
      이 스크립트가 존재하는 이유인 "없는 데이터가 틀린 결론이 된다"가 한 겹 안쪽에서
      재발한 것이다. 이제 `roster-drafts*.json` 전부를 옮긴다.
- [x] **blessed 기본 export를 최신본으로 교체 — 완료 (Fienn 결정, 2026-07-31).**
      `roster-drafts.json`(모든 스크립트의 기본값)은 07-27 export라 굴림이 없고 48유닛의
      ATK가 낮았다. 같은 계정의 `roster-drafts-jp-fienn.json`(07-31, 굴림 323/323)으로
      갈아끼웠고, 옛 파일은 `roster-drafts-jp-fienn-2026-07-27.json`으로 남겼다 —
      docs에 적힌 기존 캘리브레이션 숫자가 측정된 기준이라 재현 가능해야 한다.
      **캘리브레이션은 사실상 불변**: 실기록 25명 중 ATK가 바뀐 건 5명(각 +25)뿐이고,
      앵커 1.039→1.040 · 레드후드 0.982→0.983 두 자리만 움직였다. 합계 **1.015x ·
      21/25 그대로**. 굴림이 실리면서 애매하던 3기(ein·네온·rouge)도 전부
      **폴백과 같은 답**으로 확정됐다 — 굴림 부재가 지금 로스터에선 아무것도 안 틀리고
      있었다는 뜻이다.

### 적정사거리 배선 (2026-07-31)

- [x] **gap #16 배선 — 완료 (해소).** `BossProfile.effective_range_band`
      (`near`=SG·SMG / `mid`=AR·MG / `far`=SR, **RL은 어디에도 없음**, 기본 `None`).
      막고 있던 것은 배수가 아니라 **거리를 누가 정하느냐**였고, Fienn 판정은
      **스테이지·보스**다(니케 위치 고정 → 플레이어가 못 고른다). 그래서 코어 히트와
      달리 상한으로 켤 수 없다. 스코프는 코어와 동일(평타 전용 · `sustained`/
      `distributed` 제외). 모르는 밴드는 **ValueError**(조용히 아무도 안 주는 것과
      구분되지 않으므로). 신규 `test_effective_range.py` **8건**.
- [x] **실기록 보스는 mid — 반영 완료 (Fienn, 2026-07-31).** 애니힐리오가 mid
      적정거리라 **AR·MG가 보너스를 받았다.** 합계 **1.055x → 1.077x**, ±15%
      **19/25 → 16/25**, 백엔드 **1680 passed / 3 skipped**. 움직인 것은 AR·MG뿐
      (mast 1.305→1.446 · crown 1.225→1.367 · moran 1.009→1.095 · rei 1.008→1.066)
      이고 SR·RL·SMG는 불변, **미하라는 0.910→0.955로 개선**. 합계가 커진 것은
      engine-gap #21의 규약대로 되돌릴 신호가 아니다.
      **함정 하나 제거:** 세 스크립트가 `BossProfile`을 필드별로 조립하고 있어
      `RECORD_BOSS`에 사실이 추가돼도 안 따라왔다 — 전부 `**RECORD_BOSS` 전개로 바꿨다.

### ✅ 앱이 끝에서 끝까지 돈다 (2026-07-31, Fienn 라이브)

**로스터 동기화 성공 — 부계정 포함.** 얼린 앱을 켜고 blablalink에서 북마크릿을
눌러 로스터가 앱 화면까지 들어왔다. 부계정도 되므로 **여러 서버 후보 경로**도
같이 확인됐다. 이로써 ①실행셸+패키징과 ②동기화가 실사용으로 닫혔다.

**끝-끝을 돌려보고서야 나온 것들** — 조각별 테스트는 전부 통과하고 있었다:

- **인박스가 북마크릿의 실제 payload를 422로 거절했다.** 조립 API의 입력 모델로
  타이핑했는데 북마크릿이 보내는 것은 `{open_id, servers:[...]}`(서버 후보 목록)다.
  북마크릿에는 그것이 "앱을 찾지 못했다"로 보였다 — **앱은 응답하고 있었다.**
  테스트가 못 잡은 이유: 픽스처를 "상대가 보내는 것"이 아니라 "이 엔드포인트가
  받는 모델"로 썼다 — **같은 착각을 양쪽에 두 번** 했다.
- **SPA 폴백이 없는 자산에 index.html을 200으로 줬다.** 스크립트 태그가 HTML을
  받아 React가 마운트되지 않고, 증상은 원인이 한 마디도 없는 검은 화면이다.
- **북마크릿을 드래그로 건네고 있었다.** 네이티브 창에는 북마크 바가 없다 —
  복사 방식으로 교체.

**검은 화면 — 원인 밝혀짐, 복구 착륙 (2026-08-01).** 우리 코드가 아니었다.
오버레이 훅 소프트웨어 **RivaTuner Statistics Server**(MSI Afterburner 동봉)가
모든 프로세스에 주입되는데, WebView2의 **브라우저 프로세스** 안에서
`RTSSHooks64.dll +0x1490AF`가 `0xC0000005`로 죽는다 — 크래시 덤프 두 개가 같은
오프셋이고, Chromium 자신도 `third_party_modules`로 그 DLL 하나만 지목한다.
덤프는 `%TEMP%\tmp*\EBWebView\Crashpad\reports`에 있다(pywebview가 WebView2
프로필을 실행마다 새 임시 폴더에 만든다).

- **왜 오진했나:** 브라우저 프로세스만 죽고 pywebview 호스트는 살아남는다.
  프로세스 목록에 앱이 있고, 백엔드 포트가 계속 200을 주고, 브라우저로 열면
  멀쩡하다 — 세 신호가 전부 "우리는 정상"을 가리킨다.
- **실측 고장률:** RTSS 켬 **6/10**, 끔 **6/6**. 간헐적인 이유는 주입 타이밍
  레이스이고, 이것이 "재현되지 않았다"의 정체다.
- **막을 수는 없다.** 주입은 우리 코드보다 먼저 일어난다.
  `WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS`로 인자를 넣을 수는 있지만
  `--disable-gpu`는 **4/10**으로 오히려 나빴다.
- **그래서 복구한다.** `desktop.guard_webview()`가 `ProcessFailed`를 구독해
  (pywebview 6.2.1은 구독하지 않는다) 앱을 새 프로세스로 다시 띄운다. 4번까지
  시도하고 그 뒤엔 대화상자로 원인을 말한다 — 무한 재시작은 검은 화면보다 나쁘다.
  **복구 후 RTSS를 켠 채로 10/10.**
- **검증법:** RTSS가 죽여주기를 기다릴 필요 없다 — 브라우저 프로세스를 직접
  `Stop-Process`하면 WebView2에겐 같은 사건(`BrowserProcessExited`)이다.
  낡은 프로세스는 `os._exit` 뒤에도 **약 2.5초** 목록에 남으므로, 그보다 짧게
  확인하면 "창이 둘"로 오판한다.
- **곁다리로 드러난 것:** pywebview는 자리를 정해주지 않으면 WebView2 프로필을
  **실행마다 새 임시 폴더**에 만들고 지우지 않는다(한 번에 6MB). 재시작 경로가
  그 배수를 만들어서 `webview.start(storage_path=...)`로 자리를 못박았다 —
  `%LOCALAPPDATA%\RapiLab\webview\<포트>`, **인스턴스마다 하나**.
  **하나로 못박으면 안 된다:** 한 폴더를 두 인스턴스가 나눠 쓰면 두 번째의
  WebView2가 아예 뜨지 않는다. 백엔드는 둘 다 응답하는데 브라우저 프로세스는
  하나뿐이고, 두 번째는 **초기화 실패조차 보고하지 않아** 위 감시도 안 걸린다 —
  복구 없는 빈 창이다(실측으로 잡았다). 포트는 이미 인스턴스마다 다르고 후보가
  넷뿐이라 폴더도 넷을 넘지 않는다. 비공개 모드는 그대로다 — 쿠키·로컬 저장소를
  남기지 않는 것은 폴더 자리와 무관한 별개의 선택이다.

**유저가 겪으면:** RTSS는 `chrome.exe`·`msedge.exe` 프로필을 이미 갖고 있는데
(`ProfileTemplates`, `EnableHooking = 0`) **`msedgewebview2.exe`는 없다** — 딱
그 틈에 WebView2 앱이 빠진다. RTSS에 그 이름으로 프로필을 추가하고 application
detection level을 None으로 두면 재시작 자체가 일어나지 않는다. 프로필은 경로가
아니라 **실행 파일 이름**으로 매칭한다.

### 배포 전 점검 (2026-07-31)

- [x] **사거리 밴드를 추천 경로에 연결 — 완료.** 배선 직후엔 엔진과 실기록
      하네스에만 닿아 있어서 **유저 추천은 항상 밴드 없음**으로 돌았다(AR·MG 보너스 0).
      `BossProfileIn.effective_range_band` + 프론트 「보스 적정거리」 셀렉트.
      원인이던 **필드별 조립을 제거** — 세 엔드포인트가 `api.boss_profile()` 하나를
      쓰고 `BossProfile(**boss.model_dump())`로 펼친다. `test_api_boss_profile.py`가
      **두 필드 집합을 비교**해 다음 보스 필드는 추가되는 날 커버된다.
      백엔드 **1685 passed / 3 skipped** · 프론트 **453 passed**.
- [x] **코어히트율 100% 가정 안내 — 완료.** 「코어 피격 가능」 체크박스 힌트에
      "모든 평타가 코어에 명중한다고 가정(상한)이며 평타 비중이 큰 유닛이 실제보다
      높게 평가될 수 있다"를 명시. 근거는 engine-gap #21.
- [x] **패키징 블로커 5건 — 전부 해소 (2026-07-31).** `engine_version()`은 frozen에서
      스탬프를 읽고 없으면 **거부**한다(빈 다이제스트를 조용히 내던 것) ·
      numpy·starlette 선언 + `test_requirements`가 다음 누락을 잡는다 ·
      `__file__` 경로 5곳을 `app/paths.py` 하나로 · 캐시는 `%LOCALAPPDATA%`로 ·
      `freeze_support()` 배선 후 **얼린 exe에서 프로세스 풀 실동 확인**.
- [x] **pywebview 스모크 — 통과 (2026-07-31).** 격리 venv(Python 3.14.6)에서
      pywebview 6.2.1 · pyinstaller 6.21.0 · pythonnet 3.1.0(cp314 wheel) 설치되고
      **실제 창이 뜨고 `start()`가 반환**한다. 브레인스토밍의 유일한 미검증 가정이었다.
- [x] **①실행셸 + 패키징 — 완료.** `app/desktop.py`(uvicorn 스레드 → 응답 대기 → 창) ·
      FastAPI가 프론트를 같은 origin에서 서빙(SPA 폴백 포함, `/api/*`는 제외) ·
      `scripts/build_app.py` + `packaging/rapilab.spec`.
      **얼린 exe 검증 통과**: `RapiLab.exe --selftest` → 엔진버전 스탬프 읽힘 ·
      유닛 98 · 셸 서빙 · 프로세스 풀 정상, exit 0. 산출물 **95MB**.
      계획: `docs/superpowers/plans/2026-07-31-desktop-app-packaging.md`.
- [x] **②동기화 — 게이트 통과: 혼합 콘텐츠가 아니라 CORS였다 (Fienn 라이브, 2026-07-31).**
      blablalink 콘솔의 결과가 `net::ERR_FAILED **200 (OK)**` — **요청은 나갔고 서버가
      200을 냈다.** 브라우저가 loopback을 안전한 출처로 치므로 https→http 혼합
      콘텐츠는 애초에 적용되지 않는다. 막던 것은 `Access-Control-Allow-Origin`
      하나였고 그것은 우리 설정이다. → `api.ALLOWED_ORIGINS`에 blablalink 추가
      (목록에 적힌 출처만 허용되므로 아무 사이트나 로컬 서버를 못 부른다),
      `test_cors_for_sync.py` 4건이 프리플라이트까지 고정.
      **포트도 해결:** 셸이 OS 임의 포트를 받으면 북마클릿이 주소를 모르고, 하나로
      고정하면 그 포트가 쓰일 때 앱이 안 뜬다 → `desktop.SYNC_PORTS`
      (41573~41576) 중 **비어 있는 첫 번째**. 북마클릿의 같은 목록과 짝이다.
- [x] **②-b 인박스 + 로컬 POST 북마클릿 — 완료 (2026-07-31).**
      `POST/GET /api/sync-inbox`: 한 칸, 메모리에만, **가져가면 비운다**(안 비우면
      폴링하는 앱이 같은 로스터를 영원히 다시 집는다). 새 동기화가 앞의 것을 덮는다.
      `buildLocalSyncBookmarklet()`은 `window.open` 없이 `127.0.0.1`의 인박스로
      직접 POST하고 `LOCAL_SYNC_PORTS`(41573~41576 + 개발용 8000)를 훑는다.
      **두 빌더가 수집 소스를 공유**한다 — 같은 API 호출 4개가 두 벌로 갈라져
      있었고, 아무도 안 보는 쪽이 먼저 썩는다. 백엔드 **1720** · 프론트 **459**.
- [x] **②-c 폴링 배선 — 완료 (2026-07-31).** 훅에 인박스 확인 effect를 붙였다.
      **마운트 즉시 한 번** 확인하고(유저는 북마크릿을 누른 뒤 앱으로 돌아오므로
      그때 이미 차 있다) 이후 2초 주기. **idle일 때만** 돈다 — 후보를 고르는 중에
      새 payload가 오면 유저가 방금 누른 것과 다른 로스터가 들어온다. 폴링 실패는
      조용히 넘긴다(개발 중 백엔드 미기동).
- [x] **②-d postMessage 경로 폐기 — 완료 (2026-07-31).** 네이티브 창에는 닿을 수
      없는 경로라 소비자가 없었고, 두 경로를 남기면 **아무도 안 쓰는 쪽이 먼저 썩는다**
      (`closed_form.py`가 놓은 것과 같은 함정).
      **보관: `archive/postmessage-sync` 브랜치(`d828a34`)** — 두 경로가 공존하던
      마지막 시점이다. 웹 배포로 돌아갈 일이 생기면 고고학이 아니라 diff로 끝난다.
      함께 사라진 것: 팝업 차단 처리 · `window.open`을 첫 await 앞에 두게 강제하던
      **5초 transient activation 제약** · ready 핸드셰이크 · origin 주입 검증.
      **남은 것: payload가 도착한 뒤의 전부**(후보 선택·조립·상태기계와 그 테스트).
      제거된 테스트 3건은 커버리지를 판 것이 아니라 **대상이 사라진 것**이다
      (출처 검증 · `window.opener` · 리스너 중복 등록).
      프론트 **451 passed** · 백엔드 **1720 passed** · 빌드 정상.
- [x] **③배포채널 + ④자동업데이트 — 완료, 라이브 검증됨 (2026-07-31).**
      저장소 `fienn-eda/RapiLab` public 공개. `.github/workflows/release.yml`이
      `v*.*.*` 태그에 반응해 windows-latest에서 빌드 → **`--selftest` 통과 후**
      Release에 zip을 붙인다. 첫 릴리스 **v0.1.0(34.9MB)**.
      **자동업데이트 실동 확인:** v0.1.0을 설치·실행하니 스스로 v0.1.1을 받아
      교체하고 재시작했으며, 교체 후에도 앱이 살아서 서빙했다(설치 폴더 무결).
      오프라인에서는 조용히 건너뛴다.
      계획: `docs/superpowers/plans/2026-07-31-release-channel-and-auto-update.md`.
      **설계 요점:** 태그가 곧 앱 버전(`app_version.py`, `engine_version`과 별개 —
      소스 해시는 순서를 모른다) · Windows는 실행 중 exe를 못 덮으므로 교체는
      **앱 밖 배치 헬퍼**가 한다(앱은 스테이징 후 종료, 헬퍼가 3초 대기 →
      robocopy /MIR → 재실행) · **받다 만 zip이나 exe가 없는 압축은 교체를 걸지
      않는다**(그대로 밀면 설치본이 사라진다) · 얼리지 않은 실행은 업데이트 안 함.

### 미달 유닛 추적 (2026-07-31, 상한 해석이 만든 새 우선순위)

engine-gap #21이 `sim/record`를 **코어 100%라는 상한**으로 재정의했다. 그 귀결:
**1.0 미만인 유닛은 변명의 여지가 없는 갭**이다 — 엔진이 실제보다 유리한 조건으로
계산하고도 모자란다는 뜻이고, 실제 코어율이 100% 미만인 만큼 미달은 **더 크다**.
캐비엇을 뺀 1.0 미만은 넷뿐이다: **mihara 0.910** · cinderella 0.976 ·
snow-white 0.998 · scarlet 0.999. 뒤 셋은 오차 범위이므로 실질 대상은 하나다.
(사거리 mid 반영 후 mihara는 **0.955**, 나머지 셋은 불변 — 미달은 줄었지만 남았다.)

- [ ] **mihara-bonding-chain 0.895x — 지속딜이 캡에 포화된 채 부족하다.** 그녀 딜은
      `scheduled` 지속딜 58% + 평타 42%이고 (deck5에서 버스트 **0회**, 실기록대로)
      지속딜은 `sustained` 타입이라 **코어 보너스를 아예 못 받는다** — 그래서 코어율
      가설로는 그녀를 못 건드린다(필요 p가 1.594로 범위 밖).
      **확인된 것 (2026-07-31):**
      - 스택이 **캡 20에 포화**돼 있다. 캡만 20 → 25로 올리면 0.877B → **0.997B**로
        움직인다(record 0.964B ≈ 캡 23.6). 즉 캡이 그녀 딜을 정하고 있다.
      - **인코딩·데이터·원문이 전부 일치한다.** 원문(lootandwaifus level 10)은 캡 20,
        지속딜 25.08%/1초, 충전은 배틀스타트와 "자기 버스트 후 FB 종료" 둘뿐,
        Tighten Up은 FB 중 평타 40회당 +1 — 모두 인코딩된 그대로다. 인코딩 오류가 아니다.
      - 버프 게이팅도 정상: `sustained` 인스턴스는 상시 버킷(`attack_damage_up`)과
        타입 버킷(`sustained_damage_up`)을 둘 다 받는다(`_TYPE_BUCKETS`).
      - 방출을 매 FB로 늘려 보면 0.877B → 0.914B에 그친다 — 방출 횟수로는 못 메운다.
      - **파츠 가설 기각 (Fienn, 2026-07-31).** 원문이 타겟을 복수형으로 쓰지만
        ("the same enemy **units**", "on each target") **지속딜은 보스 본체에만
        들어간다.** 복수형은 잡몹 다수 상황의 문구다 — 파츠를 별도 타겟으로
        모델링할 이유가 없다.
      **남은 것:** 미달 17%의 출처는 미상이다. 인코딩·데이터·원문·버프 게이팅·방출
      횟수·파츠가 전부 배제됐으므로, 다음 수는 **그녀 하나만 사격장에서 재는 것**이다
      (스택 20에서 지속딜 1틱이 실제로 얼마인지). 실기록 총딜의 2.8%짜리 유닛이라
      우선순위는 낮다.

### 택티컬 베어 후속 (2026-07-31, 탄환 환급 착륙 직후 열림)

- [x] **택티컬 베어를 낀 유닛 명단 — 완료 (2026-07-31).** 흑련 + **기본 신데렐라**
      (크리스탈 웨이브 아님). 신데렐라는 탄창 24발이라 재장전을 적게 하는 쪽이 유리해
      탄약 슬롯이 재장전 슬롯을 이긴다(Fienn). 신데렐라 0.971x → **0.975x**,
      deck4 1.004x → 1.006x, 덱메이트 4명 불변.
- [x] **명단은 여기서 끝난다 — 나머지는 채울 수 없다 (Fienn, 2026-07-31).** 다른 유닛은
      **덱 조합과 취향에 따라** 큐브가 갈린다. 즉 큐브는 캐릭터의 속성이 아니라 유저의
      선택이며, 이 사실이 아래 UI 항목의 근거다 — 전역 가정으로는 원리적으로 못 맞춘다.
- [ ] **유저 큐브 선택 UI (defer 중).** `NikkeSpec.cube` 필드는 이미 있고 기본값이
      렐릭 베어다. `UserNikkeState`로 필드를 올리고 프론트 셀렉트를 붙이면 되는 크기.
      착수 조건: 렐릭/택티컬 둘로 부족해지면 큐브 카탈로그 수집이 선행돼야 한다.
- [ ] **변신 세그먼트의 발이 환급 카운터를 올리는지 인게임 확인.** 현재 엔진은 "이 탄창을
      소모하는 발만 센다"로 가정한다 — 진짜 변신(다른 무기가 장전된 채 온다)은 제외,
      `shares_magazine`은 포함. 흑련은 변신 딜이 커서 이 가정이 그녀의 숫자를 움직인다.
- [ ] **탄창이 빈 상태(재장전 중)에서 카운터가 10에 닿으면 그 3발이 어디로 가나.**
      흑련 격자에서는 발생하지 않아(환급은 늘 탄창 8발일 때 떨어진다) 지금은 무해하지만,
      탄창이 더 작은 유닛에서는 갈린다.
- [x] **합계가 1.011x → 1.015x로 멀어진 것을 추적한다 — 완료 (2026-07-31).** 둘을 같이
      봐야 한다는 읽기는 맞았고, 답은 **가려진 과대 항이 아니었다**: 두 수정 모두 평타를
      정확하게 만들었고, 엔진이 코어 100%(그 판의 실제 조건이 아닌 **상한**)를 가정하는
      한 평타가 정확해질수록 합계는 커진다. engine-gap #21 · `docs/decisions.md`
      "코어히트율은 엔진에 넣지 않는다".

### 클립형 재장전 (2026-07-30, Centi 인코딩에서 발견)

- [x] **클립 무기의 분할 재장전을 모델링한다 (engine-gap #19) — 완료 (2026-07-31).**
      Centi 발당 1.45 → **1.6167초**(Fienn 실측), 60초 발수 41 → 37.
      - [x] 클립형 유닛 명단 확정 — **실측은 필요 없었다.** 분할 수는 ShiftyPad 원본
            `shot_detail.reload_bullet`에 있다(10000 = 탄창 100%를 한 번에).
            정규화가 무기 6필드만 뽑아 안 보였을 뿐. 명단은 **9슬러그**이고
            런처·샷건뿐 아니라 **Grave(AR)** 도 포함이다.
      - [x] `reload_splits` 도입 — 단, `attack_rate`가 아니라
            `user_roster.load_nikke_spec`이 `reload_time`에 한 번 곱한다.
            `attack_rate.py`는 무변경(`reload_time_with_speed`가 선형).
            값은 `registry.CLIP_RELOAD_SPLITS`, 대조는 `audit_weapon_data.py`.
      - [x] `centi-signature`의 유효 쿨다운 재확인 — 5.7378 → **5.9605초**로
            전파되며 테스트가 양쪽을 고정한다.
      - [x] 덤: `sync_worktree_data.py`가 하위 디렉터리를 안 옮겨 워크트리에서
            `audit_weapon_data.py`가 항상 "no-live 95"였던 것을 고쳤다.

### `closed_form` 발수가 시뮬 발수와 어긋난다 (2026-07-31, gap #19 작업 중 발견)

- [x] **`closed_form`을 삭제했다 (engine-gap #20 해소, 2026-07-31).** 고칠 갭이
      아니라 지울 코드였다. `_shot_count`가 차지 모션 딜레이를 안 접어 시뮬과
      발수가 달랐지만(**14슬러그**, 센티 60초 48 vs 37, 흑련 180초 346 vs 189),
      **프로덕션 어디에서도 안 쓰이는 기각된 스코어러**(옵션 B)라 그 어긋남이
      아무것도 안 바꾸고 있었다 — 남아 있는 것 자체가 오해의 원인이었다.
      백엔드 1689 → **1667 passed/3 skipped**(삭제분 22건과 정확히 일치).
      - [x] `validate_surrogate_recall.py`는 `--surrogate closed-form` 모드만 잃고
            회귀 대리모델 검증용으로 유지. `measure_unmodeled_damage_share.py`는
            애초에 임포트하지 않아 무변경 — **기각 근거는 계속 재생산 가능하다.**

### 추천 기능 라이브 감사 (2026-07-25, 실제 로스터 159기로 브라우저 실행)

- [ ] **what-if 판독이 실측 적합보다 코어당 3.241 ATK 낮다 (원인 미상).** ShiftyPad에서
      코어만 바꿔 읽은 값이, 같은 유닛(Naga — 159기 기준값에 코어 7로 존재)의 기준값
      유도치보다 일정하게 낮다. 오프셋의 HP:ATK 비가 125로 base(30)도 core_flat(55)도 아니다.
      표 값은 159기 실측 적합에서 오므로 **현재 영향 없음**. 앞으로 what-if 판독으로
      절대값을 정하려 할 때만 문제가 된다 — 그때는 이 오프셋을 먼저 규명할 것.
- [ ] **한글화 후속 ①: 엔진 미지원 ~95기.** `supported-units`에 없어 위 경로로 안 덮인다.
      로스터 그리드에만 보이고 지금은 슬러그에서 유도한 영문이 뜬다. 인코딩 101슬러그는
      전부 채워졌으므로 착수 가능.
      **이름 규칙(Fienn, 2026-07-26): 한국 서버 공식 표기를 따른다 — 음차가 아니다.**
      대부분은 음차와 같지만(드레이크·라플라스·프리바티) 아닌 경우가 있다: `moran`은
      "모란"이 아니라 **"목단"**, `dolla`는 "돌라"가 아니라 **"도라"**다.
      **표기는 이제 `nikke-directory.json`의 `name_ko`에 196개 전부 있다**(2026-08-08) —
      손으로 남은 건 슬러그↔유닛 대응과 구분자 관례(`": "`)뿐이고, 이 유닛들은 모드
      변형·애장품 쌍이 아니라 그 판단조차 거의 없다.
- [ ] **한글화 후속 ②: UI 크롬.** "Boss profile"·"Recommend decks"·"Units to use" 등
      화면 문구가 영어다. 언어 전환 구조는 만들지 않기로 했다(한글 고정).
- [ ] **⚠ 게이지 충전은 덱 속성인데 상수 하나로 모델링돼 있다 — 현재 2.4초.**
      **값의 근거(실측, 2026-08-05):** CDR 7.48초 유닛이 든 덱을 게이지까지 최대한
      빠르게 컨트롤하면 **15번째 풀버스트가 t≈179**다. 게이지가 병목인 동안 사이클
      간격은 CDR과 무관하게 `FB 10.0 + 게이지 + 티어갭`이므로 그 한 시각이 값을
      유일하게 정한다: `143.0 + 15g = 179` → **g = 2.4**.
      `test_default_gauge_reproduces_the_measured_fifteenth_full_burst`가 이 산술을
      못박는다. **2.467부터는 절벽** — 15번째가 전투 밖으로 나가 사이클을 통째로 잃는다.
      **남은 문제는 상수라는 것 자체다.** 실제 게이지는 **가한 대미지**로 차서 편성마다
      다르고, 두 실측이 실제로 어긋난다 — 볼륨 편성은 같은 180초에 **14회**(14번째 2:57),
      위 CDR 편성은 **15회**다. 현재 값은 빠른 쪽을 따르므로 **볼륨 편성은 한 사이클
      많게** 모델된다. 결정 배경과 기각한 대안은 `docs/decisions.md`.
      **해소하려면** 게이지를 보스 속성이 아니라 **덱 속성**으로 승격해야 한다 —
      대미지/발사 수에서 채움 속도를 유도하는 모델이 필요하고(순환 의존이라 1회
      반복 근사 등), 그건 별도 설계 건이다. `burst_gauge_fill_speed_percent`
      (Anis: Star)가 "의도된 미구현"으로 남아 있는 것도 같은 뿌리다.
- [ ] **신데렐라 버스트의 다단히트는 동시가 아니라 0.2초 간격 순차다 — 미반영.**
      Fienn 실측(FB 잔여 9.05 → 7.25): 10히트가 **1.80초**에 걸쳐 0.200초 간격.
      `raid_simulator`는 "All N hits land at the same instant"로 주석까지 달고 동시
      처리한다. 그리고 불릿2는 **1회 넉이 아니라 히트마다 붙는 라이더**다 — 아름다움
      0스택 캐스팅에서 t=3(1스택) 이후 남은 **정확히 4히트**만 대미지가 들어갔고,
      0.2초 간격 모델이 이를 정확히 재현한다(t=1.95부터 3.15/3.35/3.55/3.75).
      불릿2는 FB 보너스도 받는다(위 M₂/M₁=1.5). 셋 다 그녀를 **키우는** 방향이다.
- [ ] **에이드: 에이전트 바니 1.57x는 관통과 무관한 별개 문제.** 그녀는 관통 보유자라
      위 모델에서 값이 안 변한다. 딜이 100% 평타(0.16B, 169발, SR)뿐이라 원인은
      그녀의 무기 프로필 또는 받는 버프 쪽이다.

**완료 42건** — 한 줄 요약. 각 항목의 전문은 git 이력에 있고,
결정은 `docs/decisions.md`, 교훈은 `docs/insights.md`, 갭은
`docs/engine-gaps.md`가 들고 있다.

| 날짜 | 항목 | 결과 |
|---|---|---|
| 07-25 | 레이드 할당이 한 캐릭터를 두 덱에 세우던 버그 — 완료 | 백엔드 1358 → 1361 passed |
| 07-25 | 프론트/백엔드가 base 슬러그를 두고 어긋나던 문제 — 완료 | Roster 타일 70 → 73 · 접힌 목록 89 → 86 |
| 07-25 | 드래프트에서도 이 3명을 앉힐 수 있게 — 완료 | 백엔드 1365 → 1367 passed · 프론트 268 → 270 passed |
| 07-25 | Account 드롭다운이 닉네임 대신 uid로 되돌아가던 원인 — 완료 |  |
| 07-25 | 부계정 싱크가 500으로 죽던 원인 — 완료 | 백엔드 1367 → 1369 passed · 프론트 272 → 274 passed |
| 07-25 | PILGRIM Supporter 코어당 플랫 + 스탯 모델 수정 — 완료 |  |
| 08-09 | 닉네임을 못 읽은 싱크가 조용히 성공한다 — 완료 |  |
| 07-25 | 드래프트 좌석이 적으면 사실상 응답이 안 온다 — 완료 | 백엔드 1371 → 1382 passed |
| 07-26 | 표시 이름 한글화 — 완료 |  |
| 07-28 | 정체성 그룹과 후보 팬아웃을 분리 — 완료 | 백엔드 1519 → 1529 passed |
| 07-26 | 추천 요청 취소 — 완료 |  |
| 07-26 | 시뮬 딜이 실기록 대비 1.46배 과대 — 코어 판정 + Moran 쿨감 수정 완료 | 결과 합계 1.46x → 1.08x · 93~2.00x → 0.87 |
| 07-26 | 덱1의 과소평가(0.87x) 규명 — 완료 | Liberalio 2.076B → 3.177B · 덱1 → 11.92B |
| 07-26 | 버스트 넉의 Full Burst 보너스 배선 — 완료 | 덱1 0.96x → 0.98x |
| 07-26 | 전 유닛 죽은-인코딩 감사 — 완료 | 에인의 차지 대미지 버프 2개가 죽어 있었다 · 0.347B → 0.682B |
| 07-26 | 덱2~5 유닛별 대조 착수 — Privaty의 중첩 디버프 수정 | 나유타 1.10→0.96 · 리틀머메이드 1.13→0.99 |
| 07-26 | "Damage to Parts"를 몸통 딜에서 제외 — 완료 | 스노우화이트 1.44x → 1.12x · 덱4 1.14x → 1.02x |
| 07-26 | 차지 대미지를 차지 무기 한정으로 게이팅 — 완료 | 프리바티 2.01x → 0.97x · 리틀 머메이드 0.99x → 0.55x |
| 07-26 | 탄약 소모량 카운터를 라운드 단위로 배선 — 완료 | 리틀 머메이드 0.55x → 0.76x · 덱2 0.76x → 0.82x |
| 07-26 | 나유타 풀차지 넉에 FB 보너스 부여 — 완료 | 나유타 0.79x → 0.85x |
| 07-26 | "시전자 기준"의 정의 확정 — 완료 |  |
| 07-26 | 오버로드 ATK%는 `caster_atk`에 넣지 않는다 — 확정 | 포함 시 유닛별 평균 절대오차 0.178 → 0.192 |
| 07-26 | "코어 명중 대미지"에 코어 보너스 배선 — 완료 | 신데렐라 MG 0.84x → 0.89x |
| 07-26 | 나유타·리틀머메이드 4항목 확인 완료 (Fienn, 2026-07-26) |  |
| 07-26 | 리틀 머메이드 전수 검증 완료 — 특정 결함은 남아 있지 않다 | 원문 전 불릿을 Fienn 확인과 대조 |
| 07-26 | 신데렐라 버스트 1번 불릿 검증 |  |
| 07-26 | 관통을 속성으로 배선 — 완료 | 덱5 1.14x → 1.03x · 덱4 1.01x → 0.90x |
| 07-26 | 잔여 편차의 공통 원인 조사 — 없음으로 결론 |  |
| 07-27 | 홍련(스칼렛: 블랙 섀도우) 조사 완료 — 결함 없음 |  |
| 07-27 | 차지 대미지를 평타 전용으로 게이팅 — 완료 | 홍련 1.12x → 0.62x · 신데렐라 0.88x → 0.61x |
| 07-27 | 홍련 단계 넉에 FB 보너스 부여 — 완료 | 홍련 0.62x → 0.76x · 덱1 0.688x → 0.757x |
| 07-27 | 홍련의 실기록 기준선은 유효하다 (Fienn, 2026-07-27) |  |
| 07-27 | 단계 카운터의 버스트 경계 인계는 정상 |  |
| 07-27 | 마스트: 로맨틱 메이드 스택 조사 — 결함 2건 수정 | 홍련 0.76x → 0.90x · 덱1 0.757x → 0.837x |
| 07-27 | 분산 대미지 전수 감사 — 완료 |  |
| 07-27 | Shooting Stars에 FB 보너스 부여 — 완료 | 아니스 0.748B → 0.816B · 덱1 0.837x → 0.842x |
| 07-27 | 신데렐라 검증 — 결함 3건 수정 | 단계-3 ATK 트리거 · 퍼샷 넉 FB 보너스 · Beautiful의 Max HP 스택 |
| 07-27 | 볼륨 CDR 티어는 누적이다 — 확정·반영 (Fienn, 2026-07-27) | 실측 덱4 1.24x → 1.53x · 180초 풀버스트 11 → 14 |
| 07-27 | 볼륨의 Drop the Beat 크리 대미지가 처음부터 최대치 — 수정 완료 | 덱4 1.24x → 1.24x |
| 07-27 | "버스트 N단계 진입 시" 배선 전수 정리 — 완료 | 실측: 덱4 1.19x → 1.24x · 스노우화이트 1.00 → 1.06 |
| 07-27 | ★ B3의 자기 버스트가 `full_burst_enter` 버프를 먹는다 — 수정 완료 |  |
| 07-29 | "버스트 N단계 진입 시" 전수 감사 완료 — 결함 2건 추가 적발 |  |

### 2026-07-26~27 캘리브레이션 세션 요약

실기록 5덱 대조로 **엔진 결함 9건**을 찾아 고쳤다. 패턴이 반복됐다: **가짜 배수를
걷어내면 그 아래 깔려 있던 과소 모델링이 드러난다** — 그래서 수정 직후 수치가 나빠
보이는 것은 진전이다.

| # | 결함 | 효과 |
|---|---|---|
| 1 | 버블 배러지 카운터가 **총알**을 셈(파우치 라운드 무시) | 리틀머메이드 0.55→0.76 |
| 2 | 차지 대미지가 **비차지 무기**에도 적용 | 프리바티 2.01→0.97 |
| 3 | 차지 대미지가 **스킬 넉**에도 적용(평타 전용 위반) | 스노우화이트 1.12→0.97 · 네온 1.25→1.18 |
| 4 | **관통** 대미지 증가가 관통 없는 유닛에게도 적용 | 민트 1.19→1.00 · 아크레인저 1.18→1.08 |
| 5 | **코어 명중 대미지**가 코어 보너스를 못 받음 | 신데렐라MG 0.84→0.89 |
| 6 | FB 보너스: **연산 시점** 원리 미적용(3유닛) | 나유타 0.79→0.85 · 홍련 0.62→0.76 · 아니스 +9% |
| 7 | 마스트 취기 스택을 **자기 발동 횟수**로 셈 | 버스트 버프가 매번 1스택 부족 |
| 8 | 마스트 **분배 대미지 버프 누락**("survivability"로 오분류) | 홍련 0.76→0.90 |
| 9 | Quency 버스트가 **분산 타이핑 누락** | 자기 +49.58% 버프도 못 받던 상태 |

**확립된 원칙 4개** (상세는 `docs/decisions.md` · `docs/insights.md`):
- **FB 보너스의 기준은 연산 시점**이다 — "추가 대미지" 문구는 그 대리 지표.
- **차지 대미지는 평타 전용**이고, 판정은 무기 종류가 아니라 **그 순간의 창**이다.
- **관통은 버킷이 아니라 속성**이다 — [관통 특화] 보유자에게만.
- **"시전자 기준"은 기본 스탯**(장비·큐브·소장품 포함, 전투 중 버프 제외)이다.

**검증으로 확정된 가정 2개**: 분산 대미지는 단일 보스에게 전량 적용(툴팁) ·
차지 대미지 없는 홍련은 0.62x라 실기록이 문서 쪽을 지지.

**기각된 가설**: 잔여 편차의 공통 원인 — 미모델 항목 수 · 속성 우위 · 코어 히트
노출도 · 무기 종류 · 덱 단위 원인을 모두 실측 기각(`docs/insights.md`).

백엔드 테스트 1413 → **1447 passed / 3 skipped**.

- [ ] **To-Do: 절대 오차 순 — 아스카 +0.130B · 스칼렛 −0.124B · 레이 −0.090B ·
      미하라 −0.088B · 크라운 +0.087B.** (아크레인저 +0.196B는 결정에 따라 **제외** —
      `docs/decisions.md` 참조)
      현재(차지 프레임 스냅 되돌린 뒤, 2026-07-30): 덱1 **0.990** · 덱2 1.019 ·
      덱3 1.027 · 덱4 1.004 · 덱5 1.040, 합계 **1.011x**, **±15% 이내 21/25**.
      스칼렛 개별은 **0.981x**. (스냅이 들어가 있던 동안은 덱1 0.988 · 합계 1.010x ·
      스칼렛 0.977x였다. 되돌린 근거는 `docs/decisions.md` 최상단 — 본계정 6창이
      스냅 없는 모델과 1.6σ로 맞는다. 이 절의 다른 항목들이 "수치 불변"이라고 적은
      것은 **같은 베이스에서의 A/B**를 말한 것이라 어느 쪽이든 유효하다.)
      배수 최악(캐비엇 제외)은 **볼륨 1.244x**(SMG라 차지 딜레이 설명 밖) ·
      **헬름(애장품) 1.243x**(2026-07-29 딜레이 실측 → 0.40 확정, **다른 층**) ·
      **크라운 1.177x**. 에이드 1.498x는 캐비엇으로 빠졌다.
      **※ 절대 오차 줄은 Fienn이 접었다 (2026-07-29):** 엔진은 크리티컬을 기댓값으로
      계산하는데 실기록은 RNG가 박힌 **1회 시행**이라, 아스카 +0.130B(2.805B의 4.6%)
      급의 편차는 **크리 산포 안**이다. 이 층을 더 깎는 것은 노이즈를 쫓는 것이다.
- [ ] **부위파괴 이벤트 갭은 후순위로 확인됐다 (2026-07-26 실측).** 실기록 5덱을
      floor/ceiling 양쪽으로 재보니 차이가 **덱5만 6.6%, 합계 0.9%**라 ROI가 낮다.
      (열린 갭 목록은 `docs/engine-gaps.md`가 들고 있다.)
- [ ] **UI 크롬 한글화 스펙 리뷰 중 나온 백로그 1건 (2026-07-26, 아직 미설계 — 범위 밖,
      캡처만).** `docs/superpowers/specs/2026-07-26-ui-chrome-korean-localization-design.md`
      리뷰 중 Fienn이 별도 세션감으로 떠올린 것:
      - Roster/Recommend/Sync를 사이드바 탭으로 재구성 — 지금은 `App.tsx`에 "Roster"·
        "Recommend" 탭 2개뿐이고 Sync 패널은 Roster 탭 안에 얹혀 있다. 이건 네비게이션/
        레이아웃 구조 변경.

**완료 29건** — 한 줄 요약. 각 항목의 전문은 git 이력에 있고,
결정은 `docs/decisions.md`, 교훈은 `docs/insights.md`, 갭은
`docs/engine-gaps.md`가 들고 있다.

| 날짜 | 항목 | 결과 |
|---|---|---|
| 07-27 | ★ 대조 하네스가 엉뚱한 보스와 싸우고 있었다 — 정정 완료 | 합계 0.741x → 0.914x · 덱4 1.533x → 1.081x |
| 07-27 | 실기록이 드디어 픽스처가 됐다 |  |
| 07-27 | 소장품 스킬 효과 배선 완료, 캘리브레이션은 아직 무변동 |  |
| 07-27 | 소장품 데이터 부채 종결 — 전 등급(R/SR/SSR) 실데이터 |  |
| 07-28 | 엔진 결함 2건 수정 — 합계 0.936x → 1.011x, 미달이 반감됐다 |  |
| 07-28 | 아스카의 자기 디버프가 통째로 빠져 있었다 — 1.192x → 1.055x | 덱3 1.100 → 1.037 · 합계 1.011x → 1.000x |
| 07-28 | 아르카나의 페이즈 회전 인코딩 — 그녀 +11.7%, 덱 총딜 +2.40% |  |
| 07-28 | 아니스:스타 조사 — "추가 대미지" per-shot 넉이 FB 보너스를 못 받고 있었다 | 아니스 0.703x → 0.739x · 덱1 0.946 → 0.977 |
| 07-28 | FB 보너스 판정을 「연산 시점」으로 확정하고 문구 규칙을 삭제 — ±15% 이내 13/25 | 결과: 리틀머메이드 0.850→1.048 · 미하라 0.753→0.909 |
| 07-28 | 스노우화이트 재감사 — Fully Active가 탄창을 공유한다 (2026-07-28). 1.386x → 1.320x |  |
| 07-28 | 차지 모션 딜레이 배선 완료 — ±15% 이내 13/25 → 14/25 | 스칼렛 0.981→0.559 · 신데렐라 0.971→0.654. |
| 07-28 | 실제 편성 순서로 채점 — ±15% 이내 14/25 → 16/25 | 효과: 합계 1.030x → 1.025x · 아크레인저 1.183→1.113 |
| 07-28 | 네온의 화력게이지를 3버스트 주기로 정정 — 1.306x → 1.013x | 효과: ±15% 이내 16/25 → 17 · 합계 1.025x → 1.015x |
| 07-28 | 아니스의 슈팅스타는 소환체의 사격이다 — 0.739x → 0.946x | 효과: 덱1 0.977 → 1.000x · ±15% 이내 17/25 → 18 |
| 07-28 | Pierce Damage Up이 스킬 딜에 새고 있었다 — 스노우화이트 1.110x → 0.999x | 효과: 덱4 1.077 → 1.033 · 합계 1.023 → 1.018 |
| 07-28 | 민트·프리카 차지 모션 딜레이 실측 배선 — ±15% 이내 18/25 → 20/25 | 효과: 민트 1.502→1.107 · 프리카 1.353→1.087 |
| 07-29 | 헬름·브래디·벨벳 차지 딜레이 실측 — 빌려 쓴 0.40이 맞았다 |  |
| 07-30 | 브래디 차지 실측 — 차지속도가 프레임 격자에 앉는 것을 확정, 0.01초 반올림 기각 | 백엔드 1609 → 1611 passed |
| 07-30 | 프리카 차지 실측 — 정수 % 반올림 확정, 오버로드 굴림을 실어 나르도록 배선 | 효과: 캘리 합계 1.0109 → 1.0110x · 앵커 1.016 → 1.039x |
| 07-28 | 에이드 0.35초 · 앵커 0.4초 실측 배선 + 차지 딜레이 전수 감사 | 앵커 1.406x → 1.016x |
| 07-29 | 덱1·덱2 좌석 순서 확보 — argmax 채점이 완전히 사라졌다 |  |
| 07-29 | 에이드 캐비엇 — 그녀의 기록은 인코딩이 아니라 기록을 측정한다 |  |
| 07-27 | 재동기화 완료 — 소장품이 캘리브레이션에 실제로 들어왔다 | 합계 0.914x → 0.936x · 덱별 0.842→0.867 |
| 07-27 | 소장품 레벨 0의 의미 확정 — 엔진은 이미 맞게 하고 있었다 |  |
| 07-26 | 덱 데미지 내역이 총합의 22~72%만 설명하던 문제 — 완료 | 백엔드 1413 → 1415 passed |
| 07-26 | 보스 설정 위치 — 완료 |  |
| 07-28 | 니케 검색·정렬·필터 + 로스터 탭 버스트 분류 — 완료 | 프론트 301 → 350 passed |
| 07-27 | 동기화 도움말 패널 — 완료 | 프론트 294 → 299 passed |
| 07-29 | RapiLab 개칭 + 실행 버튼 상시 노출 — 완료 |  |

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
- [x] **UI 시각적 완성도 — 완료 (2026-07-25).** 다크 단일 테마, Roster 얼굴 그리드
      (지원 70 + 접힌 미지원 89), 덱 슬롯을 게임 스쿼드 슬롯처럼(정사각 얼굴 5칸,
      덱 간 드래그 이동), 결과 화면 얼굴 로우, 오버로드 순서 고정, 돌파/코어 배지.
      프론트 234 → 264 passed. `decisions.md`·`insights.md`(Frontend)·
      `docs/superpowers/specs/2026-07-25-ui-visual-completeness-design.md`.
- [x] **draft 배치가 마우스 전용 — 해소.** 2026-08-09 커밋 `66697990`이 팔레트에
      클릭 배치(+)를 먼저 넣었고, 2026-08-10 덱 편성 조작 9건(위)이 좌석 집기·
      이동·교환·팔레트 교체·제거·Esc 취소까지 전부 진짜 `<button>`의 `onClick`으로
      넓혀 편성 전체가 키보드로 된다. 라이브로 확인: 포커스한 팔레트 버튼에
      Enter를 누르면 배치되고, 포커스한 좌석 버튼에 Enter를 누르면 들리고,
      Escape를 누르면 취소된다 — 클릭 한 번 없이 키보드만으로.
- [x] **개인정보 처리방침 — 완료 (2026-08-06).** 화면 맨 아래에서 펼쳐 읽는다
      (`components/PrivacyNotice.tsx`, 문안은 `lib/helpText.ts`의 `HELP.privacy`).
      프로필이 없을 때도 나온다 — 계정을 맡길지 정하는 순간이 그때다. 바깥 링크가
      아니라 앱 안에서 펼치는 이유는 네이티브 창에 뒤로가기가 없고, 안내가
      오프라인에서도 읽혀야 하기 때문. 문안의 주장은 `backend/tests/
      test_privacy_claims.py`가 코드와 대조해 지킨다(배포 앱의 URL 분류 ·
      GitHub 업데이트 확인이 유일한 외부 요청 · 수집기 모듈 미도달).
      **법률 검토는 여전히 범위 밖** — 서버가 없어 개인정보처리자 지위가
      성립하지 않는다는 판단 위에 서 있고, 호스팅으로 가면 다시 봐야 한다.
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
- [x] **배포 인프라 — 완료.** 리모트는 `fienn-eda/RapiLab`(public), 태그를 밀면
      Actions(`release.yml`)가 Windows 빌드를 올린다. 배포 형태는 정적 호스팅이
      아니라 **설치형 데스크톱 앱**이 됐다 — 백엔드가 유저 PC에서 돌므로 서버가
      필요 없다. 자동 업데이트는 시작 시 GitHub 릴리스를 확인한다(`app/updater.py`).

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
    `bready`(Taste), `eve`(크리티컬-히트 카운터 —
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
- [x] **차지 창 계산기(`차지` 탭 · `POST /api/charge-window`) — 완료 (2026-07-29).**
      흑련·리버렐리오·네온의 FB 10초 창 안 타수와, 다음 타수를 사는 차지속도 임계값을
      확률 분포로 낸다 — FB 진입 위상이 플레이어의 선택이 아니므로 타수 하나가 아니라
      두 타수와 각 확률로 낸다. **알려진 한계**는 재장전 모델 수정 미착륙
      (`docs/engine-gaps.md` ★). 집계 규칙은 **2026-07-30에 굴림별 정수 %로 확정**돼
      계산기도 `aggregate_charge_speed`로 그 규칙을 쓴다 — 굴림 없는 export일 때만
      합계에서 추정하고 화면이 그 사실을 말한다. 상세는
      `docs/superpowers/specs/2026-07-29-charge-window-calculator-design.md`("알려진 한계") 참조.

### 정리/보강
- [x] **`supported_units()`가 `weapon_source`를 무시해 애장품 4인방의 `-signature`
      빌드가 추천기에서 안 보이던 문제 — 수정 완료 (2026-07-25).** 두 로더가 "이 매니페스트의
      무기 파일은 어디서 오는가"를 **각자** 판단하던 게 근본 원인이라, `weapon_source` 키가
      추가됐을 때 `load_nikke_spec`만 배웠다. 분기를 `skill_values.load_weapon_data` 하나로
      합쳐 드리프트 자체를 없앴다. `supported_units`는 그 파일을 여전히 **가드 없이 즉시**
      로드한다 — 무기 데이터가 없는 유닛은 로스터에 못 들어가므로, 목록에 넣으면 팔레트에는
      보이는데 `load_nikke_spec`이 거부하는 유닛이 생기기 때문이다. **89/93 → 93/93**,
      넷 다 실제 로스터 적재까지 확인. 회귀 테스트는 이제 슬러그를 나열하지 않고
      "모든 `ENCODED_SLUGS`가 추천기에 도달하는가"를 단언한다 — 이 함수가 조용히 4개씩
      떨어뜨린 게 두 번째라, 이름을 적는 테스트는 자기를 만든 사건만 잡는다.
- [ ] `docs/decisions.md`의 "180s", "tech stack" 항목에 `Consequences:` 필드 보강
      (docs-keeper 지적, 2026-07-25 확인 — 둘 다 여전히 누락)
- [x] ~~**swap 힐클라임이 정규 순서 하나로만 후보를 채점한다**~~ → **측정 후 기각(고치지 않음),
      2026-07-25 발견·같은 날 종결.** 메커니즘은 실재한다: `search_best_decks` 독스트링이
      그 방식을 실측 최대 78% 낮다고 명시하고, `_swap_pass`에 들어오는 덱은 이미 최적 순서라
      **교체 후보만 불리하게** 채점된다(오차가 상쇄되지 않음). 그런데 **결과 가치는 거의
      안 바뀐다.** 실제 로스터 77유닛에서 후보를 전 intra-tier 순서로 채점한 힐클라임과
      현행을 끝까지 비교(`scripts/audit_swap_ordering.py`): **Water/180s +0.02%,
      Fire/180s +0.47%, Electric/90s +0.14%** — 상한 0.5%를 위해 할당 전체가 3.3~5.4배
      느려진다(94→503s, 104→348s, 62→170s). 2단계 설계로 비용을 깎아도 얻을 천장이 0.5%다.
      **이유**: 목적함수가 최적 근처에서 평평하다 — Water 실행에서 두 방식의 덱 구성이
      **완전히 달랐는데** 총딜은 0.02% 차이였다. 순서 저평가는 판정을 뒤집지만, 뒤집힌 쪽도
      거의 같은 값의 다른 국소 최적이다. 재검토 조건: 셸 규모가 커지거나(덱당 순서 수 증가)
      시너지 구조가 순서에 훨씬 민감해지면 다시 재라.

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
- **미구현 메커니즘:** 무기 변형, 공격속도 변화.
  (노멀어택 횟수 트리거·최고ATK 타겟팅은 해소됐고, **위치 타겟팅도 2026-08-13 해소** —
  `SquadContext.neighbor_slugs` + `registry.SEATED_BUFF_SLUGS`.)
- **좌석 스코프 (2026-08-13, 착륙):** 루주와 `flora-signature` 둘 다 끝났다.
  플로라의 Peace of Mind 두 불릿(Max HP +15.01% · **ATK +45.12% of Flora's ATK**)은
  ATK 쪽이 천장·바닥 두 경로라 실제로는 Effect 셋을 옮겼다. 좌석형 유닛을 **둘 다
  든 덱**이 가능해지면서(루주 B1 · 플로라 B2) 보고 단계가 「각자 최적 쌍」이 아니라
  **5칸 배치 전수**로 바뀌었다 — 자리가 서로를 제약해서, 따로 고르면 어떤 편성으로도
  못 만드는 배치를 채점한다. 배치 수는 루주 덱 6 · 플로라 덱 10 · 둘 다 18.
- **좌석 화면 표시 (2026-08-14, 착륙):** `DeckCard`가 `hold_burst_slugs` 줄 옆에
  한 줄 더 그린다 — 「루주는 2·4번 자리 중 한 곳에 두고, 양 옆에 A, B를 앉혀주세요」.
  자리 조건까지 싣기 위해 API `seating`이 `{시전자: {allies, seats}}`가 됐다:
  **「양 옆에 둘」만으로는 부족하다**(3번 자리도 양 옆이 둘인데 앞열이라 루주의
  버프가 안 켜진다). `seats`는 1-indexed이고 덱 크기보다 짧을 때만 화면이 자리를
  말하므로 슬러그 하드코딩이 없다. 같이 고친 것: 덱 목록을 「자리 순서」라 부르던
  `seatOrder` 문구 → `burstOrder`(그 목록은 버스트 순서다).

---

## 이 문서 관리 방법

- 작업이 한 단계 끝나거나 To-Do가 소화되면 여기부터 갱신 (커밋에 포함).
- 큰 결정이 새로 내려지면 → `/document` (docs-keeper)로 `decisions.md`에 기록하고,
  로드맵 단계 상태도 여기서 갱신.
- 테스트 수/인코딩 수는 상단 요약 줄에서 최신값으로 유지.
