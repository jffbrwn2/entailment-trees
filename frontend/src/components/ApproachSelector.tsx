import { useState } from 'react'
import type { Approach } from '../App'
import './ApproachSelector.css'

interface Props {
  approaches: Approach[]
  currentApproach: Approach | null
  onSelect: (approach: Approach) => void
  onCreate: (name: string, hypothesis: string) => void
}

function ApproachSelector({ approaches, currentApproach, onSelect, onCreate }: Props) {
  const [showDropdown, setShowDropdown] = useState(false)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [newName, setNewName] = useState('')
  const [newHypothesis, setNewHypothesis] = useState('')

  const handleCreate = () => {
    if (newName.trim() && newHypothesis.trim()) {
      onCreate(newName.trim(), newHypothesis.trim())
      setNewName('')
      setNewHypothesis('')
      setShowCreateModal(false)
    }
  }

  return (
    <div className="approach-selector">
      <button
        className="selector-button"
        onClick={() => setShowDropdown(!showDropdown)}
      >
        {currentApproach ? currentApproach.name : 'Select Approach'}
        <span className="arrow">▼</span>
      </button>

      {showDropdown && (
        <div className="dropdown">
          <div className="dropdown-header">
            <span>Approaches</span>
            <button
              className="create-button"
              onClick={() => {
                setShowDropdown(false)
                setShowCreateModal(true)
              }}
            >
              + New
            </button>
          </div>

          <div className="dropdown-list">
            {approaches.length === 0 ? (
              <div className="empty-state">
                No approaches yet. Create one to get started.
              </div>
            ) : (
              approaches.map((approach) => (
                <button
                  key={approach.folder}
                  className={`dropdown-item ${
                    currentApproach?.folder === approach.folder ? 'active' : ''
                  }`}
                  onClick={() => {
                    onSelect(approach)
                    setShowDropdown(false)
                  }}
                >
                  <div className="item-name">{approach.name}</div>
                  <div className="item-meta">
                    {approach.num_claims} claims · {approach.num_implications} implications
                  </div>
                </button>
              ))
            )}
          </div>
        </div>
      )}

      {showCreateModal && (
        <div className="modal-overlay" onClick={() => setShowCreateModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2>New Approach</h2>

            <div className="form-group">
              <label htmlFor="name">Name</label>
              <input
                id="name"
                type="text"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                placeholder="e.g., Ultrasound Neural Recording"
                autoFocus
              />
            </div>

            <div className="form-group">
              <label htmlFor="hypothesis">Hypothesis</label>
              <textarea
                id="hypothesis"
                value={newHypothesis}
                onChange={(e) => setNewHypothesis(e.target.value)}
                placeholder="e.g., We can detect neural signals using ultrasound"
                rows={3}
              />
            </div>

            <div className="modal-actions">
              <button
                className="cancel-button"
                onClick={() => setShowCreateModal(false)}
              >
                Cancel
              </button>
              <button
                className="submit-button"
                onClick={handleCreate}
                disabled={!newName.trim() || !newHypothesis.trim()}
              >
                Create
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default ApproachSelector
