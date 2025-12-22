import { useState, useEffect } from 'react'
import './ExploreModal.css'

interface Gap {
  id: string
  name: string
  slug: string
  description: string
  field: { id: string; name: string }
  foundationalCapabilities: string[]
  tags: string[]
}

interface Capability {
  id: string
  name: string
  slug: string
  description: string
  gaps: string[]
  resources: string[]
  tags: string[]
}

interface Field {
  id: string
  name: string
  slug: string
}

interface Resource {
  id: string
  title: string
  url: string
  summary: string
  types: string[]
}

export interface GapMapSource {
  type: 'gap' | 'capability'
  name: string
  sourceGapName?: string  // For capabilities reached via a gap
}

interface Props {
  isOpen: boolean
  onClose: () => void
  onUseIdea: (hypothesis: string, source: GapMapSource) => void
  initialSelection?: GapMapSource  // To restore state when coming back
}

type TopicType = 'gap' | 'capability'

function ExploreModal({ isOpen, onClose, onUseIdea, initialSelection }: Props) {
  const [activeTab, setActiveTab] = useState<'gaps' | 'capabilities'>('gaps')
  const [gaps, setGaps] = useState<Gap[]>([])
  const [capabilities, setCapabilities] = useState<Capability[]>([])
  const [fields, setFields] = useState<Field[]>([])
  const [resources, setResources] = useState<Resource[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [searchQuery, setSearchQuery] = useState('')
  const [selectedField, setSelectedField] = useState<string>('')

  const [selectedTopic, setSelectedTopic] = useState<{ type: TopicType; item: Gap | Capability } | null>(null)
  const [navigationHistory, setNavigationHistory] = useState<{ type: TopicType; item: Gap | Capability }[]>([])
  const [sourceGap, setSourceGap] = useState<Gap | null>(null)  // Track gap when navigating to capability
  const [relatedItems, setRelatedItems] = useState<Gap[] | Capability[]>([])
  const [loadingRelated, setLoadingRelated] = useState(false)
  const [generatingHypothesis, setGeneratingHypothesis] = useState(false)

  // Reset navigation state when modal opens
  useEffect(() => {
    if (isOpen) {
      // Reset state
      setNavigationHistory([])
      setRelatedItems([])
      setSearchQuery('')
      setSelectedField('')
      setGeneratingHypothesis(false)

      // Fetch data if not already loaded
      if (gaps.length === 0) {
        fetchData()
      }

      // If coming back with initialSelection, restore that state
      if (initialSelection && gaps.length > 0) {
        restoreSelection()
      } else if (!initialSelection) {
        // Only reset to list view if not restoring
        setSelectedTopic(null)
        setSourceGap(null)
      }
    }
  }, [isOpen])

  // Restore selection when data is loaded and we have an initialSelection
  useEffect(() => {
    if (isOpen && initialSelection && gaps.length > 0 && capabilities.length > 0) {
      restoreSelection()
    }
  }, [gaps.length, capabilities.length])

  const restoreSelection = () => {
    if (!initialSelection) return

    if (initialSelection.type === 'gap') {
      const gap = gaps.find(g => g.name === initialSelection.name)
      if (gap) {
        setSelectedTopic({ type: 'gap', item: gap })
        setSourceGap(null)
      }
    } else if (initialSelection.type === 'capability') {
      const cap = capabilities.find(c => c.name === initialSelection.name)
      if (cap) {
        setSelectedTopic({ type: 'capability', item: cap })
        // Restore source gap if we came from one
        if (initialSelection.sourceGapName) {
          const gap = gaps.find(g => g.name === initialSelection.sourceGapName)
          if (gap) setSourceGap(gap)
        }
      }
    }
  }

  // Fetch related items when a topic is selected
  useEffect(() => {
    if (selectedTopic) {
      fetchRelatedItems()
    }
  }, [selectedTopic])

  const fetchData = async () => {
    setLoading(true)
    setError(null)
    try {
      const [gapsRes, capsRes, fieldsRes, resourcesRes] = await Promise.all([
        fetch('/api/gapmap/gaps'),
        fetch('/api/gapmap/capabilities'),
        fetch('/api/gapmap/fields'),
        fetch('/api/gapmap/resources'),
      ])

      if (!gapsRes.ok || !capsRes.ok || !fieldsRes.ok || !resourcesRes.ok) {
        throw new Error('Failed to fetch data from Gap Map')
      }

      const [gapsData, capsData, fieldsData, resourcesData] = await Promise.all([
        gapsRes.json(),
        capsRes.json(),
        fieldsRes.json(),
        resourcesRes.json(),
      ])

      setGaps(gapsData)
      setCapabilities(capsData)
      setFields(fieldsData)
      setResources(resourcesData)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred')
    } finally {
      setLoading(false)
    }
  }

  const fetchRelatedItems = async () => {
    if (!selectedTopic) return

    setLoadingRelated(true)
    try {
      if (selectedTopic.type === 'gap') {
        const gap = selectedTopic.item as Gap
        const response = await fetch(`/api/gapmap/gaps/${gap.id}/capabilities`)
        if (response.ok) {
          const data = await response.json()
          setRelatedItems(data)
        }
      } else {
        const capability = selectedTopic.item as Capability
        const response = await fetch(`/api/gapmap/capabilities/${capability.id}/gaps`)
        if (response.ok) {
          const data = await response.json()
          setRelatedItems(data)
        }
      }
    } catch (err) {
      console.error('Failed to fetch related items:', err)
    } finally {
      setLoadingRelated(false)
    }
  }

  const filterItems = <T extends Gap | Capability>(items: T[]): T[] => {
    return items.filter((item) => {
      const matchesSearch =
        !searchQuery ||
        (item.name || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
        (item.description || '').toLowerCase().includes(searchQuery.toLowerCase())

      const matchesField =
        !selectedField ||
        ('field' in item && (item as Gap).field?.name === selectedField)

      return matchesSearch && matchesField
    })
  }

  const handleUseIdea = async () => {
    if (!selectedTopic) return

    // Build source info for passing back
    const source: GapMapSource = {
      type: selectedTopic.type,
      name: selectedTopic.item.name,
      sourceGapName: sourceGap?.name,
    }

    setGeneratingHypothesis(true)
    try {
      let requestBody: Record<string, string>

      if (selectedTopic.type === 'capability' && sourceGap) {
        // Capability reached from a gap - generate "X can be used to Y"
        requestBody = {
          mode: 'capability_gap',
          capability_name: selectedTopic.item.name,
          capability_description: selectedTopic.item.description || '',
          gap_name: sourceGap.name,
          gap_description: sourceGap.description || '',
        }
      } else if (selectedTopic.type === 'gap') {
        // Gap - generate a hypothesis about solving it
        requestBody = {
          mode: 'gap_only',
          gap_name: selectedTopic.item.name,
          gap_description: selectedTopic.item.description || '',
        }
      } else {
        // Capability without source gap - generate hypothesis for capability alone
        requestBody = {
          mode: 'capability_only',
          capability_name: selectedTopic.item.name,
          capability_description: selectedTopic.item.description || '',
        }
      }

      const response = await fetch('/api/gapmap/generate-hypothesis', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestBody),
      })

      if (response.ok) {
        const data = await response.json()
        onUseIdea(data.hypothesis, source)
        return
      }
    } catch (err) {
      console.error('Failed to generate hypothesis:', err)
    } finally {
      setGeneratingHypothesis(false)
    }

    // Fallback if API fails
    const item = selectedTopic.item
    if (selectedTopic.type === 'capability' && sourceGap) {
      onUseIdea(`${item.name} can be used to address ${sourceGap.name}`, source)
    } else {
      onUseIdea(`${item.name}: ${item.description || ''}`, source)
    }
  }

  const navigateToTopic = (topic: { type: TopicType; item: Gap | Capability }) => {
    // Push current topic to history before navigating
    if (selectedTopic) {
      setNavigationHistory((prev) => [...prev, selectedTopic])
      // Track source gap when navigating from gap to capability
      if (selectedTopic.type === 'gap' && topic.type === 'capability') {
        setSourceGap(selectedTopic.item as Gap)
      }
    }
    setSelectedTopic(topic)
  }

  const handleBack = () => {
    if (navigationHistory.length > 0) {
      // Pop from history and go to previous topic
      const newHistory = [...navigationHistory]
      const previousTopic = newHistory.pop()!
      setNavigationHistory(newHistory)
      setSelectedTopic(previousTopic)
      // Clear source gap if going back to a gap
      if (previousTopic.type === 'gap') {
        setSourceGap(null)
      }
    } else {
      // No history - go back to list
      setSelectedTopic(null)
      setRelatedItems([])
      setSourceGap(null)
    }
  }

  const handleBackToList = () => {
    setSelectedTopic(null)
    setNavigationHistory([])
    setRelatedItems([])
    setSourceGap(null)
  }

  if (!isOpen) return null

  return (
    <div className="explore-overlay" onClick={onClose}>
      <div className="explore-modal" onClick={(e) => e.stopPropagation()}>
        {selectedTopic ? (
          // Detail View
          <>
            <div className="explore-header">
              <div className="header-nav">
                <button className="back-button" onClick={handleBack}>
                  ← Back
                </button>
                {navigationHistory.length > 0 && (
                  <button className="list-button" onClick={handleBackToList}>
                    List
                  </button>
                )}
              </div>
              <button className="close-button" onClick={onClose}>
                ×
              </button>
            </div>
            <div className="explore-content detail-view">
              <div className="detail-title">
                <h2>{selectedTopic.item.name}</h2>
                {'field' in selectedTopic.item && selectedTopic.item.field && (
                  <span className="field-badge">{selectedTopic.item.field.name}</span>
                )}
              </div>

              {selectedTopic.item.tags && Array.isArray(selectedTopic.item.tags) && selectedTopic.item.tags.length > 0 && (
                <div className="tags-row">
                  {selectedTopic.item.tags.map((tag, index) => (
                    <span key={tag || index} className="tag">{tag}</span>
                  ))}
                </div>
              )}

              <p className="detail-description">{selectedTopic.item.description || 'No description available.'}</p>

              {/* Show source gap for capabilities reached via navigation */}
              {selectedTopic.type === 'capability' && sourceGap && (
                <div className="source-gap-indicator">
                  <span className="source-label">Addresses:</span>
                  <button
                    className="source-gap-link"
                    onClick={() => {
                      // Navigate back to the gap
                      setSelectedTopic({ type: 'gap', item: sourceGap })
                      setSourceGap(null)
                      setNavigationHistory([])
                    }}
                  >
                    {sourceGap.name}
                  </button>
                </div>
              )}

              {/* Show resources for capabilities */}
              {selectedTopic.type === 'capability' && (() => {
                const cap = selectedTopic.item as Capability
                const capResources = resources.filter(r => (cap.resources || []).includes(r.id))
                if (capResources.length === 0) return null
                return (
                  <div className="related-section">
                    <h3>Associated Work</h3>
                    <ul className="resources-list">
                      {capResources.map((resource) => (
                        <li key={resource.id} className="resource-item">
                          {resource.url ? (
                            <a href={resource.url} target="_blank" rel="noopener noreferrer" className="resource-link">
                              {resource.title}
                              <span className="external-icon">↗</span>
                            </a>
                          ) : (
                            <span className="resource-title">{resource.title}</span>
                          )}
                          {resource.types && resource.types.length > 0 && (
                            <span className="resource-type">{resource.types[0]}</span>
                          )}
                        </li>
                      ))}
                    </ul>
                  </div>
                )
              })()}

              {/* Only show related capabilities for gaps */}
              {selectedTopic.type === 'gap' && (
                <div className="related-section">
                  <h3>Related Capabilities</h3>
                  {loadingRelated ? (
                    <div className="loading-text">Loading...</div>
                  ) : relatedItems.length > 0 ? (
                    <ul className="related-list">
                      {relatedItems.map((item) => (
                        <li
                          key={item.id}
                          className="related-item"
                          onClick={() =>
                            navigateToTopic({
                              type: 'capability',
                              item,
                            })
                          }
                        >
                          <span className="related-name">{item.name}</span>
                          <span className="related-chevron">›</span>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="no-related">No related capabilities found</p>
                  )}
                </div>
              )}

              <button
                className="use-idea-button"
                onClick={handleUseIdea}
                disabled={generatingHypothesis}
              >
                {generatingHypothesis ? 'Generating hypothesis...' : 'Use this idea'}
              </button>
            </div>
          </>
        ) : (
          // List View
          <>
            <div className="explore-header">
              <h2>Explore Gap Map</h2>
              <button className="close-button" onClick={onClose}>
                ×
              </button>
            </div>
            <div className="explore-content">
              <div className="explore-tabs">
                <button
                  className={`tab-button ${activeTab === 'gaps' ? 'active' : ''}`}
                  onClick={() => setActiveTab('gaps')}
                >
                  Research Gaps
                </button>
                <button
                  className={`tab-button ${activeTab === 'capabilities' ? 'active' : ''}`}
                  onClick={() => setActiveTab('capabilities')}
                >
                  Capabilities
                </button>
              </div>

              <div className="explore-filters">
                <input
                  type="text"
                  placeholder="Search..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="search-input"
                />
                {activeTab === 'gaps' && (
                  <select
                    value={selectedField}
                    onChange={(e) => setSelectedField(e.target.value)}
                    className="field-select"
                  >
                    <option value="">All Fields</option>
                    {fields.map((field) => (
                      <option key={field.id} value={field.name}>
                        {field.name}
                      </option>
                    ))}
                  </select>
                )}
              </div>

              {loading ? (
                <div className="loading-container">
                  <div className="loading-spinner" />
                  <p>Loading Gap Map data...</p>
                </div>
              ) : error ? (
                <div className="error-container">
                  <p className="error-text">{error}</p>
                  <button onClick={fetchData} className="retry-button">
                    Retry
                  </button>
                </div>
              ) : (
                <div className="topic-grid">
                  {activeTab === 'gaps'
                    ? filterItems(gaps).map((gap) => (
                        <div
                          key={gap.id}
                          className="topic-card"
                          onClick={() => setSelectedTopic({ type: 'gap', item: gap })}
                        >
                          <h3 className="topic-name">{gap.name}</h3>
                          {gap.field && gap.field.name && (
                            <span className="topic-field">{gap.field.name}</span>
                          )}
                          <p className="topic-description">
                            {(gap.description || '').length > 120
                              ? gap.description.slice(0, 120) + '...'
                              : gap.description || 'No description'}
                          </p>
                        </div>
                      ))
                    : filterItems(capabilities).map((cap) => (
                        <div
                          key={cap.id}
                          className="topic-card"
                          onClick={() => setSelectedTopic({ type: 'capability', item: cap })}
                        >
                          <h3 className="topic-name">{cap.name}</h3>
                          <p className="topic-description">
                            {(cap.description || '').length > 120
                              ? cap.description.slice(0, 120) + '...'
                              : cap.description || 'No description'}
                          </p>
                        </div>
                      ))}
                </div>
              )}

              {!loading && !error && (
                <div className="results-count">
                  {activeTab === 'gaps'
                    ? `${filterItems(gaps).length} research gaps`
                    : `${filterItems(capabilities).length} capabilities`}
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  )
}

export default ExploreModal
