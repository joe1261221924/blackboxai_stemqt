'use client'
// ============================================================
// STEMQuest — Landing Page (Home)
// Hero, features, stats, course preview, CTA
// ============================================================

import Link from 'next/link'
import { motion } from 'framer-motion'
import { useAuth } from '@/contexts/AuthContext'
import Navbar from '@/components/shared/Navbar'
import {
  Zap, BookOpen, Trophy, Star, ArrowRight, CheckCircle,
  FlaskConical, Calculator, Cpu, Atom, TrendingUp, Users,
  Award, Target, Play, Shield, BarChart3,
} from 'lucide-react'

const features = [
  {
    icon: BookOpen,
    title: 'Structured STEM Courses',
    description: 'Learn through expertly crafted modules covering Computer Science, Mathematics, Physics, and Engineering.',
    color: 'text-primary',
    bg: 'bg-primary/10',
  },
  {
    icon: Trophy,
    title: 'Earn XP & Badges',
    description: 'Complete lessons and quizzes to earn experience points, unlock achievement badges, and build your streak.',
    color: 'text-gold',
    bg: 'bg-gold/10',
  },
  {
    icon: BarChart3,
    title: 'Adaptive Learning',
    description: 'Our quiz engine analyses your performance and recommends the perfect next step — review, advance, or progress.',
    color: 'text-accent',
    bg: 'bg-accent/10',
  },
  {
    icon: Users,
    title: 'Leaderboard & Community',
    description: 'Compete with fellow learners, track your rank on the global leaderboard, and stay motivated.',
    color: 'text-success',
    bg: 'bg-success/10',
  },
  {
    icon: Shield,
    title: 'Role-Based Access',
    description: 'Students and admins each have dedicated dashboards. Admins author content while students focus on learning and earning rewards.',
    color: 'text-[oklch(0.75_0.22_295)]',
    bg: 'bg-[oklch(0.62_0.25_295)/0.1]',
  },
  {
    icon: Target,
    title: 'Premium Deep-Dives',
    description: 'Unlock advanced courses with secure PayPal checkout and get lifetime access to cutting-edge STEM content.',
    color: 'text-warning',
    bg: 'bg-warning/10',
  },
]

const stats = [
  { value: '4+', label: 'STEM Courses' },
  { value: '16+', label: 'Lessons' },
  { value: '10', label: 'Achievements' },
  { value: '100%', label: 'Free to Start' },
]

const categories = [
  { icon: Cpu, label: 'Computer Science', color: 'text-primary', bg: 'bg-primary/10' },
  { icon: Calculator, label: 'Mathematics', color: 'text-accent', bg: 'bg-accent/10' },
  { icon: FlaskConical, label: 'Engineering', color: 'text-[oklch(0.75_0.22_295)]', bg: 'bg-[oklch(0.62_0.25_295)/0.1]' },
  { icon: Atom, label: 'Physics', color: 'text-gold', bg: 'bg-gold/10' },
]

const testimonials = [
  { name: 'Alex S.', role: 'Student', avatar: 'AS', text: 'STEMQuest turned maths from a chore into something I actually look forward to. The streak system keeps me coming back every day.' },
  { name: 'Jordan C.', role: 'Student', avatar: 'JC', text: 'I earned the Perfect Score badge on my first Python quiz and felt genuinely proud. The adaptive recommendations are spot on.' },
  { name: 'Sam R.', role: 'Student', avatar: 'SR', text: 'The leaderboard competition is so motivating. I went from knowing zero programming to finishing the whole intro course in a week.' },
]

export default function HomePage() {
  const { isAuthenticated, session } = useAuth()
  const dashboardHref = session?.role === 'admin' ? '/admin' : '/dashboard'

  return (
    <div className="min-h-screen bg-background">
      <Navbar />

      {/* ── Hero ───────────────────────────────────────────── */}
      <section className="relative overflow-hidden">
        {/* Background glow blobs */}
        <div className="pointer-events-none absolute inset-0 overflow-hidden">
          <div className="absolute -top-32 left-1/4 h-96 w-96 rounded-full bg-primary/10 blur-3xl" />
          <div className="absolute top-20 right-1/4 h-64 w-64 rounded-full bg-accent/10 blur-3xl" />
        </div>

        <div className="relative mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 pt-20 pb-24 text-center">
          {/* Pill badge */}
          <motion.div
            initial={{ opacity: 0, y: -16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full border border-primary/30 bg-primary/10 text-primary text-sm font-medium mb-8"
          >
            <Zap className="h-3.5 w-3.5" />
            Gamified STEM Learning Platform
          </motion.div>

          {/* Headline */}
          <motion.h1
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.55, delay: 0.1 }}
            className="text-5xl sm:text-6xl lg:text-7xl font-extrabold tracking-tight text-foreground mb-6 leading-tight"
          >
            Master STEM with
            <br />
            <span className="text-gradient-primary">Quest-Driven</span> Learning
          </motion.h1>

          <motion.p
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.2 }}
            className="mx-auto max-w-2xl text-lg text-muted-foreground leading-relaxed mb-10"
          >
            Earn XP, unlock badges, track streaks, and compete on leaderboards as you work through
            structured courses in Computer Science, Mathematics, Physics, and Engineering.
          </motion.p>

          {/* CTA Buttons */}
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.45, delay: 0.32 }}
            className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-16"
          >
            {isAuthenticated ? (
              <Link
                href={dashboardHref}
                className="inline-flex items-center gap-2 px-8 py-3.5 rounded-xl bg-primary text-white font-semibold text-lg hover:bg-primary/90 transition-colors glow-primary"
              >
                Go to Dashboard
                <ArrowRight className="h-5 w-5" />
              </Link>
            ) : (
              <>
                <Link
                  href="/register"
                  className="inline-flex items-center gap-2 px-8 py-3.5 rounded-xl bg-primary text-white font-semibold text-lg hover:bg-primary/90 transition-colors glow-primary"
                >
                  Start Learning Free
                  <ArrowRight className="h-5 w-5" />
                </Link>
                <Link
                  href="/courses"
                  className="inline-flex items-center gap-2 px-8 py-3.5 rounded-xl border border-border bg-secondary text-foreground font-semibold text-lg hover:bg-muted transition-colors"
                >
                  <Play className="h-5 w-5" />
                  Browse Courses
                </Link>
              </>
            )}
          </motion.div>

          {/* Stats row */}
          <div className="flex flex-wrap items-center justify-center gap-8 sm:gap-16">
            {stats.map(({ value, label }) => (
              <div key={label} className="text-center">
                <p className="text-3xl font-extrabold text-gradient-primary">{value}</p>
                <p className="text-sm text-muted-foreground mt-1">{label}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Categories ────────────────────────────────────────── */}
      <section className="py-16 border-t border-border">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <p className="text-center text-sm font-semibold uppercase tracking-widest text-muted-foreground mb-8">
            Explore STEM Disciplines
          </p>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {categories.map(({ icon: Icon, label, color, bg }) => (
              <Link
                key={label}
                href={`/courses?category=${encodeURIComponent(label)}`}
                className="flex flex-col items-center gap-3 p-6 rounded-xl border border-border bg-card card-hover text-center group"
              >
                <div className={`p-3 rounded-xl ${bg}`}>
                  <Icon className={`h-7 w-7 ${color}`} />
                </div>
                <span className="font-semibold text-foreground group-hover:text-primary transition-colors">{label}</span>
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* ── Features ──────────────────────────────────────────── */}
      <section className="py-20 border-t border-border">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-14">
            <h2 className="text-3xl sm:text-4xl font-bold text-foreground mb-4">
              Everything You Need to{' '}
              <span className="text-gradient-primary">Level Up</span>
            </h2>
            <p className="text-muted-foreground max-w-xl mx-auto">
              STEMQuest blends rigorous academic content with game mechanics that keep you engaged and progressing.
            </p>
          </div>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {features.map(({ icon: Icon, title, description, color, bg }) => (
              <div key={title} className="p-6 rounded-xl border border-border bg-card card-hover">
                <div className={`inline-flex p-3 rounded-xl ${bg} mb-4`}>
                  <Icon className={`h-6 w-6 ${color}`} />
                </div>
                <h3 className="font-semibold text-foreground mb-2">{title}</h3>
                <p className="text-sm text-muted-foreground leading-relaxed">{description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── How it works ──────────────────────────────────────── */}
      <section className="py-20 border-t border-border bg-card/30">
        <div className="mx-auto max-w-5xl px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-14">
            <h2 className="text-3xl sm:text-4xl font-bold text-foreground mb-4">
              How STEMQuest Works
            </h2>
            <p className="text-muted-foreground">Three simple steps to start your STEM journey</p>
          </div>
          <div className="grid sm:grid-cols-3 gap-8 relative">
            {/* Connector line */}
            <div className="hidden sm:block absolute top-8 left-1/3 right-1/3 h-0.5 bg-gradient-to-r from-primary/40 to-accent/40" />
            {[
              { step: '01', icon: Users, title: 'Create Free Account', desc: 'Sign up in seconds — no credit card required. Public registration always creates a student account.' },
              { step: '02', icon: BookOpen, title: 'Enrol in Courses', desc: 'Browse free and premium STEM courses. Each course has structured modules, rich lessons, and quizzes.' },
              { step: '03', icon: Trophy, title: 'Earn Rewards', desc: 'Complete lessons and quizzes to earn XP, badges, and climb the leaderboard rankings.' },
            ].map(({ step, icon: Icon, title, desc }) => (
              <div key={step} className="flex flex-col items-center text-center gap-4">
                <div className="relative">
                  <div className="h-16 w-16 rounded-2xl bg-primary/10 border border-primary/30 flex items-center justify-center">
                    <Icon className="h-7 w-7 text-primary" />
                  </div>
                  <span className="absolute -top-2 -right-2 text-xs font-bold text-primary bg-card border border-primary/30 rounded-full h-6 w-6 flex items-center justify-center">
                    {step}
                  </span>
                </div>
                <h3 className="font-semibold text-foreground">{title}</h3>
                <p className="text-sm text-muted-foreground leading-relaxed">{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Testimonials ─────────────────────────────────────── */}
      <section className="py-20 border-t border-border">
        <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold text-foreground mb-3">Loved by Learners</h2>
            <p className="text-muted-foreground">What students say about STEMQuest</p>
          </div>
          <div className="grid md:grid-cols-3 gap-6">
            {testimonials.map(({ name, role, avatar, text }) => (
              <div key={name} className="p-6 rounded-xl border border-border bg-card card-hover">
                <div className="flex mb-4">
                  {[...Array(5)].map((_, i) => (
                    <Star key={i} className="h-4 w-4 text-gold fill-gold" />
                  ))}
                </div>
                <p className="text-sm text-muted-foreground leading-relaxed mb-5 italic">&ldquo;{text}&rdquo;</p>
                <div className="flex items-center gap-3">
                  <div className="h-9 w-9 rounded-full bg-primary flex items-center justify-center text-xs font-bold text-white">
                    {avatar}
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-foreground">{name}</p>
                    <p className="text-xs text-muted-foreground">{role}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA Banner ───────────────────────────────────────── */}
      <section className="py-20 border-t border-border">
        <div className="mx-auto max-w-4xl px-4 sm:px-6 lg:px-8 text-center">
          <div className="rounded-2xl border border-primary/20 bg-gradient-to-br from-primary/10 to-accent/10 p-12">
            <div className="inline-flex p-3 rounded-xl bg-primary/20 mb-6">
              <TrendingUp className="h-8 w-8 text-primary" />
            </div>
            <h2 className="text-3xl sm:text-4xl font-bold text-foreground mb-4">
              Ready to Start Your Quest?
            </h2>
            <p className="text-muted-foreground mb-8 max-w-xl mx-auto">
              Join students already learning with STEMQuest. Free courses available instantly — no payment required.
            </p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              {isAuthenticated ? (
                <Link
                  href={dashboardHref}
                  className="inline-flex items-center gap-2 px-8 py-3.5 rounded-xl bg-primary text-white font-semibold hover:bg-primary/90 transition-colors glow-primary"
                >
                  Go to Dashboard
                  <ArrowRight className="h-5 w-5" />
                </Link>
              ) : (
                <>
                  <Link
                    href="/register"
                    className="inline-flex items-center gap-2 px-8 py-3.5 rounded-xl bg-primary text-white font-semibold hover:bg-primary/90 transition-colors glow-primary"
                  >
                    Create Free Account
                    <ArrowRight className="h-5 w-5" />
                  </Link>
                  <Link
                    href="/login"
                    className="inline-flex items-center gap-2 px-8 py-3.5 rounded-xl border border-border bg-secondary text-foreground font-semibold hover:bg-muted transition-colors"
                  >
                    Sign In
                  </Link>
                </>
              )}
            </div>
            <div className="flex flex-wrap items-center justify-center gap-x-6 gap-y-2 mt-8 text-sm text-muted-foreground">
              {['No credit card required', 'Free courses included', 'Badges & XP from day 1'].map(t => (
                <span key={t} className="flex items-center gap-1.5">
                  <CheckCircle className="h-4 w-4 text-success" />
                  {t}
                </span>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ── Footer ───────────────────────────────────────────── */}
      <footer className="border-t border-border py-10">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <div className="h-7 w-7 rounded-lg bg-primary flex items-center justify-center">
                <Zap className="h-4 w-4 text-white" />
              </div>
              <span className="font-bold text-gradient-primary">STEMQuest</span>
            </div>
            <p className="text-xs text-muted-foreground text-center">
              Built as a final year project. Demo credentials: student@demo.test / password123
            </p>
            <div className="flex gap-4 text-sm text-muted-foreground">
              <Link href="/courses" className="hover:text-foreground transition-colors">Courses</Link>
              <Link href="/leaderboard" className="hover:text-foreground transition-colors">Leaderboard</Link>
              <Link href="/login" className="hover:text-foreground transition-colors">Sign In</Link>
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}
