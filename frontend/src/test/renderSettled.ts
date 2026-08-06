import { act, render } from '@testing-library/react'

/** Render, then let the panel's mount-time async work settle.
 *
 * Several panels ask for something on mount - the supported-unit list, the
 * engine version - and the mocked call resolves a microtask later. A test that
 * asserts synchronously and ends leaves that state update outside act(), which
 * React reports on stderr; this suite's output is meant to be clean, so the
 * report is a defect even though nothing fails.
 *
 * Tests that await a user interaction flush the pending work on their own and
 * need nothing from this. Use it for the ones that only render and assert.
 */
export const renderSettled = async (ui: Parameters<typeof render>[0]) => {
  const rendered = render(ui)
  await act(async () => {})
  return rendered
}
