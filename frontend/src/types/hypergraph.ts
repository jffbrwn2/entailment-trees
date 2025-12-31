/**
 * Centralized type definitions for hypergraph data structures.
 * This is the single source of truth for all hypergraph-related types.
 */

export interface Evidence {
  type: 'simulation' | 'literature' | 'calculation'
  source?: string
  lines?: string
  code?: string
  reference_text?: string
  equations?: string
  program?: string
}

export interface Claim {
  id: string
  text: string
  score: number | null
  cost?: number | string | null
  evidence_epistemic_cost?: number | string | null
  experimental_epistemic_cost?: number | string | null
  reasoning?: string
  evidence?: Evidence[]
  uncertainties?: string[]
  tags?: string[]
  testability?: 0 | 1 | null
  proposed_experiment?: string | null
}

export interface Implication {
  id: string
  premises: string[]
  conclusion: string
  type?: 'AND' | 'OR'
  reasoning: string
  entailment_status?: 'passed' | 'failed'
  entailment_explanation?: string
}

export interface ValidationResult {
  errors: string[]
  warnings: string[]
  valid: boolean
  checked_at?: string
}

export interface Hypergraph {
  metadata?: {
    name: string
    description?: string
    validation?: ValidationResult
  }
  claims: Claim[]
  implications: Implication[]
}

export interface SelectedItem {
  type: 'claim' | 'implication'
  id: string
}

export interface Approach {
  name: string
  folder: string
  description: string
  last_updated: string
  num_claims: number
  num_implications: number
}

// D3 visualization types
export interface NodeData {
  id: string
  type: 'claim' | 'junction'
  x: number
  y: number
  text?: string
  score?: number | null
  cost?: number | string | null
  evidence?: Evidence[]
  implication?: Implication
  _animX?: number
  _animY?: number
}

export interface LinkData {
  source: NodeData
  target: NodeData
  type: 'premise-to-junction' | 'junction-to-conclusion'
  premises: string[]
  conclusion: string
  implId: string
}

export interface D3HypergraphViewerProps {
  hypergraph: Hypergraph | null
  scoreMode: 'score' | 'propagated'
  onScoreModeChange: (mode: 'score' | 'propagated') => void
  onSelect: (item: SelectedItem | null) => void
  selectedItem: SelectedItem | null
  resetKey?: number
  onReset: () => void
  onCleanup: () => void
  onDelete?: (claimId: string) => void
  onSendMessage?: (message: string) => void
}
