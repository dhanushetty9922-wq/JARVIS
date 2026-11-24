import { OverlayWrapper } from './OverlayWrapper'

interface AutomationOverlayProps {
  onClose: () => void
}

const AUTOMATIONS = [
  {
    id: 'briefing',
    title: 'Daily Morning Briefing',
    schedule: '08:00 AM Daily',
    desc: 'Summarizes weather, system telemetry, and upcoming calendar appointments.',
    status: 'ACTIVE',
  },
  {
    id: 'cleanup',
    title: 'Automated Cache & Temp Cleanup',
    schedule: 'Every 6 Hours',
    desc: 'Purges unindexed temporary audio clips and expired logs safely.',
    status: 'IDLE',
  },
  {
    id: 'health',
    title: 'Hardware S.M.A.R.T & Health Monitor',
    schedule: 'Every 30 Minutes',
    desc: 'Tracks CPU thermal dissipation and RAM saturation thresholds.',
    status: 'ACTIVE',
  },
]

export function AutomationOverlay({ onClose }: AutomationOverlayProps) {
  return (
    <OverlayWrapper
      title="AUTOMATION PROTOCOLS"
      subtitle="BACKGROUND DAEMONS & SCHEDULED ROUTINES"
      icon="bolt"
      onClose={onClose}
    >
      <div className="flex flex-col gap-3">
        {AUTOMATIONS.map((task) => (
          <div
            key={task.id}
            className="p-4 rounded-xl bg-surface-container/60 border border-white/5 hover:border-primary/30 transition-all flex flex-col gap-2"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-primary-container text-[20px]">
                  schedule
                </span>
                <span className="font-headline-sm text-[14px] text-primary">{task.title}</span>
              </div>
              <span
                className={`font-label-caps text-[10px] px-2 py-0.5 rounded border ${
                  task.status === 'ACTIVE'
                    ? 'bg-primary-container/15 text-primary-container border-primary-container/40'
                    : 'bg-surface-container-high text-on-surface-variant border-white/5'
                }`}
              >
                {task.status}
              </span>
            </div>
            <p className="font-body-sm text-[12px] text-on-surface-variant">{task.desc}</p>
            <div className="flex items-center justify-between pt-2 border-t border-white/5 font-telemetry-unit text-[11px] text-on-surface-variant">
              <span>SCHEDULE: {task.schedule}</span>
              <span className="text-primary-container font-mono">SANDBOXED // LOW PRIORITY</span>
            </div>
          </div>
        ))}
      </div>
    </OverlayWrapper>
  )
}
