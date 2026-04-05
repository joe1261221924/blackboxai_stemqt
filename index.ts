// ─── User / Auth ───────────────────────────────────────────────────────────

export type UserRole = 'student' | 'admin'

export interface User {
  id:             string
  email:          string
  name:           string
  role:           UserRole
  avatar:         string
  is_active:      boolean
  email_verified: boolean
  created_at:     string
}

export interface GamificationSummary {
  total_xp:       number
  rank:           number
  current_streak: number
  longest_streak: number
  badge_count:    number
  badges:         UserBadge[]
  enrollments:    number
}

export interface MeResponse {
  user:          User
  gamification:  GamificationSummary | null
}

// ─── Courses ───────────────────────────────────────────────────────────────

export type Difficulty = 'beginner' | 'intermediate' | 'advanced'

export interface CourseProgress {
  completed_lessons: number
  total_lessons:     number
  percentage:        number
}

export interface Course {
  id:               string
  slug:             string
  title:            string
  description:      string
  image_url:        string | null
  is_premium:       boolean
  price:            number | null
  currency:         string
  published:        boolean
  category:         string
  difficulty:       Difficulty
  tags:             string[]
  total_lessons:    number
  estimated_hours:  number
  created_at:       string
  updated_at:       string
  // per-user fields (present when authenticated)
  is_enrolled?:     boolean
  has_access?:      boolean
  progress?:        CourseProgress | null
  modules?:         Module[]
}

export interface Module {
  id:          string
  course_id:   string
  title:       string
  description: string
  sort_order:  number
  lessons:     LessonSummary[]
}

export interface LessonSummary {
  id:           string
  title:        string
  sort_order:   number
  difficulty_level: string
  xp_reward:    number
  has_quiz:     boolean
  completed:    boolean
  completed_at: string | null
}

export interface Lesson {
  id:              string
  title:           string
  content_body:    string
  difficulty_level: string
  xp_reward:       number
  sort_order:       number
  has_quiz:         boolean
  quiz_id:          string | null
  completed:        boolean
  completed_at:     string | null
}

export interface LessonCompleteResult {
  already_completed: boolean
  xp_awarded:        number
  new_badges:        Badge[]
  streak:            StreakInfo | null
  course_complete:   boolean
}

export interface StreakInfo {
  current_streak:     number
  longest_streak:     number
  last_activity_date: string | null
}

// ─── Quiz ──────────────────────────────────────────────────────────────────

export interface QuizOption {
  id:          string
  question_id: string
  option_text: string
  sort_order:  number
}

export interface QuizQuestion {
  id:          string
  quiz_id:     string
  prompt:      string
  explanation: string | null
  sort_order:  number
  options:     QuizOption[]
}

export interface Quiz {
  id:           string
  lesson_id:    string
  title:        string
  passing_score: number
  xp_reward:    number
  questions:    QuizQuestion[]
  best_attempt: QuizAttempt | null
}

export interface QuizAttempt {
  id:             string
  user_id:        string
  quiz_id:        string
  lesson_id:      string
  score:          number
  passed:         boolean
  perfect:        boolean
  answers:        Record<string, string>
  recommendation: 'review' | 'next' | 'advanced'
  xp_awarded:     number
  created_at:     string
}

export interface QuizSubmitResult {
  attempt:              QuizAttempt
  score:                number
  passed:               boolean
  perfect_score:        boolean
  correct:              number
  total:                number
  xp_awarded:           number
  new_badges:           Badge[]
  recommendation:       'review' | 'next' | 'advanced'
  recommendation_text:  string
  total_xp:             number
}

// ─── Gamification ──────────────────────────────────────────────────────────

export interface Badge {
  id:              string
  slug:            string
  title:           string
  description:     string
  points_required: number | null
  created_at:      string
}

export interface UserBadge {
  id:         string
  user_id:    string
  badge_id:   string
  awarded_at: string
  created_at: string
  badge:      Badge | null
}

export interface LeaderboardEntry {
  rank:        number
  user_id:     string
  name:        string
  avatar:      string
  total_xp:    number
  badge_count: number
  streak:      number
}

// ─── Billing ───────────────────────────────────────────────────────────────

export interface CreateOrderResult {
  approval_url:      string
  provider_order_id: string
  course_id:         string
}

export interface CaptureOrderResult {
  course_id:    string
  course_slug:  string
  course_title: string
  purchase_id:  string
}

export interface Purchase {
  id:                  string
  user_id:             string
  course_id:           string
  amount:              number
  currency:            string
  provider:            string
  provider_payment_id: string | null
  status:              'pending' | 'completed' | 'failed' | 'refunded'
  created_at:          string
  completed_at:        string | null
}

// ─── Admin ─────────────────────────────────────────────────────────────────

export interface AdminMetrics {
  users: {
    total:    number
    students: number
    admins:   number
  }
  courses: {
    total:     number
    published: number
    draft:     number
  }
  enrollments: {
    total:              number
    completions:        number
    lesson_completions: number
  }
  revenue: {
    total_usd: number
  }
  quizzes: {
    total_attempts: number
    pass_rate_pct:  number
  }
  gamification: {
    total_xp_awarded: number
  }
}

export interface AnalyticsCourse {
  course_id:          string
  course_title:       string
  published:          boolean
  is_premium:         boolean
  enrolled:           number
  completed:          number
  lesson_completions: number
  revenue_usd:        number
}

export interface PaginatedResult<T> {
  items:    T[]
  total:    number
  page:     number
  per_page: number
}

export interface WebhookEvent {
  id:          string
  event_id:    string
  event_type:  string
  processed:   boolean
  raw_payload: string
  created_at:  string
}

export interface Enrollment {
  id:         string
  user_id:    string
  course_id:  string
  source:     string
  is_active:  boolean
  created_at: string
  completed_at: string | null
}
