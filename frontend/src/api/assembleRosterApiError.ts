// Typed error thrown by the assemble-roster API client on a non-2xx
// response. Sibling to RecommendApiError (recommendApiError.ts), not a
// reuse of it: assemble-roster is a different endpoint domain (stateless
// roster sync, not deck recommendation), so its message and eventual
// user-facing detail formatting shouldn't be tied to the recommend clients'.
// `detail` is the parsed JSON response body, or null when the body wasn't
// JSON — FastAPI's default shape for a 422 is `{ detail: [{ msg, loc, type }, ...] }`.

export class AssembleRosterApiError extends Error {
  readonly status: number
  readonly detail: unknown

  constructor(status: number, detail: unknown) {
    super(`assemble-roster request failed with status ${status}`)
    this.name = 'AssembleRosterApiError'
    this.status = status
    this.detail = detail
  }
}

const extractDetailMessage = (detail: unknown): string | undefined => {
  if (detail == null || typeof detail !== 'object') return undefined
  const inner = (detail as Record<string, unknown>).detail
  if (typeof inner === 'string') return inner
  if (Array.isArray(inner)) {
    const messages = inner
      .map((item) =>
        item && typeof item === 'object' && 'msg' in item
          ? String((item as { msg: unknown }).msg)
          : undefined,
      )
      .filter((msg): msg is string => msg != null)
    if (messages.length > 0) return messages.join('; ')
  }
  return undefined
}

/** A user-facing message for an AssembleRosterApiError, preferring the backend's own detail. */
export const describeAssembleRosterApiError = (err: AssembleRosterApiError): string => {
  const detailMessage = extractDetailMessage(err.detail)
  if (err.status === 422) {
    return detailMessage ?? 'The blablalink payload was not in the expected shape.'
  }
  return detailMessage ?? `Roster sync failed (${err.status}).`
}
