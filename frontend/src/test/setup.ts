import '@testing-library/jest-dom'
import { afterAll, afterEach, beforeAll } from 'vitest'
import { setupServer } from 'msw/node'
import { http, HttpResponse } from 'msw'

// Mock API handlers
export const handlers = [
  // Mock prediction endpoint
  http.post('/api/v1/predictions/:userId', () => {
    return HttpResponse.json({
      risk_score: 35,
      risk_level: 'GREEN',
      confidence: 0.85,
      top_factors: [
        {
          factor: 'HRV',
          contribution: -5,
          description: 'HRV is within normal range',
        },
      ],
      safety_rules_triggered: [],
      alternatives: [],
      explanation: 'Your metrics look good. Low injury risk detected.',
      breakdown: {
        hrv_contribution: 0,
        rhr_contribution: 5,
        sleep_contribution: 10,
        acwr_contribution: 10,
        symptom_contribution: 0,
        session_contribution: 10,
        base_score: 0,
      },
    })
  }),

  // Mock import stats endpoint
  http.get('/api/v1/imports/stats/:userId', () => {
    return HttpResponse.json({
      total_workouts: 10,
      total_metrics: 28,
      date_range: {
        earliest: '2024-01-01',
        latest: '2024-01-28',
      },
    })
  }),

  // Mock workouts endpoint
  http.get('/api/v1/workouts/:userId', () => {
    return HttpResponse.json([
      {
        id: 1,
        sport_type: 'running',
        start_time: '2024-01-15T08:00:00Z',
        duration_minutes: 45,
        distance_meters: 8000,
        avg_heart_rate: 145,
        max_heart_rate: 165,
        calories: 450,
        trimp: 67,
        intensity_zone: 'Z2',
        source: 'garmin',
      },
    ])
  }),

  // Mock daily metrics endpoint
  http.get('/api/v1/users/:userId/metrics', () => {
    return HttpResponse.json([
      {
        id: 1,
        date: '2024-01-15',
        hrv_rmssd: 45,
        resting_hr: 58,
        sleep_duration_minutes: 450,
        sleep_score: 85,
      },
    ])
  }),
]

export const server = setupServer(...handlers)

// Start server before all tests
beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))

// Reset handlers after each test
afterEach(() => server.resetHandlers())

// Clean up after all tests
afterAll(() => server.close())
