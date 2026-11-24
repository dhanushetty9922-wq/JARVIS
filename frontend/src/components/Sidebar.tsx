import { motion } from 'framer-motion'
import {
  LayoutDashboard, MessageSquare, Monitor, Zap,
  Brain, Eye, ShieldAlert, ScrollText, Settings2,
  AlertOctagon, Sun, Moon, Wifi, WifiOff,
} from 'lucide-react'
import { useJarvisStore } from '../stores/jarvisStore'

type Panel = 'home' | 'conversation' | 'system' | 'automation' | 'memory' | 'vision' | 'privacy' | 'logs' | 'settings'

interface NavItem {
  id: string
  label: string
  icon: React.ReactNode
  panel: Panel
}

const NAV_ITEMS: NavItem[] = [
  { id: 'home', label: 'Dashboard', icon: <LayoutDashboard size={18} />, panel: 'home' },
  { id: 'conversation', label: 'AI Chat', icon: <MessageSquare size={18} />, panel: 'conversation' },
  { id: 'system', label: 'System', icon: <Monitor size={18} />, panel: 'system' },
  { id: 'automation', label: 'Automation', icon: <Zap size={18} />, panel: 'automation' },
  { id: 'memory', label: 'Memory', icon: <Brain size={18} />, panel: 'memory' },
  { id: 'vision', label: 'Vision', icon: <Eye size={18} />, panel: 'vision' },
  { id: 'privacy', label: 'Privacy', icon: <ShieldAlert size={18} />, panel: 'privacy' },
  { id: 'logs', label: 'Logs', icon: <ScrollText size={18} />, panel: 'logs' },
  { id: 'settings', label: 'Settings', icon: <Settings2 size={18} />, panel: 'settings' },
]

interface SidebarProps {
  theme: 'dark' | 'light'
  onThemeToggle: () => void
}

export function Sidebar({ theme, onThemeToggle }: SidebarProps) {
  const { activePanel, setActivePanel, backendOnline, emergencyStopped } = useJarvisStore()

  return (
    <aside style={{
      width: 220,
      flexShrink: 0,
      height: '100vh',
      background: 'var(--bg-secondary)',
      borderRight: '1px solid var(--border-subtle)',
      display: 'flex',
      flexDirection: 'column',
      padding: '0 0 16px 0',
      overflowY: 'auto',
    }}>
      {/* Logo */}
      <div style={{
        padding: '20px 20px 16px',
        borderBottom: '1px solid var(--border-subtle)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{
            width: 32, height: 32,
            borderRadius: '50%',
            background: 'linear-gradient(135deg, var(--cyan-500), var(--blue-500))',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            boxShadow: '0 0 16px rgba(56,189,248,0.4)',
            flexShrink: 0,
          }}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2.5">
              <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
            </svg>
          </div>
          <div>
            <div style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--text-accent)', letterSpacing: '0.1em' }}>
              JARVIS
            </div>
            <div style={{ fontSize: '0.6rem', color: 'var(--text-dim)', letterSpacing: '0.08em' }}>
              AI ASSISTANT
            </div>
          </div>
        </div>

        {/* Connection status */}
        <div style={{
          marginTop: 12,
          display: 'flex', alignItems: 'center', gap: 6,
          padding: '5px 10px',
          borderRadius: 'var(--radius-sm)',
          background: backendOnline
            ? 'rgba(34,197,94,0.08)'
            : 'rgba(239,68,68,0.08)',
          border: `1px solid ${backendOnline ? 'rgba(34,197,94,0.2)' : 'rgba(239,68,68,0.2)'}`,
        }}>
          {backendOnline
            ? <Wifi size={12} color="var(--green-400)" />
            : <WifiOff size={12} color="var(--red-400)" />}
          <span style={{
            fontSize: '0.68rem', fontWeight: 600,
            color: backendOnline ? 'var(--green-400)' : 'var(--red-400)',
          }}>
            {backendOnline ? 'BACKEND ONLINE' : 'DISCONNECTED'}
          </span>
        </div>

        {/* Emergency stop indicator */}
        {emergencyStopped && (
          <motion.div
            animate={{ opacity: [1, 0.5, 1] }}
            transition={{ duration: 0.8, repeat: Infinity }}
            style={{
              marginTop: 8,
              display: 'flex', alignItems: 'center', gap: 6,
              padding: '5px 10px',
              borderRadius: 'var(--radius-sm)',
              background: 'rgba(239,68,68,0.15)',
              border: '1px solid rgba(239,68,68,0.4)',
            }}
          >
            <AlertOctagon size={12} color="var(--red-400)" />
            <span style={{ fontSize: '0.68rem', fontWeight: 700, color: 'var(--red-400)' }}>
              EMERGENCY STOP
            </span>
          </motion.div>
        )}
      </div>

      {/* Nav */}
      <nav style={{ flex: 1, padding: '12px 10px', display: 'flex', flexDirection: 'column', gap: 2 }}>
        <div style={{ marginBottom: 4, padding: '0 8px' }}>
          <span className="label-sm">Navigation</span>
        </div>
        {NAV_ITEMS.map((item) => {
          const active = activePanel === item.panel
          return (
            <button
              key={item.id}
              onClick={() => setActivePanel(item.panel)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 10,
                padding: '9px 12px',
                borderRadius: 'var(--radius-md)',
                border: 'none',
                cursor: 'pointer',
                background: active ? 'rgba(56,189,248,0.1)' : 'transparent',
                color: active ? 'var(--text-accent)' : 'var(--text-secondary)',
                fontFamily: 'inherit',
                fontSize: '0.875rem',
                fontWeight: active ? 600 : 400,
                width: '100%',
                textAlign: 'left',
                transition: 'all var(--transition-fast)',
                position: 'relative',
              }}
              onMouseEnter={e => {
                if (!active) {
                  const el = e.currentTarget as HTMLButtonElement
                  el.style.background = 'var(--bg-tertiary)'
                  el.style.color = 'var(--text-primary)'
                }
              }}
              onMouseLeave={e => {
                if (!active) {
                  const el = e.currentTarget as HTMLButtonElement
                  el.style.background = 'transparent'
                  el.style.color = 'var(--text-secondary)'
                }
              }}
            >
              {active && (
                <motion.div
                  layoutId="nav-indicator"
                  style={{
                    position: 'absolute',
                    left: 0, top: 0, bottom: 0,
                    width: 3,
                    borderRadius: '0 2px 2px 0',
                    background: 'var(--cyan-500)',
                  }}
                />
              )}
              {item.icon}
              {item.label}
            </button>
          )
        })}
      </nav>

      {/* Bottom actions */}
      <div style={{ padding: '0 10px', display: 'flex', flexDirection: 'column', gap: 8 }}>
        <div className="divider" />
        <button
          onClick={onThemeToggle}
          className="btn btn-ghost"
          style={{ width: '100%', justifyContent: 'flex-start', gap: 10 }}
        >
          {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
          {theme === 'dark' ? 'Light Mode' : 'Dark Mode'}
        </button>
      </div>
    </aside>
  )
}
