// 덱 5인 중 누가 미란다의 두 대상형 버프를 받는지, 초상화 옆 뱃지로.
//
// 금색 [크확] = 웨이크업! 3번불릿, 은색 [공격력][크댐] = 파워업!(버스트).
// 두 불릿의 대상은 사이클마다 바뀔 수 있어서, 뱃지는 「전 사이클」이 기본이고
// 일부 사이클에서만 받으면 n/T가 붙는다.

import type { MirandaTargetsResult } from '../types/mirandaTargets'

interface MirandaTargetsProps {
  result: MirandaTargetsResult
  portraitFor: (slug: string) => string | null
  nameFor: (slug: string) => string
}

const percent = (value: number) => `${value.toFixed(2)}%`

const countIn = (cycles: string[][], slug: string) =>
  cycles.filter((targets) => targets.includes(slug)).length

export function MirandaTargets({ result, portraitFor, nameFor }: MirandaTargetsProps) {
  const { cycles, seats, mirandaSlug, overloadThresholds, overloadAtkCapPercent } = result
  const total = cycles.length
  const poweringUp = cycles.map((cycle) => cycle.poweringUp)
  const wakeUp = cycles.map((cycle) => cycle.wakeUpCritRate)
  const thresholdFor = new Map(overloadThresholds.map((row) => [row.slug, row]))

  // 미란다가 버스트한 사이클과 못 한 사이클. 후자가 있으면 파워업!의 n/T가
  // 「밀렸다」가 아니라 「그녀가 못 쐈다」는 뜻이 되므로 따로 말해야 한다.
  const burstCycles = poweringUp.filter((targets) => targets.length > 0).length

  // 파워업! 대상이 실제로 쏜 사이클끼리 갈리는가 - 버스트를 못 한 사이클(빈
  // poweringUp)은 비교에서 뺀다(그건 burstCycles 캐비엇의 몫이고, 빈 배열을
  // 기준으로 삼으면 나머지가 서로 같아도 전부 「갈렸다」고 오판한다). 기준은
  // 첫 버스트 사이클, 비교는 순서가 아니라 집합으로 한다 - 백엔드가 순위
  // 순으로 주므로 같은 두 명이 자리만 바뀐 것을 변경으로 읽으면 안 된다.
  const burstingCycles = cycles.filter((cycle) => cycle.poweringUp.length > 0)
  const referenceTargets = new Set(burstingCycles[0]?.poweringUp ?? [])
  const changedCycles = burstingCycles
    .filter((cycle) => {
      const targets = new Set(cycle.poweringUp)
      return targets.size !== referenceTargets.size ||
        [...targets].some((slug) => !referenceTargets.has(slug))
    })
    .map((cycle) => cycle.index)

  // 뱃지의 n/T는 「적어도 한 사이클」을 답한다. 이 문장이 재는 경계는 그와
  // 다른 「매 사이클」이다(설계문서 §5.3) - 부분 수령 행에서 둘이 같은 줄에
  // 뜨므로, 각 문장이 자기 기준을 스스로 말해야 뱃지와 안 부딪힌다.
  const describeThreshold = (slug: string): string | null => {
    const row = thresholdFor.get(slug)
    if (!row) return null
    if (row.kind === 'gain') {
      if (row.thresholdPercent === null) {
        return `오버로드 공격력을 상한(${percent(overloadAtkCapPercent)})까지 올려도 매 사이클 받지는 못해요`
      }
      const gap = row.thresholdPercent - row.currentPercent
      return `오버로드 공격력 ${percent(row.currentPercent)} → ${percent(row.thresholdPercent)}면 매 사이클 받아요 (+${gap.toFixed(2)}%p)`
    }
    // kind가 'keep'이면 지금 받고 있다는 뜻이라 경계는 항상 숫자다 (백엔드
    // overload_thresholds가 이 조합에서만 null을 안 낸다) - null 분기는 gain 쪽뿐.
    const { thresholdPercent } = row
    if (thresholdPercent === null) return null
    if (thresholdPercent === 0) return '오버로드 공격력이 없어도 매 사이클 유지돼요'
    const slack = row.currentPercent - thresholdPercent
    return `오버로드 공격력이 ${percent(thresholdPercent)} 밑으로 내려가면 매 사이클은 못 받아요 (지금 ${percent(row.currentPercent)}, 여유 ${slack.toFixed(2)}%p)`
  }

  return (
    <section className="miranda-targets">
      <ul className="miranda-targets__list">
        {seats.map((seat) => {
          const name = nameFor(seat.slug)
          const portrait = portraitFor(seat.slug)
          const wakeCount = countIn(wakeUp, seat.slug)
          const powerCount = countIn(poweringUp, seat.slug)
          const threshold = describeThreshold(seat.slug)
          return (
            <li className="miranda-targets__row" key={seat.slug} aria-label={name}>
              {portrait ? (
                <img className="miranda-targets__portrait" src={portrait} alt="" />
              ) : (
                <span className="miranda-targets__portrait miranda-targets__portrait--missing" />
              )}
              <span className="miranda-targets__name">{name}</span>
              {seat.slug === mirandaSlug ? (
                <span className="miranda-targets__caster">시전자</span>
              ) : (
                <span className="miranda-targets__badges">
                  {wakeCount > 0 && (
                    <span className="miranda-badge miranda-badge--gold">
                      <span>크확</span>
                      {wakeCount < total && <b>{wakeCount}/{total}</b>}
                    </span>
                  )}
                  {powerCount > 0 && (
                    <>
                      <span className="miranda-badge miranda-badge--silver"><span>공격력</span></span>
                      <span className="miranda-badge miranda-badge--silver">
                        <span>크댐</span>
                        {powerCount < total && <b>{powerCount}/{total}</b>}
                      </span>
                    </>
                  )}
                </span>
              )}
              {threshold && <span className="miranda-targets__threshold">{threshold}</span>}
            </li>
          )
        })}
      </ul>

      {changedCycles.length > 0 && (
        <p className="miranda-targets__caveat">
          ⚠ {changedCycles.join('·')}사이클에는 파워업!을 받는 니케가 달라요
        </p>
      )}
      {burstCycles < total && (
        <p className="miranda-targets__caveat">
          ⚠ 미란다는 {total}사이클 중 {burstCycles}번만 버스트해요 (같은 1티어에 니케가 둘이에요)
        </p>
      )}
      {result.notes.map((note) => (
        <p className="miranda-targets__note" key={note}>{note}</p>
      ))}
    </section>
  )
}
