## 병렬 세션 경계 (2026-07-18)

다른 세션이 **Phase 7 B2(ATK 자동 계산 / 스탯 조립 계산기)**를 진행 중이다.
브랜치 `wip/stat-pipeline`, 워크트리 `.claude/worktrees/plans-frontend3-encoding`.

### 그 세션이 소유한 파일 — 건드리지 말 것
- `backend/app/stat_assembly.py`, `backend/tests/test_stat_assembly.py` (신규)
- `backend/tests/fixtures/stat_ground_truth.json` (신규)
- `tools/collect-blablalink/**` 전부
- `scripts/verify_raid400_correction.py`
- `docs/superpowers/{specs,plans}/2026-07-18-stat-assembly-calculator*`
- `docs/superpowers/plans/2026-07-18-blablalink-stat-collector.md`

### 인코딩 세션이 소유 — 그 세션은 안 건드림 (읽기만)
- `backend/app/skill_rules/**` (`registry.py` 포함)
- `backend/tests/test_skill_rules_*.py`
- `frontend/src/lib/resourceIdSlugMap.ts` ← **인코딩 세션이 자유롭게 수정**
- `backend/tests/test_resource_id_slug_map.py` (`KNOWN_UNMAPPED`)
- `backend/tests/test_resource_id_directory.py` (`SLUG_NAME_EXCEPTIONS`)
- `docs/encoded-nikkes.md`, `docs/engine-gaps.md`
- `.claude/skills/nikke-skill-encoding/references/**`

### 공유 — 충돌 예상, 섹션 단위로 쓸 것
- `docs/roadmap.md` ← **가장 위험**. Phase 7 B1/B2 항목은 건드리지 말 것.
  인코딩은 "Burst 3 어태커 인코딩 배치(eb)" 섹션과 Phase 4/5 쪽만.
- `docs/decisions.md`, `docs/insights.md` ← 추가만(append). 기존 항목 수정 금지.
  추가만 하면 git이 대체로 자동 병합함.

### 주의: 엔진 코어
인코딩 중 엔진 확장이 필요해지면 `backend/app/`의 공유 모듈
(`raid_simulator.py`, `effects.py`, `squad_engine.py`, `models.py`)을 건드리게 된다.
**그 경우 병합 전에 알릴 것.** 다른 세션은 `backend/app/`에 새 모듈 하나만 추가한다.

### 운영 규칙
1. **자체 워크트리 + 자체 브랜치**에서 작업. 메인 체크아웃(`wip/scaffolding`)에서 직접 작업 금지.
2. 작업 시작 시 `python scripts/sync_worktree_data.py` **먼저 실행**.
   `data/`는 gitignore라 워크트리는 빈 상태로 시작하고, 안 돌리면 측정값이 거짓말을 한다.
3. `git stash` 맨몸 사용 금지 — stash 스택이 전 워크트리 공유다.
   불가피하면 `git stash push -u -m "<고유태그>"` 후 SHA로 `apply`.
4. **트렁크 병합은 한 번에 한 세션씩.** 병합 후 전체 스위트 재실행.
5. 문서에 **테스트 절대 개수를 적지 말 것**(예: "774 passed"). 병렬 작업 중엔 즉시 낡고
   두 세션이 서로 다른 숫자를 써서 충돌한다.