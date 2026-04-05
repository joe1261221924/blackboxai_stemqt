import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { coursesApi, billingApi } from '@/api/client'
import { useAuth } from '@/contexts/AuthContext'
import { difficultyColor, formatCurrency } from '@/utils/format'
import { PageWrapper, PageLoader, ErrorMessage, Alert } from '@/components/ui'
import type { Module, LessonSummary } from '@/types'

function LessonRow({ lesson, courseId, hasAccess }: { lesson: LessonSummary; courseId: string; hasAccess: boolean }) {
  return (
    <div className={`flex items-center gap-3 px-4 py-3 rounded-xl border transition-colors ${
      lesson.completed
        ? 'border-brand-500/30 bg-brand-500/5'
        : 'border-[#30363d] bg-surface-2 hover:border-[#484f58]'
    }`}>
      {/* Completion icon */}
      <div className={`w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 ${
        lesson.completed
          ? 'bg-brand-500 text-white'
          : 'border-2 border-[#30363d] text-transparent'
      }`}>
        {lesson.completed && (
          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
          </svg>
        )}
      </div>

      {/* Title */}
      <div className="flex-1 min-w-0">
        {hasAccess ? (
          <Link
            to={`/courses/${courseId}/lessons/${lesson.id}`}
            className="text-sm font-medium text-white hover:text-brand-400 transition-colors truncate block"
          >
            {lesson.title}
          </Link>
        ) : (
          <span className="text-sm font-medium text-[#7d8590] truncate block">{lesson.title}</span>
        )}
        <div className="flex items-center gap-2 mt-0.5">
          <span className={`text-[10px] capitalize px-1.5 py-0.5 rounded border ${difficultyColor(lesson.difficulty_level)}`}>
            {lesson.difficulty_level}
          </span>
          <span className="text-[10px] text-[#7d8590]">+{lesson.xp_reward} XP</span>
          {lesson.has_quiz && (
            <span className="text-[10px] badge-pill bg-accent-cyan/10 text-accent-cyan border-accent-cyan/20">
              Quiz
            </span>
          )}
        </div>
      </div>

      {/* Lock icon if no access */}
      {!hasAccess && (
        <svg className="w-4 h-4 text-[#7d8590] flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
        </svg>
      )}
    </div>
  )
}

function ModuleAccordion({ module: mod, courseId, hasAccess }: { module: Module; courseId: string; hasAccess: boolean }) {
  const [open, setOpen] = useState(true)
  const completedCount = mod.lessons.filter(l => l.completed).length

  return (
    <div className="card mb-4">
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between gap-4 text-left"
      >
        <div>
          <h3 className="font-semibold text-white">{mod.title}</h3>
          <p className="text-xs text-[#7d8590] mt-0.5">
            {completedCount}/{mod.lessons.length} completed
          </p>
        </div>
        <svg
          className={`w-5 h-5 text-[#7d8590] transition-transform ${open ? 'rotate-180' : ''}`}
          fill="none" stroke="currentColor" viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {open && mod.lessons.length > 0 && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          className="mt-4 space-y-2"
        >
          {mod.lessons.map(lesson => (
            <LessonRow
              key={lesson.id}
              lesson={lesson}
              courseId={courseId}
              hasAccess={hasAccess}
            />
          ))}
        </motion.div>
      )}
    </div>
  )
}

export function CourseDetail() {
  const { slug } = useParams<{ slug: string }>()
  const { user } = useAuth()
  const qc = useQueryClient()
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; msg: string } | null>(null)

  const { data, isLoading, error } = useQuery({
    queryKey: ['course', slug],
    queryFn:  () => coursesApi.detail(slug!),
    enabled:  !!slug,
  })

  const enrollMutation = useMutation({
    mutationFn: () => coursesApi.enroll(slug!),
    onSuccess:  () => {
      setFeedback({ type: 'success', msg: 'Enrolled successfully! You can now access all lessons.' })
      qc.invalidateQueries({ queryKey: ['course', slug] })
      qc.invalidateQueries({ queryKey: ['courses'] })
    },
    onError: (err: Error) => setFeedback({ type: 'error', msg: err.message }),
  })

  const purchaseMutation = useMutation({
    mutationFn: async () => {
      const result = await billingApi.createOrder(data!.course.id)
      window.location.href = result.approval_url
    },
    onError: (err: Error) => setFeedback({ type: 'error', msg: err.message }),
  })

  if (isLoading) return <PageLoader />
  if (error || !data?.course) return <ErrorMessage message="Course not found." />

  const { course } = data
  const modules   = course.modules ?? []
  const progress  = course.progress
  const hasAccess = course.has_access ?? false
  const isEnrolled = course.is_enrolled ?? false

  const totalLessons   = modules.reduce((acc, m) => acc + m.lessons.length, 0)
  const completedLessons = modules.reduce((acc, m) => acc + m.lessons.filter(l => l.completed).length, 0)

  return (
    <PageWrapper>
      <div className="grid lg:grid-cols-3 gap-8">
        {/* Main content */}
        <div className="lg:col-span-2 space-y-8">
          {/* Header */}
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
          >
            {/* Breadcrumb */}
            <nav className="flex items-center gap-2 text-sm text-[#7d8590] mb-4">
              <Link to="/courses" className="hover:text-white transition-colors">Courses</Link>
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
              <span className="text-white truncate">{course.title}</span>
            </nav>

            {/* Image */}
            {course.image_url && (
              <div className="w-full aspect-video rounded-xl overflow-hidden mb-6">
                <img src={course.image_url} alt={course.title} className="w-full h-full object-cover" />
              </div>
            )}

            {/* Title + meta */}
            <div className="flex flex-wrap items-center gap-2 mb-3">
              {course.category && (
                <span className="badge-pill bg-surface-3 text-[#7d8590] border border-[#30363d] capitalize">
                  {course.category}
                </span>
              )}
              <span className={`badge-pill border capitalize ${difficultyColor(course.difficulty)}`}>
                {course.difficulty}
              </span>
              {course.is_premium && (
                <span className="badge-pill bg-accent-amber/10 text-accent-amber border border-accent-amber/20">
                  Premium
                </span>
              )}
            </div>

            <h1 className="text-3xl font-bold text-white">{course.title}</h1>
            {course.description && (
              <p className="text-[#7d8590] mt-3 leading-relaxed">{course.description}</p>
            )}

            {/* Stats row */}
            <div className="flex flex-wrap gap-4 mt-4 text-sm text-[#7d8590]">
              <span className="flex items-center gap-1.5">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25" />
                </svg>
                {course.total_lessons} lessons
              </span>
              {course.estimated_hours > 0 && (
                <span className="flex items-center gap-1.5">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  {course.estimated_hours}h estimated
                </span>
              )}
            </div>
          </motion.div>

          {/* Feedback */}
          {feedback && (
            <Alert variant={feedback.type === 'success' ? 'success' : 'error'} message={feedback.msg} />
          )}

          {/* Progress (if enrolled) */}
          {isEnrolled && progress && (
            <div className="card">
              <div className="flex justify-between items-center mb-2 text-sm">
                <span className="font-medium text-white">Your progress</span>
                <span className="text-brand-400 font-semibold">{progress.percentage}%</span>
              </div>
              <div className="xp-bar">
                <div className="xp-bar-fill" style={{ width: `${progress.percentage}%` }} />
              </div>
              <p className="text-xs text-[#7d8590] mt-2">
                {completedLessons} of {totalLessons} lessons completed
              </p>
            </div>
          )}

          {/* Modules */}
          <div>
            <h2 className="section-heading mb-4">Course Content</h2>
            {modules.length === 0 && (
              <p className="text-sm text-[#7d8590]">No modules available yet.</p>
            )}
            {modules.map(mod => (
              <ModuleAccordion
                key={mod.id}
                module={mod}
                courseId={course.id}
                hasAccess={hasAccess}
              />
            ))}
          </div>
        </div>

        {/* Sidebar */}
        <div className="lg:col-span-1">
          <motion.div
            initial={{ opacity: 0, x: 12 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.15 }}
            className="sticky top-20"
          >
            <div className="card space-y-4">
              {/* Price */}
              <div className="text-center pb-4 border-b border-[#30363d]">
                {course.is_premium && course.price != null ? (
                  <p className="text-3xl font-black text-accent-amber">
                    {formatCurrency(course.price, course.currency)}
                  </p>
                ) : (
                  <p className="text-3xl font-black text-brand-400">Free</p>
                )}
              </div>

              {/* Actions */}
              {!user ? (
                <Link to={`/login?from=/courses/${slug}`} className="btn-primary w-full text-center">
                  Sign in to enroll
                </Link>
              ) : isEnrolled ? (
                <div className="space-y-2">
                  <div className="badge-pill bg-brand-500/10 text-brand-400 border border-brand-500/20 w-full justify-center py-2 rounded-lg text-sm">
                    Enrolled
                  </div>
                  {modules[0]?.lessons[0] && (
                    <Link
                      to={`/courses/${course.id}/lessons/${modules[0].lessons[0].id}`}
                      className="btn-secondary w-full text-center"
                    >
                      {completedLessons > 0 ? 'Continue learning' : 'Start course'}
                    </Link>
                  )}
                </div>
              ) : course.is_premium ? (
                <button
                  onClick={() => purchaseMutation.mutate()}
                  disabled={purchaseMutation.isPending}
                  className="btn-primary w-full"
                >
                  {purchaseMutation.isPending ? (
                    <span className="flex items-center gap-2 justify-center">
                      <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                      Redirecting...
                    </span>
                  ) : (
                    `Purchase — ${course.price != null ? formatCurrency(course.price, course.currency) : ''}`
                  )}
                </button>
              ) : (
                <button
                  onClick={() => enrollMutation.mutate()}
                  disabled={enrollMutation.isPending}
                  className="btn-primary w-full"
                >
                  {enrollMutation.isPending ? (
                    <span className="flex items-center gap-2 justify-center">
                      <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                      Enrolling...
                    </span>
                  ) : (
                    'Enroll for free'
                  )}
                </button>
              )}

              {/* Summary */}
              <ul className="space-y-2 text-sm text-[#7d8590]">
                <li className="flex items-center gap-2">
                  <svg className="w-4 h-4 text-brand-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  {course.total_lessons} lessons across {modules.length} modules
                </li>
                <li className="flex items-center gap-2">
                  <svg className="w-4 h-4 text-brand-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  Earn XP and unlock badges
                </li>
                <li className="flex items-center gap-2">
                  <svg className="w-4 h-4 text-brand-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  Adaptive quiz recommendations
                </li>
                {course.estimated_hours > 0 && (
                  <li className="flex items-center gap-2">
                    <svg className="w-4 h-4 text-brand-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                    Approx. {course.estimated_hours} hours
                  </li>
                )}
              </ul>

              {course.tags?.length > 0 && (
                <div className="pt-2 border-t border-[#30363d]">
                  <p className="text-xs text-[#7d8590] mb-2">Topics</p>
                  <div className="flex flex-wrap gap-1.5">
                    {course.tags.map(tag => (
                      <span key={tag} className="badge-pill bg-surface-3 text-[#7d8590] border border-[#30363d] text-[10px]">
                        {tag}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </motion.div>
        </div>
      </div>
    </PageWrapper>
  )
}
