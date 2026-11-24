import { Eye, Lock } from 'lucide-react'

export function VisionPage() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <Eye size={20} color="var(--text-accent)" />
        <div>
          <div style={{ fontWeight: 700 }}>Vision Module</div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>Optional — requires configuration</div>
        </div>
      </div>

      <div className="card" style={{ padding: 32, textAlign: 'center' }}>
        <div style={{
          width: 72, height: 72,
          borderRadius: '50%',
          background: 'var(--bg-tertiary)',
          border: '2px solid var(--border-default)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          margin: '0 auto 16px',
        }}>
          <Lock size={32} color="var(--text-dim)" />
        </div>
        <div style={{ fontWeight: 700, fontSize: '1.1rem', marginBottom: 8 }}>Vision Module Not Configured</div>
        <div style={{ fontSize: '0.85rem', color: 'var(--text-dim)', maxWidth: 400, margin: '0 auto', lineHeight: 1.7 }}>
          The vision module allows JARVIS to analyze screenshots and answer questions about your screen.
          It requires a configured vision-capable AI provider and explicit screen-capture permission.
        </div>

        <div style={{ marginTop: 24, display: 'flex', flexDirection: 'column', gap: 10, alignItems: 'center' }}>
          <div style={{
            padding: '10px 16px', borderRadius: 'var(--radius-md)',
            background: 'var(--bg-tertiary)', border: '1px solid var(--border-default)',
            fontSize: '0.82rem', color: 'var(--text-secondary)', maxWidth: 380,
          }}>
            📋 To enable: set <code style={{ color: 'var(--cyan-400)' }}>VISION_ENABLED=true</code> and
            configure a vision-capable AI provider in <code style={{ color: 'var(--cyan-400)' }}>.env</code>
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>
            Screenshots are never captured silently. Full user control at all times.
          </div>
        </div>
      </div>

      <div className="card" style={{ padding: 16 }}>
        <div style={{ fontWeight: 600, marginBottom: 10 }}>Capabilities (when enabled)</div>
        {[
          { icon: '📸', label: 'User-initiated screenshot', desc: 'Capture and analyze current screen' },
          { icon: '🔍', label: 'Image Q&A', desc: 'Ask questions about what JARVIS sees' },
          { icon: '📝', label: 'Screen OCR', desc: 'Extract text from screen content' },
          { icon: '🔒', label: 'Privacy controls', desc: 'Explicit permission required per session' },
        ].map(item => (
          <div key={item.label} style={{
            display: 'flex', alignItems: 'center', gap: 12,
            padding: '8px 0', borderBottom: '1px solid var(--border-subtle)',
            opacity: 0.5,
          }}>
            <span style={{ fontSize: '1.1rem' }}>{item.icon}</span>
            <div>
              <div style={{ fontSize: '0.83rem', fontWeight: 500 }}>{item.label}</div>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)' }}>{item.desc}</div>
            </div>
            <span className="badge badge-amber" style={{ marginLeft: 'auto' }}>UNAVAILABLE</span>
          </div>
        ))}
      </div>
    </div>
  )
}
