import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import type { Claim, Implication, SelectedItem, Evidence, ScoreMode } from '../types/hypergraph'
import { api } from '../services/api'
import './SelectedItemDetail.css'

interface Props {
  selectedItem: SelectedItem | null
  claims: Claim[]
  implications: Implication[]
  scoreMode: ScoreMode
  folder: string | null
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

function costToScore(costValue: number | string | null | undefined): number | null {
  if (costValue === null || costValue === undefined || costValue === "Infinity") {
    return 0
  }
  if (costValue === "-Infinity") {
    return 10
  }
  if (typeof costValue === 'number') {
    return Math.pow(2, -costValue) * 10
  }
  return null
}

function getEffectiveScore(claim: Claim, scoreMode: ScoreMode): number | null {
  switch (scoreMode) {
    case 'score':
      return claim.score
    case 'evidence_cost':
      return costToScore(claim.evidence_epistemic_cost)
    case 'experimental_cost':
      return costToScore(claim.experimental_epistemic_cost)
    case 'cost':
      return costToScore(claim.cost)
    default:
      return claim.score
  }
}

// Component for simulation evidence with on-demand code loading
function SimulationEvidence({
  evidence,
  folder,
}: {
  evidence: Evidence
  folder: string | null
}) {
  const [code, setCode] = useState<string | null>(evidence.code || null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleViewCode = async () => {
    if (!folder || !evidence.source || !evidence.lines) return

    setLoading(true)
    setError(null)
    try {
      const result = await api.approaches.getSourceCode(folder, evidence.source, evidence.lines)
      setCode(result.code)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load code')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="evidence-item">
      <div className="evidence-type">{evidence.type}</div>
      <div className="evidence-source">
        {evidence.source}{evidence.lines ? `:${evidence.lines}` : ''}
      </div>
      {code ? (
        <pre className="evidence-code">{code}</pre>
      ) : (
        <div className="evidence-code-actions">
          {loading ? (
            <span className="evidence-loading">Loading...</span>
          ) : error ? (
            <span className="evidence-error">{error}</span>
          ) : (
            <button
              className="view-code-button"
              onClick={handleViewCode}
              disabled={!folder || !evidence.source || !evidence.lines}
            >
              View Code
            </button>
          )}
        </div>
      )}
    </div>
  )
}

function SelectedItemDetail({ selectedItem, claims, implications, scoreMode, folder, onClose }: Props) {
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
          <span className="detail-score" style={{ background: `${getScoreColor(getEffectiveScore(claim, scoreMode))}33`, color: getScoreColor(getEffectiveScore(claim, scoreMode)) }}>
            {scoreMode === 'score' && (
              <>Score: {claim.score !== null ? `${claim.score.toFixed(1)}/10` : 'Not evaluated'}</>
            )}
            {scoreMode === 'evidence_cost' && (
              <>Evidence Cost: {claim.evidence_epistemic_cost === null || claim.evidence_epistemic_cost === "Infinity"
                ? '∞'
                : typeof claim.evidence_epistemic_cost === 'number'
                  ? claim.evidence_epistemic_cost.toFixed(3)
                  : '—'}</>
            )}
            {scoreMode === 'experimental_cost' && (
              <>Experimental Cost: {claim.experimental_epistemic_cost === null || claim.experimental_epistemic_cost === "Infinity"
                ? '∞'
                : typeof claim.experimental_epistemic_cost === 'number'
                  ? claim.experimental_epistemic_cost.toFixed(3)
                  : '—'}</>
            )}
            {scoreMode === 'cost' && (
              <>Total Cost: {claim.cost === null || claim.cost === "Infinity"
                ? '∞'
                : typeof claim.cost === 'number'
                  ? claim.cost.toFixed(3)
                  : '—'}</>
            )}
          </span>
          {scoreMode !== 'score' && (
            <div className="detail-cost-breakdown">
              <span className="cost-component">
                Evidence: {claim.evidence_epistemic_cost === null || claim.evidence_epistemic_cost === "Infinity"
                  ? '∞'
                  : typeof claim.evidence_epistemic_cost === 'number'
                    ? claim.evidence_epistemic_cost.toFixed(3)
                    : '—'}
              </span>
              <span className="cost-component">
                Experimental: {claim.experimental_epistemic_cost === null || claim.experimental_epistemic_cost === "Infinity"
                  ? '∞'
                  : typeof claim.experimental_epistemic_cost === 'number'
                    ? claim.experimental_epistemic_cost.toFixed(3)
                    : '—'}
              </span>
            </div>
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
            {claim.evidence.map((e, i) => {
              if (e.type === 'simulation') {
                return (
                  <SimulationEvidence
                    key={i}
                    evidence={e}
                    folder={folder}
                  />
                )
              }
              return (
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
              )
            })}
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
