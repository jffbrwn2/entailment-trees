import { useState, useEffect } from 'react'
import './SettingsModal.css'

interface OpenRouterModel {
  id: string
  name: string
}

interface Settings {
  darkMode: boolean
  claudeModel: string
  evaluatorModel: string
  autoModel: string
}

interface Props {
  isOpen: boolean
  onClose: () => void
  settings: Settings
  onSettingsChange: (settings: Settings) => void
}

function SettingsModal({ isOpen, onClose, settings, onSettingsChange }: Props) {
  const [localSettings, setLocalSettings] = useState<Settings>(settings)
  const [availableModels, setAvailableModels] = useState<OpenRouterModel[]>([])
  const [loadingModels, setLoadingModels] = useState(false)

  // Sync local settings when props change
  useEffect(() => {
    setLocalSettings(settings)
  }, [settings])

  // Fetch available models when modal opens
  useEffect(() => {
    if (isOpen && availableModels.length === 0) {
      fetchModels()
    }
  }, [isOpen])

  const fetchModels = async () => {
    setLoadingModels(true)
    try {
      const response = await fetch('/api/openrouter/models')
      if (response.ok) {
        const models = await response.json()
        const sortedModels = models.sort((a: OpenRouterModel, b: OpenRouterModel) =>
          (a.name || a.id).localeCompare(b.name || b.id)
        )
        setAvailableModels(sortedModels)
      }
    } catch (error) {
      console.error('Failed to fetch models:', error)
    } finally {
      setLoadingModels(false)
    }
  }

  const handleChange = (key: keyof Settings, value: string | boolean) => {
    const newSettings = { ...localSettings, [key]: value }
    setLocalSettings(newSettings)
    onSettingsChange(newSettings)
  }

  if (!isOpen) return null

  return (
    <div className="settings-overlay" onClick={onClose}>
      <div className="settings-modal" onClick={(e) => e.stopPropagation()}>
        <div className="settings-header">
          <h2>Settings</h2>
          <button className="close-button" onClick={onClose}>
            &times;
          </button>
        </div>

        <div className="settings-content">
          <div className="settings-section">
            <h3>Appearance</h3>
            <label className="settings-row toggle-row">
              <span>Dark Mode</span>
              <input
                type="checkbox"
                checked={localSettings.darkMode}
                onChange={(e) => handleChange('darkMode', e.target.checked)}
              />
              <span className="toggle-switch"></span>
            </label>
          </div>

          <div className="settings-section">
            <h3>Models</h3>

            <div className="settings-row">
              <label htmlFor="claude-model">
                <span className="label-text">Chat Agent</span>
                <span className="label-hint">Model for the main chat interface</span>
              </label>
              {loadingModels ? (
                <span className="loading-text">Loading...</span>
              ) : (
                <select
                  id="claude-model"
                  value={localSettings.claudeModel}
                  onChange={(e) => handleChange('claudeModel', e.target.value)}
                >
                  {availableModels.length === 0 ? (
                    <option value="anthropic/claude-sonnet-4">anthropic/claude-sonnet-4</option>
                  ) : (
                    availableModels.map((model) => (
                      <option key={model.id} value={model.id}>
                        {model.name || model.id}
                      </option>
                    ))
                  )}
                </select>
              )}
            </div>

            <div className="settings-row">
              <label htmlFor="evaluator-model">
                <span className="label-text">Evaluator</span>
                <span className="label-hint">Model for evaluating claims and entailments</span>
              </label>
              {loadingModels ? (
                <span className="loading-text">Loading...</span>
              ) : (
                <select
                  id="evaluator-model"
                  value={localSettings.evaluatorModel}
                  onChange={(e) => handleChange('evaluatorModel', e.target.value)}
                >
                  {availableModels.length === 0 ? (
                    <option value="anthropic/claude-sonnet-4">anthropic/claude-sonnet-4</option>
                  ) : (
                    availableModels.map((model) => (
                      <option key={model.id} value={model.id}>
                        {model.name || model.id}
                      </option>
                    ))
                  )}
                </select>
              )}
            </div>

            <div className="settings-row">
              <label htmlFor="auto-model">
                <span className="label-text">Auto Agent</span>
                <span className="label-hint">Model for autonomous exploration mode</span>
              </label>
              {loadingModels ? (
                <span className="loading-text">Loading...</span>
              ) : (
                <select
                  id="auto-model"
                  value={localSettings.autoModel}
                  onChange={(e) => handleChange('autoModel', e.target.value)}
                >
                  {availableModels.length === 0 ? (
                    <option value="anthropic/claude-3-haiku">anthropic/claude-3-haiku</option>
                  ) : (
                    availableModels.map((model) => (
                      <option key={model.id} value={model.id}>
                        {model.name || model.id}
                      </option>
                    ))
                  )}
                </select>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default SettingsModal
