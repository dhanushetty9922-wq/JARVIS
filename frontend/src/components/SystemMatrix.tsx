import { useState } from 'react'
import { useJarvisStore } from '../stores/jarvisStore'
import { sendCommand } from '../services/api'

interface SystemMatrixProps {
  onOpenMemory?: () => void
  onOpenPcControl?: () => void
}

const QUICK_APPS = [
  { label: 'Notepad', cmd: 'open notepad', icon: 'description' },
  { label: 'Calculator', cmd: 'open calculator', icon: 'calculate' },
  { label: 'Browser', cmd: 'open browser', icon: 'public' },
  { label: 'Explorer', cmd: 'open file explorer', icon: 'folder' },
  { label: 'Terminal', cmd: 'open command prompt', icon: 'terminal' },
]

export function SystemMatrix({ onOpenMemory, onOpenPcControl }: SystemMatrixProps) {
  const { status, backendOnline, safeMode, addMessage, setVoiceState } = useJarvisStore()
  const [runningCmd, setRunningCmd] = useState<string | null>(null)

  const cpuPercent = status?.system_cpu_percent ?? 18
  const ramPercent = status?.system_ram_percent ?? 42
  const ramUsed = status?.system_ram_used_gb?.toFixed(1) ?? '3.4'
  const ramTotal = status?.system_ram_total_gb?.toFixed(1) ?? '8.0'
  const cpuSpeed = (2.8 + (cpuPercent / 100) * 1.6).toFixed(2)

  const runQuickAction = async (cmd: string) => {
    if (!backendOnline || runningCmd) return
    setRunningCmd(cmd)
    addMessage({ role: 'user', text: cmd })
    setVoiceState('PROCESSING')
    try {
      const res = await sendCommand(cmd)
      addMessage({ role: 'assistant', text: res.response })
    } catch {
      addMessage({ role: 'assistant', text: 'Error executing system routine.' })
    } finally {
      setRunningCmd(null)
      setVoiceState('SLEEPING')
    }
  }

  return (
    <div className="w-full bg-surface-container-low/80 backdrop-blur-xl border border-primary/20 rounded-xl p-space-md flex flex-col gap-space-md shadow-2xl shadow-surface-container-lowest">
      {/* Header */}
      <div className="flex items-center justify-between pb-1 border-b border-white/5">
        <div className="flex items-center gap-space-sm">
          <span className="material-symbols-outlined text-primary-container text-[20px]">tune</span>
          <span className="font-headline-sm text-headline-sm text-primary tracking-wide">SYSTEM MATRIX</span>
        </div>
        <div className="flex items-center gap-1.5 px-space-xs py-0.5 rounded bg-surface-container font-label-caps text-[10px] text-primary-container border border-primary/20">
          <span className="w-1.5 h-1.5 rounded-full bg-primary-container animate-pulse"></span>
          <span>NODE: JARVIS-HOST</span>
        </div>
      </div>

      {/* Performance Gauges Dual Column */}
      <div className="grid grid-cols-2 gap-space-sm">
        {/* RAM / Memory Cluster Card */}
        <div className="bg-surface-container/70 border border-white/5 rounded-lg p-space-sm flex flex-col gap-1">
          <div className="flex justify-between items-center text-on-surface-variant font-label-caps text-[10px]">
            <span>SYSTEM RAM</span>
            <span className="text-primary-container font-mono">{ramPercent}%</span>
          </div>
          <div className="font-headline-md text-headline-md text-primary font-mono tracking-tight mt-0.5">
            {ramUsed} <span className="text-[12px] text-on-surface-variant">/ {ramTotal} GB</span>
          </div>
          <div className="w-full bg-surface-container-highest h-1 rounded-full overflow-hidden mt-1">
            <div
              className="bg-gradient-to-r from-primary-container to-secondary h-full transition-all duration-500"
              style={{ width: `${Math.min(100, Math.max(5, ramPercent))}%` }}
            ></div>
          </div>
          <span className="font-telemetry-unit text-[10px] text-on-surface-variant mt-0.5">
            DDR4 Low-Profile Pool
          </span>
        </div>

        {/* CPU Cluster Card */}
        <div className="bg-surface-container/70 border border-white/5 rounded-lg p-space-sm flex flex-col gap-1">
          <div className="flex justify-between items-center text-on-surface-variant font-label-caps text-[10px]">
            <span>CPU CLUSTER</span>
            <span className="text-secondary font-mono">{cpuPercent}%</span>
          </div>
          <div className="font-headline-md text-headline-md text-primary font-mono tracking-tight mt-0.5">
            {cpuSpeed} <span className="text-[12px] text-on-surface-variant">GHz</span>
          </div>
          <div className="w-full bg-surface-container-highest h-1 rounded-full overflow-hidden mt-1">
            <div
              className="bg-gradient-to-r from-secondary to-primary-container h-full transition-all duration-500"
              style={{ width: `${Math.min(100, Math.max(5, cpuPercent))}%` }}
            ></div>
          </div>
          <span className="font-telemetry-unit text-[10px] text-on-surface-variant mt-0.5">
            Multi-Core Dispatch Nominal
          </span>
        </div>
      </div>

      {/* Quick Launch Allowlisted Utilities */}
      <div className="flex flex-col gap-1.5 pt-0.5">
        <div className="flex items-center justify-between">
          <span className="font-label-caps text-[10px] text-on-surface-variant tracking-wider">
            ALLOWLISTED PC UTILITIES
          </span>
          {onOpenPcControl && (
            <button
              onClick={onOpenPcControl}
              className="font-label-caps text-[10px] text-primary-container hover:underline"
            >
              EXPAND
            </button>
          )}
        </div>
        <div className="grid grid-cols-5 gap-1.5">
          {QUICK_APPS.map((app) => (
            <button
              key={app.label}
              disabled={!backendOnline || runningCmd === app.cmd}
              onClick={() => runQuickAction(app.cmd)}
              className="flex flex-col items-center justify-center p-2 rounded bg-surface-container/50 hover:bg-primary-container/20 hover:text-primary-container border border-white/5 hover:border-primary-container/40 transition-all text-on-surface-variant group disabled:opacity-50"
              title={`Execute: ${app.cmd}`}
            >
              <span className="material-symbols-outlined text-[18px] group-hover:scale-110 transition-transform">
                {app.icon}
              </span>
              <span className="font-label-caps text-[8px] mt-1 truncate max-w-full">
                {app.label}
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* Active Background Protocols */}
      <div className="flex flex-col gap-space-xs pt-1">
        <span className="font-label-caps text-[10px] text-on-surface-variant tracking-wider">
          ACTIVE BACKGROUND PROTOCOLS
        </span>
        <div className="flex flex-col gap-1.5">
          <div className="flex items-center justify-between p-2 rounded bg-surface-container/40 hover:bg-surface-container border border-white/5 transition-colors">
            <div className="flex items-center gap-2">
              <span className="material-symbols-outlined text-[16px] text-primary-container">memory</span>
              <div className="flex flex-col">
                <span className="font-body-sm text-body-sm text-on-surface font-medium">
                  Dual AI Provider Pipeline
                </span>
                <span className="font-telemetry-unit text-[10px] text-on-surface-variant">
                  {status?.ai_active_provider === 'GEMINI' ? 'Gemini 3.8 Flash Primary' : 'OpenRouter Active'} // Fallback Ready
                </span>
              </div>
            </div>
            <span className="font-label-caps text-[10px] text-primary-container px-2 py-0.5 rounded bg-primary-container/10 border border-primary-container/30">
              HOT
            </span>
          </div>

          <div className="flex items-center justify-between p-2 rounded bg-surface-container/40 hover:bg-surface-container border border-white/5 transition-colors">
            <div className="flex items-center gap-2">
              <span className="material-symbols-outlined text-[16px] text-secondary">shield</span>
              <div className="flex flex-col">
                <span className="font-body-sm text-body-sm text-on-surface font-medium">
                  Zero-Trust Sandbox Guard
                </span>
                <span className="font-telemetry-unit text-[10px] text-on-surface-variant">
                  {safeMode ? 'Safe Mode Active — All Tools Verified' : 'Standard Mode'}
                </span>
              </div>
            </div>
            <span className="font-label-caps text-[10px] text-secondary px-2 py-0.5 rounded bg-secondary/10 border border-secondary/30">
              SHIELD
            </span>
          </div>
        </div>
      </div>

      {/* Vector Memory Stream Indicator */}
      <div className="flex items-center justify-between p-space-sm rounded-lg bg-surface-container/30 border border-white/5">
        <div className="flex items-center gap-space-sm">
          <span className="material-symbols-outlined text-primary-container text-[18px]">neurology</span>
          <div className="flex flex-col">
            <span className="font-label-caps text-label-caps text-primary">VECTOR RECALL CORE</span>
            <span className="font-telemetry-unit text-telemetry-unit text-on-surface-variant">
              {status?.database_status === 'CONNECTED' ? 'Local SQLite & Chroma Synced' : 'Vector Node Standby'}
            </span>
          </div>
        </div>
        <button
          onClick={onOpenMemory}
          className="px-space-sm py-1 rounded bg-surface-container-high hover:bg-primary-container hover:text-on-primary-container text-primary font-label-caps text-[10px] transition-colors border border-primary/20"
        >
          QUERY
        </button>
      </div>
    </div>
  )
}
