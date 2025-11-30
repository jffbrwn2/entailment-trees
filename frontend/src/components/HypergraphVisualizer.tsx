import { useEffect, useRef, useState } from 'react'
import './HypergraphVisualizer.css'

interface Props {
  approachFolder: string | null
}

function HypergraphVisualizer({ approachFolder }: Props) {
  const iframeRef = useRef<HTMLIFrameElement>(null)
  const [loading, setLoading] = useState(true)
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    if (!approachFolder) {
      setLoading(false)
      return
    }

    setLoading(true)

    // Connect WebSocket for live updates to notify iframe
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const ws = new WebSocket(`${wsProtocol}//${window.location.host}/ws/hypergraph/${approachFolder}`)

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.type === 'update' && iframeRef.current?.contentWindow) {
          // Post message to iframe to trigger reload
          iframeRef.current.contentWindow.postMessage({ type: 'hypergraph_update' }, '*')
        }
      } catch (e) {
        console.error('WebSocket message error:', e)
      }
    }

    wsRef.current = ws

    return () => {
      ws.close()
      wsRef.current = null
    }
  }, [approachFolder])

  const handleIframeLoad = () => {
    setLoading(false)
  }

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

  // Build URL for the existing visualizer with the approach's hypergraph
  const visualizerUrl = `/entailment_hypergraph/index.html?graph=approaches/${approachFolder}/hypergraph.json`

  return (
    <div className="visualizer">
      {loading && (
        <div className="visualizer-loading-overlay">
          <div className="spinner" />
          <p>Loading visualization...</p>
        </div>
      )}
      <iframe
        ref={iframeRef}
        src={visualizerUrl}
        className="visualizer-iframe"
        onLoad={handleIframeLoad}
        title="Hypergraph Visualizer"
      />
    </div>
  )
}

export default HypergraphVisualizer
