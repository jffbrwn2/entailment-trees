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
  score: number | null
  propagated_negative_log?: number | string
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
  const [showTutorial, setShowTutorial] = useState(false)
  const [showWelcomeModal, setShowWelcomeModal] = useState(false)
  const [welcomeModalMode, setWelcomeModalMode] = useState<'choose' | 'create'>('choose')
  const [pendingMessage, setPendingMessage] = useState<string | null>(null)
  const [showSettings, setShowSettings] = useState(false)
  const [showExplore, setShowExplore] = useState(false)
  const [exploreHypothesis, setExploreHypothesis] = useState<string | null>(null)
  const [exploreSource, setExploreSource] = useState<GapMapSource | null>(null)

  // Model settings
  const [claudeModel, setClaudeModel] = useState<string>('anthropic/claude-sonnet-4')
  const [evaluatorModel, setEvaluatorModel] = useState<string>('anthropic/claude-sonnet-4')
  const [autoModel, setAutoModel] = useState<string>('anthropic/claude-3-haiku')

  // Tool toggles
  const [edisonToolsEnabled, setEdisonToolsEnabled] = useState(true)
  const [gapMapToolsEnabled, setGapMapToolsEnabled] = useState(true)

  // Auto mode state
  const [autoModeActive, setAutoModeActive] = useState(false)
  const [autoModePaused, setAutoModePaused] = useState(false)
  const [autoTurnCount, setAutoTurnCount] = useState(0)
  const [autoMaxTurns, setAutoMaxTurns] = useState(20)

  // Apply dark/light mode
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', darkMode ? 'dark' : 'light')
  }, [darkMode])

  // Fetch approaches and settings on mount
  useEffect(() => {
    fetchApproaches()
    fetchSettings()
  }, [])

  // Fetch settings from backend
  const fetchSettings = async () => {
    try {
      const response = await fetch('/api/settings')
      if (response.ok) {
        const data = await response.json()
        setClaudeModel(data.chatModel || 'anthropic/claude-sonnet-4')
        setEvaluatorModel(data.evaluatorModel || 'anthropic/claude-sonnet-4')
        setAutoModel(data.autoModel || 'anthropic/claude-3-haiku')
        setEdisonToolsEnabled(data.edisonToolsEnabled ?? true)
        setGapMapToolsEnabled(data.gapMapToolsEnabled ?? true)
      }
    } catch (error) {
      console.error('Failed to fetch settings:', error)
    }
  }

  // Update settings on backend
  const updateSettings = async (newSettings: {
    claudeModel?: string
    evaluatorModel?: string
    autoModel?: string
    edisonToolsEnabled?: boolean
    gapMapToolsEnabled?: boolean
  }) => {
    try {
      // Map frontend names to backend API names
      const data: Record<string, unknown> = {}
      if (newSettings.claudeModel !== undefined) data.chatModel = newSettings.claudeModel
      if (newSettings.evaluatorModel !== undefined) data.evaluatorModel = newSettings.evaluatorModel
      if (newSettings.autoModel !== undefined) data.autoModel = newSettings.autoModel
      if (newSettings.edisonToolsEnabled !== undefined) data.edisonToolsEnabled = newSettings.edisonToolsEnabled
      if (newSettings.gapMapToolsEnabled !== undefined) data.gapMapToolsEnabled = newSettings.gapMapToolsEnabled

      await fetch('/api/settings', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      })
    } catch (error) {
      console.error('Failed to update settings:', error)
    }
  }

  // Show tutorial automatically when there are no approaches
  useEffect(() => {
    if (!loading && approaches.length === 0) {
      setShowTutorial(true)
    }
  }, [loading, approaches.length])

  // Fetch auto mode status when approach changes
  useEffect(() => {
    if (currentApproach) {
      fetchAutoModeStatus(currentApproach.folder)
    } else {
      // Reset auto mode state when no approach selected
      setAutoModeActive(false)
      setAutoModePaused(false)
      setAutoTurnCount(0)
    }
  }, [currentApproach])

  const fetchAutoModeStatus = async (folder: string) => {
    try {
      const response = await fetch(`/api/approaches/${folder}/auto/status`)
      if (response.ok) {
        const status = await response.json()
        setAutoModeActive(status.active)
        setAutoModePaused(status.paused)
        setAutoTurnCount(status.turn_count)
        if (status.max_turns) setAutoMaxTurns(status.max_turns)
        if (status.model) setAutoModel(status.model)
      }
    } catch (error) {
      console.error('Failed to fetch auto mode status:', error)
    }
  }

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
            setAutoModel(model)
            // Start auto mode after a brief delay to let the approach load
            setTimeout(() => {
              handleAutoStart(data.folder, model)
            }, 500)
          }
        }
      }
    } catch (error) {
      console.error('Failed to create approach:', error)
    }
  }

  // Auto mode control functions
  const handleAutoStart = async (folder: string, model: string) => {
    try {
      const response = await fetch(`/api/approaches/${folder}/auto/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model }),
      })
      if (response.ok) {
        const data = await response.json()
        setAutoModeActive(true)
        setAutoModePaused(false)
        setAutoTurnCount(0)
        setAutoMaxTurns(data.max_turns)
      }
    } catch (error) {
      console.error('Failed to start auto mode:', error)
    }
  }

  const handleAutoStop = async () => {
    if (!currentApproach) return
    try {
      await fetch(`/api/approaches/${currentApproach.folder}/auto/stop`, { method: 'POST' })
      setAutoModeActive(false)
      setAutoModePaused(false)
    } catch (error) {
      console.error('Failed to stop auto mode:', error)
    }
  }

  const handleAutoPause = async () => {
    if (!currentApproach) return
    try {
      await fetch(`/api/approaches/${currentApproach.folder}/auto/pause`, { method: 'POST' })
      setAutoModePaused(true)
    } catch (error) {
      console.error('Failed to pause auto mode:', error)
    }
  }

  const handleAutoResume = async () => {
    if (!currentApproach) return
    try {
      await fetch(`/api/approaches/${currentApproach.folder}/auto/resume`, { method: 'POST' })
      setAutoModePaused(false)
      setAutoModeActive(true)
    } catch (error) {
      console.error('Failed to resume auto mode:', error)
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
        settings={{
          darkMode,
          claudeModel,
          evaluatorModel,
          autoModel,
          edisonToolsEnabled,
          gapMapToolsEnabled,
        }}
        onSettingsChange={(newSettings) => {
          // Update local state
          setDarkMode(newSettings.darkMode)
          setClaudeModel(newSettings.claudeModel)
          setEvaluatorModel(newSettings.evaluatorModel)
          setAutoModel(newSettings.autoModel)
          setEdisonToolsEnabled(newSettings.edisonToolsEnabled)
          setGapMapToolsEnabled(newSettings.gapMapToolsEnabled)

          // Sync non-UI settings with backend
          updateSettings({
            claudeModel: newSettings.claudeModel,
            evaluatorModel: newSettings.evaluatorModel,
            autoModel: newSettings.autoModel,
            edisonToolsEnabled: newSettings.edisonToolsEnabled,
            gapMapToolsEnabled: newSettings.gapMapToolsEnabled,
          })
        }}
      />

      <ExploreModal
        isOpen={showExplore}
        onClose={() => setShowExplore(false)}
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
                  autoModeActive={autoModeActive}
                  autoModePaused={autoModePaused}
                  autoTurnCount={autoTurnCount}
                  autoMaxTurns={autoMaxTurns}
                  onAutoStart={() => currentApproach && handleAutoStart(currentApproach.folder, autoModel)}
                  onAutoPause={handleAutoPause}
                  onAutoResume={handleAutoResume}
                  onAutoStop={handleAutoStop}
                  onAutoTurnUpdate={setAutoTurnCount}
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
