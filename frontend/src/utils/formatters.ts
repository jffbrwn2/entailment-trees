/**
 * Truncate text to a max length with ellipsis
 */
export function truncate(text: string, maxLength: number): string {
  if (!text || text.length <= maxLength) return text
  return text.slice(0, maxLength - 1) + '…'
}

/**
 * Format a score for display
 */
export function formatScore(score: number | null): string {
  if (score === null) return 'Not evaluated'
  return `${score.toFixed(1)}/10`
}

/**
 * Format cost value for display
 */
export function formatCost(cost: number | string | null | undefined): string {
  if (cost === null || cost === 'Infinity') return '∞ (P = 0)'
  if (cost === '-Infinity') return '-∞ (P = 1)'
  if (typeof cost === 'number') {
    return `${cost.toFixed(3)} (P = ${Math.pow(2, -cost).toFixed(3)})`
  }
  return cost ?? 'Not computed'
}
