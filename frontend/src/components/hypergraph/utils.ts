import type { Hypergraph, Claim, LinkData } from './types'

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
 * Get the effective score for a claim based on scoreMode.
 * If isLeaf is true and the claim has no evidence, returns null (unevaluated).
 */
export function getEffectiveScore(
  claim: Claim,
  scoreMode: 'score' | 'propagated',
  isLeaf: boolean = false
): number | null {
  // Leaf claims without evidence are unevaluated (gray)
  if (isLeaf && (!claim.evidence || claim.evidence.length === 0)) {
    return null
  }

  if (scoreMode === 'propagated') {
    // null or "Infinity" means infinite uncertainty, so effective score is 0
    if (claim.propagated_negative_log === null || claim.propagated_negative_log === "Infinity") {
      return 0
    }
    // "-Infinity" would mean perfect certainty (shouldn't happen in practice)
    if (claim.propagated_negative_log === "-Infinity") {
      return 10
    }
    // undefined means not computed, fall back to raw score
    if (claim.propagated_negative_log !== undefined && typeof claim.propagated_negative_log === 'number') {
      return Math.pow(2, -claim.propagated_negative_log) * 10
    }
  }
  return claim.score
}

/**
 * Convert a score (0-10) to a color.
 * 0 = red, 5 = yellow, 10 = green, null = grey
 */
export function getScoreColor(score: number | null): string {
  // Null/unevaluated scores are grey
  if (score === null) {
    return 'rgb(128, 128, 128)'
  }
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
