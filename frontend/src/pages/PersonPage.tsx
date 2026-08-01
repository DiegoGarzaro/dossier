/** The ID-card screen — the centerpiece of the product (FR-7, Design System §5.3). */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Camera,
  Check,
  Contact,
  Download,
  FileJson,
  FileText,
  Pencil,
  Plus,
  Star,
  Trash2,
  Upload,
  X,
} from 'lucide-react'
import { type DragEvent, type FormEvent, useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'

import { FieldRow, ValueInput } from '../components/FieldRow'
import { RelationshipSection } from '../components/RelationshipSection'
import { TagsSection } from '../components/TagsSection'
import { Avatar, Button, Dialog, Input, SectionHeading, Spinner } from '../components/ui'
import { ApiError, api } from '../lib/api'
import type { DocumentOut, FieldOut, FieldType, PersonDetail } from '../lib/types'
import { useFlip } from '../lib/useFlip'

const FIELD_TYPES: { value: FieldType; label: string }[] = [
  { value: 'text', label: 'Text' },
  { value: 'textarea', label: 'Long text' },
  { value: 'number', label: 'Number' },
  { value: 'date', label: 'Date' },
  { value: 'boolean', label: 'Yes / No' },
  { value: 'sensitive', label: 'Sensitive' },
]

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function AddFieldForm({ personId, onDone }: { personId: number; onDone: () => void }) {
  const [label, setLabel] = useState('')
  const [type, setType] = useState<FieldType>('text')
  const [value, setValue] = useState('')
  const queryClient = useQueryClient()

  const create = useMutation({
    mutationFn: () =>
      api<FieldOut>(`/api/people/${personId}/fields`, {
        method: 'POST',
        body: { label, type, value: value === '' ? null : value },
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['person', personId] })
      onDone()
    },
  })

  const onSubmit = (event: FormEvent) => {
    event.preventDefault()
    create.mutate()
  }

  return (
    <form onSubmit={onSubmit} className="space-y-3 border-b border-border bg-surface-subtle px-4 py-4">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <Input
          id="field-label"
          label="Label"
          value={label}
          onChange={(event) => setLabel(event.target.value)}
          autoFocus
          required
        />
        <div className="space-y-1.5">
          <label htmlFor="field-type" className="label-caps block">
            Type
          </label>
          <select
            id="field-type"
            className="h-10 w-full rounded-sm border border-border bg-surface px-3 text-sm focus:border-accent"
            value={type}
            onChange={(event) => {
              setType(event.target.value as FieldType)
              setValue('')
            }}
          >
            {FIELD_TYPES.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
        <div className="space-y-1.5">
          <span className="label-caps block">Value</span>
          <ValueInput type={type} value={value} onChange={setValue} />
        </div>
      </div>
      {create.error instanceof ApiError && (
        <p role="alert" className="text-sm text-danger">
          {create.error.message}
        </p>
      )}
      <div className="flex justify-end gap-2">
        <Button type="button" variant="secondary" size="sm" onClick={onDone}>
          Cancel
        </Button>
        <Button type="submit" size="sm" disabled={create.isPending}>
          Add field
        </Button>
      </div>
    </form>
  )
}

function DocumentRow({ document, personId }: { document: DocumentOut; personId: number }) {
  const [confirming, setConfirming] = useState(false)
  const [renaming, setRenaming] = useState(false)
  const [title, setTitle] = useState(document.title)
  const [renameError, setRenameError] = useState<string | null>(null)
  const queryClient = useQueryClient()

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['person', personId] })

  const remove = useMutation({
    mutationFn: () => api<void>(`/api/documents/${document.id}`, { method: 'DELETE' }),
    onSuccess: invalidate,
  })

  const rename = useMutation({
    mutationFn: () => api<DocumentOut>(`/api/documents/${document.id}`, { method: 'PATCH', body: { title } }),
    onSuccess: () => {
      setRenaming(false)
      setRenameError(null)
      invalidate()
    },
    onError: (error) => setRenameError(error.message),
  })

  if (renaming) {
    return (
      <form
        onSubmit={(event) => {
          event.preventDefault()
          rename.mutate()
        }}
        className="flex items-center gap-3 px-4 py-3 odd:bg-surface-subtle"
      >
        <FileText size={18} className="shrink-0 text-subtle" aria-hidden />
        <div className="min-w-0 flex-1">
          <input
            aria-label="Document title"
            className="h-9 w-full rounded-sm border border-border bg-surface px-3 text-sm focus:border-accent"
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            autoFocus
            required
          />
          {renameError && (
            <p role="alert" className="mt-1 text-xs text-danger">
              {renameError}
            </p>
          )}
        </div>
        <Button type="submit" size="sm" aria-label="Save document title" disabled={rename.isPending}>
          <Check size={15} />
        </Button>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          aria-label="Cancel rename"
          onClick={() => {
            setRenaming(false)
            setTitle(document.title)
            setRenameError(null)
          }}
        >
          <X size={15} />
        </Button>
      </form>
    )
  }

  return (
    <div className="flex items-center gap-3 px-4 py-3 odd:bg-surface-subtle">
      <FileText size={18} className="shrink-0 text-subtle" aria-hidden />
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium">{document.title}</p>
        <p className="truncate font-mono text-xs text-muted">
          {document.mime_type.split('/')[1].toUpperCase()} · {formatSize(document.size_bytes)} ·{' '}
          {document.uploaded_at.slice(0, 10)}
        </p>
      </div>
      <a
        href={`/api/documents/${document.id}/download`}
        aria-label={`Download ${document.title}`}
        className="rounded p-1.5 text-subtle hover:bg-surface-hover hover:text-ink"
      >
        <Download size={16} />
      </a>
      <button
        type="button"
        aria-label={`Rename ${document.title}`}
        className="rounded p-1.5 text-subtle hover:bg-surface-hover hover:text-ink"
        onClick={() => setRenaming(true)}
      >
        <Pencil size={16} />
      </button>
      <button
        type="button"
        aria-label={`Delete ${document.title}`}
        className="rounded p-1.5 text-subtle hover:bg-surface-hover hover:text-danger"
        onClick={() => setConfirming(true)}
      >
        <Trash2 size={16} />
      </button>
      {confirming && (
        <Dialog title="Delete document?" onClose={() => setConfirming(false)}>
          <p className="mb-4 text-sm text-muted">
            “{document.title}” and its file will be permanently deleted.
          </p>
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={() => setConfirming(false)}>
              Cancel
            </Button>
            <Button variant="danger" onClick={() => remove.mutate()} disabled={remove.isPending}>
              Delete
            </Button>
          </div>
        </Dialog>
      )}
    </div>
  )
}

export function PersonPage() {
  const { id } = useParams()
  const personId = Number(id)
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [addingField, setAddingField] = useState(false)
  const [renaming, setRenaming] = useState(false)
  const [newName, setNewName] = useState('')
  const [confirmingDelete, setConfirmingDelete] = useState(false)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const photoInput = useRef<HTMLInputElement>(null)
  const documentInput = useRef<HTMLInputElement>(null)

  const person = useQuery({
    queryKey: ['person', personId],
    queryFn: () => api<PersonDetail>(`/api/people/${personId}`),
  })

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['person', personId] })

  const rename = useMutation({
    mutationFn: () =>
      api<PersonDetail>(`/api/people/${personId}`, { method: 'PATCH', body: { full_name: newName } }),
    onSuccess: () => {
      setRenaming(false)
      invalidate()
      queryClient.invalidateQueries({ queryKey: ['people'] })
    },
  })

  const favorite = useMutation({
    mutationFn: (next: boolean) =>
      api<PersonDetail>(`/api/people/${personId}`, { method: 'PATCH', body: { is_favorite: next } }),
    onSuccess: () => {
      invalidate()
      queryClient.invalidateQueries({ queryKey: ['people'] })
    },
    // A failed toggle must not leave the star showing a state the server rejected (G-21 lesson).
    onError: invalidate,
  })

  const removePerson = useMutation({
    mutationFn: () => api<void>(`/api/people/${personId}`, { method: 'DELETE' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['people'] })
      navigate('/')
    },
  })

  const uploadPhoto = useMutation({
    mutationFn: (file: File) => {
      const form = new FormData()
      form.append('file', file)
      return api<PersonDetail>(`/api/people/${personId}/photo`, { method: 'PUT', form })
    },
    onSuccess: () => {
      setUploadError(null)
      invalidate()
    },
    onError: (error) => setUploadError(error.message),
  })

  const uploadDocument = useMutation({
    mutationFn: (file: File) => {
      const form = new FormData()
      form.append('file', file)
      return api<DocumentOut>(`/api/people/${personId}/documents`, { method: 'POST', form })
    },
    onSuccess: () => {
      setUploadError(null)
      invalidate()
    },
    onError: (error) => setUploadError(error.message),
  })

  const [orderedFields, setOrderedFields] = useState<FieldOut[]>([])
  const [dragState, setDragState] = useState<{ draggedId: number | null; overId: number | null }>({
    draggedId: null,
    overId: null,
  })
  const [moveAnnouncement, setMoveAnnouncement] = useState('')
  const registerFlip = useFlip()

  useEffect(() => {
    if (person.data) {
      setOrderedFields([
        ...person.data.fields.filter((field) => field.is_system),
        ...person.data.fields.filter((field) => !field.is_system && field.is_pinned),
        ...person.data.fields.filter((field) => !field.is_system && !field.is_pinned),
      ])
    }
  }, [person.data])

  const reorder = useMutation({
    mutationFn: (items: { id: number; position: number }[]) =>
      api<FieldOut[]>(`/api/people/${personId}/fields/reorder`, { method: 'POST', body: { items } }),
    onSuccess: invalidate,
    // Revert the optimistic local order if the server rejected the move.
    onError: invalidate,
  })

  // Drag/keyboard reorder is confined to each field's group — built-in system
  // fields sit first and never move; pinned then unpinned fields follow, each
  // displayed group-first regardless of stored position, so a move that crossed
  // a boundary would silently revert once the list refetches.
  const groupOf = (index: number): 'system' | 'pinned' | 'unpinned' => {
    const field = orderedFields[index]
    if (field.is_system) return 'system'
    return field.is_pinned ? 'pinned' : 'unpinned'
  }

  const moveField = (fromIndex: number, toIndex: number) => {
    if (fromIndex === toIndex || toIndex < 0 || toIndex >= orderedFields.length) return
    if (groupOf(fromIndex) === 'system' || groupOf(fromIndex) !== groupOf(toIndex)) return
    const next = [...orderedFields]
    const [moved] = next.splice(fromIndex, 1)
    next.splice(toIndex, 0, moved)
    setOrderedFields(next)
    setMoveAnnouncement(`${moved.label}, position ${toIndex + 1} of ${next.length}`)
    reorder.mutate(next.map((field, index) => ({ id: field.id, position: index })))
  }

  const onRowDrop = (dropIndex: number) => {
    const fromIndex = orderedFields.findIndex((field) => field.id === dragState.draggedId)
    if (fromIndex !== -1) moveField(fromIndex, dropIndex)
    setDragState({ draggedId: null, overId: null })
  }

  if (person.isPending) return <Spinner />
  if (person.error instanceof ApiError && person.error.status === 404) {
    return <p className="text-muted">This person no longer exists.</p>
  }
  if (!person.data) return <Spinner />

  const detail = person.data
  const pinned = detail.fields.filter((field) => field.is_pinned)

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      {/* ID-card */}
      <div className="overflow-hidden rounded-lg border border-border bg-surface shadow-(--shadow-card)">
        <div className="flex flex-col gap-5 p-6 sm:flex-row sm:items-start">
          <button
            type="button"
            className="group relative shrink-0 self-center rounded-full sm:self-start"
            aria-label="Change profile photo"
            onClick={() => photoInput.current?.click()}
          >
            <Avatar
              name={detail.full_name}
              photoUrl={
                detail.has_photo
                  ? `/api/people/${detail.id}/photo?v=${detail.updated_at}`
                  : undefined
              }
              size={96}
            />
            <span className="absolute inset-0 flex items-center justify-center rounded-full bg-black/40 text-white opacity-0 transition-opacity group-hover:opacity-100">
              <Camera size={20} aria-hidden />
            </span>
          </button>
          <input
            ref={photoInput}
            type="file"
            accept="image/png,image/jpeg,image/webp"
            className="hidden"
            onChange={(event) => {
              const file = event.target.files?.[0]
              if (file) uploadPhoto.mutate(file)
              event.target.value = ''
            }}
          />
          <div className="min-w-0 flex-1">
            <div className="flex items-start gap-2">
              <h1 className="font-display text-3xl leading-tight font-semibold">
                {detail.full_name}
              </h1>
              <button
                type="button"
                aria-label="Rename person"
                className="mt-1.5 rounded p-1.5 text-subtle hover:bg-surface-hover hover:text-ink"
                onClick={() => {
                  setNewName(detail.full_name)
                  setRenaming(true)
                }}
              >
                <Pencil size={15} />
              </button>
              <button
                type="button"
                aria-label={detail.is_favorite ? 'Remove from favorites' : 'Add to favorites'}
                className={`mt-1.5 rounded p-1.5 hover:bg-surface-hover ${detail.is_favorite ? 'text-seal' : 'text-subtle hover:text-ink'}`}
                onClick={() => favorite.mutate(!detail.is_favorite)}
                disabled={favorite.isPending}
              >
                <Star size={15} fill={detail.is_favorite ? 'currentColor' : 'none'} />
              </button>
            </div>
            {pinned.length > 0 && (
              <dl className="mt-4 space-y-2 border-l-2 border-seal pl-3">
                {pinned.map((field) => (
                  <div
                    key={field.id}
                    className="grid grid-cols-[minmax(120px,240px)_1fr] items-baseline gap-x-3"
                  >
                    <dt className="label-caps min-w-0 break-words">{field.label}</dt>
                    <dd className="min-w-0 text-[15px] break-words">
                      {field.value ? (
                        <span className={field.type === 'text' ? undefined : 'font-mono'}>
                          {field.type === 'sensitive' ? '••••••••' : field.value}
                        </span>
                      ) : (
                        <span className="text-subtle">—</span>
                      )}
                    </dd>
                  </div>
                ))}
              </dl>
            )}
          </div>
        </div>

        {/* Tags */}
        <TagsSection personId={detail.id} tags={detail.tags} />

        {/* Fields */}
        <SectionHeading
          title="Fields"
          action={
            <Button variant="secondary" size="sm" onClick={() => setAddingField(true)}>
              <Plus size={14} aria-hidden /> Add field
            </Button>
          }
        />
        {addingField && <AddFieldForm personId={detail.id} onDone={() => setAddingField(false)} />}
        <div aria-live="polite" className="sr-only">
          {moveAnnouncement}
        </div>
        <div>
          {orderedFields.length === 0 && !addingField ? (
            <p className="px-4 py-6 text-sm text-muted">No fields yet.</p>
          ) : (
            orderedFields.map((field, index) => {
              const draggedIndex = orderedFields.findIndex((f) => f.id === dragState.draggedId)
              return (
              <FieldRow
                key={field.id}
                field={field}
                personId={detail.id}
                position={index + 1}
                count={orderedFields.length}
                rowRef={registerFlip(field.id)}
                onMoveUp={() => moveField(index, index - 1)}
                onMoveDown={() => moveField(index, index + 1)}
                onDragHandleStart={() => setDragState({ draggedId: field.id, overId: null })}
                onDragHandleEnd={() => setDragState({ draggedId: null, overId: null })}
                onRowDragOver={(event: DragEvent) => {
                  if (dragState.draggedId === null) return
                  const fromIndex = orderedFields.findIndex((f) => f.id === dragState.draggedId)
                  if (fromIndex === -1 || groupOf(fromIndex) !== groupOf(index)) {
                    // Different group (system/pinned/unpinned): refuse the drop
                    // outright (no preventDefault) so the cursor shows "not
                    // allowed" instead of silently doing nothing once dropped.
                    event.dataTransfer.dropEffect = 'none'
                    return
                  }
                  event.preventDefault()
                  setDragState((current) =>
                    current.overId === field.id ? current : { ...current, overId: field.id },
                  )
                }}
                onRowDrop={() => onRowDrop(index)}
                isDragSource={dragState.draggedId === field.id}
                isDropTarget={dragState.overId === field.id && dragState.draggedId !== field.id}
                dropEdge={draggedIndex !== -1 && draggedIndex < index ? 'bottom' : 'top'}
              />
              )
            })
          )}
        </div>

        {/* Documents */}
        <SectionHeading
          title="Documents"
          action={
            <Button
              variant="secondary"
              size="sm"
              onClick={() => documentInput.current?.click()}
              disabled={uploadDocument.isPending}
            >
              <Upload size={14} aria-hidden />
              {uploadDocument.isPending ? 'Uploading…' : 'Upload'}
            </Button>
          }
        />
        <input
          ref={documentInput}
          type="file"
          accept=".pdf,.png,.jpg,.jpeg,.webp"
          className="hidden"
          onChange={(event) => {
            const file = event.target.files?.[0]
            if (file) uploadDocument.mutate(file)
            event.target.value = ''
          }}
        />
        {uploadError && (
          <p role="alert" className="px-4 py-2 text-sm text-danger">
            {uploadError}
          </p>
        )}
        {detail.documents.length === 0 ? (
          <p className="px-4 py-6 text-sm text-muted">No documents yet.</p>
        ) : (
          detail.documents.map((document) => (
            <DocumentRow key={document.id} document={document} personId={detail.id} />
          ))
        )}

        {/* Relationships */}
        <RelationshipSection personId={detail.id} relationships={detail.relationships} />
      </div>

      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <a
            href={`/api/people/${detail.id}/vcard`}
            className="inline-flex h-8 items-center justify-center gap-2 rounded-md border border-border bg-surface px-3 text-[13px] font-medium text-ink transition-colors hover:bg-surface-hover"
          >
            <Contact size={14} aria-hidden /> Export vCard
          </a>
          <a
            href={`/api/people/${detail.id}/export`}
            className="inline-flex h-8 items-center justify-center gap-2 rounded-md border border-border bg-surface px-3 text-[13px] font-medium text-ink transition-colors hover:bg-surface-hover"
          >
            <FileJson size={14} aria-hidden /> Export JSON
          </a>
        </div>
        <Button variant="danger" size="sm" onClick={() => setConfirmingDelete(true)}>
          <Trash2 size={14} aria-hidden /> Delete person
        </Button>
      </div>

      {renaming && (
        <Dialog title="Rename person" onClose={() => setRenaming(false)}>
          <form
            onSubmit={(event) => {
              event.preventDefault()
              rename.mutate()
            }}
            className="space-y-4"
          >
            <Input
              id="rename"
              label="Full name"
              value={newName}
              onChange={(event) => setNewName(event.target.value)}
              autoFocus
              required
            />
            <div className="flex justify-end gap-2">
              <Button type="button" variant="secondary" onClick={() => setRenaming(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={rename.isPending}>
                Save
              </Button>
            </div>
          </form>
        </Dialog>
      )}

      {confirmingDelete && (
        <Dialog title="Delete person?" onClose={() => setConfirmingDelete(false)}>
          <p className="mb-4 text-sm text-muted">
            “{detail.full_name}” and all of their fields and documents will be permanently deleted.
          </p>
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={() => setConfirmingDelete(false)}>
              Cancel
            </Button>
            <Button
              variant="danger"
              onClick={() => removePerson.mutate()}
              disabled={removePerson.isPending}
            >
              Delete
            </Button>
          </div>
        </Dialog>
      )}
    </div>
  )
}
