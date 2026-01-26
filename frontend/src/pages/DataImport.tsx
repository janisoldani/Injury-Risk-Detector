import { useState, useCallback } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Upload, AlertCircle, CheckCircle, X } from 'lucide-react'
import { uploadFitFile, getImportStats } from '../lib/api'
import { useToast } from '../context/ToastContext'
import type { ImportResult } from '../types/api'

export default function DataImport() {
  const [dragActive, setDragActive] = useState(false)
  const [results, setResults] = useState<ImportResult[]>([])
  const queryClient = useQueryClient()
  const toast = useToast()

  const { data: stats, isLoading: statsLoading, error: statsError } = useQuery({
    queryKey: ['import-stats'],
    queryFn: getImportStats,
  })

  const uploadMutation = useMutation({
    mutationFn: uploadFitFile,
    onSuccess: (result) => {
      setResults((prev) => [result, ...prev])
      queryClient.invalidateQueries({ queryKey: ['import-stats'] })
      queryClient.invalidateQueries({ queryKey: ['prediction'] })
      if (result.success) {
        toast.success(`Imported ${result.workouts_imported} workout(s) successfully!`)
      }
    },
    onError: (error: Error) => {
      const errorMessage = error.message || 'Upload failed'
      toast.error(`Import failed: ${errorMessage}`)
      setResults((prev) => [
        {
          success: false,
          message: errorMessage,
          workouts_imported: 0,
          workouts_skipped: 0,
          metrics_imported: 0,
          errors: [errorMessage],
        },
        ...prev,
      ])
    },
  })

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true)
    } else if (e.type === 'dragleave') {
      setDragActive(false)
    }
  }, [])

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      e.stopPropagation()
      setDragActive(false)

      const files = Array.from(e.dataTransfer.files).filter(
        (file) => file.name.endsWith('.fit') || file.name.endsWith('.FIT')
      )

      files.forEach((file) => uploadMutation.mutate(file))
    },
    [uploadMutation]
  )

  const handleFileInput = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = e.target.files
      if (files) {
        Array.from(files).forEach((file) => uploadMutation.mutate(file))
      }
      e.target.value = '' // Reset input
    },
    [uploadMutation]
  )

  const clearResult = (index: number) => {
    setResults((prev) => prev.filter((_, i) => i !== index))
  }

  return (
    <div className="sm:ml-64 space-y-6 pb-20 sm:pb-0">
      <h1 className="text-2xl font-bold text-gray-900">Import Data</h1>

      {/* Stats Card */}
      <div className="card">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          Import Statistics
        </h2>
        {statsLoading ? (
          <div className="animate-pulse text-gray-500">Loading stats...</div>
        ) : stats ? (
          <div className="grid grid-cols-3 gap-4">
            <div className="text-center p-4 bg-gray-50 rounded-lg">
              <div className="text-3xl font-bold text-blue-600">
                {stats.total_workouts}
              </div>
              <div className="text-sm text-gray-500">Total Workouts</div>
            </div>
            <div className="text-center p-4 bg-gray-50 rounded-lg">
              <div className="text-3xl font-bold text-green-600">
                {stats.total_metrics}
              </div>
              <div className="text-sm text-gray-500">Daily Metrics</div>
            </div>
            <div className="text-center p-4 bg-gray-50 rounded-lg">
              <div className="text-sm font-medium text-gray-900">
                {stats.date_range
                  ? `${stats.date_range.earliest} - ${stats.date_range.latest}`
                  : 'No data'}
              </div>
              <div className="text-sm text-gray-500">Date Range</div>
            </div>
          </div>
        ) : (
          <div className="text-gray-500">No data imported yet</div>
        )}
      </div>

      {/* Upload Area */}
      <div className="card">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          Upload FIT Files
        </h2>
        <div
          className={`relative border-2 border-dashed rounded-xl p-12 text-center transition-colors ${
            dragActive
              ? 'border-blue-500 bg-blue-50'
              : 'border-gray-300 hover:border-gray-400'
          }`}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
        >
          <input
            type="file"
            accept=".fit,.FIT"
            multiple
            onChange={handleFileInput}
            className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
          />
          <Upload
            className={`h-12 w-12 mx-auto ${
              dragActive ? 'text-blue-500' : 'text-gray-400'
            }`}
          />
          <p className="mt-4 text-lg font-medium text-gray-700">
            Drop FIT files here or click to browse
          </p>
          <p className="mt-2 text-sm text-gray-500">
            Supports Garmin and other FIT file formats
          </p>
        </div>

        {/* Upload Progress */}
        {uploadMutation.isPending && (
          <div className="mt-4 p-4 bg-blue-50 rounded-lg">
            <div className="flex items-center gap-3">
              <div className="animate-spin h-5 w-5 border-2 border-blue-500 border-t-transparent rounded-full" />
              <span className="text-blue-700">Uploading and processing...</span>
            </div>
          </div>
        )}
      </div>

      {/* Results */}
      {results.length > 0 && (
        <div className="card">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Recent Imports
          </h2>
          <div className="space-y-3">
            {results.map((result, index) => (
              <div
                key={index}
                className={`p-4 rounded-lg flex items-start gap-3 ${
                  result.success
                    ? 'bg-green-50 border border-green-200'
                    : 'bg-red-50 border border-red-200'
                }`}
              >
                {result.success ? (
                  <CheckCircle className="h-5 w-5 text-green-600 mt-0.5" />
                ) : (
                  <AlertCircle className="h-5 w-5 text-red-600 mt-0.5" />
                )}
                <div className="flex-1 min-w-0">
                  <div
                    className={`font-medium ${
                      result.success ? 'text-green-800' : 'text-red-800'
                    }`}
                  >
                    {result.message}
                  </div>
                  {result.success && (
                    <div className="text-sm text-green-600 mt-1">
                      {result.workouts_imported} workout(s) imported
                      {result.workouts_skipped > 0 &&
                        `, ${result.workouts_skipped} skipped (duplicates)`}
                      {result.metrics_imported > 0 &&
                        `, ${result.metrics_imported} metric record(s)`}
                    </div>
                  )}
                  {result.errors.length > 0 && (
                    <ul className="text-sm text-red-600 mt-1 list-disc list-inside">
                      {result.errors.map((err, i) => (
                        <li key={i}>{err}</li>
                      ))}
                    </ul>
                  )}
                </div>
                <button
                  onClick={() => clearResult(index)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Instructions */}
      <div className="card bg-blue-50 border-blue-200">
        <h3 className="font-semibold text-blue-900">Supported Data</h3>
        <ul className="mt-2 text-sm text-blue-700 space-y-1">
          <li>• <strong>Activities:</strong> Running, cycling, swimming, and other workouts</li>
          <li>• <strong>Health Metrics:</strong> HRV (RMSSD), resting heart rate, sleep data</li>
          <li>• <strong>Training Load:</strong> TRIMP, Training Effect, intensity zones</li>
        </ul>
        <p className="mt-3 text-sm text-blue-600">
          Connect your Garmin watch and export FIT files from Garmin Connect, or sync directly from your device.
        </p>
      </div>
    </div>
  )
}
