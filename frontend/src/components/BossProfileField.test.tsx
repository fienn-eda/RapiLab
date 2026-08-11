// 보스 설정의 설명은 라벨 옆 버튼 뒤에 접혀 있다. 여기서 지키는 것은 그
// 버튼이 설정 자체를 건드리지 않는다는 것 - 체크박스 라벨 안에 있으면
// 설명을 열려는 클릭이 보스 프로필을 바꾼다.

import { useState } from 'react'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { BossProfileField } from './BossProfileField'
import { bossElementFor } from '../lib/elementAdvantage'
import { makeDefaultBossProfileDraft } from '../types/bossProfileDraft'
import type { RaidRotation } from '../types/raidRotation'
import { HELP } from '../lib/helpText'

const renderField = (onChange = vi.fn()) => {
  render(<BossProfileField value={makeDefaultBossProfileDraft()} onChange={onChange} />)
  return onChange
}

describe('BossProfileField', () => {
  it('설명 버튼을 눌러도 체크박스가 바뀌지 않는다', async () => {
    const user = userEvent.setup()
    const onChange = renderField()

    await user.click(screen.getByRole('button', { name: '코어 타격 가능 설명' }))
    await user.click(screen.getByRole('button', { name: '부위파괴 기믹 설명' }))

    expect(onChange).not.toHaveBeenCalled()
  })

  it('체크박스는 설명을 뺀 이름으로 잡힌다', async () => {
    // 설명이 라벨 안에 있으면 접근성 이름이 문단 하나가 되어, 화면 낭독기가
    // 체크박스 하나를 읽는 데 세 문장을 읽는다.
    const user = userEvent.setup()
    const onChange = renderField()

    await user.click(screen.getByLabelText('코어 타격 가능'))

    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ core_hittable: true }),
    )
  })

  it('설명은 자기가 딸린 설정을 가리킨다', () => {
    renderField()

    const button = screen.getByRole('button', { name: '보스 적정거리 설명' })
    const bubbleId = button.getAttribute('aria-describedby')

    expect(bubbleId).toBeTruthy()
    expect(document.getElementById(bubbleId!)).toHaveTextContent(HELP.boss.rangeBand)
  })
})

describe('BossProfileField 약점 속성 선택', () => {
  it('약점 아이콘을 고르면 보스 본인 속성이 draft로 간다', async () => {
    // 화면은 약점으로 말하고 와이어는 보스 본인 속성을 나른다. 수냉이 약점이면
    // 보스는 작열이다.
    const user = userEvent.setup()
    const onChange = renderField()

    await user.click(screen.getByLabelText('수냉'))

    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ element: 'Fire' }))
  })

  it('저장된 보스 속성이 대응하는 약점 아이콘을 선택 상태로 그린다', () => {
    render(
      <BossProfileField
        value={{ ...makeDefaultBossProfileDraft(), element: 'Fire' }}
        onChange={vi.fn()}
      />,
    )

    expect(screen.getByLabelText('수냉')).toBeChecked()
    expect(screen.getByLabelText('작열')).not.toBeChecked()
  })

  it('약점 없음이 null로 왕복한다', async () => {
    const user = userEvent.setup()
    const onChange = vi.fn()
    render(
      <BossProfileField
        value={{ ...makeDefaultBossProfileDraft(), element: 'Fire' }}
        onChange={onChange}
      />,
    )

    await user.click(screen.getByLabelText('약점 없음'))

    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ element: null }))
  })
})

describe('BossProfileField 속성저지', () => {
  it('기본으로 속성저지 체크박스를 그린다', async () => {
    const user = userEvent.setup()
    const onChange = renderField()

    await user.click(screen.getByLabelText('속성저지 필수'))

    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ elemental_interrupt_required: true }),
    )
  })

  it('showElementalInterrupt=false면 그리지 않는다', () => {
    // 유니온레이드 탭은 탐색이 없어 제약이 걸 곳이 없다.
    render(
      <BossProfileField
        value={makeDefaultBossProfileDraft()}
        onChange={vi.fn()}
        showElementalInterrupt={false}
      />,
    )

    expect(screen.queryByLabelText('속성저지 필수')).not.toBeInTheDocument()
  })
})

describe('BossProfileField 코어 2관통', () => {
  it('2관통을 켜면 코어 타격 가능도 함께 켜진다', async () => {
    // 코어를 못 때리면 뚫고 지나갈 것이 없다. 모순 상태를 만들 수 없게 한다.
    const user = userEvent.setup()
    const onChange = renderField()

    await user.click(screen.getByLabelText('상시 코어 2관통'))

    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ core_hittable: true, pierce_hits_body_behind_core: true }),
    )
  })

  it('코어 타격 가능을 끄면 2관통도 꺼진다', async () => {
    const user = userEvent.setup()
    const onChange = vi.fn()
    render(
      <BossProfileField
        value={{
          ...makeDefaultBossProfileDraft(),
          core_hittable: true,
          pierce_hits_body_behind_core: true,
        }}
        onChange={onChange}
      />,
    )

    await user.click(screen.getByLabelText('코어 타격 가능'))

    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ core_hittable: false, pierce_hits_body_behind_core: false }),
    )
  })
})

describe('기타 설정', () => {
  it('방어력과 전투 시간을 접되 요약에 그 값을 남긴다', () => {
    render(
      <BossProfileField value={makeDefaultBossProfileDraft('31784')} onChange={vi.fn()} />,
    )

    const details = screen.getByText(/기타 설정/).closest('details')
    expect(details).not.toBeNull()
    expect(details).not.toHaveAttribute('open')
    expect(screen.getByText(/방어력 31,784/)).toBeInTheDocument()
    expect(screen.getByText(/180초/)).toBeInTheDocument()
  })

  it('접힌 칸에 오류가 있으면 스스로 펼친다', () => {
    render(
      <BossProfileField
        value={{ ...makeDefaultBossProfileDraft(), enemy_def: '' }}
        errors={{ enemy_def: '필수 입력이에요' }}
        onChange={vi.fn()}
      />,
    )

    expect(screen.getByText(/기타 설정/).closest('details')).toHaveAttribute('open')
  })

  it('편집 중이라 비어 있는 칸은 요약에서 —로 둔다', () => {
    render(
      <BossProfileField
        value={{ ...makeDefaultBossProfileDraft(), enemy_def: '' }}
        onChange={vi.fn()}
      />,
    )

    expect(screen.getByText(/방어력 —/)).toBeInTheDocument()
  })
})

const rotation: RaidRotation = {
  id: 'union-2026-07-31',
  raid: 'union',
  title: '유니온 레이드 7/31',
  starts_at: '2026-07-31T05:00:00+09:00',
  ends_at: '2026-08-06T04:59:00+09:00',
  source_url: 'https://arca.live/b/nikketgv/177833660',
  source_locale: 'ko',
  read_on: '2026-08-07',
  bosses: [
    { name: '선바스', weakness: 'Electric', range_band: 'near', core_diameter_px: null,
      stated: { 거리: '근거리' } },
    { name: '토커티브', weakness: 'Water', range_band: 'far', core_diameter_px: null,
      stated: { 거리: '원거리' } },
  ],
}

/** 거리를 안 적는 솔로 공지에서 오는 모양. */
const soloRotation: RaidRotation = {
  ...rotation,
  id: 'solo-39',
  raid: 'solo',
  title: '솔로 레이드 39시즌',
  bosses: [{ name: '아일랜드 이터', weakness: 'Iron', range_band: null,
             core_diameter_px: null, stated: {} }],
}

describe('BossProfileField 회차 보스 피커', () => {
  it('회차가 없으면 피커를 그리지 않는다', () => {
    render(<BossProfileField value={makeDefaultBossProfileDraft()} onChange={vi.fn()} />)
    expect(screen.queryByRole('radio', { name: '전격선바스' })).not.toBeInTheDocument()
  })

  it('보스를 고르면 약점에서 역산한 보스 속성이 들어간다', async () => {
    const user = userEvent.setup()
    const onChange = vi.fn()
    render(
      <BossProfileField
        value={makeDefaultBossProfileDraft()}
        onChange={onChange}
        rotation={rotation}
      />,
    )
    await user.click(screen.getByRole('radio', { name: '전격선바스' }))
    // 약점 전격 -> 전격이 이기는 속성이 보스 본인 속성이다.
    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ element: bossElementFor('Electric') }),
    )
  })

  it('보스를 고르면 손으로 켜둔 다른 필드가 전부 초기화된다', async () => {
    // 설계 D2. 이게 없으면 화면에는 「토커티브」라고 적혀 있는데 계산은 직전 보스
    // 가정(코어 타격 가능 · 부위파괴 · 방어력)으로 돈다.
    const user = userEvent.setup()
    const onChange = vi.fn()
    const dirty = {
      ...makeDefaultBossProfileDraft(),
      core_hittable: true,
      pierce_hits_body_behind_core: true,
      part_destructible: true,
      elemental_interrupt_required: true,
      effective_range_band: 'far' as const,
      enemy_def: '99999',
      fight_duration: '240',
    }
    render(<BossProfileField value={dirty} onChange={onChange} rotation={rotation} />)
    await user.click(screen.getByRole('radio', { name: '수냉토커티브' }))
    expect(onChange).toHaveBeenCalledWith({
      ...makeDefaultBossProfileDraft(),
      element: bossElementFor('Water'),
      boss_name: '토커티브',
      effective_range_band: 'far',
    })
  })

  it('유니온 보스를 고르면 공지가 적은 적정거리가 들어간다', async () => {
    const user = userEvent.setup()
    const onChange = vi.fn()
    render(
      <BossProfileField
        value={makeDefaultBossProfileDraft()}
        onChange={onChange}
        rotation={rotation}
      />,
    )
    await user.click(screen.getByRole('radio', { name: '전격선바스' }))
    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ effective_range_band: 'near' }),
    )
  })

  it('거리를 안 적는 솔로 보스는 적정거리를 모름으로 남긴다', async () => {
    // 솔로 공지에는 「거리」 항목이 없다. 없는 값을 추측해 채우면 그 순간 아무도
    // 근거를 댈 수 없는 +30%가 평타에 붙는다.
    const user = userEvent.setup()
    const onChange = vi.fn()
    const dirty = { ...makeDefaultBossProfileDraft(), effective_range_band: 'mid' as const }
    render(<BossProfileField value={dirty} onChange={onChange} rotation={soloRotation} />)
    await user.click(screen.getByRole('radio', { name: '철갑아일랜드 이터' }))
    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ effective_range_band: null }),
    )
  })

  it('초기화되는 방어력은 호출부가 준 기본값이다', async () => {
    // 솔로와 유니온 보스는 방어력이 달라서 공유 기본값 하나로는 한쪽이 틀린다 —
    // makeDefaultBossProfileDraft가 인자를 받는 것과 같은 이유다. value와 prop을
    // 다른 값으로 둬야 pickRotationBoss가 실제로 defaultEnemyDef를 쓰는지 갈린다
    // - 둘을 같은 값으로 두면 `...value`로 초기화해도 통과해 버린다.
    const user = userEvent.setup()
    const onChange = vi.fn()
    render(
      <BossProfileField
        value={makeDefaultBossProfileDraft('99999')}
        onChange={onChange}
        rotation={rotation}
        defaultEnemyDef="31784"
      />,
    )
    await user.click(screen.getByRole('radio', { name: '전격선바스' }))
    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ enemy_def: '31784' }),
    )
  })

  it('카드를 고르면 어떻게 되는지는 보스 설정 옆 설명이 말한다', () => {
    // 카드 아래 문단으로 두면 5장 밑에 깔려 정작 읽어야 할 때 안 읽힌다.
    render(
      <BossProfileField
        value={makeDefaultBossProfileDraft()}
        onChange={vi.fn()}
        rotation={rotation}
      />,
    )
    expect(screen.getByRole('button', { name: '회차 보스 설명' })).toBeInTheDocument()
  })

  it('회차가 없으면 그 설명도 없다', () => {
    render(<BossProfileField value={makeDefaultBossProfileDraft()} onChange={vi.fn()} />)
    expect(screen.queryByRole('button', { name: '회차 보스 설명' })).not.toBeInTheDocument()
  })

  it('약점을 손으로 바꾸면 카드 선택이 풀린다', async () => {
    // 카드는 「이 보스로 계산 중」이라고 말한다. 속성이 그 보스와 달라진 뒤에도
    // 체크가 남아 있으면 화면이 거짓말을 한다.
    const user = userEvent.setup()
    const Harness = () => {
      const [draft, setDraft] = useState(makeDefaultBossProfileDraft())
      return <BossProfileField value={draft} onChange={setDraft} rotation={rotation} />
    }
    render(<Harness />)
    await user.click(screen.getByRole('radio', { name: '전격선바스' }))
    expect(screen.getByRole('radio', { name: '전격선바스' })).toBeChecked()

    await user.click(screen.getByRole('radio', { name: '작열' }))
    expect(screen.getByRole('radio', { name: '전격선바스' })).not.toBeChecked()
  })
})

describe('BossProfileField 보스 이름', () => {
  it('회차 보스를 고르면 그 이름을 draft에 담아 올린다', async () => {
    const user = userEvent.setup()
    const onChange = vi.fn()
    render(
      <BossProfileField
        value={makeDefaultBossProfileDraft()}
        onChange={onChange}
        rotation={rotation}
      />,
    )

    await user.click(screen.getByRole('radio', { name: '전격선바스' }))

    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ boss_name: '선바스' }))
  })

  // 라벨이 거짓말하지 않게 하는 가드. 이름은 그 속성의 보스를 가리켜 붙은 것이라,
  // 속성을 손으로 바꾸면 가리킬 대상이 없어진다.
  it('속성을 직접 바꾸면 보스 이름을 버린다', async () => {
    const user = userEvent.setup()
    const onChange = vi.fn()
    render(
      <BossProfileField
        value={{ ...makeDefaultBossProfileDraft(), element: 'Fire', boss_name: '선바스' }}
        onChange={onChange}
        rotation={rotation}
      />,
    )

    await user.click(screen.getByRole('radio', { name: '전격' }))

    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ boss_name: null }))
  })

  it('약점 없음을 골라도 보스 이름을 버린다', async () => {
    const user = userEvent.setup()
    const onChange = vi.fn()
    render(
      <BossProfileField
        value={{ ...makeDefaultBossProfileDraft(), element: 'Fire', boss_name: '선바스' }}
        onChange={onChange}
        rotation={rotation}
      />,
    )

    await user.click(screen.getByRole('radio', { name: '약점 없음' }))

    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ boss_name: null }))
  })
})

describe('BossProfileField 코어 지름', () => {
  it('코어 피격이 꺼져 있으면 칸이 없다', () => {
    // 엔진이 core_hittable이 거짓이면 이 값을 무시한다. 켤 수는 있는데 아무 일도
    // 안 일어나는 칸을 그리지 않는다.
    render(<BossProfileField value={makeDefaultBossProfileDraft()} onChange={vi.fn()} />)

    // 롤로 겨눈다 - /코어 지름/은 설명 버튼(「코어 지름 설명」)까지 문다.
    expect(screen.queryByRole('spinbutton', { name: /코어 지름/ })).not.toBeInTheDocument()
  })

  it('접힌 요약이 코어 지름까지 적는다 — 펼치지 않아도 무엇으로 계산되는지 보인다', () => {
    render(
      <BossProfileField
        value={{ ...makeDefaultBossProfileDraft('31784'), core_hittable: true,
                 core_diameter_px: '58.67' }}
        onChange={vi.fn()}
      />,
    )

    expect(screen.getByText(/기타 설정 — 방어력 31,784 · 180초 · 코어 58.67/))
      .toBeInTheDocument()
  })

  it('코어 피격이 꺼져 있으면 요약에 코어를 안 적는다', () => {
    render(
      <BossProfileField value={makeDefaultBossProfileDraft('31784')} onChange={vi.fn()} />,
    )

    expect(screen.getByText(/기타 설정 — 방어력 31,784 · 180초$/)).toBeInTheDocument()
  })

  it('코어 지름 오류는 접힌 상자를 강제로 펼친다', () => {
    // 제출을 막는 이유가 접힌 상자 안에 숨으면 버튼만 죽은 화면이 된다 -
    // 방어력·전투 시간이 이미 같은 규칙으로 펼쳐진다.
    const { container } = render(
      <BossProfileField
        value={{ ...makeDefaultBossProfileDraft(), core_hittable: true,
                 core_diameter_px: '0' }}
        errors={{ core_diameter_px: '0보다 커야 해요' }}
        onChange={vi.fn()}
      />,
    )

    expect(container.querySelector('details.boss-profile__folded')).toHaveAttribute('open')
  })

  it('코어 피격을 켜면 칸이 나온다', () => {
    render(
      <BossProfileField
        value={{ ...makeDefaultBossProfileDraft(), core_hittable: true }}
        onChange={vi.fn()}
      />,
    )

    expect(screen.getByRole('spinbutton', { name: /코어 지름/ })).toBeInTheDocument()
  })

  it('코어 피격을 끄면 값도 지운다 — 폼에 모순 상태를 만들지 않는다', async () => {
    // 값을 남겨 두면 화면에서 사라진 칸이 계산에는 남는다.
    const user = userEvent.setup()
    const onChange = vi.fn()
    render(
      <BossProfileField
        value={{
          ...makeDefaultBossProfileDraft(),
          core_hittable: true,
          core_diameter_px: '33.33',
        }}
        onChange={onChange}
      />,
    )

    await user.click(screen.getByLabelText('코어 타격 가능'))

    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ core_hittable: false, core_diameter_px: '' }),
    )
  })

  it('코어가 기록된 회차 보스를 고르면 값과 코어 피격이 함께 들어간다', async () => {
    // 코어 피격을 같이 켜지 않으면 엔진이 값을 무시해, 카드를 눌러도 아무 일이
    // 없는 것과 같아진다.
    const user = userEvent.setup()
    const onChange = vi.fn()
    const measured: RaidRotation = {
      ...rotation,
      bosses: rotation.bosses.map((boss) =>
        boss.name === '선바스' ? { ...boss, core_diameter_px: 58.67 } : boss,
      ),
    }
    render(
      <BossProfileField
        value={makeDefaultBossProfileDraft()}
        onChange={onChange}
        rotation={measured}
      />,
    )

    await user.click(screen.getByRole('radio', { name: '전격선바스' }))

    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ core_diameter_px: '58.67', core_hittable: true }),
    )
  })

  it('값을 넣으면 그 값이 무기별로 무엇을 뜻하는지 옆에 적는다', () => {
    // 「33.33」은 사용자에게 아무 의미가 없다. 틀린 값을 넣었을 때 조용히 덱
    // 순위만 바뀌지 않으려면 결과가 보여야 한다.
    render(
      <BossProfileField
        value={{ ...makeDefaultBossProfileDraft(), core_hittable: true,
                 core_diameter_px: '33.33' }}
        onChange={vi.fn()}
      />,
    )

    // 실측 mid 코어. 문서 표의 AR 19.8%는 자르지 않은 33.333…(=25×4/3)의 값이라
    // 여기 33.33으로는 19.7%가 맞다.
    const readout = screen.getByTestId('core-hit-rate-readout')
    expect(readout).toHaveTextContent('AR 19.7%')
    expect(readout).toHaveTextContent('SMG 9.2%')
    expect(readout).toHaveTextContent('SG 1.8%')
    expect(readout).toHaveTextContent('MG·SR·RL 100%')
  })

  it('칸이 비어 있으면 아무것도 적지 않는다', () => {
    render(
      <BossProfileField
        value={{ ...makeDefaultBossProfileDraft(), core_hittable: true }}
        onChange={vi.fn()}
      />,
    )

    expect(screen.queryByTestId('core-hit-rate-readout')).not.toBeInTheDocument()
  })

  it('값이 유효하지 않으면 아무것도 적지 않는다 — 0으로 나눈 비율을 보이지 않는다', () => {
    render(
      <BossProfileField
        value={{ ...makeDefaultBossProfileDraft(), core_hittable: true,
                 core_diameter_px: '0' }}
        onChange={vi.fn()}
      />,
    )

    expect(screen.queryByTestId('core-hit-rate-readout')).not.toBeInTheDocument()
  })

  it('코어가 없는 회차 보스를 고르면 칸이 비고 코어 피격도 꺼진다', async () => {
    const user = userEvent.setup()
    const onChange = vi.fn()
    render(
      <BossProfileField
        value={{ ...makeDefaultBossProfileDraft(), core_hittable: true,
                 core_diameter_px: '99' }}
        onChange={onChange}
        rotation={rotation}
      />,
    )

    await user.click(screen.getByRole('radio', { name: '전격선바스' }))

    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ core_diameter_px: '', core_hittable: false }),
    )
  })
})

describe('BossProfileField 화면에서 재서 넣기', () => {
  const openCore = (onChange = vi.fn()) => {
    render(
      <BossProfileField
        value={{ ...makeDefaultBossProfileDraft(), core_hittable: true }}
        onChange={onChange}
      />,
    )
    return onChange
  }

  it('코어 피격이 꺼져 있으면 계산기도 없다', () => {
    render(<BossProfileField value={makeDefaultBossProfileDraft()} onChange={vi.fn()} />)

    expect(screen.queryByRole('button', { name: '코어 지름 넣기' })).not.toBeInTheDocument()
  })

  it('두 픽셀을 넣으면 환산값을 보여준다', async () => {
    const user = userEvent.setup()
    openCore()

    await user.type(screen.getByRole('spinbutton', { name: /코어 \(px\)/ }), '25')
    await user.type(screen.getByRole('spinbutton', { name: /조준원 \(px\)/ }), '187')

    // 기본 기준자는 SG(가장 큼 = 가장 정확). 25 x 250/187 = 33.42
    expect(screen.getByTestId('core-measurement-result')).toHaveTextContent('33.42')
  })

  it('넣기를 누르면 엔진 칸이 채워진다', async () => {
    const user = userEvent.setup()
    const onChange = openCore()

    await user.type(screen.getByRole('spinbutton', { name: /코어 \(px\)/ }), '25')
    await user.type(screen.getByRole('spinbutton', { name: /조준원 \(px\)/ }), '187')
    await user.click(screen.getByRole('button', { name: '코어 지름 넣기' }))

    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ core_diameter_px: '33.42' }),
    )
  })

  it('기준자 무기를 바꾸면 값이 따라 바뀐다', async () => {
    const user = userEvent.setup()
    openCore()

    await user.type(screen.getByRole('spinbutton', { name: /코어 \(px\)/ }), '25')
    await user.type(screen.getByRole('spinbutton', { name: /조준원 \(px\)/ }), '187')
    await user.selectOptions(screen.getByRole('combobox', { name: '탄착군 측정한 무기' }), 'AR')

    // 25 x 75/187 = 10.03
    expect(screen.getByTestId('core-measurement-result')).toHaveTextContent('10.03')
  })

  it('한쪽만 채우면 결과도 없고 넣기도 막힌다', async () => {
    const user = userEvent.setup()
    openCore()

    await user.type(screen.getByRole('spinbutton', { name: /코어 \(px\)/ }), '25')

    expect(screen.queryByTestId('core-measurement-result')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: '코어 지름 넣기' })).toBeDisabled()
  })

  it('탄착군 10짜리 무기는 기준자로 고를 수 없다 — 판독 오차가 13%다', () => {
    openCore()

    const options = [...screen.getByRole('combobox', { name: '탄착군 측정한 무기' })
      .querySelectorAll('option')].map((o) => o.value)
    expect(options).toEqual(['SG', 'SMG', 'AR'])
  })
})

describe('BossProfileField 접기', () => {
  // 머리는 늘 bossHeading이 정한다 - 펼쳐져 있을 때도 같은 이름이다.
  const toggle = (name: string) => screen.getByRole('button', { name })

  it('처음에는 펼쳐져 있다', () => {
    render(<BossProfileField value={makeDefaultBossProfileDraft()} onChange={vi.fn()} />)

    expect(toggle('보스 설정')).toHaveAttribute('aria-expanded', 'true')
    expect(screen.getByRole('radiogroup', { name: '보스 약점 속성' })).toBeInTheDocument()
  })

  it('접으면 본문이 사라진다', async () => {
    const user = userEvent.setup()
    render(
      <BossProfileField
        value={{ ...makeDefaultBossProfileDraft(), element: 'Fire', boss_name: '선바스' }}
        onChange={vi.fn()}
      />,
    )

    await user.click(toggle('선바스'))

    expect(toggle('선바스')).toHaveAttribute('aria-expanded', 'false')
    expect(screen.queryByRole('radiogroup', { name: '보스 약점 속성' })).not.toBeInTheDocument()
    // getByLabelText는 라벨 전체 텍스트("전투 시간 초")와 정확히 맞아야 하므로 롤로 겨눈다.
    expect(screen.queryByLabelText(/전투 시간/)).not.toBeInTheDocument()
  })

  it('보스를 골랐으면 그 이름으로 부른다', () => {
    render(
      <BossProfileField
        value={{ ...makeDefaultBossProfileDraft(), element: 'Fire', boss_name: '선바스' }}
        onChange={vi.fn()}
      />,
    )
    expect(toggle('선바스')).toBeInTheDocument()
  })

  it('이름이 없으면 약점 이름으로 부른다', () => {
    render(
      <BossProfileField
        value={{ ...makeDefaultBossProfileDraft(), element: 'Fire' }}
        onChange={vi.fn()}
      />,
    )
    expect(toggle('수냉')).toBeInTheDocument()
  })

  it('이름도 속성도 없으면 보스 설정이라고 부른다', () => {
    render(<BossProfileField value={makeDefaultBossProfileDraft()} onChange={vi.fn()} />)
    expect(toggle('보스 설정')).toBeInTheDocument()
  })

  // 접힌 안에 오류가 숨으면 계산이 이유 없이 안 되는 것처럼 보인다.
  it('오류가 있으면 접혀 있어도 펼친다', async () => {
    const user = userEvent.setup()
    const view = render(
      <BossProfileField value={makeDefaultBossProfileDraft()} errors={{}} onChange={vi.fn()} />,
    )

    await user.click(toggle('보스 설정'))
    expect(screen.queryByRole('radiogroup', { name: '보스 약점 속성' })).not.toBeInTheDocument()

    view.rerender(
      <BossProfileField
        value={makeDefaultBossProfileDraft()}
        errors={{ fight_duration: '0보다 커야 해요' }}
        onChange={() => {}}
      />,
    )

    expect(screen.getByText('0보다 커야 해요')).toBeInTheDocument()
    expect(screen.getByRole('radiogroup', { name: '보스 약점 속성' })).toBeInTheDocument()
    expect(toggle('보스 설정')).toHaveAttribute('aria-expanded', 'true')
  })

  it('회차 보스 설명 버튼을 눌러도 접힘 상태는 안 바뀐다', async () => {
    // HelpTip이 접기 버튼 안에 있으면 버튼 안의 버튼이 되어, 이 클릭이 접기까지 토글한다.
    const user = userEvent.setup()
    render(
      <BossProfileField
        value={makeDefaultBossProfileDraft()}
        onChange={vi.fn()}
        rotation={rotation}
      />,
    )

    await user.click(screen.getByRole('button', { name: '회차 보스 설명' }))

    expect(toggle('보스 설정')).toHaveAttribute('aria-expanded', 'true')
  })
})

describe('BossProfileField 코어 지름', () => {
  const renderWithCore = () =>
    render(
      <BossProfileField
        value={{ ...makeDefaultBossProfileDraft(), core_hittable: true }}
        onChange={vi.fn()}
      />,
    )

  it('소수를 받는다 - 바로 아래 계산기가 소수를 채우기 때문이다', () => {
    // 「화면에서 재서 넣기」는 toFixed(2)로 87.50 같은 값을 넣고, 백엔드도
    // core_diameter_px를 float으로 받는다. 이 칸이 정수만 받으면 폼이 자기
    // 도구가 채운 값을 거부한다("가장 근접한 유효 값 2개는 87 및 88입니다").
    renderWithCore()

    const input = screen.getByRole('spinbutton', { name: /코어 지름/ }) as HTMLInputElement

    expect(input.getAttribute('step')).toBe('any')
  })

  it('계산기가 채우는 소수가 실제로 유효하다', () => {
    // 위 단언은 속성을 보고, 이쪽은 제약 검증에 물어본다 - 제출을 막는 것은
    // 속성이 아니라 검증이다.
    renderWithCore()

    const input = screen.getByRole('spinbutton', { name: /코어 지름/ }) as HTMLInputElement
    input.value = '87.50'

    expect(input.validity.stepMismatch).toBe(false)
    expect(input.checkValidity()).toBe(true)
  })
})
