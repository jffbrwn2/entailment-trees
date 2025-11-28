import { useState, useEffect } from 'react'
import Split from 'react-split'
import ApproachSelector from './components/ApproachSelector'
import ChatInterface from './components/ChatInterface'
import HypergraphVisualizer from './components/HypergraphVisualizer'
import './App.css'

export interface Approach {
  name: string
  folder: string
  description: string
  last_updated: string
  num_claims: number
  num_implications: number
}

function App() {
  const [approaches, setApproaches] = useState<Approach[]>([])
  const [currentApproach, setCurrentApproach] = useState<Approach | null>(null)
  const [loading, setLoading] = useState(true)

  // Fetch approaches on mount
  useEffect(() => {
    fetchApproaches()
  }, [])

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

  const handleSelectApproach = async (approach: Approach) => {
    try {
      // Load the approach on the backend
      await fetch(`/api/approaches/${approach.folder}/load`, { method: 'POST' })
      setCurrentApproach(approach)
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
        await fetchApproaches()
        // Select the newly created approach
        const newApproach = approaches.find(a => a.folder === data.folder)
        if (newApproach) {
          setCurrentApproach(newApproach)
        }
      }
    } catch (error) {
      console.error('Failed to create approach:', error)
    }
  }

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
        <h1>Entailment Trees</h1>
        <ApproachSelector
          approaches={approaches}
          currentApproach={currentApproach}
          onSelect={handleSelectApproach}
          onCreate={handleCreateApproach}
        />
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
            <HypergraphVisualizer
              approachFolder={currentApproach?.folder || null}
            />
          </div>
          <div className="panel chat-panel">
            <ChatInterface
              approachFolder={currentApproach?.folder || null}
              approachName={currentApproach?.name || null}
            />
          </div>
        </Split>
      </main>
    </div>
  )
}

export default App
