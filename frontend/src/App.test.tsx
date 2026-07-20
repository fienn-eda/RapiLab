import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import App from './App'

describe('App', () => {
  it('states the harmony cube assumption', () => {
    render(<App />)
    expect(screen.getByText(/Resilience Cube Lv\.15/i)).toBeInTheDocument()
  })
})
