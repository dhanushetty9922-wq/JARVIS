import { Zap } from 'lucide-react'

export function AutomationPage() {
  const tasks = [
    { id: 'briefing', name: 'Daily Briefing', desc: 'Summarize news, weather, and calendar events', status: 'idle' },
    { id: 'cleanup', name: 'Temp Cleanup', desc: 'Clear approved temp folders when disk space is low', status: 'idle' },
    { id: 'reminder', name: 'Reminder Engine', desc: 'Scheduled voice reminders', status: 'idle' },
  ]

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <Zap size={20} color="var(--text-accent)" />
        <div>
          <div style={{ fontWeight: 700 }}>Automation Engine</div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>Safe, allowlisted automations only</div>
        </div>
      </div>

      {tasks.map(task => (
        <div key={task.id} className="card-accent" style={{ padding: 18 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <div>
              <div style={{ fontWeight: 600, marginBottom: 4 }}>{task.name}</div>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-dim)' }}>{task.desc}</div>
            </div>
            <span className="badge badge-cyan">
              {task.status.toUpperCase()}
            </span>
          </div>
          <div style={{ marginTop: 12, display: 'flex', gap: 8 }}>
            <button className="btn btn-ghost btn-sm" disabled>Run</button>
            <button className="btn btn-ghost btn-sm" disabled>Schedule</button>
          </div>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)', marginTop: 8 }}>
            ⚠ Requires backend automation module — coming in next phase.
          </div>
        </div>
      ))}
    </div>
  )
}
