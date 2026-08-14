/** Login screen — centered card on the paper background. */

import { useMutation, useQueryClient } from '@tanstack/react-query'
import { FolderLock } from 'lucide-react'
import { type FormEvent, useState } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'

import { Button, Card, Input, Spinner } from '../components/ui'
import { ApiError, api } from '../lib/api'
import type { AuthStatus } from '../lib/types'
import { useAuthStatus } from '../router'

export function Login() {
  const { data: status, isPending } = useAuthStatus()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const login = useMutation({
    mutationFn: () =>
      api<AuthStatus>('/api/auth/login', { method: 'POST', body: { username, password } }),
    // The login response *is* the authoritative auth status, so seed the cache
    // with it rather than re-deriving it from a second round-trip: a failed or
    // stale `GET /api/auth/status` used to bounce the user straight back to a
    // freshly-mounted (= cleared) form, session cookie set and no error shown
    // — the "I have to refresh to get in" bug (G-48).
    onSuccess: (status) => {
      queryClient.setQueryData(['auth'], status)
      navigate('/', { replace: true })
    },
  })

  if (isPending) return <Spinner />
  if (status && !status.initialized) return <Navigate to="/setup" replace />
  if (status?.authenticated) return <Navigate to="/" replace />

  const onSubmit = (event: FormEvent) => {
    event.preventDefault()
    login.mutate()
  }

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <Card className="w-full max-w-sm p-6 sm:p-8">
        <div className="mb-1 flex items-center gap-2.5">
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-accent-fill text-accent">
            <FolderLock size={20} aria-hidden />
          </span>
          <h1 className="font-display text-h1 font-semibold">Dossier</h1>
        </div>
        <p className="mb-6 font-display text-sm text-muted italic">Your people, on file.</p>
        <form onSubmit={onSubmit} className="space-y-4">
          <Input
            id="username"
            label="Username"
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            autoComplete="username"
            autoFocus
            required
          />
          <Input
            id="password"
            label="Password"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            autoComplete="current-password"
            required
          />
          {login.error instanceof ApiError && (
            <p role="alert" className="text-sm text-danger">
              {login.error.message}
            </p>
          )}
          <Button type="submit" className="w-full" disabled={login.isPending}>
            {login.isPending ? 'Signing in…' : 'Sign in'}
          </Button>
        </form>
      </Card>
    </div>
  )
}
