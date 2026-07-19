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
