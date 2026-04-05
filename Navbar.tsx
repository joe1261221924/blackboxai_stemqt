import { useState } from 'react'
import { Link, NavLink, useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { useAuth } from '@/contexts/AuthContext'
import { formatXP } from '@/utils/format'

const Logo = () => (
  <Link to="/" className="flex items-center gap-2.5 group">
    <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-brand-500 to-accent-cyan flex items-center justify-center text-white font-bold text-sm glow-green group-hover:scale-105 transition-transform">
      SQ
    </div>
    <span className="font-bold text-lg tracking-tight text-white">
      STEM<span className="text-gradient">Quest</span>
    </span>
  </Link>
)

export function Navbar() {
  const { user, gamification, logout } = useAuth()
  const navigate = useNavigate()
  const [menuOpen, setMenuOpen] = useState(false)
  const [profileOpen, setProfileOpen] = useState(false)

  const handleLogout = async () => {
    await logout()
    navigate('/')
    setProfileOpen(false)
    setMenuOpen(false)
  }

  const navLinkClass = ({ isActive }: { isActive: boolean }) =>
    `text-sm font-medium px-3 py-1.5 rounded-md transition-colors ${
      isActive
        ? 'text-white bg-surface-3'
        : 'text-[#7d8590] hover:text-white hover:bg-surface-3'
    }`

  return (
    <header className="sticky top-0 z-50 bg-surface-1/80 backdrop-blur-md border-b border-[#30363d]">
      <nav className="max-w-7xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between gap-4">
        {/* Logo */}
        <Logo />

        {/* Desktop nav links */}
        <div className="hidden md:flex items-center gap-1">
          <NavLink to="/courses" className={navLinkClass}>Courses</NavLink>
          {user?.role === 'admin' && (
            <NavLink to="/admin" className={navLinkClass}>Admin</NavLink>
          )}
          {user?.role === 'student' && (
            <NavLink to="/dashboard" className={navLinkClass}>Dashboard</NavLink>
          )}
        </div>

        {/* Right side */}
        <div className="flex items-center gap-3">
          {user ? (
            <>
              {/* XP chip (student only) */}
              {user.role === 'student' && gamification && (
                <div className="hidden sm:flex items-center gap-1.5 bg-brand-500/10 border border-brand-500/20 rounded-full px-3 py-1 text-xs font-semibold text-brand-400">
                  <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M11.983 1.907a.75.75 0 00-1.292-.657l-8.5 9.5A.75.75 0 002.75 12h6.042l-1.274 7.132a.75.75 0 001.292.657l8.5-9.5A.75.75 0 0016.75 9h-6.042l1.274-7.132z" />
                  </svg>
                  {formatXP(gamification.total_xp)} XP
                </div>
              )}

              {/* Profile dropdown */}
              <div className="relative">
                <button
                  onClick={() => setProfileOpen(p => !p)}
                  className="flex items-center gap-2 px-2 py-1 rounded-lg hover:bg-surface-3 transition-colors"
                >
                  <div className="w-7 h-7 rounded-full bg-gradient-to-br from-brand-500 to-accent-cyan flex items-center justify-center text-white text-xs font-bold">
                    {user.avatar || user.name[0]?.toUpperCase()}
                  </div>
                  <span className="hidden sm:block text-sm font-medium text-white max-w-[120px] truncate">
                    {user.name}
                  </span>
                  <svg className="w-4 h-4 text-[#7d8590]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </button>

                <AnimatePresence>
                  {profileOpen && (
                    <>
                      <div className="fixed inset-0 z-10" onClick={() => setProfileOpen(false)} />
                      <motion.div
                        initial={{ opacity: 0, y: -8 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -8 }}
                        transition={{ duration: 0.15 }}
                        className="absolute right-0 top-full mt-2 w-52 bg-surface-2 border border-[#30363d] rounded-xl shadow-xl z-20 overflow-hidden"
                      >
                        <div className="px-4 py-3 border-b border-[#30363d]">
                          <p className="text-sm font-semibold text-white truncate">{user.name}</p>
                          <p className="text-xs text-[#7d8590] truncate">{user.email}</p>
                          <span className="mt-1 inline-block badge-pill bg-brand-500/10 text-brand-400 border border-brand-500/20 capitalize">
                            {user.role}
                          </span>
                        </div>
                        {user.role === 'student' && (
                          <Link
                            to="/dashboard"
                            onClick={() => setProfileOpen(false)}
                            className="flex items-center gap-2 w-full px-4 py-2.5 text-sm text-[#e6edf3] hover:bg-surface-3 transition-colors"
                          >
                            Dashboard
                          </Link>
                        )}
                        {user.role === 'admin' && (
                          <Link
                            to="/admin"
                            onClick={() => setProfileOpen(false)}
                            className="flex items-center gap-2 w-full px-4 py-2.5 text-sm text-[#e6edf3] hover:bg-surface-3 transition-colors"
                          >
                            Admin Panel
                          </Link>
                        )}
                        <button
                          onClick={handleLogout}
                          className="flex items-center gap-2 w-full px-4 py-2.5 text-sm text-accent-rose hover:bg-surface-3 transition-colors border-t border-[#30363d]"
                        >
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                          </svg>
                          Sign out
                        </button>
                      </motion.div>
                    </>
                  )}
                </AnimatePresence>
              </div>
            </>
          ) : (
            <div className="flex items-center gap-2">
              <Link to="/login" className="btn-ghost text-sm">Sign in</Link>
              <Link to="/register" className="btn-primary text-sm">Get started</Link>
            </div>
          )}

          {/* Mobile hamburger */}
          <button
            className="md:hidden p-1.5 rounded-lg text-[#7d8590] hover:text-white hover:bg-surface-3"
            onClick={() => setMenuOpen(p => !p)}
            aria-label="Toggle menu"
          >
            {menuOpen ? (
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            ) : (
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            )}
          </button>
        </div>
      </nav>

      {/* Mobile menu */}
      <AnimatePresence>
        {menuOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="md:hidden bg-surface-1 border-b border-[#30363d] overflow-hidden"
          >
            <div className="px-4 py-3 flex flex-col gap-1">
              <NavLink to="/courses" className={navLinkClass} onClick={() => setMenuOpen(false)}>
                Courses
              </NavLink>
              {user?.role === 'student' && (
                <NavLink to="/dashboard" className={navLinkClass} onClick={() => setMenuOpen(false)}>
                  Dashboard
                </NavLink>
              )}
              {user?.role === 'admin' && (
                <NavLink to="/admin" className={navLinkClass} onClick={() => setMenuOpen(false)}>
                  Admin
                </NavLink>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </header>
  )
}
