import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { useAuth } from '@/contexts/AuthContext'
import { gamificationApi, coursesApi } from '@/api/client'
import { StatCard } from '@/components/StatCard'
import { BadgeGrid } from '@/components/BadgeCard'
import { LeaderboardSection } from '@/components/LeaderboardSection'
import { CourseCard } from '@/components/CourseCard'
import { PageWrapper, SectionHeader, PageLoader, ErrorMessage } from '@/components/ui'
import { formatXP } from '@/utils/format'

export function StudentDashboard() {
  const { user } = useAuth()

  const { data: gami, isLoading: gamiLoading, error: gamiErr } = useQuery({
    queryKey: ['gamification', 'me'],
    queryFn:  () => gamificationApi.me(),
  })

  const { data: leaderboard, isLoading: lbLoading } = useQuery({
    queryKey: ['gamification', 'leaderboard'],
    queryFn:  () => gamificationApi.leaderboard(10),
  })

  const { data: coursesData, isLoading: coursesLoading } = useQuery({
    queryKey: ['courses'],
    queryFn:  () => coursesApi.list(),
  })

  if (gamiLoading) return <PageLoader />
  if (gamiErr)     return <ErrorMessage message="Failed to load dashboard data." />

  const enrolledCourses = (coursesData?.courses ?? []).filter(c => c.is_enrolled)
  const streak = gami?.current_streak ?? 0

  return (
    <PageWrapper>
      {/* Welcome header */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-8"
      >
        <h1 className="text-3xl font-bold text-white">
          Welcome back, <span className="text-gradient">{user?.name?.split(' ')[0]}</span>
        </h1>
        <p className="text-[#7d8590] mt-1">
          {streak > 0
            ? `You're on a ${streak}-day streak! Keep it going.`
            : 'Complete a lesson today to start your streak.'}
        </p>
      </motion.div>

      {/* Stats grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-10">
        <StatCard
          label="Total XP"
          value={formatXP(gami?.total_xp ?? 0)}
          sub="experience points"
          icon={
            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
              <path d="M11.983 1.907a.75.75 0 00-1.292-.657l-8.5 9.5A.75.75 0 002.75 12h6.042l-1.274 7.132a.75.75 0 001.292.657l8.5-9.5A.75.75 0 0016.75 9h-6.042l1.274-7.132z" />
            </svg>
          }
          color="green"
          index={0}
        />
        <StatCard
          label="Global Rank"
          value={gami?.rank ? `#${gami.rank}` : '—'}
          sub="among all students"
          icon={
            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
              <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
            </svg>
          }
          color="amber"
          index={1}
        />
        <StatCard
          label="Day Streak"
          value={streak}
          sub={`Longest: ${gami?.longest_streak ?? 0} days`}
          icon={
            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M12.395 2.553a1 1 0 00-1.45-.385c-.345.23-.614.558-.822.88-.214.33-.403.713-.57 1.116-.334.804-.614 1.768-.84 2.734a31.365 31.365 0 00-.613 3.58 2.64 2.64 0 01-.945-1.067c-.328-.68-.398-1.534-.398-2.654A1 1 0 005.05 6.05 6.981 6.981 0 003 11a7 7 0 1011.95-4.95c-.592-.591-.98-.985-1.348-1.467-.363-.476-.724-1.063-1.207-2.03zM12.12 15.12A3 3 0 017 13s.879.5 2.5.5c0-1 .5-4 1.25-4.5.5 1 .786 1.293 1.371 1.879A2.99 2.99 0 0113 13a2.99 2.99 0 01-.879 2.121z" clipRule="evenodd" />
            </svg>
          }
          color="rose"
          index={2}
        />
        <StatCard
          label="Badges"
          value={gami?.badge_count ?? 0}
          sub={`${gami?.enrollments ?? 0} courses enrolled`}
          icon={
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16.5 18.75h-9m9 0a3 3 0 013 3h-15a3 3 0 013-3m9 0v-3.375c0-.621-.503-1.125-1.125-1.125h-.871M7.5 18.75v-3.375c0-.621.504-1.125 1.125-1.125h.872m5.007 0H9.497m5.007 0a7.454 7.454 0 01-.982-3.172M9.497 14.25a7.454 7.454 0 00.981-3.172M5.25 4.236c-.982.143-1.954.317-2.916.52A6.003 6.003 0 007.73 9.728M5.25 4.236V4.5c0 2.108.966 3.99 2.48 5.228M5.25 4.236V2.721C7.456 2.41 9.71 2.25 12 2.25c2.291 0 4.545.16 6.75.47v1.516M7.73 9.728a6.726 6.726 0 002.748 1.35m8.272-6.842V4.5c0 2.108-.966 3.99-2.48 5.228m2.48-5.492a46.32 46.32 0 012.916.52 6.003 6.003 0 01-5.395 4.972m0 0a6.726 6.726 0 01-2.749 1.35m0 0a6.772 6.772 0 01-3.044 0" />
            </svg>
          }
          color="cyan"
          index={3}
        />
      </div>

      {/* XP progress bar towards next milestone */}
      <div className="card mb-10">
        <div className="flex items-center justify-between mb-3">
          <div>
            <p className="text-sm font-medium text-white">XP Progress</p>
            <p className="text-xs text-[#7d8590] mt-0.5">Keep earning XP to climb the leaderboard</p>
          </div>
          <span className="text-2xl font-black text-gradient">{formatXP(gami?.total_xp ?? 0)} XP</span>
        </div>
        <div className="xp-bar">
          <div
            className="xp-bar-fill"
            style={{ width: `${Math.min(((gami?.total_xp ?? 0) % 500) / 500 * 100, 100)}%` }}
          />
        </div>
        <p className="text-xs text-[#7d8590] mt-2">
          {500 - ((gami?.total_xp ?? 0) % 500)} XP to next 500-XP milestone
        </p>
      </div>

      {/* Two-column layout */}
      <div className="grid lg:grid-cols-3 gap-8">
        {/* Left — enrolled courses */}
        <div className="lg:col-span-2 space-y-6">
          <SectionHeader
            title="My Courses"
            sub={enrolledCourses.length > 0 ? `${enrolledCourses.length} course${enrolledCourses.length > 1 ? 's' : ''} in progress` : undefined}
            action={
              <Link to="/courses" className="btn-ghost text-sm">
                Browse all
              </Link>
            }
          />

          {coursesLoading && (
            <div className="grid sm:grid-cols-2 gap-4">
              {[1, 2].map(i => (
                <div key={i} className="card space-y-3">
                  <div className="skeleton w-full aspect-video rounded-lg" />
                  <div className="skeleton h-4 w-3/4 rounded" />
                  <div className="skeleton h-3 w-full rounded" />
                </div>
              ))}
            </div>
          )}

          {!coursesLoading && enrolledCourses.length === 0 && (
            <div className="card text-center py-10">
              <p className="text-[#7d8590] text-sm mb-4">
                You have not enrolled in any courses yet.
              </p>
              <Link to="/courses" className="btn-primary">
                Browse Courses
              </Link>
            </div>
          )}

          {!coursesLoading && enrolledCourses.length > 0 && (
            <div className="grid sm:grid-cols-2 gap-4">
              {enrolledCourses.map((c, i) => (
                <CourseCard key={c.id} course={c} index={i} />
              ))}
            </div>
          )}

          {/* Badges section */}
          <div className="mt-8">
            <SectionHeader title="My Badges" sub={`${gami?.badge_count ?? 0} earned`} />
            <BadgeGrid badges={gami?.badges ?? []} />
          </div>
        </div>

        {/* Right — leaderboard */}
        <div className="space-y-4">
          <SectionHeader
            title="Leaderboard"
            sub="Top 10 students"
          />
          {lbLoading ? (
            <div className="space-y-2">
              {[1,2,3,4,5].map(i => (
                <div key={i} className="card flex items-center gap-3">
                  <div className="skeleton w-7 h-7 rounded-lg flex-shrink-0" />
                  <div className="skeleton w-8 h-8 rounded-full flex-shrink-0" />
                  <div className="flex-1 space-y-1.5">
                    <div className="skeleton h-3 w-2/3 rounded" />
                    <div className="skeleton h-2.5 w-1/3 rounded" />
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <LeaderboardSection
              entries={leaderboard?.leaderboard ?? []}
              currentUserId={user?.id}
            />
          )}
        </div>
      </div>
    </PageWrapper>
  )
}
