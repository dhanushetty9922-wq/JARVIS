import { motion, AnimatePresence } from 'framer-motion'
import type { VoiceState } from '../stores/jarvisStore'

interface JarvisCoreProps {
  state: VoiceState
  size?: number
  reducedMotion?: boolean
}

const STATE_CONFIG: Record<VoiceState, {
  label: string
  color: string
  ringColor: string
  pulseSpeed: number
  glow: string
}> = {
  INITIALIZING: {
    label: 'INIT',
    color: '#94a3b8',
    ringColor: 'rgba(148,163,184,0.15)',
    pulseSpeed: 3,
    glow: '0 0 20px rgba(148,163,184,0.15)',
  },
  AWAKE: {
    label: 'AWAKE',
    color: '#00f0ff',
    ringColor: 'rgba(0,240,255,0.25)',
    pulseSpeed: 2.5,
    glow: '0 0 35px rgba(0,240,255,0.3)',
  },
  SLEEP: {
    label: 'SLEEP',
    color: '#38bdf8',
    ringColor: 'rgba(56,189,248,0.15)',
    pulseSpeed: 4.5,
    glow: '0 0 25px rgba(56,189,248,0.15)',
  },
  SLEEPING: {
    label: 'STANDBY',
    color: '#38bdf8',
    ringColor: 'rgba(56,189,248,0.15)',
    pulseSpeed: 4,
    glow: '0 0 30px rgba(56,189,248,0.15)',
  },
  LISTENING: {
    label: 'LISTENING',
    color: '#22d3ee',
    ringColor: 'rgba(34,211,238,0.3)',
    pulseSpeed: 1.2,
    glow: '0 0 40px rgba(34,211,238,0.35), 0 0 80px rgba(34,211,238,0.12)',
  },
  THINKING: {
    label: 'THINKING',
    color: '#a855f7',
    ringColor: 'rgba(168,85,247,0.25)',
    pulseSpeed: 0.8,
    glow: '0 0 40px rgba(168,85,247,0.35)',
  },
  PROCESSING: {
    label: 'THINKING',
    color: '#60a5fa',
    ringColor: 'rgba(96,165,250,0.25)',
    pulseSpeed: 0.8,
    glow: '0 0 40px rgba(96,165,250,0.35)',
  },
  SPEAKING: {
    label: 'SPEAKING',
    color: '#4ade80',
    ringColor: 'rgba(74,222,128,0.25)',
    pulseSpeed: 1.5,
    glow: '0 0 40px rgba(74,222,128,0.3)',
  },
  EXECUTING: {
    label: 'EXECUTING',
    color: '#7bd1fa',
    ringColor: 'rgba(123,209,250,0.25)',
    pulseSpeed: 1.0,
    glow: '0 0 40px rgba(123,209,250,0.3)',
  },
  MIC_DISABLED: {
    label: 'MIC MUTED',
    color: '#f59e0b',
    ringColor: 'rgba(245,158,11,0.2)',
    pulseSpeed: 5,
    glow: '0 0 25px rgba(245,158,11,0.2)',
  },
  ERROR: {
    label: 'ERROR',
    color: '#f87171',
    ringColor: 'rgba(248,113,113,0.25)',
    pulseSpeed: 0.6,
    glow: '0 0 40px rgba(248,113,113,0.35)',
  },
}

export function JarvisCore({ state, size = 200, reducedMotion = false }: JarvisCoreProps) {
  const cfg = STATE_CONFIG[state] ?? STATE_CONFIG.SLEEPING
  const cx = size / 2
  const r = size * 0.38
  const dur = (s: number) => (reducedMotion ? 0 : s)

  return (
    <div style={{ position: 'relative', width: size, height: size }} aria-label={`JARVIS state: ${cfg.label}`}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} style={{ overflow: 'visible' }}>
        {/* Outer glow ring */}
        <motion.circle
          cx={cx} cy={cx} r={r * 1.35}
          fill="none"
          stroke={cfg.ringColor}
          strokeWidth={1}
          initial={{ opacity: 0 }}
          animate={{ opacity: [0.3, 0.8, 0.3], scale: [1, 1.05, 1] }}
          transition={{ duration: dur(cfg.pulseSpeed * 2), repeat: Infinity, ease: 'easeInOut' }}
        />

        {/* Rotating outer ring */}
        <motion.g
          animate={{ rotate: reducedMotion ? 0 : 360 }}
          transition={{ duration: dur(8), repeat: Infinity, ease: 'linear' }}
          style={{ originX: `${cx}px`, originY: `${cx}px`, transformOrigin: `${cx}px ${cx}px` }}
        >
          {[0, 60, 120, 180, 240, 300].map((deg, i) => {
            const rad = (deg * Math.PI) / 180
            const x = cx + r * 1.18 * Math.cos(rad)
            const y = cx + r * 1.18 * Math.sin(rad)
            return (
              <motion.circle
                key={i}
                cx={x} cy={y} r={2.5}
                fill={cfg.color}
                opacity={0.7}
                animate={{ opacity: [0.4, 1, 0.4] }}
                transition={{ duration: dur(1.5), delay: i * 0.25, repeat: Infinity }}
              />
            )
          })}
        </motion.g>

        {/* Counter-rotating inner ring */}
        <motion.g
          animate={{ rotate: reducedMotion ? 0 : -360 }}
          transition={{ duration: dur(12), repeat: Infinity, ease: 'linear' }}
          style={{ originX: `${cx}px`, originY: `${cx}px`, transformOrigin: `${cx}px ${cx}px` }}
        >
          <circle cx={cx} cy={cx} r={r * 0.88} fill="none" stroke={cfg.ringColor} strokeWidth={1} strokeDasharray="6 14" />
        </motion.g>

        {/* Mid ring */}
        <motion.circle
          cx={cx} cy={cx} r={r * 0.7}
          fill="none"
          stroke={cfg.color}
          strokeWidth={0.5}
          opacity={0.25}
          animate={{ rotate: reducedMotion ? 0 : 360 }}
          transition={{ duration: dur(20), repeat: Infinity, ease: 'linear' }}
        />

        {/* Main circle */}
        <motion.circle
          cx={cx} cy={cx} r={r}
          fill={`rgba(10,14,26,0.95)`}
          stroke={cfg.color}
          strokeWidth={1.5}
          filter={`drop-shadow(${cfg.glow})`}
          animate={{ opacity: state === 'ERROR' ? [1, 0.6, 1] : 1 }}
          transition={{ duration: dur(0.5), repeat: state === 'ERROR' ? Infinity : 0 }}
        />

        {/* Reactor core */}
        <motion.circle
          cx={cx} cy={cx} r={r * 0.25}
          fill={cfg.color}
          opacity={0.9}
          animate={{
            scale: state === 'LISTENING' ? [1, 1.2, 1] : state === 'SPEAKING' ? [1, 1.3, 0.9, 1.1, 1] : [1, 1.04, 1],
            opacity: [0.7, 1, 0.7],
          }}
          transition={{ duration: dur(cfg.pulseSpeed), repeat: Infinity, ease: 'easeInOut' }}
        />

        {/* Inner highlight */}
        <motion.circle
          cx={cx - r * 0.08} cy={cx - r * 0.08} r={r * 0.1}
          fill="rgba(255,255,255,0.25)"
          animate={{ opacity: [0.2, 0.5, 0.2] }}
          transition={{ duration: dur(2), repeat: Infinity }}
        />

        {/* Scan line (LISTENING / PROCESSING) */}
        <AnimatePresence>
          {(state === 'LISTENING' || state === 'PROCESSING') && !reducedMotion && (
            <motion.line
              key="scan"
              x1={cx - r} y1={cx} x2={cx + r} y2={cx}
              stroke={cfg.color}
              strokeWidth={0.8}
              opacity={0.4}
              initial={{ y: cx - r, opacity: 0 }}
              animate={{ y: [cx - r, cx + r], opacity: [0, 0.5, 0] }}
              exit={{ opacity: 0 }}
              transition={{ duration: dur(1.5), repeat: Infinity, ease: 'easeInOut' }}
            />
          )}
        </AnimatePresence>
      </svg>

      {/* State label */}
      <div style={{
        position: 'absolute',
        bottom: -28,
        left: 0,
        right: 0,
        textAlign: 'center',
        fontSize: '0.65rem',
        fontWeight: 700,
        letterSpacing: '0.18em',
        color: cfg.color,
        textShadow: `0 0 12px ${cfg.color}`,
        fontFamily: 'JetBrains Mono, monospace',
      }}>
        {cfg.label}
      </div>
    </div>
  )
}
