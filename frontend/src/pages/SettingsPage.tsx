/** Settings — change password (FR-3); backup guidance lives in the README. */

import { useMutation, useQueryClient } from '@tanstack/react-query'
import { FileJson, Upload } from 'lucide-react'
import { type ChangeEvent, type FormEvent, useId, useState } from 'react'

import { Button, Dialog, Input } from '../components/ui'
import { ApiError, api } from '../lib/api'
import type { ImportReport } from '../lib/types'

export function SettingsPage() {
  const queryClient = useQueryClient()
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [localError, setLocalError] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)
  const [includeSensitive, setIncludeSensitive] = useState(false)
  const includeSensitiveId = useId()
  const importFileId = useId()
  const exportHref = `/api/export${includeSensitive ? '?include_sensitive=true' : ''}`

  const [importFile, setImportFile] = useState<File | null>(null)
  const [importData, setImportData] = useState<unknown>(null)
  const [parseError, setParseError] = useState<string | null>(null)
  const [confirmingImport, setConfirmingImport] = useState(false)
  const [importReport, setImportReport] = useState<ImportReport | null>(null)

  const importMutation = useMutation({
    mutationFn: () => api<ImportReport>('/api/import', { method: 'POST', body: importData }),
    onSuccess: (report) => {
      setImportReport(report)
      setConfirmingImport(false)
      setImportFile(null)
      setImportData(null)
      void queryClient.invalidateQueries({ queryKey: ['people'] })
    },
  })
  const importError = importMutation.error instanceof ApiError ? importMutation.error.message : null

  const onImportFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file) return
    setImportReport(null)
    importMutation.reset()
    setParseError(null)
    void file.text().then((text) => {
      try {
        setImportData(JSON.parse(text))
        setImportFile(file)
      } catch {
        setImportData(null)
        setImportFile(null)
        setParseError("That file isn't valid JSON.")
      }
    })
  }

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

        <div className="mt-4 border-t border-border pt-4">
          <p className="mb-3 text-sm text-muted">
            The JSON export below covers people, fields, and relationships. It does not include
            uploaded documents or photos — those are only covered by the <code className="font-mono text-xs">/data</code>{' '}
            directory backup above.
          </p>
          <div className="mb-3 flex items-start gap-2">
            <input
              id={includeSensitiveId}
              type="checkbox"
              checked={includeSensitive}
              onChange={(event) => setIncludeSensitive(event.target.checked)}
              className="mt-0.5 h-4 w-4 rounded border-border text-accent focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
            />
            <label htmlFor={includeSensitiveId} className="text-sm text-ink">
              Include sensitive field values
            </label>
          </div>
          {includeSensitive && (
            <p className="mb-3 text-sm text-accent">
              The exported file will contain sensitive field values in plain text. Store and
              share it with the same care as the database itself.
            </p>
          )}
          <a
            href={exportHref}
            className="inline-flex h-8 items-center justify-center gap-2 rounded-md border border-border bg-surface px-3 text-[13px] font-medium text-ink transition-colors hover:bg-surface-hover"
          >
            <FileJson size={14} aria-hidden /> Export all data (JSON)
          </a>
        </div>

        <div className="mt-4 border-t border-border pt-4">
          <h3 className="mb-2 text-sm font-semibold text-ink">Restore from export</h3>
          <p className="mb-3 text-sm text-muted">
            Importing adds people, fields, and relationships from a Dossier export file. It never
            deletes or overwrites anything already here — a person who already exists by name is
            skipped, and its relationships are reconnected to the existing record instead.
            Uploaded documents and photos aren't part of the export file, so they aren't restored,
            and sensitive field values that were exported without their value come back empty.
          </p>
          <div className="space-y-1.5">
            <label htmlFor={importFileId} className="label-caps block">
              Export file (JSON)
            </label>
            <input
              id={importFileId}
              type="file"
              accept="application/json,.json"
              onChange={onImportFileChange}
              className="block w-full text-sm text-ink file:mr-3 file:h-8 file:rounded-md file:border file:border-border file:bg-surface file:px-3 file:text-[13px] file:font-medium file:text-ink hover:file:bg-surface-hover"
            />
          </div>
          {parseError && (
            <p role="alert" className="mt-2 text-sm text-danger">
              {parseError}
            </p>
          )}
          {importFile && !parseError && (
            <div className="mt-3 flex items-center justify-between gap-3 rounded-md border border-border bg-surface-hover px-3 py-2">
              <span className="truncate text-sm text-ink">{importFile.name}</span>
              <Button type="button" size="sm" onClick={() => setConfirmingImport(true)}>
                <Upload size={14} aria-hidden /> Import
              </Button>
            </div>
          )}
          {importReport && (
            <div
              role="status"
              className="mt-3 space-y-1.5 rounded-md border border-border bg-surface-hover px-3 py-2 text-sm"
            >
              <p className="font-medium text-ink">Import complete</p>
              <ul className="list-disc space-y-0.5 pl-4 text-muted">
                <li>
                  {importReport.people_created} {importReport.people_created === 1 ? 'person' : 'people'} added
                  {importReport.people_skipped > 0
                    ? `, ${importReport.people_skipped} skipped (already existed)`
                    : ''}
                </li>
                <li>{importReport.fields_created} fields added</li>
                <li>
                  {importReport.relationships_created} relationships added
                  {importReport.relationships_skipped > 0
                    ? `, ${importReport.relationships_skipped} skipped`
                    : ''}
                </li>
              </ul>
              {(importReport.documents_skipped > 0 || importReport.sensitive_values_missing > 0) && (
                <p className="text-accent">
                  {importReport.documents_skipped > 0 &&
                    `${importReport.documents_skipped} document${importReport.documents_skipped === 1 ? '' : 's'} weren't restored — documents and photos aren't included in exports. `}
                  {importReport.sensitive_values_missing > 0 &&
                    `${importReport.sensitive_values_missing} sensitive field value${importReport.sensitive_values_missing === 1 ? '' : 's'} came back empty and need to be re-entered.`}
                </p>
              )}
              {importReport.warnings.length > 0 && (
                <ul className="list-disc space-y-0.5 pl-4 text-muted">
                  {importReport.warnings.map((warning, index) => (
                    <li key={index}>{warning}</li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </div>
      </div>

      {confirmingImport && importFile && (
        <Dialog title="Import from export file" onClose={() => setConfirmingImport(false)}>
          <div className="space-y-4">
            <p className="text-sm text-ink">
              Import <span className="font-medium">{importFile.name}</span>? This adds people,
              fields, and relationships from the file — it never deletes or overwrites anything
              already here. People who already exist by name are skipped.
            </p>
            {importError && (
              <p role="alert" className="text-sm text-danger">
                {importError}
              </p>
            )}
            <div className="flex justify-end gap-2">
              <Button
                type="button"
                variant="secondary"
                onClick={() => setConfirmingImport(false)}
                disabled={importMutation.isPending}
              >
                Cancel
              </Button>
              <Button type="button" onClick={() => importMutation.mutate()} disabled={importMutation.isPending}>
                {importMutation.isPending ? 'Importing…' : 'Import'}
              </Button>
            </div>
          </div>
        </Dialog>
      )}
    </div>
  )
}
