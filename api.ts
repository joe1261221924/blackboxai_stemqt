// ============================================================
// STEMQuest — Real API Client
// All fetch calls to the Flask backend. Uses credentials:'include'
// for HTTP-only cookie auth. All responses are mapped from
// snake_case (backend) to camelCase (frontend types).
// ============================================================

export const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:5000'

// ── Core fetch wrapper ──────────────────────────────────────

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public detail?: unknown,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    credentials: 'include',       // send/receive HTTP-only JWT cookie
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers ?? {}),
    },
  })

  // 204 No Content
  if (res.status === 204) return undefined as unknown as T

  let body: unknown
  try {
    body = await res.json()
  } catch {
    throw new ApiError(res.status, `HTTP ${res.status}`)
  }

  if (!res.ok) {
    const msg =
      (body as { message?: string; error?: string })?.message ??
      (body as { message?: string; error?: string })?.error ??
      `HTTP ${res.status}`
    throw new ApiError(res.status, msg, (body as { detail?: unknown })?.detail)
  }

  return body as T
}

const get  = <T>(path: string, opts?: RequestInit) =>
  request<T>(path, { method: 'GET', ...opts })
const post = <T>(path: string, body?: unknown, opts?: RequestInit) =>
  request<T>(path, { method: 'POST', body: JSON.stringify(body), ...opts })
const put  = <T>(path: string, body?: unknown, opts?: RequestInit) =>
  request<T>(path, { method: 'PUT', body: JSON.stringify(body), ...opts })

// ── Snake → Camel mapper ────────────────────────────────────

function toCamel(s: string): string {
  return s.replace(/_([a-z])/g, (_, c) => c.toUpperCase())
}

type AnyCamel = Record<string, unknown>

export function mapCamel(obj: unknown): unknown {
  if (Array.isArray(obj)) return obj.map(mapCamel)
  if (obj !== null && typeof obj === 'object') {
    const out: AnyCamel = {}
    for (const [k, v] of Object.entries(obj as Record<string, unknown>)) {
      out[toCamel(k)] = mapCamel(v)
    }
    return out
  }
  return obj
}

// ── Auth Types (raw backend shapes) ─────────────────────────

interface RawUser {
  id: string
  email: string
  name: string
  role: 'student' | 'admin'
  avatar: string
  is_active: boolean
  email_verified: boolean
  created_at: string
}

interface RawGamificationSummary {
  total_xp: number
  rank: number
  current_streak: number
  longest_streak: number
  badge_count: number
  badges: RawUserBadge[]
  enrollments: number
}

interface RawUserBadge {
  id: string
  badge_id: string
  user_id: string
  earned_at: string
  badge?: RawBadge
}

interface RawBadge {
  id: string
  name: string
  description: string
  icon: string
  category: string
  criteria: string
  color: string
  threshold?: number
}

// ── Auth API ─────────────────────────────────────────────────

export interface AuthUser {
  id: string
  email: string
  name: string
  role: 'student' | 'admin'
  avatar: string
  isActive: boolean
  emailVerified: boolean
  createdAt: string
}

export interface GamificationSummary {
  totalXp: number
  rank: number
  currentStreak: number
  longestStreak: number
  badgeCount: number
  badges: BadgeSummaryItem[]
  enrollments: number
}

export interface BadgeSummaryItem {
  id: string
  badgeId: string
  userId: string
  earnedAt: string
  badge?: BadgeItem
}

export interface BadgeItem {
  id: string
  name: string
  description: string
  icon: string
  category: string
  criteria: string
  color: string
  threshold?: number
}

function mapUser(raw: RawUser): AuthUser {
  return {
    id:            raw.id,
    email:         raw.email,
    name:          raw.name,
    role:          raw.role,
    avatar:        raw.avatar,
    isActive:      raw.is_active,
    emailVerified: raw.email_verified,
    createdAt:     raw.created_at,
  }
}

function mapGamification(raw: RawGamificationSummary): GamificationSummary {
  return {
    totalXp:       raw.total_xp,
    rank:          raw.rank,
    currentStreak: raw.current_streak,
    longestStreak: raw.longest_streak,
    badgeCount:    raw.badge_count,
    badges:        (raw.badges ?? []).map(mapBadgeSummary),
    enrollments:   raw.enrollments,
  }
}

function mapBadgeSummary(raw: RawUserBadge): BadgeSummaryItem {
  return {
    id:       raw.id,
    badgeId:  raw.badge_id,
    userId:   raw.user_id,
    earnedAt: raw.earned_at,
    badge:    raw.badge ? mapBadge(raw.badge) : undefined,
  }
}

function mapBadge(raw: RawBadge): BadgeItem {
  return {
    id:          raw.id,
    name:        raw.name,
    description: raw.description,
    icon:        raw.icon,
    category:    raw.category,
    criteria:    raw.criteria,
    color:       raw.color,
    threshold:   raw.threshold,
  }
}

export interface MeResponse {
  user: AuthUser
  gamification: GamificationSummary | null
}

export const authApi = {
  async register(email: string, name: string, password: string): Promise<{ user: AuthUser }> {
    const res = await post<{ user: RawUser }>('/api/auth/register', { email, name, password })
    return { user: mapUser(res.user) }
  },
  async login(email: string, password: string): Promise<{ user: AuthUser }> {
    const res = await post<{ user: RawUser }>('/api/auth/login', { email, password })
    return { user: mapUser(res.user) }
  },
  async logout(): Promise<void> {
    await post('/api/auth/logout')
  },
  async me(): Promise<MeResponse> {
    const res = await get<{ user: RawUser; gamification: RawGamificationSummary | null }>('/api/auth/me')
    return {
      user: mapUser(res.user),
      gamification: res.gamification ? mapGamification(res.gamification) : null,
    }
  },
}

// ── Course Types ─────────────────────────────────────────────

export interface CourseItem {
  id: string
  slug: string
  title: string
  description: string
  imageUrl: string
  instructorId: string
  instructorName: string
  isFree: boolean
  price: number
  currency: string
  isPublished: boolean
  category: string
  difficulty: string
  tags: string[]
  totalLessons: number
  estimatedHours: number
  isEnrolled: boolean
  hasAccess: boolean
  progress: CourseProgress | null
  modules?: ModuleItem[]
}

export interface CourseProgress {
  completedLessons: number
  totalLessons: number
  percentage: number
}

export interface ModuleItem {
  id: string
  courseId: string
  title: string
  description: string
  order: number
  lessons?: LessonItem[]
}

export interface LessonItem {
  id: string
  moduleId: string
  courseId: string
  title: string
  summary: string
  content: string
  videoUrl?: string
  difficulty: string
  xpReward: number
  order: number
  hasQuiz: boolean
  quizId?: string
  completed: boolean
  completedAt?: string
}

// ── Course API ────────────────────────────────────────────────

function mapCourse(raw: Record<string, unknown>): CourseItem {
  return {
    id:             raw.id as string,
    slug:           raw.slug as string,
    title:          raw.title as string,
    description:    raw.description as string,
    imageUrl:       (raw.image_url as string) ?? '',
    instructorId:   (raw.instructor_id as string) ?? '',
    instructorName: (raw.instructor_name as string) ?? 'STEMQuest Team',
    isFree:         raw.is_free as boolean,
    price:          raw.price as number,
    currency:       (raw.currency as string) ?? 'USD',
    isPublished:    raw.is_published as boolean,
    category:       (raw.category as string) ?? '',
    difficulty:     (raw.difficulty as string) ?? 'beginner',
    tags:           (raw.tags as string[]) ?? [],
    totalLessons:   (raw.total_lessons as number) ?? 0,
    estimatedHours: (raw.estimated_hours as number) ?? 0,
    isEnrolled:     (raw.is_enrolled as boolean) ?? false,
    hasAccess:      (raw.has_access as boolean) ?? false,
    progress:       raw.progress ? mapProgress(raw.progress as Record<string, unknown>) : null,
    modules:        raw.modules
      ? (raw.modules as Record<string, unknown>[]).map(mapModule)
      : undefined,
  }
}

function mapProgress(raw: Record<string, unknown>): CourseProgress {
  return {
    completedLessons: (raw.completed_lessons as number) ?? 0,
    totalLessons:     (raw.total_lessons as number) ?? 0,
    percentage:       (raw.percentage as number) ?? 0,
  }
}

function mapModule(raw: Record<string, unknown>): ModuleItem {
  return {
    id:          raw.id as string,
    courseId:    (raw.course_id as string) ?? '',
    title:       raw.title as string,
    description: (raw.description as string) ?? '',
    order:       (raw.order as number) ?? 0,
    lessons:     raw.lessons
      ? (raw.lessons as Record<string, unknown>[]).map(mapLesson)
      : undefined,
  }
}

function mapLesson(raw: Record<string, unknown>): LessonItem {
  return {
    id:          raw.id as string,
    moduleId:    (raw.module_id as string) ?? '',
    courseId:    (raw.course_id as string) ?? '',
    title:       raw.title as string,
    summary:     (raw.summary as string) ?? '',
    content:     (raw.content as string) ?? '',
    videoUrl:    raw.video_url as string | undefined,
    difficulty:  (raw.difficulty as string) ?? 'beginner',
    xpReward:    (raw.xp_reward as number) ?? 20,
    order:       (raw.order as number) ?? 0,
    hasQuiz:     (raw.has_quiz as boolean) ?? false,
    quizId:      raw.quiz_id as string | undefined,
    completed:   (raw.completed as boolean) ?? false,
    completedAt: raw.completed_at as string | undefined,
  }
}

export const courseApi = {
  async list(): Promise<CourseItem[]> {
    const res = await get<{ courses: Record<string, unknown>[] }>('/api/courses')
    return res.courses.map(mapCourse)
  },
  async detail(slug: string): Promise<CourseItem> {
    const res = await get<{ course: Record<string, unknown> }>(`/api/courses/${slug}`)
    return mapCourse(res.course)
  },
  async enroll(slug: string): Promise<void> {
    await post(`/api/courses/${slug}/enroll`)
  },
  async getLesson(courseId: string, lessonId: string): Promise<LessonItem> {
    const res = await get<{ lesson: Record<string, unknown> }>(
      `/api/courses/${courseId}/lessons/${lessonId}`,
    )
    return mapLesson(res.lesson)
  },
  async completeLesson(courseId: string, lessonId: string): Promise<{
    alreadyCompleted: boolean
    xpAwarded: number
    newBadges: BadgeItem[]
    streak: StreakItem | null
    courseComplete: boolean
  }> {
    const res = await post<{
      already_completed: boolean
      xp_awarded: number
      new_badges: RawBadge[]
      streak: Record<string, unknown> | null
      course_complete: boolean
    }>(`/api/courses/${courseId}/lessons/${lessonId}/complete`)
    return {
      alreadyCompleted: res.already_completed,
      xpAwarded:        res.xp_awarded,
      newBadges:        (res.new_badges ?? []).map(mapBadge),
      streak:           res.streak ? mapStreak(res.streak) : null,
      courseComplete:   res.course_complete,
    }
  },
  async getQuiz(courseId: string, lessonId: string): Promise<QuizItem> {
    const res = await get<{ quiz: Record<string, unknown> }>(
      `/api/courses/${courseId}/lessons/${lessonId}/quiz`,
    )
    return mapQuiz(res.quiz)
  },
  async submitQuiz(
    courseId: string,
    lessonId: string,
    answers: Record<string, string>,
  ): Promise<QuizSubmitResult> {
    const res = await post<Record<string, unknown>>(
      `/api/courses/${courseId}/lessons/${lessonId}/quiz/submit`,
      { answers },
    )
    return mapQuizResult(res)
  },
}

// ── Streak ───────────────────────────────────────────────────

export interface StreakItem {
  id: string
  userId: string
  currentStreak: number
  longestStreak: number
  lastActivityDate: string
  updatedAt: string
}

function mapStreak(raw: Record<string, unknown>): StreakItem {
  return {
    id:               (raw.id as string) ?? '',
    userId:           (raw.user_id as string) ?? '',
    currentStreak:    (raw.current_streak as number) ?? 0,
    longestStreak:    (raw.longest_streak as number) ?? 0,
    lastActivityDate: (raw.last_activity_date as string) ?? '',
    updatedAt:        (raw.updated_at as string) ?? '',
  }
}

// ── Quiz Types ────────────────────────────────────────────────

export interface QuizItem {
  id: string
  lessonId: string
  title: string
  passingScore: number
  questions: QuestionItem[]
  bestAttempt: AttemptItem | null
}

export interface QuestionItem {
  id: string
  quizId: string
  text: string
  order: number
  options: OptionItem[]
}

export interface OptionItem {
  id: string
  questionId: string
  text: string
  order: number
}

export interface AttemptItem {
  id: string
  quizId: string
  lessonId: string
  userId: string
  score: number
  passed: boolean
  perfectScore: boolean
  answers: Record<string, string>
  recommendation: string
  xpAwarded: number
  completedAt: string
}

export interface QuizSubmitResult {
  attempt: AttemptItem
  score: number
  passed: boolean
  perfectScore: boolean
  correct: number
  total: number
  xpAwarded: number
  newBadges: BadgeItem[]
  recommendation: string
  recommendationText: string
  totalXp: number
}

function mapQuiz(raw: Record<string, unknown>): QuizItem {
  return {
    id:           raw.id as string,
    lessonId:     (raw.lesson_id as string) ?? '',
    title:        raw.title as string,
    passingScore: (raw.passing_score as number) ?? 70,
    questions:    ((raw.questions ?? []) as Record<string, unknown>[]).map(mapQuestion),
    bestAttempt:  raw.best_attempt
      ? mapAttempt(raw.best_attempt as Record<string, unknown>)
      : null,
  }
}

function mapQuestion(raw: Record<string, unknown>): QuestionItem {
  return {
    id:      raw.id as string,
    quizId:  (raw.quiz_id as string) ?? '',
    text:    raw.text as string,
    order:   (raw.order as number) ?? 0,
    options: ((raw.options ?? []) as Record<string, unknown>[]).map(mapOption),
  }
}

function mapOption(raw: Record<string, unknown>): OptionItem {
  return {
    id:         raw.id as string,
    questionId: (raw.question_id as string) ?? '',
    text:       raw.text as string,
    order:      (raw.order as number) ?? 0,
  }
}

function mapAttempt(raw: Record<string, unknown>): AttemptItem {
  return {
    id:             raw.id as string,
    quizId:         (raw.quiz_id as string) ?? '',
    lessonId:       (raw.lesson_id as string) ?? '',
    userId:         (raw.user_id as string) ?? '',
    score:          (raw.score as number) ?? 0,
    passed:         (raw.passed as boolean) ?? false,
    perfectScore:   (raw.perfect_score as boolean) ?? false,
    answers:        (raw.answers as Record<string, string>) ?? {},
    recommendation: (raw.recommendation as string) ?? 'next',
    xpAwarded:      (raw.xp_awarded as number) ?? 0,
    completedAt:    (raw.completed_at as string) ?? '',
  }
}

function mapQuizResult(raw: Record<string, unknown>): QuizSubmitResult {
  return {
    attempt:            mapAttempt(raw.attempt as Record<string, unknown>),
    score:              (raw.score as number) ?? 0,
    passed:             (raw.passed as boolean) ?? false,
    perfectScore:       (raw.perfect_score as boolean) ?? false,
    correct:            (raw.correct as number) ?? 0,
    total:              (raw.total as number) ?? 0,
    xpAwarded:          (raw.xp_awarded as number) ?? 0,
    newBadges:          ((raw.new_badges ?? []) as RawBadge[]).map(mapBadge),
    recommendation:     (raw.recommendation as string) ?? 'next',
    recommendationText: (raw.recommendation_text as string) ?? '',
    totalXp:            (raw.total_xp as number) ?? 0,
  }
}

// ── Gamification API ─────────────────────────────────────────

export interface LeaderboardEntry {
  rank: number
  userId: string
  name: string
  avatar: string
  totalXp: number
  badgeCount: number
  streak: number
}

export const gamificationApi = {
  async me(): Promise<GamificationSummary> {
    const res = await get<RawGamificationSummary>('/api/gamification/me')
    return mapGamification(res)
  },
  async leaderboard(limit = 20): Promise<LeaderboardEntry[]> {
    const res = await get<{ leaderboard: Record<string, unknown>[] }>(
      `/api/gamification/leaderboard?limit=${limit}`,
    )
    return res.leaderboard.map(r => ({
      rank:       (r.rank as number) ?? 0,
      userId:     (r.user_id as string) ?? '',
      name:       (r.name as string) ?? '',
      avatar:     (r.avatar as string) ?? '',
      totalXp:    (r.total_xp as number) ?? 0,
      badgeCount: (r.badge_count as number) ?? 0,
      streak:     (r.streak as number) ?? 0,
    }))
  },
  async myBadges(): Promise<BadgeSummaryItem[]> {
    const res = await get<{ badges: RawUserBadge[] }>('/api/gamification/my-badges')
    return (res.badges ?? []).map(mapBadgeSummary)
  },
}

// ── Billing API ───────────────────────────────────────────────

export const billingApi = {
  async createOrder(courseId: string): Promise<{
    approvalUrl: string
    paypalOrderId: string
    courseId: string
  }> {
    const res = await post<{
      approval_url: string
      paypal_order_id: string
      course_id: string
    }>('/api/billing/create-order', { course_id: courseId })
    return {
      approvalUrl:   res.approval_url,
      paypalOrderId: res.paypal_order_id,
      courseId:      res.course_id,
    }
  },
  async captureOrder(paypalOrderId: string): Promise<{
    courseId: string
    courseSlug: string
    courseTitle: string
    purchaseId: string
  }> {
    const res = await post<{
      course_id: string
      course_slug: string
      course_title: string
      purchase_id: string
    }>('/api/billing/capture', { paypal_order_id: paypalOrderId })
    return {
      courseId:    res.course_id,
      courseSlug:  res.course_slug,
      courseTitle: res.course_title,
      purchaseId:  res.purchase_id,
    }
  },
}

// ── Admin API ─────────────────────────────────────────────────

export interface AdminMetrics {
  users: { total: number; students: number; admins: number }
  courses: { total: number; published: number; draft: number }
  enrollments: { total: number; completions: number }
  revenue: { totalUsd: number }
  quizzes: { totalAttempts: number; passRatePct: number }
}

export interface AdminAnalyticsRow {
  courseId: string
  courseTitle: string
  isPublished: boolean
  isFree: boolean
  enrolled: number
  completed: number
  revenueUsd: number
}

export interface AdminUser {
  id: string
  email: string
  name: string
  role: 'student' | 'admin'
  avatar: string
  isActive: boolean
  createdAt: string
}

export interface AdminPurchase {
  id: string
  userId: string
  courseId: string
  amount: number
  currency: string
  paypalOrderId: string
  status: string
  createdAt: string
  completedAt?: string
}

export interface AdminWebhookEvent {
  id: string
  provider: string
  eventType: string
  status: string
  createdAt: string
  processedAt?: string
  errorMessage?: string
}

export interface AdminCourse {
  id: string
  slug: string
  title: string
  isPublished: boolean
  isFree: boolean
  price: number
  difficulty: string
  category: string
  totalLessons: number
}

function mapAdminMetrics(raw: Record<string, unknown>): AdminMetrics {
  const rev = raw.revenue as Record<string, unknown>
  const q   = raw.quizzes as Record<string, unknown>
  const u   = raw.users   as Record<string, unknown>
  const c   = raw.courses as Record<string, unknown>
  const e   = raw.enrollments as Record<string, unknown>
  return {
    users:       { total: Number(u.total), students: Number(u.students), admins: Number(u.admins) },
    courses:     { total: Number(c.total), published: Number(c.published), draft: Number(c.draft) },
    enrollments: { total: Number(e.total), completions: Number(e.completions) },
    revenue:     { totalUsd: Number(rev.total_usd) },
    quizzes:     { totalAttempts: Number(q.total_attempts), passRatePct: Number(q.pass_rate_pct) },
  }
}

function mapAdminUser(raw: Record<string, unknown>): AdminUser {
  return {
    id:        raw.id as string,
    email:     raw.email as string,
    name:      raw.name as string,
    role:      raw.role as 'student' | 'admin',
    avatar:    (raw.avatar as string) ?? '',
    isActive:  (raw.is_active as boolean) ?? true,
    createdAt: (raw.created_at as string) ?? '',
  }
}

function mapAdminCourse(raw: Record<string, unknown>): AdminCourse {
  return {
    id:           raw.id as string,
    slug:         (raw.slug as string) ?? '',
    title:        raw.title as string,
    isPublished:  (raw.is_published as boolean) ?? false,
    isFree:       (raw.is_free as boolean) ?? true,
    price:        (raw.price as number) ?? 0,
    difficulty:   (raw.difficulty as string) ?? 'beginner',
    category:     (raw.category as string) ?? '',
    totalLessons: (raw.total_lessons as number) ?? 0,
  }
}

function mapAdminPurchase(raw: Record<string, unknown>): AdminPurchase {
  return {
    id:            raw.id as string,
    userId:        (raw.user_id as string) ?? '',
    courseId:      (raw.course_id as string) ?? '',
    amount:        (raw.amount as number) ?? 0,
    currency:      (raw.currency as string) ?? 'USD',
    paypalOrderId: (raw.paypal_order_id as string) ?? '',
    status:        (raw.status as string) ?? 'pending',
    createdAt:     (raw.created_at as string) ?? '',
    completedAt:   raw.completed_at as string | undefined,
  }
}

function mapAdminWebhook(raw: Record<string, unknown>): AdminWebhookEvent {
  return {
    id:           raw.id as string,
    provider:     (raw.provider as string) ?? 'paypal',
    eventType:    (raw.event_type as string) ?? '',
    status:       (raw.status as string) ?? 'received',
    createdAt:    (raw.created_at as string) ?? '',
    processedAt:  raw.processed_at as string | undefined,
    errorMessage: raw.error_message as string | undefined,
  }
}

export const adminApi = {
  async metrics(): Promise<AdminMetrics> {
    const res = await get<Record<string, unknown>>('/api/admin/metrics')
    return mapAdminMetrics(res)
  },
  async analytics(): Promise<AdminAnalyticsRow[]> {
    const res = await get<{ courses: Record<string, unknown>[] }>('/api/admin/analytics')
    return (res.courses ?? []).map(r => ({
      courseId:    (r.course_id as string) ?? '',
      courseTitle: (r.course_title as string) ?? '',
      isPublished: (r.is_published as boolean) ?? false,
      isFree:      (r.is_free as boolean) ?? true,
      enrolled:    (r.enrolled as number) ?? 0,
      completed:   (r.completed as number) ?? 0,
      revenueUsd:  (r.revenue_usd as number) ?? 0,
    }))
  },
  async listUsers(page = 1, perPage = 50): Promise<{ items: AdminUser[]; total: number; pages: number; page: number }> {
    const res = await get<{ items: Record<string, unknown>[]; total: number; pages: number; page: number }>(
      `/api/admin/users?page=${page}&per_page=${perPage}`,
    )
    return { ...res, items: (res.items ?? []).map(mapAdminUser) }
  },
  async updateUserRole(userId: string, role: 'student' | 'admin'): Promise<AdminUser> {
    const res = await put<{ user: Record<string, unknown> }>(`/api/admin/users/${userId}/role`, { role })
    return mapAdminUser(res.user)
  },
  async grantEnrollment(userId: string, courseId: string): Promise<void> {
    await post(`/api/admin/users/${userId}/enroll`, { course_id: courseId })
  },
  async listCourses(): Promise<AdminCourse[]> {
    // Merge analytics (all courses including drafts) with the public catalog
    // (published-only, but rich fields). Draft-only courses appear from analytics
    // with limited field data; published courses get full detail from the catalog.
    const [analyticsRes, catalogRes] = await Promise.all([
      get<{ courses: Record<string, unknown>[] }>('/api/admin/analytics'),
      get<{ courses: Record<string, unknown>[] }>('/api/courses').catch(() => ({ courses: [] })),
    ])
    const catalogMap = new Map<string, Record<string, unknown>>()
    for (const c of catalogRes.courses ?? []) {
      catalogMap.set(c.id as string, c)
    }
    return (analyticsRes.courses ?? []).map(r => {
      const catalogEntry = catalogMap.get(r.course_id as string)
      if (catalogEntry) return mapAdminCourse(catalogEntry)
      // Draft course not in public catalog — use analytics fields only
      return {
        id:           (r.course_id as string) ?? '',
        slug:         '',
        title:        (r.course_title as string) ?? '',
        isPublished:  (r.is_published as boolean) ?? false,
        isFree:       (r.is_free as boolean) ?? true,
        price:        0,
        difficulty:   'beginner',
        category:     '',
        totalLessons: 0,
      } satisfies AdminCourse
    })
  },
  async createCourse(data: {
    title: string; description: string; slug: string; category: string
    difficulty: string; isFree: boolean; price: number; estimatedHours: number
  }): Promise<AdminCourse> {
    const res = await post<{ course: Record<string, unknown> }>('/api/admin/courses', {
      title: data.title,
      description: data.description,
      slug: data.slug,
      category: data.category,
      difficulty: data.difficulty,
      is_free: data.isFree,
      price: data.price,
      estimated_hours: data.estimatedHours,
    })
    return mapAdminCourse(res.course)
  },
  async togglePublish(courseId: string): Promise<AdminCourse> {
    const res = await post<{ course: Record<string, unknown> }>(`/api/admin/courses/${courseId}/publish`)
    return mapAdminCourse(res.course)
  },
  async createModule(courseId: string, title: string, description: string): Promise<{ id: string }> {
    const res = await post<{ module: Record<string, unknown> }>(`/api/admin/courses/${courseId}/modules`, { title, description })
    return { id: res.module.id as string }
  },
  async createLesson(moduleId: string, data: {
    title: string; summary: string; content: string; difficulty: string; xpReward: number
  }): Promise<{ id: string }> {
    const res = await post<{ lesson: Record<string, unknown> }>(`/api/admin/modules/${moduleId}/lessons`, {
      title:      data.title,
      summary:    data.summary,
      content:    data.content,
      difficulty: data.difficulty,
      xp_reward:  data.xpReward,
    })
    return { id: res.lesson.id as string }
  },
  async createQuiz(lessonId: string, data: {
    title: string; passingScore: number
    questions: Array<{ text: string; options: Array<{ text: string; isCorrect: boolean }> }>
  }): Promise<void> {
    await post(`/api/admin/lessons/${lessonId}/quiz`, {
      title:         data.title,
      passing_score: data.passingScore,
      questions:     data.questions.map((q, qi) => ({
        text:    q.text,
        order:   qi + 1,
        options: q.options.map((o, oi) => ({
          text:       o.text,
          is_correct: o.isCorrect,
          order:      oi + 1,
        })),
      })),
    })
  },
  async listPurchases(page = 1): Promise<{ items: AdminPurchase[]; total: number }> {
    const res = await get<{ items: Record<string, unknown>[]; total: number }>(
      `/api/admin/purchases?page=${page}`,
    )
    return { total: res.total, items: (res.items ?? []).map(mapAdminPurchase) }
  },
  async listWebhookEvents(page = 1): Promise<{ items: AdminWebhookEvent[]; total: number }> {
    const res = await get<{ items: Record<string, unknown>[]; total: number }>(
      `/api/admin/webhook-events?page=${page}`,
    )
    return { total: res.total, items: (res.items ?? []).map(mapAdminWebhook) }
  },
}
