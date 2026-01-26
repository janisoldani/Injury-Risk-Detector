import { useQuery } from '@tanstack/react-query'
import { format } from 'date-fns'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts'
import { Activity, Heart } from 'lucide-react'
import { getWorkouts, getDailyMetrics } from '../lib/api'
import type { SportType, IntensityZone } from '../types/api'

const sportLabels: Record<SportType, string> = {
  running: 'Running',
  cycling: 'Cycling',
  swimming: 'Swimming',
  strength: 'Strength',
  hiit: 'HIIT',
  yoga: 'Yoga',
  other: 'Other',
}

const sportIcons: Record<SportType, string> = {
  running: '🏃',
  cycling: '🚴',
  swimming: '🏊',
  strength: '🏋️',
  hiit: '⚡',
  yoga: '🧘',
  other: '🎯',
}

const intensityColors: Record<IntensityZone, string> = {
  Z1: 'bg-blue-100 text-blue-700',
  Z2: 'bg-green-100 text-green-700',
  Z3: 'bg-yellow-100 text-yellow-700',
  Z4: 'bg-orange-100 text-orange-700',
  Z5: 'bg-red-100 text-red-700',
}

export default function History() {
  const { data: workouts, isLoading: workoutsLoading } = useQuery({
    queryKey: ['workouts'],
    queryFn: () => getWorkouts(0, 50),
  })

  const { data: metrics, isLoading: metricsLoading } = useQuery({
    queryKey: ['daily-metrics'],
    queryFn: () => getDailyMetrics(28),
  })

  const chartData = metrics
    ?.map((m) => ({
      date: format(new Date(m.date), 'MMM d'),
      hrv: m.hrv_rmssd,
      rhr: m.resting_hr,
      sleep: m.sleep_duration_minutes ? m.sleep_duration_minutes / 60 : null,
    }))
    .reverse()

  return (
    <div className="sm:ml-64 space-y-6 pb-20 sm:pb-0">
      <h1 className="text-2xl font-bold text-gray-900">History</h1>

      {/* Metrics Chart */}
      <div className="card">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          Health Trends (28 Days)
        </h2>
        {metricsLoading ? (
          <div className="h-64 flex items-center justify-center">
            <div className="animate-pulse text-gray-500">Loading metrics...</div>
          </div>
        ) : chartData && chartData.length > 0 ? (
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 12 }}
                  stroke="#9ca3af"
                />
                <YAxis
                  yAxisId="left"
                  tick={{ fontSize: 12 }}
                  stroke="#9ca3af"
                  label={{
                    value: 'HRV / RHR',
                    angle: -90,
                    position: 'insideLeft',
                    fontSize: 12,
                  }}
                />
                <YAxis
                  yAxisId="right"
                  orientation="right"
                  tick={{ fontSize: 12 }}
                  stroke="#9ca3af"
                  label={{
                    value: 'Sleep (hrs)',
                    angle: 90,
                    position: 'insideRight',
                    fontSize: 12,
                  }}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'white',
                    border: '1px solid #e5e7eb',
                    borderRadius: '8px',
                  }}
                />
                <Legend />
                <Line
                  yAxisId="left"
                  type="monotone"
                  dataKey="hrv"
                  stroke="#22c55e"
                  strokeWidth={2}
                  dot={false}
                  name="HRV (ms)"
                />
                <Line
                  yAxisId="left"
                  type="monotone"
                  dataKey="rhr"
                  stroke="#ef4444"
                  strokeWidth={2}
                  dot={false}
                  name="RHR (bpm)"
                />
                <Line
                  yAxisId="right"
                  type="monotone"
                  dataKey="sleep"
                  stroke="#8b5cf6"
                  strokeWidth={2}
                  dot={false}
                  name="Sleep (hrs)"
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <div className="h-64 flex items-center justify-center text-gray-500">
            No metrics data available. Import FIT files to see trends.
          </div>
        )}
      </div>

      {/* Recent Workouts */}
      <div className="card">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          Recent Workouts
        </h2>
        {workoutsLoading ? (
          <div className="animate-pulse text-gray-500">Loading workouts...</div>
        ) : workouts && workouts.length > 0 ? (
          <div className="space-y-3">
            {workouts.map((workout) => (
              <div
                key={workout.id}
                className="flex items-center gap-4 p-4 bg-gray-50 rounded-lg"
              >
                <div className="text-3xl">
                  {sportIcons[workout.sport_type]}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-gray-900">
                      {sportLabels[workout.sport_type]}
                    </span>
                    <span
                      className={`px-2 py-0.5 rounded text-xs font-medium ${
                        intensityColors[workout.intensity_zone]
                      }`}
                    >
                      {workout.intensity_zone}
                    </span>
                  </div>
                  <div className="text-sm text-gray-500 mt-1">
                    {format(new Date(workout.start_time), 'PPp')}
                  </div>
                </div>
                <div className="text-right">
                  <div className="flex items-center gap-4 text-sm">
                    <div className="flex items-center gap-1 text-gray-600">
                      <Activity className="h-4 w-4" />
                      {workout.duration_minutes} min
                    </div>
                    {workout.avg_heart_rate && (
                      <div className="flex items-center gap-1 text-gray-600">
                        <Heart className="h-4 w-4" />
                        {workout.avg_heart_rate} bpm
                      </div>
                    )}
                    {workout.trimp && (
                      <div className="text-blue-600 font-medium">
                        {workout.trimp.toFixed(0)} TRIMP
                      </div>
                    )}
                  </div>
                  {workout.distance_meters && (
                    <div className="text-sm text-gray-500 mt-1">
                      {(workout.distance_meters / 1000).toFixed(2)} km
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-gray-500 text-center py-8">
            No workouts recorded yet. Import FIT files to see your history.
          </div>
        )}
      </div>
    </div>
  )
}
