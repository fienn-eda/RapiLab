import { describe, it, expect } from 'vitest'
import { AssembleRosterApiError, describeAssembleRosterApiError } from './assembleRosterApiError'

describe('describeAssembleRosterApiError', () => {
  it('surfaces a string detail from a 422 response', () => {
    const err = new AssembleRosterApiError(422, { detail: 'owned[3].name_code is missing.' })
    expect(describeAssembleRosterApiError(err)).toBe('owned[3].name_code is missing.')
  })

  it('joins a FastAPI validation error array into one message, naming the offending field path', () => {
    const err = new AssembleRosterApiError(422, {
      detail: [
        { loc: ['body', 'owned', 0, 'name_code'], msg: 'field required', type: 'missing' },
        { loc: ['body', 'character_details'], msg: 'field required', type: 'missing' },
      ],
    })
    expect(describeAssembleRosterApiError(err)).toBe(
      'owned.0.name_code: field required; character_details: field required',
    )
  })

  it('falls back to the bare msg when a validation entry has no loc', () => {
    const err = new AssembleRosterApiError(422, {
      detail: [{ msg: 'field required', type: 'missing' }],
    })
    expect(describeAssembleRosterApiError(err)).toBe('field required')
  })

  it('falls back to a generic 422 message when there is no parseable detail', () => {
    const err = new AssembleRosterApiError(422, null)
    expect(describeAssembleRosterApiError(err)).toBe(
      'The blablalink payload was not in the expected shape.',
    )
  })

  it('falls back to a generic status message for non-422 errors without detail', () => {
    const err = new AssembleRosterApiError(500, null)
    expect(describeAssembleRosterApiError(err)).toBe('Roster sync failed (500).')
  })

  it('prefers a string detail even for a non-422 status', () => {
    const err = new AssembleRosterApiError(500, { detail: 'Internal error' })
    expect(describeAssembleRosterApiError(err)).toBe('Internal error')
  })
})
