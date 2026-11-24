import { OverlayWrapper } from './OverlayWrapper'
import { useJarvisStore } from '../../stores/jarvisStore'

interface SettingsOverlayProps {
  onClose: () => void
}

export function SettingsOverlay({ onClose }: SettingsOverlayProps) {
  const { status } = useJarvisStore()

  return (
    <OverlayWrapper
      title="SYSTEM SETTINGS & ARCHITECTURE"
      subtitle="DUAL AI CONFIGURATION & LOW-LATENCY RUNTIME"
      icon="settings"
      onClose={onClose}
    >
      <div className="flex flex-col gap-4">
        {/* Dual AI Provider Details */}
        <div className="p-4 rounded-xl bg-surface-container/60 border border-primary/20 flex flex-col gap-2">
          <div className="flex items-center justify-between">
            <span className="font-headline-sm text-[13px] text-primary">
              DUAL AI ENGINE SPECIFICATIONS
            </span>
            <span className="font-label-caps text-[10px] text-primary-container px-2 py-0.5 rounded bg-primary-container/10 border border-primary-container/30">
              OPTIMIZED 8 GB RAM
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-1">
            <div className="p-3 rounded-lg bg-surface-container-high/60 border border-white/5">
              <div className="font-label-caps text-[10px] text-primary-container">
                PRIMARY PROVIDER
              </div>
              <div className="font-mono text-[12px] text-on-surface font-semibold mt-0.5">
                Google Gemini API
              </div>
              <div className="font-telemetry-unit text-[10px] text-on-surface-variant mt-1">
                Model: gemini-3.8-flash // Streaming low-latency conversational brain
              </div>
            </div>

            <div className="p-3 rounded-lg bg-surface-container-high/60 border border-white/5">
              <div className="font-label-caps text-[10px] text-secondary">
                FALLBACK PROVIDER
              </div>
              <div className="font-mono text-[12px] text-on-surface font-semibold mt-0.5">
                OpenRouter API
              </div>
              <div className="font-telemetry-unit text-[10px] text-on-surface-variant mt-1">
                Model: meta-llama/llama-3-70b-instruct // Instant automatic failover
              </div>
            </div>
          </div>
        </div>

        {/* Voice Subsystem Info */}
        <div className="p-4 rounded-xl bg-surface-container/60 border border-white/5 flex flex-col gap-2">
          <span className="font-headline-sm text-[13px] text-primary">VOICE & DSP SUBSYSTEM</span>
          <div className="grid grid-cols-2 gap-2 text-on-surface-variant font-mono text-[11px]">
            <div>• Wake Phrase: "Jarvis"</div>
            <div>• TTS Engine: pyttsx3 (SAPI5)</div>
            <div>• Hotkey Toggle: Ctrl + Space</div>
            <div>• Interrupt Action: Esc / "Stop"</div>
          </div>
        </div>

        {/* Runtime Diagnostics */}
        <div className="p-4 rounded-xl bg-surface-container/60 border border-white/5 flex flex-col gap-1.5 font-mono text-[11px]">
          <span className="font-headline-sm text-[13px] text-primary mb-1">
            RUNTIME DIAGNOSTICS
          </span>
          <div className="flex justify-between text-on-surface-variant">
            <span>JARVIS Kernel Version:</span>
            <span className="text-primary-container">{status?.version ?? '4.2.0-STITCH'}</span>
          </div>
          <div className="flex justify-between text-on-surface-variant">
            <span>Registered Safe Tools:</span>
            <span className="text-primary-container">{status?.registered_tools_count ?? 18} Active</span>
          </div>
          <div className="flex justify-between text-on-surface-variant">
            <span>Memory Architecture:</span>
            <span className="text-secondary">{status?.memory_subsystem ?? 'Vector SQLite + JSON'}</span>
          </div>
        </div>
      </div>
    </OverlayWrapper>
  )
}
