import { useState, useEffect } from 'react'
import './SettingsModal.css'

interface OpenRouterModel {
  id: string
  name: string
}

// Anthropic models for the Evaluator (uses Anthropic API directly, not OpenRouter)
const ANTHROPIC_MODELS = [
  { id: 'claude-sonnet-4-5-20250929', name: 'Claude Sonnet 4.5' },
  { id: 'claude-opus-4-20250514', name: 'Claude Opus 4' },
  { id: 'claude-3-5-sonnet-20241022', name: 'Claude 3.5 Sonnet' },
  { id: 'claude-3-5-haiku-20241022', name: 'Claude 3.5 Haiku' },
  { id: 'claude-3-opus-20240229', name: 'Claude 3 Opus' },
]

interface Settings {
  darkMode: boolean
  claudeModel: string
  evaluatorModel: string
  autoModel: string
  // Tool toggles
  edisonToolsEnabled: boolean
  gapMapToolsEnabled: boolean
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
            <div className="settings-row toggle-row">
              <span className="toggle-label-text">Theme</span>
              <div className="toggle-control">
                <span className={`toggle-option ${!localSettings.darkMode ? 'active' : ''}`}>Light</span>
                <label className="toggle-wrapper">
                  <input
                    type="checkbox"
                    checked={localSettings.darkMode}
                    onChange={(e) => handleChange('darkMode', e.target.checked)}
                  />
                  <span className="toggle-switch"></span>
                </label>
                <span className={`toggle-option ${localSettings.darkMode ? 'active' : ''}`}>Dark</span>
              </div>
            </div>
          </div>

          <div className="settings-section">
            <h3>Models</h3>

            <div className="settings-row">
              <label htmlFor="claude-model">
                <span className="label-text">Chat Agent</span>
                <span className="label-hint">Model for the main chat interface (Anthropic API)</span>
              </label>
              <select
                id="claude-model"
                value={localSettings.claudeModel}
                onChange={(e) => handleChange('claudeModel', e.target.value)}
              >
                {ANTHROPIC_MODELS.map((model) => (
                  <option key={model.id} value={model.id}>
                    {model.name}
                  </option>
                ))}
              </select>
            </div>

            <div className="settings-row">
              <label htmlFor="evaluator-model">
                <span className="label-text">Evaluator</span>
                <span className="label-hint">Model for evaluating claims and entailments (Anthropic API)</span>
              </label>
              <select
                id="evaluator-model"
                value={localSettings.evaluatorModel}
                onChange={(e) => handleChange('evaluatorModel', e.target.value)}
              >
                {ANTHROPIC_MODELS.map((model) => (
                  <option key={model.id} value={model.id}>
                    {model.name}
                  </option>
                ))}
              </select>
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
                    <option value="google/gemini-3-pro-preview">google/gemini-3-pro-preview</option>
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

          <div className="settings-section">
            <h3>Tools</h3>
            <div className="settings-row toggle-row">
              <div className="toggle-label">
                <span className="label-text">Edison Tools</span>
                <span className="label-hint">Access to Edison Scientific knowledge base</span>
              </div>
              <label className="toggle-wrapper">
                <input
                  type="checkbox"
                  checked={localSettings.edisonToolsEnabled}
                  onChange={(e) => handleChange('edisonToolsEnabled', e.target.checked)}
                />
                <span className="toggle-switch"></span>
              </label>
            </div>
            <div className="settings-row toggle-row">
              <div className="toggle-label">
                <span className="label-text">Gap Map Tools</span>
                <span className="label-hint">Access to Gap Map research database</span>
              </div>
              <label className="toggle-wrapper">
                <input
                  type="checkbox"
                  checked={localSettings.gapMapToolsEnabled}
                  onChange={(e) => handleChange('gapMapToolsEnabled', e.target.checked)}
                />
                <span className="toggle-switch"></span>
              </label>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default SettingsModal
