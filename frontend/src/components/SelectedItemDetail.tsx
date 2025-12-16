import './SelectedItemDetail.css'

interface Claim {
  id: string
  text: string
  score: number | null
  propagated_negative_log?: number | string | null
  reasoning?: string
  evidence?: Evidence[]
  uncertainties?: string[]
  tags?: string[]
}

interface Evidence {
  type: 'simulation' | 'literature' | 'calculation'
  source?: string
  lines?: string
  code?: string
  reference_text?: string
  equations?: string
  program?: string
}

interface Implication {
  id: string
  premises: string[]
  conclusion: string
  type?: 'AND' | 'OR'
  reasoning: string
  entailment_status?: 'passed' | 'failed'
  entailment_explanation?: string
}

interface SelectedItem {
  type: 'claim' | 'implication'
  id: string
}

interface Props {
  selectedItem: SelectedItem | null
  claims: Claim[]
  implications: Implication[]
  scoreMode: 'score' | 'propagated'
  onClose: () => void
}

function getScoreColor(score: number | null): string {
  if (score === null) return 'rgb(128, 128, 128)'
  const clampedScore = Math.max(0, Math.min(10, score))
  if (clampedScore <= 5) {
    const t = clampedScore / 5
    const r = 248
    const g = Math.round(81 + (217 - 81) * t)
    const b = Math.round(73 + (34 - 73) * t)
    return `rgb(${r}, ${g}, ${b})`
  } else {
    const t = (clampedScore - 5) / 5
    const r = Math.round(217 - (217 - 63) * t)
    const g = Math.round(217 - (217 - 185) * t)
    const b = Math.round(34 + (80 - 34) * t)
    return `rgb(${r}, ${g}, ${b})`
  }
}

function getEffectiveScore(claim: Claim, scoreMode: 'score' | 'propagated'): number | null {
  if (scoreMode === 'propagated') {
    // null or "Infinity" means failed entailment or error, show as 0
    if (claim.propagated_negative_log === null || claim.propagated_negative_log === "Infinity") {
      return 0
    }
    // "-Infinity" would mean perfect certainty (shouldn't happen in practice)
    if (claim.propagated_negative_log === "-Infinity") {
      return 10
    }
    if (claim.propagated_negative_log !== undefined && typeof claim.propagated_negative_log === 'number') {
      return Math.pow(2, -claim.propagated_negative_log) * 10
    }
  }
  return claim.score
}

function SelectedItemDetail({ selectedItem, claims, implications, scoreMode, onClose }: Props) {
  if (!selectedItem) {
    return (
      <div className="detail-panel detail-empty">
        <p>Click on a node or edge to view details</p>
      </div>
    )
  }

  if (selectedItem.type === 'claim') {
    const claim = claims.find(c => c.id === selectedItem.id)
    if (!claim) return null

    return (
      <div className="detail-panel">
        <div className="detail-header">
          <span className="detail-id">{claim.id}</span>
          <button className="detail-close" onClick={onClose}>×</button>
        </div>

        <div className="detail-text">{claim.text}</div>

        <div className="detail-scores">
          {scoreMode === 'score' ? (
            <span className="detail-score" style={{ background: `${getScoreColor(claim.score)}33`, color: getScoreColor(claim.score) }}>
              Score: {claim.score !== null ? `${claim.score.toFixed(1)}/10` : 'Not evaluated'}
            </span>
          ) : (
            <span className="detail-score" style={{ background: `${getScoreColor(getEffectiveScore(claim, scoreMode))}33`, color: getScoreColor(getEffectiveScore(claim, scoreMode)) }}>
              Cost: {claim.propagated_negative_log === null || claim.propagated_negative_log === "Infinity"
                ? '∞ (P = 0)'
                : typeof claim.propagated_negative_log === 'number'
                  ? `${claim.propagated_negative_log.toFixed(3)} (P = ${Math.pow(2, -claim.propagated_negative_log).toFixed(3)})`
                  : claim.propagated_negative_log ?? 'Not computed'}
            </span>
          )}
        </div>

        {claim.tags && claim.tags.length > 0 && (
          <div className="detail-tags">
            {claim.tags.map(tag => (
              <span key={tag} className="detail-tag">{tag}</span>
            ))}
          </div>
        )}

        {claim.reasoning && (
          <div className="detail-section">
            <div className="detail-section-title">Reasoning</div>
            <div className="detail-section-content">{claim.reasoning}</div>
          </div>
        )}

        {claim.evidence && claim.evidence.length > 0 && (
          <div className="detail-section">
            <div className="detail-section-title">Evidence</div>
            {claim.evidence.map((e, i) => (
              <div key={i} className="evidence-item">
                <div className="evidence-type">{e.type}</div>
                {e.type === 'literature' && (
                  <>
                    <div className="evidence-source">{e.source}</div>
                    {e.reference_text && (
                      <div className="evidence-text">{e.reference_text}</div>
                    )}
                  </>
                )}
                {e.type === 'simulation' && (
                  <>
                    <div className="evidence-source">
                      {e.source}{e.lines ? `:${e.lines}` : ''}
                    </div>
                    {e.code && (
                      <pre className="evidence-code">{e.code}</pre>
                    )}
                  </>
                )}
                {e.type === 'calculation' && (
                  <>
                    {e.equations && (
                      <div className="evidence-equations">{e.equations}</div>
                    )}
                    {e.program && (
                      <pre className="evidence-code">{e.program}</pre>
                    )}
                  </>
                )}
              </div>
            ))}
          </div>
        )}

        {claim.uncertainties && claim.uncertainties.length > 0 && (
          <div className="detail-section">
            <div className="detail-section-title uncertainty-title">Uncertainties</div>
            {claim.uncertainties.map((u, i) => (
              <div key={i} className="uncertainty-item">{u}</div>
            ))}
          </div>
        )}
      </div>
    )
  }

  if (selectedItem.type === 'implication') {
    const impl = implications.find(i => i.id === selectedItem.id)
    if (!impl) return null

    const formula = `(${impl.premises.join(', ')}) → ${impl.conclusion}`

    return (
      <div className="detail-panel">
        <div className="detail-header">
          <span className="detail-id">{impl.id}</span>
          <button className="detail-close" onClick={onClose}>×</button>
        </div>

        <div className="detail-formula">{formula}</div>

        {impl.entailment_status && (
          <div className="detail-scores">
            <span className={`entailment-status ${impl.entailment_status}`}>
              Entailment: {impl.entailment_status === 'passed' ? '✓ Passed' : '✗ Failed'}
            </span>
          </div>
        )}

        <div className="detail-section">
          <div className="detail-section-title">Reasoning</div>
          <div className="detail-section-content">{impl.reasoning}</div>
        </div>

        {impl.entailment_explanation && (
          <div className="detail-section">
            <div className="detail-section-title">Entailment Check Details</div>
            <pre className="entailment-explanation">{impl.entailment_explanation}</pre>
          </div>
        )}
      </div>
    )
  }

  return null
}

export default SelectedItemDetail
