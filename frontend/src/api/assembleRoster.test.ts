import { afterEach, describe, expect, it, vi } from 'vitest'
import { assembleRoster } from './assembleRoster'
import { AssembleRosterApiError } from './assembleRosterApiError'
import { getClientId } from '../lib/clientId'

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
    expect(init.headers['X-Client-Id']).toBe(getClientId())
  })

  it('실패 응답은 상태와 detail을 담은 에러로 올린다', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false,
      status: 422,
      json: async () => ({ detail: [{ msg: 'field required', loc: ['body', 'owned'], type: 'missing' }] }),
    }))

    const err: unknown = await assembleRoster(payload).catch((e) => e)

    expect(err).toBeInstanceOf(AssembleRosterApiError)
    const apiErr = err as AssembleRosterApiError
    expect(apiErr.status).toBe(422)
    expect(apiErr.detail).toEqual({
      detail: [{ msg: 'field required', loc: ['body', 'owned'], type: 'missing' }],
    })
  })
})
