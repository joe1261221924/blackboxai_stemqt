import { motion } from 'framer-motion'
import type { LeaderboardEntry } from '@/types'
import { formatXP } from '@/utils/format'

interface Props {
  entries:       LeaderboardEntry[]
  currentUserId?: string
}

const rankColors = ['text-accent-amber', 'text-[#7d8590]', 'text-accent-amber/60']
const rankBg     = ['bg-accent-amber/10', 'bg-[#7d8590]/10', 'bg-accent-amber/5']

export function LeaderboardSection({ entries, currentUserId }: Props) {
  if (!entries.length) {
    return (
      <div className="text-center py-8 text-[#7d8590] text-sm">
        No entries yet. Be the first to earn XP.
      </div>
    )
  }

  return (
    <div className="space-y-2">
      {entries.map((entry, i) => {
        const isMe      = entry.user_id === currentUserId
        const rankColor = rankColors[i] ?? 'text-[#7d8590]'
        const rankBgCls = rankBg[i] ?? ''

        return (
          <motion.div
            key={entry.user_id}
            initial={{ opacity: 0, x: -12 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.04 }}
            className={`flex items-center gap-3 px-4 py-3 rounded-xl border transition-colors ${
              isMe
                ? 'bg-brand-500/10 border-brand-500/30'
                : 'bg-surface-2 border-[#30363d] hover:border-[#484f58]'
            }`}
          >
            {/* Rank */}
            <div className={`w-7 h-7 rounded-lg flex items-center justify-center text-xs font-bold ${rankBgCls} ${rankColor} flex-shrink-0`}>
              {entry.rank}
            </div>

            {/* Avatar */}
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-brand-500/30 to-accent-cyan/30 border border-[#30363d] flex items-center justify-center text-xs font-bold text-white flex-shrink-0">
              {entry.avatar || entry.name[0]?.toUpperCase()}
            </div>

            {/* Name */}
            <div className="flex-1 min-w-0">
              <p className={`text-sm font-semibold truncate ${isMe ? 'text-brand-400' : 'text-white'}`}>
                {entry.name}
                {isMe && <span className="ml-1.5 text-xs font-normal text-brand-400/70">(You)</span>}
              </p>
              <div className="flex items-center gap-2 text-xs text-[#7d8590]">
                <span className="flex items-center gap-0.5">
                  <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                  </svg>
                  {entry.badge_count}
                </span>
                {entry.streak > 0 && (
                  <span className="flex items-center gap-0.5 text-accent-amber">
                    <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M12.395 2.553a1 1 0 00-1.45-.385c-.345.23-.614.558-.822.88-.214.33-.403.713-.57 1.116-.334.804-.614 1.768-.84 2.734a31.365 31.365 0 00-.613 3.58 2.64 2.64 0 01-.945-1.067c-.328-.68-.398-1.534-.398-2.654A1 1 0 005.05 6.05 6.981 6.981 0 003 11a7 7 0 1011.95-4.95c-.592-.591-.98-.985-1.348-1.467-.363-.476-.724-1.063-1.207-2.03zM12.12 15.12A3 3 0 017 13s.879.5 2.5.5c0-1 .5-4 1.25-4.5.5 1 .786 1.293 1.371 1.879A2.99 2.99 0 0113 13a2.99 2.99 0 01-.879 2.121z" clipRule="evenodd" />
                    </svg>
                    {entry.streak}d
                  </span>
                )}
              </div>
            </div>

            {/* XP */}
            <div className="text-right flex-shrink-0">
              <p className="text-sm font-bold text-white">{formatXP(entry.total_xp)}</p>
              <p className="text-xs text-[#7d8590]">XP</p>
            </div>
          </motion.div>
        )
      })}
    </div>
  )
}
