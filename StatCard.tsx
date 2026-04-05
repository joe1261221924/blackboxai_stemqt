import { motion } from 'framer-motion'

interface Props {
  label:    string
  value:    string | number
  sub?:     string
  icon:     React.ReactNode
  color?:   'green' | 'cyan' | 'amber' | 'rose'
  index?:   number
}

const colorMap = {
  green: {
    bg:   'bg-brand-500/10',
    icon: 'text-brand-400',
    ring: 'ring-brand-500/20',
  },
  cyan: {
    bg:   'bg-accent-cyan/10',
    icon: 'text-accent-cyan',
    ring: 'ring-accent-cyan/20',
  },
  amber: {
    bg:   'bg-accent-amber/10',
    icon: 'text-accent-amber',
    ring: 'ring-accent-amber/20',
  },
  rose: {
    bg:   'bg-accent-rose/10',
    icon: 'text-accent-rose',
    ring: 'ring-accent-rose/20',
  },
}

export function StatCard({ label, value, sub, icon, color = 'green', index = 0 }: Props) {
  const c = colorMap[color]
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.07, duration: 0.3 }}
      className="card flex items-start gap-4"
    >
      <div className={`flex-shrink-0 w-11 h-11 rounded-xl flex items-center justify-center ${c.bg} ring-1 ${c.ring}`}>
        <span className={c.icon}>{icon}</span>
      </div>
      <div className="min-w-0">
        <p className="text-sm text-[#7d8590] font-medium">{label}</p>
        <p className="text-2xl font-bold text-white mt-0.5">{value}</p>
        {sub && <p className="text-xs text-[#7d8590] mt-0.5">{sub}</p>}
      </div>
    </motion.div>
  )
}
