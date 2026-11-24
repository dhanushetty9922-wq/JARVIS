import { useJarvisStore } from '../stores/jarvisStore'
import { toggleMuteVoice } from '../services/api'

export function BottomFooter() {
  const { status, safeMode, voiceState, isMuted, setIsMuted } = useJarvisStore()

  const isMicMuted = isMuted || status?.is_muted || voiceState === 'MIC_DISABLED'
  const isSleep = voiceState === 'SLEEP' || voiceState === 'SLEEPING'

  let micStateLabel = '48kHz FLAC ACTIVE'
  let micIcon = 'mic'
  let micColor = 'var(--primary-container)'

  if (isMicMuted) {
    micStateLabel = 'MIC MUTED (CAPTURE OFF)'
    micIcon = 'mic_off'
    micColor = '#f59e0b'
  } else if (isSleep) {
    micStateLabel = 'SLEEP (WAKE: "JARVIS")'
    micIcon = 'bedtime'
    micColor = '#38bdf8'
  } else if (status?.microphone_permission !== 'ALLOWED') {
    micStateLabel = 'MIC BLOCKED'
    micIcon = 'mic_off'
    micColor = 'var(--error)'
  }

  const handleToggleMute = async () => {
    try {
      const res = await toggleMuteVoice()
      if (res && typeof res.is_muted === 'boolean') {
        setIsMuted(res.is_muted)
      }
    } catch {
      // ignore
    }
  }

  const isSafe = safeMode ?? (status?.safe_mode === 'ENABLED')

  return (
    <footer
      className="fixed bottom-0 left-0 right-0 h-8 z-50 flex items-center justify-between px-4 select-none backdrop-blur-xl"
      style={{
        background: 'rgba(10, 14, 23, 0.92)',
        borderTop: '1px solid var(--border-subtle)',
        boxShadow: '0 -1px 8px rgba(0, 0, 0, 0.45)',
      }}
    >
      {/* Left: Audio IN / OUT telemetry & Mute Toggle */}
      <div className="flex items-center gap-4 text-telemetry-unit text-[11px]" style={{ color: 'var(--on-surface-variant)' }}>
        <button
          onClick={handleToggleMute}
          className="flex items-center gap-1.5 px-2 py-0.5 rounded hover:bg-white/5 transition-colors cursor-pointer border border-transparent hover:border-white/10"
          title={isMicMuted ? 'Click to unmute microphone' : 'Click to mute microphone (halts all capture)'}
        >
          <span
            className="material-symbols-outlined text-[14px]"
            style={{ color: micColor }}
          >
            {micIcon}
          </span>
          <span style={{ color: isMicMuted ? '#f59e0b' : 'inherit' }}>IN: {micStateLabel}</span>
          {!isMicMuted && !isSleep && status?.seconds_until_sleep !== undefined && status.seconds_until_sleep > 0 && (
            <span className="text-[9px] opacity-70 ml-1 font-mono text-cyan-400">
              [{Math.round(status.seconds_until_sleep)}s]
            </span>
          )}
        </button>
        <div className="hidden sm:flex items-center gap-1.5">
          <span className="material-symbols-outlined text-[14px]" style={{ color: 'var(--secondary)' }}>
            graphic_eq
          </span>
          <span>OUT: Spatial DSP (SAPI5 Engine)</span>
        </div>
      </div>

      {/* Right: Security & Network Telemetry */}
      <div className="flex items-center gap-4 text-telemetry-unit text-[11px]">
        <div className="flex items-center gap-1.5">
          <span
            className="w-1.5 h-1.5 rounded-full"
            style={{ backgroundColor: 'var(--primary-container)', boxShadow: '0 0 6px #00f0ff' }}
          />
          <span style={{ color: 'var(--on-surface-variant)' }}>LATENCY: 11.4ms</span>
        </div>

        <div
          className="flex items-center gap-1 px-2 py-0.5 rounded"
          style={{
            background: isSafe ? 'rgba(0, 240, 255, 0.1)' : 'rgba(245, 158, 11, 0.15)',
            border: isSafe ? '1px solid var(--border-subtle)' : '1px solid var(--amber-400)',
            color: isSafe ? 'var(--primary)' : 'var(--amber-400)',
          }}
        >
          <span className="material-symbols-outlined text-[13px]">
            {isSafe ? 'lock' : 'lock_open'}
          </span>
          <span className="text-label-caps text-[9px]">
            PROTOCOL: {isSafe ? 'SAFE MODE ACTIVE' : 'UNSAFE MODE'}
          </span>
        </div>
      </div>
    </footer>
  )
}
