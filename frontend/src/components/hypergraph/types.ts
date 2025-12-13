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
  propagated_negative_log?: number | string | null
  reasoning?: string
  evidence?: Evidence[]
  uncertainties?: string[]
  tags?: string[]
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

export interface Hypergraph {
  metadata?: {
    name: string
    description?: string
  }
  claims: Claim[]
  implications: Implication[]
}

export interface SelectedItem {
  type: 'claim' | 'implication'
  id: string
}

export interface NodeData {
  id: string
  type: 'claim' | 'junction'
  x: number
  y: number
  text?: string
  score?: number | null
  propagated_negative_log?: number | string | null
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
  onSelect: (item: SelectedItem | null) => void
  selectedItem: SelectedItem | null
  resetKey?: number
  onDelete?: (claimId: string) => void
}
