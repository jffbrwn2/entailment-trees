import ReactMarkdown from 'react-markdown'
import type { Claim, Implication, SelectedItem } from '../types/hypergraph'
import './SelectedItemDetail.css'

interface Props {
  selectedItem: SelectedItem | null
  claims: Claim[]
  implications: Implication[]
  scoreMode: 'score' | 'propagated'
  onClose: () => void
}

// Parse XML tags from entailment explanation
function parseEntailmentExplanation(explanation: string): {
  analysis: string
  valid: string
  redundantPremises: string
  degeneratePremises: string
  suggestions: string
} {
  const extractTag = (text: string, tag: string): string => {
    const pattern = new RegExp(`<${tag}>(.*?)</${tag}>`, 'is')
    const match = text.match(pattern)
    return match ? match[1].trim() : ''
  }

  return {
    analysis: extractTag(explanation, 'analysis'),
    valid: extractTag(explanation, 'valid'),
    redundantPremises: extractTag(explanation, 'redundant_premises'),
    degeneratePremises: extractTag(explanation, 'degenerate_premises'),
    suggestions: extractTag(explanation, 'suggestions'),
  }
}

function getScoreColor(score: number | null): string {
  if (score === null) {
    const isLightMode = document.documentElement.getAttribute('data-theme') === 'light'
    return isLightMode ? 'rgb(200, 200, 200)' : 'rgb(128, 128, 128)'
  }
  const clampedScore = Math.max(0, Math.min(10, score))
  // Muted color palette: coral red -> amber -> teal green
  if (clampedScore <= 5) {
    const t = clampedScore / 5
    const r = Math.round(180 - (180 - 170) * t)
    const g = Math.round(85 + (135 - 85) * t)
    const b = Math.round(80 + (75 - 80) * t)
    return `rgb(${r}, ${g}, ${b})`
  } else {
    const t = (clampedScore - 5) / 5
    const r = Math.round(170 - (170 - 75) * t)
    const g = Math.round(135 + (145 - 135) * t)
    const b = Math.round(75 + (110 - 75) * t)
    return `rgb(${r}, ${g}, ${b})`
  }
}

function getEffectiveScore(claim: Claim, scoreMode: 'score' | 'propagated'): number | null {
  if (scoreMode === 'propagated') {
    // null or "Infinity" means failed entailment or error, show as 0
    if (claim.cost === null || claim.cost === "Infinity") {
      return 0
    }
    // "-Infinity" would mean perfect certainty (shouldn't happen in practice)
    if (claim.cost === "-Infinity") {
      return 10
    }
    if (claim.cost !== undefined && typeof claim.cost === 'number') {
      return Math.pow(2, -claim.cost) * 10
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
              Cost: {claim.cost === null || claim.cost === "Infinity"
                ? '∞ (P = 0)'
                : typeof claim.cost === 'number'
                  ? `${claim.cost.toFixed(3)} (P = ${Math.pow(2, -claim.cost).toFixed(3)})`
                  : claim.cost ?? 'Not computed'}
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
            <div className="detail-section-content">
              <ReactMarkdown>{claim.reasoning}</ReactMarkdown>
            </div>
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
          <div className="detail-section-content">
            <ReactMarkdown>{impl.reasoning}</ReactMarkdown>
          </div>
        </div>

        {impl.entailment_explanation && (() => {
          const parsed = parseEntailmentExplanation(impl.entailment_explanation)
          return (
            <div className="detail-section">
              <div className="detail-section-title">Entailment Check Details</div>
              <div className="entailment-details">
                {parsed.analysis && (
                  <div className="entailment-analysis">
                    <ReactMarkdown>{parsed.analysis}</ReactMarkdown>
                  </div>
                )}
                {(parsed.redundantPremises && parsed.redundantPremises.toLowerCase() !== 'none') && (
                  <div className="entailment-warning">
                    <strong>Redundant premises:</strong> {parsed.redundantPremises}
                  </div>
                )}
                {(parsed.degeneratePremises && parsed.degeneratePremises.toLowerCase() !== 'none') && (
                  <div className="entailment-warning">
                    <strong>Degenerate premises:</strong> {parsed.degeneratePremises}
                  </div>
                )}
                {(parsed.suggestions && parsed.suggestions.toLowerCase() !== 'none') && (
                  <div className="entailment-suggestions">
                    <strong>Suggestions:</strong>
                    <ReactMarkdown>{parsed.suggestions}</ReactMarkdown>
                  </div>
                )}
              </div>
            </div>
          )
        })()}
      </div>
    )
  }

  return null
}

export default SelectedItemDetail
