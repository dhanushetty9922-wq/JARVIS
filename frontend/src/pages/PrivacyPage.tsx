import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { ShieldAlert, AlertOctagon, ShieldCheck, ShieldOff } from 'lucide-react'
import { fetchPermissions, updatePermission, triggerEmergencyStop, resetEmergencyStop, enableSafeMode, disableSafeMode } from '../services/api'
import { useJarvisStore } from '../stores/jarvisStore'

const PERM_META: Record<string, { label: string; description: string; icon: string }> = {
  microphone:  { label: 'Microphone',     description: 'Record audio for voice commands',         icon: '🎤' },
  internet:    { label: 'Internet',        description: 'Allow network requests',                   icon: '🌐' },
  files:       { label: 'File Access',     description: 'Read/write approved directories',          icon: '📁' },
  screen:      { label: 'Screen Capture',  description: 'Capture screenshots for vision analysis', icon: '🖥️' },
  pc_control:  { label: 'PC Control',      description: 'Launch apps and control system',           icon: '⌨️' },
  automation:  { label: 'Automation',      description: 'Run automated tasks in background',        icon: '⚡' },
  cloud_ai:    { label: 'Cloud AI',        description: 'Send messages to cloud AI providers',      icon: '☁️' },
  web_access:  { label: 'Web Access',      description: 'Open URLs and fetch web content',          icon: '🔗' },
  memory:      { label: 'Memory',          description: 'Store and retrieve persistent memories',   icon: '🧠' },
}

export function PrivacyPage() {
  const { backendOnline, emergencyStopped, safeMode, setEmergencyStopped, setSafeMode, setVoiceState } = useJarvisStore()
  const [permissions, setPermissions] = useState<Record<string, string>>({})
  const [loading, setLoading] = useState(false)
  const [updating, setUpdating] = useState<string | null>(null)

  const load = async () => {
    if (!backendOnline) return
    setLoading(true)
    try {
      const data = await fetchPermissions()
      setPermissions(data.permissions ?? {})
    } catch { /* ignore */ }
    finally { setLoading(false) }
  }

  useEffect(() => { load() }, [backendOnline])

  const handleToggle = async (perm: string, current: string) => {
    const newState = current === 'ALLOWED' ? 'block' : 'allow'
    setUpdating(perm)
    try {
      await updatePermission(perm, newState as 'allow' | 'block', `Toggled from Privacy UI`)
      setPermissions(prev => ({ ...prev, [perm]: newState === 'allow' ? 'ALLOWED' : 'BLOCKED' }))
    } catch { /* ignore */ }
    finally { setUpdating(null) }
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
    } catch { /* ignore */ }
  }

  const handleSafeMode = async () => {
    try {
      if (safeMode) {
        if (!confirm('Disable safe mode? Sensitive actions will require less confirmation.')) return
        await disableSafeMode()
        setSafeMode(false)
      } else {
        await enableSafeMode()
        setSafeMode(true)
      }
    } catch { /* ignore */ }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20, overflowY: 'auto', height: '100%' }}>
      {/* Security controls */}
      <div className="card" style={{ padding: 20 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
          <AlertOctagon size={18} color="var(--red-400)" />
          <span style={{ fontWeight: 700, fontSize: '0.95rem' }}>Security Controls</span>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
          {/* Emergency Stop */}
          <motion.div
            animate={emergencyStopped ? { borderColor: ['rgba(239,68,68,0.5)', 'rgba(239,68,68,0.2)', 'rgba(239,68,68,0.5)'] } : {}}
            transition={{ duration: 1.2, repeat: Infinity }}
            style={{
              padding: 16,
              borderRadius: 'var(--radius-md)',
              border: `2px solid ${emergencyStopped ? 'rgba(239,68,68,0.5)' : 'var(--border-default)'}`,
              background: emergencyStopped ? 'rgba(239,68,68,0.08)' : 'var(--bg-tertiary)',
              display: 'flex', flexDirection: 'column', gap: 10,
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <AlertOctagon size={16} color={emergencyStopped ? 'var(--red-400)' : 'var(--text-secondary)'} />
              <span style={{ fontWeight: 600, fontSize: '0.87rem' }}>Emergency Stop</span>
              {emergencyStopped && <span className="badge badge-red">ACTIVE</span>}
            </div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>
              Immediately halts all listening, automation, and active operations.
            </div>
            <button
              className={`btn ${emergencyStopped ? 'btn-ghost' : 'btn-danger'} btn-sm`}
              onClick={handleEmergencyStop}
              disabled={!backendOnline}
            >
              {emergencyStopped ? '↺ Reset Emergency Stop' : '⛔ Trigger Emergency Stop'}
            </button>
          </motion.div>

          {/* Safe Mode */}
          <div style={{
            padding: 16,
            borderRadius: 'var(--radius-md)',
            border: `2px solid ${safeMode ? 'rgba(34,197,94,0.3)' : 'rgba(245,158,11,0.3)'}`,
            background: safeMode ? 'rgba(34,197,94,0.06)' : 'rgba(245,158,11,0.06)',
            display: 'flex', flexDirection: 'column', gap: 10,
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              {safeMode ? <ShieldCheck size={16} color="var(--green-400)" /> : <ShieldOff size={16} color="var(--amber-400)" />}
              <span style={{ fontWeight: 600, fontSize: '0.87rem' }}>Safe Mode</span>
              <span className={`badge ${safeMode ? 'badge-green' : 'badge-amber'}`}>
                {safeMode ? 'ENABLED' : 'DISABLED'}
              </span>
            </div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>
              Blocks sensitive actions. Recommended to keep enabled at all times.
            </div>
            <button
              className={`btn btn-sm ${safeMode ? 'btn-ghost' : 'btn-primary'}`}
              onClick={handleSafeMode}
              disabled={!backendOnline}
            >
              {safeMode ? 'Disable Safe Mode' : 'Enable Safe Mode'}
            </button>
          </div>
        </div>
      </div>

      {/* Permissions */}
      <div className="card" style={{ padding: 20 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
          <ShieldAlert size={18} color="var(--text-accent)" />
          <span style={{ fontWeight: 700, fontSize: '0.95rem' }}>Permission Manager</span>
        </div>
        <p style={{ fontSize: '0.8rem', color: 'var(--text-dim)', marginBottom: 16 }}>
          All permissions are enforced by the backend. Toggling here sends a verified request.
        </p>

        {loading && <div style={{ textAlign: 'center', padding: 20, color: 'var(--text-dim)' }}>Loading permissions…</div>}

        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {Object.entries(PERM_META).map(([key, meta]) => {
            const state = permissions[key] ?? 'BLOCKED'
            const isAllowed = state === 'ALLOWED'
            const isUpdating = updating === key
            return (
              <motion.div
                key={key}
                layout
                style={{
                  padding: '12px 14px',
                  borderRadius: 'var(--radius-md)',
                  border: `1px solid ${isAllowed ? 'rgba(34,197,94,0.2)' : 'var(--border-subtle)'}`,
                  background: isAllowed ? 'rgba(34,197,94,0.04)' : 'var(--bg-tertiary)',
                  display: 'flex', alignItems: 'center', gap: 12,
                }}
              >
                <span style={{ fontSize: '1.2rem', flexShrink: 0 }}>{meta.icon}</span>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontWeight: 600, fontSize: '0.85rem' }}>{meta.label}</div>
                  <div style={{ fontSize: '0.73rem', color: 'var(--text-dim)' }}>{meta.description}</div>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0 }}>
                  <span className={`badge ${isAllowed ? 'badge-green' : 'badge-red'}`}>
                    {isAllowed ? 'ALLOWED' : 'BLOCKED'}
                  </span>
                  <button
                    onClick={() => handleToggle(key, state)}
                    disabled={!backendOnline || isUpdating}
                    style={{
                      width: 36, height: 20,
                      borderRadius: 'var(--radius-full)',
                      border: 'none',
                      background: isAllowed ? 'var(--green-500)' : 'var(--bg-secondary)',
                      cursor: backendOnline ? 'pointer' : 'not-allowed',
                      position: 'relative',
                      transition: 'background var(--transition-base)',
                      borderStyle: 'solid',
                      borderWidth: 1,
                      borderColor: isAllowed ? 'var(--green-400)' : 'var(--border-default)',
                    }}
                  >
                    <motion.div
                      animate={{ x: isAllowed ? 16 : 2 }}
                      transition={{ type: 'spring', stiffness: 300, damping: 25 }}
                      style={{
                        position: 'absolute',
                        top: 2, left: 0,
                        width: 14, height: 14,
                        borderRadius: '50%',
                        background: '#fff',
                      }}
                    />
                  </button>
                </div>
              </motion.div>
            )
          })}
        </div>
      </div>

      {/* Privacy note */}
      <div style={{
        padding: '12px 14px',
        borderRadius: 'var(--radius-md)',
        background: 'rgba(56,189,248,0.04)',
        border: '1px solid var(--border-subtle)',
        fontSize: '0.78rem',
        color: 'var(--text-dim)',
        lineHeight: 1.6,
      }}>
        🔒 <strong style={{ color: 'var(--text-secondary)' }}>Privacy guarantee:</strong> JARVIS never records audio secretly,
        never transmits private files, and enforces all permissions server-side. The frontend cannot bypass backend validation.
      </div>
    </div>
  )
}
