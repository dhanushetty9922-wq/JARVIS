import { useState } from 'react'
import { motion } from 'framer-motion'
import { Monitor, Cpu, MemoryStick, Activity } from 'lucide-react'
import { useJarvisStore } from '../stores/jarvisStore'
import { sendCommand } from '../services/api'
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'

const SAFE_APPS = [
  { id: 'notepad', label: 'Notepad', cmd: 'open notepad', icon: '📝' },
  { id: 'calc', label: 'Calculator', cmd: 'open calculator', icon: '🔢' },
  { id: 'browser', label: 'Browser', cmd: 'open browser', icon: '🌐' },
  { id: 'explorer', label: 'File Explorer', cmd: 'open file explorer', icon: '📁' },
  { id: 'paint', label: 'Paint', cmd: 'open paint', icon: '🎨' },
  { id: 'cmd', label: 'Command Prompt', cmd: 'open command prompt', icon: '⌨️' },
]

const SAFE_INFO = [
  { label: 'System Status', cmd: 'system status' },
  { label: 'Current Time', cmd: 'what time is it' },
  { label: 'CPU Usage', cmd: 'cpu usage' },
  { label: 'RAM Usage', cmd: 'memory usage' },
  { label: 'IP Address', cmd: 'what is my ip' },
  { label: 'Disk Space', cmd: 'disk space' },
]

// fake sparkline data for demo
const mkData = () => Array.from({ length: 20 }, (_, i) => ({ t: i, v: 20 + Math.random() * 60 }))

export function SystemPage() {
  const { status, backendOnline, addMessage, setVoiceState } = useJarvisStore()
  const [result, setResult] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [cpuData] = useState(mkData())
  const [ramData] = useState(mkData())

  const run = async (cmd: string) => {
    if (!backendOnline) return
    setLoading(true)
    addMessage({ role: 'user', text: cmd })
    setVoiceState('PROCESSING')
    try {
      const res = await sendCommand(cmd)
      setResult(res.response)
      addMessage({ role: 'assistant', text: res.response })
    } catch {
      setResult('Error — backend unavailable.')
    } finally {
      setLoading(false)
      setVoiceState('SLEEPING')
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20, overflowY: 'auto', height: '100%' }}>
      {/* App launcher */}
      <div className="card" style={{ padding: 20 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
          <Monitor size={18} color="var(--text-accent)" />
          <span style={{ fontWeight: 700, fontSize: '0.95rem' }}>Application Launcher</span>
          <span className="badge badge-cyan" style={{ marginLeft: 'auto' }}>Allowlisted Apps</span>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(120px, 1fr))', gap: 10 }}>
          {SAFE_APPS.map(app => (
            <motion.button
              key={app.id}
              whileHover={{ scale: 1.04 }}
              whileTap={{ scale: 0.97 }}
              onClick={() => run(app.cmd)}
              disabled={!backendOnline || loading}
              style={{
                padding: '14px 10px',
                borderRadius: 'var(--radius-md)',
                background: 'var(--bg-tertiary)',
                border: '1px solid var(--border-default)',
                cursor: backendOnline ? 'pointer' : 'not-allowed',
                display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8,
                color: 'var(--text-primary)',
                fontFamily: 'inherit', fontSize: '0.82rem', fontWeight: 500,
                opacity: backendOnline ? 1 : 0.5,
                transition: 'all var(--transition-fast)',
              }}
            >
              <span style={{ fontSize: '1.5rem' }}>{app.icon}</span>
              {app.label}
            </motion.button>
          ))}
        </div>
      </div>

      {/* System charts */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
        <div className="card" style={{ padding: 16 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 12 }}>
            <Cpu size={15} color="var(--cyan-400)" />
            <span style={{ fontSize: '0.85rem', fontWeight: 600 }}>CPU Usage</span>
            {status && <span style={{ marginLeft: 'auto', fontSize: '0.9rem', fontWeight: 700, color: 'var(--cyan-400)' }}>{status.system_cpu_percent?.toFixed(0)}%</span>}
          </div>
          <ResponsiveContainer width="100%" height={80}>
            <AreaChart data={cpuData}>
              <defs>
                <linearGradient id="cpuGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#22d3ee" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#22d3ee" stopOpacity={0} />
                </linearGradient>
              </defs>
              <Area type="monotone" dataKey="v" stroke="#22d3ee" strokeWidth={1.5} fill="url(#cpuGrad)" dot={false} />
              <XAxis dataKey="t" hide />
              <YAxis domain={[0, 100]} hide />
              <Tooltip
                contentStyle={{ background: 'var(--bg-card)', border: '1px solid var(--border-default)', borderRadius: 8, fontSize: '0.75rem' }}
                formatter={(v: number) => [`${v.toFixed(0)}%`, 'CPU']}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        <div className="card" style={{ padding: 16 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 12 }}>
            <MemoryStick size={15} color="var(--blue-400)" />
            <span style={{ fontSize: '0.85rem', fontWeight: 600 }}>RAM Usage</span>
            {status && <span style={{ marginLeft: 'auto', fontSize: '0.9rem', fontWeight: 700, color: 'var(--blue-400)' }}>{status.system_ram_percent?.toFixed(0)}%</span>}
          </div>
          <ResponsiveContainer width="100%" height={80}>
            <AreaChart data={ramData}>
              <defs>
                <linearGradient id="ramGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#60a5fa" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#60a5fa" stopOpacity={0} />
                </linearGradient>
              </defs>
              <Area type="monotone" dataKey="v" stroke="#60a5fa" strokeWidth={1.5} fill="url(#ramGrad)" dot={false} />
              <XAxis dataKey="t" hide />
              <YAxis domain={[0, 100]} hide />
              <Tooltip
                contentStyle={{ background: 'var(--bg-card)', border: '1px solid var(--border-default)', borderRadius: 8, fontSize: '0.75rem' }}
                formatter={(v: number) => [`${v.toFixed(0)}%`, 'RAM']}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* System info queries */}
      <div className="card" style={{ padding: 20 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 14 }}>
          <Activity size={16} color="var(--text-accent)" />
          <span style={{ fontWeight: 700, fontSize: '0.95rem' }}>System Information</span>
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 14 }}>
          {SAFE_INFO.map(info => (
            <button
              key={info.cmd}
              className="btn btn-ghost btn-sm"
              onClick={() => run(info.cmd)}
              disabled={!backendOnline || loading}
            >
              {info.label}
            </button>
          ))}
        </div>

        {/* Result panel */}
        {result && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            style={{
              padding: '12px 14px',
              borderRadius: 'var(--radius-md)',
              background: 'var(--bg-tertiary)',
              border: '1px solid var(--border-default)',
              fontFamily: 'JetBrains Mono, monospace',
              fontSize: '0.82rem',
              color: 'var(--cyan-300)',
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
            }}
          >
            {result}
          </motion.div>
        )}
      </div>
    </div>
  )
}
