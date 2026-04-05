// ============================================================
// STEMQuest — Shared TypeScript Types
// Re-exported from lib/api.ts for convenience.
// All types are aligned to real backend snake→camel-mapped shapes.
// ============================================================

// Re-export everything from the real API client so that components
// and pages only need to import from one place.
export type {
  AuthUser,
  GamificationSummary,
  BadgeSummaryItem,
  BadgeItem,
  MeResponse,
  CourseItem,
  CourseProgress,
  ModuleItem,
  LessonItem,
  StreakItem,
  QuizItem,
  QuestionItem,
  OptionItem,
  AttemptItem,
  QuizSubmitResult,
  LeaderboardEntry,
  AdminMetrics,
  AdminAnalyticsRow,
  AdminUser,
  AdminPurchase,
  AdminWebhookEvent,
  AdminCourse,
} from './api'

// ── Scalar types shared across frontend ─────────────────────
export type UserRole       = 'student' | 'admin'
export type Difficulty     = 'beginner' | 'intermediate' | 'advanced'
export type PurchaseStatus = 'pending' | 'completed' | 'failed' | 'refunded'
export type WebhookStatus  = 'received' | 'processed' | 'failed'
export type Recommendation = 'review' | 'next' | 'advanced'

// ── Badge type used by BadgeCard (matches BadgeItem + optional earnedAt) ──
export interface Badge {
  id:          string
  name:        string
  description: string
  icon:        string
  category:    string
  criteria:    string
  threshold?:  number
  color:       string
  earnedAt?:   string
}
