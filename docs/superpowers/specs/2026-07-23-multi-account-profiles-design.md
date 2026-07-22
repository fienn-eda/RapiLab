# 다계정 프로필(Multi-Account Profiles) 설계

**Goal:** 한 유저가 여러 NIKKE 계정을 절대 섞이지 않게 각각 보관하고, 각 계정의
추천 결과를 브라우저를 껐다 켜도 재활용해 매번 재실행하지 않도록 한다.

**Architecture:** 전적으로 클라이언트(브라우저 localStorage) 모델 — 서버 DB·인증
없음. 계정은 blablalink `open_id`로 식별하고, 계정 고유 데이터(로스터·추천 결과·
마지막 입력)는 프로필 안에 격리한다. 서로 다른 `open_id`는 구조적으로 병합 불가.

**전제(선행 결정):** 로스터 소스를 blablalink sync 하나로 확정하고 ExiaInvasion
파일 import·수동 입력 폼은 코드/UI까지 제거한다(`docs/decisions.md` 2026-07-23
"로스터 소스를 blablalink sync 하나로 확정"). 이후 모든 로스터는 `open_id`를 보유
하므로 프로필을 `open_id`로만 식별할 수 있다.

---

## Non-goals

- **크로스 기기/브라우저 동기화 아님.** localStorage는 origin·브라우저 로컬이라
  같은 유저가 폰과 노트북에서 열면 각각 별개다(기기마다 1회 재계산). 계정 단위
  서버 공유는 서버+인증이 필요한 별도 프로젝트로, 이번 범위 밖.
- **서버 측 연산 캐시 아님.** `recommend_from_draft`의 SimPool 공유/메모이제이션
  (L2/L3)은 `docs/roadmap.md`의 성능 백로그 별도 트랙. 이 스펙은 **클라이언트
  결과 영속**만 다룬다(둘은 상호보완).
- **수동 프로필 명명 아님.** 라벨은 blablalink 닉네임 자동 캡처(아래)로 채운다.

---

## 데이터 모델 (localStorage)

단일 `nikke-roster` 키를 프로필 키잉 저장소로 교체한다. 새 키 `nikke-profiles`:

```jsonc
{
  "activeOpenId": "78550796" | null,
  "profiles": {
    "<openId>": {
      "openId": "78550796",
      "nickname": "본계",              // blablalink 닉네임 (매 sync 갱신)
      "roster": NikkeDraft[],          // 기존 nikke-roster의 내용과 동형
      "results": {                     // 추천 결과 캐시 (프로필 격리)
        "<inputHash>": RecommendationResult
      },
      "lastResultHash": "<inputHash>" | null,  // 재오픈 시 복원할 마지막 결과
      "lastInputs": {                  // 마지막 결과를 만든 입력 (UI 복원용)
        "boss": BossProfile,
        "draft": DraftDeck[]           // 비어있으면 zero-base
      } | null
    }
  }
}
```

- 계정 고유 데이터는 전부 프로필 내부. 프로필 간 병합/공유 경로는 존재하지 않는다.
- `RecommendationResult`는 `/api/recommend-raid` 응답(3단 tier 포함)을 그대로 저장.

---

## Sync 흐름 변경 (북마클릿 재설치 수반)

북마클릿 코드를 바꾸면 전 유저가 북마크를 다시 깔아야 한다(`bookmarklet.ts` 명시).
이 비용은 수용됐다.

1. **닉네임 캡처.** 북마클릿에 4번째 blablalink 호출을 추가:
   `POST api.blablalink.com/api/game/proxy/Game/GetUserProfileBasicInfo`
   `{ intl_open_id, nikke_area_id:81 }` → 응답에 `nickname` 키 존재(유저 실측 확인,
   2026-07-23). **정확한 응답 경로(`data.nickname` vs 중첩)는 구현 시 라이브 샘플로
   확정**하고, 없거나 형태가 어긋나면 `open_id`를 라벨 fallback으로 쓴다.
2. **payload 확장.** 앱으로 넘기는 payload에 `open_id`와 `nickname`을 추가한다
   (기존 `owned`/`character_details`/`recycle_room_researches`는 불변).
   `open_id`는 `SyncRosterPanel`이 sync 시점에 이미 알지만(share URL 파싱), payload에도
   실어 조립 경로가 단일 진실원을 갖게 한다.
3. **import = upsert.** 수신 시 `open_id`로 프로필을 upsert:
   - 새 `open_id` → 새 프로필 생성(다른 프로필로 절대 병합 안 함).
   - 기존 `open_id` → 제자리 갱신(로스터 교체, 닉네임 갱신).
   - 갱신으로 **로스터 내용이 바뀌면 그 프로필의 `results`를 클리어**(과거 결과는
     새 투자 상태에서 전부 stale). 로스터가 byte-동일이면 유지.
   - import 후 그 프로필로 `activeOpenId` 전환.

---

## 프로필 생명주기 / UI

- **프로필 전환기(드롭다운).** 닉네임 목록을 보여주고, 재-sync 없이 활성 프로필을
  전환한다. 전환 시 그 프로필의 로스터·결과·마지막 입력을 UI에 로드.
- **삭제.** 프로필 삭제(확인 포함). 마지막 프로필 삭제 시 `activeOpenId=null`,
  빈 상태(“sync로 시작하세요”)로 떨어진다.
- **활성 프로필 없음(초기/전체 삭제 후).** sync 안내만 표시. 로스터 편집 UI는
  활성 프로필이 있을 때만 의미를 가진다.

---

## 결과 영속 & 무효화 (본래 목적)

- 추천 실행 결과를 `profiles[openId].results[inputHash]`에 저장하고
  `lastResultHash`/`lastInputs`를 갱신한다.
- **inputHash = 안정 해시(로스터 투자데이터 전체 + boss 프로파일 + draft).** draft가
  비면 zero-base 경로. 해시 정규화(키 정렬 등)는 구현 detail.
- **재오픈/재요청 즉시 로드.** 앱 로드 시 활성 프로필의 `lastInputs`를 UI에 복원하고
  `lastResultHash`의 결과를 즉시 표시(백엔드 호출 0). 유저가 입력을 바꿔 재요청하면
  새 해시로 조회 → 히트면 즉시, 미스면 백엔드 호출 후 저장.
- **무효화.** 로스터 변경(재-sync)은 위 upsert 규칙으로 그 프로필 results를 클리어.
  boss/draft만 바뀌는 건 해시가 달라져 자연히 새 엔트리.
- **용량 상한.** 프로필당 results 엔트리 수에 LRU 상한(구현 시 수치 확정)을 둬
  무한 성장을 막는다.
- **정확성.** 엔진은 RNG 없는 결정론적 순수 함수라 (입력→결과) 캐싱은 근사가 아니라
  정확하다(엔진 자체가 결과 비교에 `>`/`max`를 쓰는 것이 결정론성의 방증).

---

## exia + 수동입력 제거

선행 decision의 이행. 제거:
- 프론트 `ImportRosterButton`(exia 파일 import)과 exia 형식 감지 분기.
- 수동 입력 폼(Phase 6 deliverable) 및 `useRoster`의 수동 편집 op(add/update/remove
  Nikke) — 프로필 로스터는 sync로만 채워진다.
- `mergeRosterDrafts`(exia 병합)와 관련 테스트.

유지:
- `SyncRosterPanel`·`useBookmarkletImport`·`mergeCollectorDrafts`(collector 병합)·
  `parseRosterJson`의 collector 파싱. `useRoster`는 프로필-인지 저장소로 재작성되되
  로스터를 소유하는 책임은 유지.

정확한 파일·심볼 절단면은 구현 plan에서 확정한다.

---

## 마이그레이션 (일회성 — 폐기)

아직 배포 서비스가 아니므로 보존 부담이 없다. 업그레이드 시 기존 단일
`nikke-roster` 키는 **폐기**한다(open_id가 없어 소급 키잉 불가, 어차피 재-sync 예정).
첫 로드에서 `nikke-profiles`가 없으면 빈 상태로 시작하고, 남아있는 legacy
`nikke-roster` 키는 정리한다.

---

## 프라이버시

- `open_id`와 `nickname`을 localStorage(유저 자기 브라우저)에 영속한다. 이는 이
  프로젝트가 그간 이 식별자들을 "민감값"으로 스크럽/미영속해온 스탠스의 **의도적
  반전**이며, 유저가 C안을 택하며 수용했다.
- **외부로 새로 전송하는 것은 없다.** `open_id`는 이미 북마클릿이 blablalink에
  보내던 값이고, `nickname`은 로컬에만 머문다. 우리 백엔드로 가는 요청 shape은
  불변(`clientId`만 실림, 계정 식별자 미포함).
- 미정 상태인 **프라이버시 정책 문서에 "계정 식별자·닉네임·로스터·결과를 브라우저
  로컬에 저장한다"는 사실을 반영**해야 한다(배포 선결 과제).

---

## 구현 시 확정할 열린 항목

1. `GetUserProfileBasicInfo` 응답에서 `nickname`의 정확한 경로 — 라이브 샘플로 픽스처
   확보 후 픽스처 기반 파서 테스트 작성.
2. `inputHash` 정규화 방식(직렬화 canonical form + 해시 함수)과 results LRU 상한 수치.
3. `NikkeDraft`/`RecommendationResult` 타입을 프로필 저장소에 그대로 재사용(직렬화
   호환) 확인.

---

## 테스트 고려

- 프로필 upsert: 새 open_id=신규, 기존 open_id=제자리 갱신, 로스터 변경 시 results
  클리어 / 동일 시 유지.
- 서로 다른 open_id 두 프로필이 절대 섞이지 않음(격리 불변식).
- 결과 캐시 히트/미스: 동일 입력 즉시 로드, 입력 변경 시 미스.
- 재오픈 복원: `lastInputs`/`lastResultHash`로 UI·결과 복원.
- 마이그레이션: legacy `nikke-roster` 존재 시 폐기 후 빈 상태 시작.
- exia/수동입력 경로 제거 후 회귀 없음(collector 경로 정상).
