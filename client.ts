/**
 * STEMQuest API client.
 * All requests use credentials: 'include' so the JWT cookie is sent automatically.
 * Base URL is /api — proxied to Flask in dev, same origin in production.
 */

const BASE = '/api'

class ApiError extends Error {
  constructor(
    public status: number,
    public body:   unknown,
    message:       string,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

async function request<T>(
  method:  string,
  path:    string,
  body?:   unknown,
  signal?: AbortSignal,
): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  }

  const res = await fetch(`${BASE}${path}`, {
    method,
    credentials: 'include',
    headers,
    body:   body !== undefined ? JSON.stringify(body) : undefined,
    signal,
  })

  let data: unknown
  const contentType = res.headers.get('content-type') ?? ''
  if (contentType.includes('application/json')) {
    data = await res.json()
  } else {
    data = await res.text()
  }

  if (!res.ok) {
    const msg =
      (data as { message?: string })?.message ??
      `HTTP ${res.status}`
    throw new ApiError(res.status, data, msg)
  }

  return data as T
}

const get  = <T>(path: string, signal?: AbortSignal) => request<T>('GET',    path, undefined, signal)
const post = <T>(path: string, body?: unknown)        => request<T>('POST',   path, body)
const put  = <T>(path: string, body?: unknown)        => request<T>('PUT',    path, body)

export { get, post, put, ApiError }

// ── Auth ───────────────────────────────────────────────────────────────────

import type {
  MeResponse, User, GamificationSummary,
  Course, Lesson, LessonCompleteResult,
  Quiz, QuizSubmitResult,
  LeaderboardEntry, UserBadge,
  CreateOrderResult, CaptureOrderResult,
  AdminMetrics, AnalyticsCourse, Purchase,
  PaginatedResult, WebhookEvent, Enrollment,
} from '@/types'

export const authApi = {
  register: (email: string, name: string, password: string) =>
    post<{ message: string; user: User }>('/auth/register', { email, name, password }),

  login: (email: string, password: string) =>
    post<{ message: string; user: User }>('/auth/login', { email, password }),

  logout: () =>
    post<{ message: string }>('/auth/logout'),

  me: (signal?: AbortSignal) =>
    get<MeResponse>('/auth/me', signal),
}

// ── Courses ────────────────────────────────────────────────────────────────

export const coursesApi = {
  list: () =>
    get<{ courses: Course[]; total: number }>('/courses'),

  detail: (slug: string) =>
    get<{ course: Course }>(`/courses/${slug}`),

  enroll: (slug: string) =>
    post<{ message: string; enrollment: Enrollment }>(`/courses/${slug}/enroll`),

  getLesson: (courseId: string, lessonId: string) =>
    get<{ lesson: Lesson }>(`/courses/${courseId}/lessons/${lessonId}`),

  completeLesson: (courseId: string, lessonId: string) =>
    post<LessonCompleteResult>(`/courses/${courseId}/lessons/${lessonId}/complete`),

  getQuiz: (courseId: string, lessonId: string) =>
    get<{ quiz: Quiz }>(`/courses/${courseId}/lessons/${lessonId}/quiz`),

  submitQuiz: (courseId: string, lessonId: string, answers: Record<string, string>) =>
    post<QuizSubmitResult>(`/courses/${courseId}/lessons/${lessonId}/quiz/submit`, { answers }),
}

// ── Gamification ───────────────────────────────────────────────────────────

export const gamificationApi = {
  me: () =>
    get<GamificationSummary>('/gamification/me'),

  leaderboard: (limit = 20) =>
    get<{ leaderboard: LeaderboardEntry[]; count: number }>(`/gamification/leaderboard?limit=${limit}`),

  myBadges: () =>
    get<{ badges: UserBadge[]; count: number }>('/gamification/my-badges'),

  grantPoints: (userId: string, points: number, reason: string) =>
    post<{ message: string }>('/gamification/grant-points', { user_id: userId, points, reason }),
}

// ── Billing ────────────────────────────────────────────────────────────────

export const billingApi = {
  createOrder: (courseId: string) =>
    post<CreateOrderResult>('/billing/create-order', { course_id: courseId }),

  captureOrder: (providerOrderId: string) =>
    post<CaptureOrderResult>('/billing/capture', { provider_order_id: providerOrderId }),
}

// ── Admin ──────────────────────────────────────────────────────────────────

export const adminApi = {
  // Content
  createCourse: (data: Record<string, unknown>) =>
    post<{ course: Course }>('/admin/courses', data),

  updateCourse: (courseId: string, data: Record<string, unknown>) =>
    put<{ course: Course }>(`/admin/courses/${courseId}`, data),

  publishCourse: (courseId: string) =>
    post<{ message: string; course: Course }>(`/admin/courses/${courseId}/publish`),

  createModule: (courseId: string, data: Record<string, unknown>) =>
    post<{ module: unknown }>(`/admin/courses/${courseId}/modules`, data),

  createLesson: (moduleId: string, data: Record<string, unknown>) =>
    post<{ lesson: unknown }>(`/admin/modules/${moduleId}/lessons`, data),

  createQuiz: (lessonId: string, data: Record<string, unknown>) =>
    post<{ quiz: unknown }>(`/admin/lessons/${lessonId}/quiz`, data),

  // Users
  listUsers: (page = 1, perPage = 50) =>
    get<PaginatedResult<User>>(`/admin/users?page=${page}&per_page=${perPage}`),

  updateRole: (userId: string, role: string) =>
    put<{ user: User }>(`/admin/users/${userId}/role`, { role }),

  grantEnrollment: (userId: string, courseId: string) =>
    post<{ enrollment: Enrollment }>(`/admin/users/${userId}/enroll`, { course_id: courseId }),

  // Analytics
  metrics: () =>
    get<AdminMetrics>('/admin/metrics'),

  analytics: () =>
    get<{ courses: AnalyticsCourse[] }>('/admin/analytics'),

  // Billing
  purchases: (page = 1, perPage = 50) =>
    get<PaginatedResult<Purchase>>(`/admin/purchases?page=${page}&per_page=${perPage}`),

  webhookEvents: (page = 1, perPage = 50) =>
    get<PaginatedResult<WebhookEvent>>(`/admin/webhook-events?page=${page}&per_page=${perPage}`),
}
