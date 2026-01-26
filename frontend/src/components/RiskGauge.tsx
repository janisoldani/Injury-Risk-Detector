import { useMemo } from 'react'
import type { RiskLevel } from '../types/api'

interface RiskGaugeProps {
  score: number
  level: RiskLevel
  size?: 'sm' | 'md' | 'lg'
}

const sizeConfig = {
  sm: { width: 120, strokeWidth: 8, fontSize: '1.5rem' },
  md: { width: 180, strokeWidth: 12, fontSize: '2.25rem' },
  lg: { width: 240, strokeWidth: 16, fontSize: '3rem' },
}

const levelColors: Record<RiskLevel, { stroke: string; bg: string; text: string }> = {
  GREEN: {
    stroke: '#22c55e',
    bg: 'bg-green-50',
    text: 'text-green-700',
  },
  YELLOW: {
    stroke: '#eab308',
    bg: 'bg-yellow-50',
    text: 'text-yellow-700',
  },
  RED: {
    stroke: '#ef4444',
    bg: 'bg-red-50',
    text: 'text-red-700',
  },
}

const levelLabels: Record<RiskLevel, string> = {
  GREEN: 'Low Risk',
  YELLOW: 'Moderate Risk',
  RED: 'High Risk',
}

export default function RiskGauge({ score, level, size = 'md' }: RiskGaugeProps) {
  const config = sizeConfig[size]
  const colors = levelColors[level]
  const label = levelLabels[level]

  const { circumference, offset } = useMemo(() => {
    const radius = (config.width - config.strokeWidth) / 2
    const circ = 2 * Math.PI * radius
    // We show 270 degrees (3/4 of circle)
    const arcLength = circ * 0.75
    const progress = Math.min(Math.max(score, 0), 100) / 100
    const off = arcLength * (1 - progress)
    return { circumference: arcLength, offset: off }
  }, [score, config])

  const radius = (config.width - config.strokeWidth) / 2
  const center = config.width / 2

  return (
    <div className="flex flex-col items-center">
      <div className="relative" style={{ width: config.width, height: config.width }}>
        <svg
          width={config.width}
          height={config.width}
          className="transform -rotate-[135deg]"
        >
          {/* Background arc */}
          <circle
            cx={center}
            cy={center}
            r={radius}
            fill="none"
            stroke="#e5e7eb"
            strokeWidth={config.strokeWidth}
            strokeDasharray={`${circumference} ${2 * Math.PI * radius}`}
            strokeLinecap="round"
          />
          {/* Progress arc */}
          <circle
            cx={center}
            cy={center}
            r={radius}
            fill="none"
            stroke={colors.stroke}
            strokeWidth={config.strokeWidth}
            strokeDasharray={`${circumference} ${2 * Math.PI * radius}`}
            strokeDashoffset={offset}
            strokeLinecap="round"
            className="transition-all duration-500 ease-out"
          />
        </svg>
        {/* Score text */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span
            className="font-bold text-gray-900"
            style={{ fontSize: config.fontSize }}
          >
            {Math.round(score)}
          </span>
          <span className="text-gray-500 text-sm">/ 100</span>
        </div>
      </div>
      {/* Risk Level Badge */}
      <div
        className={`mt-4 px-4 py-2 rounded-full font-medium ${colors.bg} ${colors.text}`}
      >
        {label}
      </div>
    </div>
  )
}
