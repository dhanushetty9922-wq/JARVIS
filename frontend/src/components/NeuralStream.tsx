import { useState, useRef, useEffect } from 'react'
import { useJarvisStore } from '../stores/jarvisStore'
import { sendCommand, startVoice, stopVoice, interruptVoice, wakeVoice, unmuteVoice } from '../services/api'

interface NeuralStreamProps {
  onStopVoice?: () => void
  onToggleVoice?: () => void
  onVisionClick?: () => void
}

export function NeuralStream({ onStopVoice, onToggleVoice, onVisionClick }: NeuralStreamProps) {
  const {
    messages,
    addMessage,
    clearMessages,
    voiceState,
    setVoiceState,
    backendOnline,
    safeMode,
  } = useJarvisStore()

  const [input, setInput] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom of conversation
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages, voiceState])

  const handleSend = async () => {
    const text = input.trim()
    if (!text || submitting || !backendOnline) return

    setInput('')
    setSubmitting(true)
    addMessage({ role: 'user', text })
    setVoiceState('PROCESSING')

    try {
      const res = await sendCommand(text)
      addMessage({ role: 'assistant', text: res.response })
    } catch {
      addMessage({ role: 'assistant', text: 'Error communicating with JARVIS neural brain.' })
    } finally {
      setSubmitting(false)
      setVoiceState('AWAKE')
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      handleSend()
    }
  }

  const handleMicToggle = async () => {
    if (onToggleVoice) {
      onToggleVoice()
      return
    }
    try {
      if (voiceState === 'MIC_DISABLED') {
        await unmuteVoice()
      } else if (voiceState === 'LISTENING' || voiceState === 'SPEAKING') {
        await stopVoice()
        setVoiceState('AWAKE')
      } else if (voiceState === 'SLEEP' || voiceState === 'SLEEPING') {
        await wakeVoice()
        setVoiceState('AWAKE')
      } else {
        await startVoice()
        setVoiceState('LISTENING')
      }
    } catch {
      // ignore
    }
  }

  const handleInterrupt = async () => {
    if (onStopVoice) {
      onStopVoice()
      return
    }
    try {
      await interruptVoice()
      setVoiceState('AWAKE')
    } catch {
      // ignore
    }
  }

  const handleExportStream = () => {
    const text = messages.map(m => `[${m.role.toUpperCase()}] ${m.timestamp ?? ''}\n${m.text}\n`).join('\n---\n\n')
    const blob = new Blob([text], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `jarvis-neural-stream-${Date.now()}.txt`
    a.click()
    URL.revokeObjectURL(url)
  }

  const isSpeaking = voiceState === 'SPEAKING'
  const isListening = voiceState === 'LISTENING'

  return (
    <div className="w-full bg-surface-container-low/80 backdrop-blur-2xl border border-primary/20 rounded-2xl p-space-md lg:p-space-lg flex flex-col gap-space-md shadow-2xl shadow-surface-container-lowest">
      {/* Terminal Panel Header */}
      <div className="flex items-center justify-between pb-space-xs border-b border-white/5">
        <div className="flex items-center gap-space-sm">
          <div className="w-2.5 h-2.5 rounded-full bg-primary-container shadow-[0_0_10px_#00f0ff] animate-pulse"></div>
          <span className="font-headline-sm text-headline-sm text-primary tracking-wide">NEURAL STREAM</span>
          <span className="font-label-caps text-[11px] text-on-surface-variant font-mono">// SESSION_ID: #JARVIS-4092</span>
        </div>
        <div className="flex items-center gap-space-xs">
          <button
            onClick={handleExportStream}
            className="w-8 h-8 rounded flex items-center justify-center text-on-surface-variant hover:bg-surface-container hover:text-on-surface transition-colors"
            title="Export Stream"
          >
            <span className="material-symbols-outlined text-[18px]">download</span>
          </button>
          <button
            onClick={clearMessages}
            className="w-8 h-8 rounded flex items-center justify-center text-on-surface-variant hover:bg-surface-container hover:text-on-surface transition-colors"
            title="Clear Buffer"
          >
            <span className="material-symbols-outlined text-[18px]">delete_sweep</span>
          </button>
        </div>
      </div>

      {/* Dialog Exchange Stream */}
      <div ref={scrollRef} className="flex flex-col gap-space-md overflow-y-auto max-h-[320px] lg:max-h-[360px] pr-2 scrollbar-thin">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-center text-on-surface-variant/70 gap-2">
            <span className="material-symbols-outlined text-[36px] text-primary/40">smart_toy</span>
            <div className="font-headline-sm text-[13px] text-primary/70">NEURAL STREAM INITIALIZED</div>
            <div className="font-body-sm text-[12px] max-w-sm">
              All neural pathways synced. Transmit command via keyboard, click microphone, or speak wake phrase <span className="text-primary-container font-mono">"Jarvis"</span>.
            </div>
          </div>
        ) : (
          messages.map((msg, idx) => (
            <div key={idx} className="w-full">
              {msg.role === 'user' ? (
                /* User Prompt Message Box */
                <div className="flex flex-col items-end gap-1">
                  <div className="flex items-center gap-space-xs font-label-caps text-[10px] text-on-surface-variant">
                    <span>USER_COMMAND</span>
                    <span>•</span>
                    <span className="font-mono">
                      {msg.timestamp ? new Date(msg.timestamp).toLocaleTimeString() : 'NOW'}
                    </span>
                  </div>
                  <div className="max-w-[85%] rounded-xl rounded-tr-none bg-surface-container p-space-md shadow-md text-on-surface font-body-md text-body-md border border-white/5">
                    {msg.text}
                  </div>
                </div>
              ) : (
                /* JARVIS Response Message Box */
                <div className="flex flex-col items-start gap-1">
                  <div className="flex items-center gap-space-xs font-label-caps text-[10px] text-primary-container">
                    <span className="w-1.5 h-1.5 rounded-full bg-primary-container animate-pulse"></span>
                    <span className="tracking-wider">JARVIS_SYNTHESIS</span>
                    <span>•</span>
                    <span className="font-mono text-on-surface-variant">
                      {msg.timestamp ? new Date(msg.timestamp).toLocaleTimeString() : 'NOW'}
                    </span>
                  </div>
                  <div className="max-w-[92%] rounded-xl rounded-tl-none bg-surface-container-high/90 border border-primary/20 p-space-md shadow-lg flex flex-col gap-space-sm text-on-surface">
                    <p className="font-body-md text-body-md leading-relaxed text-tertiary whitespace-pre-wrap">
                      {msg.text}
                    </p>

                    {/* Embedded Micro Action Telemetry Card */}
                    <div className="p-space-sm rounded bg-surface-container-lowest/80 border border-white/5 flex flex-wrap items-center justify-between gap-space-sm">
                      <div className="flex items-center gap-space-sm">
                        <span className="material-symbols-outlined text-primary-container text-[18px]">bolt</span>
                        <div className="flex flex-col">
                          <span className="font-label-caps text-[10px] text-primary">
                            EXECUTION DISPATCH: COMPLETE
                          </span>
                          <span className="font-telemetry-unit text-[10px] text-on-surface-variant">
                            Neural Pipeline Verified • Zero-Trust Guard {safeMode ? 'Active' : 'Bypassed'}
                          </span>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="px-2 py-0.5 rounded bg-primary-container/10 text-primary-container font-mono text-[11px] font-semibold border border-primary-container/30">
                          PASS
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          ))
        )}

        {/* Live Speaking Dynamic Audio Waveform Ribbon */}
        {isSpeaking && (
          <div className="p-space-sm rounded-xl bg-surface-container-high/90 border border-primary-container/50 shadow-[0_0_20px_rgba(0,240,255,0.2)] flex items-center justify-between gap-space-sm">
            <div className="flex items-center gap-space-sm flex-1">
              <span className="material-symbols-outlined text-primary-container text-[20px] animate-pulse">graphic_eq</span>
              {/* Dynamic Soundwave Array */}
              <div className="flex items-center gap-1 h-5 flex-1 max-w-xs">
                <span className="w-1 h-3 bg-primary-container rounded-none animate-pulse"></span>
                <span className="w-1 h-5 bg-primary rounded-none animate-pulse" style={{ animationDelay: '100ms' }}></span>
                <span className="w-1 h-2 bg-secondary rounded-none animate-pulse" style={{ animationDelay: '250ms' }}></span>
                <span className="w-1 h-4 bg-primary-container rounded-none animate-pulse" style={{ animationDelay: '75ms' }}></span>
                <span className="w-1 h-5 bg-primary rounded-none animate-pulse" style={{ animationDelay: '180ms' }}></span>
                <span className="w-1 h-3 bg-secondary rounded-none animate-pulse" style={{ animationDelay: '300ms' }}></span>
                <span className="w-1 h-2 bg-primary-container rounded-none animate-pulse" style={{ animationDelay: '120ms' }}></span>
                <span className="w-1 h-4 bg-primary rounded-none animate-pulse" style={{ animationDelay: '220ms' }}></span>
                <span className="w-1 h-5 bg-primary-container rounded-none animate-pulse" style={{ animationDelay: '160ms' }}></span>
              </div>
              <span className="font-telemetry-unit text-telemetry-unit text-primary-container font-mono">
                SYNTHESIS STREAMING
              </span>
            </div>
            {/* Stop Speaking Hotkey Trigger */}
            <button
              onClick={handleInterrupt}
              className="flex items-center gap-1.5 px-space-sm py-1 rounded bg-error-container/40 hover:bg-error-container/70 text-on-error-container transition-all group font-label-caps text-[10px] border border-error/50"
              title="Interrupt speech (Hotkey: Esc)"
            >
              <span className="w-2.5 h-2.5 rounded-sm bg-error group-hover:scale-110 transition-transform"></span>
              <span>STOP</span>
              <kbd className="px-1 rounded bg-surface-container-lowest font-mono text-[9px] text-on-surface-variant">ESC</kbd>
            </button>
          </div>
        )}
      </div>

      {/* Prompt Input Capsule & Multimodal Triggers */}
      <div className="mt-space-xs pt-space-xs flex flex-col gap-2">
        <div className="relative flex items-center bg-surface-container-lowest/90 rounded-xl p-1.5 border border-primary/30 shadow-inner focus-within:border-primary focus-within:shadow-[0_0_20px_rgba(0,240,255,0.25)] transition-all">
          {/* Microphone Continuous Listening Button */}
          <button
            onClick={handleMicToggle}
            className={`w-10 h-10 rounded-lg flex items-center justify-center transition-all group relative ${
              isListening
                ? 'bg-primary-container text-on-primary-container shadow-[0_0_16px_#00f0ff]'
                : voiceState === 'MIC_DISABLED'
                ? 'bg-amber-500/20 text-amber-400 border border-amber-500/40'
                : 'bg-primary-container/15 hover:bg-primary-container/25 text-primary-container'
            }`}
            id="mic-trigger"
            title={
              voiceState === 'MIC_DISABLED'
                ? 'Microphone muted (Click to unmute)'
                : voiceState === 'SLEEP' || voiceState === 'SLEEPING'
                ? 'Sleep mode (Say "Jarvis" or click to wake)'
                : 'Toggle voice listening (Hotkey: Ctrl+Space)'
            }
          >
            <span className="material-symbols-outlined text-[20px] group-hover:scale-110 transition-transform">
              {voiceState === 'MIC_DISABLED'
                ? 'mic_off'
                : isListening
                ? 'mic'
                : voiceState === 'SLEEP' || voiceState === 'SLEEPING'
                ? 'mic_none'
                : 'mic'}
            </span>
            {isListening && (
              <span className="absolute -top-0.5 -right-0.5 w-2.5 h-2.5 rounded-full bg-primary-container animate-ping"></span>
            )}
          </button>

          {/* Text Input Area */}
          <input
            className="flex-1 bg-transparent px-space-md text-on-surface placeholder:text-on-surface-variant/60 font-body-md text-body-md focus:outline-none"
            id="jarvis-prompt"
            placeholder="Ask JARVIS anything or trigger routine [Ctrl + Space]..."
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={submitting || !backendOnline}
          />

          {/* Auxiliary Multimodal Tools */}
          <div className="flex items-center gap-1 px-1">
            <button
              onClick={onVisionClick}
              className="w-9 h-9 rounded flex items-center justify-center text-on-surface-variant hover:text-primary hover:bg-surface-container transition-colors"
              title="Attach Vision Stream"
            >
              <span className="material-symbols-outlined text-[19px]">add_photo_alternate</span>
            </button>
            <button
              onClick={handleMicToggle}
              className="w-9 h-9 rounded flex items-center justify-center text-on-surface-variant hover:text-secondary hover:bg-surface-container transition-colors"
              title="Continuous Audio Stream"
            >
              <span className="material-symbols-outlined text-[19px]">graphic_eq</span>
            </button>
            {/* Send Action Button */}
            <button
              onClick={handleSend}
              disabled={!input.trim() || submitting || !backendOnline}
              className="w-10 h-10 rounded-lg bg-primary-container text-on-primary-container flex items-center justify-center hover:opacity-90 disabled:opacity-40 transition-opacity shadow-[0_0_12px_rgba(0,240,255,0.4)]"
              id="send-btn"
            >
              <span className="material-symbols-outlined text-[20px] font-bold">arrow_forward</span>
            </button>
          </div>
        </div>

        {/* Hotkey & Context Stamp Hint Line */}
        <div className="flex items-center justify-between px-space-xs font-telemetry-unit text-telemetry-unit text-on-surface-variant/70">
          <div className="flex items-center gap-space-md">
            <span>[Enter] Transmit query</span>
            <span>[Ctrl+Space] Voice toggle</span>
            <span>[Esc] Interrupt voice</span>
          </div>
          <div className="flex items-center gap-1 text-primary-container">
            <span className="w-1.5 h-1.5 rounded-full bg-primary-container animate-pulse"></span>
            <span>MODAL: MULTI-THREADED AGENT</span>
          </div>
        </div>
      </div>
    </div>
  )
}
