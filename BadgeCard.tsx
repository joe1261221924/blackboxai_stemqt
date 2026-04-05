import { motion } from 'framer-motion'
import type { UserBadge } from '@/types'
import { formatDate } from '@/utils/format'

interface Props {
  badge: UserBadge
  index?: number
}

const badgeIcons: Record<string, string> = {
  signup:         '🌱',
  first_lesson:   '📚',
  streak_7:       '🔥',
  perfect_score:  '⭐',
  quiz_passes:    '🏆',
  course_complete:'🎓',
  xp_100:         '⚡',
  xp_500:         '💎',
}

export function BadgeCard({ badge, index = 0 }: Props) {
  const b = badge.badge
  if (!b) return null

  const icon = badgeIcons[b.slug] ?? '🏅'

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ delay: index * 0.06, duration: 0.25 }}
      className="flex flex-col items-center gap-2 bg-surface-2 border border-[#30363d] rounded-xl p-4 text-center hover:border-brand-500/40 transition-colors"
      title={b.description}
    >
      <div className="w-12 h-12 rounded-full bg-gradient-to-br from-brand-500/20 to-accent-cyan/20 border border-brand-500/30 flex items-center justify-center text-2xl">
        {icon}
      </div>
      <div>
        <p className="text-xs font-semibold text-white leading-tight">{b.title}</p>
        <p className="text-[10px] text-[#7d8590] mt-0.5">{formatDate(badge.awarded_at)}</p>
      </div>
    </motion.div>
  )
}

export function BadgeGrid({ badges }: { badges: UserBadge[] }) {
  if (badges.length === 0) {
    return (
      <div className="text-center py-8 text-[#7d8590] text-sm">
        No badges yet. Complete lessons and quizzes to earn badges.
      </div>
    )
  }
  return (
    <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 gap-3">
      {badges.map((ub, i) => (
        <BadgeCard key={ub.id} badge={ub} index={i} />
      ))}
    </div>
  )
}
