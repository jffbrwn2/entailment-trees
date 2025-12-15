import { useState, useEffect, useCallback, useRef, useMemo } from 'react'
import type { Hypergraph, NodeData } from './types'

interface TreeLayoutResult {
  positions: Map<string, { x: number; y: number }>
  levels: Map<string, number>
}

interface UseTreeLayoutReturn {
  collapsedNodes: Set<string>
  setCollapsedNodes: React.Dispatch<React.SetStateAction<Set<string>>>
  maxDepth: number | null
  setMaxDepth: React.Dispatch<React.SetStateAction<number | null>>
  maxAvailableDepth: number
  orphanClaims: Set<string>
  conclusionToPremises: Map<string, string[]>
  nodeDepths: Map<string, number>
  isConclusion: (nodeId: string) => boolean
  arePremisesCollapsed: (conclusionId: string) => boolean
  getAllDescendants: (nodeId: string, visited?: Set<string>) => string[]
  calculateTreeLayout: (visibleClaims: NodeData[], width: number, height: number) => TreeLayoutResult
  nodePositionsRef: React.MutableRefObject<Map<string, { x: number; y: number }>>
}

export function useTreeLayout(
  hypergraph: Hypergraph | null,
  resetKey?: number
): UseTreeLayoutReturn {
  const [collapsedNodes, setCollapsedNodes] = useState<Set<string>>(new Set())
  const [maxDepth, setMaxDepth] = useState<number | null>(null)
  const [maxAvailableDepth, setMaxAvailableDepth] = useState(0)

  const nodePositionsRef = useRef<Map<string, { x: number; y: number }>>(new Map())
  const conclusionToPremisesRef = useRef<Map<string, string[]>>(new Map())
  const nodeDepthsRef = useRef<Map<string, number>>(new Map())
  const orphanClaimsRef = useRef<Set<string>>(new Set())

  // Clear collapsed nodes and depth limit when resetKey changes
  useEffect(() => {
    setCollapsedNodes(new Set())
    setMaxDepth(null)
    nodePositionsRef.current.clear()
  }, [resetKey])

  // Build implication map and calculate node depths
  useEffect(() => {
    if (!hypergraph) return
    conclusionToPremisesRef.current.clear()
    nodeDepthsRef.current.clear()
    orphanClaimsRef.current.clear()

    hypergraph.implications.forEach(impl => {
      conclusionToPremisesRef.current.set(impl.conclusion, impl.premises)
    })

    // Calculate depth from hypothesis for each node using BFS
    const depths = new Map<string, number>()
    depths.set('hypothesis', 0)

    const queue: string[] = ['hypothesis']
    while (queue.length > 0) {
      const nodeId = queue.shift()!
      const currentDepth = depths.get(nodeId)!

      const premises = conclusionToPremisesRef.current.get(nodeId)
      if (premises) {
        premises.forEach(premiseId => {
          if (!depths.has(premiseId)) {
            depths.set(premiseId, currentDepth + 1)
            queue.push(premiseId)
          }
        })
      }
    }

    nodeDepthsRef.current = depths

    // Identify orphan claims (not connected to hypothesis)
    const orphans = new Set<string>()
    hypergraph.claims.forEach(claim => {
      if (!depths.has(claim.id)) {
        orphans.add(claim.id)
      }
    })
    orphanClaimsRef.current = orphans
  }, [hypergraph])

  // Update max depth after depths are calculated
  useEffect(() => {
    if (!hypergraph) {
      setMaxAvailableDepth(0)
      return
    }
    // Small delay to ensure nodeDepthsRef is populated
    const timer = setTimeout(() => {
      const depths = Array.from(nodeDepthsRef.current.values())
      setMaxAvailableDepth(depths.length > 0 ? Math.max(...depths) : 0)
    }, 0)
    return () => clearTimeout(timer)
  }, [hypergraph])

  // Update collapsed nodes when maxDepth changes
  useEffect(() => {
    if (maxDepth === null) {
      // Show all - clear collapsed nodes
      setCollapsedNodes(new Set())
    } else {
      // Collapse all nodes beyond maxDepth
      const newCollapsed = new Set<string>()
      nodeDepthsRef.current.forEach((depth, nodeId) => {
        if (depth > maxDepth) {
          newCollapsed.add(nodeId)
        }
      })
      setCollapsedNodes(newCollapsed)
    }
  }, [maxDepth])

  const isConclusion = useCallback((nodeId: string) => {
    return conclusionToPremisesRef.current.has(nodeId)
  }, [])

  const arePremisesCollapsed = useCallback((conclusionId: string) => {
    const premises = conclusionToPremisesRef.current.get(conclusionId)
    if (!premises || premises.length === 0) return false
    return premises.some(p => collapsedNodes.has(p))
  }, [collapsedNodes])

  const getAllDescendants = useCallback((nodeId: string, visited = new Set<string>()): string[] => {
    if (visited.has(nodeId)) return []
    visited.add(nodeId)

    const premises = conclusionToPremisesRef.current.get(nodeId)
    if (!premises || premises.length === 0) return []

    const descendants: string[] = [...premises]
    premises.forEach(p => {
      descendants.push(...getAllDescendants(p, visited))
    })
    return descendants
  }, [])

  const calculateTreeLayout = useCallback((
    visibleClaims: NodeData[],
    width: number,
    height: number
  ): TreeLayoutResult => {
    if (!hypergraph) {
      return { positions: new Map(), levels: new Map() }
    }

    const levels = new Map<string, number>()
    const conclusionToPremises = conclusionToPremisesRef.current
    const orphans = orphanClaimsRef.current

    // Separate orphan claims from connected claims
    const connectedClaims = visibleClaims.filter(c => !orphans.has(c.id))
    const visibleOrphans = visibleClaims.filter(c => orphans.has(c.id))

    // Find root conclusions (from connected claims only)
    const allPremises = new Set<string>()
    hypergraph.implications.forEach(impl => {
      impl.premises.forEach(p => allPremises.add(p))
    })

    const rootConclusions = connectedClaims
      .filter(c => conclusionToPremises.has(c.id))
      .filter(c => !allPremises.has(c.id))
      .map(c => c.id)

    if (rootConclusions.length === 0) {
      connectedClaims
        .filter(c => conclusionToPremises.has(c.id))
        .forEach(c => rootConclusions.push(c.id))
    }

    // Calculate levels (orphans get level -1, roots get level 0)
    visibleOrphans.forEach(orphan => levels.set(orphan.id, -1))
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
        if (conclusionLevel !== undefined && conclusionLevel >= 0) {
          const junctionId = `junction_${impl.id}`
          const junctionLevel = conclusionLevel + 1
          const premiseLevel = conclusionLevel + 2

          if (!levels.has(junctionId)) {
            levels.set(junctionId, junctionLevel)
            changed = true
          }

          impl.premises.forEach(premiseId => {
            if (!orphans.has(premiseId) && (!levels.has(premiseId) || levels.get(premiseId)! < premiseLevel)) {
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
      const visiblePremises = premises ? premises.filter(p => !collapsedNodes.has(p) && !orphans.has(p)) : []

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

    connectedClaims.forEach(c => calculateSubtreeWidth(c.id))

    // Position nodes
    const positions = new Map<string, { x: number; y: number }>()
    const maxLevel = Math.max(...Array.from(levels.values()).filter(l => l >= 0), 0)

    // Reserve space for orphan region above roots
    const orphanRegionHeight = visibleOrphans.length > 0 ? 180 : 0
    const treeStartY = 100 + orphanRegionHeight

    // Minimum spacing to prevent overlap: claim radius (65) + junction radius (15) + padding (20) = 100
    const minLevelSpacing = 80
    const calculatedSpacing = maxLevel > 0 ? (height - treeStartY - 100) / (maxLevel + 1) : 150
    const levelSpacing = Math.max(minLevelSpacing, calculatedSpacing)

    function positionSubtree(nodeId: string, centerX: number, level: number) {
      const y = treeStartY + level * levelSpacing

      if (nodePositionsRef.current.has(nodeId)) {
        positions.set(nodeId, nodePositionsRef.current.get(nodeId)!)
      } else {
        positions.set(nodeId, { x: centerX, y })
      }

      const premises = conclusionToPremises.get(nodeId)
      const visiblePremises = premises ? premises.filter(p => !collapsedNodes.has(p) && !orphans.has(p)) : []

      if (visiblePremises.length === 0) return

      // Position junction
      const impl = hypergraph!.implications.find(i => i.conclusion === nodeId)
      if (impl) {
        const junctionId = `junction_${impl.id}`
        const junctionLevel = level + 1
        const junctionY = treeStartY + junctionLevel * levelSpacing

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

    // Position orphan claims in a row above the tree
    if (visibleOrphans.length > 0) {
      const orphanSpacing = 180
      const totalOrphanWidth = visibleOrphans.length * 150 + (visibleOrphans.length - 1) * (orphanSpacing - 150)
      let orphanX = width / 2 - totalOrphanWidth / 2 + 75

      visibleOrphans.forEach(orphan => {
        if (nodePositionsRef.current.has(orphan.id)) {
          positions.set(orphan.id, nodePositionsRef.current.get(orphan.id)!)
        } else {
          positions.set(orphan.id, { x: orphanX, y: 100 })
        }
        orphanX += orphanSpacing
      })
    }

    return { positions, levels }
  }, [hypergraph, collapsedNodes])

  // Memoize the returned refs as stable values
  const orphanClaims = useMemo(() => orphanClaimsRef.current, [hypergraph])
  const conclusionToPremises = useMemo(() => conclusionToPremisesRef.current, [hypergraph])
  const nodeDepths = useMemo(() => nodeDepthsRef.current, [hypergraph])

  return {
    collapsedNodes,
    setCollapsedNodes,
    maxDepth,
    setMaxDepth,
    maxAvailableDepth,
    orphanClaims,
    conclusionToPremises,
    nodeDepths,
    isConclusion,
    arePremisesCollapsed,
    getAllDescendants,
    calculateTreeLayout,
    nodePositionsRef,
  }
}
