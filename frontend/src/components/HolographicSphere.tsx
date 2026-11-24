import { useEffect, useRef, useState } from 'react'
import { motion } from 'framer-motion'

export type AssistantVisualState =
  | 'STANDBY'
  | 'AWAKE'
  | 'SLEEP'
  | 'LISTENING'
  | 'THINKING'
  | 'SPEAKING'
  | 'EXECUTING'
  | 'MIC_DISABLED'
  | 'ERROR'
  | 'DISCONNECTED'

interface HolographicSphereProps {
  state: AssistantVisualState
  size?: number
  audioLevel?: number // 0.0 to 1.0 for dynamic voice reactivity
  onStateSelect?: (state: AssistantVisualState) => void
  reducedMotion?: boolean
}

// State color schemes & kinematics
const STATE_THEMES: Record<AssistantVisualState, {
  label: string
  coreColor: string
  glowColor: string
  secondaryColor: string
  ringSpeed: number
  pulseSpeed: number
  bracketTop: string
  bracketBottom: string
  harmonics: string
}> = {
  STANDBY: {
    label: 'STANDBY',
    coreColor: '#00f0ff',
    glowColor: 'rgba(0, 240, 255, 0.45)',
    secondaryColor: '#bdc2ff',
    ringSpeed: 24,
    pulseSpeed: 3.5,
    bracketTop: 'REACTOR::STANDBY',
    bracketBottom: 'OUTPUT: 99.8%',
    harmonics: '432.09 Hz ACTIVE',
  },
  AWAKE: {
    label: 'AWAKE',
    coreColor: '#00f0ff',
    glowColor: 'rgba(0, 240, 255, 0.55)',
    secondaryColor: '#7df4ff',
    ringSpeed: 20,
    pulseSpeed: 2.5,
    bracketTop: 'AGENT::AWAKE',
    bracketBottom: 'COMMAND READY',
    harmonics: '432.09 Hz ACTIVE',
  },
  SLEEP: {
    label: 'SLEEP',
    coreColor: '#38bdf8',
    glowColor: 'rgba(56, 189, 248, 0.25)',
    secondaryColor: '#1e293b',
    ringSpeed: 45,
    pulseSpeed: 5.0,
    bracketTop: 'ACOUSTIC::STANDBY',
    bracketBottom: 'WAKE: "JARVIS"',
    harmonics: 'LOW POWER LISTENING',
  },
  MIC_DISABLED: {
    label: 'MIC MUTED',
    coreColor: '#f59e0b',
    glowColor: 'rgba(245, 158, 11, 0.35)',
    secondaryColor: '#78350f',
    ringSpeed: 60,
    pulseSpeed: 6.0,
    bracketTop: 'MIC_STREAM::HALTED',
    bracketBottom: 'CAPTURE: MUTED',
    harmonics: 'ZERO SENSOR FEED',
  },
  LISTENING: {
    label: 'LISTENING',
    coreColor: '#00f0ff',
    glowColor: 'rgba(0, 240, 255, 0.7)',
    secondaryColor: '#7df4ff',
    ringSpeed: 10,
    pulseSpeed: 1.2,
    bracketTop: 'MIC_STREAM::CAPTURE',
    bracketBottom: 'BUFFER: 48kHz FLAC',
    harmonics: 'ACOUSTIC SENSING',
  },
  THINKING: {
    label: 'THINKING',
    coreColor: '#a855f7',
    glowColor: 'rgba(168, 85, 247, 0.65)',
    secondaryColor: '#00f0ff',
    ringSpeed: 6,
    pulseSpeed: 0.9,
    bracketTop: 'NEURAL::COMPUTE',
    bracketBottom: 'LATENCY: 12ms',
    harmonics: 'SYNAPSE BURST',
  },
  SPEAKING: {
    label: 'SPEAKING',
    coreColor: '#00f0ff',
    glowColor: 'rgba(0, 240, 255, 0.8)',
    secondaryColor: '#38bdf8',
    ringSpeed: 14,
    pulseSpeed: 1.1,
    bracketTop: 'DSP_VOICE::SYNTHESIS',
    bracketBottom: 'SPATIAL 7.1 ATMOS',
    harmonics: 'MODULATION: ACTIVE',
  },
  EXECUTING: {
    label: 'EXECUTING',
    coreColor: '#7bd1fa',
    glowColor: 'rgba(123, 209, 250, 0.6)',
    secondaryColor: '#00f0ff',
    ringSpeed: 8,
    pulseSpeed: 1.4,
    bracketTop: 'SYSTEM_CALL::DISPATCH',
    bracketBottom: 'SANDBOX: LEVEL 3',
    harmonics: 'EXECUTION PIPELINE',
  },
  ERROR: {
    label: 'ERROR',
    coreColor: '#ffb4ab',
    glowColor: 'rgba(255, 180, 171, 0.65)',
    secondaryColor: '#ef4444',
    ringSpeed: 30,
    pulseSpeed: 0.7,
    bracketTop: 'FAULT::DETECTED',
    bracketBottom: 'AUTO_ISOLATED',
    harmonics: 'TELEMETRY WARN',
  },
  DISCONNECTED: {
    label: 'DISCONNECTED',
    coreColor: '#6c7886',
    glowColor: 'rgba(108, 120, 134, 0.25)',
    secondaryColor: '#353943',
    ringSpeed: 60,
    pulseSpeed: 5,
    bracketTop: 'KERNEL::OFFLINE',
    bracketBottom: 'LINK: SEVERED',
    harmonics: 'NO CARRIER',
  },
}

export function HolographicSphere({
  state,
  size = 400,
  audioLevel = 0.5,
  onStateSelect,
  reducedMotion = false,
}: HolographicSphereProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null)
  const theme = STATE_THEMES[state] || STATE_THEMES.STANDBY

  // Responsive sizing: 340px for 1366x768 screens, up to 400px for 1080p
  const [effectiveSize, setEffectiveSize] = useState(() => {
    if (typeof window !== 'undefined') {
      return window.innerHeight < 820 ? 330 : size
    }
    return size
  })

  useEffect(() => {
    const handleResize = () => {
      if (typeof window !== 'undefined') {
        setEffectiveSize(window.innerHeight < 820 ? 330 : size)
      }
    }
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [size])

  // Canvas particle / circuit sphere rendering
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    let animationFrameId: number
    let angle = 0
    const dpr = window.devicePixelRatio || 1
    canvas.width = effectiveSize * dpr
    canvas.height = effectiveSize * dpr
    ctx.scale(dpr, dpr)

    // Generate static point cloud on 3D sphere surface
    const numPoints = 140
    const points: { x: number; y: number; z: number; size: number }[] = []
    const radius = effectiveSize * 0.22

    for (let i = 0; i < numPoints; i++) {
      const phi = Math.acos(-1 + (2 * i) / numPoints)
      const theta = Math.sqrt(numPoints * Math.PI) * phi
      points.push({
        x: radius * Math.cos(theta) * Math.sin(phi),
        y: radius * Math.sin(theta) * Math.sin(phi),
        z: radius * Math.cos(phi),
        size: Math.random() * 1.5 + 0.8,
      })
    }

    const render = () => {
      ctx.clearRect(0, 0, effectiveSize, effectiveSize)
      const cx = effectiveSize / 2
      const cy = effectiveSize / 2

      // Rotation speed depends on assistant state (slowest during SLEEP to conserve CPU)
      const rotationSpeed = reducedMotion ? 0 : state === 'SLEEP' ? 0.002 : 0.008 * (24 / theme.ringSpeed)
      angle += rotationSpeed

      const cosY = Math.cos(angle)
      const sinY = Math.sin(angle)
      const cosX = Math.cos(angle * 0.4)
      const sinX = Math.sin(angle * 0.4)

      // Dynamic reactive scale when speaking/listening
      const dynamicScale = state === 'SPEAKING' || state === 'LISTENING'
        ? 1 + Math.sin(angle * 6) * 0.05 * audioLevel
        : 1

      // Render connected lines & particle nodes
      ctx.lineWidth = 0.6
      for (let i = 0; i < points.length; i++) {
        const p = points[i]

        // 3D Rotation Math
        const x1 = p.x * cosY - p.z * sinY
        const z1 = p.z * cosY + p.x * sinY
        const y2 = p.y * cosX - z1 * sinX
        const z2 = z1 * cosX + p.y * sinX

        // Perspective projection
        const fov = effectiveSize * 0.8
        const perspective = fov / (fov + z2)
        const projX = cx + x1 * perspective * dynamicScale
        const projY = cy + y2 * perspective * dynamicScale
        const alpha = Math.max(0.1, (z2 + radius) / (2 * radius))

        // Draw particle node
        ctx.beginPath()
        ctx.arc(projX, projY, p.size * perspective, 0, Math.PI * 2)
        ctx.fillStyle = i % 3 === 0 ? theme.secondaryColor : theme.coreColor
        ctx.globalAlpha = alpha * 0.85
        ctx.shadowBlur = 8 * perspective
        ctx.shadowColor = theme.coreColor
        ctx.fill()

        // Draw sparse circuit connector lines to neighbors
        if (i % 4 === 0 && i + 1 < points.length) {
          const pNext = points[i + 1]
          const nx1 = pNext.x * cosY - pNext.z * sinY
          const nz1 = pNext.z * cosY + pNext.x * sinY
          const ny2 = pNext.y * cosX - nz1 * sinX
          const nz2 = nz1 * cosX + pNext.y * sinX
          const nProjX = cx + nx1 * (fov / (fov + nz2)) * dynamicScale
          const nProjY = cy + ny2 * (fov / (fov + nz2)) * dynamicScale

          ctx.beginPath()
          ctx.moveTo(projX, projY)
          ctx.lineTo(nProjX, nProjY)
          ctx.strokeStyle = theme.coreColor
          ctx.globalAlpha = alpha * 0.25
          ctx.stroke()
        }
      }

      ctx.globalAlpha = 1
      ctx.shadowBlur = 0
      animationFrameId = requestAnimationFrame(render)
    }

    render()

    return () => {
      cancelAnimationFrame(animationFrameId)
    }
  }, [effectiveSize, state, theme, reducedMotion, audioLevel])

  // Radial equalizer spike angles (24 spikes)
  const spikes = Array.from({ length: 24 }, (_, i) => i * 15)

  return (
    <div className="relative flex flex-col items-center justify-center select-none" style={{ width: '100%', maxWidth: 720 }}>
      {/* Top Floating Vector Telemetry */}
      <div className="w-full flex items-center justify-between px-6 py-1 text-on-surface-variant/70 text-label-caps pointer-events-none">
        <div className="flex flex-col items-start gap-0.5">
          <span className="text-primary-container tracking-widest">[RESONANCE VECTOR]</span>
          <span className="text-on-surface text-[11px] font-mono">AZIMUTH: 042.88° // EL: +18.2°</span>
        </div>
        <div className="flex flex-col items-end gap-0.5">
          <span className="text-secondary tracking-widest">[NEURAL SYNC]</span>
          <span className="text-on-surface text-[11px] font-mono">{theme.harmonics}</span>
        </div>
      </div>

      {/* Main Hologram Stage Container */}
      <div
        className="relative flex items-center justify-center my-1"
        style={{ width: effectiveSize, height: effectiveSize }}
      >
        {/* Outer Static Compass HUD Ring with Cardinal Ticks & Degree Markings */}
        <svg
          className="absolute inset-0 w-full h-full pointer-events-none"
          viewBox="0 0 500 500"
          fill="none"
        >
          {/* Outer Dashed Orbit */}
          <circle
            cx="250"
            cy="250"
            r="238"
            stroke="var(--border-default)"
            strokeDasharray="4 8"
            strokeWidth="1"
          />
          {/* Inner Precision Guide */}
          <circle
            cx="250"
            cy="250"
            r="228"
            stroke="var(--border-subtle)"
            strokeWidth="0.75"
            opacity="0.5"
          />

          {/* Cardinal Ticks */}
          <line x1="250" y1="4" x2="250" y2="24" stroke="var(--primary-container)" strokeWidth="2" />
          <line x1="250" y1="476" x2="250" y2="496" stroke="var(--primary-container)" strokeWidth="2" />
          <line x1="4" y1="250" x2="24" y2="250" stroke="var(--primary-container)" strokeWidth="2" />
          <line x1="476" y1="250" x2="496" y2="250" stroke="var(--primary-container)" strokeWidth="2" />

          {/* Sub-cardinal Tick Marks */}
          {[45, 135, 225, 315].map((deg) => {
            const rad = (deg * Math.PI) / 180
            const x1 = 250 + 234 * Math.cos(rad)
            const y1 = 250 + 234 * Math.sin(rad)
            const x2 = 250 + 242 * Math.cos(rad)
            const y2 = 250 + 242 * Math.sin(rad)
            return (
              <line
                key={deg}
                x1={x1}
                y1={y1}
                x2={x2}
                y2={y2}
                stroke="var(--border-accent)"
                strokeWidth="1"
              />
            )
          })}

          {/* Cardinal Degree Indicator Labels */}
          <text x="254" y="20" fill="var(--primary-container)" fontFamily="JetBrains Mono" fontSize="9" letterSpacing="2">000°</text>
          <text x="466" y="246" fill="var(--primary-container)" fontFamily="JetBrains Mono" fontSize="9">090°</text>
          <text x="254" y="492" fill="var(--primary-container)" fontFamily="JetBrains Mono" fontSize="9">180°</text>
          <text x="8" y="246" fill="var(--primary-container)" fontFamily="JetBrains Mono" fontSize="9">270°</text>
        </svg>

        {/* Dynamic 2D Counter-Rotating Orbital Rings */}
        <motion.div
          className="absolute inset-4 rounded-full border border-primary-container/25 border-dashed pointer-events-none"
          animate={{ rotate: reducedMotion ? 0 : 360 }}
          transition={{ duration: theme.ringSpeed * 1.5, repeat: Infinity, ease: 'linear' }}
        />
        <motion.div
          className="absolute inset-8 rounded-full border border-secondary/25 border-dotted pointer-events-none"
          animate={{ rotate: reducedMotion ? 0 : -360 }}
          transition={{ duration: theme.ringSpeed, repeat: Infinity, ease: 'linear' }}
        />

        {/* Multi-Axis Hologram 3D Perspective Rings */}
        <div
          className="absolute inset-14 rounded-full border border-primary-container/40 pointer-events-none"
          style={{
            transformStyle: 'preserve-3d',
            transform: 'rotateX(65deg) rotateY(25deg)',
            animation: reducedMotion ? 'none' : `spin ${theme.ringSpeed * 0.8}s ease-in-out infinite`,
          }}
        />
        <div
          className="absolute inset-14 rounded-full border border-secondary/40 pointer-events-none"
          style={{
            transformStyle: 'preserve-3d',
            transform: 'rotateX(-50deg) rotateY(40deg)',
            animation: reducedMotion ? 'none' : `spin ${theme.ringSpeed * 0.9}s ease-in-out infinite reverse`,
          }}
        />
        <div
          className="absolute inset-20 rounded-full border border-primary/20 pointer-events-none"
          style={{
            transformStyle: 'preserve-3d',
            transform: 'rotateX(20deg) rotateY(-60deg)',
            animation: reducedMotion ? 'none' : `spin ${theme.ringSpeed * 0.5}s linear infinite`,
          }}
        />

        {/* Radial Audio Reactive Waveform Spikes */}
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <div className="relative w-64 h-64 sm:w-80 sm:h-80 flex items-center justify-center">
            {spikes.map((deg, i) => {
              const isCyan = i % 2 === 0
              const isPulse = state === 'SPEAKING' || state === 'LISTENING'
              const heightMultiplier = isPulse
                ? (Math.sin((i + deg) * 0.4) * 0.5 + 0.5) * (audioLevel + 0.4)
                : 0.3
              const spikeHeight = 12 + heightMultiplier * 26

              return (
                <div
                  key={deg}
                  className="absolute inset-0 flex items-center justify-center"
                  style={{ transform: `rotate(${deg}deg)` }}
                >
                  <motion.span
                    className="w-0.5 rounded-none"
                    style={{
                      height: `${spikeHeight}px`,
                      backgroundColor: isCyan ? theme.coreColor : theme.secondaryColor,
                      boxShadow: isCyan ? `0 0 8px ${theme.coreColor}` : `0 0 6px ${theme.secondaryColor}`,
                      transform: `translateY(-${Math.round(effectiveSize * 0.34)}px)`,
                    }}
                    animate={isPulse ? { opacity: [0.4, 1, 0.4] } : { opacity: 0.35 }}
                    transition={{
                      duration: 0.8,
                      delay: (i * 0.05) % 0.8,
                      repeat: Infinity,
                      ease: 'easeInOut',
                    }}
                  />
                </div>
              )
            })}
          </div>
        </div>

        {/* Canvas Holographic Particle & Circuit Mesh */}
        <canvas
          ref={canvasRef}
          className="absolute inset-0 pointer-events-none z-10"
          style={{ width: effectiveSize, height: effectiveSize }}
        />

        {/* The Central Arc Reactor Energy Core */}
        <motion.div
          className="relative rounded-full flex items-center justify-center z-20 cursor-pointer shadow-2xl transition-transform duration-500 hover:scale-105"
          style={{
            width: effectiveSize * 0.34,
            height: effectiveSize * 0.34,
            background: 'radial-gradient(circle at 35% 35%, #1c2333, #0a0e17 80%)',
            boxShadow: `0 0 50px ${theme.glowColor}, inset 0 0 24px rgba(0, 240, 255, 0.35)`,
            border: `1px solid ${theme.coreColor}40`,
          }}
          animate={
            reducedMotion
              ? {}
              : {
                  boxShadow: [
                    `0 0 35px ${theme.glowColor}, inset 0 0 20px rgba(0, 240, 255, 0.25)`,
                    `0 0 65px ${theme.glowColor}, inset 0 0 32px rgba(0, 240, 255, 0.55)`,
                    `0 0 35px ${theme.glowColor}, inset 0 0 20px rgba(0, 240, 255, 0.25)`,
                  ],
                }
          }
          transition={{ duration: theme.pulseSpeed, repeat: Infinity, ease: 'easeInOut' }}
        >
          {/* Inner Translucent Glow Bubble */}
          <div
            className="absolute inset-2 rounded-full backdrop-blur-md opacity-80"
            style={{
              background: `radial-gradient(circle, ${theme.coreColor}25 0%, ${theme.secondaryColor}15 70%, transparent 100%)`,
            }}
          />

          {/* Central Core Emblem */}
          <div
            className="relative w-16 h-16 sm:w-20 sm:h-20 rounded-full flex items-center justify-center"
            style={{
              background: `radial-gradient(circle, var(--primary) 0%, ${theme.coreColor}40 50%, transparent 100%)`,
              boxShadow: `inset 0 0 16px ${theme.coreColor}`,
            }}
          >
            {/* Core Neural Icon */}
            <span
              className="material-symbols-outlined text-[32px] sm:text-[38px]"
              style={{
                color: theme.coreColor,
                filter: `drop-shadow(0 0 10px ${theme.coreColor})`,
              }}
            >
              {state === 'ERROR'
                ? 'warning'
                : state === 'THINKING'
                ? 'psychology'
                : state === 'LISTENING'
                ? 'mic'
                : state === 'SPEAKING'
                ? 'graphic_eq'
                : state === 'EXECUTING'
                ? 'terminal'
                : state === 'MIC_DISABLED'
                ? 'mic_off'
                : state === 'SLEEP'
                ? 'bedtime'
                : state === 'AWAKE'
                ? 'smart_toy'
                : 'token'}
            </span>

            {/* Orbiting Quantum Micro Particle */}
            <motion.div
              className="absolute -top-1 left-1/2 w-2 h-2 rounded-full"
              style={{
                backgroundColor: 'var(--primary)',
                boxShadow: `0 0 8px #ffffff, 0 0 16px ${theme.coreColor}`,
              }}
              animate={{ rotate: 360 }}
              transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
            />
          </div>

          {/* Hexagonal HUD Telemetry Brackets */}
          <div
            className="absolute -top-3 px-2 py-0.5 rounded text-label-caps border-t"
            style={{
              background: 'var(--surface-high)',
              color: theme.coreColor,
              borderColor: `${theme.coreColor}80`,
              fontSize: '9px',
              letterSpacing: '0.14em',
            }}
          >
            {theme.bracketTop}
          </div>
          <div
            className="absolute -bottom-3 px-2 py-0.5 rounded text-label-caps border-b"
            style={{
              background: 'var(--surface-high)',
              color: theme.secondaryColor,
              borderColor: `${theme.secondaryColor}80`,
              fontSize: '9px',
              letterSpacing: '0.14em',
            }}
          >
            {theme.bracketBottom}
          </div>
        </motion.div>

        {/* 3D Holographic Perspective Platform Base */}
        <div
          className="absolute -bottom-10 w-3/4 h-16 pointer-events-none opacity-60"
          style={{
            perspective: 600,
            transformStyle: 'preserve-3d',
          }}
        >
          <div
            className="w-full h-full rounded-full"
            style={{
              transform: 'rotateX(75deg)',
              background: `radial-gradient(ellipse at center, ${theme.coreColor}35 0%, ${theme.secondaryColor}15 45%, transparent 75%)`,
              border: `1px solid ${theme.coreColor}40`,
              boxShadow: `0 0 30px ${theme.glowColor}`,
            }}
          />
        </div>
      </div>

      {/* Assistant State Ribbon Selector */}
      <div
        className="mt-3 flex flex-wrap items-center justify-center gap-1 sm:gap-2 p-1.5 rounded-full backdrop-blur-2xl shadow-2xl z-30"
        style={{
          background: 'rgba(10, 14, 23, 0.85)',
          border: '1px solid var(--border-subtle)',
        }}
      >
        {(['STANDBY', 'LISTENING', 'THINKING', 'SPEAKING', 'EXECUTING'] as AssistantVisualState[]).map((st) => {
          const isActive = state === st
          const stTheme = STATE_THEMES[st]

          return (
            <button
              key={st}
              onClick={() => onStateSelect && onStateSelect(st)}
              className="px-3.5 py-1 rounded-full text-label-caps transition-all flex items-center gap-1.5"
              style={{
                background: isActive ? `${stTheme.coreColor}20` : 'transparent',
                color: isActive ? stTheme.coreColor : 'var(--text-dim)',
                boxShadow: isActive ? `0 0 16px ${stTheme.glowColor}` : 'none',
                border: isActive ? `1px solid ${stTheme.coreColor}60` : '1px solid transparent',
                cursor: onStateSelect ? 'pointer' : 'default',
              }}
            >
              <span
                className="w-1.5 h-1.5 rounded-full"
                style={{
                  backgroundColor: isActive ? stTheme.coreColor : 'var(--text-dim)',
                  boxShadow: isActive ? `0 0 6px ${stTheme.coreColor}` : 'none',
                }}
              />
              <span>{st}</span>
              {st === 'SPEAKING' && isActive && (
                <div className="flex items-center gap-0.5 h-2.5 ml-0.5">
                  <span className="w-0.5 h-2 bg-primary-container animate-pulse" />
                  <span className="w-0.5 h-3 bg-primary-container animate-pulse" style={{ animationDelay: '150ms' }} />
                  <span className="w-0.5 h-1.5 bg-primary-container animate-pulse" style={{ animationDelay: '300ms' }} />
                </div>
              )}
            </button>
          )
        })}
      </div>
    </div>
  )
}
