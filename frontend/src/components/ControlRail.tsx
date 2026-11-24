export type OverlayPanelId =
  | 'none'
  | 'pc_control'
  | 'automation'
  | 'memory'
  | 'vision'
  | 'security'
  | 'activity'
  | 'settings'

interface ControlRailProps {
  activeOverlay: OverlayPanelId
  onToggleOverlay: (panel: OverlayPanelId) => void
}

interface NavItem {
  id: OverlayPanelId
  label: string
  icon: string
}

const NAV_ITEMS: NavItem[] = [
  { id: 'pc_control', label: 'PC Control', icon: 'terminal' },
  { id: 'automation', label: 'Automation', icon: 'precision_manufacturing' },
  { id: 'memory', label: 'Memory Core', icon: 'neurology' },
  { id: 'vision', label: 'Vision Array', icon: 'visibility' },
  { id: 'security', label: 'Security Shield', icon: 'shield' },
  { id: 'activity', label: 'Activity Stream', icon: 'monitoring' },
]

export function ControlRail({ activeOverlay, onToggleOverlay }: ControlRailProps) {
  return (
    <aside
      className="fixed left-0 top-14 bottom-8 w-16 z-40 flex flex-col items-center py-4 justify-between select-none backdrop-blur-xl"
      style={{
        background: 'rgba(10, 14, 23, 0.75)',
        borderRight: '1px solid var(--border-subtle)',
        boxShadow: '1px 0 16px rgba(0, 0, 0, 0.55)',
      }}
    >
      {/* Navigation Icons Group */}
      <nav className="flex flex-col gap-3 items-center w-full px-2">
        {NAV_ITEMS.map((item) => {
          const isActive = activeOverlay === item.id
          return (
            <button
              key={item.id}
              onClick={() => onToggleOverlay(isActive ? 'none' : item.id)}
              className="w-10 h-10 rounded-lg flex items-center justify-center transition-all relative group"
              style={{
                background: isActive
                  ? 'var(--primary-container)'
                  : 'rgba(28, 31, 41, 0.5)',
                color: isActive ? '#00363a' : 'var(--on-surface-variant)',
                boxShadow: isActive
                  ? '0 0 16px rgba(0, 240, 255, 0.45)'
                  : 'none',
                border: isActive
                  ? '1px solid var(--primary)'
                  : '1px solid var(--border-subtle)',
              }}
              title={item.label}
            >
              <span className="material-symbols-outlined text-[20px] group-hover:scale-110 transition-transform">
                {item.icon}
              </span>

              {/* Active Pip Indicator */}
              {isActive && (
                <span
                  className="absolute -right-1 top-1/2 -translate-y-1/2 w-1.5 h-3 rounded-l"
                  style={{ backgroundColor: 'var(--primary-container)' }}
                />
              )}
            </button>
          )
        })}
      </nav>

      {/* Bottom Rail Node Indicator */}
      <div className="flex flex-col items-center gap-1">
        <div
          className="w-2 h-2 rounded-full animate-pulse"
          style={{
            backgroundColor: 'var(--primary-container)',
            boxShadow: '0 0 10px #00f0ff',
          }}
        />
        <span className="text-label-caps text-[9px]" style={{ color: 'var(--text-dim)', letterSpacing: '0.14em' }}>
          NODE
        </span>
      </div>
    </aside>
  )
}
