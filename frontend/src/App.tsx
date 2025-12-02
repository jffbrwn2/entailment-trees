import { useState, useEffect, useCallback } from 'react'
import Split from 'react-split'
import ApproachSelector from './components/ApproachSelector'
import ChatInterface from './components/ChatInterface'
import D3HypergraphViewer from './components/D3HypergraphViewer'
import SelectedItemDetail from './components/SelectedItemDetail'
import './App.css'

export interface Approach {
  name: string
  folder: string
  description: string
  last_updated: string
  num_claims: number
  num_implications: number
}

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
  claims: Claim[]
  implications: Implication[]
}

interface SelectedItem {
  type: 'claim' | 'implication'
  id: string
}

function App() {
  const [approaches, setApproaches] = useState<Approach[]>([])
  const [currentApproach, setCurrentApproach] = useState<Approach | null>(null)
  const [loading, setLoading] = useState(true)
  const [hypergraph, setHypergraph] = useState<Hypergraph | null>(null)
  const [selectedItem, setSelectedItem] = useState<SelectedItem | null>(null)
  const [darkMode, setDarkMode] = useState(true)
  const [scoreMode, setScoreMode] = useState<'score' | 'propagated'>('propagated')
  const [resetKey, setResetKey] = useState(0)

  // Apply dark/light mode
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', darkMode ? 'dark' : 'light')
  }, [darkMode])

  // Fetch approaches on mount
  useEffect(() => {
    fetchApproaches()
  }, [])

  // Fetch hypergraph when approach changes
  useEffect(() => {
    if (currentApproach) {
      fetchHypergraph(currentApproach.folder)
      // Set up WebSocket for live updates
      const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const ws = new WebSocket(`${wsProtocol}//${window.location.host}/ws/hypergraph/${currentApproach.folder}`)

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          if (data.type === 'update') {
            fetchHypergraph(currentApproach.folder)
          }
        } catch (e) {
          console.error('WebSocket message error:', e)
        }
      }

      return () => ws.close()
    } else {
      setHypergraph(null)
      setSelectedItem(null)
    }
  }, [currentApproach])

  const fetchApproaches = async () => {
    try {
      const response = await fetch('/api/approaches')
      const data = await response.json()
      setApproaches(data)
    } catch (error) {
      console.error('Failed to fetch approaches:', error)
    } finally {
      setLoading(false)
    }
  }

  const fetchHypergraph = async (folder: string) => {
    try {
      const response = await fetch(`/api/approaches/${folder}/hypergraph`)
      if (response.ok) {
        const data = await response.json()
        setHypergraph(data)
      }
    } catch (error) {
      console.error('Failed to fetch hypergraph:', error)
    }
  }

  const handleSelectApproach = async (approach: Approach) => {
    try {
      // Load the approach on the backend
      await fetch(`/api/approaches/${approach.folder}/load`, { method: 'POST' })
      setCurrentApproach(approach)
      setSelectedItem(null)
    } catch (error) {
      console.error('Failed to load approach:', error)
    }
  }

  const handleCreateApproach = async (name: string, hypothesis: string) => {
    try {
      const response = await fetch('/api/approaches', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, hypothesis }),
      })
      const data = await response.json()
      if (data.success) {
        // Load the approach on the backend first
        await fetch(`/api/approaches/${data.folder}/load`, { method: 'POST' })

        // Fetch the updated approaches list
        const listResponse = await fetch('/api/approaches')
        const updatedApproaches = await listResponse.json()
        setApproaches(updatedApproaches)

        // Find and select the newly created approach from the fresh list
        const newApproach = updatedApproaches.find((a: Approach) => a.folder === data.folder)
        if (newApproach) {
          setCurrentApproach(newApproach)
        }
      }
    } catch (error) {
      console.error('Failed to create approach:', error)
    }
  }

  const handleSelect = useCallback((item: SelectedItem | null) => {
    setSelectedItem(item)
  }, [])

  const handleCloseDetail = useCallback(() => {
    setSelectedItem(null)
  }, [])

  if (loading) {
    return (
      <div className="loading">
        <div className="loading-spinner" />
        <p>Loading...</p>
      </div>
    )
  }

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-left">
          <h1>Entailment Trees</h1>
        </div>
        <div className="header-center">
          <ApproachSelector
            approaches={approaches}
            currentApproach={currentApproach}
            onSelect={handleSelectApproach}
            onCreate={handleCreateApproach}
          />
        </div>
        <div className="header-right">
          <div className="toolbar-group">
            <label className="toolbar-label">Score:</label>
            <select
              className="toolbar-select"
              value={scoreMode}
              onChange={(e) => setScoreMode(e.target.value as 'score' | 'propagated')}
            >
              <option value="score">Direct</option>
              <option value="propagated">Propagated</option>
            </select>
          </div>
          <button
            className="toolbar-button"
            onClick={() => setResetKey(k => k + 1)}
            title="Reset graph layout"
          >
            Reset
          </button>
          <button
            className="toolbar-button"
            onClick={() => setDarkMode(!darkMode)}
            title={darkMode ? 'Switch to light mode' : 'Switch to dark mode'}
          >
            {darkMode ? '☀️' : '🌙'}
          </button>
        </div>
      </header>

      <main className="app-main">
        <Split
          className="split"
          sizes={[60, 40]}
          minSize={300}
          gutterSize={8}
          direction="horizontal"
        >
          <div className="panel visualization-panel">
            <D3HypergraphViewer
              hypergraph={hypergraph}
              selectedItem={selectedItem}
              onSelect={handleSelect}
              scoreMode={scoreMode}
              resetKey={resetKey}
            />
          </div>
          <div className="panel right-panel">
            <Split
              className="split-vertical"
              sizes={selectedItem ? [40, 60] : [0, 100]}
              minSize={selectedItem ? 100 : 0}
              gutterSize={selectedItem ? 8 : 0}
              direction="vertical"
            >
              <div className="detail-pane">
                {selectedItem && hypergraph && (
                  <SelectedItemDetail
                    selectedItem={selectedItem}
                    claims={hypergraph.claims}
                    implications={hypergraph.implications}
                    onClose={handleCloseDetail}
                  />
                )}
              </div>
              <div className="chat-pane">
                <ChatInterface
                  approachFolder={currentApproach?.folder || null}
                  approachName={currentApproach?.name || null}
                />
              </div>
            </Split>
          </div>
        </Split>
      </main>
    </div>
  )
}

export default App
