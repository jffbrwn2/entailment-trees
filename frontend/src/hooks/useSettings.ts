/**
 * Custom hook for managing application settings.
 * Handles fetching from and syncing to the backend API.
 */

import { useState, useEffect, useCallback } from 'react'

export interface Settings {
  darkMode: boolean
  claudeModel: string
  evaluatorModel: string
  entailmentModel: string
  autoModel: string
  edisonToolsEnabled: boolean
  gapMapToolsEnabled: boolean
}

const DEFAULT_SETTINGS: Settings = {
  darkMode: true,
  claudeModel: 'claude-sonnet-4-5-20250929',
  evaluatorModel: 'claude-sonnet-4-5-20250929',
  entailmentModel: 'claude-sonnet-4-5-20250929',
  autoModel: 'claude-sonnet-4-5-20250929',  // Will be overridden by backend based on available keys
  edisonToolsEnabled: true,
  gapMapToolsEnabled: true,
}

export function useSettings() {
  const [settings, setSettings] = useState<Settings>(DEFAULT_SETTINGS)

  // Fetch settings from backend on mount
  useEffect(() => {
    const fetchSettings = async () => {
      try {
        const response = await fetch('/api/settings')
        if (response.ok) {
          const data = await response.json()
          setSettings(prev => ({
            ...prev,
            claudeModel: data.chatModel || DEFAULT_SETTINGS.claudeModel,
            evaluatorModel: data.evaluatorModel || DEFAULT_SETTINGS.evaluatorModel,
            entailmentModel: data.entailmentModel || DEFAULT_SETTINGS.entailmentModel,
            autoModel: data.autoModel || DEFAULT_SETTINGS.autoModel,
            edisonToolsEnabled: data.edisonToolsEnabled ?? DEFAULT_SETTINGS.edisonToolsEnabled,
            gapMapToolsEnabled: data.gapMapToolsEnabled ?? DEFAULT_SETTINGS.gapMapToolsEnabled,
          }))
        }
      } catch (error) {
        console.error('Failed to fetch settings:', error)
      }
    }
    fetchSettings()
  }, [])

  // Apply dark/light mode to document
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', settings.darkMode ? 'dark' : 'light')
  }, [settings.darkMode])

  // Update settings (local state + backend sync)
  const updateSettings = useCallback(async (newSettings: Partial<Settings>) => {
    // Update local state immediately
    setSettings(prev => ({ ...prev, ...newSettings }))

    // Sync non-UI settings with backend
    const backendSettings: Record<string, unknown> = {}
    if (newSettings.claudeModel !== undefined) backendSettings.chatModel = newSettings.claudeModel
    if (newSettings.evaluatorModel !== undefined) backendSettings.evaluatorModel = newSettings.evaluatorModel
    if (newSettings.entailmentModel !== undefined) backendSettings.entailmentModel = newSettings.entailmentModel
    if (newSettings.autoModel !== undefined) backendSettings.autoModel = newSettings.autoModel
    if (newSettings.edisonToolsEnabled !== undefined) backendSettings.edisonToolsEnabled = newSettings.edisonToolsEnabled
    if (newSettings.gapMapToolsEnabled !== undefined) backendSettings.gapMapToolsEnabled = newSettings.gapMapToolsEnabled

    // Only call backend if there are settings to sync
    if (Object.keys(backendSettings).length > 0) {
      try {
        await fetch('/api/settings', {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(backendSettings),
        })
      } catch (error) {
        console.error('Failed to update settings:', error)
      }
    }
  }, [])

  return {
    settings,
    updateSettings,
  }
}
