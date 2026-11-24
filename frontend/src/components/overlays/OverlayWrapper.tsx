import React from 'react'

interface OverlayWrapperProps {
  title: string
  subtitle: string
  icon: string
  onClose: () => void
  children: React.ReactNode
  maxWidth?: string
}

export function OverlayWrapper({
  title,
  subtitle,
  icon,
  onClose,
  children,
  maxWidth = 'max-w-xl',
}: OverlayWrapperProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-md animate-fade-in">
      <div
        className={`w-full ${maxWidth} bg-surface-container-lowest/95 border border-primary/40 rounded-2xl shadow-2xl shadow-primary-container/20 flex flex-col max-h-[85vh] overflow-hidden`}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-primary/20 bg-surface-container-low/70">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-primary-container/20 border border-primary-container/40 flex items-center justify-center text-primary-container">
              <span className="material-symbols-outlined text-[20px]">{icon}</span>
            </div>
            <div>
              <div className="font-headline-sm text-[15px] text-primary tracking-wide">{title}</div>
              <div className="font-mono text-[11px] text-on-surface-variant">{subtitle}</div>
            </div>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-lg bg-surface-container hover:bg-error/20 hover:text-error text-on-surface-variant flex items-center justify-center transition-all border border-white/5"
            title="Close [Esc]"
          >
            <span className="material-symbols-outlined text-[18px]">close</span>
          </button>
        </div>

        {/* Content area */}
        <div className="p-5 overflow-y-auto flex-1 scrollbar-thin flex flex-col gap-4">
          {children}
        </div>
      </div>
    </div>
  )
}
