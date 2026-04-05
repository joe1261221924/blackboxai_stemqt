import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  type ReactNode,
} from 'react'
import { authApi, ApiError } from '@/api/client'
import type { User, GamificationSummary } from '@/types'

interface AuthState {
  user:          User | null
  gamification:  GamificationSummary | null
  loading:       boolean
  error:         string | null
}

interface AuthContextValue extends AuthState {
  login:    (email: string, password: string) => Promise<void>
  register: (email: string, name: string, password: string) => Promise<void>
  logout:   () => Promise<void>
  refresh:  () => Promise<void>
  setGamification: (g: GamificationSummary) => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({
    user:         null,
    gamification: null,
    loading:      true,
    error:        null,
  })

  const refresh = useCallback(async () => {
    try {
      const data = await authApi.me()
      setState({
        user:         data.user,
        gamification: data.gamification,
        loading:      false,
        error:        null,
      })
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        setState({ user: null, gamification: null, loading: false, error: null })
      } else {
        setState(prev => ({ ...prev, loading: false }))
      }
    }
  }, [])

  useEffect(() => {
    refresh()
  }, [refresh])

  const login = useCallback(async (email: string, password: string) => {
    setState(prev => ({ ...prev, loading: true, error: null }))
    try {
      const data = await authApi.login(email, password)
      // Fetch full me (includes gamification for students)
      const me = await authApi.me()
      setState({
        user:         me.user ?? data.user,
        gamification: me.gamification,
        loading:      false,
        error:        null,
      })
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Login failed'
      setState(prev => ({ ...prev, loading: false, error: msg }))
      throw err
    }
  }, [])

  const register = useCallback(async (email: string, name: string, password: string) => {
    setState(prev => ({ ...prev, loading: true, error: null }))
    try {
      await authApi.register(email, name, password)
      const me = await authApi.me()
      setState({
        user:         me.user,
        gamification: me.gamification,
        loading:      false,
        error:        null,
      })
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Registration failed'
      setState(prev => ({ ...prev, loading: false, error: msg }))
      throw err
    }
  }, [])

  const logout = useCallback(async () => {
    try {
      await authApi.logout()
    } catch { /* ignore */ }
    setState({ user: null, gamification: null, loading: false, error: null })
  }, [])

  const setGamification = useCallback((g: GamificationSummary) => {
    setState(prev => ({ ...prev, gamification: g }))
  }, [])

  return (
    <AuthContext.Provider value={{ ...state, login, register, logout, refresh, setGamification }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>')
  return ctx
}
