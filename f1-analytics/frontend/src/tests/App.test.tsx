/**
 * Tests for the main App component.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import '@testing-library/jest-dom'
import App from '../App'

// Mock fetch globally
const mockFetch = vi.fn()
global.fetch = mockFetch

// Mock environment variables
vi.stubGlobal('import.meta.env', {
  VITE_API_URL: 'http://localhost:8000'
})

const mockPredictionsResponse = {
  race_id: 1,
  race_name: 'Monaco Grand Prix 2026',
  race_date: '2026-05-24',
  circuit: 'Circuit de Monaco',
  predictions: [
    {
      driver_id: 1,
      driver_name: 'Max Verstappen',
      driver_code: 'VER',
      team: 'Red Bull Racing',
      win_probability: 35.2,
      team_color: '#0600EF'
    },
    {
      driver_id: 2,
      driver_name: 'Charles Leclerc',
      driver_code: 'LEC',
      team: 'Ferrari',
      win_probability: 28.7,
      team_color: '#DC143C'
    },
    {
      driver_id: 3,
      driver_name: 'Lewis Hamilton',
      driver_code: 'HAM',
      team: 'Mercedes',
      win_probability: 22.1,
      team_color: '#00D2BE'
    }
  ],
  model_version: 'v1.0.0',
  generated_at: '2026-02-12T10:00:00Z'
}

describe('App Component', () => {
  beforeEach(() => {
    mockFetch.mockClear()
  })

  afterEach(() => {
    vi.resetAllMocks()
  })

  it('renders loading state initially', () => {
    // Mock a pending fetch
    mockFetch.mockReturnValue(new Promise(() => {}))

    render(<App />)

    expect(screen.getByText('Loading F1 Predictions...')).toBeInTheDocument()
    expect(screen.getByRole('status')).toBeInTheDocument() // Loading spinner
  })

  it('renders predictions data after successful fetch', async () => {
    // Mock successful response
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockPredictionsResponse)
    })

    render(<App />)

    // Wait for loading to finish
    await waitFor(() => {
      expect(screen.queryByText('Loading F1 Predictions...')).not.toBeInTheDocument()
    })

    // Check race information
    expect(screen.getByText('Monaco Grand Prix 2026')).toBeInTheDocument()
    expect(screen.getByText('Circuit de Monaco')).toBeInTheDocument()
    expect(screen.getByText('5/24/2026')).toBeInTheDocument() // Formatted date

    // Check predictions
    expect(screen.getByText('Max Verstappen')).toBeInTheDocument()
    expect(screen.getByText('Red Bull Racing')).toBeInTheDocument()
    expect(screen.getByText('35.2%')).toBeInTheDocument()

    expect(screen.getByText('Charles Leclerc')).toBeInTheDocument()
    expect(screen.getByText('Ferrari')).toBeInTheDocument()
    expect(screen.getByText('28.7%')).toBeInTheDocument()

    expect(screen.getByText('Lewis Hamilton')).toBeInTheDocument()
    expect(screen.getByText('Mercedes')).toBeInTheDocument()
    expect(screen.getByText('22.1%')).toBeInTheDocument()
  })

  it('renders error state when fetch fails', async () => {
    // Mock failed response
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 500
    })

    render(<App />)

    // Wait for error to appear
    await waitFor(() => {
      expect(screen.getByText('Connection Error')).toBeInTheDocument()
    })

    expect(screen.getByText('HTTP error! status: 500')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Retry Connection' })).toBeInTheDocument()
  })

  it('renders error state when network fails', async () => {
    // Mock network error
    mockFetch.mockRejectedValueOnce(new Error('Network error'))

    render(<App />)

    await waitFor(() => {
      expect(screen.getByText('Connection Error')).toBeInTheDocument()
    })

    expect(screen.getByText('Network error')).toBeInTheDocument()
  })

  it('calls correct API endpoint on load', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockPredictionsResponse)
    })

    render(<App />)

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/predictions/next-race'
      )
    })
  })

  it('retries fetch when retry button is clicked', async () => {
    // First call fails
    mockFetch
      .mockResolvedValueOnce({
        ok: false,
        status: 500
      })
      // Second call succeeds
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockPredictionsResponse)
      })

    render(<App />)

    // Wait for error state
    await waitFor(() => {
      expect(screen.getByText('Connection Error')).toBeInTheDocument()
    })

    // Click retry button
    const retryButton = screen.getByRole('button', { name: 'Retry Connection' })
    fireEvent.click(retryButton)

    // Wait for successful data load
    await waitFor(() => {
      expect(screen.getByText('Monaco Grand Prix 2026')).toBeInTheDocument()
    })

    expect(mockFetch).toHaveBeenCalledTimes(2)
  })

  it('refreshes predictions when refresh button is clicked', async () => {
    const updatedResponse = {
      ...mockPredictionsResponse,
      generated_at: '2026-02-12T11:00:00Z'
    }

    // First call
    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockPredictionsResponse)
      })
      // Second call with updated data
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(updatedResponse)
      })

    render(<App />)

    // Wait for initial load
    await waitFor(() => {
      expect(screen.getByText('Monaco Grand Prix 2026')).toBeInTheDocument()
    })

    // Click refresh button
    const refreshButton = screen.getByRole('button', { name: 'Refresh Predictions' })
    fireEvent.click(refreshButton)

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledTimes(2)
    })
  })

  it('displays correct ranking positions', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockPredictionsResponse)
    })

    render(<App />)

    await waitFor(() => {
      expect(screen.queryByText('Loading F1 Predictions...')).not.toBeInTheDocument()
    })

    // Check that ranking positions are displayed correctly
    const positions = screen.getAllByText(/^[1-3]$/)
    expect(positions).toHaveLength(3)
    expect(positions[0]).toHaveTextContent('1')
    expect(positions[1]).toHaveTextContent('2')
    expect(positions[2]).toHaveTextContent('3')
  })

  it('displays model metadata correctly', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockPredictionsResponse)
    })

    render(<App />)

    await waitFor(() => {
      expect(screen.getByText('Model Version: v1.0.0')).toBeInTheDocument()
    })

    expect(screen.getByText(/Generated:/)).toBeInTheDocument()
  })

  it('handles empty predictions array gracefully', async () => {
    const emptyResponse = {
      ...mockPredictionsResponse,
      predictions: []
    }

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(emptyResponse)
    })

    render(<App />)

    await waitFor(() => {
      expect(screen.getByText('Monaco Grand Prix 2026')).toBeInTheDocument()
    })

    // Should not find any driver names
    expect(screen.queryByText('Max Verstappen')).not.toBeInTheDocument()
  })

  it('uses fallback API URL when environment variable is not set', () => {
    // Mock environment without VITE_API_URL
    vi.stubGlobal('import.meta.env', {})

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockPredictionsResponse)
    })

    render(<App />)

    expect(mockFetch).toHaveBeenCalledWith(
      'http://localhost:8000/api/v1/predictions/next-race'
    )
  })

  it('displays correct header information', () => {
    mockFetch.mockReturnValue(new Promise(() => {}))

    render(<App />)

    expect(screen.getByText('F1 Analytics')).toBeInTheDocument()
    expect(screen.getByText('Prediction Dashboard')).toBeInTheDocument()
    expect(screen.getByText('Environment: Development')).toBeInTheDocument()
    expect(screen.getByText('API Status: Connected')).toBeInTheDocument()
  })

  it('applies team colors to progress bars', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockPredictionsResponse)
    })

    render(<App />)

    await waitFor(() => {
      expect(screen.queryByText('Loading F1 Predictions...')).not.toBeInTheDocument()
    })

    // Check that progress bars are rendered
    const progressBars = document.querySelectorAll('[style*="background-color"]')
    expect(progressBars.length).toBeGreaterThan(0)

    // Check for specific team colors
    const redBullBar = Array.from(progressBars).find(bar =>
      (bar as HTMLElement).style.backgroundColor === 'rgb(6, 0, 239)'
    )
    expect(redBullBar).toBeTruthy()
  })
})