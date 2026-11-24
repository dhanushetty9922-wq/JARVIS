import { useEffect, useState } from 'react'
import { OverlayWrapper } from './OverlayWrapper'
import { fetchMemories, deleteMemory } from '../../services/api'
import { useJarvisStore } from '../../stores/jarvisStore'

interface MemoryOverlayProps {
  onClose: () => void
}

interface MemoryItem {
  id?: string
  key?: string
  value?: string
  content?: string
  created_at?: string
}

export function MemoryOverlay({ onClose }: MemoryOverlayProps) {
  const { backendOnline } = useJarvisStore()
  const [memories, setMemories] = useState<MemoryItem[]>([])
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
      setError('Could not retrieve vector memories.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [backendOnline])

  const handleDelete = async (id: string) => {
    if (!confirm('Purge this memory from the vector database?')) return
    try {
      await deleteMemory(id)
      setMemories((prev) => prev.filter((m) => (m.id ?? m.key) !== id))
    } catch {
      alert('Failed to delete memory.')
    }
  }

  const filtered = memories.filter((m) => {
    const text = `${m.key ?? ''} ${m.value ?? m.content ?? ''}`.toLowerCase()
    return text.includes(search.toLowerCase())
  })

  return (
    <OverlayWrapper
      title="VECTOR MEMORY CORE"
      subtitle="PERSISTENT CONTEXT & USER KNOWLEDGE GRAPH"
      icon="neurology"
      onClose={onClose}
    >
      <div className="flex items-center gap-2">
        <div className="relative flex-1">
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search memory embeddings..."
            className="w-full bg-surface-container/70 border border-primary/20 rounded-lg px-3 py-2 text-on-surface text-body-sm focus:outline-none focus:border-primary-container font-mono text-[12px]"
          />
          <span className="material-symbols-outlined text-[18px] text-on-surface-variant absolute right-3 top-2.5">
            search
          </span>
        </div>
        <button
          onClick={load}
          className="px-3 py-2 rounded-lg bg-surface-container hover:bg-surface-container-high text-primary-container border border-primary/20 font-label-caps text-[11px]"
        >
          SYNC
        </button>
      </div>

      {loading ? (
        <div className="py-12 text-center text-primary-container font-mono text-[12px] animate-pulse">
          SCANNING EMBEDDINGS...
        </div>
      ) : error ? (
        <div className="py-8 text-center text-error font-mono text-[12px]">{error}</div>
      ) : filtered.length === 0 ? (
        <div className="py-12 text-center text-on-surface-variant text-body-sm">
          No memory entries found matching query.
        </div>
      ) : (
        <div className="flex flex-col gap-2.5">
          {filtered.map((item, i) => {
            const memoryId = item.id ?? item.key ?? String(i)
            return (
              <div
                key={memoryId}
                className="p-3 rounded-xl bg-surface-container/60 border border-white/5 hover:border-primary/30 transition-all flex items-start justify-between gap-3"
              >
                <div className="min-w-0 flex-1">
                  <div className="font-label-caps text-[11px] text-primary-container font-semibold truncate">
                    {item.key ?? 'RECALL_NODE'}
                  </div>
                  <div className="font-body-sm text-[12px] text-on-surface mt-1 whitespace-pre-wrap">
                    {item.value ?? item.content}
                  </div>
                  {item.created_at && (
                    <div className="font-mono text-[9px] text-on-surface-variant mt-1.5">
                      INDEXED: {new Date(item.created_at).toLocaleString()}
                    </div>
                  )}
                </div>
                <button
                  onClick={() => handleDelete(memoryId)}
                  className="w-7 h-7 rounded flex items-center justify-center text-on-surface-variant hover:text-error hover:bg-error/20 transition-all"
                  title="Purge Memory"
                >
                  <span className="material-symbols-outlined text-[16px]">delete</span>
                </button>
              </div>
            )
          })}
        </div>
      )}
    </OverlayWrapper>
  )
}
