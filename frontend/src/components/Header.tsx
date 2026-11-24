import { useJarvisStore } from '../stores/jarvisStore'

interface HeaderProps {
  onOpenSettings: () => void
}

export function Header({ onOpenSettings }: HeaderProps) {
  const { status, backendOnline } = useJarvisStore()

  const cpuPercent = status?.system_cpu_percent ? Math.round(status.system_cpu_percent) : 14
  const ramUsed = status?.system_ram_used_gb ?? 4.2
  const ramTotal = status?.system_ram_total_gb ?? 8.0

  const primaryName = status?.ai_primary_provider?.toUpperCase() || 'GEMINI 3.8 FLASH'
  const backupName = status?.ai_backup_provider?.toUpperCase() || 'OPENROUTER'
  const isFallback = Boolean(status?.ai_fallback_active)

  return (
    <header
      className="fixed top-0 left-0 right-0 h-14 z-50 flex items-center justify-between px-4 select-none backdrop-blur-xl"
      style={{
        background: 'rgba(10, 14, 23, 0.82)',
        borderBottom: '1px solid var(--border-subtle)',
        boxShadow: '0 1px 12px rgba(0, 0, 0, 0.5)',
      }}
    >
      {/* Left: Brand Identity & Kernel Readiness */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          <span
            className="material-symbols-outlined text-[20px] animate-pulse"
            style={{ color: 'var(--primary-container)', filter: 'drop-shadow(0 0 8px #00f0ff)' }}
          >
            token
          </span>
          <span className="font-display font-semibold tracking-wider text-[15px]" style={{ color: 'var(--primary)' }}>
            JARVIS{' '}
            <span className="text-label-caps" style={{ color: 'var(--primary-container)', fontSize: '10px' }}>
              // OS v4.2
            </span>
          </span>
        </div>

        {/* Kernel Status Pill */}
        <div
          className="hidden sm:flex items-center gap-1.5 px-2.5 py-0.5 rounded-full"
          style={{ background: 'var(--surface-high)', border: '1px solid var(--border-subtle)' }}
        >
          <span
            className={`w-1.5 h-1.5 rounded-full ${backendOnline ? 'bg-primary-container animate-ping' : 'bg-red-400'}`}
            style={{ backgroundColor: backendOnline ? 'var(--primary-container)' : 'var(--error)' }}
          />
          <span className="text-label-caps text-[9px]" style={{ color: 'var(--on-surface-variant)' }}>
            {backendOnline ? 'ONLINE - KERNEL READY' : 'OFFLINE - CORE DISCONNECTED'}
          </span>
        </div>
      </div>

      {/* Center: Dual AI Provider Status Indicators */}
      <div className="hidden md:flex items-center gap-2">
        {/* Primary Gemini Pill */}
        <div
          className="flex items-center gap-1.5 px-2.5 py-1 rounded"
          style={{
            background: isFallback ? 'var(--surface-container-low)' : 'var(--surface-container)',
            border: isFallback ? '1px solid var(--border-subtle)' : '1px solid var(--border-accent)',
            boxShadow: isFallback ? 'none' : '0 0 10px rgba(0, 240, 255, 0.25)',
          }}
        >
          <span
            className="w-2 h-2 rounded-full"
            style={{
              backgroundColor: isFallback ? 'var(--text-dim)' : 'var(--primary-container)',
              boxShadow: isFallback ? 'none' : '0 0 8px #00f0ff',
            }}
          />
          <span
            className="text-label-caps"
            style={{ color: isFallback ? 'var(--on-surface-variant)' : 'var(--primary)', fontSize: '10px' }}
          >
            {primaryName} // {isFallback ? 'STANDBY' : 'ACTIVE'}
          </span>
        </div>

        {/* Backup OpenRouter Pill */}
        <div
          className="flex items-center gap-1.5 px-2.5 py-1 rounded"
          style={{
            background: isFallback ? 'rgba(245, 158, 11, 0.15)' : 'var(--surface-container-low)',
            border: isFallback ? '1px solid var(--amber-400)' : '1px solid var(--border-subtle)',
            boxShadow: isFallback ? '0 0 12px rgba(245, 158, 11, 0.3)' : 'none',
          }}
        >
          <span
            className="w-2 h-2 rounded-full"
            style={{
              backgroundColor: isFallback ? 'var(--amber-400)' : 'var(--secondary)',
              boxShadow: isFallback ? '0 0 8px var(--amber-400)' : '0 0 6px #bdc2ff',
            }}
          />
          <span
            className="text-label-caps"
            style={{ color: isFallback ? 'var(--amber-400)' : 'var(--on-surface-variant)', fontSize: '10px' }}
          >
            {backupName} // {isFallback ? 'FALLBACK ACTIVE' : 'SYNCED'}
          </span>
        </div>
      </div>

      {/* Right: Live Telemetry & Control Group */}
      <div className="flex items-center gap-3">
        {/* Hardware telemetry readouts */}
        <div className="hidden lg:flex items-center gap-3 text-telemetry-data text-[12px]">
          <div className="flex items-center gap-1">
            <span className="text-label-caps text-[9px]" style={{ color: 'var(--primary-container)' }}>CPU</span>
            <span className="font-mono text-on-surface">{cpuPercent}%</span>
          </div>
          <div className="flex items-center gap-1">
            <span className="text-label-caps text-[9px]" style={{ color: 'var(--primary-container)' }}>RAM</span>
            <span className="font-mono text-on-surface">{ramUsed}/{ramTotal}GB</span>
          </div>
          <div className="flex items-center gap-1">
            <span className="text-label-caps text-[9px]" style={{ color: 'var(--primary-container)' }}>NET</span>
            <span className="font-mono text-on-surface">18ms</span>
          </div>
        </div>

        {/* Settings button */}
        <button
          onClick={onOpenSettings}
          className="w-8 h-8 rounded flex items-center justify-center transition-all hover:bg-surface-high text-on-surface-variant hover:text-primary"
          style={{ border: '1px solid var(--border-subtle)' }}
          title="System Settings"
        >
          <span className="material-symbols-outlined text-[18px]">settings</span>
        </button>

        {/* User Identity Avatar */}
        <div
          className="w-8 h-8 rounded-full flex items-center justify-center"
          style={{ background: 'var(--primary)', color: 'var(--surface-lowest)' }}
        >
          <span className="material-symbols-outlined text-[18px]">person</span>
        </div>

        {/* Windows OS Window Emulators */}
        <div className="hidden sm:flex items-center ml-1 border-l border-outline-variant/30 pl-2">
          <button className="w-8 h-7 flex items-center justify-center text-on-surface-variant hover:bg-surface-high hover:text-on-surface transition-colors">
            <span className="material-symbols-outlined text-[15px]">remove</span>
          </button>
          <button className="w-8 h-7 flex items-center justify-center text-on-surface-variant hover:bg-surface-high hover:text-on-surface transition-colors">
            <span className="material-symbols-outlined text-[13px]">crop_square</span>
          </button>
          <button className="w-8 h-7 flex items-center justify-center text-on-surface-variant hover:bg-red-500/20 hover:text-red-400 transition-colors">
            <span className="material-symbols-outlined text-[15px]">close</span>
          </button>
        </div>
      </div>
    </header>
  )
}
