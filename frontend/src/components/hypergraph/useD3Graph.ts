import { useEffect, useRef, useCallback } from 'react'
import * as d3 from 'd3'
import type { Hypergraph, Claim, NodeData, LinkData, SelectedItem } from './types'
import { getStructuralSignature, getScoreColor, getEffectiveScore, createCurvePath, computeEvidenceBacked } from './utils'

interface UseD3GraphParams {
  hypergraph: Hypergraph | null
  svgRef: React.RefObject<SVGSVGElement>
  containerRef: React.RefObject<HTMLDivElement>
  scoreMode: 'score' | 'propagated'
  selectedItem: SelectedItem | null
  collapsedNodes: Set<string>
  setCollapsedNodes: React.Dispatch<React.SetStateAction<Set<string>>>
  orphanClaims: Set<string>
  conclusionToPremises: Map<string, string[]>
  isConclusion: (nodeId: string) => boolean
  arePremisesCollapsed: (conclusionId: string) => boolean
  getAllDescendants: (nodeId: string, visited?: Set<string>) => string[]
  getExclusiveDescendants: (nodeId: string) => string[]
  calculateTreeLayout: (visibleClaims: NodeData[], width: number, height: number) => {
    positions: Map<string, { x: number; y: number }>
    levels: Map<string, number>
  }
  nodePositionsRef: React.MutableRefObject<Map<string, { x: number; y: number }>>
  onSelect: (item: SelectedItem | null) => void
  onDelete?: (claimId: string) => void
  resetKey?: number
}

export function useD3Graph({
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
}: UseD3GraphParams) {
  // Refs for D3 elements
  const gRef = useRef<d3.Selection<SVGGElement, unknown, null, undefined> | null>(null)
  const nodesDataRef = useRef<NodeData[]>([])
  const linksDataRef = useRef<LinkData[]>([])
  const isInitializedRef = useRef(false)
  const prevStructureRef = useRef<string>('')
  const zoomRef = useRef<d3.ZoomBehavior<SVGSVGElement, unknown> | null>(null)

  // Clear state on reset
  useEffect(() => {
    prevStructureRef.current = ''
    nodesDataRef.current = []
    linksDataRef.current = []
  }, [resetKey])

  // Animation helper for edges
  const animateEdgesForNode = useCallback((node: NodeData) => {
    if (!gRef.current) return

    gRef.current.selectAll<SVGPathElement, LinkData>('.hyperedge').each(function(d) {
      let updated = false

      if (d.source.id === node.id || d.target.id === node.id) {
        updated = true
      }

      if (updated) {
        const pathD = createCurvePath(d)
        d3.select(this).attr('d', pathD)
      }
    })
  }, [])

  // Initialize SVG structure (only when structure changes or reset)
  useEffect(() => {
    if (!hypergraph || !svgRef.current || !containerRef.current) {
      isInitializedRef.current = false
      prevStructureRef.current = ''
      return
    }

    // Check if the structure actually changed
    const currentStructure = getStructuralSignature(hypergraph)
    const structureChanged = currentStructure !== prevStructureRef.current

    // Skip full re-initialization if structure hasn't changed and already initialized
    if (!structureChanged && isInitializedRef.current) {
      return
    }

    prevStructureRef.current = currentStructure

    const container = containerRef.current
    const width = container.clientWidth
    const height = container.clientHeight || 600

    // Clear previous state on full re-render
    d3.select(svgRef.current).selectAll('*').remove()
    nodePositionsRef.current.clear()
    isInitializedRef.current = false

    const svg = d3.select(svgRef.current)
      .attr('width', width)
      .attr('height', height)

    const g = svg.append('g')
    gRef.current = g

    const zoom = d3.zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.1, 10])
      .on('zoom', (event) => {
        g.attr('transform', event.transform)
      })

    zoomRef.current = zoom
    svg.call(zoom)
      .call(zoom.transform, d3.zoomIdentity)  // Reset zoom/pan to initial state
      .on('dblclick.zoom', null)
      .on('dblclick', () => {
        onSelect(null)
      })

    // Defs for markers
    const defs = svg.append('defs')

    // Default arrowhead (gray)
    defs.append('marker')
      .attr('id', 'arrowhead')
      .attr('viewBox', '0 -5 10 10')
      .attr('refX', 20)
      .attr('refY', 0)
      .attr('markerWidth', 6)
      .attr('markerHeight', 6)
      .attr('orient', 'auto')
      .append('path')
      .attr('d', 'M0,-5L10,0L0,5')
      .attr('fill', 'var(--text-secondary)')

    // Passed arrowhead (green)
    defs.append('marker')
      .attr('id', 'arrowhead-passed')
      .attr('viewBox', '0 -5 10 10')
      .attr('refX', 20)
      .attr('refY', 0)
      .attr('markerWidth', 6)
      .attr('markerHeight', 6)
      .attr('orient', 'auto')
      .append('path')
      .attr('d', 'M0,-5L10,0L0,5')
      .attr('fill', '#3fb950')

    // Failed arrowhead (red)
    defs.append('marker')
      .attr('id', 'arrowhead-failed')
      .attr('viewBox', '0 -5 10 10')
      .attr('refX', 20)
      .attr('refY', 0)
      .attr('markerWidth', 6)
      .attr('markerHeight', 6)
      .attr('orient', 'auto')
      .append('path')
      .attr('d', 'M0,-5L10,0L0,5')
      .attr('fill', '#f85149')

    // Create nodes data
    const claims: NodeData[] = hypergraph.claims.map(c => ({
      ...c,
      type: 'claim' as const,
      x: width / 2,
      y: height / 2
    }))

    const junctions: NodeData[] = hypergraph.implications.map(impl => ({
      id: `junction_${impl.id}`,
      type: 'junction' as const,
      x: width / 2,
      y: height / 2,
      implication: impl
    }))

    const allNodes = [...claims, ...junctions]
    nodesDataRef.current = allNodes

    // Initial layout
    const visibleClaims = claims.filter(c => !collapsedNodes.has(c.id))
    const { positions } = calculateTreeLayout(visibleClaims, width, height)

    // Apply initial positions
    allNodes.forEach(node => {
      const pos = positions.get(node.id)
      if (pos) {
        node.x = pos.x
        node.y = pos.y
      }
    })

    // Create links data
    const links: LinkData[] = []
    hypergraph.implications.forEach(impl => {
      const junctionId = `junction_${impl.id}`

      impl.premises.forEach(premise => {
        const sourceNode = allNodes.find(n => n.id === premise)
        const targetNode = allNodes.find(n => n.id === junctionId)
        if (sourceNode && targetNode) {
          links.push({
            source: sourceNode,
            target: targetNode,
            type: 'premise-to-junction',
            premises: impl.premises,
            conclusion: impl.conclusion,
            implId: impl.id
          })
        }
      })

      const junctionNode = allNodes.find(n => n.id === junctionId)
      const conclusionNode = allNodes.find(n => n.id === impl.conclusion)
      if (junctionNode && conclusionNode) {
        links.push({
          source: junctionNode,
          target: conclusionNode,
          type: 'junction-to-conclusion',
          premises: impl.premises,
          conclusion: impl.conclusion,
          implId: impl.id
        })
      }
    })
    linksDataRef.current = links

    // Create groups for different elements
    g.append('g').attr('class', 'orphan-region')
    g.append('g').attr('class', 'links-group')
    g.append('g').attr('class', 'nodes-group')

    isInitializedRef.current = true
  }, [hypergraph, onSelect, resetKey, collapsedNodes, calculateTreeLayout, nodePositionsRef, svgRef, containerRef])

  // Update visualization (with transitions for collapse/expand)
  useEffect(() => {
    if (!hypergraph || !gRef.current || !isInitializedRef.current) return

    const g = gRef.current
    const container = containerRef.current
    if (!container) return

    const width = container.clientWidth
    const height = container.clientHeight || 600
    const allNodes = nodesDataRef.current
    const links = linksDataRef.current

    // Compute evidence-backed status for all claims
    const evidenceBacked = computeEvidenceBacked(hypergraph)

    // Calculate new layout
    const claims = allNodes.filter(n => n.type === 'claim')
    const visibleClaims = claims.filter(c => !collapsedNodes.has(c.id))
    const { positions } = calculateTreeLayout(visibleClaims, width, height)

    // Helper to get parent position for animation
    const getParentPosition = (nodeId: string): { x: number; y: number } => {
      // Find which implication has this as a premise
      for (const impl of hypergraph.implications) {
        if (impl.premises.includes(nodeId)) {
          const conclusionNode = allNodes.find(n => n.id === impl.conclusion)
          if (conclusionNode) {
            return { x: conclusionNode.x, y: conclusionNode.y }
          }
        }
      }
      // For junctions, find parent conclusion
      if (nodeId.startsWith('junction_')) {
        const implId = nodeId.replace('junction_', '')
        const impl = hypergraph.implications.find(i => i.id === implId)
        if (impl) {
          const conclusionNode = allNodes.find(n => n.id === impl.conclusion)
          if (conclusionNode) {
            return { x: conclusionNode.x, y: conclusionNode.y }
          }
        }
      }
      return { x: width / 2, y: height / 2 }
    }

    const transitionDuration = 400

    // Update all nodes with new target positions
    allNodes.forEach(node => {
      const pos = positions.get(node.id)
      if (pos) {
        node.x = pos.x
        node.y = pos.y
      }
    })

    // Fit view to visible nodes (excluding orphans)
    if (zoomRef.current && svgRef.current) {
      const visibleNodes = allNodes.filter(n => {
        // Exclude collapsed claims
        if (n.type === 'claim') {
          if (collapsedNodes.has(n.id)) return false
          // Exclude orphan claims
          if (orphanClaims.has(n.id)) return false
          return true
        }
        // Filter junctions whose implications are collapsed or orphaned
        if (n.type === 'junction' && n.implication) {
          const impl = n.implication
          // Exclude if conclusion is collapsed or orphaned
          if (collapsedNodes.has(impl.conclusion) || orphanClaims.has(impl.conclusion)) return false
          // Exclude if all premises are collapsed or orphaned
          if (!impl.premises.some(p => !collapsedNodes.has(p) && !orphanClaims.has(p))) return false
          return true
        }
        return true
      })

      if (visibleNodes.length > 0) {
        const padding = 100
        const nodeRadius = 85

        // Calculate bounding box of visible nodes
        const minX = Math.min(...visibleNodes.map(n => n.x)) - nodeRadius - padding
        const maxX = Math.max(...visibleNodes.map(n => n.x)) + nodeRadius + padding
        const minY = Math.min(...visibleNodes.map(n => n.y)) - nodeRadius - padding
        const maxY = Math.max(...visibleNodes.map(n => n.y)) + nodeRadius + padding

        const bboxWidth = maxX - minX
        const bboxHeight = maxY - minY

        // Calculate scale to fit
        const scale = Math.min(
          width / bboxWidth,
          height / bboxHeight,
          1.5  // Max zoom level
        )

        // Calculate center
        const centerX = (minX + maxX) / 2
        const centerY = (minY + maxY) / 2

        // Create transform to center and scale
        const transform = d3.zoomIdentity
          .translate(width / 2, height / 2)
          .scale(scale)
          .translate(-centerX, -centerY)

        // Animate zoom with same duration as node transitions
        d3.select(svgRef.current)
          .transition()
          .duration(transitionDuration)
          .ease(d3.easeCubicInOut)
          .call(zoomRef.current.transform, transform)
      }
    }

    // Update orphan region
    const orphanRegion = g.select<SVGGElement>('.orphan-region')
    const visibleOrphanClaims = claims.filter(c => orphanClaims.has(c.id) && !collapsedNodes.has(c.id))
    const hasOrphans = visibleOrphanClaims.length > 0

    orphanRegion.selectAll('*').remove()

    if (hasOrphans) {
      orphanRegion.append('line')
        .attr('x1', 50)
        .attr('y1', 170)
        .attr('x2', width - 50)
        .attr('y2', 170)
        .attr('stroke', 'var(--border)')
        .attr('stroke-width', 1)
        .attr('stroke-dasharray', '5,5')

      orphanRegion.append('text')
        .attr('x', width / 2)
        .attr('y', 185)
        .attr('text-anchor', 'middle')
        .attr('fill', 'var(--text-secondary)')
        .attr('font-size', '11px')
        .attr('font-style', 'italic')
        .text('Disconnected claims (drag to connect)')
    }

    // Update edges
    const linksGroup = g.select<SVGGElement>('.links-group')

    const visibleLinks = links.filter(link => {
      const impl = hypergraph.implications.find(i => i.id === link.implId)
      if (!impl) return false
      if (collapsedNodes.has(impl.conclusion)) return false
      if (impl.premises.some(p => collapsedNodes.has(p))) return false
      return true
    })

    const edgeSelection = linksGroup.selectAll<SVGPathElement, LinkData>('.hyperedge')
      .data(visibleLinks, d => `${d.source.id}-${d.target.id}`)

    edgeSelection.exit()
      .transition()
      .duration(transitionDuration)
      .attr('opacity', 0)
      .remove()

    const enteringEdges = edgeSelection.enter()
      .append('path')
      .attr('class', d => `hyperedge ${d.type}`)
      .attr('d', createCurvePath)
      .attr('stroke', d => {
        const impl = hypergraph.implications.find(i => i.id === d.implId)
        const status = impl?.entailment_status
        if (status === 'failed') return '#f85149'
        if (status === 'passed') return '#3fb950'
        return 'var(--text-secondary)'
      })
      .attr('stroke-width', d => d.type === 'junction-to-conclusion' ? 4 : 3)
      .attr('fill', 'none')
      .attr('stroke-linecap', 'round')
      .attr('marker-end', d => {
        if (d.type !== 'junction-to-conclusion') return null
        const impl = hypergraph.implications.find(i => i.id === d.implId)
        const status = impl?.entailment_status
        if (status === 'failed') return 'url(#arrowhead-failed)'
        if (status === 'passed') return 'url(#arrowhead-passed)'
        return 'url(#arrowhead)'
      })
      .attr('cursor', 'pointer')
      .attr('opacity', 0)
      .on('dblclick', (event, d) => {
        event.stopPropagation()
        onSelect({ type: 'implication', id: d.implId })
      })

    enteringEdges
      .transition()
      .duration(transitionDuration)
      .attr('opacity', d => {
        if (!selectedItem) return 0.7
        if (selectedItem.type === 'claim') {
          return d.premises.includes(selectedItem.id) || d.conclusion === selectedItem.id ? 1 : 0.2
        }
        if (selectedItem.type === 'implication') {
          return d.implId === selectedItem.id ? 1 : 0.2
        }
        return 0.7
      })

    edgeSelection
      .transition()
      .duration(transitionDuration)
      .attr('d', createCurvePath)
      .attr('opacity', d => {
        if (!selectedItem) return 0.7
        if (selectedItem.type === 'claim') {
          return d.premises.includes(selectedItem.id) || d.conclusion === selectedItem.id ? 1 : 0.2
        }
        if (selectedItem.type === 'implication') {
          return d.implId === selectedItem.id ? 1 : 0.2
        }
        return 0.7
      })

    // Update nodes
    const nodesGroup = g.select<SVGGElement>('.nodes-group')

    const nodeSelection = nodesGroup.selectAll<SVGGElement, NodeData>('.graph-node')
      .data(allNodes, d => d.id)

    // Enter new nodes
    const enteringNodes = nodeSelection.enter()
      .append('g')
      .attr('class', d => `graph-node ${d.type === 'claim' ? 'claim-node' : 'junction-node'}`)
      .attr('transform', d => `translate(${d.x},${d.y}) scale(0)`)

    // Add claim node visuals
    enteringNodes.filter(d => d.type === 'claim').each(function(d) {
      const node = d3.select(this)
      const isBacked = evidenceBacked.get(d.id) ?? false
      const effectiveScore = getEffectiveScore(d as unknown as Claim, scoreMode, isBacked)

      const isHypothesis = d.id === 'hypothesis'
      node.append('circle')
        .attr('r', isHypothesis ? 95 : 85)
        .attr('fill', getScoreColor(effectiveScore))
        .attr('fill-opacity', 0.6)
        .attr('stroke', isHypothesis ? 'var(--text-primary)' : getScoreColor(effectiveScore))
        .attr('stroke-width', isHypothesis ? 4 : 2)
        .attr('stroke-dasharray', isHypothesis ? '8,4' : null)
        .attr('cursor', 'pointer')

      // Text with word wrapping
      const text = node.append('text')
        .attr('class', 'node-text')
        .attr('text-anchor', 'middle')
        .attr('fill', 'var(--text-primary)')
        .attr('font-size', '15px')
        .attr('font-weight', '500')
        .attr('pointer-events', 'none')

      const words = (d.text || '').split(/\s+/)
      const maxWidth = 145
      const lineHeight = 17
      const maxLines = 10

      let line: string[] = []
      let lineNumber = 0
      let tspan = text.append('tspan')
        .attr('x', 0)
        .attr('dy', 0)

      for (let i = 0; i < words.length; i++) {
        line.push(words[i])
        tspan.text(line.join(' '))

        const tspanNode = tspan.node()
        if (tspanNode && tspanNode.getComputedTextLength() > maxWidth) {
          if (lineNumber >= maxLines - 1) {
            line.pop()
            tspan.text(line.join(' ') + '...')
            break
          }
          line.pop()
          tspan.text(line.join(' '))
          line = [words[i]]
          lineNumber++
          tspan = text.append('tspan')
            .attr('x', 0)
            .attr('dy', lineHeight)
            .text(words[i])
        }
      }

      const totalHeight = (lineNumber + 1) * lineHeight
      text.attr('transform', `translate(0, ${-totalHeight / 2 + 5})`)

      node.append('title')
        .text(`${d.id}\n${d.text}\nScore: ${d.score !== null ? `${d.score}/10` : 'Not evaluated'}`)
    })

    // Add junction node visuals
    enteringNodes.filter(d => d.type === 'junction').each(function(d) {
      const node = d3.select(this)

      node.append('circle')
        .attr('r', 12)
        .attr('fill', d.implication?.type === 'OR' ? '#d29922' : '#58a6ff')
        .attr('stroke', d.implication?.type === 'OR' ? '#d29922' : '#58a6ff')
        .attr('stroke-width', 3)
        .attr('opacity', 0.9)
        .attr('cursor', 'pointer')

      node.append('text')
        .text(d.implication?.type === 'OR' ? '∨' : '∧')
        .attr('text-anchor', 'middle')
        .attr('dy', '0.35em')
        .attr('fill', 'var(--bg-primary)')
        .attr('font-size', '16px')
        .attr('font-weight', '700')
        .attr('pointer-events', 'none')

      node.append('title')
        .text(() => {
          const impl = d.implication!
          const type = impl.type || 'AND'
          const symbol = type === 'OR' ? '∨' : '∧'
          return `${type} junction\n${impl.id}: ${impl.premises.join(` ${symbol} `)} → ${impl.conclusion}`
        })
    })

    // Merge and update all nodes
    const allNodeElements = nodeSelection.merge(enteringNodes)

    // Animate node visibility and position
    allNodeElements.each(function(d) {
      const node = d3.select(this)
      const isVisible = (() => {
        if (d.type === 'claim') return !collapsedNodes.has(d.id)
        const impl = d.implication
        if (!impl) return false
        return !collapsedNodes.has(impl.conclusion) && !impl.premises.some(p => collapsedNodes.has(p))
      })()

      const currentTransform = node.attr('transform')
      const isCurrentlyHidden = currentTransform?.includes('scale(0)')

      if (isVisible && isCurrentlyHidden) {
        // Expand animation
        const parentPos = getParentPosition(d.id)

        node
          .attr('transform', `translate(${parentPos.x},${parentPos.y}) scale(0)`)
          .transition()
          .duration(transitionDuration)
          .ease(d3.easeCubicOut)
          .attr('transform', `translate(${d.x},${d.y}) scale(1)`)
          .tween('position', function() {
            const interpolateX = d3.interpolate(parentPos.x, d.x)
            const interpolateY = d3.interpolate(parentPos.y, d.y)
            return function(t) {
              d._animX = interpolateX(t)
              d._animY = interpolateY(t)
              animateEdgesForNode(d)
            }
          })
          .on('end', function() {
            delete d._animX
            delete d._animY
          })
      } else if (!isVisible && !isCurrentlyHidden) {
        // Collapse animation
        const parentPos = getParentPosition(d.id)

        node
          .transition()
          .duration(transitionDuration)
          .ease(d3.easeCubicIn)
          .attr('transform', `translate(${parentPos.x},${parentPos.y}) scale(0)`)
          .tween('position', function() {
            const startX = d.x
            const startY = d.y
            const interpolateX = d3.interpolate(startX, parentPos.x)
            const interpolateY = d3.interpolate(startY, parentPos.y)
            return function(t) {
              d._animX = interpolateX(t)
              d._animY = interpolateY(t)
              animateEdgesForNode(d)
            }
          })
          .on('end', function() {
            delete d._animX
            delete d._animY
          })
      } else if (isVisible) {
        // Just update position
        node
          .transition()
          .duration(transitionDuration)
          .ease(d3.easeCubicInOut)
          .attr('transform', `translate(${d.x},${d.y}) scale(1)`)
      }
    })

    // Update expand/collapse indicators
    allNodeElements.filter(d => d.type === 'claim' && isConclusion(d.id)).each(function(d) {
      const node = d3.select(this)
      const radius = 85

      node.select('.expand-indicator').remove()

      const indicatorG = node.append('g')
        .attr('class', 'expand-indicator')
        .attr('cursor', 'pointer')
        .on('click', function(event) {
          event.stopPropagation()
          setCollapsedNodes(prev => {
            const newSet = new Set(prev)
            const premises = conclusionToPremises.get(d.id)
            if (!premises) return prev

            const currentlyCollapsed = premises.some(p => prev.has(p))

            if (currentlyCollapsed) {
              // When expanding, only reveal direct premises (one level)
              premises.forEach(p => newSet.delete(p))
            } else {
              // When collapsing, only collapse nodes that don't have other paths to root
              // This ensures nodes like c7 (premise for both c12 and hypothesis)
              // remain visible when collapsing c12
              const exclusiveDescendants = getExclusiveDescendants(d.id)
              exclusiveDescendants.forEach(p => newSet.add(p))
            }
            return newSet
          })
        })

      indicatorG.append('circle')
        .attr('cx', radius * 0.6)
        .attr('cy', radius * 0.6)
        .attr('r', 12)
        .attr('fill', 'var(--accent)')
        .attr('stroke', 'var(--text-primary)')
        .attr('stroke-width', 2)

      const isCollapsed = arePremisesCollapsed(d.id)
      indicatorG.append('text')
        .attr('class', 'expand-symbol')
        .attr('x', radius * 0.6)
        .attr('y', radius * 0.6)
        .attr('text-anchor', 'middle')
        .attr('dy', '0.35em')
        .attr('fill', 'var(--bg-primary)')
        .attr('font-size', '14px')
        .attr('font-weight', '700')
        .attr('pointer-events', 'none')
        .text(isCollapsed ? '+' : '−')
    })

    // Add delete indicator to selected claim
    allNodeElements.filter(d => d.type === 'claim').each(function(d) {
      const node = d3.select(this)
      const radius = 85

      node.select('.delete-indicator').remove()

      const isSelected = selectedItem?.type === 'claim' && selectedItem.id === d.id
      if (!onDelete || !isSelected || d.id === 'hypothesis') return

      const deleteG = node.append('g')
        .attr('class', 'delete-indicator')
        .attr('cursor', 'pointer')
        .on('click', function(event) {
          event.stopPropagation()
          if (confirm(`Delete claim "${d.id}"?\n\nThis will also remove any implications that reference this claim.`)) {
            onDelete(d.id)
          }
        })

      deleteG.append('circle')
        .attr('cx', -radius * 0.75)
        .attr('cy', -radius * 0.75)
        .attr('r', 12)
        .attr('fill', '#f85149')
        .attr('stroke', 'var(--text-primary)')
        .attr('stroke-width', 2)

      deleteG.append('text')
        .attr('x', -radius * 0.75)
        .attr('y', -radius * 0.75)
        .attr('text-anchor', 'middle')
        .attr('dy', '0.35em')
        .attr('fill', 'white')
        .attr('font-size', '14px')
        .attr('font-weight', '700')
        .attr('pointer-events', 'none')
        .text('×')
    })

    // Add drag behavior with 500ms hold delay
    let dragTimeout: ReturnType<typeof setTimeout> | null = null
    let isDragging = false
    let dragStartPos: { x: number; y: number } | null = null

    const drag = d3.drag<SVGGElement, NodeData>()
      .filter((event) => !event.target.closest('.expand-indicator') && !event.target.closest('.delete-indicator'))
      .on('start', function(event) {
        isDragging = false
        dragStartPos = { x: event.x, y: event.y }
        const node = d3.select(this)

        // Start drag after 200ms hold
        dragTimeout = setTimeout(() => {
          isDragging = true
          node.raise()
          node.style('cursor', 'grabbing')
        }, 50)
      })
      .on('drag', function(event, d) {
        // Cancel drag initiation if mouse moves before timeout
        if (!isDragging && dragStartPos) {
          const dx = event.x - dragStartPos.x
          const dy = event.y - dragStartPos.y
          if (Math.sqrt(dx * dx + dy * dy) > 5) {
            // Mouse moved too much, cancel the hold timer
            if (dragTimeout) {
              clearTimeout(dragTimeout)
              dragTimeout = null
            }
            return
          }
        }

        if (!isDragging) return

        d.x = event.x
        d.y = event.y
        d3.select(this)
          .attr('transform', `translate(${d.x},${d.y}) scale(1)`)

        g.selectAll<SVGPathElement, LinkData>('.hyperedge')
          .attr('d', createCurvePath)
      })
      .on('end', function(_event, d) {
        if (dragTimeout) {
          clearTimeout(dragTimeout)
          dragTimeout = null
        }
        d3.select(this).style('cursor', 'pointer')

        if (isDragging) {
          nodePositionsRef.current.set(d.id, { x: d.x, y: d.y })
        }
        isDragging = false
        dragStartPos = null
      })

    allNodeElements.call(drag)

    // Double-click to select (single click does nothing for claims)
    allNodeElements.filter(d => d.type === 'claim')
      .on('click', null)  // Remove single click
      .on('dblclick', (event, d) => {
        if (event.target.closest('.expand-indicator')) return
        if (event.target.closest('.delete-indicator')) return
        event.stopPropagation()
        onSelect({ type: 'claim', id: d.id })
      })

    allNodeElements.filter(d => d.type === 'junction')
      .on('click', null)  // Remove single click
      .on('dblclick', (event, d) => {
        event.stopPropagation()
        if (d.implication) {
          onSelect({ type: 'implication', id: d.implication.id })
        }
      })

    // Update node text and colors
    allNodeElements.filter(d => d.type === 'claim').each(function(d) {
      const claim = hypergraph.claims.find(c => c.id === d.id)
      if (!claim) return

      d.text = claim.text
      d.score = claim.score ?? undefined
      d.propagated_negative_log = typeof claim.propagated_negative_log === 'number'
        ? claim.propagated_negative_log
        : undefined

      const node = d3.select(this)

      node.select('title')
        .text(`${d.id}\n${claim.text}\nScore: ${claim.score !== null ? `${claim.score}/10` : 'Not evaluated'}`)

      // Update text
      const textElement = node.select<SVGTextElement>('.node-text')
      if (textElement.node()) {
        textElement.selectAll('*').remove()

        const maxWidth = 145
        const lineHeight = 17
        const maxLines = 10
        const words = (claim.text || '').split(/\s+/)
        let line: string[] = []
        let lineNumber = 0

        let tspan = textElement.append('tspan')
          .attr('x', 0)
          .attr('dy', 0)

        for (let i = 0; i < words.length; i++) {
          line.push(words[i])
          tspan.text(line.join(' '))

          const tspanNode = tspan.node()
          if (tspanNode && tspanNode.getComputedTextLength() > maxWidth) {
            if (lineNumber >= maxLines - 1) {
              line.pop()
              tspan.text(line.join(' ') + '...')
              break
            }
            line.pop()
            tspan.text(line.join(' '))
            line = [words[i]]
            lineNumber++
            tspan = textElement.append('tspan')
              .attr('x', 0)
              .attr('dy', lineHeight)
              .text(words[i])
          }
        }

        const totalHeight = (lineNumber + 1) * lineHeight
        textElement.attr('transform', `translate(0, ${-totalHeight / 2 + 5})`)
      }
    })

    // Update node colors based on score mode and selection
    allNodeElements.filter(d => d.type === 'claim')
      .select('circle')
      .attr('fill', d => {
        const claim = hypergraph.claims.find(c => c.id === d.id)
        if (!claim) return 'rgb(128, 128, 128)'
        const isBacked = evidenceBacked.get(d.id) ?? false
        const effectiveScore = getEffectiveScore(claim, scoreMode, isBacked)
        return getScoreColor(effectiveScore)
      })
      .attr('stroke', d => {
        const claim = hypergraph.claims.find(c => c.id === d.id)
        if (!claim) return 'rgb(128, 128, 128)'
        const isBacked = evidenceBacked.get(d.id) ?? false
        const effectiveScore = getEffectiveScore(claim, scoreMode, isBacked)
        return getScoreColor(effectiveScore)
      })
      .attr('stroke-width', d => {
        if (!selectedItem) return 2
        if (selectedItem.type === 'claim' && selectedItem.id === d.id) return 4
        return 2
      })
      .attr('opacity', d => {
        if (!selectedItem) return 1
        if (selectedItem.type === 'claim') {
          return selectedItem.id === d.id ? 1 : 0.3
        }
        if (selectedItem.type === 'implication') {
          const impl = hypergraph.implications.find(i => i.id === selectedItem.id)
          if (impl && (impl.premises.includes(d.id) || impl.conclusion === d.id)) return 1
          return 0.3
        }
        return 1
      })

  }, [
    hypergraph,
    collapsedNodes,
    selectedItem,
    scoreMode,
    onSelect,
    onDelete,
    calculateTreeLayout,
    animateEdgesForNode,
    isConclusion,
    arePremisesCollapsed,
    getAllDescendants,
    getExclusiveDescendants,
    setCollapsedNodes,
    conclusionToPremises,
    orphanClaims,
    nodePositionsRef,
    containerRef,
    svgRef,
  ])
}
