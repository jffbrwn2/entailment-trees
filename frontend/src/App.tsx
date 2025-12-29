import { useState, useEffect, useCallback } from 'react'
import Split from 'react-split'
import ApproachSelector from './components/ApproachSelector'
import ChatInterface from './components/ChatInterface'
import { D3HypergraphViewer } from './components/hypergraph'
import SelectedItemDetail from './components/SelectedItemDetail'
import WelcomeModal from './components/WelcomeModal'
import TutorialModal from './components/TutorialModal'
import SettingsModal from './components/SettingsModal'
import ExploreModal, { GapMapSource } from './components/ExploreModal'
import { useSettings, useAutoMode } from './hooks'
import type { Approach, Hypergraph, SelectedItem } from './types/hypergraph'
import './App.css'

// Re-export Approach for backward compatibility with components that import from App
export type { Approach } from './types/hypergraph'

function App() {
  const [approaches, setApproaches] = useState<Approach[]>([])
  const [currentApproach, setCurrentApproach] = useState<Approach | null>(null)
  const [loading, setLoading] = useState(true)
  const [hypergraph, setHypergraph] = useState<Hypergraph | null>(null)
  const [selectedItem, setSelectedItem] = useState<SelectedItem | null>(null)
  const [scoreMode, setScoreMode] = useState<'score' | 'propagated'>('propagated')
  const [resetKey, setResetKey] = useState(0)
  const [showTutorial, setShowTutorial] = useState(false)
  const [showWelcomeModal, setShowWelcomeModal] = useState(false)
  const [welcomeModalMode, setWelcomeModalMode] = useState<'choose' | 'create'>('choose')
  const [pendingMessage, setPendingMessage] = useState<string | null>(null)
  const [showSettings, setShowSettings] = useState(false)
  const [showExplore, setShowExplore] = useState(false)
  const [exploreHypothesis, setExploreHypothesis] = useState<string | null>(null)
  const [exploreSource, setExploreSource] = useState<GapMapSource | null>(null)

  // Use custom hooks for settings and auto mode
  const { settings, updateSettings } = useSettings()
  const autoMode = useAutoMode({
    folder: currentApproach?.folder || null,
    model: settings.autoModel,
    onModelUpdate: (model) => updateSettings({ autoModel: model }),
  })

  // Fetch approaches on mount
  useEffect(() => {
    fetchApproaches()
  }, [])

  // Show tutorial automatically when there are no approaches
  useEffect(() => {
    if (!loading && approaches.length === 0) {
      setShowTutorial(true)
    }
  }, [loading, approaches.length])

  // Fetch hypergraph when approach changes
  useEffect(() => {
    if (currentApproach) {
      fetchHypergraph(currentApproach.folder)
      // Set up WebSocket for live updates
      const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const ws = new WebSocket(`${wsProtocol}//${window.location.host}/ws/hypergraph/${currentApproach.folder}`)

      // Debounce rapid updates (backend may send multiple messages)
      let updateTimeout: ReturnType<typeof setTimeout> | null = null

      ws.onmessage = (event) => {
        // Handle ping messages
        if (event.data === 'ping') {
          return
        }
        try {
          const data = JSON.parse(event.data)
          console.log('[WS] Received message:', data.type)
          if (data.type === 'update') {
            // Debounce: wait 600ms before fetching, reset if another update arrives
            // (backend file watcher has 500ms debounce, so this covers both notifications)
            if (updateTimeout) {
              clearTimeout(updateTimeout)
            }
            updateTimeout = setTimeout(() => {
              console.log('[WS] Fetching updated hypergraph (debounced)')
              fetchHypergraph(currentApproach.folder)
              updateTimeout = null
            }, 600)
          }
        } catch (e) {
          console.error('WebSocket message error:', e)
        }
      }

      return () => {
        if (updateTimeout) clearTimeout(updateTimeout)
        ws.close()
      }
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
      console.log('[fetchHypergraph] Fetching hypergraph for', folder)
      const response = await fetch(`/api/approaches/${folder}/hypergraph`)
      if (response.ok) {
        const data = await response.json()
        console.log('[fetchHypergraph] Got data, setting state', data.claims?.length, 'claims')
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

  const handleCreateApproach = async (name: string, hypothesis: string, enableAutoMode?: boolean, model?: string) => {
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

          // Start auto mode if enabled
          if (enableAutoMode && model) {
            updateSettings({ autoModel: model })
            // Start auto mode after a brief delay to let the approach load
            setTimeout(() => {
              autoMode.start(data.folder)
            }, 500)
          }
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

  const handleCleanup = async () => {
    if (!currentApproach) return

    try {
      const response = await fetch(`/api/approaches/${currentApproach.folder}/cleanup`, {
        method: 'POST',
      })
      const data = await response.json()
      if (data.success) {
        if (data.removed_count > 0) {
          alert(`Removed ${data.removed_count} unreachable node(s)`)
        } else {
          alert('No unreachable nodes found. Hypergraph is clean!')
        }
        // WebSocket will trigger the refresh - no need to fetch manually
      }
    } catch (error) {
      console.error('Failed to cleanup hypergraph:', error)
    }
  }

  const handleDeleteClaim = useCallback(async (claimId: string) => {
    if (!currentApproach) return

    try {
      const response = await fetch(`/api/approaches/${currentApproach.folder}/claims/${claimId}`, {
        method: 'DELETE',
      })
      if (!response.ok) {
        const data = await response.json()
        alert(`Failed to delete claim: ${data.detail}`)
        return
      }
      // Clear selection if the deleted claim was selected
      if (selectedItem?.type === 'claim' && selectedItem.id === claimId) {
        setSelectedItem(null)
      }
      // WebSocket will trigger the refresh - no need to fetch manually
    } catch (error) {
      console.error('Failed to delete claim:', error)
      alert('Failed to delete claim')
    }
  }, [currentApproach, selectedItem])

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
      {(showWelcomeModal || (!loading && !currentApproach)) && (
        <WelcomeModal
          approaches={approaches}
          onSelect={(approach) => {
            handleSelectApproach(approach)
            setShowWelcomeModal(false)
            setWelcomeModalMode('choose')
            setExploreHypothesis(null)
            setExploreSource(null)
          }}
          onCreate={(name, hypothesis, enableAutoMode, model) => {
            handleCreateApproach(name, hypothesis, enableAutoMode, model)
            setShowWelcomeModal(false)
            setWelcomeModalMode('choose')
            setExploreHypothesis(null)
            setExploreSource(null)
          }}
          initialMode={welcomeModalMode}
          initialHypothesis={exploreHypothesis || undefined}
          exploreSource={exploreSource || undefined}
          onOpenExplore={() => {
            setShowWelcomeModal(false)
            setShowExplore(true)
          }}
          onBackToExplore={exploreSource ? () => {
            // Go back to ExploreModal with the source selection
            setShowWelcomeModal(false)
            setWelcomeModalMode('choose')
            setShowExplore(true)
          } : undefined}
          onBack={() => {
            // Reset state when user clicks Back from create mode (to choose mode)
            setWelcomeModalMode('choose')
            setExploreHypothesis(null)
            setExploreSource(null)
          }}
          onClose={currentApproach ? () => {
            setShowWelcomeModal(false)
            setWelcomeModalMode('choose')
            setExploreHypothesis(null)
            setExploreSource(null)
          } : undefined}
        />
      )}
      {showTutorial && (
        <TutorialModal
          onClose={() => setShowTutorial(false)}
          onGetStarted={() => {
            setShowTutorial(false)
            setShowWelcomeModal(true)
          }}
        />
      )}
      <header className="app-header">
        <div className="header-left">
          <h1>Entailment Trees</h1>
        </div>
        <div className="header-center">
          <ApproachSelector
            approaches={approaches}
            currentApproach={currentApproach}
            onSelect={handleSelectApproach}
            onRequestCreate={() => {
              setWelcomeModalMode('create')
              setShowWelcomeModal(true)
            }}
          />
        </div>
        <div className="header-right">
          <button
            className="tutorial-button"
            onClick={() => setShowTutorial(true)}
            title="Show tutorial"
          >
            ?
          </button>
          <button
            className="toolbar-button explore-button"
            onClick={() => setShowExplore(true)}
            title="Explore Gap Map"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10"></circle>
              <polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76"></polygon>
            </svg>
          </button>
          <button
            className="toolbar-button settings-button"
            onClick={() => setShowSettings(true)}
            title="Settings"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="3"></circle>
              <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
            </svg>
          </button>
        </div>
      </header>

      <SettingsModal
        isOpen={showSettings}
        onClose={() => setShowSettings(false)}
        settings={settings}
        onSettingsChange={updateSettings}
      />

      <ExploreModal
        isOpen={showExplore}
        onClose={() => {
          setShowExplore(false)
          // Clear source when closing without using an idea
          setExploreSource(null)
          setExploreHypothesis(null)
        }}
        onUseIdea={(hypothesis, source) => {
          setExploreHypothesis(hypothesis)
          setExploreSource(source)
          setShowExplore(false)
          setWelcomeModalMode('create')
          setShowWelcomeModal(true)
        }}
        initialSelection={exploreSource || undefined}
      />

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
              onScoreModeChange={setScoreMode}
              resetKey={resetKey}
              onReset={() => setResetKey(k => k + 1)}
              onCleanup={handleCleanup}
              onDelete={handleDeleteClaim}
              onSendMessage={setPendingMessage}
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
                    scoreMode={scoreMode}
                    folder={currentApproach?.folder || null}
                    onClose={handleCloseDetail}
                  />
                )}
              </div>
              <div className="chat-pane">
                <ChatInterface
                  approachFolder={currentApproach?.folder || null}
                  approachName={currentApproach?.description || currentApproach?.name || null}
                  pendingMessage={pendingMessage}
                  onPendingMessageHandled={() => setPendingMessage(null)}
                  autoModeActive={autoMode.active}
                  autoModePaused={autoMode.paused}
                  autoTurnCount={autoMode.turnCount}
                  autoMaxTurns={autoMode.maxTurns}
                  onAutoStart={() => currentApproach && autoMode.start()}
                  onAutoPause={autoMode.pause}
                  onAutoResume={autoMode.resume}
                  onAutoStop={autoMode.stop}
                  onAutoTurnUpdate={autoMode.setTurnCount}
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
