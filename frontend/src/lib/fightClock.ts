// 전투 시계. 게임 UI가 남은 시간을 3:00 → 0:00으로 세므로 화면도 그렇게 적는다.
//
// **저장의 진실은 경과 초다.** part_destruction_times와 엔진이 쓰는 단위가 그것이고,
// 경과로 저장해야 전투 시간을 바꿔도 이벤트가 전투 시작에 그대로 붙어 있는다.
// 잔여시간은 화면에 그릴 때만 만들어 쓰는 값이라, 변환이 이 파일 밖으로 나가면
// 두 단위가 섞이기 시작한다.

/** 경과 초 -> 남은 시간 `m:ss`. 전투 시간을 넘긴 값은 0:00으로 눕힌다 -
 * 음수 시계는 게임에 없다. */
export const remainingLabel = (elapsedSeconds: number, fightDuration: number): string => {
  const left = Math.max(0, Math.round(fightDuration - elapsedSeconds))
  const minutes = Math.floor(left / 60)
  const seconds = left % 60
  return `${minutes}:${String(seconds).padStart(2, '0')}`
}

/** 사람이 친 남은 시간 `m:ss` -> 경과 초. 온전히 읽히지 않으면 null.
 *
 * 「2」나 「2:4」처럼 치는 중인 값에 null을 주는 것이 이 함수의 목적이다 -
 * 부르는 쪽은 null인 동안 값을 갱신하지 않아서, 목록이 정렬돼 있어도 편집 중인
 * 행이 튀어 오르지 않는다. */
export const parseRemaining = (
  input: string,
  fightDuration: number,
): number | null => {
  const match = /^(\d{1,2}):([0-5]\d)$/.exec(input.trim())
  if (match === null) return null
  const left = Number(match[1]) * 60 + Number(match[2])
  // 전투 시간보다 많이 남을 수는 없다. 그런 입력은 판독이 틀린 것이고, 시작
  // 시점으로 눕히면 틀렸다는 사실이 감춰지므로 거절한다.
  if (left > fightDuration) return null
  return fightDuration - left
}
