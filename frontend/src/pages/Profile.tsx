import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { User, Globe, Activity, CheckCircle, AlertCircle } from 'lucide-react'
import { format } from 'date-fns'
import { getUser, updateUser, getImportStats } from '../lib/api'
import type { SportProfile, UserUpdate } from '../types/api'

const sportProfileOptions: { value: SportProfile; label: string; description: string }[] = [
  {
    value: 'high_training_load',
    label: 'High Training Load',
    description: 'Competitive athlete, training 6+ hours/week',
  },
  {
    value: 'moderate_training_load',
    label: 'Moderate Training Load',
    description: 'Regular exerciser, training 3-6 hours/week',
  },
  {
    value: 'recreational',
    label: 'Recreational',
    description: 'Casual fitness, training 1-3 hours/week',
  },
]

const timezoneOptions = [
  'Europe/Zurich',
  'Europe/London',
  'Europe/Berlin',
  'Europe/Paris',
  'America/New_York',
  'America/Los_Angeles',
  'America/Chicago',
  'Asia/Tokyo',
  'Asia/Shanghai',
  'Australia/Sydney',
]

export default function Profile() {
  const queryClient = useQueryClient()
  const [formData, setFormData] = useState<UserUpdate>({})
  const [saveSuccess, setSaveSuccess] = useState(false)

  const { data: user, isLoading: userLoading, error: userError } = useQuery({
    queryKey: ['user'],
    queryFn: () => getUser(),
  })

  const { data: stats } = useQuery({
    queryKey: ['import-stats'],
    queryFn: () => getImportStats(),
  })

  useEffect(() => {
    if (user) {
      setFormData({
        sport_profile: user.sport_profile,
        timezone: user.timezone,
      })
    }
  }, [user])

  const updateMutation = useMutation({
    mutationFn: updateUser,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['user'] })
      setSaveSuccess(true)
      setTimeout(() => setSaveSuccess(false), 3000)
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    updateMutation.mutate(formData)
  }

  if (userLoading) {
    return (
      <div className="sm:ml-64 flex items-center justify-center min-h-[60vh]">
        <div className="animate-pulse text-gray-500">Loading profile...</div>
      </div>
    )
  }

  if (userError || !user) {
    return (
      <div className="sm:ml-64">
        <div className="card bg-yellow-50 border-yellow-200">
          <div className="flex items-center gap-3 text-yellow-700">
            <AlertCircle className="h-5 w-5" />
            <span>User profile not found. Please create a user first.</span>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="sm:ml-64 space-y-6 pb-20 sm:pb-0">
      <h1 className="text-2xl font-bold text-gray-900">Profile Settings</h1>

      {/* Success Message */}
      {saveSuccess && (
        <div className="card bg-green-50 border-green-200">
          <div className="flex items-center gap-3 text-green-700">
            <CheckCircle className="h-5 w-5" />
            <span>Settings saved successfully!</span>
          </div>
        </div>
      )}

      {/* Error Message */}
      {updateMutation.isError && (
        <div className="card bg-red-50 border-red-200">
          <div className="flex items-center gap-3 text-red-700">
            <AlertCircle className="h-5 w-5" />
            <span>Failed to save settings. Please try again.</span>
          </div>
        </div>
      )}

      <div className="grid lg:grid-cols-2 gap-6">
        {/* User Info Card */}
        <div className="card">
          <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <User className="h-5 w-5" />
            Account Information
          </h2>
          <div className="space-y-4">
            <div>
              <label className="label">Email</label>
              <div className="input bg-gray-50 text-gray-600">{user.email}</div>
            </div>
            <div>
              <label className="label">Member Since</label>
              <div className="input bg-gray-50 text-gray-600">
                {format(new Date(user.created_at), 'PPP')}
              </div>
            </div>
            <div>
              <label className="label">Connected Devices</label>
              <div className="flex flex-wrap gap-2">
                {user.device_sources.length > 0 ? (
                  user.device_sources.map((source) => (
                    <span
                      key={source}
                      className="px-3 py-1 bg-blue-100 text-blue-700 rounded-full text-sm"
                    >
                      {source}
                    </span>
                  ))
                ) : (
                  <span className="text-gray-500 text-sm">
                    No devices connected. Import FIT files to add sources.
                  </span>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Data Stats Card */}
        <div className="card">
          <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <Activity className="h-5 w-5" />
            Your Data
          </h2>
          {stats ? (
            <div className="grid grid-cols-2 gap-4">
              <div className="text-center p-4 bg-gray-50 rounded-lg">
                <div className="text-3xl font-bold text-blue-600">
                  {stats.total_workouts}
                </div>
                <div className="text-sm text-gray-500">Workouts</div>
              </div>
              <div className="text-center p-4 bg-gray-50 rounded-lg">
                <div className="text-3xl font-bold text-green-600">
                  {stats.total_metrics}
                </div>
                <div className="text-sm text-gray-500">Daily Records</div>
              </div>
              {stats.date_range && (
                <div className="col-span-2 text-center p-4 bg-gray-50 rounded-lg">
                  <div className="text-sm font-medium text-gray-900">
                    {stats.date_range.earliest} — {stats.date_range.latest}
                  </div>
                  <div className="text-sm text-gray-500">Date Range</div>
                </div>
              )}
            </div>
          ) : (
            <div className="text-gray-500 text-center py-8">
              No data imported yet. Go to Import to add FIT files.
            </div>
          )}
        </div>
      </div>

      {/* Settings Form */}
      <form onSubmit={handleSubmit}>
        <div className="card">
          <h2 className="text-lg font-semibold text-gray-900 mb-6">
            Training Preferences
          </h2>

          <div className="space-y-6">
            {/* Sport Profile */}
            <div>
              <label className="label flex items-center gap-2">
                <Activity className="h-4 w-4" />
                Training Profile
              </label>
              <div className="space-y-2">
                {sportProfileOptions.map((option) => (
                  <button
                    key={option.value}
                    type="button"
                    onClick={() =>
                      setFormData({ ...formData, sport_profile: option.value })
                    }
                    className={`w-full text-left p-4 rounded-lg border-2 transition-colors ${
                      formData.sport_profile === option.value
                        ? 'border-blue-500 bg-blue-50'
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    <div className="font-medium text-gray-900">{option.label}</div>
                    <div className="text-sm text-gray-500">{option.description}</div>
                  </button>
                ))}
              </div>
            </div>

            {/* Timezone */}
            <div>
              <label className="label flex items-center gap-2">
                <Globe className="h-4 w-4" />
                Timezone
              </label>
              <select
                value={formData.timezone || ''}
                onChange={(e) =>
                  setFormData({ ...formData, timezone: e.target.value })
                }
                className="input"
              >
                {timezoneOptions.map((tz) => (
                  <option key={tz} value={tz}>
                    {tz}
                  </option>
                ))}
              </select>
              <p className="text-sm text-gray-500 mt-1">
                Used for calculating daily metrics and scheduling sessions.
              </p>
            </div>

            {/* Save Button */}
            <div className="pt-4 border-t">
              <button
                type="submit"
                disabled={updateMutation.isPending}
                className="btn-primary"
              >
                {updateMutation.isPending ? 'Saving...' : 'Save Changes'}
              </button>
            </div>
          </div>
        </div>
      </form>
    </div>
  )
}
