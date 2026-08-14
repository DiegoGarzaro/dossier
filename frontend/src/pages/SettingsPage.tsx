/** Settings — change password (FR-3), data summary, encrypted backup/restore
 * (Phase 3), JSON export/import, and tag admin; manual `/data` guidance lives
 * in the README. */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Check, FileJson, Lock, Pencil, Trash2, Unlock, Upload, X } from 'lucide-react'
import { type ChangeEvent, type FormEvent, useId, useState } from 'react'

import { Button, Card, Dialog, IconButton, Input, SectionHeading } from '../components/ui'
import { ApiError, api, apiBlob } from '../lib/api'
import type { ImportReport, SystemSummary, Tag } from '../lib/types'

/** Formats a byte count as a human-readable KB/MB string (no added dependency). */
function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

/** Triggers a browser download of `blob` as `filename`, then releases the
 * temporary object URL so it doesn't leak for the life of the tab. */
function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

function backupFilename(): string {
  const date = new Date().toISOString().slice(0, 10)
  return `dossier-backup-${date}.dossier`
}

/** "Your data" summary card: counts + sizes for context before backing up. */
function DataSummaryCard() {
  const summary = useQuery({
    queryKey: ['summary'],
    queryFn: () => api<SystemSummary>('/api/system/summary'),
  })

  return (
    <Card className="p-4 sm:p-6">
      <h2 className="mb-4 font-display text-h2 font-semibold">Your data</h2>
      {summary.isPending ? (
        <p className="text-sm text-muted">Loading…</p>
      ) : summary.data ? (
        <>
          <dl className="grid grid-cols-2 gap-x-4 gap-y-3 sm:grid-cols-3">
            <div>
              <dt className="label-caps">People</dt>
              <dd className="font-display text-h2 font-semibold text-ink">{summary.data.people}</dd>
            </div>
            <div>
              <dt className="label-caps">Fields</dt>
              <dd className="font-display text-h2 font-semibold text-ink">{summary.data.fields}</dd>
            </div>
            <div>
              <dt className="label-caps">Documents</dt>
              <dd className="font-display text-h2 font-semibold text-ink">{summary.data.documents}</dd>
            </div>
            <div>
              <dt className="label-caps">Relationships</dt>
              <dd className="font-display text-h2 font-semibold text-ink">{summary.data.relationships}</dd>
            </div>
            <div>
              <dt className="label-caps">Tags</dt>
              <dd className="font-display text-h2 font-semibold text-ink">{summary.data.tags}</dd>
            </div>
          </dl>
          <div className="mt-4 flex flex-wrap gap-x-6 gap-y-1 border-t border-border pt-4 text-sm text-muted">
            <span>Uploads: {formatBytes(summary.data.uploads_bytes)}</span>
            <span>Database: {formatBytes(summary.data.database_bytes)}</span>
          </div>
          <p className="mt-2 text-sm text-muted">
            {summary.data.last_backup_at
              ? `Last backup: ${summary.data.last_backup_at.slice(0, 10)}`
              : 'No backup taken yet'}
          </p>
          <p className="mt-1 text-sm text-muted">Version {summary.data.version}</p>
        </>
      ) : null}
    </Card>
  )
}

/** One row in the tags admin list: inline rename (pencil → input → save/cancel,
 * mirroring FieldRow/DocumentRow) and delete-with-confirmation. */
function TagRow({ tag }: { tag: Tag }) {
  const [editing, setEditing] = useState(false)
  const [name, setName] = useState(tag.name)
  const [renameError, setRenameError] = useState<string | null>(null)
  const [confirmingDelete, setConfirmingDelete] = useState(false)
  const queryClient = useQueryClient()

  // A rename/delete changes a label shown in the filter bar, on the index
  // cards, *and* as a chip on every ID-card wearing it. `['person', id]` is a
  // different key prefix from `['people']`, so those cards were left stale and
  // kept showing the old name until something happened to refetch them (G-55).
  // `refetchType: 'all'` reaches the screens that are currently unmounted.
  const invalidate = () => {
    for (const key of [['tags'], ['people'], ['person']]) {
      queryClient.invalidateQueries({ queryKey: key, refetchType: 'all' })
    }
  }

  const rename = useMutation({
    mutationFn: () => api<Tag>(`/api/tags/${tag.id}`, { method: 'PATCH', body: { name } }),
    onSuccess: () => {
      setEditing(false)
      setRenameError(null)
      invalidate()
    },
    onError: (error) => setRenameError(error.message),
  })

  const remove = useMutation({
    mutationFn: () => api<void>(`/api/tags/${tag.id}`, { method: 'DELETE' }),
    onSuccess: () => {
      setConfirmingDelete(false)
      invalidate()
    },
  })

  if (editing) {
    return (
      <form
        onSubmit={(event) => {
          event.preventDefault()
          rename.mutate()
        }}
        className="flex items-center gap-2 px-4 py-3 odd:bg-surface-subtle sm:gap-3 sm:px-6"
      >
        <div className="min-w-0 flex-1">
          <input
            aria-label="Tag name"
            className="h-9 w-full rounded-sm border border-border bg-surface px-3 text-sm focus:border-accent"
            value={name}
            onChange={(event) => setName(event.target.value)}
            autoFocus
            required
          />
          {renameError && (
            <p role="alert" className="mt-1 text-xs text-danger">
              {renameError}
            </p>
          )}
        </div>
        <Button type="submit" size="sm" aria-label="Save tag name" disabled={rename.isPending}>
          <Check size={15} />
        </Button>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          aria-label="Cancel rename"
          onClick={() => {
            setEditing(false)
            setName(tag.name)
            setRenameError(null)
          }}
        >
          <X size={15} />
        </Button>
      </form>
    )
  }

  return (
    <div className="flex items-center gap-1 px-4 py-2 odd:bg-surface-subtle sm:gap-3 sm:px-6 sm:py-3">
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium">{tag.name}</p>
        <p className="text-xs text-muted">
          {tag.person_count} {tag.person_count === 1 ? 'person' : 'people'}
        </p>
      </div>
      <IconButton
        label={`Rename ${tag.name}`}
        className="text-subtle hover:bg-surface-hover hover:text-ink"
        onClick={() => setEditing(true)}
      >
        <Pencil size={16} />
      </IconButton>
      <IconButton
        label={`Delete ${tag.name}`}
        className="text-subtle hover:bg-surface-hover hover:text-danger"
        onClick={() => setConfirmingDelete(true)}
      >
        <Trash2 size={16} />
      </IconButton>
      {confirmingDelete && (
        <Dialog title="Delete tag?" onClose={() => setConfirmingDelete(false)}>
          <p className="mb-4 text-sm text-muted">
            “{tag.name}” is worn by {tag.person_count} {tag.person_count === 1 ? 'person' : 'people'}
            . Deleting it only removes the label — it does not delete any person.
          </p>
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={() => setConfirmingDelete(false)}>
              Cancel
            </Button>
            <Button variant="danger" onClick={() => remove.mutate()} disabled={remove.isPending}>
              {remove.isPending ? 'Deleting…' : 'Delete'}
            </Button>
          </div>
        </Dialog>
      )}
    </div>
  )
}

/** Tags admin block: create-on-type lives on the ID-card; this is where a
 * mistyped or unwanted tag gets fixed or removed (PLAN.md "tags & favorites"). */
function TagsSection() {
  const tags = useQuery({
    queryKey: ['tags'],
    queryFn: () => api<Tag[]>('/api/tags'),
  })

  const sorted = [...(tags.data ?? [])].sort((a, b) => a.name.localeCompare(b.name))

  return (
    <Card className="overflow-hidden">
      <SectionHeading title="Tags" count={sorted.length} />
      {tags.isPending ? (
        <p className="px-4 py-6 text-sm text-muted sm:px-6">Loading…</p>
      ) : sorted.length === 0 ? (
        <p className="px-4 py-6 text-sm text-muted sm:px-6">
          No tags yet. Add one from a person's card.
        </p>
      ) : (
        sorted.map((tag) => <TagRow key={tag.id} tag={tag} />)
      )}
    </Card>
  )
}

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

  const [backupPassphrase, setBackupPassphrase] = useState('')
  const [backupConfirm, setBackupConfirm] = useState('')
  const backupPassphraseId = useId()
  const backupConfirmId = useId()
  const backupValid = backupPassphrase.length >= 12 && backupPassphrase === backupConfirm

  const backupMutation = useMutation({
    mutationFn: () => apiBlob('/api/backup', { body: { passphrase: backupPassphrase } }),
    onSuccess: (blob) => {
      downloadBlob(blob, backupFilename())
      void queryClient.invalidateQueries({ queryKey: ['summary'] })
    },
    // The passphrase only ever lives in memory for the life of the request,
    // win or lose — never in a URL, a query string, or localStorage.
    onSettled: () => {
      setBackupPassphrase('')
      setBackupConfirm('')
    },
  })
  const backupError = backupMutation.error instanceof ApiError ? backupMutation.error.message : null

  const onBackupSubmit = (event: FormEvent) => {
    event.preventDefault()
    if (backupValid) backupMutation.mutate()
  }

  const [restoreFile, setRestoreFile] = useState<File | null>(null)
  const [restorePassphrase, setRestorePassphrase] = useState('')
  const [confirmingRestore, setConfirmingRestore] = useState(false)
  const [restoreReport, setRestoreReport] = useState<ImportReport | null>(null)
  const restoreFileId = useId()
  const restorePassphraseId = useId()
  const restoreValid = restoreFile !== null && restorePassphrase.length >= 12

  const restoreMutation = useMutation({
    mutationFn: () => {
      const form = new FormData()
      form.append('file', restoreFile as File)
      form.append('passphrase', restorePassphrase)
      return api<ImportReport>('/api/restore', { method: 'POST', form })
    },
    onSuccess: (report) => {
      setRestoreReport(report)
      setConfirmingRestore(false)
      setRestoreFile(null)
      setRestorePassphrase('')
      void queryClient.invalidateQueries({ queryKey: ['people'] })
      void queryClient.invalidateQueries({ queryKey: ['tags'] })
      void queryClient.invalidateQueries({ queryKey: ['summary'] })
    },
    // Deliberately no onError side effect: the dialog and file/passphrase stay
    // put (e.g. a wrong passphrase) so the user can correct and retry.
  })
  const restoreError = restoreMutation.error instanceof ApiError ? restoreMutation.error.message : null

  const onRestoreFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file) return
    setRestoreReport(null)
    restoreMutation.reset()
    setRestoreFile(file)
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
    <div className="mx-auto max-w-2xl space-y-6">
      <h1 className="font-display text-h2 font-semibold sm:text-h1">Settings</h1>
      <Card className="p-4 sm:p-6">
        <h2 className="mb-4 font-display text-h2 font-semibold">Change password</h2>
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
      </Card>

      <DataSummaryCard />

      <Card className="p-4 sm:p-6">
        <h2 className="mb-2 font-display text-h2 font-semibold">Encrypted backup</h2>
        <p className="mb-1 text-sm text-muted">
          Creates one file with everything — people, fields, relationships, tags, documents,
          photos, and sensitive field values — encrypted with the passphrase below.
        </p>
        <p className="mb-1 text-sm text-muted">
          The passphrase is <strong className="font-medium text-ink">never stored</strong>. If
          it's lost, this file cannot be opened by anyone, including us — write the passphrase
          down somewhere safe.
        </p>
        <p className="mb-4 text-sm text-muted">
          This restores your data, not your login account — the{' '}
          <code className="font-mono text-xs">/data</code> directory backup below still covers
          the account itself.
        </p>
        <form onSubmit={onBackupSubmit} className="space-y-4">
          <Input
            id={backupPassphraseId}
            label="Passphrase (minimum 12 characters)"
            type="password"
            value={backupPassphrase}
            onChange={(event) => setBackupPassphrase(event.target.value)}
            autoComplete="new-password"
            minLength={12}
            required
          />
          <Input
            id={backupConfirmId}
            label="Confirm passphrase"
            type="password"
            value={backupConfirm}
            onChange={(event) => setBackupConfirm(event.target.value)}
            autoComplete="new-password"
            required
          />
          {backupPassphrase && backupConfirm && backupPassphrase !== backupConfirm && (
            <p className="text-sm text-danger">Passphrases don't match.</p>
          )}
          {backupError && (
            <p role="alert" className="text-sm text-danger">
              {backupError}
            </p>
          )}
          <Button type="submit" disabled={!backupValid || backupMutation.isPending}>
            <Lock size={14} aria-hidden />
            {backupMutation.isPending ? 'Preparing…' : 'Create encrypted backup'}
          </Button>
        </form>
      </Card>

      <Card className="p-4 sm:p-6">
        <h2 className="mb-2 font-display text-h2 font-semibold">Restore from backup</h2>
        <p className="mb-4 text-sm text-muted">
          Restores people, fields, relationships, tags, and documents from an encrypted backup
          file. It never deletes or overwrites anything already here.
        </p>
        <div className="space-y-4">
          <div className="space-y-1.5">
            <label htmlFor={restoreFileId} className="label-caps block">
              Backup file (.dossier)
            </label>
            <input
              id={restoreFileId}
              type="file"
              accept=".dossier"
              onChange={onRestoreFileChange}
              className="block w-full text-sm text-ink file:mr-3 file:h-11 file:rounded-md file:border file:border-border file:bg-surface file:px-3 file:text-[13px] file:font-medium file:text-ink hover:file:bg-surface-hover sm:file:h-8"
            />
          </div>
          <Input
            id={restorePassphraseId}
            label="Passphrase"
            type="password"
            value={restorePassphrase}
            onChange={(event) => setRestorePassphrase(event.target.value)}
            autoComplete="current-password"
            minLength={12}
          />
          {restoreFile && (
            <div className="flex items-center justify-between gap-3 rounded-md border border-border bg-surface-hover px-3 py-2">
              <span className="truncate text-sm text-ink">{restoreFile.name}</span>
              <Button
                type="button"
                size="sm"
                onClick={() => setConfirmingRestore(true)}
                disabled={!restoreValid}
              >
                <Unlock size={14} aria-hidden /> Restore
              </Button>
            </div>
          )}
          {restoreReport && (
            <div
              role="status"
              className="space-y-1.5 rounded-md border border-border bg-surface-hover px-3 py-2 text-sm"
            >
              <p className="font-medium text-ink">Restore complete</p>
              <ul className="list-disc space-y-0.5 pl-4 text-muted">
                <li>
                  {restoreReport.people_created} {restoreReport.people_created === 1 ? 'person' : 'people'} added
                  {restoreReport.people_skipped > 0
                    ? `, ${restoreReport.people_skipped} skipped (already existed)`
                    : ''}
                </li>
                <li>{restoreReport.fields_created} fields added</li>
                <li>
                  {restoreReport.relationships_created} relationships added
                  {restoreReport.relationships_skipped > 0
                    ? `, ${restoreReport.relationships_skipped} skipped`
                    : ''}
                </li>
                <li>{restoreReport.documents_restored} documents restored</li>
              </ul>
              {restoreReport.warnings.length > 0 && (
                <ul className="list-disc space-y-0.5 pl-4 text-muted">
                  {restoreReport.warnings.map((warning, index) => (
                    <li key={index}>{warning}</li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </div>
      </Card>

      <Card className="p-4 sm:p-6">
        <h2 className="mb-2 font-display text-h2 font-semibold">Manual backup &amp; JSON export</h2>
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
          {/* The 16px box stays small on purpose, but the label carries the
              hit area: htmlFor makes the whole padded row toggle the control,
              giving a 44px target (12px padding + 20px line + 12px padding)
              without enlarging the visual checkbox. Tapping the row only
              flips a visible, reversible state (the plaintext warning
              appears) — the actual export still needs a separate deliberate
              tap on the button below, so the larger target adds no
              accidental-exfiltration risk (SEC-7). */}
          <div className="mb-3 flex items-start gap-2.5">
            <input
              id={includeSensitiveId}
              type="checkbox"
              checked={includeSensitive}
              onChange={(event) => setIncludeSensitive(event.target.checked)}
              className="mt-3.5 h-4 w-4 shrink-0 rounded border-border text-accent focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
            />
            <label
              htmlFor={includeSensitiveId}
              className="flex-1 cursor-pointer py-3 text-sm text-ink select-none"
            >
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
            className="inline-flex h-11 items-center justify-center gap-2 rounded-md border border-border bg-surface px-3 text-[13px] font-medium text-ink transition-colors hover:border-border-strong hover:bg-surface-hover sm:h-8"
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
              className="block w-full text-sm text-ink file:mr-3 file:h-11 file:rounded-md file:border file:border-border file:bg-surface file:px-3 file:text-[13px] file:font-medium file:text-ink hover:file:bg-surface-hover sm:file:h-8"
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
      </Card>

      <TagsSection />

      {confirmingRestore && restoreFile && (
        <Dialog title="Restore from backup" onClose={() => setConfirmingRestore(false)}>
          <div className="space-y-4">
            <p className="text-sm text-ink">
              Restore <span className="font-medium">{restoreFile.name}</span>? This adds people,
              fields, relationships, tags, and documents from the backup — it never deletes or
              overwrites anything already here.
            </p>
            {restoreError && (
              <p role="alert" className="text-sm text-danger">
                {restoreError}
              </p>
            )}
            <div className="flex justify-end gap-2">
              <Button
                type="button"
                variant="secondary"
                onClick={() => setConfirmingRestore(false)}
                disabled={restoreMutation.isPending}
              >
                Cancel
              </Button>
              <Button
                type="button"
                onClick={() => restoreMutation.mutate()}
                disabled={restoreMutation.isPending}
              >
                {restoreMutation.isPending ? 'Restoring…' : 'Restore'}
              </Button>
            </div>
          </div>
        </Dialog>
      )}

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
