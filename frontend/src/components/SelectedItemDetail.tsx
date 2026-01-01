import { useState, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'

import type { Claim, Implication, SelectedItem, Evidence } from '../types/hypergraph'
import { api, Note } from '../services/api'

import './SelectedItemDetail.css'

interface Props {
  selectedItem: SelectedItem | null
  claims: Claim[]
  implications: Implication[]
  folder: string | null
  notes: Record<string, Note>
  onClose: () => void
  onNoteUpdate: () => void
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

// Component for displaying and editing notes
function NoteEditor({
  itemId,
  folder,
  existingNote,
  originalContent,
  onUpdate,
}: {
  itemId: string
  folder: string | null
  existingNote: Note | null
  originalContent: string
  onUpdate: () => void
}) {
  const [isEditing, setIsEditing] = useState(false)
  const [noteText, setNoteText] = useState(existingNote?.text || '')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    setNoteText(existingNote?.text || '')
    setIsEditing(false)
  }, [itemId, existingNote?.text])

  const handleSave = async () => {
    if (!folder || !noteText.trim()) return

    setSaving(true)
    try {
      await api.approaches.createNote(folder, itemId, noteText.trim(), originalContent)
      setIsEditing(false)
      onUpdate()
    } catch (err) {
      console.error('Failed to save note:', err)
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async () => {
    if (!folder) return

    setSaving(true)
    try {
      await api.approaches.deleteNote(folder, itemId)
      setNoteText('')
      setIsEditing(false)
      onUpdate()
    } catch (err) {
      console.error('Failed to delete note:', err)
    } finally {
      setSaving(false)
    }
  }

  if (existingNote && !isEditing) {
    return (
      <div className="note-section">
        <div className="note-header">
          <span className="note-label">Note</span>
          {existingNote.content_changed && (
            <span className="note-warning" title="The content has changed since this note was written">
              Content changed
            </span>
          )}
        </div>
        <div className="note-content">{existingNote.text}</div>
        <div className="note-actions">
          <button className="note-edit-btn" onClick={() => setIsEditing(true)}>Edit</button>
          <button className="note-delete-btn" onClick={handleDelete} disabled={saving}>Delete</button>
        </div>
      </div>
    )
  }

  if (isEditing || existingNote) {
    return (
      <div className="note-section">
        <div className="note-header">
          <span className="note-label">{existingNote ? 'Edit Note' : 'Add Note'}</span>
        </div>
        <textarea
          className="note-textarea"
          value={noteText}
          onChange={(e) => setNoteText(e.target.value)}
          placeholder="Write a note..."
          rows={3}
        />
        <div className="note-actions">
          <button
            className="note-save-btn"
            onClick={handleSave}
            disabled={saving || !noteText.trim()}
          >
            {saving ? 'Saving...' : 'Save'}
          </button>
          <button
            className="note-cancel-btn"
            onClick={() => {
              setNoteText(existingNote?.text || '')
              setIsEditing(false)
            }}
          >
            Cancel
          </button>
        </div>
      </div>
    )
  }

  return (
    <button className="add-note-btn" onClick={() => setIsEditing(true)}>
      + Add Note
    </button>
  )
}

function SelectedItemDetail({ selectedItem, claims, implications, folder, notes, onClose, onNoteUpdate }: Props) {
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

    const existingNote = notes[claim.id] || null

    return (
      <div className="detail-panel">
        <div className="detail-header">
          <span className="detail-id">{claim.id}</span>
          <button className="detail-close" onClick={onClose}>×</button>
        </div>

        <div className="detail-text">{claim.text}</div>

        <NoteEditor
          itemId={claim.id}
          folder={folder}
          existingNote={existingNote}
          originalContent={claim.text}
          onUpdate={onNoteUpdate}
        />

        {claim.tags && claim.tags.length > 0 && (
          <div className="detail-tags">
            {claim.tags.map(tag => (
              <span key={tag} className="detail-tag">{tag}</span>
            ))}
          </div>
        )}

        {(claim.cost !== undefined || claim.evidence_epistemic_cost !== undefined) && (
          <div className="detail-section">
            <div className="detail-section-title">Cost</div>
            <div className="detail-section-content cost-breakdown">
              <div className="cost-line">
                <strong>Total:</strong>{' '}
                {claim.cost === null || claim.cost === "Infinity"
                  ? '∞ (P = 0)'
                  : typeof claim.cost === 'number'
                    ? `${claim.cost.toFixed(3)} (P = ${Math.pow(2, -claim.cost).toFixed(3)})`
                    : '—'}
              </div>
              <div className="cost-line">
                <span className="cost-label">Evidence Epistemic Cost:</span>{' '}
                {claim.evidence_epistemic_cost === null || claim.evidence_epistemic_cost === "Infinity"
                  ? '∞'
                  : typeof claim.evidence_epistemic_cost === 'number'
                    ? claim.evidence_epistemic_cost.toFixed(3)
                    : '—'}
              </div>
              <div className="cost-line">
                <span className="cost-label">Experimental Epistemic Cost:</span>{' '}
                {claim.experimental_epistemic_cost === null || claim.experimental_epistemic_cost === "Infinity"
                  ? '∞'
                  : typeof claim.experimental_epistemic_cost === 'number'
                    ? claim.experimental_epistemic_cost.toFixed(3)
                    : '—'}
              </div>
            </div>
          </div>
        )}

        {claim.reasoning && (
          <div className="detail-section">
            <div className="detail-section-title">Evidence Reasoning</div>
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
    const existingNote = notes[impl.id] || null

    return (
      <div className="detail-panel">
        <div className="detail-header">
          <span className="detail-id">{impl.id}</span>
          <button className="detail-close" onClick={onClose}>×</button>
        </div>

        <div className="detail-formula">{formula}</div>

        <NoteEditor
          itemId={impl.id}
          folder={folder}
          existingNote={existingNote}
          originalContent={formula}
          onUpdate={onNoteUpdate}
        />

        {impl.entailment_status && (
          <div className="detail-scores">
            <span className={`entailment-status ${impl.entailment_status}`}>
              Entailment: {impl.entailment_status === 'passed' ? '✓ Passed' : '✗ Failed'}
            </span>
          </div>
        )}

        <div className="detail-section">
          <div className="detail-section-title">Implication Reasoning</div>
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
