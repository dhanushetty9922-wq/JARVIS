import { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Send, Trash2, MessageCircle, Loader2 } from 'lucide-react'
import { useJarvisStore } from '../stores/jarvisStore'
import { sendCommand } from '../services/api'

export function ConversationPage() {
  const { messages, addMessage, clearMessages, backendOnline, voiceState, setVoiceState } = useJarvisStore()
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSend = async () => {
    const cmd = input.trim()
    if (!cmd || loading || !backendOnline) return
    setInput('')
    addMessage({ role: 'user', text: cmd })
    setLoading(true)
    setVoiceState('PROCESSING')
    try {
      const res = await sendCommand(cmd)
      addMessage({ role: 'assistant', text: res.response })
    } catch {
      addMessage({ role: 'assistant', text: '⚠ Backend error — command could not be processed.' })
    } finally {
      setLoading(false)
      setVoiceState('SLEEPING')
    }
  }

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', gap: 0 }}>
      {/* Header */}
      <div style={{
        padding: '14px 20px',
        borderBottom: '1px solid var(--border-subtle)',
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        flexShrink: 0,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <MessageCircle size={20} color="var(--text-accent)" />
          <div>
            <div style={{ fontWeight: 700, fontSize: '1rem' }}>AI Chat</div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>
              {messages.length} message{messages.length !== 1 ? 's' : ''}
            </div>
          </div>
        </div>
        <button
          className="btn btn-ghost btn-sm"
          onClick={clearMessages}
          disabled={messages.length === 0}
        >
          <Trash2 size={14} /> Clear
        </button>
      </div>

      {/* Messages area */}
      <div style={{
        flex: 1, overflowY: 'auto', padding: '20px',
        display: 'flex', flexDirection: 'column', gap: 14,
      }}>
        {messages.length === 0 && (
          <div style={{ textAlign: 'center', marginTop: '20%', color: 'var(--text-dim)' }}>
            <MessageCircle size={48} style={{ margin: '0 auto 16px', display: 'block', opacity: 0.2 }} />
            <div style={{ fontSize: '1rem', fontWeight: 500 }}>Start a conversation</div>
            <div style={{ fontSize: '0.8rem', marginTop: 8 }}>
              {backendOnline ? 'Type a command or question below.' : 'Connect the backend to start chatting.'}
            </div>
          </div>
        )}

        <AnimatePresence initial={false}>
          {messages.map((msg, i) => {
            const isUser = msg.role === 'user'
            return (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 12, scale: 0.97 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                transition={{ duration: 0.22 }}
                style={{
                  display: 'flex',
                  justifyContent: isUser ? 'flex-end' : 'flex-start',
                  alignItems: 'flex-end',
                  gap: 8,
                }}
              >
                {!isUser && (
                  <div style={{
                    width: 28, height: 28, borderRadius: '50%',
                    background: 'linear-gradient(135deg, var(--cyan-500), var(--blue-500))',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    flexShrink: 0, fontSize: '0.6rem', fontWeight: 700, color: '#fff',
                  }}>J</div>
                )}
                <div style={{
                  maxWidth: '72%',
                  padding: '11px 16px',
                  borderRadius: isUser ? '18px 18px 4px 18px' : '18px 18px 18px 4px',
                  background: isUser
                    ? 'linear-gradient(135deg, var(--cyan-600) 0%, var(--blue-500) 100%)'
                    : 'var(--bg-card)',
                  border: `1px solid ${isUser ? 'transparent' : 'var(--border-subtle)'}`,
                  boxShadow: isUser ? '0 2px 12px rgba(6,182,212,0.25)' : 'var(--shadow-card)',
                  color: isUser ? '#fff' : 'var(--text-primary)',
                  fontSize: '0.9rem',
                  lineHeight: 1.6,
                  whiteSpace: 'pre-wrap',
                }}>
                  {msg.text}
                  <div style={{ fontSize: '0.65rem', marginTop: 4, opacity: 0.6, textAlign: 'right' }}>
                    {msg.timestamp ? new Date(msg.timestamp).toLocaleTimeString() : ''}
                  </div>
                </div>
              </motion.div>
            )
          })}
        </AnimatePresence>

        {loading && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            style={{ display: 'flex', alignItems: 'center', gap: 8 }}
          >
            <div style={{
              width: 28, height: 28, borderRadius: '50%',
              background: 'linear-gradient(135deg, var(--cyan-500), var(--blue-500))',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>J</div>
            <div style={{
              padding: '11px 16px',
              borderRadius: '18px 18px 18px 4px',
              background: 'var(--bg-card)',
              border: '1px solid var(--border-subtle)',
              display: 'flex', alignItems: 'center', gap: 6,
            }}>
              <Loader2 size={14} style={{ animation: 'spin 1s linear infinite' }} color="var(--text-accent)" />
              <span style={{ fontSize: '0.85rem', color: 'var(--text-dim)' }}>Thinking…</span>
            </div>
          </motion.div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input bar */}
      <div style={{
        padding: '14px 20px',
        borderTop: '1px solid var(--border-subtle)',
        background: 'var(--bg-secondary)',
        flexShrink: 0,
      }}>
        <div style={{ display: 'flex', gap: 10 }}>
          <input
            className="input"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && !e.shiftKey && handleSend()}
            placeholder={
              !backendOnline ? 'Backend offline…'
              : voiceState === 'PROCESSING' ? 'Processing…'
              : 'Message JARVIS…'
            }
            disabled={!backendOnline || loading}
            style={{ flex: 1 }}
          />
          <button
            className="btn btn-primary"
            onClick={handleSend}
            disabled={!input.trim() || loading || !backendOnline}
            style={{ flexShrink: 0 }}
          >
            {loading ? <Loader2 size={16} style={{ animation: 'spin 1s linear infinite' }} /> : <Send size={16} />}
          </button>
        </div>
        <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      </div>
    </div>
  )
}
