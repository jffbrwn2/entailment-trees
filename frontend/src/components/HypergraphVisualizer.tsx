import { useEffect, useState, useRef } from 'react'
import './HypergraphVisualizer.css'

interface Props {
  approachFolder: string | null
}

interface Hypergraph {
  metadata: {
    name: string
    description: string
  }
  claims: Array<{
    id: string
    text: string
    score: number
  }>
  implications: Array<{
    id: string
    premises: string[]
    conclusion: string
  }>
}

function HypergraphVisualizer({ approachFolder }: Props) {
  const [hypergraph, setHypergraph] = useState<Hypergraph | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const wsRef = useRef<WebSocket | null>(null)

  // Fetch initial hypergraph and connect WebSocket
  useEffect(() => {
    if (!approachFolder) {
      setHypergraph(null)
      return
    }

    const fetchHypergraph = async () => {
      setLoading(true)
      setError(null)
      try {
        const response = await fetch(`/api/approaches/${approachFolder}/hypergraph`)
        if (!response.ok) {
          throw new Error('Failed to load hypergraph')
        }
        const data = await response.json()
        setHypergraph(data)
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Unknown error')
      } finally {
        setLoading(false)
      }
    }

    fetchHypergraph()

    // Connect WebSocket for live updates
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const ws = new WebSocket(`${wsProtocol}//${window.location.host}/ws/hypergraph/${approachFolder}`)

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.type === 'update' || data.type === 'initial') {
          setHypergraph(data.hypergraph)
        }
      } catch (e) {
        console.error('WebSocket message error:', e)
      }
    }

    ws.onerror = (e) => {
      console.error('WebSocket error:', e)
    }

    wsRef.current = ws

    return () => {
      ws.close()
      wsRef.current = null
    }
  }, [approachFolder])

  if (!approachFolder) {
    return (
      <div className="visualizer-empty">
        <div className="empty-content">
          <h3>No Approach Selected</h3>
          <p>Select or create an approach to visualize its entailment graph.</p>
        </div>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="visualizer-loading">
        <div className="spinner" />
        <p>Loading hypergraph...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="visualizer-error">
        <p>Error: {error}</p>
      </div>
    )
  }

  if (!hypergraph) {
    return null
  }

  // For now, show basic hypergraph info
  // TODO: Port full visualization from entailment_hypergraph/index.html
  return (
    <div className="visualizer">
      <div className="visualizer-header">
        <h2>{hypergraph.metadata.name}</h2>
        <p>{hypergraph.metadata.description}</p>
        <div className="stats">
          <span>{hypergraph.claims.length} claims</span>
          <span>{hypergraph.implications.length} implications</span>
        </div>
      </div>

      <div className="claims-list">
        <h3>Claims</h3>
        {hypergraph.claims.map((claim) => (
          <div
            key={claim.id}
            className="claim-card"
            style={{
              borderLeftColor: getScoreColor(claim.score),
            }}
          >
            <div className="claim-header">
              <span className="claim-id">{claim.id}</span>
              <span
                className="claim-score"
                style={{ color: getScoreColor(claim.score) }}
              >
                {claim.score.toFixed(1)}/10
              </span>
            </div>
            <p className="claim-text">{claim.text}</p>
          </div>
        ))}
      </div>

      <div className="visualizer-footer">
        <p className="todo-note">
          Full interactive visualization coming soon...
        </p>
        <a
          href={`/entailment_hypergraph/?graph=approaches/${approachFolder}/hypergraph.json`}
          target="_blank"
          rel="noopener noreferrer"
          className="open-viz-link"
        >
          Open in full visualizer ↗
        </a>
      </div>
    </div>
  )
}

function getScoreColor(score: number): string {
  // Red (0) -> Yellow (5) -> Green (10)
  const normalized = Math.max(0, Math.min(10, score)) / 10
  if (normalized < 0.5) {
    // Red to yellow
    const r = 248
    const g = Math.round(81 + (217 - 81) * (normalized * 2))
    const b = Math.round(73 + (34 - 73) * (normalized * 2))
    return `rgb(${r}, ${g}, ${b})`
  } else {
    // Yellow to green
    const r = Math.round(217 + (63 - 217) * ((normalized - 0.5) * 2))
    const g = Math.round(217 + (185 - 217) * ((normalized - 0.5) * 2))
    const b = Math.round(34 + (80 - 34) * ((normalized - 0.5) * 2))
    return `rgb(${r}, ${g}, ${b})`
  }
}

export default HypergraphVisualizer
