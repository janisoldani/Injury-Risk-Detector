import { describe, it, expect } from 'vitest'
import { getPrediction, getImportStats, getWorkouts } from './api'

describe('API Client', () => {
  it('fetches prediction successfully', async () => {
    const prediction = await getPrediction()

    expect(prediction.risk_score).toBe(35)
    expect(prediction.risk_level).toBe('GREEN')
    expect(prediction.confidence).toBe(0.85)
    expect(prediction.top_factors).toHaveLength(1)
  })

  it('fetches prediction with planned session', async () => {
    const prediction = await getPrediction({
      sport_type: 'running',
      planned_duration_minutes: 60,
      planned_intensity: 'Z3',
      scheduled_date: '2024-01-20',
    })

    expect(prediction.risk_score).toBeDefined()
    expect(prediction.risk_level).toBeDefined()
  })

  it('fetches import stats', async () => {
    const stats = await getImportStats()

    expect(stats.total_workouts).toBe(10)
    expect(stats.total_metrics).toBe(28)
    expect(stats.date_range).toBeDefined()
    expect(stats.date_range?.earliest).toBe('2024-01-01')
  })

  it('fetches workouts list', async () => {
    const workouts = await getWorkouts()

    expect(workouts).toHaveLength(1)
    expect(workouts[0].sport_type).toBe('running')
    expect(workouts[0].duration_minutes).toBe(45)
    expect(workouts[0].trimp).toBe(67)
  })
})
