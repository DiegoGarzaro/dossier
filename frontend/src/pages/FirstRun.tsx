/** First-run screen — create the initial admin account (FR-5). */

import { useMutation, useQueryClient } from '@tanstack/react-query'
import { FolderLock } from 'lucide-react'
import { type FormEvent, useState } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'

import { Button, Card, Input, Spinner } from '../components/ui'
import { ApiError, api } from '../lib/api'
import type { AuthStatus } from '../lib/types'
import { useAuthStatus } from '../router'

export function FirstRun() {
  const { data: status, isPending } = useAuthStatus()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [localError, setLocalError] = useState<string | null>(null)
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const setup = useMutation({
    mutationFn: () =>
      api<AuthStatus>('/api/auth/setup', { method: 'POST', body: { username, password } }),
    // Same rule as Login: trust the response we just got, don't re-fetch it (G-48).
    onSuccess: (status) => {
      queryClient.setQueryData(['auth'], status)
      navigate('/', { replace: true })
    },
  })

  if (isPending) return <Spinner />
  if (status?.initialized) return <Navigate to="/login" replace />

  const onSubmit = (event: FormEvent) => {
    event.preventDefault()
    if (password !== confirm) {
      setLocalError('Passwords do not match')
      return
    }
    if (password.length < 8) {
      setLocalError('Password must be at least 8 characters')
      return
    }
    setLocalError(null)
    setup.mutate()
  }

  const error = localError ?? (setup.error instanceof ApiError ? setup.error.message : null)

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <Card className="w-full max-w-sm p-6 sm:p-8">
        <div className="mb-2 flex items-center gap-2.5">
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-accent-fill text-accent">
            <FolderLock size={20} aria-hidden />
          </span>
          <h1 className="font-display text-h1 font-semibold">Welcome</h1>
        </div>
        <p className="mb-6 text-sm text-muted">
          Set up the administrator account for Dossier. There are no default credentials.
        </p>
        <form onSubmit={onSubmit} className="space-y-4">
          <Input
            id="username"
            label="Username"
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            autoComplete="username"
            minLength={3}
            autoFocus
            required
          />
          <Input
            id="password"
            label="Password"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            autoComplete="new-password"
            required
          />
          <Input
            id="confirm"
            label="Confirm password"
            type="password"
            value={confirm}
            onChange={(event) => setConfirm(event.target.value)}
            autoComplete="new-password"
            required
          />
          {error && (
            <p role="alert" className="text-sm text-danger">
              {error}
            </p>
          )}
          <Button type="submit" className="w-full" disabled={setup.isPending}>
            {setup.isPending ? 'Creating…' : 'Create account'}
          </Button>
        </form>
      </Card>
    </div>
  )
}
