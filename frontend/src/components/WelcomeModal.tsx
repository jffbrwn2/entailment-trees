import { useState, useEffect } from 'react'
import type { Approach } from '../types/hypergraph'
import { truncate } from '../utils/formatters'
import './WelcomeModal.css'

interface OpenRouterModel {
  id: string
  name: string
  pricing?: { prompt?: string; completion?: string }
  context_length?: number
}

interface GapMapSource {
  type: 'gap' | 'capability'
  name: string
  sourceGapName?: string
}

interface Props {
  approaches: Approach[]
  onSelect: (approach: Approach) => void
  onCreate: (name: string, hypothesis: string, enableAutoMode?: boolean, model?: string) => void
  initialMode?: 'choose' | 'create'
  initialHypothesis?: string  // Pre-fill hypothesis from Explore
  exploreSource?: GapMapSource  // Source from Gap Map explore
  onOpenExplore?: () => void  // Open explore modal
  onBackToExplore?: () => void  // Go back to ExploreModal
  onClose?: () => void  // For when opened from ApproachSelector
  onBack?: () => void  // Called when user clicks Back from create mode
}

function WelcomeModal({ approaches, onSelect, onCreate, initialMode = 'choose', initialHypothesis, exploreSource, onOpenExplore, onBackToExplore, onClose, onBack }: Props) {
  const [mode, setMode] = useState<'choose' | 'create'>(initialMode)
  const [newName, setNewName] = useState('')
  const [newHypothesis, setNewHypothesis] = useState(initialHypothesis || '')
  const [isCreating, setIsCreating] = useState(false)
  const [showNameField, setShowNameField] = useState(false)
  const [isRegenerating, setIsRegenerating] = useState(false)

  // Auto mode state
  const [autoModeEnabled, setAutoModeEnabled] = useState(true)
  const [availableModels, setAvailableModels] = useState<OpenRouterModel[]>([])
  const [selectedModel, setSelectedModel] = useState('google/gemini-3-pro-preview')
  const [loadingModels, setLoadingModels] = useState(false)

  // API key status (null = not yet checked)
  const [anthropicKeySet, setAnthropicKeySet] = useState<boolean | null>(null)
  const [openrouterKeySet, setOpenrouterKeySet] = useState<boolean | null>(null)

  // API key input state
  const [showAnthropicInput, setShowAnthropicInput] = useState(false)
  const [showOpenrouterInput, setShowOpenrouterInput] = useState(false)
  const [anthropicKeyInput, setAnthropicKeyInput] = useState('')
  const [openrouterKeyInput, setOpenrouterKeyInput] = useState('')
  const [savingKeys, setSavingKeys] = useState(false)

  // Sync mode with initialMode when it changes (e.g., when opened from ApproachSelector)
  useEffect(() => {
    setMode(initialMode)
  }, [initialMode])

  // Sync hypothesis with initialHypothesis when it changes (e.g., from Explore)
  useEffect(() => {
    if (initialHypothesis) {
      setNewHypothesis(initialHypothesis)
    }
  }, [initialHypothesis])

  // Fetch config status on mount
  useEffect(() => {
    fetchConfigStatus()
  }, [])

  const fetchConfigStatus = async () => {
    try {
      const response = await fetch('/api/config/status')
      if (response.ok) {
        const status = await response.json()
        setAnthropicKeySet(status.anthropic_key_set)
        setOpenrouterKeySet(status.openrouter_key_set)
      }
    } catch (error) {
      console.error('Failed to fetch config status:', error)
    }
  }

  const saveApiKey = async (keyType: 'anthropic' | 'openrouter') => {
    setSavingKeys(true)
    try {
      const body: Record<string, string> = {}
      if (keyType === 'anthropic' && anthropicKeyInput.trim()) {
        body.anthropic_key = anthropicKeyInput.trim()
      }
      if (keyType === 'openrouter' && openrouterKeyInput.trim()) {
        body.openrouter_key = openrouterKeyInput.trim()
      }

      const response = await fetch('/api/config/keys', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })

      if (response.ok) {
        // Refetch config status to update UI
        await fetchConfigStatus()
        // Clear input and hide
        if (keyType === 'anthropic') {
          setAnthropicKeyInput('')
          setShowAnthropicInput(false)
        } else {
          setOpenrouterKeyInput('')
          setShowOpenrouterInput(false)
        }
      } else {
        alert('Failed to save API key')
      }
    } catch (error) {
      console.error('Failed to save API key:', error)
      alert('Failed to save API key')
    } finally {
      setSavingKeys(false)
    }
  }

  // Fetch available models when auto mode is enabled
  useEffect(() => {
    if (autoModeEnabled && availableModels.length === 0) {
      fetchModels()
    }
  }, [autoModeEnabled])

  const fetchModels = async () => {
    setLoadingModels(true)
    try {
      const response = await fetch('/api/openrouter/models')
      if (response.ok) {
        const models = await response.json()
        // Sort by name and filter to popular/useful models
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

  const handleRegenerate = async () => {
    if (!exploreSource) return

    setIsRegenerating(true)
    try {
      let requestBody: Record<string, string>

      if (exploreSource.type === 'capability' && exploreSource.sourceGapName) {
        requestBody = {
          mode: 'capability_gap',
          capability_name: exploreSource.name,
          capability_description: '',
          gap_name: exploreSource.sourceGapName,
          gap_description: '',
        }
      } else if (exploreSource.type === 'gap') {
        requestBody = {
          mode: 'gap_only',
          gap_name: exploreSource.name,
          gap_description: '',
        }
      } else {
        // Capability without source gap
        requestBody = {
          mode: 'capability_gap',
          capability_name: exploreSource.name,
          capability_description: '',
          gap_name: '',
          gap_description: '',
        }
      }

      const response = await fetch('/api/gapmap/generate-hypothesis', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestBody),
      })

      if (response.ok) {
        const data = await response.json()
        setNewHypothesis(data.hypothesis)
      }
    } catch (err) {
      console.error('Failed to regenerate hypothesis:', err)
    } finally {
      setIsRegenerating(false)
    }
  }

  const handleCreate = async () => {
    if (!newHypothesis.trim()) return

    setIsCreating(true)
    let name = newName.trim()

    // If no name provided, generate one
    if (!name) {
      try {
        const response = await fetch('/api/generate-name', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ hypothesis: newHypothesis.trim() })
        })
        if (response.ok) {
          const data = await response.json()
          name = data.name || ''
        }
      } catch (err) {
        console.error('Failed to generate name:', err)
      }

      // Fallback to simple slug if still no name
      if (!name) {
        name = newHypothesis.trim().toLowerCase().replace(/[^a-z0-9]+/g, '-').slice(0, 30)
      }
    }

    onCreate(name, newHypothesis.trim(), autoModeEnabled, autoModeEnabled ? selectedModel : undefined)
    setIsCreating(false)
  }

  return (
    <div className="welcome-overlay">
      <div className="welcome-modal">
        <h1>Entailment Trees</h1>
        <p className="welcome-subtitle">
          Collaborate with AI to rigorously evaluate ideas through structured reasoning
        </p>

        {mode === 'create' && exploreSource && (
          <div className="explore-source-badge">
            <div className="source-info">
              <span className="source-type">{exploreSource.type === 'gap' ? 'Research Gap' : 'Capability'}</span>
              <span className="source-name">{exploreSource.name}</span>
              {exploreSource.sourceGapName && (
                <span className="source-gap">via {exploreSource.sourceGapName}</span>
              )}
            </div>
            <button
              className="regenerate-button"
              onClick={handleRegenerate}
              disabled={isRegenerating}
              title="Generate a different hypothesis"
            >
              {isRegenerating ? (
                <span className="regenerate-spinner" />
              ) : (
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21 2v6h-6"></path>
                  <path d="M3 12a9 9 0 0 1 15-6.7L21 8"></path>
                  <path d="M3 22v-6h6"></path>
                  <path d="M21 12a9 9 0 0 1-15 6.7L3 16"></path>
                </svg>
              )}
            </button>
          </div>
        )}

        {mode === 'choose' ? (
          <>
            <div className="welcome-options">
              <button
                className="welcome-option-button primary"
                onClick={() => setMode('create')}
              >
                <span className="option-icon">+</span>
                <span className="option-text">
                  <strong>New Approach</strong>
                  <small>Start evaluating a new idea</small>
                </span>
              </button>

              {onOpenExplore && (
                <button
                  className="welcome-option-button"
                  onClick={onOpenExplore}
                >
                  <span className="option-icon explore-icon">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <circle cx="12" cy="12" r="10"></circle>
                      <polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76"></polygon>
                    </svg>
                  </span>
                  <span className="option-text">
                    <strong>Explore Gap Map</strong>
                    <small>Browse open research problems</small>
                  </span>
                </button>
              )}

              {approaches.length > 0 && (
                <div className="existing-approaches">
                  <div className="divider">
                    <span>or continue with</span>
                  </div>
                  <div className="approach-list">
                    {approaches.map((approach) => (
                      <button
                        key={approach.folder}
                        className="approach-item"
                        onClick={() => onSelect(approach)}
                        title={approach.description || approach.name}
                      >
                        <div className="approach-name">{truncate(approach.description || approach.name, 80)}</div>
                        <div className="approach-meta">
                          {approach.num_claims} claims · {approach.num_implications} implications
                        </div>
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </>
        ) : (
          <div className="create-form">
            <div className="form-group">
              <label htmlFor="welcome-hypothesis">What idea do you want to evaluate?</label>
              <textarea
                id="welcome-hypothesis"
                value={newHypothesis}
                onChange={(e) => setNewHypothesis(e.target.value)}
                placeholder="e.g., We can detect neural signals using ultrasound reflections from the skull"
                rows={4}
                autoFocus
              />
            </div>

            {showNameField ? (
              <div className="form-group">
                <label htmlFor="welcome-name">Name (optional)</label>
                <input
                  id="welcome-name"
                  type="text"
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  placeholder="Leave blank to auto-generate"
                />
              </div>
            ) : (
              <button
                type="button"
                className="add-name-link"
                onClick={() => setShowNameField(true)}
              >
                + Add custom name
              </button>
            )}

            <div className="auto-mode-section">
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={autoModeEnabled}
                  onChange={(e) => setAutoModeEnabled(e.target.checked)}
                />
                <span className="checkbox-text">
                  <strong>Auto Mode</strong>
                  <small>AI will automatically explore and validate your hypothesis</small>
                </span>
              </label>

              {autoModeEnabled && (
                <div className="model-selector">
                  <label htmlFor="auto-model">Auto agent model:</label>
                  {loadingModels ? (
                    <span className="loading-models">Loading models...</span>
                  ) : (
                    <select
                      id="auto-model"
                      value={selectedModel}
                      onChange={(e) => setSelectedModel(e.target.value)}
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
              )}
            </div>

            <div className="form-actions">
              <button
                className="back-button"
                onClick={() => {
                  if (onClose) {
                    // Close modal entirely when opened from ApproachSelector
                    onClose()
                  } else if (onBackToExplore) {
                    // Go back to ExploreModal when coming from there
                    onBackToExplore()
                  } else {
                    // Go back to choose mode when on welcome screen
                    setMode('choose')
                    // Notify parent so it can reset its state
                    if (onBack) onBack()
                  }
                  setShowNameField(false)
                  setNewName('')
                  setNewHypothesis('')
                }}
              >
                {onClose ? 'Cancel' : onBackToExplore ? 'Back to Explore' : 'Back'}
              </button>
              <button
                className="create-button"
                onClick={handleCreate}
                disabled={
                  !newHypothesis.trim() ||
                  isCreating ||
                  anthropicKeySet === false ||
                  (autoModeEnabled && openrouterKeySet === false)
                }
              >
                {isCreating ? 'Creating...' : 'Start Evaluating'}
              </button>
            </div>

            {(anthropicKeySet === false || (autoModeEnabled && openrouterKeySet === false)) && (
              <div className="api-key-warnings">
                {anthropicKeySet === false && (
                  <div className="api-key-warning-item">
                    <div className="warning">
                      <span>ANTHROPIC_API_KEY not set</span>
                      {!showAnthropicInput && (
                        <button
                          className="enter-key-button"
                          onClick={() => setShowAnthropicInput(true)}
                        >
                          Enter Key
                        </button>
                      )}
                    </div>
                    {showAnthropicInput && (
                      <div className="api-key-input-group">
                        <input
                          type="password"
                          className="api-key-input"
                          placeholder="sk-ant-..."
                          value={anthropicKeyInput}
                          onChange={(e) => setAnthropicKeyInput(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter' && anthropicKeyInput.trim()) {
                              saveApiKey('anthropic')
                            }
                          }}
                        />
                        <button
                          className="api-key-save-button"
                          onClick={() => saveApiKey('anthropic')}
                          disabled={!anthropicKeyInput.trim() || savingKeys}
                        >
                          {savingKeys ? '...' : 'Save'}
                        </button>
                        <button
                          className="api-key-cancel-button"
                          onClick={() => {
                            setShowAnthropicInput(false)
                            setAnthropicKeyInput('')
                          }}
                        >
                          Cancel
                        </button>
                      </div>
                    )}
                  </div>
                )}
                {autoModeEnabled && openrouterKeySet === false && (
                  <div className="api-key-warning-item">
                    <div className="warning">
                      <span>OPENROUTER_API_KEY not set (required for Auto Mode)</span>
                      {!showOpenrouterInput && (
                        <button
                          className="enter-key-button"
                          onClick={() => setShowOpenrouterInput(true)}
                        >
                          Enter Key
                        </button>
                      )}
                    </div>
                    {showOpenrouterInput && (
                      <div className="api-key-input-group">
                        <input
                          type="password"
                          className="api-key-input"
                          placeholder="sk-or-..."
                          value={openrouterKeyInput}
                          onChange={(e) => setOpenrouterKeyInput(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter' && openrouterKeyInput.trim()) {
                              saveApiKey('openrouter')
                            }
                          }}
                        />
                        <button
                          className="api-key-save-button"
                          onClick={() => saveApiKey('openrouter')}
                          disabled={!openrouterKeyInput.trim() || savingKeys}
                        >
                          {savingKeys ? '...' : 'Save'}
                        </button>
                        <button
                          className="api-key-cancel-button"
                          onClick={() => {
                            setShowOpenrouterInput(false)
                            setOpenrouterKeyInput('')
                          }}
                        >
                          Cancel
                        </button>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

export default WelcomeModal
