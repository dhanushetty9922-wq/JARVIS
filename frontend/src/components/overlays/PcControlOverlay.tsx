import { useState } from 'react'
import { OverlayWrapper } from './OverlayWrapper'
import { useJarvisStore } from '../../stores/jarvisStore'
import { sendCommand } from '../../services/api'

interface PcControlOverlayProps {
  onClose: () => void
}

const APPS = [
  { id: 'notepad', label: 'Notepad', cmd: 'open notepad', icon: 'description', desc: 'Text editor' },
  { id: 'calc', label: 'Calculator', cmd: 'open calculator', icon: 'calculate', desc: 'Math utility' },
  { id: 'browser', label: 'Browser', cmd: 'open browser', icon: 'public', desc: 'Default web browser' },
  { id: 'explorer', label: 'File Explorer', cmd: 'open file explorer', icon: 'folder', desc: 'Local directory tree' },
  { id: 'paint', label: 'Paint', cmd: 'open paint', icon: 'draw', desc: 'Canvas application' },
  { id: 'cmd', label: 'Command Prompt', cmd: 'open command prompt', icon: 'terminal', desc: 'System shell' },
]

const SYSTEM_QUERIES = [
  { label: 'System Status', cmd: 'system status' },
  { label: 'Current Time', cmd: 'what time is it' },
  { label: 'CPU Usage', cmd: 'cpu usage' },
  { label: 'Memory Usage', cmd: 'memory usage' },
  { label: 'Disk Space', cmd: 'disk space' },
  { label: 'Network IP', cmd: 'what is my ip' },
]

export function PcControlOverlay({ onClose }: PcControlOverlayProps) {
  const { backendOnline, addMessage, setVoiceState } = useJarvisStore()
  const [running, setRunning] = useState<string | null>(null)
  const [lastOutput, setLastOutput] = useState<string | null>(null)

  const executeCmd = async (cmd: string) => {
    if (!backendOnline || running) return
    setRunning(cmd)
    addMessage({ role: 'user', text: cmd })
    setVoiceState('PROCESSING')

    try {
      const res = await sendCommand(cmd)
      setLastOutput(res.response)
      addMessage({ role: 'assistant', text: res.response })
    } catch {
      setLastOutput('Command failed: backend unreachable or permission blocked.')
    } finally {
      setRunning(null)
      setVoiceState('SLEEPING')
    }
  }

  return (
    <OverlayWrapper
      title="PC CONTROL MATRIX"
      subtitle="SANDBOXED SYSTEM EXECUTION & APP LAUNCHER"
      icon="laptop_windows"
      onClose={onClose}
    >
      <div>
        <div className="font-label-caps text-[11px] text-primary-container mb-2">
          ALLOWLISTED DESKTOP APPLICATIONS
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
          {APPS.map((app) => (
            <button
              key={app.id}
              disabled={!backendOnline || running === app.cmd}
              onClick={() => executeCmd(app.cmd)}
              className="flex items-center gap-2.5 p-3 rounded-xl bg-surface-container/60 hover:bg-primary-container/20 border border-white/5 hover:border-primary-container/40 transition-all text-left text-on-surface group disabled:opacity-50"
            >
              <div className="w-8 h-8 rounded-lg bg-surface-container-high flex items-center justify-center text-primary-container group-hover:scale-105 transition-transform">
                <span className="material-symbols-outlined text-[20px]">{app.icon}</span>
              </div>
              <div className="min-w-0 flex-1">
                <div className="font-headline-sm text-[13px] text-primary group-hover:text-primary-container">
                  {app.label}
                </div>
                <div className="font-telemetry-unit text-[10px] text-on-surface-variant truncate">
                  {app.desc}
                </div>
              </div>
            </button>
          ))}
        </div>
      </div>

      <div className="mt-2">
        <div className="font-label-caps text-[11px] text-secondary mb-2">
          SYSTEM TELEMETRY QUERIES
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
          {SYSTEM_QUERIES.map((q) => (
            <button
              key={q.label}
              disabled={!backendOnline || running === q.cmd}
              onClick={() => executeCmd(q.cmd)}
              className="p-2.5 rounded-lg bg-surface-container/40 hover:bg-secondary/20 border border-white/5 hover:border-secondary/40 text-left transition-all disabled:opacity-50"
            >
              <div className="font-label-caps text-[11px] text-on-surface">{q.label}</div>
              <div className="font-mono text-[10px] text-on-surface-variant mt-0.5">{q.cmd}</div>
            </button>
          ))}
        </div>
      </div>

      {lastOutput && (
        <div className="mt-2 p-3 rounded-lg bg-surface-container-low/90 border border-primary/20">
          <div className="font-label-caps text-[10px] text-primary-container mb-1">EXECUTION OUTCOME</div>
          <div className="font-mono text-[12px] text-tertiary whitespace-pre-wrap">{lastOutput}</div>
        </div>
      )}
    </OverlayWrapper>
  )
}
