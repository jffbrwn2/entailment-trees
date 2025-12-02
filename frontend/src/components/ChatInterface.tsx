import { useState, useRef, useEffect } from 'react'
import './ChatInterface.css'

interface ToolUse {
  name: string
  status: 'running' | 'done' | 'error'
}

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  toolUses: ToolUse[]
}

interface Props {
  approachFolder: string | null
  approachName: string | null
}

function ChatInterface({ approachFolder, approachName }: Props) {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Clear messages and optionally load history when approach changes
  useEffect(() => {
    // Clear current messages
    setMessages([])
    inputRef.current?.focus()

    // If we have an approach, try to load the most recent conversation
    if (approachFolder) {
      loadRecentConversation(approachFolder)
    }
  }, [approachFolder])

  const loadRecentConversation = async (folder: string) => {
    try {
      // Get list of conversations for this approach
      const response = await fetch(`/api/approaches/${folder}/conversations`)
      if (!response.ok) return

      const conversations = await response.json()
      if (conversations.length === 0) return

      // Load the most recent conversation
      const mostRecent = conversations[0]
      const logResponse = await fetch(`/api/conversations/${mostRecent.filename}`)
      if (!logResponse.ok) return

      const log = await logResponse.json()

      // Convert turns to messages format
      const loadedMessages: Message[] = []
      for (const turn of log.turns) {
        // Add user message
        loadedMessages.push({
          id: `${turn.turn_number}-user`,
          role: 'user',
          content: turn.user_input,
          toolUses: [],
        })
        // Add assistant message with tool uses
        loadedMessages.push({
          id: `${turn.turn_number}-assistant`,
          role: 'assistant',
          content: turn.claude_response,
          toolUses: turn.tools_used.map((t: { tool_name: string }) => ({
            name: t.tool_name,
            status: 'done' as const,
          })),
        })
      }

      setMessages(loadedMessages)
    } catch (error) {
      console.error('Failed to load conversation history:', error)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || isStreaming) return

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input.trim(),
      toolUses: [],
    }

    setMessages((prev) => [...prev, userMessage])
    setInput('')
    setIsStreaming(true)

    // Create assistant message placeholder
    const assistantMessageId = (Date.now() + 1).toString()
    setMessages((prev) => [
      ...prev,
      { id: assistantMessageId, role: 'assistant', content: '', toolUses: [] },
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
      // Mark any running tools as done when stream ends
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantMessageId
            ? {
                ...m,
                toolUses: m.toolUses.map((t) =>
                  t.status === 'running' ? { ...t, status: 'done' as const } : t
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
          prev.map((m) =>
            m.id === messageId ? { ...m, content: m.content + (data.text || '') } : m
          )
        )
        break

      case 'tool_use':
        setMessages((prev) =>
          prev.map((m) =>
            m.id === messageId
              ? {
                  ...m,
                  toolUses: [
                    ...m.toolUses,
                    { name: data.tool_name || 'unknown', status: 'running' as const },
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
            const toolUses = [...m.toolUses]
            for (let i = toolUses.length - 1; i >= 0; i--) {
              if (toolUses[i].name === data.tool_name && toolUses[i].status === 'running') {
                toolUses[i] = { ...toolUses[i], status: 'done' }
                break
              }
            }
            return { ...m, toolUses }
          })
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
              <li>"Generate the first level of the entailment tree"</li>
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
            {message.toolUses.length > 0 && (
              <div className="tool-indicators">
                {message.toolUses.map((tool, index) => (
                  <div key={index} className={`tool-indicator ${tool.status}`}>
                    {tool.status === 'running' && <span className="spinner" />}
                    {tool.name}
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}

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
