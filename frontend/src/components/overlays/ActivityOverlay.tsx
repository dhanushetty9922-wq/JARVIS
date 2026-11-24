import { useEffect, useState } from 'react'
import { OverlayWrapper } from './OverlayWrapper'
import { fetchLogs, type AuditEntry } from '../../services/api'
import { useJarvisStore } from '../../stores/jarvisStore'

interface ActivityOverlayProps {
  onClose: () => void
}

export function ActivityOverlay({ onClose }: ActivityOverlayProps) {
  const { backendOnline } = useJarvisStore()
  const [logs, setLogs] = useState<AuditEntry[]>([])
  const [loading, setLoading] = useState(false)
  const [search, setSearch] = useState('')
  const [riskFilter, setRiskFilter] = useState('ALL')

  const load = async () => {
    if (!backendOnline) return
    setLoading(true)
    try {
      const data = await fetchLogs(60)
      setLogs(data.logs || [])
    } catch {
      // ignore
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [backendOnline])

  const filtered = logs.filter((log) => {
    const text = `${log.action ?? ''} ${log.tool_name ?? ''} ${log.result ?? ''}`.toLowerCase()
    const matchesSearch = text.includes(search.toLowerCase())
    const matchesRisk = riskFilter === 'ALL' || log.risk_level?.toUpperCase() === riskFilter
    return matchesSearch && matchesRisk
  })

  return (
    <OverlayWrapper
      title="AUDIT TELEMETRY STREAM"
      subtitle="IMMUTABLE SECURITY EVENT JOURNAL"
      icon="receipt_long"
      onClose={onClose}
    >
      <div className="flex items-center gap-2">
        <div className="relative flex-1">
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Filter audit logs..."
            className="w-full bg-surface-container/70 border border-primary/20 rounded-lg px-3 py-2 text-on-surface text-body-sm focus:outline-none focus:border-primary-container font-mono text-[12px]"
          />
          <span className="material-symbols-outlined text-[18px] text-on-surface-variant absolute right-3 top-2.5">
            filter_list
          </span>
        </div>
        <div className="flex items-center gap-1 bg-surface-container p-1 rounded-lg border border-white/5 font-label-caps text-[10px]">
          {['ALL', 'LOW', 'MEDIUM', 'HIGH'].map((level) => (
            <button
              key={level}
              onClick={() => setRiskFilter(level)}
              className={`px-2 py-1 rounded transition-colors ${
                riskFilter === level
                  ? 'bg-primary-container text-on-primary-container font-semibold'
                  : 'text-on-surface-variant hover:text-on-surface'
              }`}
            >
              {level}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="py-12 text-center text-primary-container font-mono text-[12px] animate-pulse">
          FETCHING AUDIT JOURNAL...
        </div>
      ) : filtered.length === 0 ? (
        <div className="py-12 text-center text-on-surface-variant text-body-sm">
          No audit entries recorded for the current filter.
        </div>
      ) : (
        <div className="flex flex-col gap-2">
          {filtered.map((log, i) => (
            <div
              key={i}
              className="p-3 rounded-lg bg-surface-container/60 border border-white/5 hover:border-primary/20 flex flex-col gap-1 transition-all"
            >
              <div className="flex items-center justify-between text-[11px] font-mono">
                <span className="text-primary-container font-semibold">{log.action}</span>
                <span className="text-on-surface-variant">
                  {log.timestamp ? new Date(log.timestamp).toLocaleTimeString() : 'RECENT'}
                </span>
              </div>
              <div className="font-body-sm text-[12px] text-on-surface">
                {log.tool_name ? `Tool: ${log.tool_name} — ` : ''}
                {log.result}
              </div>
              <div className="flex items-center gap-2 mt-1">
                <span
                  className={`font-label-caps text-[9px] px-1.5 py-0.5 rounded border ${
                    log.risk_level === 'CRITICAL' || log.risk_level === 'HIGH'
                      ? 'bg-error/20 text-error border-error/40'
                      : 'bg-primary-container/10 text-primary-container border-primary-container/30'
                  }`}
                >
                  RISK: {log.risk_level ?? 'LOW'}
                </span>
                <span className="font-mono text-[9px] text-on-surface-variant">
                  STATUS: {log.confirmation_status ?? 'VERIFIED'}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </OverlayWrapper>
  )
}
