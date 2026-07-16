import { describe, it, expect } from 'vitest'
import { describeRecommendApiError, RecommendApiError } from './recommendApiError'

describe('describeRecommendApiError', () => {
  it('surfaces a string detail from a 422 response', () => {
    const err = new RecommendApiError(422, { detail: 'No feasible 5-unit deck.' })
    expect(describeRecommendApiError(err)).toBe('No feasible 5-unit deck.')
  })

  it('joins a FastAPI validation error array into one message', () => {
    const err = new RecommendApiError(422, {
      detail: [
        { loc: ['body', 'boss', 'enemy_def'], msg: 'ensure this value is >= 0', type: 'value_error' },
        { loc: ['body', 'roster'], msg: 'field required', type: 'value_error.missing' },
      ],
    })
    expect(describeRecommendApiError(err)).toBe(
      'ensure this value is >= 0; field required',
    )
  })

  it('falls back to a generic 422 message when there is no parseable detail', () => {
    const err = new RecommendApiError(422, null)
    expect(describeRecommendApiError(err)).toBe(
      'The roster or boss profile is invalid for a deck recommendation.',
    )
  })

  it('falls back to a generic status message for non-422 errors without detail', () => {
    const err = new RecommendApiError(500, null)
    expect(describeRecommendApiError(err)).toBe('Deck recommendation request failed (500).')
  })

  it('prefers a string detail even for a non-422 status', () => {
    const err = new RecommendApiError(500, { detail: 'Internal error' })
    expect(describeRecommendApiError(err)).toBe('Internal error')
  })
})
