// 전투 한 판을 세로 한 줄로. 남은 시간이 위에서 아래로 3:00 → 0:00으로 줄어들고,
// 그 위에 이 보스가 무엇을 하는지가 얹힌다.
//
// 세로인 이유: 설명이 「탄막 사격 — 엄폐로 넘긴다」 같은 한글 문장이고, 이 카드가
// 서는 곳은 세로로 긴 우측 컬럼이다. 가로축에 얹으면 라벨 자리가 모자라 서너 개만
// 넘어가도 겹친다(참고로 받은 가로 타임라인 셋이 전부 라벨을 위아래로 교차
// 배치하거나 줄기 길이를 엇갈리는 이유가 그것이다). 세로면 이벤트마다 한 줄을
// 통째로 써서 길이 제약이 없다.
//
// 읽기용과 편집용을 따로 두지 않는다 - 행이 곧 입력이다. 단 **파괴 행은 읽기
// 전용이다**: 엔진이 읽는 입력(보스 설정의 「파괴 시각」)이라 여기서도 고치게 하면
// 같은 값을 두 자리에서 편집하게 되고 진실이 둘이 된다.

import { useId } from 'react'
import { parseRemaining, remainingLabel } from '../lib/fightClock'
import { makeGuideEventId, type GuideEvent } from '../hooks/useBossGuides'

interface FightTimelineProps {
  /** 전투 시간(초). 숫자가 아니거나 0 이하면 그리지 않는다 - 잔여시간을 셀
   *  기준이 없다. */
  fightDuration: number
  /** 보스 설정에서 오는 파츠 파괴 시각(경과 초). 읽기 전용 행이 된다. */
  destructionTimes: number[]
  /** Fienn이 직접 적는 이벤트들. */
  events: GuideEvent[]
  onChange: (events: GuideEvent[]) => void
}

/** 설명 칸의 높이를 내용에 맞춘다. 한 줄짜리 input으로 두면 문장이 잘려서
 * 읽을 수가 없는데, 이 칸에 들어가는 것은 「탄막 사격 — 엄폐로 넘긴다」 같은
 * 문장이다. 늘 auto로 되돌린 뒤 재는 이유: 줄이 줄어들 때 scrollHeight가 옛
 * 높이에 갇힌다. */
const autosize = (el: HTMLTextAreaElement | null) => {
  if (el === null) return
  el.style.height = 'auto'
  el.style.height = `${el.scrollHeight}px`
}

/** 한 행. 파괴(자동)와 패턴(직접 입력)이 같은 축 위에 서되 마커로 갈린다. */
type Row =
  | { kind: 'edge'; at: number; label: string }
  | { kind: 'destruction'; at: number }
  | { kind: 'event'; at: number | null; event: GuideEvent }

/** 경과 초 오름차순 = 잔여시간이 줄어드는 순서. 시각 없는 항목은 맨 뒤로 민다 -
 * 축 위에 놓을 자리가 없기 때문이지 덜 중요해서가 아니다. */
const sortRows = (rows: Row[]): Row[] =>
  [...rows].sort((a, b) => {
    const at = (row: Row) => (row.kind === 'event' ? row.at : row.at)
    const left = at(a)
    const right = at(b)
    if (left === null) return right === null ? 0 : 1
    if (right === null) return -1
    return left - right
  })

export function FightTimeline({
  fightDuration,
  destructionTimes,
  events,
  onChange,
}: FightTimelineProps) {
  const timeLabelId = useId()

  if (!Number.isFinite(fightDuration) || fightDuration <= 0) return null

  const rows = sortRows([
    { kind: 'edge', at: 0, label: '전투 시작' },
    ...destructionTimes
      .filter((t) => t >= 0 && t <= fightDuration)
      .map((at): Row => ({ kind: 'destruction', at })),
    ...events.map((event): Row => ({ kind: 'event', at: event.at, event })),
    { kind: 'edge', at: fightDuration, label: '종료' },
  ])

  const replace = (id: string, patch: Partial<GuideEvent>) =>
    onChange(events.map((e) => (e.id === id ? { ...e, ...patch } : e)))

  return (
    <div className="timeline">
      <ol className="timeline__rows">
        {rows.map((row, index) => {
          if (row.kind === 'edge') {
            return (
              <li
                key={`edge-${index}`}
                className={`timeline__row timeline__row--edge timeline__row--${
                  row.at === 0 ? 'start' : 'end'
                }`}
              >
                <span className="timeline__time">{remainingLabel(row.at, fightDuration)}</span>
                <span className="timeline__text">{row.label}</span>
              </li>
            )
          }

          if (row.kind === 'destruction') {
            return (
              <li
                key={`destruction-${row.at}`}
                className="timeline__row timeline__row--auto"
              >
                <span className="timeline__time">{remainingLabel(row.at, fightDuration)}</span>
                <span className="timeline__text">부위파괴</span>
              </li>
            )
          }

          const { event } = row
          return (
            <li
              key={event.id}
              className={`timeline__row timeline__row--event${
                event.at === null ? ' timeline__row--always' : ''
              }`}
            >
              {/* 시각 칸은 온전히 읽힐 때만 at을 갱신한다. 「1:」에서 갱신하면
                  목록이 정렬돼 있어 편집 중인 행이 튀어 오른다. 비우면 「상시」다. */}
              <input
                className="timeline__time timeline__time--input"
                type="text"
                inputMode="numeric"
                aria-label="남은 시간"
                placeholder="상시"
                defaultValue={event.at === null ? '' : remainingLabel(event.at, fightDuration)}
                onChange={(e) => {
                  const raw = e.target.value
                  if (raw.trim() === '') {
                    replace(event.id, { at: null })
                    return
                  }
                  const at = parseRemaining(raw, fightDuration)
                  if (at !== null) replace(event.id, { at })
                }}
              />
              <textarea
                className="timeline__text timeline__text--input"
                rows={1}
                aria-labelledby={timeLabelId}
                placeholder="이 시점에 무엇을 하나"
                value={event.text}
                ref={autosize}
                onChange={(e) => {
                  autosize(e.currentTarget)
                  replace(event.id, { text: e.target.value })
                }}
              />
              <button
                type="button"
                className="timeline__remove"
                aria-label="삭제"
                onClick={() => onChange(events.filter((e) => e.id !== event.id))}
              >
                ×
              </button>
            </li>
          )
        })}
      </ol>

      <span id={timeLabelId} className="visually-hidden">
        이벤트 설명
      </span>

      <button
        type="button"
        className="btn timeline__add"
        onClick={() =>
          onChange([...events, { id: makeGuideEventId(), at: null, text: '' }])
        }
      >
        이벤트 추가
      </button>
    </div>
  )
}
