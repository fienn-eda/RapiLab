// 한 blablalink 계정은 여러 게임 서버에 각각 다른 로스터를 가질 수 있고, API는
// 서버를 `nikke_area_id`로 지목한다. 목록의 출처는 blablalink 자신이다:
// GET api/lip/direct/commodity/Game/GetRegionList?game_id=29080 -> area_list.
// API가 부르는 이름은 Japan/NA/Korea/Global/SEA이고, 화면에는 짧은 코드를 쓴다.
// 하드코딩인 이유: 이 목록이 바뀌는 것은 새 서버가 열릴 때뿐이고, 그때 한 줄
// 더하는 것이 라이브 조회를 유지하는 것보다 싸다.

export const SERVERS: readonly { area: number; label: string }[] = [
  { area: 81, label: 'JP' },
  { area: 82, label: 'NA' },
  { area: 83, label: 'KR' },
  { area: 84, label: 'GL' },
  { area: 85, label: 'SEA' },
]

export const SERVER_AREAS: readonly number[] = SERVERS.map((s) => s.area)

export const serverLabel = (area: number): string =>
  SERVERS.find((s) => s.area === area)?.label ?? String(area)
