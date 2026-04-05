import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { useAuth } from '@/contexts/AuthContext'

const features = [
  {
    icon: (
      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M11.983 1.907a.75.75 0 00-1.292-.657l-8.5 9.5A.75.75 0 002.75 12h6.042l-1.274 7.132a.75.75 0 001.292.657l8.5-9.5A.75.75 0 0016.75 9h-6.042l1.274-7.132z" />
      </svg>
    ),
    title: 'Earn XP & Level Up',
    description: 'Every lesson you complete and quiz you pass awards experience points. Watch your rank climb the leaderboard.',
    color: 'brand',
  },
  {
    icon: (
      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M16.5 18.75h-9m9 0a3 3 0 013 3h-15a3 3 0 013-3m9 0v-3.375c0-.621-.503-1.125-1.125-1.125h-.871M7.5 18.75v-3.375c0-.621.504-1.125 1.125-1.125h.872m5.007 0H9.497m5.007 0a7.454 7.454 0 01-.982-3.172M9.497 14.25a7.454 7.454 0 00.981-3.172M5.25 4.236c-.982.143-1.954.317-2.916.52A6.003 6.003 0 007.73 9.728M5.25 4.236V4.5c0 2.108.966 3.99 2.48 5.228M5.25 4.236V2.721C7.456 2.41 9.71 2.25 12 2.25c2.291 0 4.545.16 6.75.47v1.516M7.73 9.728a6.726 6.726 0 002.748 1.35m8.272-6.842V4.5c0 2.108-.966 3.99-2.48 5.228m2.48-5.492a46.32 46.32 0 012.916.52 6.003 6.003 0 01-5.395 4.972m0 0a6.726 6.726 0 01-2.749 1.35m0 0a6.772 6.772 0 01-3.044 0" />
      </svg>
    ),
    title: 'Unlock Badges',
    description: 'From your first lesson to perfect quiz scores and weekly streaks — collect achievement badges that showcase your progress.',
    color: 'amber',
  },
  {
    icon: (
      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3.75 3v11.25A2.25 2.25 0 006 16.5h2.25M3.75 3h-1.5m1.5 0h16.5m0 0h1.5m-1.5 0v11.25A2.25 2.25 0 0118 16.5h-2.25m-7.5 0h7.5m-7.5 0l-1 3m8.5-3l1 3m0 0l.5 1.5m-.5-1.5h-9.5m0 0l-.5 1.5M9 11.25v1.5M12 9v3.75m3-6v6" />
      </svg>
    ),
    title: 'Adaptive Learning',
    description: 'Our quiz engine analyses your performance and recommends whether to review, advance, or try more challenging content.',
    color: 'cyan',
  },
  {
    icon: (
      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 19.128a9.38 9.38 0 002.625.372 9.337 9.337 0 004.121-.952 4.125 4.125 0 00-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 018.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0111.964-3.07M12 6.375a3.375 3.375 0 11-6.75 0 3.375 3.375 0 016.75 0zm8.25 2.25a2.625 2.625 0 11-5.25 0 2.625 2.625 0 015.25 0z" />
      </svg>
    ),
    title: 'Global Leaderboard',
    description: 'Compete with learners worldwide. Daily streaks, total XP, and badge counts combine for your global ranking.',
    color: 'rose',
  },
]

const colorMap: Record<string, string> = {
  brand: 'bg-brand-500/10 text-brand-400 ring-brand-500/20',
  amber: 'bg-accent-amber/10 text-accent-amber ring-accent-amber/20',
  cyan:  'bg-accent-cyan/10 text-accent-cyan ring-accent-cyan/20',
  rose:  'bg-accent-rose/10 text-accent-rose ring-accent-rose/20',
}

const subjects = [
  { label: 'Science',      icon: '🔬' },
  { label: 'Technology',   icon: '💻' },
  { label: 'Engineering',  icon: '⚙️' },
  { label: 'Mathematics',  icon: '📐' },
]

export function HomePage() {
  const { user } = useAuth()

  return (
    <div className="min-h-screen bg-surface">
      {/* ── Hero ──────────────────────────────────────────────────────── */}
      <section className="relative overflow-hidden pt-20 pb-28 px-4">
        {/* Background elements */}
        <div className="absolute inset-0 pointer-events-none">
          <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[400px] bg-brand-500/5 rounded-full blur-3xl" />
          <div className="absolute top-20 right-10 w-[300px] h-[300px] bg-accent-cyan/5 rounded-full blur-3xl" />
        </div>

        <div className="max-w-5xl mx-auto relative">
          {/* Eyebrow */}
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
            className="flex justify-center mb-6"
          >
            <span className="badge-pill bg-brand-500/10 text-brand-400 border border-brand-500/20 px-4 py-1.5 text-sm">
              Gamified STEM Learning Platform
            </span>
          </motion.div>

          {/* Headline */}
          <motion.h1
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1, duration: 0.45 }}
            className="text-center text-5xl sm:text-6xl md:text-7xl font-black tracking-tight text-balance leading-[1.05]"
          >
            Learn STEM.
            <br />
            <span className="text-gradient">Earn rewards.</span>
            <br />
            Conquer knowledge.
          </motion.h1>

          <motion.p
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2, duration: 0.4 }}
            className="mt-6 text-center text-lg text-[#7d8590] max-w-2xl mx-auto leading-relaxed text-balance"
          >
            STEMQuest turns Science, Technology, Engineering, and Mathematics into an adventure.
            Complete lessons, ace quizzes, build streaks, and climb the leaderboard.
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3, duration: 0.4 }}
            className="mt-10 flex flex-col sm:flex-row gap-4 justify-center"
          >
            {user ? (
              <>
                <Link
                  to={user.role === 'admin' ? '/admin' : '/dashboard'}
                  className="btn-primary text-base px-8 py-3"
                >
                  Go to Dashboard
                </Link>
                <Link to="/courses" className="btn-secondary text-base px-8 py-3">
                  Browse Courses
                </Link>
              </>
            ) : (
              <>
                <Link to="/register" className="btn-primary text-base px-8 py-3">
                  Start for free
                </Link>
                <Link to="/courses" className="btn-secondary text-base px-8 py-3">
                  Browse Courses
                </Link>
              </>
            )}
          </motion.div>

          {/* Subject pills */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.5 }}
            className="mt-12 flex flex-wrap justify-center gap-3"
          >
            {subjects.map(s => (
              <div
                key={s.label}
                className="flex items-center gap-2 bg-surface-1 border border-[#30363d] rounded-xl px-4 py-2 text-sm font-medium text-[#e6edf3]"
              >
                <span>{s.icon}</span>
                {s.label}
              </div>
            ))}
          </motion.div>
        </div>
      </section>

      {/* ── Stats bar ─────────────────────────────────────────────────── */}
      <section className="bg-surface-1 border-y border-[#30363d]">
        <div className="max-w-5xl mx-auto px-4 py-8 grid grid-cols-2 md:grid-cols-4 gap-6 text-center">
          {[
            { label: 'Students enrolled',   value: '1,200+' },
            { label: 'Courses available',   value: '40+'    },
            { label: 'Badges awarded',       value: '8,500+' },
            { label: 'XP earned total',      value: '2M+'    },
          ].map((stat, i) => (
            <motion.div
              key={stat.label}
              initial={{ opacity: 0, y: 8 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.07 }}
            >
              <p className="text-3xl font-black text-white">{stat.value}</p>
              <p className="text-sm text-[#7d8590] mt-1">{stat.label}</p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* ── Features ──────────────────────────────────────────────────── */}
      <section className="py-24 px-4">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-14">
            <h2 className="text-3xl md:text-4xl font-bold text-white text-balance">
              Built for the next generation of{' '}
              <span className="text-gradient">STEM leaders</span>
            </h2>
            <p className="mt-4 text-[#7d8590] max-w-xl mx-auto leading-relaxed">
              Gamification, adaptive learning, and real content combined into one powerful platform.
            </p>
          </div>

          <div className="grid sm:grid-cols-2 gap-6">
            {features.map((f, i) => (
              <motion.div
                key={f.title}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.08, duration: 0.35 }}
                className="card hover:border-[#484f58] transition-colors"
              >
                <div className={`w-11 h-11 rounded-xl flex items-center justify-center ring-1 mb-4 ${colorMap[f.color]}`}>
                  {f.icon}
                </div>
                <h3 className="font-semibold text-white text-lg mb-2">{f.title}</h3>
                <p className="text-sm text-[#7d8590] leading-relaxed">{f.description}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA banner ────────────────────────────────────────────────── */}
      <section className="py-20 px-4">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="max-w-3xl mx-auto text-center bg-surface-1 border border-brand-500/20 rounded-2xl p-10 glow-green"
        >
          <h2 className="text-3xl font-bold text-white text-balance">
            Ready to start your quest?
          </h2>
          <p className="mt-3 text-[#7d8590] leading-relaxed">
            Join thousands of students already earning XP and mastering STEM subjects.
          </p>
          <div className="mt-8 flex flex-col sm:flex-row gap-4 justify-center">
            {user ? (
              <Link to="/courses" className="btn-primary text-base px-10 py-3">
                Explore Courses
              </Link>
            ) : (
              <>
                <Link to="/register" className="btn-primary text-base px-10 py-3">
                  Create free account
                </Link>
                <Link to="/login" className="btn-secondary text-base px-10 py-3">
                  Sign in
                </Link>
              </>
            )}
          </div>
        </motion.div>
      </section>

      {/* ── Footer ────────────────────────────────────────────────────── */}
      <footer className="bg-surface-1 border-t border-[#30363d] py-8 px-4">
        <div className="max-w-5xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4 text-sm text-[#7d8590]">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded bg-gradient-to-br from-brand-500 to-accent-cyan flex items-center justify-center text-white text-xs font-bold">
              SQ
            </div>
            <span className="font-semibold text-white">STEMQuest</span>
          </div>
          <p>&copy; {new Date().getFullYear()} STEMQuest. All rights reserved.</p>
          <div className="flex gap-4">
            <Link to="/courses" className="hover:text-white transition-colors">Courses</Link>
            <Link to="/login"   className="hover:text-white transition-colors">Sign in</Link>
            <Link to="/register" className="hover:text-white transition-colors">Register</Link>
          </div>
        </div>
      </footer>
    </div>
  )
}
