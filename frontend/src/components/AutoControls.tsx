import './AutoControls.css'

interface Props {
  active: boolean
  paused: boolean
  turnCount: number
  maxTurns: number
  onStart: () => void
  onPause: () => void
  onResume: () => void
  onStop: () => void
}

function AutoControls({
  active,
  paused,
  turnCount,
  maxTurns,
  onStart,
  onPause,
  onResume,
  onStop,
}: Props) {
  const getStatusText = () => {
    if (!active && !paused) return 'Auto mode ready'
    if (paused) return 'Auto mode paused'
    return 'Auto agent working...'
  }

  return (
    <div className="auto-controls">
      <div className="auto-status">
        <span className={`status-indicator ${active ? 'active' : ''} ${paused ? 'paused' : ''}`} />
        <span className="status-text">{getStatusText()}</span>
        {(active || paused) && (
          <span className="turn-counter">
            Turn {turnCount}/{maxTurns}
          </span>
        )}
      </div>
      <div className="auto-buttons">
        {!active && !paused && (
          <button className="auto-button start" onClick={onStart} title="Start auto mode">
            Start
          </button>
        )}
        {active && !paused && (
          <button className="auto-button pause" onClick={onPause} title="Pause auto mode">
            Pause
          </button>
        )}
        {paused && (
          <button className="auto-button resume" onClick={onResume} title="Resume auto mode">
            Resume
          </button>
        )}
        {(active || paused) && (
          <button className="auto-button stop" onClick={onStop} title="Stop auto mode">
            Stop
          </button>
        )}
      </div>
    </div>
  )
}

export default AutoControls
