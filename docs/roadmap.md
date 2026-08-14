# NIKKE Deck Builder — 로드맵 & 진행 현황

우리가 뭘 만들고 있고, 어디까지 왔고, 다음에 뭘 할지 한눈에 보는 문서.
큰 그림은 **로드맵(단계)**, 작은 단위 작업은 **To-Do**에서 관리한다.
결정의 배경은 `docs/decisions.md`, 엔진 함정/패턴은 `docs/insights.md`,
인코딩된 니케 목록(Burst 단계별)은 `docs/encoded-nikkes.md`,
엔진 갭 인벤토리(확장 우선순위)는 `docs/engine-gaps.md`,
스킬 인코딩 방법은 `nikke-skill-encoding` 스킬 참고.

- 마지막 갱신: 2026-08-14
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
- **MG 예열의 감쇠와 램프 모양이 실측됐다 (2026-08-14, 코드 미반영).** 예열은 재장전
  진입 시 즉시 풀리지 않고 마지막 발사부터 **62~70프레임에 걸쳐 선형으로** 빠지고,
  램프 비용은 앞쪽에 몰려 있다 — 콜드 137프레임 중 **56프레임이 첫 2발**이다. 엔진의
  「일정한 낮은 연사」는 총합만 맞다. 재장전 속도를 쌓은 덱의 MG는 매 탄창 최대
  1.85초를 잘못 청구받는다. 배선하면 콜드 램프의 발사 분포까지 재배치되어 모든 MG의
  발수 트리거가 움직이므로 **자체 설계가 필요하다** — 다음 세션.
  `docs/measurements/mg-spinup.md`, `docs/engine-gaps.md`.
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
- 이전 갱신: 2026-08-06
- 브랜치: 없음 — `wip/transform-window-refresh`를 트렁크에 병합(로컬, `61ec16a2`).
  기준선 **백엔드 1944 passed / 3 skipped**, 캘리 **1.079x · 17/25 불변**.

  **합법적인 덱 하나가 시뮬레이터를 죽이고 있었다.** 무기변형 창이 아직 열려 있는데
  주인이 다시 버스트하면 `generate_segmented_shots`가 겹침을 거부한다. 사이클이
  최소 12.4초(FB 10 + 게이지 2.4)라 어떤 창보다도 길어서 그동안 우연히 안 겹쳤을
  뿐이고, 어제 착륙한 사이클별 FB 길이(이사벨 −5초)가 그 바닥을 없앴다. CDR이 붙은
  덱은 9.45초마다 버스트하므로 나유타의 10초 창이 0.55초 일찍 다시 열린다.
  프로덕션에서는 `/api/recommend-raid`의 500이다 — 대리모델 적합이 표본 200덱을
  시뮬레이션하므로 그중 하나가 이 조합이면 요청 전체가 죽는다. 걸리는 유닛은
  **나유타·타키나 이노우에**(둘 다 B2라 이사벨과 티어를 안 나눈다).
  판정은 「재시전은 새 발동 기준으로 갱신」(Fienn)이고, 그래서 이전 창을 끊는다 —
  합치는 방식은 타키나의 `until_shots` 형태에 안 통한다. 상세 `docs/decisions.md`,
  교훈 둘은 `docs/insights.md`(우연히 참인 불변식 · 매거진 베이스로도 경계를 잴 것).

- 이전 갱신: 2026-08-06
- 브랜치: `worktree-result-view-and-saved-runs` — 결과 화면 정리와 결과 보관.
  기준선 **프론트 573 passed**(524에서 +49). 백엔드와 캘리는 손대지 않았다.

  Fienn이 화면에 대해 다섯 가지를 요청했고 전부 착지했다.

  **① 솔로 보스 방어력 기본값 31784.** `makeDefaultBossProfileDraft()`가 두 탭
  공유라, 기본값을 인자로 받게 하고 솔로만 넘긴다 — 유니온 보스는 방어력이 다르므로
  공유 기본값을 바꾸면 유니온이 조용히 틀린 값으로 계산된다.

  **② 방어력·전투 시간을 "기타 설정"으로 접음.** 요약(`방어력 31,784 · 180초`)은
  접힌 채로도 보이고, 그 두 칸에 오류가 있으면 스스로 펼친다.

  **③ 결과 덱 카드가 다열 그리드.** `.deck-results`를 flex column →
  `repeat(auto-fill, minmax(340px, 1fr))`로. 한 줄 고쳐 네 결과 화면이 같이 바뀐다.
  1600px 창에서 3열, 700px에서 1열로 되돌아간다(육안 확인).

  **④ 결과에 보스 설정 표시.** 새 `BossSummary` — 켜진 기믹만, 약점 속성으로,
  방어력·전투 시간을 함께. 폼이 그 둘을 접었으므로 여기가 그 값이 남는 유일한
  자리다. 솔로는 결과 위 한 줄, 유니온은 전투마다 보스가 달라 카드 안에.

  **⑤ 결과를 이름 붙여 보관.** `Profile.savedRuns`에 `tab: 'solo' | 'union'`으로
  담긴다 — 두 탭이 섞이지 않는 것은 그 필드 하나다. 여는 것은 읽기 모드이고, 폼은
  "이 설정으로 폼 채우기"를 눌러야 바뀐다. 결과 캐시(`results`)와 달리 **로스터
  재동기화에도 지워지지 않는다**: 유저가 이름 붙여 남긴 것을 말없이 버리면 안 된다.
  상한 50개를 넘으면 오래된 것을 밀어내지 않고 저장을 거절한다.

  육안 확인에서 결함 둘을 잡았다. **CSS는 앱을 띄워야 보인다**는 것이 두 번
  확인된 셈이다(Vitest는 `css: false`).

  **㉮ 보관 목록 상자가 좁았다.** `align-items: flex-start` 때문에 내용 크기
  (428px)로 줄어, 펼친 보관물 안의 덱 그리드가 한 열에 갇혔다.
  `.saved-runs-group { width: 100% }`로 고쳐 1336px·3열이 됐다.

  **㉯ 필터의 아이콘 칩 폭이 제각각이었다** (Fienn 지적). 버스트 칩이
  `22×37 · 32×37 · 38×37`로 잡혔는데, 아이콘 원본의 가로 비율이 패밀리 안에서도
  달라(B1은 좁고 B3은 넓다) `width: auto`가 그대로 칩 폭이 됐기 때문이다.
  `--filter-chip-box` 정사각형으로 고정해 여덟 칩 전부 `37×37`이 됐다.
  속성 아이콘의 1.2배 시각 보정은 그대로 둔다 — 그것은 아이콘 크기 얘기지
  상자 얘기가 아니었다. 팔레트 칩에서 한 번 고쳤던 것과 같은 종류의 결함이
  필터 툴바에 남아 있었다(`71668f9c`).

- 브랜치: 없음 — `wip/soda-full-burst-extension`을 트렁크에 병합(로컬).
  소다: 트윙클링 바니의 FB 확장 + 그 상태에 게이팅된 넉. 병합 후 기준선
  **백엔드 1936 passed, 3 skipped** · 실기록 캘리 **1.079x · 17/25**.

  캘리는 이 작업 전후로 한 자리도 안 움직인다 — 병합 전 트렁크 `19afe0ac`에서
  재봐도 1.079x다. 이 문서와 `docs/engine-gaps.md`에 오래 적혀 있던 **1.078x는
  낡은 값**이었고, 2026-08-06 재측정으로 정정한다.

- 이전 갱신: 2026-08-05
- 브랜치: 없음 — 트렁크 `wip/scaffolding`에 전부 병합(로컬). 기준선
  **백엔드 1911 passed, 3 skipped · 프론트 523 passed** · 실기록 캘리
  **1.078x · 17/25**.

  두 건이 착지했다.

  **① 게이지 충전 상수를 실측에서 역산 — 2.0 → 2.4초.** 「아르카나가 과대평가된
  것 같다」는 제보에서 시작했는데 **인코딩은 무죄**였다(원문 6불릿의 스코프·수치·
  조건 전부 일치, 자기 딜은 5.1%). 과대는 `gauge_charge_time`에 있었다. Fienn 지적:
  아르카나의 「버스트 쿨다운 -6초」는 인게임에서 이득이 없다 — 사이클이 이미
  풀버스트 10초 + 게이지를 치르고 그 바닥은 쿨다운으로 못 내린다. 실제로 그 불릿만
  0으로 만들면 총딜이 **자릿수까지 동일**하고, 게이지 2.0에서만 +13.6%를 벌었다.
  값은 실측 하나가 정한다(CDR 7.48초 덱을 최대한 빠르게 굴리면 15번째 풀버스트가
  t≈179 → `143.0 + 15g = 179` → **2.4**). 핵심은 **게이지가 덱의 CDR이 클수록 더
  병목이 된다**는 것 — 그래서 낮은 값은 CDR 쌓은 덱만 부풀리고 탐색이 그것을 1순위로
  올린다. 캘리 **1.082x → 1.078x**, ±15% **16/25 → 17/25**.
  결정과 기각한 대안은 `docs/decisions.md`.

  **② 낡은 캐시 결과가 앱을 통째로 검은 화면으로 만들던 버그.** `restoreResult`가
  저장 당시의 `lastResultHash`로 결과를 곧장 꺼내 `inputHash`의 엔진 버전 무효화를
  우회했다. `hold_burst_slugs`가 추가되자 옛 결과에 그 필드가 없어 `DeckCard`가
  터졌고, 에러 바운더리가 없어 트리 전체가 언마운트됐다(배경 `#0e0d13` = 검은 화면).
  복원도 캐시 조회와 같은 규칙을 쓰게 고쳤다(`lib/restorableResult.ts`).

- 이전 갱신: 2026-08-03
- 브랜치: 없음 — 트렁크 `wip/scaffolding`에 전부 병합되고 origin `f8ccf40`까지
  푸시됐다(태그는 아직 v0.1.1). 기준선 **백엔드 1810 passed, 3 skipped ·
  프론트 467 passed** · 실기록 캘리 **1.082x · 16/25**.

  이 날은 **실측 세션**이었다. Fienn이 「스킬 설명에 적혀 있는 효과가 반영되지
  않는다는 게 믿기 어렵다」고 짚은 한 줄에서 시작해 판정 여섯 개가 나왔고, 셋은
  엔진/기록이 틀렸고 셋은 맞았다. 맞았던 셋도 이제 가정이 아니라 실측 위에 있다.
  판독 원본은 전부 `docs/measurements/`에 있다(4건 → **8건**).

  | 판정 | 잔차 | 결과 |
  |---|---|---|
  | 청춘의 기록은 작동한다 — 그녀의 SG 소장품이 같은 「일반공격 배율」 버킷에 9.46%를 이미 채우고 있어 한계효과가 `0.1/1.0946`으로 작아 보였을 뿐 | 3e-07 | 엔진 수정 |
  | 소장품은 무기변형 중에도 붙는다 (`damage-formula-reference.md:77`의 커뮤니티 주장 반증) | 4.9e-08 | 기록 정정 |
  | 무기변형 세그먼트가 차지댐 소장품 배율을 잃고 있었다 | 4.9e-05 | 엔진 수정 |
  | 펠릿 +1은 데미지 버프가 아니다 — 같은 샷 총합이 더 많은 펠릿에 나뉜다 | 3e-07 | 기존 모델 확인 |
  | 소장품 배율은 차지댐 **버프**에는 안 붙는다 (레퍼런스 괄호절 확인) | 3.6e-05 | 기존 모델 확인 |
  | 무기변형 중에도 **기본 무기**의 유효사거리 밴드를 유지한다 | 5.8e-08 | 기존 모델 확인 |

  엔진 쪽 실물 변경은 셋이다: SG·SMG 소장품을 무기 스탯에서
  `normal_attack_damage_multiplier` **가산 버킷**으로 이동(같은 스탯 이름은 같은
  버킷), 청춘의 기록을 데이터 슬롯에서 복구하고 피팅 상수 `0.091354` 삭제(그것은
  상수가 아니라 `0.1/1.0946`, 즉 소장품 15단계를 박아넣은 값이었다), 그리고
  `caster_charge_damage_multiplier`를 값 딕셔너리로 실어 보내 maxwell·red-hood의
  변형 프로파일이 소비하게 한 것. 캘리는 1.077x → **1.082x**로 움직였는데 전부
  나유타 한 명이다 — 그녀의 변형 창이 소장품을 잃고 있던 잠재 버그가 같이 고쳐졌다.

  부수로 확정된 것: 엔진 갭 하나를 **8유닛 → 2유닛**으로 정정(변형 빌더가 값을
  `weapon_stats`에서 읽는지 스킬 슬롯에서 읽는지를 안 봤던 오집계), major 버킷의
  사거리 항 **+0.3**·풀버스트 항 **+0.5**를 SMG로 재확인, 나유타 Hypocrisy의 코어
  버프가 스택 무관 **고정 25.15%**. 목록 없이 도는 방어 테스트
  (`test_weapon_mode_collectible.py`)도 함께 들어갔다.

- 이전 갱신: 2026-08-02 — 이 날 착지한 것:
  배분 탐색 6건(교차-티어 스왑 +6.93% 외, 아래 "배분 탐색 품질" To-Do),
  **PR #1**(WebView2 크래시 복구 · UI 다듬기 · 동기화 탭), 그리고 **플랫 발수 장탄
  버프**(`max_ammo_rounds` — 토브·그레이브·느와르의 "최대 장탄 수 ▲ N발"이 퍼센트로는
  근사조차 안 돼 defer 중이던 것. 고정 덱 +2.59%, 캘리 불변), 그리고 **힐·쉴드·Max HP
  분류 정정**(지침이 "생존기라 스킵"이라 적고 있어 여섯 유닛이 비어 있었다 — 힐 제공자
  목록 드리프트 6슬러그 + Max HP 5유닛 + 쉴드 제공자 목록 신설. 캘리 불변), 그리고
  **유동폭 레이아웃**(셸은 창을 채우고 본문은 가독폭을 지킨다 · 모드 열은 내용에
  맞춰 좁아지고 · 결과가 설정 행 아래·팔레트 위로 · 유니온 결과가 로스터 위로).
- 이전 브랜치: `worktree-identity-vs-fanout` 워크트리(`.claude/worktrees/identity-vs-fanout`,
  `wip/scaffolding` `8a1ed2c` 기준에서 분기 — 백엔드 1519 passed, 3 skipped, 이 항목
  시점에 트렁크 미병합). 이전: `worktree-fixed-deck-evaluation` 워크트리
  (`wip/scaffolding` `3a3731c` 기준에서 분기 — 백엔드 1487 passed, 3 skipped · 프론트 350)
- 프론트: **464 passed** (2026-08-01, **UI 다듬기 + 동기화 탭 분리** — Fienn이 설치된
  앱을 켜고 짚은 6건. 그중 가장 무거운 것은 버그였다: 인박스 폴링 게이트가
  `status !== 'idle'`이라 **동기화가 한 번 끝나면 폴링이 영구 정지**하고, 그 뒤 누른
  북마크릿은 인박스에 놓인 채 앱에 닿지 못한다(브라우저는 200을 받으므로 "보냈어요"까지
  띄운다 — 부계정이 안 들어온 경로다). 첫 동기화가 멀쩡했던 건 계정이 처음 생길 때
  `App.tsx`가 패널을 통째로 갈아끼워 상태가 리셋되기 때문. 게이트를 `choosing`/
  `importing`으로 좁혔다. 동기화는 자기 탭(맨 뒤)으로 옮기고, payload가 오면 그 탭을
  앞으로 가져온다 — 서버 선택 질문이 감춰진 패널에 뜨면 유저는 멈춘 것으로만 본다.
  보스 설정 설명 3개는 `HelpTip` 호버로 접었고(유니온 3열이 특히 짧아진다), 안내
  문구는 `lib/helpText.ts` 한 곳에 모았다(`**강조**`만 지원). 니케 풀 기본 정렬은
  우코 내림차순, 오버로드 옵션명은 본문색. 백엔드 무변경. was 452.)
- 이전(백엔드): **1529 passed, 3 skipped** (2026-07-28, **정체성/팬아웃 분리 착지** —
  `MODE_VARIANTS` 하나가 (a) 누가 같은 캐릭터인가 (b) 엔진이 무엇을 고를 수 있는가를
  겸하는 바람에 애장품 `-signature` 13쌍이 두 캐릭터로 보이던 빈틈을 닫았다. 정체성은
  신설 `registry.character_map()`이 **매니페스트 `data_slug`에서 파생**해 답하고
  (17그룹 정확히, 오탐 0 — 손으로 유지할 표 없음), `MODE_VARIANTS`는 팬아웃 전용으로
  남는다. **애장품 쌍은 (b)에 절대 넣지 않는다** — 넣으면 아이템이 없는 유저에게
  엔진이 `-signature`를 골라준다. 실제 로스터 4모드 전부 트렁크와 바이트 동일(순수
  확장), 라이브에서 같은 형태 (2,1,2) 기준 다른 두 캐릭터 200 / 한 캐릭터 두 빌드 422.
  프론트 무변경. 상세는 아래 To-Do 항목. was 1519/3.)
- 이전(백엔드/프론트): **1513 passed, 3 skipped** · 프론트: **380 passed** (2026-07-28,
  **고정 편성 평가(evaluate-decks) 착지** — 기존 추천 탭의 세 모드(단일 덱·레이드
  배분·초안 기반)는 전부 엔진이 덱을 **만드는** 방향이었는데, 이번 작업은 그
  반대로 플레이어가 5자리를 전부 채운 편성을 엔진이 **채점만** 하게 한다.
  `backend/app/deck_evaluation.py`의 `evaluate_decks(decks, bosses,
  alternatives=None)`가 덱마다 자기 보스를 상대로 `best_ordering_summary`
  (Task 3에서 비공개명에서 승격)에 위임해 채점 후 합산 — 별도 데미지 계산
  경로를 새로 만들지 않았다. `deck_search.deck_is_valid(units)`(허용 형태
  (1,1,3)/(1,2,2)/(2,1,2) + 변형 충돌 + 티어1 좌석 + 버퍼석 규칙)를 신설해
  "필드 가능한 5인 덱"의 정의 하나를 탐색·평가가 공유. `POST /api/evaluate-decks`
  (요청 `{roster, decks: [{units, boss}]}` — 덱마다 보스가 하나인 이유는
  유니온 레이드가 전투마다 다른 보스를 상대하기 때문; 응답 `{decks,
  combined_total_damage, excluded_slugs, engine_version}`, `deck` 배열은
  제출 순서가 아니라 **엔진이 고른 좌석 순서**; 422 다섯 가지 — 빈 덱
  목록·5인이 아닌 덱·덱 간 슬러그 중복·평가 불가 슬러그·형태/좌석이 필드
  불가한 덱)로 노출. `backend/app/engine_version.py`의 `engine_version()`
  (`backend/app/` 전체 `.py`에 대한 12자리 sha256, `lru_cache`)과
  `GET /api/engine-version`을 신설(프론트가 요청을 보내기 전에 캐시부터
  확인하므로 응답에 얹는 것만으로는 부족), 프론트 결과 캐시 키
  (`lib/inputHash.ts`)의 필수 인자로 섞어 엔진이 바뀌면 같은 입력이라도
  캐시가 조용히 낡는 문제를 막는다. 프론트: 추천 탭 4번째 모드 "평가"
  (1–5덱, 보스 1개), 신규 3번째 탭 "유니온 레이드"(1–3전투, 기본 3, 전투마다
  자기 보스 프로필 + 180초 기본값), 두 화면이 `EvaluationResults.tsx` 하나를
  공유하고 각 덱에 자기 보스 원소를 라벨링. `DraftEditor`에 `showLocks?:
  boolean`(기본 true) 신설 — 두 화면 다 잠금 토글이 의미 없어 숨긴다. 평가
  결과는 **캐시하지 않음**(초 단위 응답이라 재실행이 저렴하고, 캐싱하려면
  배분 결과용으로 짜인 저장 스키마를 넓혀야 함). **실측(TestClient, 실
  로스터):** 3덱×서로 다른 보스 3개 = 3.43초, 5덱×보스 1개 = 4.40초(대체
  대상인 초안 모드의 797초 대비 압도적으로 빠름) — SimPool 없이 순차 실행이
  정답으로 확인됨(SimPool은 워커 초기화 시 보스를 고정해 덱별-보스 배치를
  못 건넘). 덱별 보스가 실제로 수치를 바꾸는 것도 확인(동일 덱 기준 철갑
  1.5715e9 vs 무속성 1.4282e9). 브라우저 실측: 편성 제출 시 "1번 덱 · 철갑 /
  892,714,648 총딜"과 함께 엔진이 배치를 재정렬했고, 결과 제출 후 보스
  셀렉트를 바꿔도 결과 카드의 라벨은 제출 시점 보스로 고정됨을 확인. 스펙:
  `docs/superpowers/specs/2026-07-28-fixed-deck-evaluation-design.md`, 플랜:
  `docs/superpowers/plans/2026-07-28-fixed-deck-evaluation.md`(13개 작업,
  서브에이전트 기반 개발로 각 작업 개별 리뷰). **범위 밖:** 유니온 레이드
  *추천*(엔진이 3덱을 직접 구성 — 배분 알고리즘의 덱별-보스 인지 확장과
  스왑 언덕오르기 재검토 필요) · 5속성 보스 프리셋(보스별 부위파괴/코어피격
  특성 데이터 미확보) · 평가 결과 화면에 "이 편성 최적화?" CTA 없음(초안
  모드가 이미 그 역할). was 1487/3 · 350(이 브랜치 분기 시점).)
- 이전(프론트): **294 passed** (2026-07-26, **UI 크롬 한글화 완료** — 2026-07-25 "유닛 표시
  이름 한글화" 스펙(`docs/superpowers/specs/2026-07-25-korean-display-names-design.md`,
  유닛 이름·애장품 하트 담당)이 별도 작업으로 미뤄뒀던 "UI 크롬 한글화(Boss profile,
  Recommend decks 등)"를 마무리. 헤딩·라벨·버튼·힌트·빈 상태 메시지·aria-label·title·
  폴백 에러/검증 메시지까지 `frontend/src/` 전역의 하드코딩 영문 UI 문자열을 한글로
  교체(i18n 라이브러리 없이 직접 치환 — 한국 서비스 전용이라 그걸로 충분, Fienn 판단).
  스펙: `docs/superpowers/specs/2026-07-26-ui-chrome-korean-localization-design.md`,
  계획: `docs/superpowers/plans/2026-07-26-ui-chrome-korean-localization.md`(15개
  계획 작업 + 실행 중 발견한 갭픽스 3건, 서브에이전트 기반 개발로 각 작업 개별 리뷰).
  범위: 컴포넌트 ~15개(App.tsx·BossProfileField·RecommendPanel·SyncRosterPanel·
  ProfileSwitcher·DraftEditor·DraftResults·RaidResults·DeckCard·DeckResults·
  RosterGrid·ExcludedSlugsNote·InvestmentBadge·InvestmentSummary·NikkeCard·
  UnitPalette) + 훅/API 5개(useAsyncRequestStatus·useRecommendRaid·useSupportedUnits·
  recommendApiError·assembleRosterApiError) + `lib/rosterImport.ts`·`lib/shareUrl.ts`·
  `types/bossProfileDraft.ts`·`types/nikkeDraft.ts`(죽은 코드지만 일관성 위해 함께
  번역). 신규 공용 모듈 `frontend/src/lib/elementName.ts`(`elementLabel()` — Fire=작열/
  Water=수냉/Wind=풍압/Iron=철갑/Electric=전격, Fienn 확정 표기). **범위 제외**(스펙에
  명시): 백엔드 FastAPI/Pydantic 검증 메시지 원문 그대로 통과되는 것·이미 한글인
  `lib/bookmarklet.ts`·게임 표준 코드(S1/S2/B, B1/B2/B3)·SyncRosterPanel의 예시
  URL 플레이스홀더. 기준선 289 passed → **294 passed, 0 failed**(+5는 신규
  `elementName.test.ts`로 인한 정상 증가, 회귀 아님). `tsc -b --noEmit`·`npm run build`
  클린. 과정 통찰 2건은 `docs/insights.md`(Frontend 섹션 CJK 줄바꿈 항목) 및 아래
  참고: (1) 계획이 작성한 한글 문장 3곳(BossProfileField·DraftResults·RecommendPanel)이
  프로젝트의 확립된 캐주얼-정중체(~해요/~돼요, `lib/bookmarklet.ts` 기준) 대신
  격식체(~됨/~습니다/~ㅂ니다)로 새 나온 걸 세 차례 독립 리뷰가 각각 잡아냄 — 같은
  결함 종류가 반복 발견됐다는 것 자체가 "전체 문장형 문자열은 톤을 따로 검사해야
  한다"는 신호. (2) 계획 순서 버그 1건: `SyncRosterPanel.test.tsx`의 단언이
  `lib/rosterImport.ts` 경고 문구가 이미 한글이라고 가정했는데, 그 파일의 번역은
  계획상 **더 나중** 작업으로 배치돼 있었음 — 나중 작업의 확정 문구를 앞당겨
  해결하고, 그 작업이 이미 바뀐 텍스트를 다시 diff하지 않도록 주의. 커밋 범위
  `b21cfff..b3bd244`(작업 9~14, 9개 커밋), 브랜치 전체는 `wip/scaffolding` 대비 25
  커밋(설계/계획 문서 2건 + 작업 1~14 포함).)
- 이전(백엔드 테스트, 이 워크트리 분기 시점 상태): **1413 passed, 3 skipped** (2026-07-19,
  **무기변형 계획 2 착지** — v1이 백로그로 남겨둔
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
- [x] **MG 예열 착륙 (2026-08-07, Fienn 프레임 판독).** 최대 연사 60발/초는 맞았고
      엔진이 그걸 **첫 발부터** 주고 있었다 — 예열은 48구간/137프레임, 탄창당 1.4833초
      손실. 합계 1.076x → **1.047x**, ±15% 이내 17/25 → **19/25**, MG 평균 1.193x →
      **1.051x**(RL 1.035 바로 옆, 1.0 아래로 안 내려감). 아스카 +0.449B → **+0.069B**.
      원본 `docs/measurements/mg-spinup.md`.
- [x] **SMG에는 예열이 없다 — 가설 기각 (2026-08-08, Fienn 인게임 확인).** 「heating」은
      게임이 MG에만 쓰는 어휘다 — 수집 데이터에서 이 문구를 쓰는 건 아스카·레이 둘뿐이고
      둘 다 같은 용어 ID(`word_group=10073`)이며, 레이 원문은 대상을 아예 `allies with a
      Machine Gun`으로 못박는다. MG 착륙이 근거도 하나 걷어갔다 — **「잔차가 연사 속도 순」이
      더는 성립하지 않는다**(MG 60발/초 1.066x가 SMG 20발/초 1.148x **아래**). SMG는 공칭
      연사 그대로 두고 `spinup_for_weapon`은 MG만 안다. `docs/measurements/smg-no-spinup.md`.
- [ ] **SMG 1.148x의 원인은 예열이 아니라 따로 있다 — 지금 최대 무기군 항.** 2026-08-08
      재측정: SMG 1.148 · SR 1.115 · AR 1.114 · MG 1.066 · RL 1.035(합계 1.055x·19/25).
      셋 중 **나유타 +0.352B는 실기록 25유닛 전체에서 절대오차 1위**이고, 볼륨 1.224x는
      이미 「차지 설명 밖의 별개 원인」으로 표시돼 있다(`docs/insights.md`). 후보는 이미
      엔진에 있다 — 탄착군에서 SMG는 SG 다음으로 넓고(110px), 실기록 보스에 코어 50px를
      켜면 SMG가 **0.69x로 뒤집힌다**. 방향은 맞고 크기를 모른다. **필요한 건 SMG 측정이
      아니라 실기록 보스의 코어 지름**이다.
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
- [ ] **그 15유닛은 여전히 실측이 필요하다** (`scripts/audit_charge_motion_delay.py`가
      `assumed`도 계속 질문하고 exit 1). 실측값은 0.34~0.43으로 흩어져 있고 **네 유닛은
      아예 멈춤이 없으므로**, stand-in은 그 중 누군가에게 반드시 틀리다. 대상:
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

- [ ] **mihara-bonding-chain 0.910x — 지속딜이 캡에 포화된 채 17% 부족.** 그녀 딜은
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

- [x] **레이드 할당이 한 캐릭터를 두 덱에 세우던 버그 — 완료 (2026-07-25).** 배타 단위를
      슬러그에서 소유 캐릭터(`deck_search.variant_base`)로 변경. peel·벤치·힐클라임 전부
      이 키로 판단하고, 드래프트가 한 캐릭터를 두 덱에 넣으면 422로 거절. 백엔드
      1358 → **1361 passed / 3 skipped**. 실측: 풀 77유닛 = 소유 캐릭터 73명, 두 번 앉은
      캐릭터 없음. `decisions.md`("레이드 할당의 배타 단위를...") 참고.
- [x] **프론트/백엔드가 base 슬러그를 두고 어긋나던 문제 — 완료 (2026-07-25).**
      `/api/supported-units`가 소유 슬러그 엔트리를 추가로 반환하도록(93 → 96,
      `candidates` 필드) 하고 초상화 매니페스트도 두 어휘로 키를 갖게 했다. 라이브 확인:
      팔레트 **`73/73 (86 owned but not yet supported)`**, Roster 타일 70 → 73, 접힌 목록
      89 → 86(백엔드 `excluded_slugs`와 일치). 백엔드 1361 → **1365 passed**, 프론트
      264 → **268 passed**. `decisions.md`("`supported-units`가 두 어휘를...") 참고.
- [x] **드래프트에서도 이 3명을 앉힐 수 있게 — 완료 (2026-07-25).** 위 수정 직후
      드래프트 팔레트에서만 걸러냈던 것을 되돌렸다(드래프트 모드는 풀 팔레트를 렌더하지
      않아 보기·제외까지 막혀 있었음). 드래프트가 소유 슬러그를 그대로 보내고,
      `allocate_decks`의 seed 루프가 후보별로 `best_completions`를 돌려 모드를 고른다
      (`_seed_choices`). 잠금·pinned·결과 diff·덱 매칭을 모두 소유 캐릭터 키로 옮겼다.
      백엔드 1365 → **1367 passed**, 프론트 268 → **270 passed**, 드래프트 팔레트
      70 → **73칩**. `decisions.md`("드래프트도 소유 슬러그로 받는다...") 참고.
- [x] **Account 드롭다운이 닉네임 대신 uid로 되돌아가던 원인 — 완료 (2026-07-25).**
      코드 회귀가 아니었다(`ProfileSwitcher`의 `nickname || openId`는 멀쩡). `upsertProfile`이
      재싱크 닉네임을 무조건 덮어써서, 닉네임을 못 읽은 싱크 한 번이 저장된 값을 지웠다.
      이제 빈 닉네임은 저장된 값을 유지한다(`nickname: existing.nickname || args.nickname`).
      **이미 비어버린 프로필은 앱에서 북마클릿을 새로 받아 한 번 싱크해야 복구된다** —
      북마크바에 저장된 복사본은 `50176df`(닉네임을 `basic_info`에서 읽기) 이전 버전일 수 있다.
- [x] **부계정 싱크가 500으로 죽던 원인 — 완료 (2026-07-25).** 코어를 올린 PILGRIM
      Supporter의 코어당 플랫이 측정된 적이 없어 `core_flat_atk`가 (의도적으로) 예외를
      던지고, 그게 엔드포인트까지 올라가 **유닛 1기의 공백이 계정 전체를 못 쓰게** 했다.
      전용 예외 `UnmeasuredStat`를 두고 `assemble_roster`가 그 유닛만 빼고
      `unmeasured: [{name_en, reason}]`로 보고한다(프론트는 경고 줄로 표시).
      백엔드 1367 → **1369 passed**, 프론트 272 → **274 passed**.
- [x] **PILGRIM Supporter 코어당 플랫 + 스탯 모델 수정 — 완료 (2026-07-25).**
      측정하러 들어갔다가 **모델 버그를 찾았다**: 호감도 기여가 `(1 + 0.02×코어)`로
      스케일되는데 배수 밖에 더해지고 있었다. 그 효과가 적합값에 흡수돼 있었던 이유는
      코어 있는 유닛이 적합 그룹마다 호감도가 단일했기 때문(class 30, PILGRIM/OVERSPEC 40).
      **부수 효과가 순수한 단순화다** — 삭제: `CORE_FLAT_*_BY_RESOURCE_ID`(유닛별 예외
      3기, "설명 안 됨"이라 적혀 있던 Vesti·Rosanna·Nero가 호감도 10 유닛이었다),
      `CORE_FLAT_ATK_OVERSPEC`, `CORE_FLAT_HP_OVERSPEC`(**OVERSPEC 계층은 존재하지
      않았다**), `core_flat_*`의 `resource_id`·`corporation_sub_type` 인자.
      HP는 클래스만으로 159/159(최대 0.87), ATK는 PILGRIM 행 하나만 남아 159/159(최대 0.90).
      **PILGRIM은 Supporter에게 아무것도 주지 않는다**(같은 방식으로 읽은 Supporter 4기가
      0.67 폭에 모임, Attacker는 +9.95). 백엔드 **1371 passed / 3 skipped**, 코어 3
      PILGRIM Supporter 6기 전원 조립. `decisions.md`("호감도는 코어 단계 안에 있다...") 참고.
      계측 도구: `scripts/solve_core_flat.py`.
- [ ] **what-if 판독이 실측 적합보다 코어당 3.241 ATK 낮다 (원인 미상).** ShiftyPad에서
      코어만 바꿔 읽은 값이, 같은 유닛(Naga — 159기 기준값에 코어 7로 존재)의 기준값
      유도치보다 일정하게 낮다. 오프셋의 HP:ATK 비가 125로 base(30)도 core_flat(55)도 아니다.
      표 값은 159기 실측 적합에서 오므로 **현재 영향 없음**. 앞으로 what-if 판독으로
      절대값을 정하려 할 때만 문제가 된다 — 그때는 이 오프셋을 먼저 규명할 것.
- [x] **닉네임을 못 읽은 싱크가 조용히 성공한다 — 완료 (2026-08-09).** 근본 원인은
      호출 수·간격·순서가 아니라 ShiftyPad 화면 자신이 뜨며 같은 이름 조회를 이미
      하고 있는 것이었다(경쟁 몇 초 안에 최초 동기화가 걸린다). 계정 이름을
      **유저가 소유하는 라벨**로 바꿔 동기화는 비어 있을 때만 씨앗을 심고, 유저는
      계정 드롭다운 옆에서 직접 바꾼다. 이름 조회는 재시도 없는 최선 노력 1회로
      낮췄고, 화면은 `SyncRosterPanel`에서 "계정 이름을 읽지 못했어요, 직접
      붙여주세요"를 안내한다. `docs/decisions.md`("계정 이름은 유저가 소유하는
      라벨이다")·`docs/insights.md`("blablalink 1300015…") 참고.
- [x] **드래프트 좌석이 적으면 사실상 응답이 안 온다 — 완료 (2026-07-25).**
      `best_completions`가 `SEARCH_SIM_BUDGET`(1200)을 받고, 초과하면 `search_best_decks`와
      **같은 2단 축소**(캐스케이드 shortlist → 실패 시 `prune_candidate_pool`)를 탄다.
      실측(실제 77유닛 로스터, `scripts/measure_thin_draft.py`): 좌석 1개 완성이
      **1,830,670 순서(8워커 ~6.5시간, 사실상 무응답) → 86.2초**. 좌석 2개 126,513 → 69.6초,
      좌석 3개 10,835 → 70.0초. **캐스케이드가 필수였다** — prune만 붙인 1차 구현은
      좌석 1개에서 총딜 36.73B로, **제약이 더 많은** 좌석 2개(42.99B)보다 14.6% 낮았다
      (좌석이 적을수록 완성 유닛 4/5를 축소 풀에서 뽑으므로 recall 오차 노출이 커진다).
      캐스케이드 적용 후 **43.06B**로 단조성 회복(zero-base 43.51B ≥ 좌석1 43.06B ≥ 좌석2 42.99B).
      surrogate 적합은 예산을 실제로 초과한 seed가 있을 때만 지불하며 seed·peel이 1회를
      공유한다. 백엔드 **1371 → 1382 passed / 3 skipped**. `decisions.md`·`insights.md` 참고.
- [x] **표시 이름 한글화 — 완료 (2026-07-26).** `backend/app/display_names.py`의
      **96개 전부 Fienn이 작성**(빈칸 0). 겹치는 이름은 17건 → 13건이 됐고, 남은 13건은
      전부 의도한 `-signature` 쌍이다. 벤치의 "Bready, Bready"는 사라졌다.
      **이름 규칙: 한국 서버 공식 표기이며 음차가 아니다** — `moran`은 "모란"이 아니라
      "목단"이다. 영문명으로는 유추할 수 없으니 후속 작업에서도 공식 표기를 확인할 것.
      **빈 줄은 영문으로 떨어진다**(회귀 없음). 모드 변형은 접미사 파생 없이
      표에 통째로 다르게 쓴다(예: "브레디 (잔류)"/"브레디 (권장)"). **애장품은 base와
      같은 이름으로 쓴다** — 로스터가 둘 중 하나로만 해석해 함께 뜨지 않으므로
      `helm`·`helm-signature` 둘 다 "헬름"이 맞고, 빌드 구분은 하트가 한다. 유일성은
      캐릭터 단위로만 요구된다(`test_display_names.py`).
      조사에서 드러난 것: 겹치는 이름은 **17건**이고 원래 To-Do가 제안한 `candidates`
      해법으로는 3건밖에 못 고친다(`rapi-red-hood-b1`은 base가 곧 후보라 `candidates`가
      없고, `-signature` 13쌍은 MODE_VARIANTS가 아니다). 이때는 blablalink에 한글 이름이
      없다고 봤다 — 디렉토리·캐릭터 데이터가 전부 영문이고 Accept-Language·쿠키·`/ko/`
      경로 모두 196행 영문이었다. **그 판독은 2026-08-08에 뒤집혔다**: 목록 자체가
      로케일별 파일이라 한국어판은 다른 경로(`/character/ko/nikke_list_v2.json`)에 있다.
      지금은 그쪽에서 받아 오고(위 「한글 표시 이름은 이제 받아 온다」), 표를 손으로
      쓰는 이유는 아래 두 규칙(모드 변형·애장품)만 남았다.
      애장품은 이름이 아니라 **주황 하트**로 표시(초상화 뱃지 + 텍스트 목록엔 이름 뒤
      하트). 대상은 `-signature` 13기가 아니라 **실제로 장착한 유닛**이라 `favorite_item`
      플래그를 `NikkeDraft`까지 보존했다(`grade`/`core`와 같은 패턴, 와이어 타입은 불변).
      백엔드 **1387 passed / 3 skipped**, 프론트 **282 passed**. 라이브 확인 완료.
      스펙: `docs/superpowers/specs/2026-07-25-korean-display-names-design.md`.
- [x] **정체성 그룹과 후보 팬아웃을 분리 — 완료 (2026-07-28).** 정체성은 이제
      `registry.character_map()`이 답하고, `MODE_VARIANTS`는 팬아웃 전용으로 남았다.
      **정체성의 출처는 매니페스트의 `data_slug`다** — 인코딩 93슬러그를 그걸로 묶으면
      MODE_VARIANTS 4그룹 + `-signature` 13쌍 = **17그룹이 정확히, 오탐 0으로** 나온다.
      손으로 유지할 표가 없고 앞으로 인코딩될 애장품 빌드가 자동으로 덮인다. 대신
      "데이터 출처" 필드에 정체성을 얹는 결합이 생기므로 `test_character_map.py`가
      17그룹을 통째로 고정해 드리프트를 막는다. 표는 **빌드가 2개 이상인 캐릭터의
      슬러그만** 담는다(솔로는 `.get(slug, slug)`로 자기 자신이라 넣을 필요가 없고,
      덱 탐색 최내곽 루프의 비용이 그대로 유지된다).
      이름도 따라갔다: `_VARIANT_GROUP`·`variant_base`·`_no_variant_clash`·
      `_variant_safe_top` → `_CHARACTER_OF`·`character_of`·`_no_character_clash`·
      `_character_safe_top`. `VARIANT_BURST_TIERS`와 `SOLE_TIER1_SLUGS`는 진짜로 모드
      변형 개념이라 그대로 뒀고, 주석도 정체성 자리만 "sibling build"로 바꾸고
      팬아웃을 말하는 자리는 `MODE_VARIANTS`를 남겼다.
      **반대쪽이 안 넓어졌음을 세 각도로 못박았다**(이게 이 작업의 안전장치다):
      `load_roster`가 miranda 1기를 스펙 1개로만 내놓고 · `supported_units`의 miranda에
      `candidates`가 없고 · 드래프트 좌석이 `alternatives`를 안 달고 온다. 애장품이
      없는 유저에게 엔진이 `-signature`를 골라주는 일은 여전히 불가능하다.
      **회귀 실측**: 실제 로스터(77스펙) 4모드 전부 트렁크와 **바이트 단위 동일**
      (단일 12,962,894,676.151 · 분배 34,898,460,675.857 · 드래프트 35,767,895,536.505 ·
      고정평가 12,962,894,676.151) — 기존 정의역 위에선 순수 확장이기 때문이다.
      결함의 직접 증거: 옛 표로 되돌린 mutation 런에서 `miranda`가 1덱, `miranda-signature`가
      2덱에 동시에 앉는다. 라이브 확인도 결정적 — **같은 덱 형태 (2,1,2)에서 다른 두
      캐릭터는 200, 한 캐릭터의 두 빌드는 422**. 백엔드 **1519 → 1529 passed / 3 skipped**
      (신규 10). 프론트 무변경. 스펙·계획은
      `docs/superpowers/specs/2026-07-28-identity-vs-candidate-fanout-design.md`.
      (원래 항목 기록) `deck_search._VARIANT_GROUP`이
      `MODE_VARIANTS` 하나에서 파생되는데, 그 테이블이 성격이 다른 두 질문을 겸한다:
      (a) **누가 같은 캐릭터인가**(중복 편성 금지) (b) **엔진이 무엇을 고를 수 있는가**
      (`api.py`의 `alternatives` 팬아웃). `-signature` 13쌍은 (a)가 필요하지만 (b)는
      절대 아니다 — 애장품 보유 여부는 이미 정해진 사실이지 엔진이 고를 선택지가
      아니며, (b)에 들어가면 **애장품이 없는 유저에게 엔진이 `-signature` 인코딩을
      골라줄 수 있다**(없는 아이템의 효과를 얻는다). 그러므로 `MODE_VARIANTS`에
      추가하는 식의 처방은 틀렸고, 두 테이블을 나눠 애장품 쌍을 (a)에만 넣어야 한다.
      실측: `variant_base('miranda-signature')`가 `'miranda-signature'`를 돌려주고
      `_no_variant_clash([miranda, miranda-signature, …])`가 `True`다 — 엔진이 둘을
      다른 캐릭터로 본다. **지금은 실제 로스터로 닿지 않는다**: `rosterImport.ts`가
      `favorite_item` 플래그로 캐릭터당 슬러그를 하나만 만들기 때문(위 한글화 항목의
      "둘 중 하나로만 해석"과 같은 성질). 손으로 고친 roster.json·낡은 임포트·수집기
      변경으로 둘 다 들어오면 한 캐릭터가 두 덱에 앉아 유니온 "재사용 불가"와 솔로
      5덱 동시 편성 전제가 함께 깨진다. 기존 네 모드 전부가 지나는 경로라 회귀 확인
      필요. (이번 브랜치가 만든 결함이 아니라 원래 있던 빈틈이다.)
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
- [x] **추천 요청 취소 — 완료 (2026-07-26).** 실행 중에만 뜨는 Cancel 버튼이
      fetch를 abort하고, 백엔드가 그 끊김을 취소로 읽는다. **화면뿐 아니라 기계도 푼다.**
      계측: 수정 전에는 연결이 끊겨도 워커 8개가 계산 끝까지(최대 2분) 돌았고, 지금은
      **1.5초** 만에 접힌다. 지연의 병목은 폴링(0.5초)이 아니라 워커가 이미 시작한
      청크였다 — `chunksize`를 8로 상한 두니 7.8초 → 1.5초, 그리고 **처리량 대가는 없다**
      (실제 로스터 좌석3 드래프트 83.4/83.3초 vs 상한 없이 84.1/84.1초, 총딜 동일).
      취소는 두 경로로 닿는다: 탐색 루프는 반복 사이에 토큰을 확인하고, `executor.map`에
      막힌 워커는 풀을 밖에서 접어야 한다(`app/cancellation.py`). 단일 덱 경로도 동일.
      **한계**: 직렬 실행(풀 없음)은 배치 사이에서만 취소되어 거칠다 — API는 항상 병렬.
      백엔드 1401 · 프론트 289 passed. 브라우저에서 종단 확인.
- [x] **시뮬 딜이 실기록 대비 1.46배 과대 — 코어 판정 + Moran 쿨감 수정 완료 (2026-07-26).**
      Fienn의 두 시즌 전 애니힐리오 솔로레이드 실기록 5덱(합계 34.77B)을 기준점으로
      대조. ① 코어 보너스가 **모든** 데미지 인스턴스에 붙던 것을 **평타 전용**으로
      (지속/분배는 평타여도 제외) ② Moran 애장품 Fervor 상시 −20초 자기 쿨감 인코딩.
      결과 **합계 1.46x → 1.08x, 덱별 편차 0.93~2.00x → 0.87~1.35x**. 백엔드
      1401 → **1406 passed / 3 skipped**. 상세는 `docs/decisions.md` 2건.
- [x] **덱1의 과소평가(0.87x) 규명 — 완료 (2026-07-26).** Fienn이 유닛별 실기록을
      주면서 즉시 좁혀졌다: 홍련 7.30B(실기록 6.5B, **+12% 과대**) · **Liberalio 2.08B
      (실기록 3.86B, −46%)** — 그녀 한 명이 덱 부족분 전부였다. 원인은 Calm Depths
      3번 불릿 `"Deals 40.5%... Activates 5 times."`를 **전투당 5회**로 읽은 것.
      수집 데이터 전수 대조 결과 같은 표현의 다른 유닛은 **전부 `per battle`/`during
      battle`을 명시**하고(Neon: Vision Eye·Nayuta·Rosanna) Liberalio만 한정어가 없다
      → **풀차지마다 5타**로 정정. Liberalio 2.076B → **3.177B**, 덱1 → **11.92B(0.96x)**.
      **다섯 덱에서 과소평가가 사라졌다**(0.87~1.18x → **0.96~1.18x**, 전부 같은 방향).
      실기록이 **여러 번 시도한 최고 기록**임을 감안하면 방향이 맞다.
      배제 기록: 앵커 분산 버프 정상(−9.62%) · 버스트 로테이션은 쿨 40초로 강제 ·
      차지속도 면역은 원문 그대로 · 포뮬러 입력 전부 정상 · 온코어 버프 누적설은
      **Fienn 기각**(`stacks up to` 없음). 백엔드 **1416 passed / 3 skipped**.
- [x] **버스트 넉의 Full Burst 보너스 배선 — 완료 (2026-07-26).** Fienn의 Liberalio
      버스트 검증 요청에서 나왔다. +50% Attack Damage가 925%에 반영되는지는 **정상**
      (버프를 먼저 쏘고 같은 시각에 넉을 기록, 레지스트리가 `applied_at`부터 셈).
      그런데 **Full Burst 보너스는 0.0**이었다 — `full_burst_bonus_eligible` 옵트인이
      per-shot·periodic·resource-scaled에는 다 붙었는데 **평범한 `burst_damage_percents`
      경로에만 안 넘어가고 있었다**. 2026-07-12 판정문이 문자 그대로 "burst skill"에
      대한 것이었으니, 규칙이 겨냥한 경로에 구현이 없던 셈. 대상은 원문을 **불릿 단위로**
      읽어 `liberalio`·`rapi-red-hood` **2개뿐**(나머지 7유닛은 "additional damage"
      불릿이 별도 자원 게이팅 넉이고 이미 플래그가 있다). Liberalio 버스트 **+42.5%**,
      덱1 **0.96x → 0.98x**. B1·B2는 manual 모드의 0.1초 스태거 덕에 구조적으로 제외되나
      **auto 모드는 gap 0.0이라 겹친다**(테스트 도크스트링에 명시). 백엔드
      **1421 passed / 3 skipped**. `docs/decisions.md` 참고.
- [x] **전 유닛 죽은-인코딩 감사 — 완료 (2026-07-26).** 덱2~5는 유닛별 실기록이 없어
      덱1식 진단을 못 쓰므로, 대신 **지금까지 나온 버그 유형을 전 유닛에 훑었다**.
      ① *등록되지만 엔진이 안 읽는 스탯* — 정적 대조(인코딩이 쓰는 스탯 46개 vs 엔진이
      읽는 41개)로 11건 적발, 9건 오탐, **진짜 1건: Ein이 `charge_damage_up`을 쓴다**
      (엔진·타 인코딩은 전부 `charge_damage_bonus`). 그녀의 차지 대미지 버프 2개가
      통째로 죽어 있었고, SR이라 모든 평타에 곱해진다 — **0.347B → 0.682B(+96.5%)**,
      덱 +8.1%. 나머지 1건 `burst_gauge_fill_speed_percent`(Anis: Star)는 의도된
      미구현(게이지 시간은 `BossProfile` 고정 입력)이라 등록 지점에 명시.
      ② *다른 효과에 잘려 죽는 버프* — **구조적으로 닫힘**. `add_refreshing`이
      `refresh_group`을 필수로 요구하고 평범한 효과는 `None`이라 안 잘린다(충돌 형태
      5유닛 전부 안전). ③ *텍스트 오독*은 정적으로 못 잡는다. 백엔드 **1422 passed**.
- [x] **덱2~5 유닛별 대조 착수 — Privaty의 중첩 디버프 수정 (2026-07-26).**
      Fienn이 유닛별 실기록 + 운용(신데렐라 **MG 모드**·덱별 실제 버스트 사용자·파츠
      보너스가 덱 총합에 별도 가산)을 줬다. 덱2가 **전원 1.10x 이상**이라 한 명이 아니라
      덱 전체를 드는 원인을 가리켰고, `privaty.py`가 스스로 "Unconfirmed assumption"으로
      적어둔 자리였다 — LD Assault의 Damage Taken 디버프가 `add`라서 10초 창 안에서
      **중첩**됐다. 적 디버프는 아군 전원이 곱하는 항이라 스쿼드 전체가 부풀었다.
      갱신으로 고치니 **나유타 1.10→0.96 · 리틀머메이드 1.13→0.99 · 벨벳 1.15→1.00**,
      덱2 1.35x → **1.17x**. 기존 E2E 테스트가 중첩 동작을 고정하고 있었다.
      백엔드 **1423 passed / 3 skipped**.
- [x] **"Damage to Parts"를 몸통 딜에서 제외 — 완료 (2026-07-26).** 절대 초과 1위였던
      스노우화이트:헤비암즈(1.44x)의 원인. 엔진이 이 스탯을 `damage_up` 버킷에 넣어
      **모든 타격이 파츠를 맞혔다고 치고** 있었다(noir.py에 명시된 기존 관례).
      실기록이 천장 가정을 직접 반증 — 항을 완전히 빼도 1.88B로 실기록 1.68B보다
      높다. **몸통 딜엔 안 붙는 것으로 확정**(Fienn), 파라미터·인코딩은 존치.
      스노우화이트 **1.44x → 1.12x**, 덱4 **1.14x → 1.02x**, 합계 1.08x → **1.06x**.
      영향 8유닛. 백엔드 **1424 passed / 3 skipped**.
- [x] **차지 대미지를 차지 무기 한정으로 게이팅 — 완료 (2026-07-26).** 신데렐라 MG를
      파다 발견: 벨벳의 스쿼드 Charge Damage +100.8%가 **비차지 무기 평타에도** 곱해져
      덱2 전원이 거의 2배가 되고 있었다. **차지 대미지는 차지 무기에만**(Fienn) —
      단 **나유타는 버스트 무기 변경으로 그동안 차지 형식**이 되므로 무기가 아니라
      **시점**으로 판정해야 한다. 평타는 자기 `ShotRecord.weapon`으로 판정하게 해서
      변형 창이 자동으로 맞았다. `closed_form`도 게이팅.
      **프리바티 2.01x → 0.97x.** 동시에 **가려져 있던 과소 모델링이 드러났다** —
      리틀 머메이드 0.99x → **0.55x**, 나유타 0.96x → 0.79x, 신데렐라 MG 1.31x → 0.84x.
      백엔드 **1430 passed / 3 skipped**.
- [x] **탄약 소모량 카운터를 라운드 단위로 배선 — 완료 (2026-07-26).** "탄약 파우치에서
      N발 소모"는 **실탄 1발을 쏘고 장부에 N발을 올리는 것**이고, 그 장부는 애초에
      리틀 머메이드의 버블 배러지 같은 **소모량 연동 시너지를 먹이려고** 존재한다
      (Fienn 2026-07-19 판정, `cinderella_crystal_wave.py`에 이미 적혀 있었다).
      카운터는 총알이 아니라 라운드를 세야 한다 — 벨벳 풀버스트 중 300 / 밖 100,
      신데렐라 스나이프 40. **리틀 머메이드 0.55x → 0.76x**(배러지 28회 → 89회),
      덱2 0.76x → 0.82x. 백엔드 **1435 passed / 3 skipped**.
- [x] **나유타 풀차지 넉에 FB 보너스 부여 — 완료 (2026-07-26).** 530.46%(=150% +
      380.46%) 전체가 대상이다. **FB 보너스의 기준은 문구가 아니라 연산 시점**이며
      (Fienn), 이 넉은 풀차지 1.8초 후 = 버스트 이후이므로 항상 FB 구간 안이다.
      **나유타 0.79x → 0.85x.**
- [x] **"시전자 기준"의 정의 확정 — 완료 (2026-07-26).** 시전자의 **기본 스탯**(장비·큐브·
      소장품 포함, **전투 중 부가효과 제외**) 기반이다(Fienn). 현재 엔진의
      `caster_atk = base_stats["atk"]` 관례가 맞다. 나유타 스킬1 2번 불릿은
      **타이밍도 값 기준도 모두 정상**(3초 간격 < 5초 지속이라 t=3s부터 영구 효과로
      축약, 결과 동일). 참고로 덱2 라이브/기본 ATK 비율은 나유타 2.05 · 신데렐라 2.37 ·
      리틀머메이드 1.99 · 프리바티 1.93 · 벨벳 1.88이었다.
- [x] **오버로드 ATK%는 `caster_atk`에 넣지 않는다 — 확정 (2026-07-26).** Fienn이 말한
      "장비 스탯"은 **장비의 HP/ATK/DEF 수치**를 뜻하며 **오버로드 옵션은 시전자 기준
      버프에 포함되지 않는다.** 실측도 같은 방향이었다(포함 시 유닛별 평균 절대오차
      0.178 → 0.192, 정확한 유닛들이 전부 1.0 초과). 현행 유지.
- [x] **"코어 명중 대미지"에 코어 보너스 배선 — 완료 (2026-07-26).** 스킬 딜이지만
      **코어 보너스 배율과 코어 대미지 증감 효과를 받는다**(인게임 툴팁). `core_strike`
      대미지 타입 신설, `core_eligible`이 소스 무관 True. **신데렐라 MG 0.84x → 0.89x.**
      로스터 유일 소비자라 다른 유닛은 안 움직인다.
- [x] **나유타·리틀머메이드 4항목 확인 완료 (Fienn, 2026-07-26).** Bubble Order 1번
      불릿 = 조준점 동기화(DPS 무관, 미모델이 정답) · 폭발 거품은 Bubble을 **교체**
      (추가 딜 없음이 정답) · 나유타 변형 창 **10초에 5발**(현행 일치) · MG 60발/초 일치.
      신데렐라 [변경 준비] 재장전 3초 고정은 **적용되지 않음**을 확인(프로필 2.5초).
- [x] **리틀 머메이드 전수 검증 완료 — 특정 결함은 남아 있지 않다 (2026-07-26).**
      스킬 원문의 모든 불릿을 Fienn 확인과 대조했다: Bubble Order 1번 불릿 = 조준점
      동기화(DPS 무관) · Bubble/폭발 거품은 교체 관계(추가 딜 없음) · FB 주기 넉
      1초마다 4연타(540히트 = FB 135초) · 버블 배러지 아군 500라운드마다 10연타
      (89회) · **스킬 딜에 [코어 명중 대미지] 표기 없음** → 코어 보너스 미수령이 정답.
      그녀는 0.55x → **0.76x**까지 올라왔고, 남은 −0.51B는 지목 가능한 결함이 아니라
      로스터 전반의 잔여 편차와 같은 성격으로 분류한다.
- [x] **신데렐라 버스트 1번 불릿 검증 (2026-07-26).** 자기 AD +92% / ATK +65%가 같은
      버스트의 6000% 넉에 **적용된다**(절제 시 1.959배 차이). [변경 준비] 재장전 3초
      고정은 적용되지 않는다(프로필 2.5초).
- [x] **관통을 속성으로 배선 — 완료 (2026-07-26).** **관통 대미지 증가는 관통 속성을
      가진 유닛에게만 적용된다**(Fienn). 판별은 스킬 원문의 [관통 특화] / "Gain Pierce".
      `has_pierce` 스탯 신설(정적 목록이 아니라 **효과 창** — 15기 중 다수가 시간·발수
      한정), `_damage_instance`와 `closed_form` 양쪽에 게이트. 보유자 15기 인코딩 완료.
      **덱5 1.14x → 1.03x · 덱4 1.01x → 0.90x · 합계 0.977x → 0.950x.**
      초과 유닛이 정확해지고(민트 1.19→1.00 · 네온 1.38→1.25 · 아크레인저 1.18→1.08)
      미달 유닛은 더 내려갔다(신데렐라 0.88→0.70 · 미하라 0.80→0.70 · 목단 0.97→0.84)
      — 가짜 버프가 걷히자 계통적 과소 모델링이 드러난 것.
- [x] **잔여 편차의 공통 원인 조사 — 없음으로 결론 (2026-07-26).** 다섯 후보를 실측
      기각했다: 미모델 항목 수 · 속성 우위 · 코어 히트 노출도 · 무기 종류 · 덱 단위 원인.
      상세와 각 반증 수치는 `docs/insights.md`. 남는 것은 전역 **−3.4%**(실기록이
      최고 기록이라는 것으로 설명됨)와 유닛별 **±16%** 산포다.
      **다음부터는 절대 오차 순으로 개별 유닛을 본다**: scarlet **+0.80B** ·
      cinderella **−0.60B** · little-mermaid −0.51B · liberalio −0.45B ·
      nayuta −0.37B · neon +0.31B · mihara −0.29B.
- [x] **홍련(스칼렛: 블랙 섀도우) 조사 완료 — 결함 없음 (2026-07-27).** 절대 오차
      최대(+0.80B, 1.12x)였으나 인코딩 결함은 없었다. 대신 **미해결 가정 두 개가
      실기록의 지지를 받았다**: 차지 대미지 버프는 스킬 넉에도 붙고(빼면 0.62x),
      분산 대미지는 단일 보스에게 전량 들어간다(절반이면 0.76x). 버스트 주기와
      발사 간격도 검증. 상세는 `docs/insights.md`. 가정 A의 검증은 벨벳·네온의
      넉에도 그대로 적용된다.
- [x] **차지 대미지를 평타 전용으로 게이팅 — 완료 (2026-07-27).** nikke.gg와 프로젝트
      자체 레퍼런스가 모두 **평타 전용**이라 명시하고 Fienn이 확인했다. 스킬 넉·버스트
      넉·DoT는 시전자가 차지 무기를 들었어도 못 받는다. `closed_form`도 동일.
      **홍련 1.12x → 0.62x · 신데렐라 0.88x → 0.61x · liberalio 0.88x → 0.80x**,
      개선: 스노우화이트 1.12 → **0.97** · 네온 1.25 → 1.18 · 헬름 1.52 → 1.46.
- [x] **홍련 단계 넉에 FB 보너스 부여 — 완료 (2026-07-27).** 각 단계는 자기 샷의
      시각에 연산되므로 문구와 무관하게 FB 창 검사를 받아야 한다. **홍련 0.62x → 0.76x**,
      덱1 0.688x → 0.757x.
- [x] **홍련의 실기록 기준선은 유효하다 (Fienn, 2026-07-27).** 기록은 **7월 6일** —
      2026-06-23 솔로레이드 중단과 07-02 계수 상향(+13%) **이후**다. 계수도 현행이고
      분배 대미지 버그도 없는 상태이므로 6.5B를 그대로 기준으로 쓴다.
- [x] **단계 카운터의 버스트 경계 인계는 정상 (2026-07-27).** Fienn 시나리오("6회 조건
      만족 직후 버스트 → 다음 평타가 9회 조건 만족")를 추적 검증했다. 기존 회귀 테스트가
      **같은 알고리즘을 재구현해 기대값을 만드는 동어반복**이었어서, 하드코딩 기대값
      행동 테스트 2건으로 교체했다.
- [x] **마스트: 로맨틱 메이드 스택 조사 — 결함 2건 수정 (2026-07-27).** 궤적은 의도대로
      **1,2,3,3,3**이 맞았다(앵커가 있어 행오버 리셋 없음). 그러나 ① 스택을 **그녀 자신의
      발동 횟수**로 세고 있었다 — 취기는 "버스트 1단계 진입 시" 쌓이는 **스쿼드 이벤트**인데,
      덱1에서 그녀는 앵커와 슬롯을 번갈아 써 15사이클 중 7번만 버스트한다 → 버스트 버프가
      매번 한 스택씩 부족했다. ② 2스킬의 **분배 대미지 ▲15.03%×스택**이 "survivability"로
      오분류돼 **통째로 누락**돼 있었다 — 같은 덱의 홍련이 딜의 65%를 분산 대미지로 낸다.
      **홍련 0.76x → 0.90x · 덱1 0.757x → 0.837x.**
- [x] **분산 대미지 전수 감사 — 완료 (2026-07-27).** 딜러 5기(홍련 · phantom(+시그) ·
      **quency-escape-queen** · bready · milk)와 버퍼 4기(앵커 · 마스트 · phantom ·
      quency)를 원문 대조했다. 결함 1건: **Quency: 이스케이프 퀸의 버스트**(1736.31%
      "as Distributed Damage")가 `_BURST_DAMAGE_TYPES`에 없어 `attack`으로 처리되어
      **자기 자신의 +49.58% 분산 버프조차 못 받고** 있었다 → 배선. 나머지는 정상이고,
      phantom의 12.86% 스택분은 의도된 defer(베이스 빌드는 최대 스택 도달 불가).
      스킬 레퍼런스의 "engine status: inert" 문구도 낡아서 갱신했다.
- [x] **Shooting Stars에 FB 보너스 부여 — 완료 (2026-07-27).** Fienn 지적: 아니스의
      버스트와 풀버스트 발동 사이는 **0.2초**, 틱 간격은 **0.25초** — 첫 틱부터 이미
      창 안이다. FB 보너스의 기준은 문구가 아니라 연산 시점이므로 40틱 전부 자격을 준다.
      엔진이 틱별로 창을 대조하므로 **근사가 아니라 정확**하다. 아니스 0.748B → **0.816B**,
      덱1 0.837x → **0.842x**. `test_roster.py` 골든 핀 재기준화(비율 1.0345 → 1.0335 —
      별은 사이클당 고정 40틱이라 재장전 버프가 더 사도록 만들지 못하고, 별이 커진 만큼
      재장전이 움직일 수 있는 딜의 비중이 희석된다).
- [x] **신데렐라 검증 — 결함 3건 수정 (2026-07-27).** ① 단계-3 ATK 버프가
      `own_burst_activate`(원문은 "entering Burst Stage 3" = **단계** 이벤트) ②
      퍼샷 넉이 FB 보너스 미수령(원문 "as additional damage" — 07-26 감사가 **버스트
      경로만** 훑어 놓친 두 번째 불릿) ③ Beautiful의 **Max HP ▲1.6%/스택 미부여**.
      실측 **B3 단독 +9.8% · B3 공유 +22.1%**. 상세는 `docs/decisions.md`.
      **다만 셋을 합쳐도 0.61x → 1.0x에 못 닿는다** — 아래 항목 참조.
- [ ] **⚠ "신데렐라 0.61x"는 재현되지 않는다 — 실제로는 과대다 (2026-07-27 실측).**
      Fienn이 준 덱4 편성(볼륨 · 민트 · 프리카 · 신데렐라 · 스노우화이트:헤비암즈)과
      유닛별 기록(0.174B · 0.178B · 0.190B · **2.007B** · 1.683B)으로
      `scripts/measure_deck_breakdown.py`를 돌리면 신데렐라는 **수정 전 0.87~1.26x ·
      수정 후 1.10~1.55x**(4개 편성순서 전 범위)로 나온다. **어떤 순서·보스 설정으로도
      0.61x가 안 나온다**(코어/파츠 토글은 1.55↔1.38까지만 움직인다).
      **하네스 쪽 문제가 아니다** — 같은 실행에서 스노우화이트:헤비암즈 **1.00x** ·
      민트 1.02x · 프리카 0.98x로 셋이 기록에 정확히 안착한다(가장 그럴듯한 순서는
      `volume > prika > mint > snow-white-heavy-arms > cinderella`).
      따라서 캘리브레이션 표의 **신데렐라 0.61 · 덱4 0.80은 신뢰할 수 없다**.
      이상치는 **신데렐라 1.48x(과대)** 와 볼륨 0.71x(미달) 둘이다.
      속성은 원인이 아니다(엔진은 우위 +10%만 적용하고 열세 패널티는 없는데,
      1.00x인 스노우화이트도 신데렐라도 둘 다 우위가 아니다).
      **원인 특정됨 (2026-07-27, Fienn 사격장 측정)** — 아래 항목.
- [x] **볼륨 CDR 티어는 누적이다 — 확정·반영 (Fienn, 2026-07-27).**
      2.34 → 5.04 → **8.21초**. 실측 덱4 1.24x → **1.53x**, 180초 풀버스트
      11 → **14회**.
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
- [x] **볼륨의 Drop the Beat 크리 대미지가 처음부터 최대치 — 수정 완료 (2026-07-27).**
      `volume.py`가 세 에스컬레이션 단계를 **합**해서 **전투 시작부터** 스쿼드에
      걸고 있었다. `escalating_buff_rule`(앵커 선례)로 교체 — 1회차 티어1, 2회차
      티어1+2, 3회차부터 전부. 사격장 대조에서 `other_critical_damage_sources`가
      **0.1536**(= 오버로드 0.0762 + 티어1 0.0774)으로 실측과 정확히 일치하고,
      불릿1 논크리·크리가 **둘 다 1.0000x**로 재현된다.
      **덱 총합 영향은 작다**(덱4 1.24x → 1.24x): 티어가 갈리는 것은 1~2사이클뿐이고
      버프 지속이 5초라 11사이클 중 비중이 작다. 정확도 수정이지 과대 해소가 아니다.
- [x] **"버스트 N단계 진입 시" 배선 전수 정리 — 완료 (2026-07-27).**
      두 표현은 B3 캐스트를 사이에 둔 **서로 다른 순간**이다(3단계 진입은 캐스트 前,
      풀버스트 시작은 後). 아래 수정 전에는 두 순간이 동시각이라 오류가 안 보였다.
      고친 유닛 5기 — `mint`(Fienn 지적) · `mihara-bonding-chain` · `rei-ayanami` ·
      `snow-white-heavy-arms`(**두 불릿이 한 룰에 묶여 있어 분리**: Fully Active는
      자기 버스트 유지, Shades of White만 stage-3로) · `mast-romantic-maid`(**2건** —
      Spirit의 분산 대미지는 stage-3, Heart의 Drunken 상시 버프는 stage-1).
      `maiden-ice-rose`는 **오탐**이었다: 그녀의 MP는 SkillRule이 아니라 자원
      시스템이 처리하고 원문도 "entering **Full Burst**"라 현행이 맞다 — 파일 안의
      `_full_burst_enter` **헬퍼 이름**이 grep에 걸린 것이다(불릿 단위로 봐야 한다는
      교훈에 스크립트가 걸린 사례).
      **함정 하나**: 마스트의 스택 카운트는 `((cycle−1) % 3) + 1`로 **순환**하므로
      "최초 1회" 게이트에 쓰면 4번째 사이클에 재발동해 영구 버프가 중복 적립된다 —
      원시 카운터(`_burst_stage_one_entries`)를 분리했다.
      실측: 덱4 1.19x → **1.24x**(스노우화이트 1.00 → 1.06 — 그녀 ATK 버프 지속률이
      5/11 → 11/11이 됐다). **정확도는 올랐지만 과대는 줄지 않았다.**
- [x] **★ B3의 자기 버스트가 `full_burst_enter` 버프를 먹는다 — 수정 완료 (2026-07-27).**
      사이클은 [3단계 진입 → **B3 사용** → **풀버스트 시작**]이므로 B3의 버스트 대미지는
      풀버스트가 열리기 **직전**에 연산된다 → **FB 보너스도, `full_burst_enter` 버프도
      받으면 안 된다**(Fienn 판정, 2026-07-27). 엔진은 호출 순서는 맞지만 **둘이 같은
      타임스탬프**라 Phase 2의 `applied_at <= time`이 함께 걷는다.
      **파급: `full_burst_enter`로 버프를 주는 유닛 30기 이상 × 모든 덱의 B3 딜러.**
      이 판정을 넣으면 사격장 4개 값이 **1.0000x / 1.0000x / 0.9952x / 0.9952x**로 전부
      맞는다. 상세는 `docs/insights.md`.
      ※ 한때 크라운의 One for All 자체를 결함으로 적었으나 **철회**했다 — 대상 범위는
      B1·B2·B3 전원이 맞고, 문제는 대상이 아니라 **타이밍**이었다.
- [ ] **신데렐라 버스트의 다단히트는 동시가 아니라 0.2초 간격 순차다 — 미반영.**
      Fienn 실측(FB 잔여 9.05 → 7.25): 10히트가 **1.80초**에 걸쳐 0.200초 간격.
      `raid_simulator`는 "All N hits land at the same instant"로 주석까지 달고 동시
      처리한다. 그리고 불릿2는 **1회 넉이 아니라 히트마다 붙는 라이더**다 — 아름다움
      0스택 캐스팅에서 t=3(1스택) 이후 남은 **정확히 4히트**만 대미지가 들어갔고,
      0.2초 간격 모델이 이를 정확히 재현한다(t=1.95부터 3.15/3.35/3.55/3.75).
      불릿2는 FB 보너스도 받는다(위 M₂/M₁=1.5). 셋 다 그녀를 **키우는** 방향이다.
- [x] **"버스트 N단계 진입 시" 전수 감사 완료 — 결함 2건 추가 적발 (2026-07-29).**
      한때 이 자리에 "6기 잔존(ein · maiden-ice-rose · mast(3단계) · mint ·
      rei-ayanami · snow-white)"이라고 적혀 있었으나 **그 목록이 양방향으로 틀렸다**:
      네 기는 07-27에 이미 고쳐졌고 maiden-ice-rose는 오탐이며, **정작 빠져 있던
      `laplace-ultimate-hero`가 결함이었다.**
      원인은 07-27 감사가 **한 가지 표현만 grep**했다는 것이다 — 에인의 원문은
      "entering Burst **Skill** Stage 3"이고, 라플라스(UH)는 ShiftyPad 수치만 있어
      **대조할 원문 자체가 없다**. 둘 다 구조적으로 안 보였다.
      `scripts/audit_burst_stage_triggers.py` 신설 — 93 슬러그 전체에서 **수집 원문 ↔
      배선**을 대조하고, 표현 변종·원문 없음·다른 표현을 각각 별도 버킷으로 보고한다.
      **수정 2건:** 에인 Feather Standby 자ATK +70.12%(버스트 스킬 버프 2개와 한 룰에
      묶여 있어 먼저 분리) · 라플라스(UH) Over Energy 자AD +52.14%. 둘 다 독스트링이
      반증된 근거("그녀가 B3 슬롯이니 그 순간이 자기 캐스트")를 명시하고 있었고,
      라플라스 쪽은 **낡은 테스트가 그 동작을 고정**하고 있었다.
      **효과: B3를 2기 앉힌 덱에서 에인 덱 +3.81% · 라플라스 덱 +1.12%**
      (`ally_burst_activate`로 바꾸기 전과의 인프로세스 A/B).
      두 유닛 다 실기록 5덱에 없어 **캘리브레이션은 1.011x 그대로**(덱별·유닛별 전부 불변).
      감사가 무죄로 판정한 3기: maiden-ice-rose(MP는 자원 시스템이 **스쿼드 단위**로
      이미 처리) · velvet(탄약 파우치 fill은 미모델이고 6000이라 구속력 없음) ·
      soda-twinkling-bunny(Beginner's Rewards 전체가 FB 지속시간 확장 미지원으로 deferred).
      백엔드 **1561 passed / 3 skipped**.
- [ ] **에이드: 에이전트 바니 1.57x는 관통과 무관한 별개 문제.** 그녀는 관통 보유자라
      위 모델에서 값이 안 변한다. 딜이 100% 평타(0.16B, 169발, SR)뿐이라 원인은
      그녀의 무기 프로필 또는 받는 버프 쪽이다.
- [ ] **덱2가 유일하게 남은 구조적 이상치 (0.86x).**
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

- [x] **★ 대조 하네스가 엉뚱한 보스와 싸우고 있었다 — 정정 완료 (2026-07-27).**
      `RECORD_BOSS`가 `element="Water"`였고 독스트링이 "Wind attackers get
      advantage"라고 정당화하고 있었는데, **`element`는 보스 자신의 코드**이고
      순환상 Wind가 이기는 것은 **Iron**이다. 실기록 원문에 "애니힐리오: **철갑**
      =Wind 약점"이라고 이미 적혀 있었다. `"Water"`는 보스를 **Electric 약점**으로
      만들어 신데렐라(Electric)에게 원소 배수 **1.0 → 2.079**(우위 1.1 + 그때만
      열리는 `other_elemental_bonus` 0.979)를 주고 볼륨(Wind)에게선 실제 우위를
      뺏고 있었다 — **이 세션이 쫓던 두 이상치가 같은 한 줄에서 나왔다.**
      `element="Iron"`으로 정정 + `test_elements.py`에 상수 고정.
      **덱4 1.533x → 1.081x**, 유닛별 **0.78~1.88 → 0.90~1.29**:
      볼륨 0.784→**1.012** · 신데렐라 1.875→**0.902** · 프리카 1.069 · 민트 1.184 ·
      스노우화이트 1.291. 백엔드 **1461 passed / 3 skipped**.
      상세는 `docs/decisions.md` · `docs/insights.md`.
- [x] **실기록이 드디어 픽스처가 됐다 (2026-07-27).** Fienn이 5덱 편성과 유닛별
      기록을 전부 줬고 `scripts/raid_record.py`에 못박았다 — 지금까지는 **어디에도
      없어서** 세션마다 대화 중에 재구성하고 버렸고, 그래서 재현 불가능한
      "신데렐라 0.61x" 같은 값이 표에 남아 있었다. `scripts/measure_record_calibration.py`
      가 5덱을 한 번에 채점한다. 슬러그 해석 주의: **레이(가칭)=`rei-ayanami-tentative-name`**
      (`rei-ayanami`와 별개) · 라피(B1)=`rapi-red-hood-b1`(모드 변형) ·
      프리바티/목단/헬름은 **애장품 빌드**(`-signature`).
      **덱2 무기 모드도 확정**: MG 0.839x vs 스나이프 0.669x → **MG가 실기록**이다
      (전부터 미해결로 적혀 있던 항목).
- [ ] **캘리브레이션 현황 (2026-07-27, 보스 원소 정정 후 · 전부 재현 가능).**
      명령 하나로 재현: `python3 scripts/measure_record_calibration.py`
      덱별: 덱1 **0.842** · 덱2 **0.838** · 덱3 **0.966** · 덱4 **1.081** · 덱5 **1.016**
      **합계 0.914x**, 25유닛 중 **±15% 이내 12기**.
      *(정정 전 잘못된 보스 기준: 0.519/0.573/0.603/1.533/1.089, 합계 0.741x,
      ±15% 이내 5기 — 덱1·2·3이 Wind 편성이라 우위를 통째로 못 받고 있었다.
      **Wind 약점 보스에 Wind 덱을 짜는 건 당연하므로 이게 가장 강한 확증이다.**)*
      **과대 3기**: 에이드 **1.535** · 헬름(애장품) **1.435** · 스노우화이트 **1.323**
      **미달 3기**: 아니스:스타 **0.594** · 미하라 **0.697** · 리틀머메이드 0.759
      이제 **미달과 과대가 양쪽에 있다** — 이전의 "미달 쪽에 몰려 있다"는 관측은
      잘못된 보스가 만든 것이었다.
- [x] **소장품 스킬 효과 배선 완료, 캘리브레이션은 아직 무변동 (2026-07-27).**
      gap #17(에이드의 사격장 균일 편차 0.94315x = SR 소장품 「차지대미지 6.31%
      배율」 누락)를 5개 태스크로 배선 — 데이터 테이블 → 리졸버 → 유닛별 배선
      (`UserNikkeState`/`NikkeSpec`) → 데미지 적용 → 프론트 페이로드. 배선 후
      `python3 scripts/measure_record_calibration.py`를 재실행해 배선 전과 대조한
      결과 **수치가 완전히 동일**하다(합계 0.914x, 덱별 0.842/0.838/0.966/1.081/1.016,
      ±15% 이내 12/25) — 실제 로스터(`tools/collect-blablalink/roster-drafts.json`)가
      `NikkeDraft[]` 형태라 `collectible_tid` 필드 자체가 없고
      `scripts/roster_fixture.py::_state_from_draft`도 그 필드를 안 읽어 전원 미보유로
      떨어지기 때문이다. 회귀가 아니라 **배선이 소장품 미보유 유닛에 정확히 무해하다는
      확인**. 백엔드 1479 passed / 3 skipped, 프론트 291 passed 유지. 상세
      `docs/decisions.md` ADR, `docs/engine-gaps.md` gap #17.
- [x] **소장품 데이터 부채 종결 — 전 등급(R/SR/SSR) 실데이터 (2026-07-27).**
      "SMG·RL 없음 · SR/SG/AR은 툴팁 유도 · R 사다리 미상"이 전부 닫혔다. 막고
      있던 것은 로그인이 아니라 **요청 자체**였다 — 소장품 테이블은 로그인한
      Collection 화면에서만 요청되므로 헤드리스로 돌려도 가로채기는 빈손이다.
      ShiftyPad의 CDN 경로 난독화가 **경로의 순수 함수**(djb2 + md5)임을 앱 번들에서
      옮겨 적어(`tools/collect-blablalink/resource-url.js`) 테이블을 **브라우저·세션
      없이 평범한 HTTP GET**으로 받는다. 33개 레코드 전량 커밋(R 6 · SR 6 · 애장품
      SSR 21), 갱신은 `node collect.js --collectibles` → `python3
      scripts/update_collectible_table.py`. **툴팁 유도값이 옳았음이 확인됐다** —
      SR 무기군 사다리 `[4.74, 6.31, 7.89, 9.47]`에서 에이드 5단계 = 6.31.
      부수로 잡은 결함: R과 SR은 스탯 커브가 갈리는데(최대 ATK 4,736 vs 9,688)
      `stat_assembly`가 커브 하나만 읽어 R 보유자를 2배 넘게 과대평가하고 있었다.
      백엔드 **1486 passed / 3 skipped**. 상세 `docs/decisions.md` ADR 2건,
      `docs/engine-gaps.md` gap #17.
- [x] **엔진 결함 2건 수정 — 합계 0.936x → 1.011x, 미달이 반감됐다 (2026-07-28).**
      절대 오차 순으로 파고들다 나온 두 건이고, 둘 다 **사격장 측정으로 확정한 뒤에만**
      건드렸다. 상세는 `docs/decisions.md` ADR 2건.
      1. **평타가 Full Burst 보너스를 못 받고 있었다**(gap #18). 실측 5덱 전 유닛이
         해당 — 창 안 비율 77~89%인데 전부 0이었다. 옵트인 플래그가 스킬 넉에만
         달려 있고 평타 경로는 애초에 안 넘기고 있어서, 규칙이 재구성될 때
         **재검토 목록에 오르지도 않았다.** 아니스 평타가 창 밖 1,586,816 · 창 안
         7,492,265로 정확히 1.25배 갈려 확정(0.00003% 일치). → **0.936x → 1.023x**,
         미달 −3.884B → −1.954B. 골든 테스트 19건은 `fb_factor()`로 창 상태를
         명시하도록 재구성.
      2. **「순차 공격 대미지 158.4%」가 계수에 곱해지고 있었다.** 실제로는
         `attack_damage_up`과 같은 **가산 버킷**이다(실측 1.69249 =
         1 + 1.584/(1+1.2874), 분모는 엔진이 그 순간 계산한 버킷). 신규 타입 게이팅
         `"sequential"`로 순차타에만 닿게 하고 스윕은 분리. → 스노우화이트
         **1.424x → 1.152x**, 과대 +2.760B → +2.302B, 전체 **1.011x**.
      **그 시점 캘리브레이션:** 덱1 0.946 · 덱2 0.938 · 덱3 1.100 · 덱4 1.094 ·
      덱5 1.121, 합계 1.011x, ±15% 이내 10/25, 미달 −1.903B · 과대 +2.302B.
- [x] **아스카의 자기 디버프가 통째로 빠져 있었다 — 1.192x → 1.055x (2026-07-28).**
      Annihilation State는 세 효과를 한 번에 거는데(자ATK +46.8% · 공격력 +36% ·
      **평타 대미지 배율 ▼40%**, 전부 9초) 인코딩이 앞의 둘만 걸고 있었다.
      독스트링에 적힌 보류 사유("평타에만 스코프를 거는 수단이 엔진에 없다")가
      **낡은 판단이었다** — `normal_attack_damage_multiplier`는 gap #9에서 이미
      만들어져 질 발렌타인이 쓰고 있다. 이 스탯의 **음의 방향**일 뿐이다.
      그리고 이 누락은 작지 않다: 그녀의 버스트가 곧 풀버스트 시작점이라 9초 창이
      **가장 비싼 발들**을 덮는다 — 덱3에서 그녀 평타 데미지의 **62.1%**가 창 안이다.
      → 3.345B → 2.960B, 덱3 1.100 → **1.037**, 합계 **1.011x → 1.000x**,
      ±15% 이내 10/25 → **11/25**, 과대 +2.302B → +1.917B.
      **재발 방지:** "엔진이 X를 못 한다"는 보류 사유는 유통기한이 있다.
      gap이 닫히면 그 사유로 보류된 유닛을 되짚어야 한다 — 같은 사유가 아르카나
      (Snapshots of Youth)에도 남아 있어 사유를 정정해 뒀다(스택 수가 불확실해
      인코딩은 Fienn 확인 후).
      **현재 캘리브레이션:** 덱1 0.946 · 덱2 0.938 · 덱3 **1.037** · 덱4 1.094 ·
      덱5 1.121, **합계 1.000x**, ±15% 이내 **11/25**, 미달 −1.903B · 과대 +1.917B.
      백엔드 **1488 passed / 3 skipped**.
- [x] **아르카나의 페이즈 회전 인코딩 — 그녀 +11.7%, 덱 총딜 +2.40% (2026-07-28).**
      Fienn 관측으로 skill2의 "공격 횟수에 따라"가 임계값 3개가 아니라 **2타마다 셋 중
      하나씩 도는 회전**(2 재장전 / 4 행복한기억 / 6 소중한추억, 반복)임이 확정됐다.
      결정적 근거는 **부정형**이었다 — 12타에서 행복한기억·재장전이 안 뜬다(임계값
      모델이면 셋 다 떠야 한다).
      **사격장 측정으로 확정한 것:** 소중한추억 ATK +2.49%/스택(3회 독립 측정이 단일
      버킷값 1+A=2.6927로 0.007% 일치) · **기본 펠릿 10**(데이터 소스에 없는데
      "증가분이 일정해지는 P"로 풀렸고 Fienn이 인게임 확인, 펠릿 자체는 데미지 갭이
      아니다 — `docs/engine-gaps.md`) · **청춘의기록(Snapshots of Youth)은 스택당
      한계효과 +9.13573%로 작동한다** — 그녀의 SG 소장품(레벨 15, 배율 1.0946)이
      이미 같은 "일반 공격 대미지 배율" 버킷에 값을 채우고 있어 명목 +10%가
      `0.1/1.0946`로 줄어든 것(잔차 3e-07, 2026-08-03 확정, `docs/decisions.md`·
      `docs/measurements/arcana-fortune-mate-happy-memories.md`).
      **엔진 확장 3건:** `per_shot_cycle_from_own_burst_to_full_burst_end`(창마다
      리셋되는 위상 카운터) · 자원 리셋 트리거 `full_burst_end` · `resource_gated_buffs`의
      `at:"full_burst_end"`/`value_per_stack`/`member_filter`.
      상수로 접지 않은 이유: 회전이 어디까지 도는지를 **덱이 정한다**(단독 창당 14발 =
      각 2스택, 토브 공속 시 22발 = 셋 다 3스택). 백엔드 **1491 passed / 3 skipped**.
      아르카나는 실기록 5덱에 없어 **캘리브레이션 합계는 1.000x 그대로**다.
- [x] **아니스:스타 조사 — "추가 대미지" per-shot 넉이 FB 보너스를 못 받고 있었다 (2026-07-28).**
      그녀의 Starfall은 원문이 "Deals 120.13% of final ATK as **additional** damage"인데
      `full_burst_bonus_eligible`을 안 넘기고 있었다. 훑어보니 per-shot 넉 38개 중
      **21개가 미플래그**였고, 헬퍼 독스트링은 **2026-07-12의 옛 문구 규칙**을 그대로
      들고 있었다(07-26에 "연산 시점으로 판단"으로 재구성됐는데도).
      **두 규칙이 합의하는 곳에만 적용했다** — 원문에 "as additional damage"가 있는
      5유닛 6개 호출. → **리베랄리오 0.922x → 1.006x**(−0.302B → +0.024B) ·
      아니스 0.703x → 0.739x · 덱1 0.946 → **0.977**. **덱2~5는 완전히 불변.**
      미달 총합 −1.903B → **−1.552B**. 백엔드 **1491 passed / 3 skipped**.
      **미해결로 남긴 것:** plain "as damage" per-shot 넉 15개. 일괄 적용하면 합계가
      1.025x로 오르지만 스노우화이트가 1.386x로 튄다 — 반면 그녀 본인의 실측은
      "as damage" 스윕도 보너스를 받는다고 말한다. 가르는 측정법은 `docs/insights.md`.
      **아니스의 잔여 −0.358B는 발당 계층이 아니다** — 세 소스가 같은 창 안에서
      맨계수 대비 정확히 분해되고(코어 1.5388 · 발사체폭발 버킷 1.4994 · FB 1.3687),
      원소 페널티는 없으며, 버스트 15회·창 141.6초/180초가 정상. 명명된 잔여
      과소모델은 **탄창 단위 차지속도 샘플링**뿐이다(0.7초 간격 71.9% vs 가동률 79.9%,
      약 +0.038B).
- [x] **FB 보너스 판정을 「연산 시점」으로 확정하고 문구 규칙을 삭제 — ±15% 이내 13/25 (2026-07-28).**
      Fienn이 규칙의 정체를 정리해줬다: **"as damage" 문구가 못 받는 것처럼 보인 이유는
      B3 즉발 스킬이 FB 진입 이전에 연산되기 때문**이지 문구 자체가 아니다. 진입 이후에
      연산되면 "as damage"여도 받는다.
      **결정적 측정은 이미 있었다** — 크리/논크리 비가 완벽한 탐침이다(FB는 크리와 같은
      가산 버킷의 +0.5라 분모에 남고 나머지는 상쇄된다). 원문이 "as damage"인 스노우화이트
      오토파이어: 창 밖 **1.586000**(무보너스 가설 0.00001% 일치) · 창 안 **1.390667**
      (보너스 가설 0.00000% 일치). 가설 간격 12~14%.
      **삭제한 것:** `full_burst_bonus_eligible` 배선 전부(엔진 파라미터·`Pulse` 필드·
      헬퍼 인자·스펙 키·약 40개 호출부·테스트 단언·유닛 독스트링의 판정 서술).
      **살린 것:** 플래그가 겸하던 **시각 이동**(버스트 넉·자원스케일 DoT를
      `FULL_BURST_OPEN_DELAY`만큼 뒤로)은 진짜 모델링 결정이라 **`resolves_after_cast`**로
      이름만 바로잡았다.
      **결과:** 리틀머메이드 0.850→**1.048** · 미하라 0.753→**0.909** · 라피 0.924→**0.990** ·
      신데렐라:CW 0.897→**0.962** · 아스카 1.055→1.074 · 스노우화이트 1.152→**1.386**.
      ±15% 이내 11/25 → **13/25**, 미달 −1.552B → **−0.873B**, 과대 +1.942B → +2.487B.
      백엔드 **1490 passed / 3 skipped**. 검증은 **순수 삭제 불변식**(판정만 바꾼 실험과
      배선 제거 후 결과가 완전히 동일해야 한다)으로 했고, 실제로 아크레인저가 시각 이동을
      잃은 것을 이 검사가 잡았다.
- [x] **스노우화이트 재감사 — Fully Active가 탄창을 공유한다 (2026-07-28). 1.386x → 1.320x.**
      **발당 계층은 두 번째로 무죄.** 실측 덱4에서 엔진이 Fienn의 사격장 비를
      **12.60024 vs 12.60025**로 재현하고, 한 발의 포뮬러 항이 전부 손으로 재현되며,
      버스트 케이던스는 **같은 덱의 신데렐라(0.971x)**가 보증한다 — 공유 버프가
      부풀었다면 그녀도 같이 부풀었을 것이다.
      **Fienn 인게임 확인 3건 중 2건은 엔진이 맞았다:** 오토파이어 15발은 Fully Active
      **한 발당**이고, **두 발 모두** +528% 차지·+158.4% 순차를 받는다(「for 1 round」이
      한 발만이 아니다). 틀린 것은 **탄창 공유** — 엔진은 Fully Active 2발이 탄을 안 쓰고
      세그먼트 종료 시 **새 탄창으로 재개**해서 180초에 재장전이 1회뿐이었다.
      신규 `shares_magazine` 옵트인(`attack_rate._shared_magazine_shots`)으로 수정.
      **진짜 무기변형(스칼렛·맥스웰·라플라스·신데렐라 스나이프)은 기존 관례 유지** —
      다른 무기가 장전된 채 오는 게 맞다.
- [ ] **To-Do: 스노우화이트 잔여 +0.539B (1.320x) — 여전히 절대오차 1위.**
      **민감도(각 항목을 0으로):** 버스트3단계 ATK +73.92% → **1.039x** ·
      강화장탄 15→5 → **1.069x** · 풀차지 ATK +46.84% → 1.153x ·
      버스트 공격력 +84.48% → 1.194x · 순차 +158.4% → 1.211x · 차지 +528% → 1.283x.
      뒤 네 개는 사격장 실측이고 장탄은 인게임 카운트라 **용의선상이 좁다.**
      그녀 데미지의 **46.5%가 Fully Active 14발**에서 나오므로 그 블록에 관한 것이면
      무엇이든 크게 움직인다.
      **★ 사격장 2판이 이 표의 1위를 죽였다 (Fienn, 2026-07-28).** 둘 다 "버스트 전 평타
      vs 첫 풀버스트 창 안 평타"(논크리·논코어) 비다 — 버스트에 붙는 버프 스택 전체가
      비 하나로 나온다. ① 목단(애장품)+크라운+**라피(B3)**+그녀: 실측 3.18397 vs 엔진
      3.35587(**5.4% 과대**). ② 라피(B1)+크라운+**그녀(B3)**: 실측 17.5775 vs 엔진
      18.7239(**6.5% 과대**). **두 비를 나누면 그녀 자기 버스트 킷만 남고 그 값이 1.011 —
      자기 킷은 1% 과대에 불과하다.** 5.4%는 두 덱이 공유하는 아군(크라운·라피·목단) 몫.
      그리고 버스트3단계 ATK +73.92%를 빼면 엔진이 **2.42127**로 실측보다 **24% 낮아진다** —
      그 버프는 실재하고 크기도 대체로 맞다.
      **★ 덱4 자체도 측정됐다 (Fienn, 2026-07-28) — 덱4 버프도 무죄.** 그녀가 실제로
      쓰는 로테이션(볼륨+프리카+스노우 → 볼륨+민트+신데렐라 → 볼륨+민트+스노우)은
      **엔진이 스스로 고르는 순서와 정확히 같고**, 풀버스트 14회도 실측과 일치한다.
      버스트 전 기준선 1,803,987 대비: 자기 버스트 Fully Active 19,490,867(비 10.8043,
      엔진 11.1754 = **3.4% 과대**) · 아군 버스트 기본 평타 7,868,058(비 4.3615,
      엔진 4.5641 = **4.7% 과대**).
      **⇒ 잔여는 전부 발수다.** Fully Active 블록을 측정된 3.4%로 보정하면 14발 1.083B →
      1.047B, 기록에서 빼면 기본 블록에 **0.636B**가 남는데 엔진은 96발에 1.138B를 준다 —
      기본 블록이 엔진의 **0.558배**, 즉 96발이 아니라 **약 51발**이어야 한다.
      180초 중 사격 가동률 **약 62%**인 셈이고, 엔진은 연속 사격을 가정한다.
      **★ 그리고 그 타수가 측정됐다 (Fienn, 180초 사격장, 2026-07-28): 86타
      (Fully Active 14 + 기본 70).** Fully Active 14는 **정확히 일치**하고 기본만
      엔진이 96 → **37% 과대**. 이것만 고쳐도 **1.320x → 1.137x**, 발당 과대 4%까지
      빼면 **1.088x** — 두 측정 층이 그녀의 잔여를 전부 설명한다.
      **정체는 발당 회복 시간이다.** 그녀의 차지는 「고정」이라 차지속도가 아니다.
      86타를 시간으로 환산하면 차지 128.8초 + 재장전 7.1초 = 135.9초뿐이고
      **44.1초가 남는다(발당 0.526초)**. 엔진은 **차지 시간만** 발당 간격으로 쓴다.
      **교차검증:** `CHARGE_INTERVAL_FLOOR = 10/29 = 0.345초`는 신데렐라가 차지를 0으로
      만든 상태의 측정값이다 — **차지가 사라졌을 때 남는 것**, 곧 회복 시간이다.
      `interval = charge + recovery`로 보면 그 바닥은 특수 케이스가 아니게 된다.
      그녀에게 크게 나타나는 이유는 **오토파이어 볼리(5발/15발)가 재생되는 동안 다음
      차지를 못 시작하기** 때문일 가능성이 크다.
- [x] **차지 모션 딜레이 배선 완료 — ±15% 이내 13/25 → 14/25 (2026-07-28).**
      **유닛별이지 무기군 상수가 아니다**(Fienn): 리베랄리오도 SR인데 차지샷을 딜레이
      없이 연달아 쏜다. 일괄 적용은 실측이 기각한다 — 스칼렛 0.981→0.559 ·
      신데렐라 0.971→0.654. **보유 유닛 5명**(스노우화이트:헤비암즈 · 에이드:에이전트버니 ·
      헬름 · 브래디 · 벨벳)만 `registry._CHARGE_MOTION_DELAY`에 등록.
      값 **0.4초**는 스노우화이트에서만 시계로 쟀고 나머지는 "있다"는 관측에 근거한다.
      **효과:** 에이드 1.970→**1.451** · 헬름(애장품) 1.699→**1.243** ·
      스노우화이트 1.320→**1.151** · 벨벳 1.213→1.074. 리베랄리오·스칼렛·아니스 불변.
      과대 합계 +2.377B → **+1.895B**, 백엔드 1490 passed.
      **부수 정정: 오버로드에 「재장전 속도」는 없다**(공격력·우월코드대미지·차지대미지·
      차지속도·최대장탄수·크리티컬대미지·크리티컬확률 7종뿐). 콘솔 cp949로 깨진 한글을
      제가 잘못 읽어 그녀의 재장전을 2.0초 대신 1.008초로 계산했었다 — 엔진은 정상.
- [x] **실제 편성 순서로 채점 — ±15% 이내 14/25 → 16/25 (2026-07-28).**
      캘리브레이션은 그동안 **가능한 순서 중 총딜 최대**를 골라 채점했는데, 순서별
      진폭이 유닛 단위로 컸다(덱4 민트 1.015–1.502 · 프리카 0.764–1.353, 덱5 아크
      0.562–1.183, 덱3 레이 0.309–0.936). 과대 유닛 대부분이 자기 범위의 **최상단**에
      앉아 있었으니 argmax 자체가 편향이었다. Fienn이 덱3/4/5의 좌석 순서를 줬고
      (`raid_record.RECORD_ROTATIONS`), 이제 그 순서로만 채점한다. 덱1·2는 순서
      미기록이라 argmax 유지(진폭이 0.918–0.977 · 1.013–1.019로 좁다).
      **→ 2026-07-29에 덱1·2도 받아 argmax는 전부 사라졌다. 아래 항목 참고.**
      **효과:** 합계 1.030x → **1.025x**, 과대 +1.895B → **+1.672B**,
      아크레인저 1.183→**1.113** · 스노우화이트 1.151→**1.110** · 아스카 1.066→1.046 ·
      레이 0.923→0.936. 덱3 1.027 · 덱4 1.077 · 덱5 1.121.
      **함께 확인된 것:** 헬름·미하라의 **버스트 미사용(토템)**과 프리카의 **1회만**은
      기록된 좌석 순서에서 엔진이 **이미 그대로 굴리고 있었다** — 스케줄러가 셋째 B3를
      쓸 일이 없었기 때문. 그래도 `max_bursts`(버스트 사이클 신규 필드)로 못 박았다:
      우연히 맞는 것과 데이터로 맞는 것은 다르고, 쿨감이 조금만 바뀌어도 조용히 어긋난다.
- [x] **네온의 화력게이지를 3버스트 주기로 정정 — 1.306x → 1.013x (2026-07-28).**
      **Super Firepower는 자기 1·4·7번째 버스트에만 켜진다**(Fienn 인게임). 게이지 100으로
      전투를 시작해 첫 버스트가 100을 **전부 소모**하고, 재충전(평타당 +2 · Firepower
      Charge 종료시 +45)이 100에 닿는 데 두 버스트가 더 걸린다. 인코딩은 "쿨다운 안에
      충분히 리필된다"고 보고 **매 사이클 정상상태**로 근사해, 게이지100 보너스 3종을
      **세 배로** 지급하고 있었다.
      **교훈: 자원이 실제로 얼마에 도달하는지를 물어라** — 리필 항목이 넉넉해 보이는 것과
      두 버스트 사이에 100을 채우는 것은 다르다. 합산을 안 해보고 "far inside the cooldown"
      이라고 적어둔 것이 3주를 갔다.
      **게이팅 3곳:** 버스트의 자AD +45.03% · 풀버스트 진입의 추가 자ATK +35.05%(그녀는 B3라
      자기 버스트와 자기가 연 풀버스트가 같은 순간이고, 버스트 간격이 10초 상태창보다
      넓어 **자격 버스트에 붙이는 것과 동치**) · 창 내 폭발 보너스 +262.79%.
      기본분(자ATK +80.04%는 **모든** 풀버스트, 자AD +110.21%는 매 버스트, 폭발 437.98%는
      매 발)은 그대로다.
      **엔진 확장:** `every_during_own_status_window`의 threshold에 **선택적 버스트 주기**
      3번째 원소를 받아 `own_burst_times[::period]`로 창을 연다(기존 소비자 전부 불변).
      **효과:** ±15% 이내 16/25 → **17/25**, 합계 1.025x → **1.015x**,
      과대 +1.672B → **+1.311B**, 덱5 1.121 → **1.039**.
- [x] **아니스의 슈팅스타는 소환체의 사격이다 — 0.739x → 0.946x (2026-07-28).**
      Fienn의 사격장 영상(3인 덱, 풀버스트 창 안, 논크리)이 두 값을 줬다:
      코어히트 **별 틱 1,786,809** vs 코어히트 **평타 7,492,265** → 비 4.193098.
      맨계수 비 (61.3%×273.675%)/40.01% = **4.193021**로 **0.0018% 일치** →
      **모든 수정자가 약분** → 틱은 평타와 완전히 같은 상태에 있다.
      즉 틱은 **코어 히트도 받고 투사체폭발 버킷도 받는다.** 엔진은 둘 다 안 주고 있었다.
      **기여 분해:** 코어만 0.823x · 타이핑만 0.818x · **둘 다 0.946x**.
      **엔진 확장:** `scheduled_nukes` 스펙에 **인스턴스 단위 `core_eligible` opt-in**.
      "스케줄 틱은 코어를 못 받는다"는 포괄 규칙은 **방출 경로**를 기준으로 삼은 것이고,
      게임이 보는 것은 다르다 — **소환체의 사격은 평타다, 소유자의 평타가 아닐 뿐.**
      **★ 왜 여러 번의 감사가 못 잡았나:** 소스 대 소스 비는 **시뮬이 자기 가정과
      일관되는지**만 검증한다. 실제로 이전 감사는 차이를 관찰해놓고("별 틱 vs 평타 =
      코어 1.5388 × PE 1.4994") 그것을 정당한 것으로 **기록**했다. 솔로 사격장도 못
      본다 — 솔로는 FB에 안 들어가 Stardust의 PE 버프가 없어 비교할 인자가 없다.
      또 하나: 버스트의 「폭발 범위 +100%」를 inert로 치웠는데, **폭발하지 않는 것에
      폭발 범위를 붙이지 않는다** — 미모델 목록이 분류의 증거였다.
      **효과:** 덱1 0.977 → **1.000x**, ±15% 이내 17/25 → **18/25**,
      미달 −0.789B → **−0.505B**. 백엔드 1508 passed.
- [x] **Pierce Damage Up이 스킬 딜에 새고 있었다 — 스노우화이트 1.110x → 0.999x (2026-07-28).**
      `pierce_damage_up`이 `has_pierce > 0`만 보고 **그 유닛의 모든 인스턴스**에 붙었다.
      Pierce는 "관통하는 **평타**"라 **유닛 속성이자 인스턴스 종류**이고, 관통 유닛이 쏘는
      **스킬 넉은 관통 데미지가 아니다.** 이제 `is_normal_attack`까지 함께 요구한다.
      **실측이 소수점까지 지목:** 첫 버스트 FB 창, 오토파이어 15발 중 1발 6,286,230 vs
      같은 발의 41.9% 스윕 1,342,112 → 비 4.68383. 맨계수 비 2.52005이므로 초과분
      1.85863 = `(1+A+순차1.584)/(1+A)` → **A = 0.8448**인데, 엔진의 `attack_damage_up`이
      **정확히 0.8448**이고 버킷 총합만 1.9757이었다 — 차이 **0.1309 = 그녀의
      `pierce_damage_up`**. 크리/논크리 쌍(9,066,420/6,286,230)은 major 버킷을
      **1.500000**(풀버스트만·코어 없음·사거리 없음)으로 확정해 엔진과 일치했고,
      볼륨 1티어 크리대미지 7.74%도 함께 재확인됐다.
      **낡은 테스트가 버그를 고정하고 있었다** — `test_pierce_needs_the_property.py`가
      게이트를 **버스트 데미지**로 재느라 "스킬 딜도 받는다"를 조용히 단언하고 있었다.
      평타 기준으로 다시 쓰고 "스킬 넉은 못 받는다"를 별도 테스트로 추가.
      **효과:** 덱4 1.077 → **1.033**, 합계 1.023 → **1.018**, 과대 +1.311B → **+1.126B**.
      함께 확인: 발수 85 vs 실측 86 · Fully Active 창 안 **14 vs 14**로 발사 타임라인은
      이미 정확했다. 버스트 2번불릿(파괴가능 발사체 대상 41.9%)은 보스에 안 터지는데
      애초에 인코딩돼 있지 않아 무관.
- [x] **민트·프리카 차지 모션 딜레이 실측 배선 — ±15% 이내 18/25 → 20/25 (2026-07-28).**
      민트 **0.39초** · 프리카 **0.34초**(스노우화이트 0.4초와 나란히). 값이 유닛마다
      달라 레지스트리가 "상수 하나 + 명단"에서 **슬러그→초 매핑**이 됐다.
      **측정법이 핵심이다** — 대미지 표기 간격이 아니라 **차지게이지가 차오르기 시작하는
      시점**을 읽는다(RL 유탄의 비행시간이 거리에 따라 표기 간격을 흔들기 때문).
      발간 간격이 `차지 + 딜레이`로 떨어져 **모델까지 함께 검증**됐다(민트 1.40 = 1.0+0.39).
      **효과:** 민트 1.502→**1.107** · 프리카 1.353→**1.087**, 덱4 1.033→**1.004x**,
      과대 합계 1.126B → **1.005B**.
- [x] **헬름·브래디·벨벳 차지 딜레이 실측 — 빌려 쓴 0.40이 맞았다 (2026-07-29).**
      추정으로 남아 있던 마지막 5슬러그를 Fienn이 시계로 쟀다(차지 완료 ↔ 다음 차지
      시작): 헬름 0.39/0.40/0.39/0.40/0.40 · 브래디 0.40 x4 · 벨벳 0.40/0.40/0.40/0.39/0.40.
      **수치는 안 움직인다**(합계 1.011x·21/25 그대로) — 바뀐 것은 **가정이 사실이 된 것**이고,
      감사가 이제 **실측 12 · 추정 0 · 없음확인 4 · 미검증 16**을 보고한다.
      **덤으로 모델이 세 번째로 검증됐다:** 발간 간격 1.380/1.343/1.393에서 딜레이를 빼면
      실측 차지 0.987/0.943/0.997로 **0.003초 안에서** 돌아온다.
      **★ 그래서 헬름(애장품) 1.243x는 딜레이가 아니다** — 가장 값싼 가설이 닫혔고,
      그녀는 이제 에이드와 같은 **"발수도 발당도 맞는데 총합이 안 맞는"** 자리에 있다.
      (브래디의 실측 차지 0.943이 기본 1.0보다 6% 빨랐던 것은 **아래 2026-07-30 항목에서
      설명된다** — 그녀의 차지속도 오버로드 6.09%가 3프레임을 사서 차지가 0.95초다.)

- [x] **브래디 차지 실측 — 차지속도가 프레임 격자에 앉는 것을 확정, 0.01초 반올림 기각 (2026-07-30).**
      커뮤니티 두 글이 주장하는 「차속 0.01초 단위 반올림」을 판정했다. 흑련은 두 차속
      값이 **서로 다른 계정**에 있어 구조적으로 못 갈랐는데(계정 축 미해결 0.19프레임 대
      필요 신호 0.6프레임), 브래디는 차지 **1.00초**라 갈림이 3배 크고 차지 게이지를
      직접 읽어 **한 계정 안에서 끝난다**. 원본 6시퀀스는 `docs/measurements/bready-charge.md`.
      **서로 다른 전제의 두 논거가 같은 답:** ① 간격 실측 78.9696 ± 0.0319프레임이
      프레임 격자의 79.0f와 **1.0σ**, 0.01초 규칙의 78.4/79.4f와 17.9/**13.5σ**.
      ② 차지 판독 51회에서 56·57로 읽힌 41회 중 57이 34회(83%)인데 0.01초 규칙 예측은
      40% → **5.61σ**. 앨리스 컷도 독립적으로 같은 말을 한다.
      **6.09%는 3프레임만 사고 1.09%p는 버려진다** — 엔진 동작은 안 바뀌고 확정만 된다.
      **덤:** 브래디 딜레이가 **22프레임(0.36667초)** 으로 재측정됐다 — 0.4는 FB 시계
      (0.01초 표시에 0.04초 점프)로 읽어 22와 24를 못 가르던 값이다. 그녀는 실기록 덱에
      없어 **캘리브레이션 출력이 바이트 단위 동일**. 백엔드 1609 → **1611 passed / 3 skipped**.
      **미판정으로 남은 것:** 정수 % 반올림(브래디에서 프레임 격자와 같은 답을 낸다) ·
      같은 값 줄 그룹 합산(줄이 하나뿐인 측정) · `int()` 음수 절단 비대칭.

- [x] **프리카 차지 실측 — 정수 % 반올림 확정, 오버로드 굴림을 실어 나르도록 배선 (2026-07-30).**
      브래디가 못 가른 축을 **차지 1.00초 × 차속 4.92% 한 줄**이 갈랐다(생합계 2프레임 대
      정수 % 3프레임). 차지 판독 31회 **57.0000 ± 0.1606프레임** — 생합계의 58과 **6.22σ**,
      정수 %의 57과 **0.00σ**. 딜레이도 22.14 ± 0.19로 정수 %의 22에 0.75σ, 생합계의 21에
      6.0σ. 원본은 `docs/measurements/prika-charge.md`.
      **데이터 모델이 함께 움직였다** — 규칙이 굴림별이라 합계로는 적용이 안 된다
      (`2.28+4.92`와 `2.57+4.63`이 둘 다 7.20%인데 7%와 8%를 낸다). 굴림은 이미
      `GetUserCharacterDetails`의 `{slot}_equip_option{1,2,3}_id`에 있었고 `overload_decode`가
      해독까지 했는데 `assemble_overload`가 표시용으로 합산하며 버리고 있었다. 이제
      `OverloadOption.lines`로 슬롯 태그와 함께 온다. **UI는 그대로**(합계 7줄 표시).
      **효과:** 캘리 합계 1.0109 → **1.0110x**, ±15% 이내 **21/25 유지**. 움직인 건 셋뿐 —
      앵커 1.016 → **1.039x** · 프리카 1.087 → 1.095 · 에이드 1.498 → 1.528(caveat).
      **근거는 실측 일치이지 비율 개선이 아니다.**
      백엔드 1611 → **1621 passed/3 skipped** · 프론트 423 → **425 passed**.
      **★ Fienn의 로스터는 굴림 없이 동기화된 스냅샷이라 재동기화가 필요하다.**
      신설: `scripts/find_charge_rule_discriminators.py`(어느 유닛이 규칙을 판정하는지 로스터에서 탐색).
      **미판정:** 그룹 합산(두 글이 공통 주장이라 채택했으나 갈라놓는 조합이 로스터에 없다) ·
      `int()` 음수 절단 비대칭.

- [x] **에이드 0.35초 · 앵커 0.4초 실측 배선 + 차지 딜레이 전수 감사 (2026-07-28).**
      **앵커 1.406x → 1.016x**(딜레이가 아예 없던 상태였다). 에이드는 빌려 쓰던 0.4가
      실측 0.35로 바뀌어 1.451 → **1.498x**로 오히려 올랐다 — 그녀의 잔차는 발수가
      아니라는 뜻이고, 발당은 이미 소장품 정정으로 0.002% 안에서 맞은 상태다.
      **`scripts/audit_charge_motion_delay.py` 신설** — 인코딩된 차지 무기 32기 중
      **실측 5 · 추정 5 · 없음 확인 3 · 미검증 19**. 엔진 기본값이 "딜레이 없음"이라
      **미검증은 조용한 과대평가**이므로, "0"과 "아무도 안 봤음"을 구분하려고
      `NO_CHARGE_MOTION_DELAY`(확인했고 없음)를 별도로 둔다.
      **인코딩 절차에 SR/RL 필수 질문 추가**(SKILL.md 4단계).
      **효과:** ±15% 이내 20/25 → **21/25**, 합계 1.014 → **1.011x**.
- [x] **덱1·덱2 좌석 순서 확보 — argmax 채점이 완전히 사라졌다 (2026-07-29).**
      Fienn이 두 덱 모두 **[1]번 순서**라고 확인했다:
      덱1 `아니스:스타 → 앵커 → 마스트 → 리베랄리오 → 홍련`,
      덱2 `리틀머메이드 → 나유타 → 벨벳 → 신데렐라(MG) → 프리바티(애장품)`.
      둘 다 버스트를 전부 소모(`max_bursts` 비어 있음).
      **수치는 안 움직인다**(합계 1.011x·21/25, 덱1 0.990 · 덱2 1.019 그대로) —
      실제 순서가 곧 argmax였기 때문이다. 덱3/4/5에서는 argmax가 편향이라 실제
      순서로 바꾸자 수치가 내려갔는데, 여기선 우연히 일치했다.
      **그래도 기록할 값어치가 있다** — 덱1의 순서별 진폭 0.932~0.990은 전적으로
      홍련이 만들고(Fienn이 안 쓴 두 순서에서 0.86x), "우연히 맞는 것"과 "실제로
      그렇게 썼다"는 물어보기 전까진 다른 주장이었다.
      `--orderings` 플래그 신설 — 순서 후보를 유닛별 비와 함께 뽑아, 어떤 유닛을
      재현하느냐로 순서를 역추정할 수 있게 한다.
- [x] **에이드 캐비엇 — 그녀의 기록은 인코딩이 아니라 기록을 측정한다 (2026-07-29).**
      Fienn이 레이드 녹화를 다시 보니 **끊어쏘기(톡톡이)**를 했다 — 엔진이 시뮬하는
      풀차지 로테이션과 애초에 다른 운용이다. 차지 딜레이(0.35)와 발당 대미지는
      이미 실측으로 맞다고 확인된 상태였고, **그래서 잔차가 갈 곳이 없었던 것**이다.
      `raid_record.RECORD_CAVEATS`에 아크레인저(브래킷이라 점추정 아님)와 함께
      이유째로 박고, "worst by ratio"와 절대오차 목록에서 뺀다 — 안 그러면 배수
      1위로 떠서 **매 세션 재조사**된다. 과대/미달 합계는 이 둘이 빠져 이전 수치와
      비교 불가이므로 `(chaseable only)`로 표시.
      **이제 실제 최상위는 볼륨 1.24x · 헬름(애장품) 1.24x · 크라운 1.18x다.**
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
- [x] **재동기화 완료 — 소장품이 캘리브레이션에 실제로 들어왔다 (2026-07-27).**
      합계 **0.914x → 0.936x**. 같은 로스터로 소장품만 껐다 켠 A/B라 변화분은 전부
      소장품이다(소장품을 끈 새 로스터가 예전 로스터 수치를 유닛별 ±0.001로 재현).
      덱별 0.842→**0.867** · 0.839→**0.851** · 0.967→**0.990** · 1.082→**1.111** ·
      1.017→**1.040**. 로스터는 착용 109 / 미착용 50, 애장품 11(플로라가 R→SSR).
      **±15% 이내는 12/25 → 11/25로 줄었다.** 회귀가 아니라 방향의 문제다 — 소장품은
      전 유닛을 위로 밀기 때문에 미달 유닛(아니스:스타 0.595→0.627, 리베랄리오
      0.802→0.837, 목단 0.830→**0.879**로 진입)은 좋아지고 **과대 유닛은 더 나빠진다**
      (에이드 1.537→**1.629**, 헬름 1.436→**1.516**, 민트 1.186→1.289, 프리카
      1.070→1.160·앵커 1.081→1.174는 1.15를 넘어 이탈). 몇 유닛이 미세하게 내려간
      것(마스트 −0.6%, 미하라 −1.6%)은 덱1·덱2에서 최적 순서가 바뀐 결과다.
      **에이드가 가장 큰 시사점이다** — 소장품의 존재를 증명한 것이 그녀의 사격장
      실측인데, 그 항이 맞다면 그녀의 180초 레이드 과대(1.63x)는 **다른 원인**이고
      소장품은 그 위에 정직하게 얹혔을 뿐이다. 다음 조사 대상.
      **★ 재동기화는 두 단계다 — 앱에서 동기화해도 측정 스크립트는 못 본다.**
      동기화는 브라우저 localStorage까지만 가고, 스크립트가 읽는
      `tools/collect-blablalink/roster-drafts.json`은 거기서 **손으로 반출**해야 한다
      (콘솔 스니펫은 `tools/collect-blablalink/RECIPE.md`). 이 단계를 빠뜨리면 모든
      수치가 예전 스냅샷 그대로라 **"효과가 없다"와 구별이 안 된다** — 실제로 한 번
      물렸다. 반출 후 `python3 scripts/audit_collectible_coverage.py`가 첫 줄에
      어느 로스터를 읽었는지 출력한다.
- [x] **소장품 레벨 0의 의미 확정 — 엔진은 이미 맞게 하고 있었다 (2026-07-27).**
      Fienn이 레벨 0 보유 유닛을 인게임에서 전수 확인: **스킬은 레벨 0부터 나오고**
      값도 엔진이 내던 것과 정확히 같다(헬름: 아쿠아마린 코어 +10.22% · 볼륨·리터
      평타 배율 4.73% · D: 킬러 와이프 차지 4.74% · R등급 코어 +5.67% / 장탄 +1.56%).
      **스탯(ATK/HP)만 레벨 1부터** 붙는데 이건 실측이 결정적이다 — 레벨 0에 커브
      index 0을 주면 159 측정 유닛 중 **정확히 31기**(레벨 0 착용자 전원)가 그
      값만큼 어긋난다(SR 3,029 · R 638). 자기모순이 아니라 **축이 두 개**였고,
      미착용/0단계착용은 **`favorite_item_tid`로 완전히 구분된다**(빈 슬롯 = tid 0,
      실계정 50유닛). 두 반쪽을 한 테스트로 묶었다 —
      `test_level_zero_is_equipped_and_pays_both_its_skill_and_its_stat`.
      코드 변경 없음(주석의 잘못된 근거만 정정). 백엔드 **1487 passed / 3 skipped**.
- [ ] **⚠ 폐기: 이전 캘리브레이션 표 — 잘못된 보스에서 측정됐다.** 아래 덱별/유닛별
      숫자는 Electric 약점 보스 기준이라 **못 쓴다**(특히 Electric·Wind 유닛).
      사격장 단발 측정들은 표적이 "우월코드 미적용"이라 **영향 없다**.
      덱별: 덱1 **0.84** · 덱2 **0.86** · 덱3 **0.98** · 덱4 **0.80** · 덱5 **1.01**
      유닛별 (절대 오차 큰 순): 신데렐라 **0.61** · 미하라 0.70 · 리틀머메이드 0.76 ·
      라피 0.79 · liberalio 0.80 · 목단 0.84 · 레이 0.85 · 나유타 0.85 ·
      신데렐라MG 0.89 · **홍련 0.90** · 볼륨 0.93 · 크라운 0.96 ·
      스노우화이트 0.97 · 프리바티 0.97 · 프리카 0.98 · 벨벳 0.99 · 민트 1.00 ·
      아스카 1.07 · 아크레인저 1.08 · 네온 1.18 · **헬름 1.46** · **에이드 1.57**
      정확한 유닛 8기가 ±0.03 안에 들어왔다(민트·벨벳·프리카·프리바티·스노우화이트·
      크라운·볼륨·홍련). 남은 큰 편차는 **미달 쪽에 몰려 있다**.
- [ ] **잔여 편차 0.98~1.18x는 여전히 안 갈렸다.** Liberalio는 아직 −12%, 홍련은 +12%다.
      섞여 있는 갈래: (a) 실기록이 **여러 번 시도한 최고 기록**이라 시뮬(이상화된 1회)이
      낮게 나올 여지가 있다, (b) "실제 플레이가 코어를 얼마나 자주 맞히는가"는 여전히
      미모델(적격 히트는 항상 맞힌 것으로 계산) — 이쪽은 시뮬을 **높이는** 방향.
      두 힘이 반대 방향이라 총합만으로는 못 가른다. **최근 시즌 유닛별 기록**이 있으면
      가장 빠르다.
- [ ] **부위파괴 이벤트 갭은 후순위로 확인됐다 (2026-07-26 실측).** 실기록 5덱을
      floor/ceiling 양쪽으로 재보니 차이가 **덱5만 6.6%, 합계 0.9%**다. 마지막 남은
      엔진 갭이지만 ROI가 낮다.
- [ ] **대조 픽스처에 무기 모드를 못박아야 한다.** 덱2의 1.35x는 모델 오차가 아니라
      엔진이 신데렐라:크리스탈 웨이브의 **더 좋은 모드를 고른** 결과였다
      (`-mg` 10.29B/1.35x vs `-snipe` 9.02B/1.18x). Fienn이 실제로 쓴 모드를 확인해
      고정하지 않으면 시뮬이 자기가 고른 모드로 채점받는다.
- [x] **덱 데미지 내역이 총합의 22~72%만 설명하던 문제 — 완료 (2026-07-26).**
      백엔드에 `skill_damage`(시뮬레이터의 여덟 소스 중 burst·normal_attack이 아닌
      여섯 개의 합)를 추가해 **세 값의 합 = `total_damage`** 를 계약으로 고정했다.
      `_summarize`가 소스별 합산 후 남은 것을 모으므로 새 소스가 생겨도 자동으로 들어간다.
      실측(실제 로스터·철갑·DEF 31,784): 설명 비율 **37/38/50/86/39% → 전부 100.0%**.
      드러난 사실 — **대부분의 덱에서 화면에 없던 항목이 최대 딜 소스였다**
      (덱1 스킬 7.65B vs 평타 4.43B vs 버스트 0.10B).
      **덱 카드는 그 셋을 그리지 않고 총합만 보여준다**(Fienn 지정, 2026-07-26) —
      소스별 분해는 시뮬레이터를 의심할 때 필요한 것이지 덱을 고를 때 필요한 게 아니다.
      합=총합은 엔진 불변식으로 남아 새는 소스를 잡는다. `"Burst: 0"`이 고장처럼
      읽히던 문제도 그 줄이 사라져 함께 없어졌다. 백엔드 1413 → **1415 passed /
      3 skipped**, 프론트 **289 passed**. `docs/decisions.md` 참고.
      **남은 것**: 유닛별 기여도(누가 딜하는가)는 별개 기능으로 미착수.
- [x] **보스 설정 위치 — 완료 (2026-07-26).** 폼 맨 끝에 있던 Boss profile을
      **mode 섹션 왼쪽**으로 옮겨 2컬럼 행으로 묶었다(Fienn 지정). 제출 버튼이 그 행 안에
      있으므로 실행에 필요한 모든 것이 한 줄에 모인다 — **버튼↔보스 거리 2040px → 159px**,
      사이에 팔레트 없음. 900px 이하에서는 세로로 접힌다(가로 스크롤 없음 확인).
      좁아진 컬럼에서 체크박스 힌트가 라벨과 폭을 다퉈 "Part-destruction gimmick"이 3줄로
      쪼개지던 것도 같이 고쳤다(힌트를 아랫줄로).
      **남은 것**: Element 기본값 "Non-elemental"은 그대로다(저장된 입력·결과 캐시 해시와
      얽혀 범위가 커져 분리). 완료 후 결과로 스크롤 이동도 미착수.
- [ ] **UI 크롬 한글화 스펙 리뷰 중 나온 백로그 1건 (2026-07-26, 아직 미설계 — 범위 밖,
      캡처만).** `docs/superpowers/specs/2026-07-26-ui-chrome-korean-localization-design.md`
      리뷰 중 Fienn이 별도 세션감으로 떠올린 것:
      - Roster/Recommend/Sync를 사이드바 탭으로 재구성 — 지금은 `App.tsx`에 "Roster"·
        "Recommend" 탭 2개뿐이고 Sync 패널은 Roster 탭 안에 얹혀 있다. 이건 네비게이션/
        레이아웃 구조 변경.
- [x] **니케 검색·정렬·필터 + 로스터 탭 버스트 분류 — 완료 (2026-07-28).** 두 화면이
      `lib/unitFilter.ts`의 순수 규칙 하나를 공유한다(데이터 모양이 달라 `UnitFacets`
      접근자를 받는 제네릭). 이름 부분일치 검색 · 속성/버스트 다중 필터 · 이름 또는
      오버로드 7종 중 하나로 양방향 정렬. 로스터 탭에 B1/B2/B3 분류를 신설했고, 정렬은
      그룹 **안에서만** 일어난다. 핵심 불변식은 **필터가 시야만 바꾼다**는 것 —
      추천 탭에서 숨겨진 유닛도 탐색 풀에 그대로 있고, 요청 payload·풀 개수·개별 제외
      상태가 필터에 안 흔들린다는 것을 회귀 테스트 3개로 고정했다. 작열 속성색도
      `#f0603c` → `#dd3333`(Fienn 지정)으로 바꿔 철갑 금색과 안 헷갈리게 했다.
      최종 리뷰가 잡은 것: **주석 4곳이 "예전엔 이랬다"를 서술**하고 있었다(플랜 문구
      탓). 보스 속성 `<select>`와 필터 툴바의 속성 칩 그룹이 **접근성 이름 "속성"을
      공유**해서 보스 쪽을 `보스 속성`으로 개명(Fienn 판단). 회귀 테스트 하나가
      "필터가 실제로 듣는지"를 안 봐서 무효화돼도 통과할 수 있었다.
      실화면 검증(159기 실제 로스터): 툴바 **75px**로 레이아웃 여유 충분, 작열
      `rgb(221,51,51)` 확인, 필터를 걸어도 풀 개수 **73/73 불변**·제외 상태 보존,
      한글 입력·오버로드 정렬·미지원 목록 불변 전부 정상, 콘솔 무에러.
      프론트 **301 → 350 passed**. 스펙:
      `docs/superpowers/specs/2026-07-28-roster-search-filter-design.md`.
- [x] **동기화 도움말 패널 — 완료 (2026-07-27).** 제목 옆 "동기화 방법" 토글이 공유
      URL 획득(스크린샷 2장)부터 북마크 설치·재싱크·다계정 운용까지를 인라인으로
      펼친다. 활성 프로필이 없는 화면에서는 기본 펼침, 로스터 탭에서는 접힘. 최종
      리뷰가 잡은 것: 도움말이 "로그인한 상태"라고 했지만 북마크릿의 실제 관문은
      **출처(origin)** 검사라 우리 탭에서 눌러도 조건을 만족한 것처럼 보였다 —
      문구를 "blablalink 페이지를 열고"로 정정. 프론트 **294 → 299 passed**. 스펙:
      `docs/superpowers/specs/2026-07-26-sync-help-panel-design.md`.
- [x] **RapiLab 개칭 + 실행 버튼 상시 노출 — 완료 (2026-07-29).** 앱 이름을 RapiLab으로
      바꾸고 탭을 `니케 풀`/`솔로 레이드`/`유니온 레이드`로, 솔로 레이드의 네 모드를
      `단일 덱`/`전부 최적화`/`빈자리만 최적화`/`기대 딜량 계산`으로 개칭했다(내부
      `RecommendMode`/`Tab` 유니언 값은 localStorage에 저장되므로 그대로 유지). 모든
      제출 버튼의 유휴 라벨을 `인카운터!`로 통일하고, 실행 버튼이 스크롤 위치와
      무관하게 항상 화면에 남도록 했다 — 덱 컬럼이 없는 모드는 화면 하단에 고정,
      덱 컬럼이 있는 모드는 sticky 컬럼에 얹었다. 전 브랜치 리뷰가 잡은 잔여 항목:
      진행 중 라벨(`배분 중…` 등)이 진행 배너와 다른 옛 어휘를 쓰던 것, 네트워크
      실패 메시지가 폐기된 모드명(`레이드 덱 배분`)을 그대로 쓰던 것, `빈자리만
      최적화` 모드의 섹션 제목이 여전히 `드래프트`였던 것을 통일했다. 그리고 5덱
      찬 sticky 덱 컬럼(~760px)이 768px 뷰포트에서는 버튼을 화면 밖으로 미는
      것을 실측으로 확인해, 컬럼을 뷰포트 높이로 캡(`max-height:
      calc(100svh - var(--sp-4) * 2)`)하고 그 안에서 덱 목록만 스크롤하며 실행
      버튼은 컬럼 하단에 고정되게 했다. 프론트 **393 passed** (44 files) 그대로.

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
