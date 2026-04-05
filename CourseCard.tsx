import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import type { Course } from '@/types'
import { difficultyColor, formatCurrency } from '@/utils/format'

interface Props {
  course: Course
  index?:  number
}

export function CourseCard({ course, index = 0 }: Props) {
  const progress = course.progress

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05, duration: 0.3 }}
    >
      <Link
        to={`/courses/${course.slug}`}
        className="group card-hover flex flex-col h-full"
      >
        {/* Header / banner */}
        <div className="relative w-full aspect-video rounded-lg overflow-hidden mb-4 bg-surface-3">
          {course.image_url ? (
            <img
              src={course.image_url}
              alt={course.title}
              className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-surface-3 to-surface-4">
              <svg className="w-12 h-12 text-[#30363d]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25" />
              </svg>
            </div>
          )}

          {/* Premium badge */}
          {course.is_premium && (
            <div className="absolute top-2 right-2 badge-pill bg-accent-amber/90 text-black border-0">
              Premium
            </div>
          )}

          {/* Enrolled badge */}
          {course.is_enrolled && (
            <div className="absolute top-2 left-2 badge-pill bg-brand-500/90 text-white border-0">
              Enrolled
            </div>
          )}
        </div>

        {/* Content */}
        <div className="flex flex-col flex-1 gap-3">
          {/* Category + difficulty */}
          <div className="flex items-center gap-2 flex-wrap">
            {course.category && (
              <span className="badge-pill bg-surface-3 text-[#7d8590] border border-[#30363d] capitalize">
                {course.category}
              </span>
            )}
            <span className={`badge-pill border capitalize ${difficultyColor(course.difficulty)}`}>
              {course.difficulty}
            </span>
          </div>

          {/* Title */}
          <h3 className="font-semibold text-white leading-snug group-hover:text-brand-400 transition-colors line-clamp-2">
            {course.title}
          </h3>

          {/* Description */}
          {course.description && (
            <p className="text-sm text-[#7d8590] leading-relaxed line-clamp-2 flex-1">
              {course.description}
            </p>
          )}

          {/* Progress bar (if enrolled) */}
          {progress && (
            <div className="space-y-1">
              <div className="flex justify-between text-xs text-[#7d8590]">
                <span>{progress.completed_lessons}/{progress.total_lessons} lessons</span>
                <span>{progress.percentage}%</span>
              </div>
              <div className="xp-bar">
                <div
                  className="xp-bar-fill"
                  style={{ width: `${progress.percentage}%` }}
                />
              </div>
            </div>
          )}

          {/* Footer */}
          <div className="flex items-center justify-between mt-auto pt-2 border-t border-[#30363d]">
            <div className="flex items-center gap-3 text-xs text-[#7d8590]">
              <span className="flex items-center gap-1">
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25" />
                </svg>
                {course.total_lessons} lessons
              </span>
              {course.estimated_hours > 0 && (
                <span className="flex items-center gap-1">
                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  {course.estimated_hours}h
                </span>
              )}
            </div>

            <div className="text-sm font-semibold">
              {course.is_premium && course.price != null ? (
                <span className="text-accent-amber">{formatCurrency(course.price, course.currency)}</span>
              ) : (
                <span className="text-brand-400">Free</span>
              )}
            </div>
          </div>
        </div>
      </Link>
    </motion.div>
  )
}
