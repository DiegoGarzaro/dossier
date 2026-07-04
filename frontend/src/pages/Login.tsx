/** Login screen — centered card on the paper background. */

import { useMutation, useQueryClient } from '@tanstack/react-query'
import { FolderLock } from 'lucide-react'
import { type FormEvent, useState } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'

import { Button, Input, Spinner } from '../components/ui'
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
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['auth'] })
      navigate('/')
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
      <div className="w-full max-w-sm rounded-lg border border-border bg-surface p-8 shadow-(--shadow-card)">
        <div className="mb-6 flex items-center gap-2">
          <FolderLock size={22} className="text-accent" aria-hidden />
          <h1 className="font-display text-2xl font-semibold">Dossier</h1>
        </div>
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
      </div>
    </div>
  )
}
