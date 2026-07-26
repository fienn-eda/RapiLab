import { describe, expect, it } from 'vitest'
import { parseShareUrl } from './shareUrl'

// uid는 "<shiftypad_region_id>-<intl_open_id>"의 base64. 앞자리는 ShiftyPad
// 리전 id이지 API의 nikke_area_id(81 고정)가 아니다.
const uid = btoa('29080-1234567890123456789')

describe('parseShareUrl', () => {
  it('대시 뒤 open_id만 취한다', () => {
    expect(parseShareUrl(`https://www.blablalink.com/shiftyspad?uid=${uid}`))
      .toBe('1234567890123456789')
  })

  it('open_id를 직접 붙여넣어도 받는다', () => {
    expect(parseShareUrl('1234567890123456789')).toBe('1234567890123456789')
  })

  it('uid가 없으면 거부한다', () => {
    expect(() => parseShareUrl('https://www.blablalink.com/shiftyspad'))
      .toThrow(/공유 URL/i)
  })

  it('디코드 결과가 예상 형태가 아니면 거부한다', () => {
    expect(() => parseShareUrl(`https://www.blablalink.com/shiftyspad?uid=${btoa('junk')}`))
      .toThrow(/공유 URL/i)
  })
})
