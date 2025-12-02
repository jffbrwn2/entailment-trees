import { useState } from 'react'
import type { Approach } from '../App'
import './WelcomeModal.css'

interface Props {
  approaches: Approach[]
  onSelect: (approach: Approach) => void
  onCreate: (name: string, hypothesis: string) => void
}

function WelcomeModal({ approaches, onSelect, onCreate }: Props) {
  const [mode, setMode] = useState<'choose' | 'create'>('choose')
  const [newName, setNewName] = useState('')
  const [newHypothesis, setNewHypothesis] = useState('')
  const [isCreating, setIsCreating] = useState(false)
  const [showNameField, setShowNameField] = useState(false)

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

    onCreate(name, newHypothesis.trim())
    setIsCreating(false)
  }

  return (
    <div className="welcome-overlay">
      <div className="welcome-modal">
        <h1>Entailment Trees</h1>
        <p className="welcome-subtitle">
          Collaborate with AI to rigorously evaluate ideas through structured reasoning
        </p>

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
                      >
                        <div className="approach-name">{approach.name}</div>
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

            <div className="form-actions">
              <button
                className="back-button"
                onClick={() => {
                  setMode('choose')
                  setShowNameField(false)
                  setNewName('')
                  setNewHypothesis('')
                }}
              >
                Back
              </button>
              <button
                className="create-button"
                onClick={handleCreate}
                disabled={!newHypothesis.trim() || isCreating}
              >
                {isCreating ? 'Creating...' : 'Start Evaluating'}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default WelcomeModal
