// 보스의 기믹을 낱말로. 결과 화면(BossSummary)과 시즌 가이드 카드가 같은 낱말을
// 써야 해서 한 곳에서 만든다 - 두 곳이 갈라지면 같은 보스가 화면마다 다른 기믹을
// 가진 것처럼 읽힌다.

/** 뱃지를 만드는 데 필요한 필드만. 결과의 `BossProfile`과 폼 상태인
 * `BossProfileDraft`가 둘 다 구조적으로 이것을 만족한다 - 둘 중 하나로 좁혀
 * 잡으면 나머지 한쪽이 못 부른다. */
export interface BossGimmickFlags {
  core_hittable: boolean
  pierce_hits_body_behind_core: boolean
  part_destructible: boolean
  spawns_adds: boolean
  elemental_interrupt_required: boolean
}

/** 켜진 기믹만. 꺼진 것까지 적으면 줄만 길어지고, 없는 것은 화면에 없는 것으로
 * 읽힌다. 순서가 고정인 이유: 보스를 바꿀 때마다 뱃지가 자리를 옮기면 읽는 눈이
 * 매번 줄 전체를 처음부터 훑어야 한다. */
export const gimmickBadges = (boss: BossGimmickFlags): string[] =>
  [
    boss.core_hittable && '코어 피격',
    boss.pierce_hits_body_behind_core && '2관통',
    boss.part_destructible && '부위파괴',
    boss.spawns_adds && '잡몹 생성',
    boss.elemental_interrupt_required && '속성저지 필수',
  ].filter((label): label is string => typeof label === 'string')
