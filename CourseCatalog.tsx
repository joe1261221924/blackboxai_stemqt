import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { coursesApi } from '@/api/client'
import { CourseCard } from '@/components/CourseCard'
import { PageWrapper, SectionHeader, PageLoader, ErrorMessage, SkeletonCard } from '@/components/ui'
import type { Course } from '@/types'

const DIFFICULTY_OPTIONS = ['all', 'beginner', 'intermediate', 'advanced'] as const
const ACCESS_OPTIONS      = ['all', 'free', 'premium']                       as const

export function CourseCatalog() {
  const [search,     setSearch]     = useState('')
  const [difficulty, setDifficulty] = useState<typeof DIFFICULTY_OPTIONS[number]>('all')
  const [access,     setAccess]     = useState<typeof ACCESS_OPTIONS[number]>('all')

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['courses'],
    queryFn:  () => coursesApi.list(),
  })

  const courses: Course[] = data?.courses ?? []

  const filtered = courses.filter(c => {
    const matchSearch = !search ||
      c.title.toLowerCase().includes(search.toLowerCase()) ||
      c.description?.toLowerCase().includes(search.toLowerCase()) ||
      c.category?.toLowerCase().includes(search.toLowerCase())
    const matchDifficulty = difficulty === 'all' || c.difficulty === difficulty
    const matchAccess     = access === 'all' ||
      (access === 'free'    && !c.is_premium) ||
      (access === 'premium' &&  c.is_premium)
    return matchSearch && matchDifficulty && matchAccess
  })

  if (error) return <ErrorMessage message="Failed to load courses." retry={refetch} />

  return (
    <PageWrapper>
      <SectionHeader
        title="Course Catalog"
        sub={`${courses.length} courses available`}
      />

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-3 mb-8">
        {/* Search */}
        <div className="flex-1 relative">
          <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#7d8590]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            type="search"
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search courses..."
            className="input-base pl-9"
          />
        </div>

        {/* Difficulty filter */}
        <div className="flex items-center gap-1 bg-surface-2 border border-[#30363d] rounded-lg p-1">
          {DIFFICULTY_OPTIONS.map(d => (
            <button
              key={d}
              onClick={() => setDifficulty(d)}
              className={`px-3 py-1.5 rounded-md text-xs font-semibold capitalize transition-colors ${
                difficulty === d
                  ? 'bg-brand-500 text-white'
                  : 'text-[#7d8590] hover:text-white'
              }`}
            >
              {d}
            </button>
          ))}
        </div>

        {/* Access filter */}
        <div className="flex items-center gap-1 bg-surface-2 border border-[#30363d] rounded-lg p-1">
          {ACCESS_OPTIONS.map(a => (
            <button
              key={a}
              onClick={() => setAccess(a)}
              className={`px-3 py-1.5 rounded-md text-xs font-semibold capitalize transition-colors ${
                access === a
                  ? 'bg-brand-500 text-white'
                  : 'text-[#7d8590] hover:text-white'
              }`}
            >
              {a}
            </button>
          ))}
        </div>
      </div>

      {/* Grid */}
      {isLoading && (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {Array.from({ length: 6 }).map((_, i) => <SkeletonCard key={i} />)}
        </div>
      )}

      {!isLoading && filtered.length === 0 && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="text-center py-20"
        >
          <p className="text-white font-semibold">No courses found</p>
          <p className="text-sm text-[#7d8590] mt-1">Try adjusting your filters or search query.</p>
          <button
            onClick={() => { setSearch(''); setDifficulty('all'); setAccess('all') }}
            className="btn-secondary mt-4 text-sm"
          >
            Clear filters
          </button>
        </motion.div>
      )}

      {!isLoading && filtered.length > 0 && (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {filtered.map((c, i) => (
            <CourseCard key={c.id} course={c} index={i} />
          ))}
        </div>
      )}
    </PageWrapper>
  )
}
