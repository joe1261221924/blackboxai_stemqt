import { motion } from 'framer-motion'

// ── Loading spinner ────────────────────────────────────────────────────────

export function LoadingSpinner({ size = 'md' }: { size?: 'sm' | 'md' | 'lg' }) {
  const sizes = { sm: 'w-5 h-5', md: 'w-8 h-8', lg: 'w-12 h-12' }
  return (
    <div className={`${sizes[size]} border-2 border-brand-500 border-t-transparent rounded-full animate-spin`} />
  )
}

export function PageLoader() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[40vh] gap-4">
      <LoadingSpinner size="lg" />
      <p className="text-sm text-[#7d8590]">Loading...</p>
    </div>
  )
}

// ── Error message ──────────────────────────────────────────────────────────

interface ErrorMessageProps {
  message?:  string
  retry?:    () => void
}

export function ErrorMessage({ message = 'Something went wrong.', retry }: ErrorMessageProps) {
  return (
    <div className="flex flex-col items-center gap-4 py-16 px-4 text-center">
      <div className="w-12 h-12 rounded-full bg-accent-rose/10 border border-accent-rose/20 flex items-center justify-center">
        <svg className="w-6 h-6 text-accent-rose" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
      </div>
      <div>
        <p className="text-white font-semibold">Error</p>
        <p className="text-sm text-[#7d8590] mt-1 max-w-sm">{message}</p>
      </div>
      {retry && (
        <button onClick={retry} className="btn-secondary text-sm">
          Try again
        </button>
      )}
    </div>
  )
}

// ── Empty state ────────────────────────────────────────────────────────────

export function EmptyState({ message, icon }: { message: string; icon?: React.ReactNode }) {
  return (
    <div className="flex flex-col items-center gap-3 py-12 text-center">
      {icon && (
        <div className="w-12 h-12 rounded-full bg-surface-3 flex items-center justify-center text-[#7d8590]">
          {icon}
        </div>
      )}
      <p className="text-sm text-[#7d8590]">{message}</p>
    </div>
  )
}

// ── Page wrapper with fade-in ──────────────────────────────────────────────

export function PageWrapper({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
      className={`max-w-7xl mx-auto px-4 sm:px-6 py-8 ${className}`}
    >
      {children}
    </motion.div>
  )
}

// ── Section header ─────────────────────────────────────────────────────────

export function SectionHeader({ title, sub, action }: { title: string; sub?: string; action?: React.ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-4 mb-6">
      <div>
        <h2 className="section-heading">{title}</h2>
        {sub && <p className="text-sm text-[#7d8590] mt-1">{sub}</p>}
      </div>
      {action && <div className="flex-shrink-0">{action}</div>}
    </div>
  )
}

// ── Alert / toast-style banner ─────────────────────────────────────────────

type AlertVariant = 'success' | 'error' | 'info' | 'warning'

const alertStyles: Record<AlertVariant, string> = {
  success: 'bg-brand-500/10 border-brand-500/30 text-brand-400',
  error:   'bg-accent-rose/10 border-accent-rose/30 text-accent-rose',
  info:    'bg-accent-cyan/10 border-accent-cyan/30 text-accent-cyan',
  warning: 'bg-accent-amber/10 border-accent-amber/30 text-accent-amber',
}

export function Alert({ variant = 'info', message }: { variant?: AlertVariant; message: string }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      className={`rounded-xl border px-4 py-3 text-sm font-medium ${alertStyles[variant]}`}
    >
      {message}
    </motion.div>
  )
}

// ── Skeleton loader ────────────────────────────────────────────────────────

export function SkeletonCard() {
  return (
    <div className="card space-y-4">
      <div className="skeleton w-full aspect-video rounded-lg" />
      <div className="space-y-2">
        <div className="skeleton h-4 w-3/4 rounded" />
        <div className="skeleton h-3 w-full rounded" />
        <div className="skeleton h-3 w-5/6 rounded" />
      </div>
    </div>
  )
}

export function SkeletonList({ rows = 4 }: { rows?: number }) {
  return (
    <div className="space-y-3">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="card flex items-center gap-4">
          <div className="skeleton w-10 h-10 rounded-full flex-shrink-0" />
          <div className="flex-1 space-y-2">
            <div className="skeleton h-4 w-1/3 rounded" />
            <div className="skeleton h-3 w-2/3 rounded" />
          </div>
        </div>
      ))}
    </div>
  )
}

// ── Reward popup ───────────────────────────────────────────────────────────

interface RewardPopupProps {
  xpAwarded:  number
  newBadges:  Array<{ title: string }>
  onClose:    () => void
}

export function RewardPopup({ xpAwarded, newBadges, onClose }: RewardPopupProps) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.85 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.85 }}
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
      onClick={onClose}
    >
      <motion.div
        initial={{ y: 20 }}
        animate={{ y: 0 }}
        className="bg-surface-1 border border-brand-500/40 rounded-2xl p-8 max-w-sm w-full text-center shadow-2xl glow-green"
        onClick={e => e.stopPropagation()}
      >
        <div className="text-5xl mb-4">🎉</div>
        <h3 className="text-xl font-bold text-white mb-2">Well done!</h3>
        {xpAwarded > 0 && (
          <div className="flex items-center justify-center gap-2 mb-4">
            <div className="badge-pill bg-brand-500/20 text-brand-400 border border-brand-500/30 text-base px-4 py-1">
              +{xpAwarded} XP
            </div>
          </div>
        )}
        {newBadges.length > 0 && (
          <div className="mt-3">
            <p className="text-sm text-[#7d8590] mb-2">New badge{newBadges.length > 1 ? 's' : ''} unlocked:</p>
            <div className="flex flex-wrap justify-center gap-2">
              {newBadges.map(b => (
                <span key={b.title} className="badge-pill bg-accent-amber/10 text-accent-amber border border-accent-amber/20">
                  {b.title}
                </span>
              ))}
            </div>
          </div>
        )}
        <button onClick={onClose} className="btn-primary mt-6 w-full">Continue</button>
      </motion.div>
    </motion.div>
  )
}
