import { useState, useEffect } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { Calendar, Clock, Zap, AlertCircle, CheckCircle } from 'lucide-react'
import RiskGauge from '../components/RiskGauge'
import { getPrediction, createPlannedSession } from '../lib/api'
import { useToast } from '../context/ToastContext'
import type { PlannedSessionCreate, SportType, IntensityZone } from '../types/api'

const sportOptions: { value: SportType; label: string; icon: string }[] = [
  { value: 'running', label: 'Running', icon: '🏃' },
  { value: 'cycling', label: 'Cycling', icon: '🚴' },
  { value: 'swimming', label: 'Swimming', icon: '🏊' },
  { value: 'strength', label: 'Strength', icon: '🏋️' },
  { value: 'hiit', label: 'HIIT', icon: '⚡' },
  { value: 'yoga', label: 'Yoga', icon: '🧘' },
  { value: 'other', label: 'Other', icon: '🎯' },
]

const intensityOptions: { value: IntensityZone; label: string; description: string }[] = [
  { value: 'Z1', label: 'Zone 1 - Recovery', description: '50-60% max HR' },
  { value: 'Z2', label: 'Zone 2 - Endurance', description: '60-70% max HR' },
  { value: 'Z3', label: 'Zone 3 - Tempo', description: '70-80% max HR' },
  { value: 'Z4', label: 'Zone 4 - Threshold', description: '80-90% max HR' },
  { value: 'Z5', label: 'Zone 5 - VO2max', description: '90-100% max HR' },
]

const durationOptions = [15, 30, 45, 60, 75, 90, 120]

export default function SessionPlanner() {
  const toast = useToast()
  const [session, setSession] = useState<PlannedSessionCreate>({
    sport_type: 'running',
    planned_duration_minutes: 45,
    planned_intensity: 'Z2',
    scheduled_date: new Date().toISOString().split('T')[0],
  })

  const [debouncedSession, setDebouncedSession] = useState(session)

  // Debounce session changes for prediction
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSession(session)
    }, 500)
    return () => clearTimeout(timer)
  }, [session])

  // Real-time prediction based on planned session
  const { data: prediction, isLoading: isPredicting, error: predictionError } = useQuery({
    queryKey: ['prediction', 'session', debouncedSession],
    queryFn: () => getPrediction(debouncedSession),
    refetchOnWindowFocus: false,
  })

  // Show error toast when prediction fails
  useEffect(() => {
    if (predictionError) {
      toast.error('Failed to calculate risk. Please check your connection.')
    }
  }, [predictionError, toast])

  // Save session mutation
  const saveMutation = useMutation({
    mutationFn: (session: PlannedSessionCreate) => createPlannedSession(session),
    onSuccess: () => {
      toast.success('Session saved successfully!')
    },
    onError: () => {
      toast.error('Failed to save session. Please try again.')
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    saveMutation.mutate(session)
  }

  return (
    <div className="sm:ml-64 space-y-6 pb-20 sm:pb-0">
      <h1 className="text-2xl font-bold text-gray-900">Plan Your Session</h1>

      <div className="grid lg:grid-cols-2 gap-6">
        {/* Session Form */}
        <div className="card">
          <h2 className="text-lg font-semibold text-gray-900 mb-6">
            Session Details
          </h2>
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Sport Type */}
            <div>
              <label className="label">Sport Type</label>
              <div className="grid grid-cols-4 gap-2">
                {sportOptions.map((sport) => (
                  <button
                    key={sport.value}
                    type="button"
                    onClick={() => setSession({ ...session, sport_type: sport.value })}
                    className={`flex flex-col items-center p-3 rounded-lg border-2 transition-colors ${
                      session.sport_type === sport.value
                        ? 'border-blue-500 bg-blue-50'
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    <span className="text-2xl">{sport.icon}</span>
                    <span className="text-xs mt-1 text-gray-600">{sport.label}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Duration */}
            <div>
              <label className="label">
                <Clock className="inline h-4 w-4 mr-1" />
                Duration (minutes)
              </label>
              <div className="flex flex-wrap gap-2">
                {durationOptions.map((duration) => (
                  <button
                    key={duration}
                    type="button"
                    onClick={() =>
                      setSession({ ...session, planned_duration_minutes: duration })
                    }
                    className={`px-4 py-2 rounded-lg border-2 font-medium transition-colors ${
                      session.planned_duration_minutes === duration
                        ? 'border-blue-500 bg-blue-50 text-blue-700'
                        : 'border-gray-200 hover:border-gray-300 text-gray-700'
                    }`}
                  >
                    {duration}
                  </button>
                ))}
              </div>
            </div>

            {/* Intensity */}
            <div>
              <label className="label">
                <Zap className="inline h-4 w-4 mr-1" />
                Intensity Zone
              </label>
              <div className="space-y-2">
                {intensityOptions.map((intensity) => (
                  <button
                    key={intensity.value}
                    type="button"
                    onClick={() =>
                      setSession({ ...session, planned_intensity: intensity.value })
                    }
                    className={`w-full text-left px-4 py-3 rounded-lg border-2 transition-colors ${
                      session.planned_intensity === intensity.value
                        ? 'border-blue-500 bg-blue-50'
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    <div className="font-medium text-gray-900">{intensity.label}</div>
                    <div className="text-sm text-gray-500">{intensity.description}</div>
                  </button>
                ))}
              </div>
            </div>

            {/* Date */}
            <div>
              <label className="label">
                <Calendar className="inline h-4 w-4 mr-1" />
                Scheduled Date
              </label>
              <input
                type="date"
                value={session.scheduled_date}
                onChange={(e) =>
                  setSession({ ...session, scheduled_date: e.target.value })
                }
                className="input"
              />
            </div>

            {/* Save Button */}
            <button
              type="submit"
              disabled={saveMutation.isPending}
              className="btn-primary w-full"
            >
              {saveMutation.isPending ? 'Saving...' : 'Save Session'}
            </button>
          </form>
        </div>

        {/* Real-time Risk Preview */}
        <div className="card">
          <h2 className="text-lg font-semibold text-gray-900 mb-6">
            Risk Preview
          </h2>

          {isPredicting ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-pulse text-gray-500">Calculating...</div>
            </div>
          ) : prediction ? (
            <div className="space-y-6">
              <div className="flex justify-center">
                <RiskGauge
                  score={prediction.risk_score}
                  level={prediction.risk_level}
                  size="md"
                />
              </div>

              {/* Safety Alerts */}
              {prediction.safety_rules_triggered.some((r) => r.triggered) && (
                <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
                  <div className="flex items-center gap-2 text-red-700 font-medium">
                    <AlertCircle className="h-5 w-5" />
                    Safety Concerns
                  </div>
                  <ul className="mt-2 space-y-1 text-sm text-red-600">
                    {prediction.safety_rules_triggered
                      .filter((r) => r.triggered)
                      .map((rule) => (
                        <li key={rule.rule_id}>• {rule.message}</li>
                      ))}
                  </ul>
                </div>
              )}

              {/* Green Light */}
              {prediction.risk_level === 'GREEN' && (
                <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
                  <div className="flex items-center gap-2 text-green-700 font-medium">
                    <CheckCircle className="h-5 w-5" />
                    Good to Go!
                  </div>
                  <p className="mt-1 text-sm text-green-600">
                    This session looks safe based on your current metrics.
                  </p>
                </div>
              )}

              {/* Explanation */}
              <p className="text-gray-600 text-sm">{prediction.explanation}</p>

              {/* Alternatives */}
              {prediction.alternatives.length > 0 &&
                prediction.risk_level !== 'GREEN' && (
                  <div>
                    <h3 className="font-medium text-gray-900 mb-2">
                      Consider Instead:
                    </h3>
                    <div className="space-y-2">
                      {prediction.alternatives.map((alt, i) => (
                        <button
                          key={i}
                          onClick={() =>
                            setSession({
                              ...session,
                              sport_type: alt.sport_type,
                              planned_duration_minutes: alt.duration_minutes,
                              planned_intensity: alt.intensity,
                            })
                          }
                          className="w-full text-left p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
                        >
                          <div className="font-medium">
                            {sportOptions.find((s) => s.value === alt.sport_type)?.icon}{' '}
                            {alt.duration_minutes} min {alt.intensity}
                          </div>
                          <div className="text-sm text-gray-500">{alt.rationale}</div>
                        </button>
                      ))}
                    </div>
                  </div>
                )}
            </div>
          ) : (
            <div className="text-gray-500 text-center py-12">
              Configure your session to see risk preview
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
