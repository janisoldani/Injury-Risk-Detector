import { Clock, Zap } from 'lucide-react'
import type { AlternativeSession, SportType, IntensityZone } from '../types/api'

interface AlternativeCardProps {
  alternative: AlternativeSession
  onSelect?: () => void
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

const sportLabels: Record<SportType, string> = {
  running: 'Running',
  cycling: 'Cycling',
  swimming: 'Swimming',
  strength: 'Strength',
  hiit: 'HIIT',
  yoga: 'Yoga',
  other: 'Other',
}

const intensityLabels: Record<IntensityZone, string> = {
  Z1: 'Recovery',
  Z2: 'Endurance',
  Z3: 'Tempo',
  Z4: 'Threshold',
  Z5: 'VO2max',
}

const intensityColors: Record<IntensityZone, string> = {
  Z1: 'bg-blue-100 text-blue-700',
  Z2: 'bg-green-100 text-green-700',
  Z3: 'bg-yellow-100 text-yellow-700',
  Z4: 'bg-orange-100 text-orange-700',
  Z5: 'bg-red-100 text-red-700',
}

export default function AlternativeCard({ alternative, onSelect }: AlternativeCardProps) {
  return (
    <div className="card hover:border-blue-200 transition-colors cursor-pointer" onClick={onSelect}>
      <div className="flex items-start gap-4">
        <div className="text-3xl">{sportIcons[alternative.sport_type]}</div>
        <div className="flex-1 min-w-0">
          <h4 className="font-semibold text-gray-900">
            {sportLabels[alternative.sport_type]}
          </h4>
          <div className="flex items-center gap-4 mt-2 text-sm text-gray-600">
            <div className="flex items-center gap-1">
              <Clock className="h-4 w-4" />
              {alternative.duration_minutes} min
            </div>
            <div
              className={`flex items-center gap-1 px-2 py-0.5 rounded ${intensityColors[alternative.intensity]}`}
            >
              <Zap className="h-3 w-3" />
              {intensityLabels[alternative.intensity]}
            </div>
          </div>
          <p className="text-sm text-gray-600 mt-2">{alternative.rationale}</p>
        </div>
      </div>
    </div>
  )
}
