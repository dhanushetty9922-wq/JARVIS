import { motion } from 'framer-motion'
import type { VoiceState } from '../stores/jarvisStore'

interface WaveformProps {
  state: VoiceState
  bars?: number
}

export function Waveform({ state, bars = 20 }: WaveformProps) {
  const active = state === 'LISTENING' || state === 'SPEAKING'
  const color = state === 'SPEAKING' ? 'var(--green-400)'
    : state === 'LISTENING' ? 'var(--cyan-400)'
    : 'var(--border-default)'

  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      gap: 3,
      height: 36,
    }}>
      {Array.from({ length: bars }).map((_, i) => {
        const delay = (i / bars) * 0.8
        const baseHeight = 4 + Math.random() * 8
        return (
          <motion.div
            key={i}
            style={{
              width: 3,
              borderRadius: 2,
              background: color,
              originY: 1,
            }}
            animate={active ? {
              scaleY: [0.2, 0.8 + Math.random() * 0.8, 0.2],
              opacity: [0.5, 1, 0.5],
            } : {
              scaleY: 0.15,
              opacity: 0.3,
            }}
            initial={{ height: baseHeight, scaleY: 0.2 }}
            transition={active ? {
              duration: 0.5 + Math.random() * 0.5,
              delay,
              repeat: Infinity,
              ease: 'easeInOut',
            } : { duration: 0.3 }}
            // Fix: set explicit height so scaleY works
            {...{ 'data-height': baseHeight }}
          />
        )
      })}
    </div>
  )
}
