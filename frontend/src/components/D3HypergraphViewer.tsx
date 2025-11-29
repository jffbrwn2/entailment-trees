import { useEffect, useRef, useState, useCallback } from 'react'
import * as d3 from 'd3'
import './D3HypergraphViewer.css'

interface Claim {
  id: string
  text: string
  score: number
  propagated_negative_log?: number
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

interface Hypergraph {
  metadata?: {
    name: string
    description?: string
  }
  claims: Claim[]
  implications: Implication[]
}

interface SelectedItem {
  type: 'claim' | 'implication'
  id: string
}

interface Props {
  hypergraph: Hypergraph | null
  scoreMode: 'score' | 'propagated'
  onSelect: (item: SelectedItem | null) => void
  selectedItem: SelectedItem | null
}

interface NodeData {
  id: string
  type: 'claim' | 'junction'
  x: number
  y: number
  text?: string
  score?: number
  propagated_negative_log?: number
  implication?: Implication
  _animX?: number
  _animY?: number
}

interface LinkData {
  source: NodeData
  target: NodeData
  type: 'premise-to-junction' | 'junction-to-conclusion'
  premises: string[]
  conclusion: string
  implId: string
}

function D3HypergraphViewer({ hypergraph, scoreMode, onSelect, selectedItem }: Props) {
  const svgRef = useRef<SVGSVGElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const [collapsedNodes, setCollapsedNodes] = useState<Set<string>>(new Set())
  const nodePositionsRef = useRef<Map<string, { x: number; y: number }>>(new Map())
  const conclusionToPremisesRef = useRef<Map<string, string[]>>(new Map())

  // Build implication map
  useEffect(() => {
    if (!hypergraph) return
    conclusionToPremisesRef.current.clear()
    hypergraph.implications.forEach(impl => {
      conclusionToPremisesRef.current.set(impl.conclusion, impl.premises)
    })
  }, [hypergraph])

  const isConclusion = useCallback((nodeId: string) => {
    return conclusionToPremisesRef.current.has(nodeId)
  }, [])

  const arePremisesCollapsed = useCallback((conclusionId: string) => {
    const premises = conclusionToPremisesRef.current.get(conclusionId)
    if (!premises || premises.length === 0) return false
    return premises.some(p => collapsedNodes.has(p))
  }, [collapsedNodes])

  const getEffectiveScore = useCallback((claim: Claim) => {
    if (scoreMode === 'propagated' && claim.propagated_negative_log !== undefined) {
      return Math.pow(2, -claim.propagated_negative_log) * 10
    }
    return claim.score
  }, [scoreMode])

  const getScoreColor = useCallback((score: number) => {
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
  }, [])

  const calculateTreeLayout = useCallback((
    visibleClaims: NodeData[],
    width: number,
    height: number
  ) => {
    if (!hypergraph) return { positions: new Map<string, { x: number; y: number }>(), levels: new Map<string, number>() }

    const levels = new Map<string, number>()
    const conclusionToPremises = conclusionToPremisesRef.current

    // Find root conclusions
    const allPremises = new Set<string>()
    hypergraph.implications.forEach(impl => {
      impl.premises.forEach(p => allPremises.add(p))
    })

    const rootConclusions = visibleClaims
      .filter(c => conclusionToPremises.has(c.id))
      .filter(c => !allPremises.has(c.id))
      .map(c => c.id)

    if (rootConclusions.length === 0) {
      visibleClaims
        .filter(c => conclusionToPremises.has(c.id))
        .forEach(c => rootConclusions.push(c.id))
    }

    // Calculate levels
    rootConclusions.forEach(rootId => levels.set(rootId, 0))

    let changed = true
    let iterations = 0
    while (changed && iterations < 20) {
      changed = false
      iterations++

      hypergraph.implications.forEach(impl => {
        if (collapsedNodes.has(impl.conclusion) ||
            impl.premises.some(p => collapsedNodes.has(p))) {
          return
        }

        const conclusionLevel = levels.get(impl.conclusion)
        if (conclusionLevel !== undefined) {
          const junctionId = `junction_${impl.id}`
          const junctionLevel = conclusionLevel + 1
          const premiseLevel = conclusionLevel + 2

          if (!levels.has(junctionId)) {
            levels.set(junctionId, junctionLevel)
            changed = true
          }

          impl.premises.forEach(premiseId => {
            if (!levels.has(premiseId) || levels.get(premiseId)! < premiseLevel) {
              levels.set(premiseId, premiseLevel)
              changed = true
            }
          })
        }
      })
    }

    // Calculate subtree widths
    const subtreeWidths = new Map<string, number>()

    function calculateSubtreeWidth(nodeId: string, visited = new Set<string>()): number {
      if (subtreeWidths.has(nodeId)) return subtreeWidths.get(nodeId)!
      if (visited.has(nodeId)) return 150
      visited.add(nodeId)

      const premises = conclusionToPremises.get(nodeId)
      const visiblePremises = premises ? premises.filter(p => !collapsedNodes.has(p)) : []

      if (visiblePremises.length === 0) {
        subtreeWidths.set(nodeId, 150)
        return 150
      }

      let totalWidth = 0
      visiblePremises.forEach(premiseId => {
        totalWidth += calculateSubtreeWidth(premiseId, visited)
      })
      totalWidth += (visiblePremises.length - 1) * 100

      const w = Math.max(150, totalWidth)
      subtreeWidths.set(nodeId, w)
      return w
    }

    visibleClaims.forEach(c => calculateSubtreeWidth(c.id))

    // Position nodes
    const positions = new Map<string, { x: number; y: number }>()
    const maxLevel = Math.max(...Array.from(levels.values()), 0)
    const levelSpacing = (height - 200) / (maxLevel + 1)

    function positionSubtree(nodeId: string, centerX: number, level: number) {
      const y = 100 + level * levelSpacing

      if (nodePositionsRef.current.has(nodeId)) {
        positions.set(nodeId, nodePositionsRef.current.get(nodeId)!)
      } else {
        positions.set(nodeId, { x: centerX, y })
      }

      const premises = conclusionToPremises.get(nodeId)
      const visiblePremises = premises ? premises.filter(p => !collapsedNodes.has(p)) : []

      if (visiblePremises.length === 0) return

      // Position junction
      const impl = hypergraph!.implications.find(i => i.conclusion === nodeId)
      if (impl) {
        const junctionId = `junction_${impl.id}`
        const junctionLevel = level + 1
        const junctionY = 100 + junctionLevel * levelSpacing

        if (nodePositionsRef.current.has(junctionId)) {
          positions.set(junctionId, nodePositionsRef.current.get(junctionId)!)
        } else {
          positions.set(junctionId, { x: centerX, y: junctionY })
        }
      }

      // Position children
      const premiseLevel = level + 2
      const childWidths = visiblePremises.map(p => subtreeWidths.get(p) || 150)
      const premiseSpacing = 50
      const totalWidth = childWidths.reduce((a, b) => a + b, 0) + (visiblePremises.length - 1) * premiseSpacing

      let currentX = centerX - totalWidth / 2
      visiblePremises.forEach((premiseId, i) => {
        const childCenterX = currentX + childWidths[i] / 2
        positionSubtree(premiseId, childCenterX, premiseLevel)
        currentX += childWidths[i] + premiseSpacing
      })
    }

    // Position roots
    let totalRootWidth = 0
    rootConclusions.forEach(rootId => {
      totalRootWidth += subtreeWidths.get(rootId) || 150
    })
    totalRootWidth += (rootConclusions.length - 1) * 200

    let rootX = width / 2 - totalRootWidth / 2
    rootConclusions.forEach(rootId => {
      const rootWidth = subtreeWidths.get(rootId) || 150
      positionSubtree(rootId, rootX + rootWidth / 2, 0)
      rootX += rootWidth + 200
    })

    return { positions, levels }
  }, [hypergraph, collapsedNodes])

  // Main render effect
  useEffect(() => {
    if (!hypergraph || !svgRef.current || !containerRef.current) return

    const container = containerRef.current
    const width = container.clientWidth
    const height = container.clientHeight || 600

    // Clear previous
    d3.select(svgRef.current).selectAll('*').remove()

    const svg = d3.select(svgRef.current)
      .attr('width', width)
      .attr('height', height)

    const g = svg.append('g')

    const zoom = d3.zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.1, 10])
      .on('zoom', (event) => {
        g.attr('transform', event.transform)
      })

    svg.call(zoom)
      .on('dblclick.zoom', null)
      .on('dblclick', () => {
        onSelect(null)
      })

    // Create nodes
    const claims: NodeData[] = hypergraph.claims.map(c => ({
      ...c,
      type: 'claim' as const,
      x: 0,
      y: 0
    }))

    const junctions: NodeData[] = hypergraph.implications.map(impl => ({
      id: `junction_${impl.id}`,
      type: 'junction' as const,
      x: 0,
      y: 0,
      implication: impl
    }))

    const allNodes = [...claims, ...junctions]

    // Calculate layout
    const visibleClaims = claims.filter(c => !collapsedNodes.has(c.id))
    const { positions } = calculateTreeLayout(visibleClaims, width, height)

    // Apply positions
    allNodes.forEach(node => {
      const pos = positions.get(node.id)
      if (pos) {
        node.x = pos.x
        node.y = pos.y
      } else {
        const savedPos = nodePositionsRef.current.get(node.id)
        if (savedPos) {
          node.x = savedPos.x
          node.y = savedPos.y
        } else {
          node.x = width / 2
          node.y = height / 2
        }
      }
    })

    // Create links
    const links: LinkData[] = []
    hypergraph.implications.forEach(impl => {
      const junctionId = `junction_${impl.id}`

      if (collapsedNodes.has(impl.conclusion) ||
          impl.premises.some(p => collapsedNodes.has(p))) {
        return
      }

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

    // Defs
    const defs = svg.append('defs')

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
      .attr('fill', 'var(--accent)')

    // Draw links
    function createCurvePath(d: LinkData) {
      const sourceX = d.source.x
      const sourceY = d.source.y
      const targetX = d.target.x
      const targetY = d.target.y
      const dx = targetX - sourceX
      const dy = targetY - sourceY

      if (d.type === 'premise-to-junction') {
        const cp1X = sourceX + dx * 0.3
        const cp1Y = sourceY + dy * 0.3
        const cp2X = targetX - dx * 0.2
        const cp2Y = targetY - dy * 0.2
        return `M ${sourceX},${sourceY} C ${cp1X},${cp1Y} ${cp2X},${cp2Y} ${targetX},${targetY}`
      } else {
        const cp1X = sourceX + dx * 0.3
        const cp1Y = sourceY + dy * 0.3 - 15
        const cp2X = sourceX + dx * 0.7
        const cp2Y = sourceY + dy * 0.7 - 15
        return `M ${sourceX},${sourceY} C ${cp1X},${cp1Y} ${cp2X},${cp2Y} ${targetX},${targetY}`
      }
    }

    g.append('g')
      .selectAll('path')
      .data(links)
      .join('path')
      .attr('class', d => `hyperedge ${d.type}`)
      .attr('d', createCurvePath)
      .attr('stroke', d => {
        const impl = hypergraph.implications.find(i => i.id === d.implId)
        const status = impl?.entailment_status

        if (d.type === 'junction-to-conclusion') {
          if (status === 'failed') return '#f85149'
          if (status === 'passed') return 'var(--accent)'
          return 'var(--text-secondary)'
        }
        return 'var(--text-secondary)'
      })
      .attr('stroke-width', d => {
        const dx = Math.abs(d.target.x - d.source.x)
        const isVertical = dx < 5
        const baseWidth = d.type === 'junction-to-conclusion' ? 3 : 2
        return isVertical ? baseWidth + 1 : baseWidth
      })
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
      .attr('fill', 'none')
      .attr('stroke-linecap', 'round')
      .attr('marker-end', d => d.type === 'junction-to-conclusion' ? 'url(#arrowhead)' : null)
      .attr('cursor', 'pointer')
      .on('click', (event, d) => {
        event.stopPropagation()
        onSelect({ type: 'implication', id: d.implId })
      })

    // Drag handlers
    function dragstarted(event: d3.D3DragEvent<SVGGElement, NodeData, NodeData>) {
      d3.select(event.sourceEvent.currentTarget).raise()
    }

    function dragged(event: d3.D3DragEvent<SVGGElement, NodeData, NodeData>, d: NodeData) {
      d.x = event.x
      d.y = event.y
      d3.select(event.sourceEvent.currentTarget)
        .attr('transform', `translate(${d.x},${d.y})`)

      // Update connected edges
      g.selectAll<SVGPathElement, LinkData>('.hyperedge')
        .attr('d', createCurvePath)
    }

    function dragended(_event: d3.D3DragEvent<SVGGElement, NodeData, NodeData>, d: NodeData) {
      nodePositionsRef.current.set(d.id, { x: d.x, y: d.y })
    }

    // Draw nodes
    const node = g.append('g')
      .selectAll<SVGGElement, NodeData>('g')
      .data(allNodes)
      .join('g')
      .attr('class', d => d.type === 'claim' ? 'claim-node' : 'junction-node')
      .attr('transform', d => `translate(${d.x},${d.y})`)
      .style('display', d => {
        if (d.type === 'claim') {
          return collapsedNodes.has(d.id) ? 'none' : null
        }
        // Junction visibility
        const impl = d.implication!
        if (collapsedNodes.has(impl.conclusion)) return 'none'
        if (impl.premises.some(p => collapsedNodes.has(p))) return 'none'
        return null
      })
      .call(d3.drag<SVGGElement, NodeData>()
        .filter((event) => !event.target.closest('.expand-indicator'))
        .on('start', dragstarted)
        .on('drag', dragged)
        .on('end', dragended))

    // Claim nodes
    const claimNodes = node.filter(d => d.type === 'claim')

    claimNodes.append('circle')
      .attr('r', 65)
      .attr('fill', d => getScoreColor(getEffectiveScore(d as unknown as Claim)))
      .attr('fill-opacity', 0.6)
      .attr('stroke', d => getScoreColor(getEffectiveScore(d as unknown as Claim)))
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
      .attr('cursor', 'pointer')

    // Claim text
    claimNodes.each(function(d) {
      const text = d3.select(this).append('text')
        .attr('text-anchor', 'middle')
        .attr('fill', 'var(--text-primary)')
        .attr('font-size', '10px')
        .attr('font-weight', '500')
        .attr('pointer-events', 'none')

      const words = (d.text || '').split(/\s+/)
      const maxWidth = 110
      const lineHeight = 11
      const maxLines = 10

      let line: string[] = []
      let lineNumber = 0
      let tspan = text.append('tspan')
        .attr('x', 0)
        .attr('dy', 0)

      for (let i = 0; i < words.length; i++) {
        line.push(words[i])
        tspan.text(line.join(' '))

        const node = tspan.node()
        if (node && node.getComputedTextLength() > maxWidth) {
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
    })

    // Expand/collapse indicators
    claimNodes.filter(d => isConclusion(d.id))
      .each(function(d) {
        const parentG = d3.select(this)
        const radius = 65

        const indicatorG = parentG.append('g')
          .attr('class', 'expand-indicator')
          .attr('cursor', 'pointer')
          .on('click', function(event) {
            event.stopPropagation()
            setCollapsedNodes(prev => {
              const newSet = new Set(prev)
              const premises = conclusionToPremisesRef.current.get(d.id)
              if (!premises) return prev

              const currentlyCollapsed = premises.some(p => prev.has(p))
              if (currentlyCollapsed) {
                // Expand
                premises.forEach(p => newSet.delete(p))
              } else {
                // Collapse
                premises.forEach(p => newSet.add(p))
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

    // Junction nodes
    const junctionNodes = node.filter(d => d.type === 'junction')

    junctionNodes.append('circle')
      .attr('r', 8)
      .attr('fill', d => d.implication?.type === 'OR' ? '#d29922' : '#58a6ff')
      .attr('stroke', d => d.implication?.type === 'OR' ? '#d29922' : '#58a6ff')
      .attr('stroke-width', 2)
      .attr('opacity', 0.9)
      .attr('cursor', 'pointer')

    junctionNodes.append('text')
      .text(d => d.implication?.type === 'OR' ? '∨' : '∧')
      .attr('text-anchor', 'middle')
      .attr('dy', '0.35em')
      .attr('fill', 'var(--bg-primary)')
      .attr('font-size', '12px')
      .attr('font-weight', '700')
      .attr('pointer-events', 'none')

    // Click handlers
    claimNodes.on('click', (event, d) => {
      event.stopPropagation()
      onSelect({ type: 'claim', id: d.id })
    })

    junctionNodes.on('click', (event, d) => {
      event.stopPropagation()
      if (d.implication) {
        onSelect({ type: 'implication', id: d.implication.id })
      }
    })

    // Tooltips
    claimNodes.append('title')
      .text(d => `${d.id}\n${d.text}\nScore: ${d.score}/10`)

    junctionNodes.append('title')
      .text(d => {
        const impl = d.implication!
        const type = impl.type || 'AND'
        const symbol = type === 'OR' ? '∨' : '∧'
        return `${type} junction\n${impl.id}: ${impl.premises.join(` ${symbol} `)} → ${impl.conclusion}`
      })

  }, [hypergraph, scoreMode, collapsedNodes, selectedItem, onSelect, calculateTreeLayout, getScoreColor, getEffectiveScore, isConclusion, arePremisesCollapsed])

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
    </div>
  )
}

export default D3HypergraphViewer
