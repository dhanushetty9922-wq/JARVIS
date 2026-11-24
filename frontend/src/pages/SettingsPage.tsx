import { Server, Palette, Volume2, KeyRound, Info } from 'lucide-react'
import { useJarvisStore } from '../stores/jarvisStore'

interface SettingsPageProps {
  theme: 'dark' | 'light'
  onThemeToggle: () => void
}

export function SettingsPage({ theme, onThemeToggle }: SettingsPageProps) {
  const { status, backendOnline } = useJarvisStore()

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20, overflowY: 'auto', height: '100%' }}>
      {/* Appearance */}
      <Section icon={<Palette size={18} />} title="Appearance">
        <SettingsRow label="Theme" description="Choose interface color scheme">
          <div style={{ display: 'flex', gap: 6 }}>
            {(['dark', 'light'] as const).map(t => (
              <button
                key={t}
                className={`btn btn-sm ${theme === t ? 'btn-primary' : 'btn-ghost'}`}
                onClick={() => t !== theme && onThemeToggle()}
              >
                {t === 'dark' ? '🌙 Dark' : '☀️ Light'}
              </button>
            ))}
          </div>
        </SettingsRow>
      </Section>

      {/* Backend */}
      <Section icon={<Server size={18} />} title="Backend Connection">
        <SettingsRow label="Status" description="API server at 127.0.0.1:8765">
          <span className={`badge ${backendOnline ? 'badge-green' : 'badge-red'}`}>
            {backendOnline ? 'CONNECTED' : 'OFFLINE'}
          </span>
        </SettingsRow>
        {status && (
          <>
            <SettingsRow label="Version" description="JARVIS backend version">
              <span style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>{status.version}</span>
            </SettingsRow>
            <SettingsRow label="Operating Mode" description="Current runtime mode">
              <span className="badge badge-cyan">{status.operating_mode?.toUpperCase()}</span>
            </SettingsRow>
            <SettingsRow label="AI Provider" description="Currently configured AI backend">
              <span style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>{status.ai_provider}</span>
            </SettingsRow>
          </>
        )}
        <div style={{
          marginTop: 8, padding: '10px 12px',
          borderRadius: 'var(--radius-sm)',
          background: 'var(--bg-tertiary)',
          fontSize: '0.77rem', color: 'var(--text-dim)',
          fontFamily: 'JetBrains Mono, monospace',
        }}>
          Start backend: python -m uvicorn api.server:app --host 127.0.0.1 --port 8765
        </div>
      </Section>

      {/* AI configuration */}
      <Section icon={<KeyRound size={18} />} title="AI Configuration">
        <SettingsRow label="API Keys" description="Set keys in .env file (never in the frontend)">
          <span className="badge badge-amber">BACKEND ONLY</span>
        </SettingsRow>
        <div style={{
          padding: '10px 12px',
          borderRadius: 'var(--radius-sm)',
          background: 'var(--bg-tertiary)',
          fontSize: '0.77rem', color: 'var(--text-dim)', lineHeight: 1.7,
        }}>
          Edit <code style={{ color: 'var(--cyan-400)' }}>.env</code> in the project root to configure AI providers.<br />
          Set <code style={{ color: 'var(--cyan-400)' }}>GEMINI_API_KEY</code> for primary Google Gemini AI.<br />
          Set <code style={{ color: 'var(--cyan-400)' }}>OPENROUTER_API_KEY</code> for automatic cloud backup fallback.<br />
          Local fallback: point <code style={{ color: 'var(--cyan-400)' }}>LOCAL_MODEL_ENDPOINT</code> to your Ollama instance.
        </div>
      </Section>

      {/* Voice */}
      <Section icon={<Volume2 size={18} />} title="Voice Configuration">
        <SettingsRow label="Wake Phrase" description="Phrase to wake JARVIS (configured in .env)">
          <span style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', fontFamily: 'JetBrains Mono, monospace' }}>
            {status?.wake_phrase ?? 'Jzt Jarvis'}
          </span>
        </SettingsRow>
        <SettingsRow label="Voice Subsystem" description="Speech recognition + TTS engine">
          <span className="badge badge-cyan">{status?.voice_subsystem ?? 'READY'}</span>
        </SettingsRow>
      </Section>

      {/* About */}
      <Section icon={<Info size={18} />} title="About">
        <div style={{ fontSize: '0.82rem', color: 'var(--text-dim)', lineHeight: 1.8 }}>
          <strong style={{ color: 'var(--text-primary)' }}>JARVIS</strong> — Personal AI Computer Assistant<br />
          Version: <span style={{ color: 'var(--text-accent)' }}>{status?.version ?? '1.0.0'}</span><br />
          Architecture: React + FastAPI + SQLite<br />
          Privacy: Local-first · Zero-trust · No secret telemetry
        </div>
      </Section>
    </div>
  )
}

function Section({ icon, title, children }: { icon: React.ReactNode; title: string; children: React.ReactNode }) {
  return (
    <div className="card" style={{ padding: 20 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
        <span style={{ color: 'var(--text-accent)' }}>{icon}</span>
        <span style={{ fontWeight: 700, fontSize: '0.95rem' }}>{title}</span>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {children}
      </div>
    </div>
  )
}

function SettingsRow({ label, description, children }: { label: string; description: string; children: React.ReactNode }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '8px 0', borderBottom: '1px solid var(--border-subtle)' }}>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: '0.85rem', fontWeight: 500 }}>{label}</div>
        <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)' }}>{description}</div>
      </div>
      {children}
    </div>
  )
}
