# 애장품 4인방 온보딩 — Sugar · Flora · Rosanna · Phantom

- 날짜: 2026-07-24
- 상태: 설계 확정 (구현 대기)
- 관련: `2026-07-21-shiftypad-weapon-skill-migration-design.md`
  (이 설계는 그 문서가 "받아들이는 한계"로 남긴 dollskills 구멍을 코드로 메운다)

Sugar · Flora · Rosanna · Phantom 네 유닛에 애장품(Favorite Item)이 추가됐다. 넷 다
미인코딩이고 로컬 데이터도 없어 수집부터 시작한다. 각 유닛을 **base + `-signature`
듀얼 슬롯**으로 인코딩한다.

주의: `rosanna-chic-ocean`은 이미 인코딩된 **별개 유닛**이다. 여기서 다루는 Rosanna는
base(resource_id 280) 쪽이다.

## 실측으로 확인한 전제

- **애장품 스킬 데이터는 lootandwaifus에 이미 있다.** 네 유닛 페이지 모두
  `skill-title-section` 타이틀 6개(base 3 + treasure 3) · `level-description` 문단
  60개를 반환한다 — `lootandwaifus_html_to_json.py`가 `dollskills`로 잘라내는 바로 그
  구조다.
- **dotgg는 죽었다.** `api.dotgg.gg/cgfw/getcharacter`가 네 유닛 모두 HTTP 200에
  **빈 본문**을 준다. 무기 스탯을 dotgg에서 받을 길은 없다.
- **`load_nikke_spec`은 lootandwaifus 소스 유닛의 무기 스탯을 dotgg에서만 읽는다.**
  (트렁크 `659e1fa` 기준 재확인.) 따라서 시그니처 슬러그를 `source: "lootandwaifus"`로
  두면 무기 파일이 없어 `None`을 반환하고 유닛이 **조용히 로스터에서 제외**된다.
  기존 시그니처 3인방이 멀쩡한 것은 `data/dotgg/`에 `char_julia.json` ·
  `char_drake-nikke.json` · `char_laplace.json`이 **실제로 있기 때문**이지 경로가
  옳아서가 아니다. 네 유닛은 그 파일이 없고 dotgg에서 새로 받을 수도 없다.
  이것이 이번 작업의 유일한 엔진 변경 지점이다.
- **듀얼 슬롯 기계는 이미 완성돼 있다.** `resourceIdSlugMap.ts`의
  `RESOURCE_ID_TO_SLUG` → base, `SIGNATURE_OWNED`(보유 rid 집합) ∩
  `DUAL_SLOT_BASES`일 때만 `-signature`로 승격. 백엔드 드리프트 테스트가
  `DUAL_SLOT_BASES == 인코딩된 base/-signature 페어`를 단언한다.
- **resource_id**: Sugar 140 · Rosanna 280 · Flora 411 · Phantom 580
  (`data/cache/new-nikke-check/fresh-directory.json` 조회).

## 애장품 보유 상태

Fienn은 넷 다 애장품 제작 계획은 있으나 **지금은 불가능**하다. 그래서
`SIGNATURE_OWNED`는 **이번 작업에서 건드리지 않는다** — 추천은 base로 나가고,
애장품을 완성하면 그 rid 한 줄을 추가하는 것만으로 시그니처 인코딩이 활성화된다.
시그니처를 지금 함께 인코딩하는 이유는 (1) 데이터 파일이 유닛당 하나라 수집 비용이
동일하고, (2) base와 doll의 스킬명이 같아(예: Sugar `Black Typhoon` / `Noire Sensor` /
`Trouble Shooter`) 스킬 문맥이 머릿속에 있을 때 delta만 보면 되며, (3) "애장품을
만들 가치가 있나"를 지금 시뮬레이션으로 답할 수 있기 때문이다.

---

## Phase 0 — `weapon_source` 배선

`SKILL_VALUE_MANIFESTS`에 **선택적 `weapon_source` 키**를 추가하고,
`load_nikke_spec`이 무기 파일 소스를 `manifest.get("weapon_source", manifest["source"])`
로 고르게 한다. 기본값이 현행 동작이므로 기존 77슬러그는 무영향이다.

- shiftypad 소스: `data/shiftypad/<data_slug>.json`
- 그 외(dotgg · lootandwaifus): 현행대로 `data/dotgg/<dotgg_slug 또는 data_slug>.json`

시그니처 슬러그의 매니페스트 모양:

```python
"sugar-signature": {
    "source": "lootandwaifus",      # 스킬값 = dollskills
    "weapon_source": "shiftypad",   # 무기 스탯 = 정규화된 ShiftyPad 파일
    "data_slug": "sugar",           # 두 소스 모두 base 슬러그의 파일을 읽는다
    "test_module": "test_skill_rules_sugar_signature",
    "keys": {...: ("dollskills", N)},
}
```

애장품은 무기 자체를 바꾸지 않으므로 base와 같은 무기 스탯 파일을 공유하는 것이
옳다. 무기 프로필이 스킬로 바뀌는 경우는 기존대로
`get_weapon_profile_override`가 처리한다.

## Phase 1 — 수집 (유닛당)

**수집은 메인 체크아웃에서 돌리고 워크트리로 동기화한다.** `collect.js`의
`node_modules`가 메인 체크아웃에만 있어 워크트리에서 실행하면 `MODULE_NOT_FOUND`로
죽는다. 수집 후 워크트리에서 `python scripts/sync_worktree_data.py`
(`data/dotgg` · `data/lootandwaifus` · `data/shiftypad`를 가져온다 — shiftypad 누락은
`659e1fa`에서 수정됨).

1. **lootandwaifus** (base 스킬 텍스트 + dollskills): 참조 문서의 `curl -A`
   (WebFetch는 403) 로 `data/lootandwaifus/char_<slug>.html` 저장 → `python
   scripts/lootandwaifus_html_to_json.py --slug <slug>` → `skills` + `dollskills`.
2. **ShiftyPad** (무기 6필드 + 스킬 값 슬롯 + element/burst/burst-cooldown):
   `cd tools/collect-blablalink && node collect.js --nikke <rid> --headless` →
   `data/shiftypad/raw/<rid>.json` → `python scripts/normalize_shiftypad_raw.py
   140:sugar` (스크립트는 `<rid>:<slug>` 쌍을 명시적으로 받으므로 프런트의 슬러그
   맵보다 먼저 돌 수 있다) → `data/shiftypad/<slug>.json`.
   **무기 스탯 수동 입력 없음.**
3. **포트레이트**: `python scripts/download_portraits.py`.

## Phase 2 — 인코딩 (유닛별 완주: base → signature → 다음 유닛)

`nikke-skill-encoding` 스킬의 워크플로를 그대로 따른다. 유닛당 산출물:

- `backend/app/skill_rules/<slug>.py` — `source: "shiftypad"`, native slot keys.
- `backend/app/skill_rules/<slug>_signature.py` — Phase 0의 매니페스트 모양.
  doll 스킬이 base와 **같은 형태에 값만 다르면** base 모듈의 `build_*` 함수를
  import해 재사용하고, **효과 자체가 다르면** 시그니처 모듈에 새로 쓴다. 기준은
  형태(어떤 규칙 프리미티브를 쓰는가)이지 값이 아니다 — Julia가 base/시그니처를
  별도 모듈로 두면서도 Crescendo의 `ResourceSpec` 모양을 공유하는 것과 같다.
- `registry.py` 배선 2건(base, signature).
- `backend/tests/test_skill_rules_<slug>.py` · `..._signature.py`.

엔진이 표현 못 하는 기전은 스킬 규칙대로 모듈 docstring에 보류로 적고
`docs/engine-gaps.md`에 집계한다. 기전이 불명확하면 추측하지 않고 Fienn에게 묻는다.

**두 소스를 함께 읽는다 — 어느 한쪽만으로는 인코딩할 수 없다.**

- **ShiftyPad 정규화 출력의 스킬 description은 비어 있다** (값 슬롯만 있고 문장이
  없다). 각 슬롯이 무슨 효과인지는 **반드시 lootandwaifus 텍스트로 확인**한다.
  애장품 유닛만의 문제가 아니라 shiftypad 소스 유닛 전반에 해당한다.
- **lootandwaifus에는 `description_value_NN`이 없다** — 숫자가 문장에 인라인으로
  렌더된다. 슬롯 번호는 그 스킬 텍스트의 **좌→우 등장 순서**로 직접 매기고, 소스 간
  번호가 어긋나면 매니페스트의 `drop_tokens`로 보정한다. 어긋남은
  `test_skill_value_assembly.py` 하네스가 잡아준다.

## Phase 3 — 로스터 배선

`frontend/src/lib/resourceIdSlugMap.ts`:
- `RESOURCE_ID_TO_SLUG`에 `140: 'sugar'` · `280: 'rosanna'` · `411: 'flora'` ·
  `580: 'phantom'` 추가 (듀얼 슬롯 주석 관례를 따른다).
- `DUAL_SLOT_BASES`에 네 base 슬러그 추가.
- `SIGNATURE_OWNED`는 **변경 없음** (애장품 미보유).

## Phase 4 — 문서

- `docs/encoded-nikkes.md` — 유닛 8행 추가, 총계·버스트 티어 분포 갱신, 완성도 등급.
- `docs/roadmap.md` — 배치 완료 기록.
- `docs/decisions.md` — `weapon_source` 도입(맥락: dotgg 사망 + ShiftyPad가
  dollskills 미노출 → 소스를 무기/스킬로 분리).
- `docs/engine-gaps.md` — 이번 8모듈에서 나온 보류를 기존 갭에 합산하거나 신규 등록.

---

## 테스트

- **Phase 0 배선:** `weapon_source: "shiftypad"` + `source: "lootandwaifus"` 조합이
  `load_nikke_spec`을 통과해 무기 스탯·스킬값·메타를 올바르게 산출하는지. 키를
  생략한 기존 매니페스트가 현행과 동일하게 동작하는지(회귀).
- **유닛별:** 스킬 규칙 단위 테스트(버프 값·지속·쿨다운·버스트 배율), base와
  signature가 서로 다른 값을 내는지, `SKILL_VALUE_MANIFESTS` 조립이 실제 데이터
  파일에서 성공하는지(`test_skill_value_assembly.py`가 전수 검사).
- **듀얼 슬롯 정합:** 기존 드리프트 테스트가 `DUAL_SLOT_BASES`와 인코딩 페어의
  일치를 자동 단언한다 — 프런트 갱신을 빠뜨리면 스위트가 실패한다.
- **회귀:** 백엔드 전체 스위트가 기존 기준선을 유지.
- 라이브 수집(네트워크)은 단위 테스트하지 않는다.

## 범위 밖

- `SIGNATURE_OWNED` 갱신 — 애장품 실제 제작 시점의 별건.
- 기존 유닛의 무기 스탯 소스 백필 — go-forward 결정 유지.
- 애장품 **스탯 보너스**(ATK/HP/DEF 증가분) 모델링 — 엔진은 base_stats를 사용자
  입력으로 받으므로, 애장품 스탯은 Fienn이 로스터 동기화로 넘기는 실제 수치에 이미
  포함된다. 별도 모델링 대상이 아니다.
- 애장품 자동 감지(collector Collection 탭 `favorite_rare`) — 기존 TODO, 이번 범위 밖.
