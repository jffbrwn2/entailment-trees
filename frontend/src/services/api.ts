/**
 * Centralized API service for all backend communication.
 * This reduces duplication of fetch calls across components.
 */

const API_BASE = '/api'

// Helper for JSON requests
async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, options)
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`)
  }
  return response.json()
}

async function postJson<T>(url: string, body?: unknown): Promise<T> {
  return fetchJson<T>(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  })
}

// Approach types
export interface Approach {
  name: string
  folder: string
  description: string
  last_updated: string
  num_claims: number
  num_implications: number
}

export interface CreateApproachResponse {
  success: boolean
  folder: string
}

// Settings types
export interface Settings {
  chatModel: string
  evaluatorModel: string
  autoModel: string
  edisonToolsEnabled: boolean
  gapMapToolsEnabled: boolean
}

// Auto mode types
export interface AutoModeStatus {
  active: boolean
  paused: boolean
  turn_count: number
  max_turns?: number
  model?: string
}

// Config status types
export interface ConfigStatus {
  anthropic_key_set: boolean
  openrouter_key_set: boolean
}

/**
 * API methods organized by domain
 */
export const api = {
  // Approaches
  approaches: {
    list: () => fetchJson<Approach[]>(`${API_BASE}/approaches`),

    create: (name: string, hypothesis: string) =>
      postJson<CreateApproachResponse>(`${API_BASE}/approaches`, { name, hypothesis }),

    load: (folder: string) =>
      postJson<unknown>(`${API_BASE}/approaches/${folder}/load`),

    getHypergraph: (folder: string) =>
      fetchJson<unknown>(`${API_BASE}/approaches/${folder}/hypergraph`),

    cleanup: (folder: string) =>
      postJson<{ success: boolean; removed_count: number }>(
        `${API_BASE}/approaches/${folder}/cleanup`
      ),

    deleteClaim: (folder: string, claimId: string) =>
      fetch(`${API_BASE}/approaches/${folder}/claims/${claimId}`, {
        method: 'DELETE',
      }),
  },

  // Conversations
  conversations: {
    list: (folder: string) =>
      fetchJson<unknown[]>(`${API_BASE}/approaches/${folder}/conversations`),

    get: (filename: string) =>
      fetchJson<unknown>(`${API_BASE}/conversations/${filename}`),

    newSession: (folder: string) =>
      postJson<unknown>(`${API_BASE}/approaches/${folder}/new-session`),

    resumeSession: (folder: string, conversationFilename: string) =>
      postJson<unknown>(`${API_BASE}/approaches/${folder}/resume-session`, {
        conversation_filename: conversationFilename,
      }),
  },

  // Settings
  settings: {
    get: () => fetchJson<Settings>(`${API_BASE}/settings`),

    update: (settings: Partial<Settings>) =>
      fetch(`${API_BASE}/settings`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings),
      }),
  },

  // Auto mode
  autoMode: {
    getStatus: (folder: string) =>
      fetchJson<AutoModeStatus>(`${API_BASE}/approaches/${folder}/auto/status`),

    start: (folder: string, model: string) =>
      postJson<{ max_turns: number }>(`${API_BASE}/approaches/${folder}/auto/start`, { model }),

    pause: (folder: string) =>
      postJson<unknown>(`${API_BASE}/approaches/${folder}/auto/pause`),

    resume: (folder: string) =>
      postJson<unknown>(`${API_BASE}/approaches/${folder}/auto/resume`),

    stop: (folder: string) =>
      postJson<unknown>(`${API_BASE}/approaches/${folder}/auto/stop`),
  },

  // Config
  config: {
    getStatus: () => fetchJson<ConfigStatus>(`${API_BASE}/config/status`),

    setKeys: (keys: { anthropic_key?: string; openrouter_key?: string }) =>
      postJson<unknown>(`${API_BASE}/config/keys`, keys),
  },

  // OpenRouter
  openRouter: {
    getModels: () => fetchJson<unknown[]>(`${API_BASE}/openrouter/models`),
  },

  // Chat (returns streaming response, not JSON)
  chat: {
    send: (message: string, approachName: string | null, signal?: AbortSignal) =>
      fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message, approach_name: approachName }),
        signal,
      }),
  },

  // Name generation
  generateName: (hypothesis: string) =>
    postJson<{ name: string }>(`${API_BASE}/generate-name`, { hypothesis }),
}

export default api
