import { afterEach, describe, expect, it, vi } from 'vitest'
import { assembleRoster } from './assembleRoster'

const payload = { owned: [], character_details: [], recycle_room_researches: [] }

afterEach(() => vi.restoreAllMocks())

describe('assembleRoster', () => {
  it('익명 id 헤더를 붙여 POST한다', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true, json: async () => ({ units: [] }),
    })
    vi.stubGlobal('fetch', fetchMock)

    await assembleRoster(payload)

    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/assemble-roster')
    expect(init.method).toBe('POST')
    expect(init.headers['X-Client-Id']).toMatch(/^[0-9a-f-]{36}$/)
  })

  it('실패 응답은 에러로 올린다', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 422 }))
    await expect(assembleRoster(payload)).rejects.toThrow(/422/)
  })
})
