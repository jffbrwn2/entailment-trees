import { useRef, useMemo, useState } from 'react'
import type { D3HypergraphViewerProps, Hypergraph, SelectedItem } from './types'
import { useTreeLayout } from './useTreeLayout'
import { useD3Graph } from './useD3Graph'
import '../D3HypergraphViewer.css'

interface Warning {
  message: string
  ref: SelectedItem | null
}

// Parse validation error to extract claim/implication reference
function parseErrorReference(error: string, hypergraph: Hypergraph): { type: 'claim' | 'implication'; id: string } | null {
  // Match patterns like "claims[1]" or "implications[2]"
  const claimMatch = error.match(/^claims\[(\d+)\]/)
  const implMatch = error.match(/^implications\[(\d+)\]/)

  if (claimMatch) {
    const index = parseInt(claimMatch[1], 10)
    if (index >= 0 && index < hypergraph.claims.length) {
      return { type: 'claim', id: hypergraph.claims[index].id }
    }
  }

  if (implMatch) {
    const index = parseInt(implMatch[1], 10)
    if (index >= 0 && index < hypergraph.implications.length) {
      return { type: 'implication', id: hypergraph.implications[index].id }
    }
  }

  return null
}

// Compute warnings for failed entailments and leaf nodes without evidence
function computeWarnings(hypergraph: Hypergraph): Warning[] {
  const warnings: Warning[] = []

  // Find claims that are conclusions of implications
  const conclusions = new Set(hypergraph.implications.map(impl => impl.conclusion))

  // Check for leaf nodes without evidence
  for (const claim of hypergraph.claims) {
    const isLeaf = !conclusions.has(claim.id)
    if (isLeaf && (!claim.evidence || claim.evidence.length === 0)) {
      warnings.push({
        message: `${claim.id}: Leaf node without evidence`,
        ref: { type: 'claim', id: claim.id }
      })
    }
  }

  // Check for failed or unchecked entailments
  for (const impl of hypergraph.implications) {
    if (impl.entailment_status === 'failed') {
      warnings.push({
        message: `${impl.id}: Entailment failed`,
        ref: { type: 'implication', id: impl.id }
      })
    } else if (!impl.entailment_status) {
      warnings.push({
        message: `${impl.id}: Entailment not checked`,
        ref: { type: 'implication', id: impl.id }
      })
    }
  }

  return warnings
}

function ValidationIndicator({ hypergraph, onSelect, onSendMessage }: {
  hypergraph: Hypergraph
  onSelect: (item: SelectedItem | null) => void
  onSendMessage?: (message: string) => void
}) {
  const warnings = useMemo(() => computeWarnings(hypergraph), [hypergraph])
  const errors = hypergraph.metadata?.validation?.errors || []
  const hasErrors = errors.length > 0
  const hasWarnings = warnings.length > 0

  // Determine status: error > warning > valid
  const status = hasErrors ? 'error' : hasWarnings ? 'warning' : 'valid'
  const count = hasErrors ? errors.length : hasWarnings ? warnings.length : 0

  // Don't show indicator if everything is valid and no validation metadata
  if (status === 'valid' && !hypergraph.metadata?.validation) {
    return null
  }

  const handleFix = () => {
    if (!onSendMessage) return

    const issues: string[] = []

    // Collect errors
    errors.forEach(error => {
      issues.push(`Error: ${error}`)
    })

    // Collect warnings
    warnings.forEach(warning => {
      issues.push(`Warning: ${warning.message}`)
    })

    const message = `Please fix the following issues in the hypergraph:\n\n${issues.join('\n')}\n\nFor unchecked entailments, run the entailment checker. For missing evidence, find appropriate evidence. For validation errors, fix the structural issues.`
    onSendMessage(message)
  }

  return (
    <div className={`validation-indicator ${status}`}>
      <div className="validation-circle">
        {status === 'valid' ? '✓' : count}
      </div>
      {(hasErrors || hasWarnings) && (
        <div className="validation-popup">
          {hasErrors && (
            <>
              <div className="validation-popup-header">
                {errors.length} validation error{errors.length !== 1 ? 's' : ''}
              </div>
              <div className="validation-popup-content">
                {errors.map((error, i) => {
                  const ref = parseErrorReference(error, hypergraph)
                  return (
                    <div
                      key={`error-${i}`}
                      className={`validation-error ${ref ? 'clickable' : ''}`}
                      onClick={() => ref && onSelect(ref)}
                    >
                      {error}
                    </div>
                  )
                })}
              </div>
            </>
          )}
          {hasWarnings && (
            <>
              <div className={`validation-popup-header warning-header`}>
                {warnings.length} warning{warnings.length !== 1 ? 's' : ''}
              </div>
              <div className="validation-popup-content">
                {warnings.map((warning, i) => (
                  <div
                    key={`warning-${i}`}
                    className={`validation-warning ${warning.ref ? 'clickable' : ''}`}
                    onClick={() => warning.ref && onSelect(warning.ref)}
                  >
                    {warning.message}
                  </div>
                ))}
              </div>
            </>
          )}
          {onSendMessage && (
            <div className="validation-popup-footer">
              <button className="validation-fix-button" onClick={handleFix}>
                Fix Issues
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function D3HypergraphViewer({
  hypergraph,
  scoreMode,
  onScoreModeChange,
  onSelect,
  selectedItem,
  resetKey,
  onReset,
  onCleanup,
  onDelete,
  onSendMessage,
}: D3HypergraphViewerProps) {
  const svgRef = useRef<SVGSVGElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const [legendCollapsed, setLegendCollapsed] = useState(false)
  const [depthCollapsed, setDepthCollapsed] = useState(false)

  const {
    collapsedNodes,
    setCollapsedNodes,
    maxDepth,
    setMaxDepth,
    maxAvailableDepth,
    orphanClaims,
    conclusionToPremises,
    isConclusion,
    arePremisesCollapsed,
    getAllDescendants,
    getExclusiveDescendants,
    calculateTreeLayout,
    nodePositionsRef,
  } = useTreeLayout(hypergraph, resetKey)

  useD3Graph({
    hypergraph,
    svgRef,
    containerRef,
    scoreMode,
    selectedItem,
    collapsedNodes,
    setCollapsedNodes,
    orphanClaims,
    conclusionToPremises,
    isConclusion,
    arePremisesCollapsed,
    getAllDescendants,
    getExclusiveDescendants,
    calculateTreeLayout,
    nodePositionsRef,
    onSelect,
    onDelete,
    resetKey,
  })

  if (!hypergraph) {
    return (
      <div className="d3-viewer-empty">
        <p>Select an approach to view the hypergraph</p>
      </div>
    )
  }

  return (
    <div ref={containerRef} className="d3-viewer-container">
      <svg ref={svgRef} className="d3-viewer-svg" />
      <div className="graph-toolbar">
        <div className="toolbar-trigger">
          <span className="toolbar-arrow">▼</span>
        </div>
        <div className="toolbar-dropdown">
          <div className="toolbar-item">
            <label>View:</label>
            <select
              value={scoreMode}
              onChange={(e) => onScoreModeChange(e.target.value as 'score' | 'propagated')}
            >
              <option value="score">Score</option>
              <option value="propagated">Cost</option>
            </select>
          </div>
          <button className="toolbar-item" onClick={onReset}>
            Reset Layout
          </button>
          <button className="toolbar-item" onClick={onCleanup}>
            Clean Up
          </button>
        </div>
      </div>
      <div className="graph-controls-left">
        <div className={`graph-legend ${legendCollapsed ? 'collapsed' : ''}`}>
          <div className="legend-header" onClick={() => setLegendCollapsed(!legendCollapsed)}>
            <span className="legend-title">Legend</span>
            <span className="legend-toggle">{legendCollapsed ? '▶' : '▼'}</span>
          </div>
          {!legendCollapsed && (
            <>
              <div className="legend-section">
                <div className="legend-section-title">Score</div>
                <div className="legend-gradient">
                  <div className="legend-bar" />
                  <div className="legend-labels">
                    <span>0 (false)</span>
                    <span>5</span>
                    <span>10 (true)</span>
                  </div>
                </div>
                <div className="legend-item">
                  <span className="legend-color" style={{ background: 'rgb(128, 128, 128)' }} />
                  <span>Not evaluated</span>
                </div>
              </div>
              <div className="legend-section">
                <div className="legend-section-title">Logic Nodes</div>
                <div className="legend-item">
                  <span className="legend-node and-node">∧</span>
                  <span>AND (all required)</span>
                </div>
                <div className="legend-item">
                  <span className="legend-node or-node">∨</span>
                  <span>OR (any sufficient)</span>
                </div>
              </div>
              <div className="legend-section">
                <div className="legend-section-title">Edges</div>
                <div className="legend-item">
                  <span className="legend-line passed" />
                  <span>Passed</span>
                </div>
                <div className="legend-item">
                  <span className="legend-line failed" />
                  <span>Failed</span>
                </div>
                <div className="legend-item">
                  <span className="legend-line unchecked" />
                  <span>Not checked</span>
                </div>
              </div>
            </>
          )}
        </div>
        {maxAvailableDepth > 0 && (
          <div className={`depth-control-panel ${depthCollapsed ? 'collapsed' : ''}`}>
            <div className="depth-header" onClick={() => setDepthCollapsed(!depthCollapsed)}>
              <span className="depth-title">Depth</span>
              <span className="depth-toggle">{depthCollapsed ? '▶' : '▼'}</span>
            </div>
            {!depthCollapsed && (
              <div className="depth-options">
                <button
                  className={`depth-option ${maxDepth === null ? 'active' : ''}`}
                  onClick={() => setMaxDepth(null)}
                >
                  All
                </button>
                {Array.from({ length: maxAvailableDepth + 1 }, (_, i) => (
                  <button
                    key={i}
                    className={`depth-option ${maxDepth === i ? 'active' : ''}`}
                    onClick={() => setMaxDepth(i)}
                  >
                    {i}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
      <ValidationIndicator hypergraph={hypergraph} onSelect={onSelect} onSendMessage={onSendMessage} />
    </div>
  )
}

export default D3HypergraphViewer
