import type { Hypergraph, Claim, Implication, LinkData } from './types'

/**
 * Generate a signature that represents the graph structure (not content/scores).
 * Used to detect when nodes/edges are added/removed vs just content changes.
 */
export function getStructuralSignature(hypergraph: Hypergraph | null): string {
  if (!hypergraph) return ''
  const claimIds = hypergraph.claims.map(c => c.id).sort().join(',')
  const implSigs = hypergraph.implications.map(i =>
    `${i.id}:${[...i.premises].sort().join('+')}=>${i.conclusion}`
  ).sort().join('|')
  return `${claimIds}||${implSigs}`
}

/**
 * Compute which claims are "evidence-backed" - meaning they have evidence
 * support somewhere in their subtree.
 *
 * - Leaf nodes: backed if they have evidence
 * - AND junctions: backed if ALL premises are backed
 * - OR junctions: backed if ANY premise is backed
 *
 * Returns a Map of claimId -> boolean
 */
export function computeEvidenceBacked(hypergraph: Hypergraph): Map<string, boolean> {
  const result = new Map<string, boolean>()

  // Build map of conclusion -> implication
  const conclusionToImpl = new Map<string, Implication>()
  for (const impl of hypergraph.implications) {
    conclusionToImpl.set(impl.conclusion, impl)
  }

  // Build map of claimId -> claim
  const claimMap = new Map<string, Claim>()
  for (const claim of hypergraph.claims) {
    claimMap.set(claim.id, claim)
  }

  // Memoized recursive function
  function isEvidenceBacked(claimId: string): boolean {
    if (result.has(claimId)) {
      return result.get(claimId)!
    }

    const claim = claimMap.get(claimId)
    if (!claim) {
      result.set(claimId, false)
      return false
    }

    const impl = conclusionToImpl.get(claimId)

    let backed: boolean
    if (!impl) {
      // Leaf node - backed if has evidence
      backed = !!(claim.evidence && claim.evidence.length > 0)
    } else {
      // Non-leaf - check premises based on junction type
      const premisesBacked = impl.premises.map(p => isEvidenceBacked(p))
      if (impl.type === 'OR') {
        // OR: backed if ANY premise is backed
        backed = premisesBacked.some(b => b)
      } else {
        // AND (default): backed if ALL premises are backed
        backed = premisesBacked.every(b => b)
      }
    }

    result.set(claimId, backed)
    return backed
  }

  // Compute for all claims
  for (const claim of hypergraph.claims) {
    isEvidenceBacked(claim.id)
  }

  return result
}

/**
 * Get the effective score for a claim based on scoreMode.
 * If isEvidenceBacked is false, returns null (unevaluated/gray).
 */
export function getEffectiveScore(
  claim: Claim,
  scoreMode: 'score' | 'propagated',
  isEvidenceBacked: boolean = true
): number | null {
  // Claims not backed by evidence are unevaluated (gray)
  if (!isEvidenceBacked) {
    return null
  }

  if (scoreMode === 'propagated') {
    // null or "Infinity" means failed entailment or error, show as 0
    if (claim.cost === null || claim.cost === "Infinity") {
      return 0
    }
    // "-Infinity" would mean perfect certainty (shouldn't happen in practice)
    if (claim.cost === "-Infinity") {
      return 10
    }
    // undefined means not computed, fall back to raw score
    if (claim.cost !== undefined && typeof claim.cost === 'number') {
      return Math.pow(2, -claim.cost) * 10
    }
  }
  return claim.score
}

/**
 * Convert a score (0-10) to a color.
 * 0 = red, 5 = amber, 10 = green, null = grey
 */
export function getScoreColor(score: number | null): string {
  // Null/unevaluated scores are grey (lighter in light mode)
  if (score === null) {
    const isLightMode = document.documentElement.getAttribute('data-theme') === 'light'
    return isLightMode ? 'rgb(200, 200, 200)' : 'rgb(128, 128, 128)'
  }
  const clampedScore = Math.max(0, Math.min(10, score))
  // Brighter color palette: red -> golden amber -> green
  if (clampedScore <= 5) {
    const t = clampedScore / 5
    const r = Math.round(220 - (220 - 220) * t)  // 220 -> 220
    const g = Math.round(70 + (175 - 70) * t)    // 70 -> 175
    const b = Math.round(60 + (50 - 60) * t)     // 60 -> 50
    return `rgb(${r}, ${g}, ${b})`
  } else {
    const t = (clampedScore - 5) / 5
    const r = Math.round(220 - (220 - 60) * t)   // 220 -> 60
    const g = Math.round(175 + (180 - 175) * t)  // 175 -> 180
    const b = Math.round(50 + (100 - 50) * t)    // 50 -> 100
    return `rgb(${r}, ${g}, ${b})`
  }
}

/**
 * Create a curved SVG path for an edge.
 */
export function createCurvePath(d: LinkData): string {
  const sourceX = d.source._animX !== undefined ? d.source._animX : d.source.x
  const sourceY = d.source._animY !== undefined ? d.source._animY : d.source.y
  const targetX = d.target._animX !== undefined ? d.target._animX : d.target.x
  const targetY = d.target._animY !== undefined ? d.target._animY : d.target.y
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
