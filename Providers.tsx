'use client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useState } from 'react'
import { AuthProvider } from '@/contexts/AuthContext'

export default function Providers({ children }: { children: React.ReactNode }) {
  // Create a stable QueryClient per browser session
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 30_000,          // 30 s — avoid redundant refetches
            retry: (failureCount, err) => {
              // Don't retry 401/403/404 — they are expected errors
              if (err && typeof err === 'object' && 'status' in err) {
                const status = (err as { status: number }).status
                if (status === 401 || status === 403 || status === 404) return false
              }
              return failureCount < 2
            },
          },
        },
      }),
  )

  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>{children}</AuthProvider>
    </QueryClientProvider>
  )
}
