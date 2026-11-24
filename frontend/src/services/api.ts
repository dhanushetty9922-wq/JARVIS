// JARVIS API Service — communicates with the FastAPI backend
import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 10000,
})

export interface JarvisStatus {
  version: string
  operating_mode: string
  safe_mode: string
  emergency_stopped: boolean
  voice_state: string
  voice_subsystem?: string
  is_muted?: boolean
  seconds_until_sleep?: number
  inactivity_timeout_seconds?: number
  wake_phrase: string
  microphone_permission: string
  internet_permission: string
  cloud_ai_permission: string
  memory_permission: string
  memory_subsystem: string
  ai_mode: string
  ai_provider: string
  ai_provider_available: string
  ai_active_provider?: string
  ai_primary_provider?: string
  ai_backup_provider?: string
  ai_fallback_active?: boolean
  ai_fallback_reason?: string
  gemini_status?: string
  openrouter_status?: string
  database_status: string
  registered_tools_count: number
  automation_subsystem: string
  system_cpu_percent: number
  system_ram_percent: number
  system_ram_used_gb: number
  system_ram_total_gb: number
  memory_usage: string
}

export interface CommandResponse {
  response: string
  success: boolean
}

export interface Message {
  role: 'user' | 'assistant'
  text: string
  timestamp?: string
}

export interface AuditEntry {
  timestamp: string
  action: string
  tool_name?: string
  permission?: string
  risk_level: string
  confirmation_status: string
  result: string
  error_details?: string
}

// Status & health
export const fetchStatus = () => api.get<JarvisStatus>('/status').then(r => r.data)
export const fetchHealth = () => api.get('/health').then(r => r.data)

// Commands
export const sendCommand = (command: string) =>
  api.post<CommandResponse>('/command', { command }).then(r => r.data)

// Voice
export const startVoice = () => api.post('/voice/start').then(r => r.data)
export const stopVoice = () => api.post('/voice/stop').then(r => r.data)
export const interruptVoice = () => api.post('/voice/interrupt').then(r => r.data)
export const muteVoice = () => api.post('/voice/mute').then(r => r.data)
export const unmuteVoice = () => api.post('/voice/unmute').then(r => r.data)
export const toggleMuteVoice = () => api.post('/voice/toggle-mute').then(r => r.data)
export const wakeVoice = () => api.post('/voice/wake').then(r => r.data)
export const sleepVoice = () => api.post('/voice/sleep').then(r => r.data)

// Security
export const triggerEmergencyStop = () => api.post('/security/emergency-stop').then(r => r.data)
export const resetEmergencyStop = () => api.post('/security/reset-emergency-stop').then(r => r.data)
export const enableSafeMode = () => api.post('/security/safe-mode/enable').then(r => r.data)
export const disableSafeMode = () => api.post('/security/safe-mode/disable').then(r => r.data)

// Permissions
export const fetchPermissions = () => api.get('/permissions').then(r => r.data)
export const updatePermission = (permission: string, state: 'allow' | 'block', reason?: string) =>
  api.post('/permissions/update', { permission, state, reason }).then(r => r.data)

// Memory
export const fetchMemories = () => api.get('/memory').then(r => r.data)
export const deleteMemory = (id: string) => api.delete(`/memory/${id}`).then(r => r.data)

// Conversations
export const fetchConversations = () => api.get('/conversations').then(r => r.data)

// Logs
export const fetchLogs = (limit = 50) =>
  api.get<{ logs: AuditEntry[] }>(`/logs?limit=${limit}`).then(r => r.data)

export default api
