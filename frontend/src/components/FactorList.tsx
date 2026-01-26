import { AlertTriangle, TrendingDown, TrendingUp, Minus } from 'lucide-react'
import type { FactorContribution } from '../types/api'

interface FactorListProps {
  factors: FactorContribution[]
}

function getFactorIcon(contribution: number) {
  if (contribution > 10) return <TrendingUp className="h-4 w-4 text-red-500" />
  if (contribution < -5) return <TrendingDown className="h-4 w-4 text-green-500" />
  return <Minus className="h-4 w-4 text-gray-400" />
}

function getContributionColor(contribution: number) {
  if (contribution > 15) return 'text-red-600 bg-red-50'
  if (contribution > 5) return 'text-orange-600 bg-orange-50'
  if (contribution < -5) return 'text-green-600 bg-green-50'
  return 'text-gray-600 bg-gray-50'
}

export default function FactorList({ factors }: FactorListProps) {
  if (factors.length === 0) {
    return (
      <div className="text-gray-500 text-sm italic">
        No significant contributing factors
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {factors.map((factor, index) => (
        <div
          key={index}
          className="flex items-start gap-3 p-3 rounded-lg bg-gray-50"
        >
          <div className="mt-0.5">{getFactorIcon(factor.contribution)}</div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center justify-between gap-2">
              <span className="font-medium text-gray-900">{factor.factor}</span>
              <span
                className={`px-2 py-0.5 rounded text-xs font-medium ${getContributionColor(factor.contribution)}`}
              >
                {factor.contribution > 0 ? '+' : ''}
                {factor.contribution.toFixed(1)}
              </span>
            </div>
            <p className="text-sm text-gray-600 mt-1">{factor.description}</p>
          </div>
        </div>
      ))}
    </div>
  )
}
