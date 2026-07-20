import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { InvestmentBadge } from './InvestmentBadge'

describe('InvestmentBadge', () => {
  it('fills one star per breakthrough and appends the core count', () => {
    render(<InvestmentBadge grade={3} core={7} />)
    expect(screen.getByText('★★★')).toBeInTheDocument()
    expect(screen.getByText('+7')).toBeInTheDocument()
  })

  it('omits the core count when core is zero', () => {
    render(<InvestmentBadge grade={3} core={0} />)
    expect(screen.getByText('★★★')).toBeInTheDocument()
    expect(screen.queryByText(/^\+/)).toBeNull()
  })

  it('shows empty stars for a partially broken-through unit', () => {
    render(<InvestmentBadge grade={2} core={0} />)
    expect(screen.getByText('★★☆')).toBeInTheDocument()
  })

  it('shows three empty stars for a genuinely zero-breakthrough unit', () => {
    render(<InvestmentBadge grade={0} core={0} />)
    expect(screen.getByText('☆☆☆')).toBeInTheDocument()
  })

  it('renders nothing when grade is unknown, rather than claiming zero', () => {
    // A manually entered draft carries no grade/core. Drawing ☆☆☆ for it would
    // assert "zero breakthrough" about a unit we have no data for. This is the
    // one distinction the whole design turns on - do not collapse it into the
    // grade=0 case above.
    const { container } = render(<InvestmentBadge />)
    expect(container).toBeEmptyDOMElement()
  })
})
