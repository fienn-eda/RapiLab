// 전투 한 판을 가로 한 줄로. 엔진이 실제로 읽는 두 값 - 전투 시간과 파츠가
// 깨지는 시각 - 을 그대로 그린다.
//
// 왜 있나: 솔로 탭에서 보스 설정을 접어 두므로 그 두 값을 볼 곳이 여기뿐이다.
// 그리고 값이 틀리면 그 자리에서 이상함이 보인다 - CoreHitRateReadout이 코어
// 지름 옆에서 하는 일과 같은 종류다.
//
// 눈금(svg)은 aria-hidden이다. 같은 값을 아래 줄이 낱말로 다시 말하므로 화면
// 낭독기에는 그 줄 하나면 된다.

interface FightTimelineProps {
  /** 전투 시간(초). 숫자가 아니거나 0 이하면 그리지 않는다 - 편집 중인 반쪽짜리
   *  입력에 대고 눈금을 내면 자가 춤춘다. */
  durationSeconds: number
  /** 파츠가 깨지는 시각(초). */
  destructionTimes: number[]
}

export function FightTimeline({ durationSeconds, destructionTimes }: FightTimelineProps) {
  if (!Number.isFinite(durationSeconds) || durationSeconds <= 0) return null

  // 전투 시간 밖의 시각은 판독이 틀린 것이다. 끝에 몰아 찍으면 틀렸다는 사실이
  // 감춰지므로 잘라내지 않고 버린다.
  const marks = destructionTimes.filter((t) => t >= 0 && t <= durationSeconds)
  if (marks.length === 0) return null

  return (
    <div className="fight-timeline">
      <p className="fight-timeline__ends">
        <span>0</span>
        <span>{durationSeconds}초</span>
      </p>
      <svg
        className="fight-timeline__rule"
        viewBox="0 0 100 8"
        preserveAspectRatio="none"
        aria-hidden="true"
      >
        {/* preserveAspectRatio="none"이라 가로로 늘어난다. 선 굵기까지 같이
            늘어나지 않도록 non-scaling-stroke를 준다. */}
        <line x1="0" y1="4" x2="100" y2="4" vectorEffect="non-scaling-stroke" />
        {marks.map((t) => {
          const x = (t / durationSeconds) * 100
          return (
            <line key={t} x1={x} y1="0" x2={x} y2="8" vectorEffect="non-scaling-stroke" />
          )
        })}
      </svg>
      <p className="fight-timeline__marks">파괴 {marks.join(' · ')}초</p>
    </div>
  )
}
