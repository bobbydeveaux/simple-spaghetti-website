import React, { useState, useEffect } from 'react'
import './App.css'

interface PredictionData {
  driver_name: string
  team: string
  win_probability: number
  team_color: string
}

interface ApiResponse {
  race_name: string
  race_date: string
  circuit: string
  predictions: PredictionData[]
  model_version: string
  generated_at: string
}

function App() {
  const [predictions, setPredictions] = useState<ApiResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchPredictions()
  }, [])

  const fetchPredictions = async () => {
    try {
      setLoading(true)
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'
      const response = await fetch(`${apiUrl}/api/v1/predictions/next-race`)

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.json()
      setPredictions(data)
      setError(null)
    } catch (err) {
      console.error('Failed to fetch predictions:', err)
      setError(err instanceof Error ? err.message : 'Failed to fetch predictions')
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-red-600 mx-auto mb-4"></div>
          <h2 className="text-xl font-semibold text-gray-700">
            Loading F1 Predictions...
          </h2>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="text-6xl mb-4">⚠️</div>
          <h1 className="text-2xl font-bold text-gray-900 mb-4">
            Connection Error
          </h1>
          <p className="text-gray-600 mb-8">
            {error}
          </p>
          <button
            onClick={fetchPredictions}
            className="bg-red-600 hover:bg-red-700 text-white font-bold py-2 px-4 rounded"
          >
            Retry Connection
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-red-600 shadow-lg">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <div className="flex items-center">
              <div className="text-3xl font-bold text-white mr-4">🏎️</div>
              <div>
                <h1 className="text-2xl font-bold text-white">F1 Analytics</h1>
                <p className="text-red-100">Prediction Dashboard</p>
              </div>
            </div>
            <div className="text-white text-right">
              <div className="text-sm opacity-75">Environment: Development</div>
              <div className="text-sm opacity-75">API Status: Connected</div>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {predictions && (
          <>
            {/* Race Information */}
            <div className="bg-white rounded-lg shadow mb-8 p-6">
              <h2 className="text-2xl font-bold text-gray-900 mb-4">
                Next Race Predictions
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <h3 className="text-lg font-semibold text-gray-700">Race</h3>
                  <p className="text-gray-900">{predictions.race_name}</p>
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-gray-700">Circuit</h3>
                  <p className="text-gray-900">{predictions.circuit}</p>
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-gray-700">Date</h3>
                  <p className="text-gray-900">
                    {new Date(predictions.race_date).toLocaleDateString()}
                  </p>
                </div>
              </div>
            </div>

            {/* Predictions */}
            <div className="bg-white rounded-lg shadow mb-8 p-6">
              <h3 className="text-xl font-bold text-gray-900 mb-6">
                Win Probability Rankings
              </h3>
              <div className="space-y-4">
                {predictions.predictions.map((prediction, index) => (
                  <div
                    key={index}
                    className="flex items-center p-4 border border-gray-200 rounded-lg"
                  >
                    <div className="flex-shrink-0 w-8 h-8 bg-gray-100 rounded-full flex items-center justify-center mr-4">
                      <span className="text-sm font-bold text-gray-700">
                        {index + 1}
                      </span>
                    </div>
                    <div className="flex-grow">
                      <div className="flex items-center justify-between mb-2">
                        <div>
                          <h4 className="text-lg font-semibold text-gray-900">
                            {prediction.driver_name}
                          </h4>
                          <p className="text-gray-600">{prediction.team}</p>
                        </div>
                        <div className="text-right">
                          <div className="text-2xl font-bold text-gray-900">
                            {prediction.win_probability.toFixed(1)}%
                          </div>
                        </div>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div
                          className="h-2 rounded-full transition-all duration-500"
                          style={{
                            width: `${prediction.win_probability}%`,
                            backgroundColor: prediction.team_color,
                          }}
                        ></div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Footer Info */}
            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex justify-between items-center">
                <div>
                  <p className="text-sm text-gray-600">
                    Model Version: {predictions.model_version}
                  </p>
                  <p className="text-sm text-gray-600">
                    Generated: {new Date(predictions.generated_at).toLocaleString()}
                  </p>
                </div>
                <button
                  onClick={fetchPredictions}
                  className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded"
                >
                  Refresh Predictions
                </button>
              </div>
            </div>
          </>
        )}
      </main>
    </div>
  )
}

export default App