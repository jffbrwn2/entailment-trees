import { useState } from 'react'
import type { Approach } from '../App'
import './ApproachSelector.css'

interface Props {
  approaches: Approach[]
  currentApproach: Approach | null
  onSelect: (approach: Approach) => void
  onRequestCreate: () => void
}

function ApproachSelector({ approaches, currentApproach, onSelect, onRequestCreate }: Props) {
  const [showDropdown, setShowDropdown] = useState(false)

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
                onRequestCreate()
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
    </div>
  )
}

export default ApproachSelector
