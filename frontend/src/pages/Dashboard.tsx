import { useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { JarvisCore } from '../components/JarvisCore'
import { Waveform } from '../components/Waveform'
import { useJarvisStore } from '../stores/jarvisStore'
import {
  Mic, MicOff, AlertOctagon, ShieldCheck, ShieldOff,
  Cpu, MemoryStick, Activity, Brain, ChevronRight
} from 'lucide-react'
import {
  startVoice, stopVoice, fetchStatus,
  triggerEmergencyStop, resetEmergencyStop,
  enableSafeMode, disableSafeMode, sendCommand
} from '../services/api'

export function Dashboard() {
  const {
    status, voiceState, emergencyStopped, safeMode,
    backendOnline, messages, addMessage, setVoiceState,
    setEmergencyStopped, setSafeMode, setStatus,
  } = useJarvisStore()

  const inputRef = useRef<HTMLInputElement>(null)

  const handleVoiceToggle = async () => {
    try {
      if (voiceState === 'LISTENING') {
        await stopVoice()
        setVoiceState('SLEEPING')
      } else {
        await startVoice()
        setVoiceState('LISTENING')
      }
    } catch { /* backend offline */ }
  }

  const handleEmergencyStop = async () => {
    try {
      if (emergencyStopped) {
        await resetEmergencyStop()
        setEmergencyStopped(false)
      } else {
        await triggerEmergencyStop()
        setEmergencyStopped(true)
        setVoiceState('SLEEPING')
      }
    } catch { /* offline */ }
  }

  const handleSafeMode = async () => {
    try {
      if (safeMode) {
        await disableSafeMode()
        setSafeMode(false)
      } else {
        await enableSafeMode()
        setSafeMode(true)
      }
    } catch { /* offline */ }
  }

  const handleSend = async (cmd: string) => {
    if (!cmd.trim() || !backendOnline) return
    addMessage({ role: 'user', text: cmd })
    setVoiceState('PROCESSING')
    try {
      const res = await sendCommand(cmd)
      addMessage({ role: 'assistant', text: res.response })
    } catch (e) {
      addMessage({ role: 'assistant', text: 'Backend error — could not process command.' })
    } finally {
      setVoiceState('SLEEPING')
    }
  }

  // Refresh status
  useEffect(() => {
    if (!backendOnline) return
    const refresh = async () => {
      try {
        const s = await fetchStatus()
        setStatus(s)
      } catch { /* ignore */ }
    }
    refresh()
    const interval = setInterval(refresh, 10000)
    return () => clearInterval(interval)
  }, [backendOnline, setStatus])

  const quickCommands = [
    'open notepad', 'open calculator', 'open browser',
    'system status', 'what time is it', 'help',
  ]

  return (
    <div style={{ display: 'flex', gap: 20, height: '100%', overflow: 'hidden' }}>
      {/* ── Left column ── */}
      <div style={{ flex: '0 0 280px', display: 'flex', flexDirection: 'column', gap: 16, overflowY: 'auto', paddingRight: 4 }}>

        {/* Core panel */}
        <div className="card-accent" style={{ padding: 24, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 20 }}>
          <JarvisCore state={voiceState} size={160} />
          <div style={{ width: '100%', height: 40, marginTop: 8 }}>
            <Waveform state={voiceState} bars={24} />
          </div>

          {/* Controls */}
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', justifyContent: 'center' }}>
            <button
              className={`btn ${voiceState === 'LISTENING' ? 'btn-primary' : 'btn-ghost'}`}
              onClick={handleVoiceToggle}
              disabled={!backendOnline}
              title={voiceState === 'LISTENING' ? 'Stop Listening' : 'Start Listening'}
            >
              {voiceState === 'LISTENING' ? <MicOff size={15} /> : <Mic size={15} />}
              {voiceState === 'LISTENING' ? 'Stop' : 'Listen'}
            </button>

            <button
              className={`btn ${emergencyStopped ? 'btn-ghost' : 'btn-danger'} btn-sm`}
              onClick={handleEmergencyStop}
              title="Emergency Stop"
            >
              <AlertOctagon size={13} />
              {emergencyStopped ? 'Reset' : 'E-Stop'}
            </button>

            <button
              className="btn btn-ghost btn-sm"
              onClick={handleSafeMode}
              disabled={!backendOnline}
              title="Toggle Safe Mode"
            >
              {safeMode ? <ShieldCheck size={13} color="var(--green-400)" /> : <ShieldOff size={13} color="var(--amber-400)" />}
              {safeMode ? 'Safe' : 'Unsafe'}
            </button>
          </div>
        </div>

        {/* System metrics */}
        {status && (
          <div className="card" style={{ padding: 16 }}>
            <div className="label-sm" style={{ marginBottom: 12 }}>System Metrics</div>
            <MetricBar label="CPU" value={status.system_cpu_percent} color="var(--cyan-400)" icon={<Cpu size={13} />} />
            <MetricBar label="RAM" value={status.system_ram_percent} color="var(--blue-400)" icon={<MemoryStick size={13} />}
              detail={`${status.system_ram_used_gb}/${status.system_ram_total_gb} GB`} />
          </div>
        )}

        {/* Quick status */}
        {status && (
          <div className="card" style={{ padding: 16 }}>
            <div className="label-sm" style={{ marginBottom: 12 }}>Dual AI Providers</div>
            <StatusRow label="Active Provider" value={status.ai_active_provider ? status.ai_active_provider.toUpperCase() : status.ai_provider} color="var(--cyan-400)" />
            <StatusRow label="Primary (Gemini)" value={status.gemini_status ? status.gemini_status : 'READY'} color={status.gemini_status === 'CONFIGURED' ? 'var(--green-400)' : 'var(--text-secondary)'} />
            <StatusRow label="Backup (OpenRouter)" value={status.openrouter_status ? status.openrouter_status : 'STANDBY'} color={status.openrouter_status === 'CONFIGURED' ? 'var(--green-400)' : 'var(--text-secondary)'} />
            <StatusRow label="Fallback State" value={status.ai_fallback_active ? 'ACTIVE' : 'STANDBY'} color={status.ai_fallback_active ? 'var(--amber-400)' : 'var(--text-dim)'} />
            <StatusRow label="AI Status" value={status.ai_provider_available} color={status.ai_provider_available === 'ONLINE' || status.ai_provider_available === 'AVAILABLE' ? 'var(--green-400)' : 'var(--amber-400)'} />
            <StatusRow label="Database" value={status.database_status} />
            <StatusRow label="Tools" value={String(status.registered_tools_count)} />
            <StatusRow label="Memory" value={status.memory_subsystem} />
          </div>
        )}
      </div>

      {/* ── Right column ── */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 16, overflowY: 'auto' }}>

        {/* Fallback Notification Banner */}
        {status?.ai_fallback_active && (
          <div style={{
            padding: '10px 14px',
            borderRadius: 'var(--radius-md)',
            background: 'rgba(245, 158, 11, 0.12)',
            border: '1px solid var(--amber-500)',
            color: 'var(--amber-400)',
            fontSize: '0.8rem',
            display: 'flex',
            alignItems: 'center',
            gap: 10,
          }}>
            <AlertOctagon size={16} color="var(--amber-400)" style={{ flexShrink: 0 }} />
            <span>
              <strong>Automatic Fallback Active:</strong> Currently routing requests through backup provider (<strong>{status.ai_backup_provider?.toUpperCase() || 'OPENROUTER'}</strong>). {status.ai_fallback_reason ? `Reason: ${status.ai_fallback_reason}` : ''}
            </span>
          </div>
        )}

        {/* Conversation panel */}
        <div className="card" style={{ flex: 1, minHeight: 300, display: 'flex', flexDirection: 'column' }}>
          <div style={{ padding: '14px 16px', borderBottom: '1px solid var(--border-subtle)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <Activity size={16} color="var(--text-accent)" />
              <span style={{ fontWeight: 600, fontSize: '0.9rem' }}>Live Conversation</span>
            </div>
            {messages.length > 0 && (
              <span className="badge badge-cyan">{messages.length} msgs</span>
            )}
          </div>

          {/* Messages */}
          <div style={{ flex: 1, overflowY: 'auto', padding: 16, display: 'flex', flexDirection: 'column', gap: 10 }}>
            {messages.length === 0 && (
              <div style={{ textAlign: 'center', color: 'var(--text-dim)', marginTop: 40 }}>
                <Brain size={32} style={{ margin: '0 auto 12px', display: 'block', opacity: 0.3 }} />
                <div style={{ fontSize: '0.85rem' }}>Awaiting your command, sir.</div>
              </div>
            )}
            <AnimatePresence>
              {messages.map((msg, i) => (
                <ChatBubble key={i} role={msg.role} text={msg.text} timestamp={msg.timestamp} />
              ))}
            </AnimatePresence>
          </div>

          {/* Input */}
          <div style={{ padding: 12, borderTop: '1px solid var(--border-subtle)' }}>
            <form
              onSubmit={e => {
                e.preventDefault()
                const val = inputRef.current?.value.trim()
                if (val) {
                  handleSend(val)
                  if (inputRef.current) inputRef.current.value = ''
                }
              }}
              style={{ display: 'flex', gap: 8 }}
            >
              <input
                ref={inputRef}
                className="input"
                placeholder={backendOnline ? 'Enter command or question…' : 'Backend offline — connect to use'}
                disabled={!backendOnline || voiceState === 'PROCESSING'}
              />
              <button
                type="submit"
                className="btn btn-primary"
                disabled={!backendOnline || voiceState === 'PROCESSING'}
              >
                Send
              </button>
            </form>
          </div>
        </div>

        {/* Quick commands */}
        <div className="card" style={{ padding: 16 }}>
          <div className="label-sm" style={{ marginBottom: 10 }}>Quick Commands</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {quickCommands.map(cmd => (
              <button
                key={cmd}
                className="btn btn-ghost btn-sm"
                onClick={() => handleSend(cmd)}
                disabled={!backendOnline}
                style={{ display: 'flex', alignItems: 'center', gap: 4 }}
              >
                <ChevronRight size={12} />
                {cmd}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

// ── Sub-components ───────────────────────────────

function MetricBar({ label, value, color, icon, detail }: {
  label: string; value: number; color: string; icon: React.ReactNode; detail?: string
}) {
  const clamped = Math.min(100, Math.max(0, value || 0))
  return (
    <div style={{ marginBottom: 12 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
        <span style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
          {icon}{label}
        </span>
        <span style={{ fontSize: '0.75rem', color }}>
          {detail ?? `${clamped.toFixed(0)}%`}
        </span>
      </div>
      <div style={{ height: 4, borderRadius: 2, background: 'var(--bg-tertiary)', overflow: 'hidden' }}>
        <motion.div
          style={{ height: '100%', borderRadius: 2, background: color }}
          initial={{ width: 0 }}
          animate={{ width: `${clamped}%` }}
          transition={{ duration: 0.6, ease: 'easeOut' }}
        />
      </div>
    </div>
  )
}

function StatusRow({ label, value, color }: { label: string; value?: string; color?: string }) {
  return (
    <div style={{
      display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      padding: '5px 0', borderBottom: '1px solid var(--border-subtle)',
    }}>
      <span style={{ fontSize: '0.78rem', color: 'var(--text-dim)' }}>{label}</span>
      <span style={{ fontSize: '0.78rem', fontWeight: 600, color: color ?? 'var(--text-secondary)' }}>
        {value ?? '—'}
      </span>
    </div>
  )
}

function ChatBubble({ role, text, timestamp }: { role: string; text: string; timestamp?: string }) {
  const isUser = role === 'user'
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.2 }}
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: isUser ? 'flex-end' : 'flex-start',
      }}
    >
      <div style={{
        maxWidth: '80%',
        padding: '9px 13px',
        borderRadius: isUser ? '12px 12px 4px 12px' : '12px 12px 12px 4px',
        background: isUser
          ? 'linear-gradient(135deg, var(--cyan-600), var(--blue-500))'
          : 'var(--bg-tertiary)',
        border: `1px solid ${isUser ? 'transparent' : 'var(--border-subtle)'}`,
        fontSize: '0.875rem',
        lineHeight: 1.55,
        color: isUser ? '#fff' : 'var(--text-primary)',
      }}>
        {text}
      </div>
      {timestamp && (
        <div style={{ fontSize: '0.65rem', color: 'var(--text-dim)', marginTop: 3 }}>
          {new Date(timestamp).toLocaleTimeString()}
        </div>
      )}
    </motion.div>
  )
}
