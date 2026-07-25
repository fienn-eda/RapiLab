import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { FavoriteItemBadge } from './FavoriteItemBadge'

describe('FavoriteItemBadge', () => {
  it('draws a heart when the Favorite Item is equipped', () => {
    render(<FavoriteItemBadge equipped />)
    expect(screen.getByTitle('애장품 장착')).toHaveTextContent('♥')
  })

  it('draws nothing when it is not equipped', () => {
    const { container } = render(<FavoriteItemBadge equipped={false} />)
    expect(container).toBeEmptyDOMElement()
  })

  // Absent is not false: a manually entered draft was never told either way,
  // and a heart-shaped "no" would claim a fact the roster never reported.
  it('draws nothing when the roster never said', () => {
    const { container } = render(<FavoriteItemBadge />)
    expect(container).toBeEmptyDOMElement()
  })
})
