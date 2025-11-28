import { useState, useRef, useEffect } from 'react'
import './ChatInterface.css'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  toolUse?: {
    name: string
    status: 'running' | 'done' | 'error'
  }
}

interface Props {
  approachFolder: string | null
  approachName: string | null
}

function ChatInterface({ approachFolder, approachName }: Props) {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const [currentTool, setCurrentTool] = useState<string | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Focus input when approach changes
  useEffect(() => {
    inputRef.current?.focus()
  }, [approachFolder])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || isStreaming) return

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input.trim(),
    }

    setMessages((prev) => [...prev, userMessage])
    setInput('')
    setIsStreaming(true)

    // Create assistant message placeholder
    const assistantMessageId = (Date.now() + 1).toString()
    setMessages((prev) => [
      ...prev,
      { id: assistantMessageId, role: 'assistant', content: '' },
    ])

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: userMessage.content,
          approach_name: approachFolder,
        }),
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
      console.error('Chat error:', error)
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantMessageId
            ? { ...m, content: m.content + '\n\n*Error: Failed to get response*' }
            : m
        )
      )
    } finally {
      setIsStreaming(false)
      setCurrentTool(null)
    }
  }

  const handleStreamEvent = (
    data: { type: string; text?: string; tool_name?: string; error?: string; full_response?: string },
    messageId: string
  ) => {
    switch (data.type) {
      case 'text':
        setMessages((prev) =>
          prev.map((m) =>
            m.id === messageId ? { ...m, content: m.content + (data.text || '') } : m
          )
        )
        break

      case 'tool_use':
        setCurrentTool(data.tool_name || null)
        setMessages((prev) =>
          prev.map((m) =>
            m.id === messageId
              ? { ...m, toolUse: { name: data.tool_name || 'unknown', status: 'running' } }
              : m
          )
        )
        break

      case 'tool_result':
        setCurrentTool(null)
        setMessages((prev) =>
          prev.map((m) =>
            m.id === messageId && m.toolUse
              ? { ...m, toolUse: { ...m.toolUse, status: 'done' } }
              : m
          )
        )
        break

      case 'error':
        setMessages((prev) =>
          prev.map((m) =>
            m.id === messageId
              ? { ...m, content: m.content + `\n\n*Error: ${data.error}*` }
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

  return (
    <div className="chat-interface">
      <div className="chat-header">
        <h2>{approachName || 'Chat'}</h2>
        {!approachFolder && (
          <p className="hint">Select or create an approach to begin</p>
        )}
      </div>

      <div className="messages">
        {messages.length === 0 && approachFolder && (
          <div className="empty-chat">
            <p>Start a conversation to explore your hypothesis.</p>
            <p className="suggestions">Try:</p>
            <ul>
              <li>"Break down this hypothesis into testable claims"</li>
              <li>"What simulations should we run?"</li>
              <li>"Search for prior work on this topic"</li>
            </ul>
          </div>
        )}

        {messages.map((message) => (
          <div key={message.id} className={`message ${message.role}`}>
            <div className="message-content">
              {message.content || (message.role === 'assistant' && isStreaming && '...')}
            </div>
            {message.toolUse && (
              <div className={`tool-indicator ${message.toolUse.status}`}>
                {message.toolUse.status === 'running' && (
                  <span className="spinner" />
                )}
                {message.toolUse.name}
              </div>
            )}
          </div>
        ))}

        {currentTool && (
          <div className="streaming-tool">
            <span className="spinner" />
            Running {currentTool}...
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <form className="input-area" onSubmit={handleSubmit}>
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
          rows={1}
        />
        <button
          type="submit"
          disabled={!approachFolder || !input.trim() || isStreaming}
        >
          {isStreaming ? '...' : 'Send'}
        </button>
      </form>
    </div>
  )
}

export default ChatInterface
