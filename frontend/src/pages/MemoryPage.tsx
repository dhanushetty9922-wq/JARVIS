import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Brain, Search, Trash2 } from 'lucide-react'
import { fetchMemories, deleteMemory } from '../services/api'
import { useJarvisStore } from '../stores/jarvisStore'

interface Memory {
  id?: string
  key?: string
  value?: string
  content?: string
  created_at?: string
  updated_at?: string
}

export function MemoryPage() {
  const { backendOnline } = useJarvisStore()
  const [memories, setMemories] = useState<Memory[]>([])
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const load = async () => {
    if (!backendOnline) return
    setLoading(true)
    try {
      const data = await fetchMemories()
      setMemories(data.memories || [])
      setError(null)
    } catch {
      setError('Failed to load memories.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [backendOnline])

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this memory?')) return
    try {
      await deleteMemory(id)
      setMemories(prev => prev.filter(m => (m.id ?? m.key) !== id))
    } catch {
      alert('Failed to delete memory.')
    }
  }

  const filtered = memories.filter(m => {
    const text = `${m.key ?? ''} ${m.value ?? m.content ?? ''}`.toLowerCase()
    return text.includes(search.toLowerCase())
  })

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16, height: '100%' }}>
      {/* Header */}
      <div className="card" style={{ padding: 16, display: 'flex', alignItems: 'center', gap: 10, flexShrink: 0 }}>
        <Brain size={20} color="var(--text-accent)" />
        <div style={{ flex: 1 }}>
          <div style={{ fontWeight: 700 }}>Long-Term Memory</div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>
            {memories.length} stored {memories.length === 1 ? 'memory' : 'memories'}
          </div>
        </div>
        <button className="btn btn-ghost btn-sm" onClick={load} disabled={loading}>
          Refresh
        </button>
      </div>

      {/* Search */}
      <div style={{ position: 'relative', flexShrink: 0 }}>
        <Search size={15} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-dim)', pointerEvents: 'none' }} />
        <input
          className="input"
          style={{ paddingLeft: 36 }}
          placeholder="Search memories…"
          value={search}
          onChange={e => setSearch(e.target.value)}
        />
      </div>

      {/* Memory list */}
      <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 8 }}>
        {!backendOnline && (
          <div style={{ textAlign: 'center', padding: 40, color: 'var(--text-dim)' }}>
            Connect backend to view memories.
          </div>
        )}
        {backendOnline && loading && (
          <div style={{ textAlign: 'center', padding: 40, color: 'var(--text-dim)' }}>Loading…</div>
        )}
        {backendOnline && error && (
          <div style={{ textAlign: 'center', padding: 40, color: 'var(--red-400)' }}>{error}</div>
        )}
        {backendOnline && !loading && filtered.length === 0 && (
          <div style={{ textAlign: 'center', padding: 40 }}>
            <Brain size={40} style={{ margin: '0 auto 12px', display: 'block', opacity: 0.2 }} />
            <div style={{ color: 'var(--text-dim)' }}>
              {search ? 'No memories match your search.' : 'No memories stored yet.'}
            </div>
          </div>
        )}

        <AnimatePresence>
          {filtered.map((mem, i) => {
            const id = mem.id ?? mem.key ?? String(i)
            const key = mem.key ?? `Memory #${i + 1}`
            const value = mem.value ?? mem.content ?? '(empty)'
            const date = mem.updated_at ?? mem.created_at
            return (
              <motion.div
                key={id}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, x: -20 }}
                transition={{ duration: 0.2, delay: i * 0.03 }}
                className="card"
                style={{ padding: '12px 14px', display: 'flex', alignItems: 'flex-start', gap: 10 }}
              >
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontWeight: 600, fontSize: '0.85rem', color: 'var(--text-accent)', marginBottom: 3 }}>
                    {key}
                  </div>
                  <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', wordBreak: 'break-word' }}>
                    {value}
                  </div>
                  {date && (
                    <div style={{ fontSize: '0.68rem', color: 'var(--text-dim)', marginTop: 4 }}>
                      {new Date(date).toLocaleString()}
                    </div>
                  )}
                </div>
                <button
                  className="btn btn-danger btn-sm btn-icon"
                  onClick={() => handleDelete(id)}
                  title="Delete memory"
                >
                  <Trash2 size={13} />
                </button>
              </motion.div>
            )
          })}
        </AnimatePresence>
      </div>

      {/* Footer note */}
      <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)', textAlign: 'center', flexShrink: 0 }}>
        Memories are stored locally in SQLite and never leave your device.
      </div>
    </div>
  )
}
