import { useState, useEffect, useCallback } from 'react'
import './App.css'
import { Header } from './components/Header'
import { ControlRail, type OverlayPanelId } from './components/ControlRail'
import { HolographicSphere, type AssistantVisualState } from './components/HolographicSphere'
import { SystemMatrix } from './components/SystemMatrix'
import { NeuralStream } from './components/NeuralStream'
import { StatusMatrixBar } from './components/StatusMatrixBar'
import { BottomFooter } from './components/BottomFooter'

// Overlay components
import { PcControlOverlay } from './components/overlays/PcControlOverlay'
import { AutomationOverlay } from './components/overlays/AutomationOverlay'
import { MemoryOverlay } from './components/overlays/MemoryOverlay'
import { VisionOverlay } from './components/overlays/VisionOverlay'
import { SecurityOverlay } from './components/overlays/SecurityOverlay'
import { ActivityOverlay } from './components/overlays/ActivityOverlay'
import { SettingsOverlay } from './components/overlays/SettingsOverlay'

// State & API
import { useJarvisStore } from './stores/jarvisStore'
import { useJarvisWebSocket } from './hooks/useJarvisWebSocket'
import { fetchStatus, startVoice, stopVoice, interruptVoice, wakeVoice, unmuteVoice } from './services/api'

export default function App() {
  const {
    status,
    setStatus,
    voiceState,
    setVoiceState,
    backendOnline,
    setBackendOnline,
  } = useJarvisStore()

  const [activeOverlay, setActiveOverlay] = useState<OverlayPanelId>('none')
  const [manualStateOverride, setManualStateOverride] = useState<AssistantVisualState | null>(null)

  // Establish WebSocket telemetry stream
  useJarvisWebSocket()

  // Poll status periodically to update telemetry metrics
  useEffect(() => {
    let mounted = true

    const poll = async () => {
      try {
        const data = await fetchStatus()
        if (mounted) {
          setStatus(data)
          setBackendOnline(true)
        }
      } catch {
        if (mounted) {
          setBackendOnline(false)
        }
      }
    }

    poll()
    const interval = setInterval(poll, 4000)
    return () => {
      mounted = false
      clearInterval(interval)
    }
  }, [setStatus, setBackendOnline])

  // Derive active visual state for Holographic Sphere
  const visualState: AssistantVisualState = manualStateOverride ?? (() => {
    if (!backendOnline) return 'DISCONNECTED'
    if (voiceState === 'MIC_DISABLED') return 'MIC_DISABLED'
    if (voiceState === 'LISTENING') return 'LISTENING'
    if (voiceState === 'THINKING' || voiceState === 'PROCESSING') return 'THINKING'
    if (voiceState === 'EXECUTING') return 'EXECUTING'
    if (voiceState === 'SPEAKING') return 'SPEAKING'
    if (voiceState === 'AWAKE') return 'AWAKE'
    if (voiceState === 'SLEEP' || voiceState === 'SLEEPING') return 'SLEEP'
    if (voiceState === 'ERROR') return 'ERROR'
    return 'STANDBY'
  })()

  // Voice command handlers
  const handleToggleVoice = useCallback(async () => {
    try {
      if (voiceState === 'MIC_DISABLED') {
        await unmuteVoice()
      } else if (voiceState === 'LISTENING' || voiceState === 'SPEAKING') {
        await stopVoice()
        setVoiceState('AWAKE')
      } else if (voiceState === 'SLEEP' || voiceState === 'SLEEPING') {
        await wakeVoice()
        setVoiceState('AWAKE')
      } else {
        await startVoice()
        setVoiceState('LISTENING')
      }
    } catch {
      // ignore
    }
  }, [voiceState, setVoiceState])

  const handleInterruptVoice = useCallback(async () => {
    try {
      await interruptVoice()
      setVoiceState('AWAKE')
      setManualStateOverride(null)
    } catch {
      // ignore
    }
  }, [setVoiceState])

  // Global hotkeys: [Esc] interrupts voice / closes overlay, [Ctrl+Space] toggles voice
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        if (activeOverlay !== 'none') {
          setActiveOverlay('none')
        } else if (voiceState === 'SPEAKING' || voiceState === 'LISTENING') {
          handleInterruptVoice()
        }
      } else if (e.ctrlKey && e.code === 'Space') {
        e.preventDefault()
        handleToggleVoice()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [activeOverlay, voiceState, handleInterruptVoice, handleToggleVoice])

  return (
    <div className="relative min-h-screen w-full bg-surface-container-lowest text-on-surface select-none overflow-x-hidden font-body-md">
      {/* Fixed Top Status Bar */}
      <Header onOpenSettings={() => setActiveOverlay('settings')} />

      {/* Fixed Left Floating Control Rail */}
      <ControlRail
        activeOverlay={activeOverlay}
        onToggleOverlay={(panel) => setActiveOverlay((curr) => (curr === panel ? 'none' : panel))}
      />

      {/* Main Viewport Content Area */}
      <div className="pl-16">
        <main className="relative pt-14 pb-10 min-h-screen w-full bg-surface-container-lowest bg-[radial-gradient(ellipse_80%_80%_at_50%_-20%,rgba(0,240,255,0.08),rgba(15,19,28,0))]">
          {/* Dynamic Atmospheric Glows & Grid Matrix */}
          <div className="absolute inset-0 pointer-events-none overflow-hidden">
            <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[720px] h-[720px] bg-radial from-primary-container/15 via-secondary/5 to-transparent blur-3xl opacity-75"></div>
            <div className="absolute top-10 left-20 w-96 h-96 bg-primary-container/10 blur-[100px] rounded-full"></div>
            <div className="absolute bottom-20 right-20 w-[480px] h-[480px] bg-secondary/10 blur-[120px] rounded-full"></div>
            {/* Fine HUD Blueprint Reticle Matrix */}
            <div className="absolute inset-0 bg-[radial-gradient(rgba(0,240,255,0.06)_1px,transparent_1px)] [background-size:32px_32px] opacity-40"></div>
            <div className="absolute inset-x-0 top-1/2 h-px bg-gradient-to-r from-transparent via-primary-container/20 to-transparent"></div>
            <div className="absolute inset-y-0 left-1/2 w-px bg-gradient-to-b from-transparent via-primary-container/20 to-transparent"></div>
          </div>

          {/* Primary HUD Stage Area */}
          <div className="relative z-10 w-full max-w-[1720px] mx-auto px-space-md lg:px-space-xl py-space-sm flex flex-col gap-space-md">
            {/* Top Telemetry Ribbon / Quick Diagnostics */}
            <div className="w-full flex flex-wrap items-center justify-between gap-space-sm bg-surface-container-low/70 border border-primary/20 backdrop-blur-xl px-space-md py-space-sm rounded-lg shadow-xl shadow-surface-container-lowest/80">
              <div className="flex items-center gap-space-md divide-x divide-outline-variant/30">
                <div className="flex items-center gap-space-sm">
                  <span className="w-2 h-2 rounded-full bg-primary-container shadow-[0_0_10px_#00f0ff] animate-ping"></span>
                  <span className="font-label-caps text-label-caps text-primary tracking-widest">
                    ARC-CORE::SYS_STABLE
                  </span>
                  <span className="font-telemetry-unit text-telemetry-unit px-space-xs py-0.5 rounded bg-surface-container text-on-surface-variant font-mono">
                    LAT: 11.4ms
                  </span>
                </div>
                <div className="hidden sm:flex items-center gap-space-sm pl-space-md">
                  <span className="font-label-caps text-label-caps text-on-surface-variant">
                    SEC_ENCLAVE
                  </span>
                  <span className="font-telemetry-data text-telemetry-data text-primary-container font-mono">
                    HARDWARE_ISOLATED
                  </span>
                </div>
                <div className="hidden md:flex items-center gap-space-sm pl-space-md">
                  <span className="font-label-caps text-label-caps text-on-surface-variant">
                    MEM_BANDWIDTH
                  </span>
                  <span className="font-telemetry-data text-telemetry-data text-secondary font-mono">
                    1.24 TB/s
                  </span>
                </div>
              </div>

              <div className="flex items-center gap-space-md font-telemetry-unit text-telemetry-unit">
                <div className="hidden xl:flex items-center gap-space-xs text-on-surface-variant">
                  <span className="material-symbols-outlined text-[15px] text-primary-container">
                    mic
                  </span>
                  <span>48kHz SAPI Audio Capture</span>
                </div>
                <div className="hidden lg:flex items-center gap-space-xs text-on-surface-variant">
                  <span className="material-symbols-outlined text-[15px] text-secondary">
                    surround_sound
                  </span>
                  <span>Spatial DSP 7.1 Atmos</span>
                </div>
                <div className="flex items-center gap-space-xs px-space-sm py-0.5 rounded bg-surface-container text-primary border border-primary/20">
                  <span className="w-1.5 h-1.5 rounded-full bg-primary-container"></span>
                  <span className="font-label-caps text-label-caps">
                    {status?.ai_active_provider === 'GEMINI' ? 'GEMINI 3.8 FLASH // PRIME' : 'OPENROUTER // HOT BACKUP'}
                  </span>
                </div>
              </div>
            </div>

            {/* Central Holographic Sphere & Assistant Visualizer */}
            <div className="relative w-full flex flex-col items-center justify-center py-1">
              <HolographicSphere
                state={visualState}
                onStateSelect={(s) => setManualStateOverride(s)}
              />
            </div>

            {/* Lower Cockpit Bento Split View */}
            <div className="w-full grid grid-cols-1 lg:grid-cols-12 gap-space-lg items-start">
              {/* Left Column: System Matrix (Cols 1-4) */}
              <div className="lg:col-span-4 flex flex-col gap-space-md">
                <SystemMatrix
                  onOpenMemory={() => setActiveOverlay('memory')}
                  onOpenPcControl={() => setActiveOverlay('pc_control')}
                />
              </div>

              {/* Right Column: Neural Stream & Dialog Terminal (Cols 5-12) */}
              <div className="lg:col-span-8 flex flex-col gap-space-md">
                <NeuralStream
                  onStopVoice={handleInterruptVoice}
                  onToggleVoice={handleToggleVoice}
                  onVisionClick={() => setActiveOverlay('vision')}
                />
              </div>
            </div>

            {/* Complementary Status Matrix (Quick Floating System Bar) */}
            <StatusMatrixBar />
          </div>
        </main>
      </div>

      {/* Floating HUD Overlays for Rail Actions */}
      {activeOverlay === 'pc_control' && (
        <PcControlOverlay onClose={() => setActiveOverlay('none')} />
      )}
      {activeOverlay === 'automation' && (
        <AutomationOverlay onClose={() => setActiveOverlay('none')} />
      )}
      {activeOverlay === 'memory' && (
        <MemoryOverlay onClose={() => setActiveOverlay('none')} />
      )}
      {activeOverlay === 'vision' && (
        <VisionOverlay onClose={() => setActiveOverlay('none')} />
      )}
      {activeOverlay === 'security' && (
        <SecurityOverlay onClose={() => setActiveOverlay('none')} />
      )}
      {activeOverlay === 'activity' && (
        <ActivityOverlay onClose={() => setActiveOverlay('none')} />
      )}
      {activeOverlay === 'settings' && (
        <SettingsOverlay onClose={() => setActiveOverlay('none')} />
      )}

      {/* Fixed Bottom Telemetry Footer */}
      <BottomFooter />
    </div>
  )
}
