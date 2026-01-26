import axios from 'axios'
import type {
  PredictionResponse,
  PlannedSessionCreate,
  SymptomCreate,
  ImportResult,
  WorkoutResponse,
  DailyMetricsResponse,
  UserResponse,
  UserUpdate,
} from '../types/api'

const api = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
})

// Default user ID for MVP (can be overridden via context)
let currentUserId = 1

export function setCurrentUserId(userId: number): void {
  currentUserId = userId
}

export function getCurrentUserId(): number {
  return currentUserId
}

// Predictions
export async function getPrediction(
  plannedSession?: PlannedSessionCreate,
  userId?: number
): Promise<PredictionResponse> {
  const uid = userId ?? currentUserId
  const response = await api.post(`/predictions/${uid}`, plannedSession || {})
  return response.data
}

// Planned Sessions
export async function createPlannedSession(
  session: PlannedSessionCreate,
  userId?: number
): Promise<{ id: number }> {
  const uid = userId ?? currentUserId
  const response = await api.post(`/planned-sessions/${uid}`, session)
  return response.data
}

export async function getPlannedSessions(userId?: number): Promise<PlannedSessionCreate[]> {
  const uid = userId ?? currentUserId
  const response = await api.get(`/planned-sessions/${uid}`)
  return response.data
}

// Symptoms
export async function createSymptom(
  symptom: SymptomCreate,
  userId?: number
): Promise<{ id: number }> {
  const uid = userId ?? currentUserId
  const response = await api.post(`/symptoms/${uid}`, symptom)
  return response.data
}

export async function getTodaySymptoms(userId?: number): Promise<SymptomCreate | null> {
  const uid = userId ?? currentUserId
  const response = await api.get(`/symptoms/${uid}/today`)
  return response.data
}

// FIT File Import
export async function uploadFitFile(file: File, userId?: number): Promise<ImportResult> {
  const uid = userId ?? currentUserId
  const formData = new FormData()
  formData.append('file', file)
  const response = await api.post(`/imports/fit?user_id=${uid}`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  })
  return response.data
}

export async function getImportStats(userId?: number): Promise<{
  total_workouts: number
  total_metrics: number
  date_range: { earliest: string; latest: string } | null
}> {
  const uid = userId ?? currentUserId
  const response = await api.get(`/imports/stats/${uid}`)
  return response.data
}

// Workouts
export async function getWorkouts(
  skip = 0,
  limit = 50,
  userId?: number
): Promise<WorkoutResponse[]> {
  const uid = userId ?? currentUserId
  const response = await api.get(`/workouts/${uid}?skip=${skip}&limit=${limit}`)
  return response.data
}

// Daily Metrics
export async function getDailyMetrics(days = 28, userId?: number): Promise<DailyMetricsResponse[]> {
  const uid = userId ?? currentUserId
  const response = await api.get(`/users/${uid}/metrics?days=${days}`)
  return response.data
}

// User Profile
export async function getUser(userId?: number): Promise<UserResponse> {
  const uid = userId ?? currentUserId
  const response = await api.get(`/users/${uid}`)
  return response.data
}

export async function updateUser(data: UserUpdate): Promise<UserResponse> {
  const response = await api.patch(`/users/me`, data)
  return response.data
}

export default api
