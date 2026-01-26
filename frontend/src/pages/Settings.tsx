import { useState, useEffect } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Heart, Activity, AlertTriangle, CheckCircle, Settings as SettingsIcon } from 'lucide-react'

// Settings stored in localStorage for MVP (will be moved to backend in v2)
interface UserSettings {
  restingHrBaseline: number
  hrvBaseline: number
  maxHeartRate: number
  hasCurrentInjury: boolean
  injuryNotes: string
}

const DEFAULT_SETTINGS: UserSettings = {
  restingHrBaseline: 60,
  hrvBaseline: 50,
  maxHeartRate: 185,
  hasCurrentInjury: false,
  injuryNotes: '',
}

function loadSettings(): UserSettings {
  try {
    const stored = localStorage.getItem('userSettings')
    if (stored) {
      return { ...DEFAULT_SETTINGS, ...JSON.parse(stored) }
    }
  } catch {
    console.error('Failed to load settings from localStorage')
  }
  return DEFAULT_SETTINGS
}

function saveSettings(settings: UserSettings): void {
  localStorage.setItem('userSettings', JSON.stringify(settings))
}

export default function Settings() {
  const queryClient = useQueryClient()
  const [settings, setSettings] = useState<UserSettings>(loadSettings)
  const [saveSuccess, setSaveSuccess] = useState(false)
  const [hasChanges, setHasChanges] = useState(false)

  useEffect(() => {
    const stored = loadSettings()
    const changed = JSON.stringify(settings) !== JSON.stringify(stored)
    setHasChanges(changed)
  }, [settings])

  const saveMutation = useMutation({
    mutationFn: async (newSettings: UserSettings) => {
      saveSettings(newSettings)
      return newSettings
    },
    onSuccess: () => {
      setSaveSuccess(true)
      setHasChanges(false)
      queryClient.invalidateQueries({ queryKey: ['prediction'] })
      setTimeout(() => setSaveSuccess(false), 3000)
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    saveMutation.mutate(settings)
  }

  const handleReset = () => {
    setSettings(loadSettings())
    setHasChanges(false)
  }

  return (
    <div className="sm:ml-64 space-y-6 pb-20 sm:pb-0">
      <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
        <SettingsIcon className="h-7 w-7" />
        Training Settings
      </h1>

      {/* Success Message */}
      {saveSuccess && (
        <div className="card bg-green-50 border-green-200">
          <div className="flex items-center gap-3 text-green-700">
            <CheckCircle className="h-5 w-5" />
            <span>Settings saved successfully!</span>
          </div>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Baseline Metrics Card */}
        <div className="card">
          <h2 className="text-lg font-semibold text-gray-900 mb-6 flex items-center gap-2">
            <Heart className="h-5 w-5 text-red-500" />
            Baseline Metrics
          </h2>
          <p className="text-sm text-gray-600 mb-6">
            Set your personal baselines for accurate risk calculations. These values are used to detect deviations from your normal state.
          </p>

          <div className="grid sm:grid-cols-3 gap-6">
            {/* Resting Heart Rate */}
            <div>
              <label className="label">Resting Heart Rate (bpm)</label>
              <input
                type="number"
                min="30"
                max="120"
                value={settings.restingHrBaseline}
                onChange={(e) =>
                  setSettings({ ...settings, restingHrBaseline: parseInt(e.target.value) || 60 })
                }
                className="input"
              />
              <p className="text-xs text-gray-500 mt-1">
                Your typical morning resting HR (usually 40-80 bpm)
              </p>
            </div>

            {/* HRV Baseline */}
            <div>
              <label className="label">HRV Baseline (ms RMSSD)</label>
              <input
                type="number"
                min="10"
                max="200"
                value={settings.hrvBaseline}
                onChange={(e) =>
                  setSettings({ ...settings, hrvBaseline: parseInt(e.target.value) || 50 })
                }
                className="input"
              />
              <p className="text-xs text-gray-500 mt-1">
                Your typical HRV reading (usually 20-100 ms)
              </p>
            </div>

            {/* Max Heart Rate */}
            <div>
              <label className="label">Max Heart Rate (bpm)</label>
              <input
                type="number"
                min="120"
                max="220"
                value={settings.maxHeartRate}
                onChange={(e) =>
                  setSettings({ ...settings, maxHeartRate: parseInt(e.target.value) || 185 })
                }
                className="input"
              />
              <p className="text-xs text-gray-500 mt-1">
                Used for zone calculations (220 - age is a rough estimate)
              </p>
            </div>
          </div>
        </div>

        {/* Injury Status Card */}
        <div className="card">
          <h2 className="text-lg font-semibold text-gray-900 mb-6 flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-yellow-500" />
            Current Injury Status
          </h2>

          <div className="space-y-4">
            {/* Injury Toggle */}
            <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
              <div>
                <div className="font-medium text-gray-900">Currently Injured</div>
                <div className="text-sm text-gray-500">
                  Enable this if you have an active injury to increase safety thresholds
                </div>
              </div>
              <button
                type="button"
                onClick={() =>
                  setSettings({ ...settings, hasCurrentInjury: !settings.hasCurrentInjury })
                }
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                  settings.hasCurrentInjury ? 'bg-red-500' : 'bg-gray-300'
                }`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    settings.hasCurrentInjury ? 'translate-x-6' : 'translate-x-1'
                  }`}
                />
              </button>
            </div>

            {/* Injury Notes */}
            {settings.hasCurrentInjury && (
              <div>
                <label className="label">Injury Notes</label>
                <textarea
                  value={settings.injuryNotes}
                  onChange={(e) => setSettings({ ...settings, injuryNotes: e.target.value })}
                  placeholder="Describe your injury (e.g., location, severity, date started)..."
                  className="input min-h-[100px] resize-y"
                />
              </div>
            )}

            {settings.hasCurrentInjury && (
              <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
                <div className="flex items-start gap-3">
                  <AlertTriangle className="h-5 w-5 text-yellow-600 mt-0.5" />
                  <div className="text-sm text-yellow-800">
                    <strong>Injury Mode Active:</strong> Risk thresholds will be more conservative.
                    All high-intensity sessions will show elevated risk warnings.
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Heart Rate Zones Preview */}
        <div className="card">
          <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <Activity className="h-5 w-5 text-blue-500" />
            Calculated Heart Rate Zones
          </h2>
          <p className="text-sm text-gray-600 mb-4">
            Based on your max HR of {settings.maxHeartRate} bpm:
          </p>
          <div className="grid grid-cols-5 gap-2">
            {[
              { zone: 'Z1', pct: [50, 60], color: 'bg-blue-100 text-blue-700' },
              { zone: 'Z2', pct: [60, 70], color: 'bg-green-100 text-green-700' },
              { zone: 'Z3', pct: [70, 80], color: 'bg-yellow-100 text-yellow-700' },
              { zone: 'Z4', pct: [80, 90], color: 'bg-orange-100 text-orange-700' },
              { zone: 'Z5', pct: [90, 100], color: 'bg-red-100 text-red-700' },
            ].map(({ zone, pct, color }) => {
              const low = Math.round(settings.maxHeartRate * pct[0] / 100)
              const high = Math.round(settings.maxHeartRate * pct[1] / 100)
              return (
                <div key={zone} className={`p-3 rounded-lg text-center ${color}`}>
                  <div className="font-bold">{zone}</div>
                  <div className="text-sm">{low}-{high}</div>
                  <div className="text-xs opacity-75">bpm</div>
                </div>
              )
            })}
          </div>
        </div>

        {/* Save/Reset Buttons */}
        <div className="flex items-center gap-4">
          <button
            type="submit"
            disabled={saveMutation.isPending || !hasChanges}
            className="btn-primary"
          >
            {saveMutation.isPending ? 'Saving...' : 'Save Settings'}
          </button>
          {hasChanges && (
            <button
              type="button"
              onClick={handleReset}
              className="btn-secondary"
            >
              Discard Changes
            </button>
          )}
        </div>
      </form>
    </div>
  )
}
