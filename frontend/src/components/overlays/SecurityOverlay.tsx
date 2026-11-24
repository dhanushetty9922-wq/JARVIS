import { useEffect, useState } from 'react'
import { OverlayWrapper } from './OverlayWrapper'
import {
  fetchPermissions,
  updatePermission,
  triggerEmergencyStop,
  resetEmergencyStop,
  enableSafeMode,
  disableSafeMode,
} from '../../services/api'
import { useJarvisStore } from '../../stores/jarvisStore'

interface SecurityOverlayProps {
  onClose: () => void
}

const PERMISSIONS_LIST = [
  { key: 'microphone', label: 'Microphone', icon: 'mic', desc: 'Audio recording & voice parsing' },
  { key: 'internet', label: 'Internet Access', icon: 'public', desc: 'Cloud endpoints & web queries' },
  { key: 'pc_control', label: 'PC Control', icon: 'laptop_windows', desc: 'Allowlisted app launching' },
  { key: 'cloud_ai', label: 'Cloud AI Providers', icon: 'cloud', desc: 'Gemini & OpenRouter APIs' },
  { key: 'memory', label: 'Persistent Memory', icon: 'neurology', desc: 'Vector database read/write' },
]

export function SecurityOverlay({ onClose }: SecurityOverlayProps) {
  const { backendOnline, emergencyStopped, safeMode, setEmergencyStopped, setSafeMode } = useJarvisStore()
  const [permissions, setPermissions] = useState<Record<string, string>>({})
  const [updating, setUpdating] = useState<string | null>(null)

  const load = async () => {
    if (!backendOnline) return
    try {
      const data = await fetchPermissions()
      setPermissions(data.permissions ?? {})
    } catch {
      // ignore
    }
  }

  useEffect(() => {
    load()
  }, [backendOnline])

  const togglePermission = async (perm: string, current: string) => {
    const nextState = current === 'ALLOWED' ? 'block' : 'allow'
    setUpdating(perm)
    try {
      await updatePermission(perm, nextState as 'allow' | 'block', 'Toggled via Security HUD')
      setPermissions((prev) => ({
        ...prev,
        [perm]: nextState === 'allow' ? 'ALLOWED' : 'BLOCKED',
      }))
    } catch {
      // ignore
    } finally {
      setUpdating(null)
    }
  }

  const toggleSafeMode = async () => {
    try {
      if (safeMode) {
        await disableSafeMode()
        setSafeMode(false)
      } else {
        await enableSafeMode()
        setSafeMode(true)
      }
    } catch {
      // ignore
    }
  }

  const handleEmergencyStop = async () => {
    try {
      if (emergencyStopped) {
        await resetEmergencyStop()
        setEmergencyStopped(false)
      } else {
        await triggerEmergencyStop()
        setEmergencyStopped(true)
      }
    } catch {
      // ignore
    }
  }

  return (
    <OverlayWrapper
      title="SECURITY & DEFENSE MATRIX"
      subtitle="SANDBOX PERMISSIONS, SAFE MODE & KILL SWITCH"
      icon="security"
      onClose={onClose}
    >
      {/* Kill Switch & Safe Mode Controls */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {/* Emergency Stop Button */}
        <button
          onClick={handleEmergencyStop}
          className={`p-3.5 rounded-xl border flex items-center justify-between transition-all ${
            emergencyStopped
              ? 'bg-error text-white border-error shadow-[0_0_20px_rgba(255,82,82,0.5)]'
              : 'bg-error-container/20 hover:bg-error-container/40 text-error border-error/40'
          }`}
        >
          <div className="flex items-center gap-2.5">
            <span className="material-symbols-outlined text-[24px]">power_settings_new</span>
            <div className="text-left">
              <div className="font-headline-sm text-[13px]">
                {emergencyStopped ? 'EMERGENCY STOPPED' : 'EMERGENCY KILL SWITCH'}
              </div>
              <div className="font-telemetry-unit text-[10px] opacity-80">
                {emergencyStopped ? 'Click to re-arm kernel' : 'Halt all processes instantly'}
              </div>
            </div>
          </div>
          <span className="font-mono text-[11px] font-bold">
            {emergencyStopped ? 'RESET' : 'TRIP'}
          </span>
        </button>

        {/* Safe Mode Toggle */}
        <button
          onClick={toggleSafeMode}
          className={`p-3.5 rounded-xl border flex items-center justify-between transition-all ${
            safeMode
              ? 'bg-primary-container/20 border-primary-container/50 text-primary-container shadow-[0_0_16px_rgba(0,240,255,0.2)]'
              : 'bg-surface-container border-white/5 text-on-surface-variant hover:border-primary/40'
          }`}
        >
          <div className="flex items-center gap-2.5">
            <span className="material-symbols-outlined text-[24px]">verified_user</span>
            <div className="text-left">
              <div className="font-headline-sm text-[13px]">SAFE MODE PROTOCOL</div>
              <div className="font-telemetry-unit text-[10px] opacity-80">
                {safeMode ? 'L3 Strict Sandbox Active' : 'Relaxed Mode'}
              </div>
            </div>
          </div>
          <span className="font-mono text-[11px] font-bold">
            {safeMode ? 'ENABLED' : 'DISABLED'}
          </span>
        </button>
      </div>

      {/* Granular Permissions */}
      <div className="mt-2">
        <div className="font-label-caps text-[11px] text-primary-container mb-2">
          SUBSYSTEM PERMISSION GATES
        </div>
        <div className="flex flex-col gap-2">
          {PERMISSIONS_LIST.map((perm) => {
            const current = permissions[perm.key] ?? 'ALLOWED'
            const isAllowed = current === 'ALLOWED'
            return (
              <div
                key={perm.key}
                className="p-3 rounded-xl bg-surface-container/60 border border-white/5 flex items-center justify-between gap-3"
              >
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg bg-surface-container-high flex items-center justify-center text-primary-container">
                    <span className="material-symbols-outlined text-[18px]">{perm.icon}</span>
                  </div>
                  <div>
                    <div className="font-headline-sm text-[13px] text-on-surface">{perm.label}</div>
                    <div className="font-telemetry-unit text-[10px] text-on-surface-variant">
                      {perm.desc}
                    </div>
                  </div>
                </div>
                <button
                  disabled={updating === perm.key || !backendOnline}
                  onClick={() => togglePermission(perm.key, current)}
                  className={`px-3 py-1 rounded font-mono text-[11px] font-semibold transition-all border ${
                    isAllowed
                      ? 'bg-primary-container/20 text-primary-container border-primary-container/40 hover:bg-error/20 hover:text-error hover:border-error/40'
                      : 'bg-surface-container text-on-surface-variant border-white/10 hover:bg-primary-container/20 hover:text-primary-container hover:border-primary/40'
                  }`}
                >
                  {updating === perm.key ? 'SYNCING...' : isAllowed ? 'ALLOWED' : 'BLOCKED'}
                </button>
              </div>
            )
          })}
        </div>
      </div>
    </OverlayWrapper>
  )
}
