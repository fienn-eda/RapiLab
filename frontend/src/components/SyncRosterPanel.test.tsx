import { render, screen, fireEvent } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { SyncRosterPanel } from './SyncRosterPanel'

const uid = btoa('29080-1234567890123456789')
const shareUrl = `https://www.blablalink.com/shiftyspad?uid=${uid}`

describe('SyncRosterPanel', () => {
  it('공유 URL을 넣으면 북마크릿 링크가 나온다', () => {
    render(<SyncRosterPanel onImport={vi.fn()} />)
    fireEvent.change(screen.getByLabelText(/share url/i), {
      target: { value: shareUrl },
    })
    const link = screen.getByRole('link', { name: /roster/i })
    expect(link.getAttribute('href')).toContain('javascript:')
    expect(link.getAttribute('href')).toContain('1234567890123456789')
  })

  it('잘못된 URL은 에러를 보여주고 링크를 만들지 않는다', () => {
    render(<SyncRosterPanel onImport={vi.fn()} />)
    fireEvent.change(screen.getByLabelText(/share url/i), {
      target: { value: 'https://example.com' },
    })
    expect(screen.getByRole('alert')).toBeTruthy()
    expect(screen.queryByRole('link', { name: /roster/i })).toBeNull()
  })
})
