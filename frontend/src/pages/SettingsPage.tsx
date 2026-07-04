/** Settings — change password (FR-3); backup guidance lives in the README. */

import { useMutation } from '@tanstack/react-query'
import { type FormEvent, useState } from 'react'

import { Button, Input } from '../components/ui'
import { ApiError, api } from '../lib/api'

export function SettingsPage() {
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [localError, setLocalError] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)

  const change = useMutation({
    mutationFn: () =>
      api<void>('/api/auth/password', {
        method: 'POST',
        body: { current_password: currentPassword, new_password: newPassword },
      }),
    onSuccess: () => {
      setSaved(true)
      setLocalError(null)
      setCurrentPassword('')
      setNewPassword('')
      setConfirm('')
    },
  })

  const onSubmit = (event: FormEvent) => {
    event.preventDefault()
    setSaved(false)
    if (newPassword !== confirm) {
      setLocalError('New passwords do not match')
      return
    }
    setLocalError(null)
    change.mutate()
  }

  const error = localError ?? (change.error instanceof ApiError ? change.error.message : null)

  return (
    <div className="mx-auto max-w-md space-y-6">
      <h1 className="font-display text-3xl font-semibold">Settings</h1>
      <div className="rounded-lg border border-border bg-surface p-6 shadow-(--shadow-card)">
        <h2 className="mb-4 font-display text-lg font-semibold">Change password</h2>
        <form onSubmit={onSubmit} className="space-y-4">
          <Input
            id="current"
            label="Current password"
            type="password"
            value={currentPassword}
            onChange={(event) => setCurrentPassword(event.target.value)}
            autoComplete="current-password"
            required
          />
          <Input
            id="new"
            label="New password"
            type="password"
            value={newPassword}
            onChange={(event) => setNewPassword(event.target.value)}
            autoComplete="new-password"
            minLength={8}
            required
          />
          <Input
            id="confirm"
            label="Confirm new password"
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
          {saved && (
            <p role="status" className="text-sm text-success">
              Password changed. Other sessions have been signed out.
            </p>
          )}
          <Button type="submit" disabled={change.isPending}>
            {change.isPending ? 'Saving…' : 'Change password'}
          </Button>
        </form>
      </div>
      <div className="rounded-lg border border-border bg-surface p-6 shadow-(--shadow-card)">
        <h2 className="mb-2 font-display text-lg font-semibold">Backups</h2>
        <p className="text-sm text-muted">
          All data lives in the <code className="font-mono text-xs">/data</code> volume (database +
          uploads). Back up that directory while the container is stopped — see the README for the
          full procedure.
        </p>
      </div>
    </div>
  )
}
