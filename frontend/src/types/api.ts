// Risk Level enum
export type RiskLevel = 'GREEN' | 'YELLOW' | 'RED'

// Sport Type enum
export type SportType =
  | 'running'
  | 'cycling'
  | 'swimming'
  | 'strength'
  | 'hiit'
  | 'yoga'
  | 'other'

// Intensity Zone enum
export type IntensityZone = 'Z1' | 'Z2' | 'Z3' | 'Z4' | 'Z5'

// Planned Session
export interface PlannedSessionCreate {
  sport_type: SportType
  planned_duration_minutes: number
  planned_intensity: IntensityZone
  scheduled_date: string // ISO date string
  notes?: string
}

// Symptom Input
export interface SymptomCreate {
  date: string // ISO date string
  pain_score?: number // 0-10
  pain_location?: string
  swelling?: boolean
  muscle_soreness?: number // 0-10
  fatigue_level?: number // 0-10
  sleep_quality?: number // 0-10
  perceived_readiness?: number // 0-10
  notes?: string
}

// Alternative Session Recommendation
export interface AlternativeSession {
  sport_type: SportType
  duration_minutes: number
  intensity: IntensityZone
  rationale: string
}

// Factor Contribution
export interface FactorContribution {
  factor: string
  contribution: number
  description: string
}

// Safety Rule Result
export interface SafetyRuleResult {
  rule_id: string
  triggered: boolean
  message?: string
  override_risk_level?: RiskLevel
}

// Prediction Response
export interface PredictionResponse {
  risk_score: number
  risk_level: RiskLevel
  confidence: number
  top_factors: FactorContribution[]
  safety_rules_triggered: SafetyRuleResult[]
  alternatives: AlternativeSession[]
  explanation: string
  breakdown?: {
    hrv_contribution: number
    rhr_contribution: number
    sleep_contribution: number
    acwr_contribution: number
    symptom_contribution: number
    session_contribution: number
    base_score: number
  }
}

// Import Result
export interface ImportResult {
  success: boolean
  message: string
  workouts_imported: number
  workouts_skipped: number
  metrics_imported: number
  errors: string[]
}

// Workout Response
export interface WorkoutResponse {
  id: number
  sport_type: SportType
  start_time: string
  duration_minutes: number
  distance_meters?: number
  avg_heart_rate?: number
  max_heart_rate?: number
  calories?: number
  trimp?: number
  intensity_zone: IntensityZone
  source: string
}

// Daily Metrics Response
export interface DailyMetricsResponse {
  id: number
  date: string
  hrv_rmssd?: number
  hrv_score?: number
  resting_hr?: number
  sleep_duration_minutes?: number
  sleep_score?: number
  readiness_score?: number
  stress_score?: number
}
