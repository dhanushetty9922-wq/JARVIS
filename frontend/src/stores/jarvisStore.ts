// JARVIS Global State Store (Zustand)
import { create } from 'zustand'
import type { JarvisStatus, Message } from '../services/api'

export type VoiceState =
  | 'INITIALIZING'
  | 'AWAKE'
  | 'SLEEP'
  | 'LISTENING'
  | 'THINKING'
  | 'SPEAKING'
  | 'EXECUTING'
  | 'MIC_DISABLED'
  | 'ERROR'
  | 'SLEEPING'
  | 'PROCESSING'

interface JarvisStore {
  // Connection
  connected: boolean
  backendOnline: boolean

  // Status
  status: JarvisStatus | null
  voiceState: VoiceState
  isMuted: boolean
  emergencyStopped: boolean
  safeMode: boolean

  // Conversation
  messages: Message[]
  currentInput: string

  // UI
  activePanel: 'home' | 'conversation' | 'system' | 'automation' | 'memory' | 'privacy' | 'security' | 'logs' | 'vision' | 'settings'
  
  // Permission badges
  permissions: Record<string, string>

  // Actions
  setConnected: (connected: boolean) => void
  setBackendOnline: (online: boolean) => void
  setStatus: (status: JarvisStatus) => void
  setVoiceState: (state: VoiceState) => void
  setIsMuted: (isMuted: boolean) => void
  setEmergencyStopped: (stopped: boolean) => void
  setSafeMode: (safe: boolean) => void
  addMessage: (msg: Message) => void
  clearMessages: () => void
  setCurrentInput: (input: string) => void
  setActivePanel: (panel: JarvisStore['activePanel']) => void
  setPermissions: (permissions: Record<string, string>) => void
}

export const useJarvisStore = create<JarvisStore>((set) => ({
  connected: false,
  backendOnline: false,
  status: null,
  voiceState: 'SLEEP',
  isMuted: false,
  emergencyStopped: false,
  safeMode: true,
  messages: [],
  currentInput: '',
  activePanel: 'home',
  permissions: {},

  setConnected: (connected) => set({ connected }),
  setBackendOnline: (backendOnline) => set({ backendOnline }),
  setStatus: (status) => set({
    status,
    voiceState: (status.voice_state || 'SLEEP') as VoiceState,
    isMuted: Boolean(status.is_muted),
    emergencyStopped: status.emergency_stopped,
    safeMode: status.safe_mode === 'ENABLED',
  }),
  setVoiceState: (voiceState) => set({ voiceState }),
  setIsMuted: (isMuted) => set({ isMuted }),
  setEmergencyStopped: (emergencyStopped) => set({ emergencyStopped }),
  setSafeMode: (safeMode) => set({ safeMode }),
  addMessage: (msg) => set((state) => ({
    messages: [...state.messages, { ...msg, timestamp: new Date().toISOString() }]
  })),
  clearMessages: () => set({ messages: [] }),
  setCurrentInput: (currentInput) => set({ currentInput }),
  setActivePanel: (activePanel) => set({ activePanel }),
  setPermissions: (permissions) => set({ permissions }),
}))
