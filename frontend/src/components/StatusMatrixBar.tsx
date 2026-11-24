import { useJarvisStore } from '../stores/jarvisStore'

export function StatusMatrixBar() {
  const { status, safeMode } = useJarvisStore()

  const primaryModel = status?.ai_primary_provider === 'GEMINI' ? 'Gemini 3.8 Flash Low-Latency' : 'Dual Engine Ready'
  const backupModel = status?.ai_backup_provider === 'OPENROUTER' ? 'OpenRouter Llama 3 70B' : 'Hot Backup Standby'
  const isFallback = status?.ai_fallback_active ?? false

  return (
    <div className="w-full grid grid-cols-2 md:grid-cols-4 gap-space-sm pt-space-xs">
      <div className="bg-surface-container-low/70 border border-primary/20 backdrop-blur-md p-space-sm rounded-lg flex items-center gap-space-sm shadow-md">
        <span className="material-symbols-outlined text-primary-container text-[22px]">hub</span>
        <div className="flex flex-col min-w-0">
          <span className="font-label-caps text-[10px] text-on-surface-variant truncate">NEURAL ENGINE</span>
          <span className="font-telemetry-data text-telemetry-data text-primary truncate" title={primaryModel}>
            {primaryModel}
          </span>
        </div>
      </div>

      <div className="bg-surface-container-low/70 border border-secondary/20 backdrop-blur-md p-space-sm rounded-lg flex items-center gap-space-sm shadow-md">
        <span className="material-symbols-outlined text-secondary text-[22px]">swap_calls</span>
        <div className="flex flex-col min-w-0">
          <span className="font-label-caps text-[10px] text-on-surface-variant truncate">
            {isFallback ? 'BACKUP ENGAGED' : 'HOT BACKUP'}
          </span>
          <span className="font-telemetry-data text-telemetry-data text-secondary truncate" title={backupModel}>
            {backupModel}
          </span>
        </div>
      </div>

      <div className="bg-surface-container-low/70 border border-primary/20 backdrop-blur-md p-space-sm rounded-lg flex items-center gap-space-sm shadow-md">
        <span className="material-symbols-outlined text-primary-container text-[22px]">graphic_eq</span>
        <div className="flex flex-col min-w-0">
          <span className="font-label-caps text-[10px] text-on-surface-variant truncate">SPEECH SYNTHESIS</span>
          <span className="font-telemetry-data text-telemetry-data text-primary truncate">
            Spatial Voice (pyttsx3 // SAPI)
          </span>
        </div>
      </div>

      <div className="bg-surface-container-low/70 border border-tertiary/20 backdrop-blur-md p-space-sm rounded-lg flex items-center gap-space-sm shadow-md">
        <span className="material-symbols-outlined text-tertiary-fixed-dim text-[22px]">security</span>
        <div className="flex flex-col min-w-0">
          <span className="font-label-caps text-[10px] text-on-surface-variant truncate">HARDWARE SANDBOX</span>
          <span className="font-telemetry-data text-telemetry-data text-tertiary-fixed-dim truncate">
            {safeMode ? 'Safe Mode Active // L3' : 'Standard Sandbox // Permissive'}
          </span>
        </div>
      </div>
    </div>
  )
}
