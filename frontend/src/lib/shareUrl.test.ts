import { describe, expect, it } from 'vitest'
import { parseShareUrl } from './shareUrl'

// uid는 "<앞자리>-<intl_open_id>"의 base64. 앞자리는 API의 nikke_area_id가
// 아니고, 계정의 서버 리전도 여기서는 알 수 없다.
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
