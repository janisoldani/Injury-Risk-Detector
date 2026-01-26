import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import RiskGauge from './RiskGauge'

describe('RiskGauge', () => {
  it('renders the risk score', () => {
    render(<RiskGauge score={35} level="GREEN" />)
    expect(screen.getByText('35')).toBeInTheDocument()
  })

  it('displays "Low Risk" for GREEN level', () => {
    render(<RiskGauge score={25} level="GREEN" />)
    expect(screen.getByText('Low Risk')).toBeInTheDocument()
  })

  it('displays "Moderate Risk" for YELLOW level', () => {
    render(<RiskGauge score={55} level="YELLOW" />)
    expect(screen.getByText('Moderate Risk')).toBeInTheDocument()
  })

  it('displays "High Risk" for RED level', () => {
    render(<RiskGauge score={85} level="RED" />)
    expect(screen.getByText('High Risk')).toBeInTheDocument()
  })

  it('clamps score to 0-100 range', () => {
    const { rerender } = render(<RiskGauge score={-10} level="GREEN" />)
    expect(screen.getByText('0')).toBeInTheDocument()

    rerender(<RiskGauge score={150} level="RED" />)
    expect(screen.getByText('100')).toBeInTheDocument()
  })

  it('renders different sizes', () => {
    const { rerender } = render(<RiskGauge score={50} level="YELLOW" size="sm" />)
    expect(screen.getByText('50')).toBeInTheDocument()

    rerender(<RiskGauge score={50} level="YELLOW" size="lg" />)
    expect(screen.getByText('50')).toBeInTheDocument()
  })
})
