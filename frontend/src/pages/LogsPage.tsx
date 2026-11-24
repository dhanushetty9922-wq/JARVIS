import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { ScrollText, Search } from 'lucide-react'
import { fetchLogs } from '../services/api'
import { useJarvisStore } from '../stores/jarvisStore'
import type { AuditEntry } from '../services/api'

const LEVEL_STYLE: Record<string, { badge: string; dot: string }> = {
  LOW:      { badge: 'badge-cyan',  dot: 'var(--cyan-400)' },
  MEDIUM:   { badge: 'badge-blue',  dot: 'var(--blue-400)' },
  HIGH:     { badge: 'badge-amber', dot: 'var(--amber-400)' },
  CRITICAL: { badge: 'badge-red',   dot: 'var(--red-400)' },
}

export function LogsPage() {
  const { backendOnline } = useJarvisStore()
  const [logs, setLogs] = useState<AuditEntry[]>([])
  const [loading, setLoading] = useState(false)
  const [search, setSearch] = useState('')
  const [limitFilter, setLimitFilter] = useState<string>('all')

  const load = async (limit = 50) => {
    if (!backendOnline) return
    setLoading(true)
    try {
      const data = await fetchLogs(limit)
      setLogs(data.logs || [])
    } catch { /* ignore */ }
    finally { setLoading(false) }
  }

  useEffect(() => { load() }, [backendOnline])

  const filtered = logs.filter(log => {
    const text = `${log.action ?? ''} ${log.tool_name ?? ''} ${log.result ?? ''} ${log.risk_level ?? ''}`.toLowerCase()
    const matchSearch = text.includes(search.toLowerCase())
    const matchLevel = limitFilter === 'all' || log.risk_level === limitFilter
    return matchSearch && matchLevel
  })

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14, height: '100%' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexShrink: 0 }}>
        <ScrollText size={20} color="var(--text-accent)" />
        <div style={{ flex: 1 }}>
          <div style={{ fontWeight: 700 }}>Activity Logs</div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>{logs.length} events</div>
        </div>
        <button className="btn btn-ghost btn-sm" onClick={() => load(100)}>Load More</button>
        <button className="btn btn-ghost btn-sm" onClick={() => load()}>Refresh</button>
      </div>

      {/* Filters */}
      <div style={{ display: 'flex', gap: 8, flexShrink: 0, flexWrap: 'wrap' }}>
        <div style={{ position: 'relative', flex: 1, minWidth: 180 }}>
          <Search size={14} style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-dim)', pointerEvents: 'none' }} />
          <input className="input" style={{ paddingLeft: 32 }} placeholder="Search logs…" value={search} onChange={e => setSearch(e.target.value)} />
        </div>
        <div style={{ display: 'flex', gap: 4 }}>
          {['all', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'].map(lvl => (
            <button
              key={lvl}
              onClick={() => setLimitFilter(lvl)}
              className={`btn btn-sm ${limitFilter === lvl ? 'btn-primary' : 'btn-ghost'}`}
            >
              {lvl}
            </button>
          ))}
        </div>
      </div>

      {/* Log list */}
      <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 6 }}>
        {!backendOnline && (
          <div style={{ textAlign: 'center', padding: 40, color: 'var(--text-dim)' }}>Backend offline.</div>
        )}
        {loading && (
          <div style={{ textAlign: 'center', padding: 40, color: 'var(--text-dim)' }}>Loading logs…</div>
        )}
        {!loading && filtered.length === 0 && backendOnline && (
          <div style={{ textAlign: 'center', padding: 40, color: 'var(--text-dim)' }}>No log entries found.</div>
        )}
        {filtered.map((log, i) => {
          const risk = log.risk_level ?? 'LOW'
          const style = LEVEL_STYLE[risk] ?? LEVEL_STYLE.LOW
          const success = log.confirmation_status === 'CONFIRMED' || log.result?.startsWith('OK') || log.result?.toLowerCase().includes('success')
          return (
            <motion.div
              key={i}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: i * 0.015 }}
              style={{
                padding: '10px 14px',
                borderRadius: 'var(--radius-md)',
                background: 'var(--bg-card)',
                border: '1px solid var(--border-subtle)',
                display: 'grid',
                gridTemplateColumns: '120px 1fr auto',
                gap: 10,
                alignItems: 'start',
              }}
            >
              <div>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)', fontFamily: 'JetBrains Mono, monospace' }}>
                  {log.timestamp ? new Date(log.timestamp).toLocaleTimeString() : '—'}
                </div>
                <div style={{ fontSize: '0.65rem', color: 'var(--text-dim)' }}>
                  {log.timestamp ? new Date(log.timestamp).toLocaleDateString() : ''}
                </div>
              </div>
              <div>
                <div style={{ fontWeight: 600, fontSize: '0.82rem', marginBottom: 2 }}>
                  {log.action ?? log.tool_name ?? 'Unknown action'}
                </div>
                {log.tool_name && log.tool_name !== log.action && (
                  <div style={{ fontSize: '0.73rem', color: 'var(--text-dim)' }}>Tool: {log.tool_name}</div>
                )}
                <div style={{
                  fontSize: '0.73rem',
                  color: success ? 'var(--green-400)' : 'var(--red-400)',
                  marginTop: 2,
                  wordBreak: 'break-word',
                }}>
                  {log.result ?? '—'}
                </div>
                {log.error_details && (
                  <div style={{ fontSize: '0.7rem', color: 'var(--red-400)', marginTop: 2 }}>
                    ⚠ {log.error_details}
                  </div>
                )}
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 4, alignItems: 'flex-end' }}>
                <span className={`badge ${style.badge}`}>{risk}</span>
                {log.permission && (
                  <span className="badge badge-blue">{log.permission}</span>
                )}
              </div>
            </motion.div>
          )
        })}
      </div>
    </div>
  )
}
