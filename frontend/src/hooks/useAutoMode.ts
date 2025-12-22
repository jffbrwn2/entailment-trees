/**
 * Custom hook for managing auto mode state and controls.
 * Handles starting, stopping, pausing, and resuming auto mode.
 */

import { useState, useEffect, useCallback, useRef } from 'react'

export interface AutoModeState {
  active: boolean
  paused: boolean
  turnCount: number
  maxTurns: number
}

interface UseAutoModeOptions {
  folder: string | null
  model: string
  onModelUpdate?: (model: string) => void
}

export function useAutoMode({ folder, model, onModelUpdate }: UseAutoModeOptions) {
  const [state, setState] = useState<AutoModeState>({
    active: false,
    paused: false,
    turnCount: 0,
    maxTurns: 20,
  })

  // Use ref for callback to avoid dependency issues
  const onModelUpdateRef = useRef(onModelUpdate)
  onModelUpdateRef.current = onModelUpdate

  // Fetch status when folder changes (only on folder change)
  useEffect(() => {
    if (!folder) {
      setState({ active: false, paused: false, turnCount: 0, maxTurns: 20 })
      return
    }

    const fetchStatus = async () => {
      try {
        const response = await fetch(`/api/approaches/${folder}/auto/status`)
        if (response.ok) {
          const status = await response.json()
          setState({
            active: status.active,
            paused: status.paused,
            turnCount: status.turn_count,
            maxTurns: status.max_turns || 20,
          })
          if (status.model && onModelUpdateRef.current) {
            onModelUpdateRef.current(status.model)
          }
        }
      } catch (error) {
        console.error('Failed to fetch auto mode status:', error)
      }
    }

    fetchStatus()
  }, [folder]) // Only depend on folder

  const start = useCallback(async (targetFolder?: string) => {
    const f = targetFolder || folder
    if (!f) return

    try {
      const response = await fetch(`/api/approaches/${f}/auto/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model }),
      })
      if (response.ok) {
        const data = await response.json()
        setState({
          active: true,
          paused: false,
          turnCount: 0,
          maxTurns: data.max_turns,
        })
      }
    } catch (error) {
      console.error('Failed to start auto mode:', error)
    }
  }, [folder, model])

  const stop = useCallback(async () => {
    if (!folder) return

    try {
      await fetch(`/api/approaches/${folder}/auto/stop`, { method: 'POST' })
      setState(prev => ({ ...prev, active: false, paused: false }))
    } catch (error) {
      console.error('Failed to stop auto mode:', error)
    }
  }, [folder])

  const pause = useCallback(async () => {
    if (!folder) return

    try {
      await fetch(`/api/approaches/${folder}/auto/pause`, { method: 'POST' })
      setState(prev => ({ ...prev, paused: true }))
    } catch (error) {
      console.error('Failed to pause auto mode:', error)
    }
  }, [folder])

  const resume = useCallback(async () => {
    if (!folder) return

    try {
      await fetch(`/api/approaches/${folder}/auto/resume`, { method: 'POST' })
      setState(prev => ({ ...prev, paused: false, active: true }))
    } catch (error) {
      console.error('Failed to resume auto mode:', error)
    }
  }, [folder])

  const setTurnCount = useCallback((count: number) => {
    setState(prev => ({ ...prev, turnCount: count }))
  }, [])

  return {
    ...state,
    start,
    stop,
    pause,
    resume,
    setTurnCount,
  }
}
