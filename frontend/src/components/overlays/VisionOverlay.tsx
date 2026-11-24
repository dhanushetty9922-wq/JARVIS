import { OverlayWrapper } from './OverlayWrapper'

interface VisionOverlayProps {
  onClose: () => void
}

export function VisionOverlay({ onClose }: VisionOverlayProps) {
  return (
    <OverlayWrapper
      title="OPTICAL & VISION SENSOR ARRAY"
      subtitle="DESKTOP SCREEN CAPTURE & MULTIMODAL INFERENCE"
      icon="visibility"
      onClose={onClose}
    >
      <div className="flex flex-col items-center justify-center p-6 text-center rounded-xl bg-surface-container/40 border border-white/5">
        <div className="w-14 h-14 rounded-full bg-primary-container/10 border border-primary-container/30 flex items-center justify-center text-primary-container mb-3 shadow-[0_0_16px_rgba(0,240,255,0.2)]">
          <span className="material-symbols-outlined text-[28px]">center_focus_strong</span>
        </div>
        <div className="font-headline-sm text-[15px] text-primary">VISION MODULE ACTIVE & READY</div>
        <p className="font-body-sm text-[12px] text-on-surface-variant max-w-sm mt-1">
          JARVIS can analyze the active workspace or inspect captured visual context with user approval.
        </p>

        <div className="mt-4 p-3 rounded-lg bg-surface-container-high/60 border border-primary/20 text-left w-full font-mono text-[11px] text-tertiary">
          <div className="text-primary-container font-semibold mb-1">PROTOCOLS:</div>
          <div>• Zero-silent captures: Screen is only read on explicit command</div>
          <div>• Resolution: Native display framebuffer scaled for low RAM</div>
          <div>• Multimodal Engine: Gemini 3.8 Flash Vision Pipeline</div>
        </div>
      </div>
    </OverlayWrapper>
  )
}
