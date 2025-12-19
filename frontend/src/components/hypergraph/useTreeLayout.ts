import { useState, useEffect, useCallback, useRef, useMemo } from 'react'
import type { Hypergraph, NodeData } from './types'

interface TreeLayoutResult {
  positions: Map<string, { x: number; y: number }>
  levels: Map<string, number>
}

export type LayoutMode = 'compact' | 'spaced'

interface UseTreeLayoutReturn {
  collapsedNodes: Set<string>
  setCollapsedNodes: React.Dispatch<React.SetStateAction<Set<string>>>
  maxDepth: number | null
  setMaxDepth: React.Dispatch<React.SetStateAction<number | null>>
  maxAvailableDepth: number
  layoutMode: LayoutMode
  setLayoutMode: React.Dispatch<React.SetStateAction<LayoutMode>>
  orphanClaims: Set<string>
  conclusionToPremises: Map<string, string[]>
  premiseToConclusions: Map<string, string[]>
  nodeDepths: Map<string, number>
  isConclusion: (nodeId: string) => boolean
  arePremisesCollapsed: (conclusionId: string) => boolean
  getAllDescendants: (nodeId: string, visited?: Set<string>) => string[]
  getExclusiveDescendants: (nodeId: string) => string[]
  calculateTreeLayout: (visibleClaims: NodeData[], width: number, height: number) => TreeLayoutResult
  nodePositionsRef: React.MutableRefObject<Map<string, { x: number; y: number }>>
  autoFitPending: boolean
  clearAutoFit: () => void
}

export function useTreeLayout(
  hypergraph: Hypergraph | null,
  resetKey?: number
): UseTreeLayoutReturn {
  const [collapsedNodes, setCollapsedNodes] = useState<Set<string>>(new Set())
  const [maxDepth, setMaxDepth] = useState<number | null>(null)
  const [autoFitPending, setAutoFitPending] = useState(false)
  const [maxAvailableDepth, setMaxAvailableDepth] = useState(0)
  const [layoutMode, setLayoutMode] = useState<LayoutMode>('compact')

  const nodePositionsRef = useRef<Map<string, { x: number; y: number }>>(new Map())
  const conclusionToPremisesRef = useRef<Map<string, string[]>>(new Map())
  const premiseToConclusionsRef = useRef<Map<string, string[]>>(new Map())
  const nodeDepthsRef = useRef<Map<string, number>>(new Map())
  const orphanClaimsRef = useRef<Set<string>>(new Set())

  // Clear collapsed nodes and depth limit when resetKey changes
  useEffect(() => {
    setCollapsedNodes(new Set())
    setMaxDepth(null)
    nodePositionsRef.current.clear()
  }, [resetKey])

  // Clear positions when layout mode changes to force recalculation
  useEffect(() => {
    nodePositionsRef.current.clear()
  }, [layoutMode])

  // Build implication map and calculate node depths
  useEffect(() => {
    if (!hypergraph) return
    conclusionToPremisesRef.current.clear()
    premiseToConclusionsRef.current.clear()
    nodeDepthsRef.current.clear()
    orphanClaimsRef.current.clear()

    hypergraph.implications.forEach(impl => {
      conclusionToPremisesRef.current.set(impl.conclusion, impl.premises)
      // Build reverse map: premise -> conclusions that use it
      impl.premises.forEach(premiseId => {
        const conclusions = premiseToConclusionsRef.current.get(premiseId) || []
        conclusions.push(impl.conclusion)
        premiseToConclusionsRef.current.set(premiseId, conclusions)
      })
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
    // Request auto-fit after depth change
    setAutoFitPending(true)
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

  // Returns only descendants that are exclusively reachable through the given node.
  // If a descendant has another path to the root (i.e., it's a premise for another
  // conclusion not in the collapse set), it won't be included.
  const getExclusiveDescendants = useCallback((nodeId: string): string[] => {
    const allDescendants = getAllDescendants(nodeId)
    const collapseSet = new Set([nodeId, ...allDescendants])

    // Filter to only descendants that don't have outside connections
    return allDescendants.filter(descendant => {
      const parentConclusions = premiseToConclusionsRef.current.get(descendant) || []
      // Check if ALL parent conclusions are within the collapse set
      return parentConclusions.every(conclusion => collapseSet.has(conclusion))
    })
  }, [getAllDescendants])

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

    // Calculate levels for main tree (roots get level 0)
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

        // Skip orphan implications for now - handle separately
        if (orphans.has(impl.conclusion)) {
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

    // Now handle orphan subgraphs - find orphan roots and calculate their levels
    // Orphan roots are orphan claims that are conclusions but not premises of other orphan conclusions
    const orphanPremises = new Set<string>()
    hypergraph.implications.forEach(impl => {
      if (orphans.has(impl.conclusion)) {
        impl.premises.forEach(p => orphanPremises.add(p))
      }
    })

    const orphanRoots = visibleOrphans
      .filter(o => conclusionToPremises.has(o.id))
      .filter(o => !orphanPremises.has(o.id))
      .map(o => o.id)

    // Also include orphans that are standalone (no implications at all)
    const orphanLeaves = visibleOrphans
      .filter(o => !conclusionToPremises.has(o.id) && !orphanPremises.has(o.id))
      .map(o => o.id)

    // Set levels for orphan roots at -1 (will be adjusted later based on max depth)
    orphanRoots.forEach(rootId => levels.set(rootId, -1))
    orphanLeaves.forEach(leafId => levels.set(leafId, -1))

    // Propagate levels through orphan subgraphs
    changed = true
    iterations = 0
    while (changed && iterations < 20) {
      changed = false
      iterations++

      hypergraph.implications.forEach(impl => {
        if (!orphans.has(impl.conclusion)) return
        if (collapsedNodes.has(impl.conclusion) ||
            impl.premises.some(p => collapsedNodes.has(p))) {
          return
        }

        const conclusionLevel = levels.get(impl.conclusion)
        if (conclusionLevel !== undefined) {
          const junctionId = `junction_${impl.id}`
          const junctionLevel = conclusionLevel - 1  // Negative levels going up
          const premiseLevel = conclusionLevel - 2

          if (!levels.has(junctionId)) {
            levels.set(junctionId, junctionLevel)
            changed = true
          }

          impl.premises.forEach(premiseId => {
            if (!levels.has(premiseId) || levels.get(premiseId)! > premiseLevel) {
              levels.set(premiseId, premiseLevel)
              changed = true
            }
          })
        }
      })
    }

    // For 'spaced' mode, calculate subtree widths recursively
    const subtreeWidths = new Map<string, number>()

    function calculateSubtreeWidth(nodeId: string, allowOrphans: boolean, visited = new Set<string>()): number {
      if (subtreeWidths.has(nodeId)) return subtreeWidths.get(nodeId)!
      if (visited.has(nodeId)) return 190
      visited.add(nodeId)

      const premises = conclusionToPremises.get(nodeId)
      const visiblePremises = premises ? premises.filter(p =>
        !collapsedNodes.has(p) && (allowOrphans || !orphans.has(p))
      ) : []

      if (visiblePremises.length === 0) {
        subtreeWidths.set(nodeId, 190)
        return 190
      }

      let totalWidth = 0
      visiblePremises.forEach(premiseId => {
        totalWidth += calculateSubtreeWidth(premiseId, allowOrphans, visited)
      })
      totalWidth += (visiblePremises.length - 1) * 130

      const w = Math.max(190, totalWidth)
      subtreeWidths.set(nodeId, w)
      return w
    }

    // Only calculate subtree widths for 'spaced' mode
    if (layoutMode === 'spaced') {
      connectedClaims.forEach(c => calculateSubtreeWidth(c.id, false))
      orphanRoots.forEach(rootId => calculateSubtreeWidth(rootId, true))
    }

    // Position nodes
    const positions = new Map<string, { x: number; y: number }>()
    const maxLevel = Math.max(...Array.from(levels.values()).filter(l => l >= 0), 0)

    // Calculate orphan region depth (how many levels deep the orphan trees go)
    const minOrphanLevel = Math.min(...Array.from(levels.values()).filter(l => l < 0), -1)
    const orphanDepth = Math.abs(minOrphanLevel)  // Number of levels in orphan region

    // Reserve space for orphan region above roots
    const orphanRegionHeight = visibleOrphans.length > 0 ? (orphanDepth * 110 + 120) : 0
    const treeStartY = 120 + orphanRegionHeight

    // Minimum spacing to prevent overlap: claim radius (85) + junction radius (15) + padding (20) = 120
    const minLevelSpacing = 110
    const calculatedSpacing = maxLevel > 0 ? (height - treeStartY - 120) / (maxLevel + 1) : 190
    const levelSpacing = Math.max(minLevelSpacing, calculatedSpacing)

    function positionSubtree(nodeId: string, centerX: number, level: number) {
      const y = treeStartY + level * levelSpacing

      if (layoutMode === 'compact' && nodePositionsRef.current.has(nodeId)) {
        positions.set(nodeId, nodePositionsRef.current.get(nodeId)!)
      } else {
        const newPos = { x: centerX, y }
        positions.set(nodeId, newPos)
        if (layoutMode === 'compact') {
          nodePositionsRef.current.set(nodeId, newPos)  // Persist for future layouts
        }
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

        if (layoutMode === 'compact' && nodePositionsRef.current.has(junctionId)) {
          positions.set(junctionId, nodePositionsRef.current.get(junctionId)!)
        } else {
          const newPos = { x: centerX, y: junctionY }
          positions.set(junctionId, newPos)
          if (layoutMode === 'compact') {
            nodePositionsRef.current.set(junctionId, newPos)  // Persist for future layouts
          }
        }
      }

      // Position children - use subtree widths for 'spaced' mode, minimum spacing for 'compact'
      const premiseLevel = level + 2
      const premiseSpacing = 70

      if (layoutMode === 'spaced') {
        const childWidths = visiblePremises.map(p => subtreeWidths.get(p) || 190)
        const totalWidth = childWidths.reduce((a, b) => a + b, 0) + (visiblePremises.length - 1) * premiseSpacing

        let currentX = centerX - totalWidth / 2
        visiblePremises.forEach((premiseId, i) => {
          const childCenterX = currentX + childWidths[i] / 2
          positionSubtree(premiseId, childCenterX, premiseLevel)
          currentX += childWidths[i] + premiseSpacing
        })
      } else {
        // Compact mode: minimum spacing, collision detection handles overlaps
        const nodeWidth = 190
        const totalWidth = visiblePremises.length * nodeWidth + (visiblePremises.length - 1) * premiseSpacing

        let currentX = centerX - totalWidth / 2
        visiblePremises.forEach((premiseId) => {
          const childCenterX = currentX + nodeWidth / 2
          positionSubtree(premiseId, childCenterX, premiseLevel)
          currentX += nodeWidth + premiseSpacing
        })
      }
    }

    // Position roots
    const rootSpacing = 250
    if (layoutMode === 'spaced') {
      let totalRootWidth = 0
      rootConclusions.forEach(rootId => {
        totalRootWidth += subtreeWidths.get(rootId) || 190
      })
      totalRootWidth += (rootConclusions.length - 1) * rootSpacing

      let rootX = width / 2 - totalRootWidth / 2
      rootConclusions.forEach(rootId => {
        const rootWidth = subtreeWidths.get(rootId) || 190
        positionSubtree(rootId, rootX + rootWidth / 2, 0)
        rootX += rootWidth + rootSpacing
      })
    } else {
      // Compact mode
      const rootWidth = 190
      const totalRootWidth = rootConclusions.length * rootWidth + (rootConclusions.length - 1) * rootSpacing

      let rootX = width / 2 - totalRootWidth / 2
      rootConclusions.forEach(rootId => {
        positionSubtree(rootId, rootX + rootWidth / 2, 0)
        rootX += rootWidth + rootSpacing
      })
    }

    // Position orphan subtrees above the main tree
    if (visibleOrphans.length > 0) {
      const orphanLevelSpacing = 110

      // Function to position an orphan subtree (similar to main tree but inverted)
      function positionOrphanSubtree(nodeId: string, centerX: number, level: number) {
        // Orphan levels are negative, convert to Y position
        // Level -1 is closest to main tree, more negative levels go higher
        const y = treeStartY + (level + 1) * orphanLevelSpacing - orphanRegionHeight - 40

        if (layoutMode === 'compact' && nodePositionsRef.current.has(nodeId)) {
          positions.set(nodeId, nodePositionsRef.current.get(nodeId)!)
        } else {
          const newPos = { x: centerX, y }
          positions.set(nodeId, newPos)
          if (layoutMode === 'compact') {
            nodePositionsRef.current.set(nodeId, newPos)  // Persist for future layouts
          }
        }

        const premises = conclusionToPremises.get(nodeId)
        const visiblePremises = premises ? premises.filter(p => !collapsedNodes.has(p)) : []

        if (visiblePremises.length === 0) return

        // Position junction
        const impl = hypergraph!.implications.find(i => i.conclusion === nodeId)
        if (impl) {
          const junctionId = `junction_${impl.id}`
          const junctionLevel = level - 1
          const junctionY = treeStartY + (junctionLevel + 1) * orphanLevelSpacing - orphanRegionHeight - 40

          if (layoutMode === 'compact' && nodePositionsRef.current.has(junctionId)) {
            positions.set(junctionId, nodePositionsRef.current.get(junctionId)!)
          } else {
            const newPos = { x: centerX, y: junctionY }
            positions.set(junctionId, newPos)
            if (layoutMode === 'compact') {
              nodePositionsRef.current.set(junctionId, newPos)  // Persist for future layouts
            }
          }
        }

        // Position children (premises go above, so use level - 2)
        const premiseLevel = level - 2
        const premiseSpacing = 70

        if (layoutMode === 'spaced') {
          const childWidths = visiblePremises.map(p => subtreeWidths.get(p) || 190)
          const totalWidth = childWidths.reduce((a, b) => a + b, 0) + (visiblePremises.length - 1) * premiseSpacing

          let currentX = centerX - totalWidth / 2
          visiblePremises.forEach((premiseId, i) => {
            const childCenterX = currentX + childWidths[i] / 2
            positionOrphanSubtree(premiseId, childCenterX, premiseLevel)
            currentX += childWidths[i] + premiseSpacing
          })
        } else {
          const nodeWidth = 190
          const totalWidth = visiblePremises.length * nodeWidth + (visiblePremises.length - 1) * premiseSpacing

          let currentX = centerX - totalWidth / 2
          visiblePremises.forEach((premiseId) => {
            const childCenterX = currentX + nodeWidth / 2
            positionOrphanSubtree(premiseId, childCenterX, premiseLevel)
            currentX += nodeWidth + premiseSpacing
          })
        }
      }

      // Position orphan roots and standalone orphans
      const allOrphanRoots = [...orphanRoots, ...orphanLeaves]
      const orphanSpacing = 190

      if (layoutMode === 'spaced') {
        let totalOrphanWidth = 0
        allOrphanRoots.forEach(rootId => {
          totalOrphanWidth += subtreeWidths.get(rootId) || 190
        })
        totalOrphanWidth += (allOrphanRoots.length - 1) * orphanSpacing

        let orphanX = width / 2 - totalOrphanWidth / 2
        allOrphanRoots.forEach(rootId => {
          const rootWidth = subtreeWidths.get(rootId) || 190
          const rootLevel = levels.get(rootId) ?? -1
          positionOrphanSubtree(rootId, orphanX + rootWidth / 2, rootLevel)
          orphanX += rootWidth + orphanSpacing
        })
      } else {
        const orphanNodeWidth = 190
        const totalOrphanWidth = allOrphanRoots.length * orphanNodeWidth + (allOrphanRoots.length - 1) * orphanSpacing

        let orphanX = width / 2 - totalOrphanWidth / 2
        allOrphanRoots.forEach(rootId => {
          const rootLevel = levels.get(rootId) ?? -1
          positionOrphanSubtree(rootId, orphanX + orphanNodeWidth / 2, rootLevel)
          orphanX += orphanNodeWidth + orphanSpacing
        })
      }
    }

    // Collision detection: push apart overlapping nodes at each level (compact mode only)
    if (layoutMode === 'compact') {
      const minNodeDistance = 190 + 20  // node width + padding
      const nodesByY = new Map<number, string[]>()

      // Group nodes by Y position (rounded to handle floating point)
      positions.forEach((pos, nodeId) => {
        const roundedY = Math.round(pos.y / 10) * 10
        if (!nodesByY.has(roundedY)) nodesByY.set(roundedY, [])
        nodesByY.get(roundedY)!.push(nodeId)
      })

      // For each Y level, resolve horizontal overlaps
      nodesByY.forEach((nodesAtY) => {
        if (nodesAtY.length < 2) return

        // Sort by X position
        nodesAtY.sort((a, b) => positions.get(a)!.x - positions.get(b)!.x)

        // Push apart overlapping nodes
        for (let i = 1; i < nodesAtY.length; i++) {
          const prevPos = positions.get(nodesAtY[i - 1])!
          const currPos = positions.get(nodesAtY[i])!
          const distance = currPos.x - prevPos.x

          if (distance < minNodeDistance) {
            const shift = minNodeDistance - distance
            // Push current node and all nodes to its right
            for (let j = i; j < nodesAtY.length; j++) {
              const pos = positions.get(nodesAtY[j])!
              pos.x += shift
              // Update the ref with new position
              nodePositionsRef.current.set(nodesAtY[j], { ...pos })
            }
          }
        }
      })
    }

    return { positions, levels }
  }, [hypergraph, collapsedNodes, layoutMode])

  // Compute orphan claims directly (claims not connected to hypothesis)
  const orphanClaims = useMemo(() => {
    if (!hypergraph) return new Set<string>()

    // Build the connection map
    const conclusionToPremises = new Map<string, string[]>()
    hypergraph.implications.forEach(impl => {
      conclusionToPremises.set(impl.conclusion, impl.premises)
    })

    // BFS from hypothesis to find all connected claims
    const connected = new Set<string>()
    const queue = ['hypothesis']
    while (queue.length > 0) {
      const current = queue.shift()!
      if (connected.has(current)) continue
      connected.add(current)
      const premises = conclusionToPremises.get(current)
      if (premises) {
        premises.forEach(p => {
          if (!connected.has(p)) queue.push(p)
        })
      }
    }

    // Orphans are claims not in connected set
    const orphans = new Set<string>()
    hypergraph.claims.forEach(claim => {
      if (!connected.has(claim.id)) {
        orphans.add(claim.id)
      }
    })
    return orphans
  }, [hypergraph])
  const conclusionToPremises = useMemo(() => conclusionToPremisesRef.current, [hypergraph])
  const premiseToConclusions = useMemo(() => premiseToConclusionsRef.current, [hypergraph])
  const nodeDepths = useMemo(() => nodeDepthsRef.current, [hypergraph])

  const clearAutoFit = useCallback(() => setAutoFitPending(false), [])

  return {
    collapsedNodes,
    setCollapsedNodes,
    maxDepth,
    setMaxDepth,
    maxAvailableDepth,
    layoutMode,
    setLayoutMode,
    orphanClaims,
    conclusionToPremises,
    premiseToConclusions,
    nodeDepths,
    isConclusion,
    arePremisesCollapsed,
    getAllDescendants,
    getExclusiveDescendants,
    calculateTreeLayout,
    nodePositionsRef,
    autoFitPending,
    clearAutoFit,
  }
}
