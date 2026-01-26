import { useQuery } from '@tanstack/react-query'
import { AlertTriangle, RefreshCw } from 'lucide-react'
import RiskGauge from '../components/RiskGauge'
import FactorList from '../components/FactorList'
import AlternativeCard from '../components/AlternativeCard'
import { getPrediction } from '../lib/api'

export default function Dashboard() {
  const {
    data: prediction,
    isLoading,
    error,
    refetch,
    isFetching,
  } = useQuery({
    queryKey: ['prediction'],
    queryFn: () => getPrediction(),
    refetchOnWindowFocus: false,
  })

  if (isLoading) {
    return (
      <div className="sm:ml-64 flex items-center justify-center min-h-[60vh]">
        <div className="text-center">
          <RefreshCw className="h-8 w-8 animate-spin text-blue-600 mx-auto" />
          <p className="mt-4 text-gray-600">Analyzing your risk...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="sm:ml-64">
        <div className="card bg-red-50 border-red-200">
          <div className="flex items-center gap-3 text-red-700">
            <AlertTriangle className="h-5 w-5" />
            <span>Failed to load prediction. Make sure the backend is running.</span>
          </div>
          <button
            onClick={() => refetch()}
            className="mt-4 btn-primary"
          >
            Retry
          </button>
        </div>
      </div>
    )
  }

  if (!prediction) {
    return null
  }

  return (
    <div className="sm:ml-64 space-y-6 pb-20 sm:pb-0">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Today's Risk Assessment</h1>
        <button
          onClick={() => refetch()}
          disabled={isFetching}
          className="btn-secondary flex items-center gap-2"
        >
          <RefreshCw className={`h-4 w-4 ${isFetching ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Safety Rules Alert */}
      {prediction.safety_rules_triggered.some((r) => r.triggered) && (
        <div className="card bg-red-50 border-red-200">
          <div className="flex items-start gap-3">
            <AlertTriangle className="h-5 w-5 text-red-600 mt-0.5" />
            <div>
              <h3 className="font-semibold text-red-800">Safety Alert</h3>
              {prediction.safety_rules_triggered
                .filter((r) => r.triggered)
                .map((rule) => (
                  <p key={rule.rule_id} className="text-red-700 text-sm mt-1">
                    {rule.message}
                  </p>
                ))}
            </div>
          </div>
        </div>
      )}

      {/* Main Risk Display */}
      <div className="grid lg:grid-cols-2 gap-6">
        {/* Risk Gauge Card */}
        <div className="card">
          <h2 className="text-lg font-semibold text-gray-900 mb-6">Risk Score</h2>
          <div className="flex justify-center">
            <RiskGauge
              score={prediction.risk_score}
              level={prediction.risk_level}
              size="lg"
            />
          </div>
          <p className="text-center text-gray-600 mt-6">{prediction.explanation}</p>
        </div>

        {/* Contributing Factors */}
        <div className="card">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Contributing Factors
          </h2>
          <FactorList factors={prediction.top_factors} />
        </div>
      </div>

      {/* Score Breakdown */}
      {prediction.breakdown && (
        <div className="card">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Score Breakdown</h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <BreakdownItem
              label="HRV"
              value={prediction.breakdown.hrv_contribution}
            />
            <BreakdownItem
              label="Resting HR"
              value={prediction.breakdown.rhr_contribution}
            />
            <BreakdownItem
              label="Sleep"
              value={prediction.breakdown.sleep_contribution}
            />
            <BreakdownItem
              label="Training Load"
              value={prediction.breakdown.acwr_contribution}
            />
            <BreakdownItem
              label="Symptoms"
              value={prediction.breakdown.symptom_contribution}
            />
            <BreakdownItem
              label="Session"
              value={prediction.breakdown.session_contribution}
            />
            <BreakdownItem
              label="Base"
              value={prediction.breakdown.base_score}
              isBase
            />
          </div>
        </div>
      )}

      {/* Alternatives */}
      {prediction.alternatives.length > 0 && (
        <div className="card">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Recommended Alternatives
          </h2>
          <div className="grid sm:grid-cols-2 gap-4">
            {prediction.alternatives.map((alt, index) => (
              <AlternativeCard key={index} alternative={alt} />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function BreakdownItem({
  label,
  value,
  isBase = false,
}: {
  label: string
  value: number
  isBase?: boolean
}) {
  const getColor = () => {
    if (isBase) return 'text-gray-600'
    if (value > 15) return 'text-red-600'
    if (value > 5) return 'text-orange-600'
    if (value < 0) return 'text-green-600'
    return 'text-gray-600'
  }

  return (
    <div className="text-center p-3 bg-gray-50 rounded-lg">
      <div className={`text-2xl font-bold ${getColor()}`}>
        {isBase ? value : value > 0 ? `+${value}` : value}
      </div>
      <div className="text-sm text-gray-500">{label}</div>
    </div>
  )
}
