import { useRef } from 'react'
import type { D3HypergraphViewerProps, Hypergraph } from './types'
import { useTreeLayout } from './useTreeLayout'
import { useD3Graph } from './useD3Graph'
import '../D3HypergraphViewer.css'

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

function D3HypergraphViewer({
  hypergraph,
  scoreMode,
  onSelect,
  selectedItem,
  resetKey,
  onDelete,
}: D3HypergraphViewerProps) {
  const svgRef = useRef<SVGSVGElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)

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
      <div className="graph-legend">
        <div className="legend-title">Score</div>
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
        {maxAvailableDepth > 0 && (
          <div className="depth-control">
            <label htmlFor="depth-select">Depth</label>
            <select
              id="depth-select"
              value={maxDepth === null ? 'all' : maxDepth}
              onChange={(e) => {
                const val = e.target.value
                setMaxDepth(val === 'all' ? null : parseInt(val, 10))
              }}
            >
              <option value="all">All</option>
              {Array.from({ length: maxAvailableDepth + 1 }, (_, i) => (
                <option key={i} value={i}>{i}</option>
              ))}
            </select>
          </div>
        )}
      </div>
      {hypergraph.metadata?.validation && (
        <div className={`validation-indicator ${hypergraph.metadata.validation.valid ? 'valid' : 'error'}`}>
          <div className="validation-circle">
            {hypergraph.metadata.validation.valid ? '✓' : hypergraph.metadata.validation.errors.length}
          </div>
          {!hypergraph.metadata.validation.valid && (
            <div className="validation-popup">
              <div className="validation-popup-header">
                {hypergraph.metadata.validation.errors.length} validation error{hypergraph.metadata.validation.errors.length !== 1 ? 's' : ''}
              </div>
              <div className="validation-popup-content">
                {hypergraph.metadata.validation.errors.map((error, i) => {
                  const ref = parseErrorReference(error, hypergraph)
                  return (
                    <div
                      key={i}
                      className={`validation-error ${ref ? 'clickable' : ''}`}
                      onClick={() => ref && onSelect(ref)}
                    >
                      {error}
                    </div>
                  )
                })}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default D3HypergraphViewer
