import { QueryErrorResetBoundary } from '@tanstack/react-query'
import { ErrorBoundary } from './ErrorBoundary'
import { ReactNode } from 'react'

interface QueryErrorBoundaryProps {
  children: ReactNode
}

export default function QueryErrorBoundary({ children }: QueryErrorBoundaryProps) {
  return (
    <QueryErrorResetBoundary>
      {({ reset }) => (
        <ErrorBoundary
          fallback={
            <div className="min-h-[400px] flex items-center justify-center p-8">
              <div className="card max-w-md text-center">
                <h2 className="text-xl font-semibold text-gray-900 mb-2">
                  Failed to load data
                </h2>
                <p className="text-gray-600 mb-4">
                  There was a problem fetching the data. Please check your connection and try again.
                </p>
                <button onClick={reset} className="btn-primary">
                  Retry
                </button>
              </div>
            </div>
          }
        >
          {children}
        </ErrorBoundary>
      )}
    </QueryErrorResetBoundary>
  )
}
