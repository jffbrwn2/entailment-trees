import { useState, useRef, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import AutoControls from './AutoControls'
import { truncate } from '../utils/formatters'
import './ChatInterface.css'

interface ToolUse {
  name: string
  status: 'running' | 'done' | 'error'
}

interface MessagePart {
  type: 'text' | 'tool'
  content?: string  // for text parts
  tool?: ToolUse    // for tool parts
}

interface Message {
  id: string
  role: 'user' | 'assistant' | 'auto' | 'system'
  parts: MessagePart[]  // interleaved text and tool uses
}

interface Conversation {
  session_id: string
  started_at: string
  ended_at: string | null
  num_turns: number
  filename: string
}

interface Props {
  approachFolder: string | null
  approachName: string | null
  pendingMessage?: string | null
  onPendingMessageHandled?: () => void
  // Auto mode props
  autoModeActive?: boolean
  autoModePaused?: boolean
  autoTurnCount?: number
  autoMaxTurns?: number
  onAutoStart?: () => void
  onAutoPause?: () => void
  onAutoResume?: () => void
  onAutoStop?: () => void
  onAutoTurnUpdate?: (turn: number) => void
}

interface SuggestionButton {
  label: string
  prompt: string
}

const suggestions: SuggestionButton[] = [
  {
    label: "Generate an entailment tree for this idea",
    prompt: "Generate an entailment tree for this idea. Do not finish until all entailments pass as valid."
  },
  {
    label: "Find evidence for the claims",
    prompt: "Find evidence for the claims. Use the internet to look for reputable sources. The evidence should give accurate, fair context on whether the claim is true, false, or unsure. Add the evidence to the claims and run the claim evaluator tool."
  },
  {
    label: "Write simulations to test the claims",
    prompt: "Write simulations to test the claims that can be validated through computation. Create Python scripts that model the relevant physics or behavior, run them, and use the results as evidence. Add the simulation evidence to the claims and run the claim evaluator tool."
  },
]

function ChatInterface({
  approachFolder,
  approachName,
  pendingMessage,
  onPendingMessageHandled,
  autoModeActive = false,
  autoModePaused = false,
  autoTurnCount = 0,
  autoMaxTurns = 20,
  onAutoStart,
  onAutoPause,
  onAutoResume,
  onAutoStop,
  onAutoTurnUpdate,
}: Props) {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [selectedConversation, setSelectedConversation] = useState<string>('')
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const abortControllerRef = useRef<AbortController | null>(null)
  const [textareaHeight, setTextareaHeight] = useState(44)
  const resizeRef = useRef<{ startY: number; startHeight: number } | null>(null)

  // Handle Escape key to cancel streaming
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isStreaming && abortControllerRef.current) {
        abortControllerRef.current.abort()
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [isStreaming])

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Handle pending messages from other components (e.g., Fix button)
  useEffect(() => {
    if (pendingMessage && approachFolder && !isStreaming) {
      setInput(pendingMessage)
      onPendingMessageHandled?.()
      // Submit after a brief delay
      setTimeout(() => {
        const form = document.querySelector('.input-area') as HTMLFormElement
        if (form) {
          form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }))
        }
      }, 50)
    }
  }, [pendingMessage, approachFolder, isStreaming, onPendingMessageHandled])

  // Clear messages and optionally load history when approach changes
  useEffect(() => {
    // Clear current messages and conversations
    setMessages([])
    setConversations([])
    setSelectedConversation('')
    inputRef.current?.focus()

    // If we have an approach, fetch conversations and load the most recent
    if (approachFolder) {
      fetchConversations(approachFolder)
    }
  }, [approachFolder])

  // WebSocket for auto mode events
  useEffect(() => {
    if (!approachFolder) return

    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const ws = new WebSocket(`${wsProtocol}//${window.location.host}/ws/hypergraph/${approachFolder}`)

    // Track current assistant message ID for streaming
    let currentAssistantMessageId: string | null = null

    ws.onmessage = (event) => {
      if (event.data === 'ping') return

      try {
        const data = JSON.parse(event.data)

        switch (data.type) {
          case 'auto_message':
            // Add auto agent message
            const autoMessage: Message = {
              id: `auto-${Date.now()}`,
              role: 'auto',
              parts: [{ type: 'text', content: data.text }],
            }
            setMessages((prev) => [...prev, autoMessage])
            break

          case 'text':
            // Claude's response text (during auto mode)
            if (!currentAssistantMessageId) {
              currentAssistantMessageId = `assistant-${Date.now()}`
              setMessages((prev) => [
                ...prev,
                { id: currentAssistantMessageId!, role: 'assistant', parts: [] },
              ])
            }
            setMessages((prev) =>
              prev.map((m) => {
                if (m.id !== currentAssistantMessageId) return m
                const parts = [...m.parts]
                const lastPart = parts[parts.length - 1]
                if (lastPart && lastPart.type === 'text') {
                  parts[parts.length - 1] = { ...lastPart, content: (lastPart.content || '') + (data.text || '') }
                } else {
                  parts.push({ type: 'text', content: data.text || '' })
                }
                return { ...m, parts }
              })
            )
            break

          case 'tool_use':
            if (currentAssistantMessageId) {
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === currentAssistantMessageId
                    ? {
                        ...m,
                        parts: [
                          ...m.parts,
                          { type: 'tool' as const, tool: { name: data.tool_name || 'unknown', status: 'running' as const } },
                        ],
                      }
                    : m
                )
              )
            }
            break

          case 'tool_result':
            if (currentAssistantMessageId) {
              setMessages((prev) =>
                prev.map((m) => {
                  if (m.id !== currentAssistantMessageId) return m
                  const parts = [...m.parts]
                  for (let i = parts.length - 1; i >= 0; i--) {
                    const part = parts[i]
                    if (part.type === 'tool' && part.tool?.name === data.tool_name && part.tool?.status === 'running') {
                      parts[i] = { ...part, tool: { ...part.tool, status: 'done' } }
                      break
                    }
                  }
                  return { ...m, parts }
                })
              )
            }
            break

          case 'done':
            // Claude finished responding - reset for next turn
            currentAssistantMessageId = null
            break

          case 'auto_turn':
            onAutoTurnUpdate?.(data.turn_number)
            break

          case 'auto_status':
            // Status updates are handled by parent component via polling
            break

          case 'error':
            if (currentAssistantMessageId) {
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === currentAssistantMessageId
                    ? { ...m, parts: [...m.parts, { type: 'text' as const, content: `\n\n*Error: ${data.error}*` }] }
                    : m
                )
              )
            }
            break

          case 'warning':
            // Display warning as a system message
            const warningMessage: Message = {
              id: `warning-${Date.now()}`,
              role: 'system',
              parts: [{ type: 'text', content: data.warning }],
            }
            setMessages((prev) => [...prev, warningMessage])
            break
        }
      } catch (e) {
        console.error('WebSocket message error:', e)
      }
    }

    return () => {
      ws.close()
    }
  }, [approachFolder, onAutoTurnUpdate])

  const handleNewChat = async () => {
    if (!approachFolder || isStreaming) return

    try {
      // Call backend to properly clear session state
      const response = await fetch(`/api/approaches/${approachFolder}/new-session`, {
        method: 'POST',
      })
      if (response.ok) {
        // Clear UI state
        setMessages([])
        setSelectedConversation('')
        inputRef.current?.focus()
      } else {
        console.error('Failed to start new chat:', response.status)
      }
    } catch (error) {
      console.error('Failed to start new chat:', error)
    }
  }

  const fetchConversations = async (folder: string) => {
    try {
      const response = await fetch(`/api/approaches/${folder}/conversations`)
      if (!response.ok) return

      const convos: Conversation[] = await response.json()
      setConversations(convos)

      // Auto-load the most recent conversation
      if (convos.length > 0) {
        setSelectedConversation(convos[0].filename)
        loadConversation(convos[0].filename)
      }
    } catch (error) {
      console.error('Failed to fetch conversations:', error)
    }
  }

  const loadConversation = async (filename: string) => {
    if (!filename) {
      setMessages([])
      return
    }

    try {
      const response = await fetch(`/api/conversations/${filename}`)
      if (!response.ok) return

      const log = await response.json()

      // Convert turns to messages format
      const loadedMessages: Message[] = []
      for (const turn of log.turns) {
        // Add user message
        loadedMessages.push({
          id: `${turn.turn_number}-user`,
          role: 'user',
          parts: [{ type: 'text', content: turn.user_input }],
        })
        // Build assistant message parts - use response_parts if available for correct interleaving
        let assistantParts: MessagePart[]
        if (turn.response_parts && turn.response_parts.length > 0) {
          // Use interleaved response_parts from conversation log
          assistantParts = turn.response_parts.map((part: { type: string; content?: string; tool_name?: string }) => {
            if (part.type === 'text') {
              return { type: 'text' as const, content: part.content || '' }
            } else {
              return { type: 'tool' as const, tool: { name: part.tool_name || 'unknown', status: 'done' as const } }
            }
          })
        } else {
          // Fallback for old logs without response_parts - tools at end
          assistantParts = [{ type: 'text', content: turn.claude_response }]
          for (const t of turn.tools_used) {
            assistantParts.push({
              type: 'tool',
              tool: { name: t.tool_name, status: 'done' as const }
            })
          }
        }
        loadedMessages.push({
          id: `${turn.turn_number}-assistant`,
          role: 'assistant',
          parts: assistantParts,
        })
      }

      setMessages(loadedMessages)
    } catch (error) {
      console.error('Failed to load conversation:', error)
    }
  }

  const handleConversationChange = async (filename: string) => {
    setSelectedConversation(filename)

    if (filename && approachFolder) {
      // Switching to an old conversation - resume that conversation's session
      try {
        await fetch(`/api/approaches/${approachFolder}/resume-session`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ conversation_filename: filename }),
        })
      } catch (error) {
        console.error('Failed to resume session:', error)
      }
      loadConversation(filename)
    } else if (approachFolder) {
      // Selecting "New conversation" - start fresh
      try {
        await fetch(`/api/approaches/${approachFolder}/new-session`, {
          method: 'POST',
        })
      } catch (error) {
        console.error('Failed to start new session:', error)
      }
      setMessages([])
    }
  }

  const formatConversationLabel = (conv: Conversation) => {
    const date = new Date(conv.started_at)
    const timeStr = date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    const dateStr = date.toLocaleDateString([], { month: 'short', day: 'numeric' })
    return `${dateStr} ${timeStr} (${conv.num_turns} turns)`
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || isStreaming) return

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      parts: [{ type: 'text', content: input.trim() }],
    }

    setMessages((prev) => [...prev, userMessage])
    setInput('')
    setIsStreaming(true)

    // Create abort controller for this request
    abortControllerRef.current = new AbortController()

    // Create assistant message placeholder
    const assistantMessageId = (Date.now() + 1).toString()
    setMessages((prev) => [
      ...prev,
      { id: assistantMessageId, role: 'assistant', parts: [] },
    ])

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: userMessage.parts[0]?.content,
          approach_name: approachFolder,
        }),
        signal: abortControllerRef.current.signal,
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const reader = response.body?.getReader()
      const decoder = new TextDecoder()

      if (!reader) {
        throw new Error('No response body')
      }

      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })

        // Process complete SSE messages
        const lines = buffer.split('\n\n')
        buffer = lines.pop() || '' // Keep incomplete message in buffer

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6))
              handleStreamEvent(data, assistantMessageId)
            } catch (e) {
              console.error('Failed to parse SSE data:', e)
            }
          }
        }
      }
    } catch (error) {
      // Check if this was a user cancellation
      if (error instanceof Error && error.name === 'AbortError') {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantMessageId
              ? { ...m, parts: [...m.parts, { type: 'text' as const, content: '\n\n*[Cancelled by user]*' }] }
              : m
          )
        )
      } else {
        console.error('Chat error:', error)
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantMessageId
              ? { ...m, parts: [...m.parts, { type: 'text' as const, content: '\n\n*Error: Failed to get response*' }] }
              : m
          )
        )
      }
    } finally {
      setIsStreaming(false)
      abortControllerRef.current = null
      // Mark any running tools as done when stream ends
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantMessageId
            ? {
                ...m,
                parts: m.parts.map((part) =>
                  part.type === 'tool' && part.tool?.status === 'running'
                    ? { ...part, tool: { ...part.tool, status: 'done' as const } }
                    : part
                ),
              }
            : m
        )
      )
    }
  }

  const handleStreamEvent = (
    data: { type: string; text?: string; tool_name?: string; error?: string; full_response?: string },
    messageId: string
  ) => {
    switch (data.type) {
      case 'text':
        setMessages((prev) =>
          prev.map((m) => {
            if (m.id !== messageId) return m
            // Append text to the last text part, or create a new one
            const parts = [...m.parts]
            const lastPart = parts[parts.length - 1]
            if (lastPart && lastPart.type === 'text') {
              parts[parts.length - 1] = { ...lastPart, content: (lastPart.content || '') + (data.text || '') }
            } else {
              parts.push({ type: 'text', content: data.text || '' })
            }
            return { ...m, parts }
          })
        )
        break

      case 'tool_use':
        setMessages((prev) =>
          prev.map((m) =>
            m.id === messageId
              ? {
                  ...m,
                  parts: [
                    ...m.parts,
                    { type: 'tool' as const, tool: { name: data.tool_name || 'unknown', status: 'running' as const } },
                  ],
                }
              : m
          )
        )
        break

      case 'tool_result':
        setMessages((prev) =>
          prev.map((m) => {
            if (m.id !== messageId) return m
            // Mark the most recent running tool with matching name as done
            const parts = [...m.parts]
            for (let i = parts.length - 1; i >= 0; i--) {
              const part = parts[i]
              if (part.type === 'tool' && part.tool?.name === data.tool_name && part.tool?.status === 'running') {
                parts[i] = { ...part, tool: { ...part.tool, status: 'done' } }
                break
              }
            }
            return { ...m, parts }
          })
        )
        break

      case 'error':
        setMessages((prev) =>
          prev.map((m) =>
            m.id === messageId
              ? { ...m, parts: [...m.parts, { type: 'text' as const, content: `\n\n*Error: ${data.error}*` }] }
              : m
          )
        )
        break

      case 'done':
        // Stream complete
        break
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  const handleSuggestionClick = (prompt: string) => {
    if (isStreaming) return
    setInput(prompt)
    // Submit after a brief delay to show the input
    setTimeout(() => {
      const form = document.querySelector('.input-area') as HTMLFormElement
      if (form) {
        form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }))
      }
    }, 50)
  }

  const handleResizeStart = (e: React.MouseEvent) => {
    e.preventDefault()
    resizeRef.current = { startY: e.clientY, startHeight: textareaHeight }

    const handleMouseMove = (moveEvent: MouseEvent) => {
      if (!resizeRef.current) return
      // Dragging up (negative delta) should increase height
      const delta = resizeRef.current.startY - moveEvent.clientY
      const newHeight = Math.max(44, Math.min(300, resizeRef.current.startHeight + delta))
      setTextareaHeight(newHeight)
    }

    const handleMouseUp = () => {
      resizeRef.current = null
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
    }

    document.addEventListener('mousemove', handleMouseMove)
    document.addEventListener('mouseup', handleMouseUp)
  }

  return (
    <div className="chat-interface">
      <div className="chat-header">
        <div className="chat-header-top">
          <h2 title={approachName || ''}>{truncate(approachName || 'Chat', 40)}</h2>
          <div className="header-buttons">
            {approachFolder && (
              <button
                className="new-chat-button"
                onClick={handleNewChat}
                disabled={isStreaming}
                title="Start a new conversation"
              >
                + New Chat
              </button>
            )}
          </div>
        </div>
        {approachFolder && conversations.length > 0 && (
          <div className="conversation-selector">
            <select
              value={selectedConversation}
              onChange={(e) => handleConversationChange(e.target.value)}
              disabled={isStreaming}
            >
              <option value="">New conversation</option>
              {conversations.map((conv) => (
                <option key={conv.filename} value={conv.filename}>
                  {formatConversationLabel(conv)}
                </option>
              ))}
            </select>
          </div>
        )}
        {!approachFolder && (
          <p className="hint">Select or create an approach to begin</p>
        )}
      </div>

      {approachFolder && (
        <AutoControls
          active={autoModeActive}
          paused={autoModePaused}
          turnCount={autoTurnCount}
          maxTurns={autoMaxTurns}
          onStart={onAutoStart || (() => {})}
          onPause={onAutoPause || (() => {})}
          onResume={onAutoResume || (() => {})}
          onStop={onAutoStop || (() => {})}
        />
      )}

      <div className="messages">
        {messages.length === 0 && approachFolder && (
          <div className="empty-chat">
            <p>Start a conversation to explore your hypothesis</p>
            <p className="or-divider">— or choose a suggested prompt —</p>
            <div className="suggestion-buttons">
              {suggestions.map((suggestion, index) => (
                <button
                  key={index}
                  className="suggestion-button"
                  onClick={() => handleSuggestionClick(suggestion.prompt)}
                  disabled={isStreaming}
                >
                  {suggestion.label}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((message) => (
          <div key={message.id} className={`message ${message.role}`}>
            {message.role === 'auto' && <span className="auto-label">Auto</span>}
            {message.role === 'system' && <span className="system-label">System</span>}
            <div className="message-content">
              {message.role === 'assistant' || message.role === 'auto' || message.role === 'system' ? (
                message.parts.length > 0 ? (
                  message.parts.map((part, index) => (
                    part.type === 'text' ? (
                      <ReactMarkdown key={index}>{part.content || ''}</ReactMarkdown>
                    ) : (
                      <div key={index} className={`tool-indicator inline ${part.tool?.status}`}>
                        {part.tool?.status === 'running' && <span className="spinner" />}
                        {part.tool?.name}
                      </div>
                    )
                  ))
                ) : (
                  isStreaming && '...'
                )
              ) : (
                message.parts[0]?.content || ''
              )}
            </div>
          </div>
        ))}

        <div ref={messagesEndRef} />
      </div>

      <form className="input-area" onSubmit={handleSubmit}>
        <div className="resize-handle" onMouseDown={handleResizeStart} title="Drag to resize" />
        <div className="input-row">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              approachFolder
                ? 'Ask about your hypothesis...'
                : 'Select an approach first'
            }
            disabled={!approachFolder || isStreaming}
            style={{ height: textareaHeight }}
          />
          <button
            type="submit"
            disabled={!approachFolder || !input.trim() || isStreaming}
          >
            {isStreaming ? '...' : 'Send'}
          </button>
        </div>
      </form>
    </div>
  )
}

export default ChatInterface
