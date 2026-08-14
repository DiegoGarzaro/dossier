/** The person record — an open letterhead, the centerpiece of the product
 * (FR-7, Design System §5.3). No card chrome: a centered masthead (photo,
 * serif name, file meta, tags) on the bare paper background, then sections
 * ruled off with small-caps markers and hairlines. */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  ArrowLeft,
  Camera,
  Check,
  Contact,
  Download,
  FileJson,
  FileText,
  MoreVertical,
  Pencil,
  Plus,
  Star,
  Trash2,
  Upload,
  X,
} from 'lucide-react'
import { type DragEvent, type FormEvent, useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'

import { FieldRow, FieldValue, ValueInput } from '../components/FieldRow'
import { RelationshipSection } from '../components/RelationshipSection'
import { TagsSection } from '../components/TagsSection'
import {
  Avatar,
  Button,
  Dialog,
  EmptyState,
  IconButton,
  Input,
  SectionRule,
  Spinner,
} from '../components/ui'
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

/** The ⋯ menu in the utility row: rename, exports and the danger action live
 * here so the record itself stays free of button chrome. */
function RecordMenu({
  personId,
  onRename,
  onDelete,
}: {
  personId: number
  onRename: () => void
  onDelete: () => void
}) {
  const [open, setOpen] = useState(false)
  const close = () => setOpen(false)

  useEffect(() => {
    if (!open) return
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') close()
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [open])

  const itemClass =
    'flex w-full items-center gap-2.5 px-3 py-2.5 text-sm transition-colors hover:bg-surface-hover'

  return (
    <div className="relative">
      <IconButton
        label="More actions"
        aria-haspopup="menu"
        aria-expanded={open}
        className="text-muted hover:bg-surface-hover hover:text-ink"
        onClick={() => setOpen((current) => !current)}
      >
        <MoreVertical size={18} />
      </IconButton>
      {open && (
        <>
          {/* Click-away layer, same pattern as the Dialog scrim. */}
          <button
            type="button"
            aria-hidden
            tabIndex={-1}
            className="fixed inset-0 z-40 cursor-default"
            onClick={close}
          />
          <div
            role="menu"
            aria-label="Record actions"
            className="absolute right-0 z-50 mt-1 w-52 rounded-md border border-border bg-surface py-1 shadow-raised"
          >
            <button
              type="button"
              role="menuitem"
              className={`${itemClass} text-ink`}
              onClick={() => {
                close()
                onRename()
              }}
            >
              <Pencil size={15} className="text-subtle" aria-hidden /> Rename person
            </button>
            <a
              role="menuitem"
              className={`${itemClass} text-ink`}
              href={`/api/people/${personId}/vcard`}
              onClick={close}
            >
              <Contact size={15} className="text-subtle" aria-hidden /> Export vCard
            </a>
            <a
              role="menuitem"
              className={`${itemClass} text-ink`}
              href={`/api/people/${personId}/export`}
              onClick={close}
            >
              <FileJson size={15} className="text-subtle" aria-hidden /> Export JSON
            </a>
            <div aria-hidden className="mx-3 my-1 h-px bg-border" />
            <button
              type="button"
              role="menuitem"
              className={`${itemClass} text-danger`}
              onClick={() => {
                close()
                onDelete()
              }}
            >
              <Trash2 size={15} aria-hidden /> Delete person
            </button>
          </div>
        </>
      )}
    </div>
  )
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
    <form
      onSubmit={onSubmit}
      className="space-y-3 rounded-md border border-border bg-surface px-4 py-4"
    >
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
        className="flex items-center gap-2 py-2 sm:gap-3"
      >
        <FileText size={18} className="hidden shrink-0 text-subtle sm:block" aria-hidden />
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
    <div className="group flex items-center gap-1 py-3 transition-colors hover:bg-surface sm:gap-3">
      <FileText size={18} className="hidden shrink-0 text-subtle sm:block" aria-hidden />
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium">{document.title}</p>
        <p className="truncate font-mono text-xs text-muted">
          {document.mime_type.split('/')[1].toUpperCase()} · {formatSize(document.size_bytes)} ·{' '}
          {document.uploaded_at.slice(0, 10)}
        </p>
      </div>
      <div className="flex shrink-0 items-center opacity-100 transition-opacity duration-150 can-hover:opacity-0 can-hover:group-focus-within:opacity-100 can-hover:group-hover:opacity-100">
        <a
          href={`/api/documents/${document.id}/download`}
          aria-label={`Download ${document.title}`}
          className="inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-full text-subtle transition-colors hover:bg-surface-hover hover:text-ink sm:h-8 sm:w-8"
        >
          <Download size={16} />
        </a>
        <IconButton
          label={`Rename ${document.title}`}
          className="text-subtle hover:bg-surface-hover hover:text-ink"
          onClick={() => setRenaming(true)}
        >
          <Pencil size={16} />
        </IconButton>
        <IconButton
          label={`Delete ${document.title}`}
          className="text-subtle hover:bg-surface-hover hover:text-danger"
          onClick={() => setConfirming(true)}
        >
          <Trash2 size={16} />
        </IconButton>
      </div>
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
    return (
      <div className="mx-auto max-w-2xl pt-10">
        <EmptyState
          icon={<Contact size={26} aria-hidden />}
          message="This person no longer exists."
          action={
            <Button variant="secondary" onClick={() => navigate('/')}>
              Back to people
            </Button>
          }
        />
      </div>
    )
  }
  if (!person.data) return <Spinner />

  const detail = person.data
  const pinned = detail.fields.filter((field) => field.is_pinned)

  return (
    <div className="mx-auto max-w-2xl">
      {/* Utility row: wayfinding left, record actions right. */}
      <div className="flex items-center justify-between gap-2">
        <Link
          to="/"
          className="inline-flex h-11 items-center gap-1.5 rounded-md px-2 text-sm text-muted transition-colors hover:bg-surface-hover hover:text-ink sm:h-9"
        >
          <ArrowLeft size={16} aria-hidden /> All people
        </Link>
        <div className="flex items-center">
          <IconButton
            label={detail.is_favorite ? 'Remove from favorites' : 'Add to favorites'}
            className={`hover:bg-surface-hover ${detail.is_favorite ? 'text-seal' : 'text-muted hover:text-ink'}`}
            onClick={() => favorite.mutate(!detail.is_favorite)}
            disabled={favorite.isPending}
          >
            <Star size={18} fill={detail.is_favorite ? 'currentColor' : 'none'} />
          </IconButton>
          <RecordMenu
            personId={detail.id}
            onRename={() => {
              setNewName(detail.full_name)
              setRenaming(true)
            }}
            onDelete={() => setConfirmingDelete(true)}
          />
        </div>
      </div>

      {/* Masthead */}
      <header className="mt-8 flex flex-col items-center text-center">
        <button
          type="button"
          className="group relative shrink-0 rounded-full"
          aria-label="Change profile photo"
          onClick={() => photoInput.current?.click()}
        >
          <Avatar
            name={detail.full_name}
            photoUrl={
              detail.has_photo ? `/api/people/${detail.id}/photo?v=${detail.updated_at}` : undefined
            }
            size={112}
          />
          {/* Two affordances for the same tap: mouse gets a hover veil over
              the photo; touch (no real hover) gets a persistent badge in the
              corner instead — the veil would sit over the face permanently. */}
          <span className="absolute inset-0 hidden items-center justify-center rounded-full bg-black/40 text-white transition-opacity can-hover:flex can-hover:opacity-0 can-hover:group-hover:opacity-100">
            <Camera size={20} aria-hidden />
          </span>
          <span className="absolute -right-0.5 -bottom-0.5 flex h-8 w-8 items-center justify-center rounded-full border border-border bg-surface text-muted shadow-sm can-hover:hidden">
            <Camera size={14} aria-hidden />
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
        <h1 className="mt-5 font-display text-h1 leading-tight font-semibold text-balance sm:text-display">
          {detail.full_name}
        </h1>
        <p className="mt-2.5 font-mono text-xs tracking-wider text-subtle uppercase">
          File № {String(detail.id).padStart(4, '0')} · Added {detail.created_at.slice(0, 10)}
        </p>
        <TagsSection personId={detail.id} tags={detail.tags} />
      </header>

      {/* Key facts — pinned fields set with dotted leaders, like a filled form. */}
      {pinned.length > 0 && (
        <section className="mt-12">
          <SectionRule title="Key facts" />
          <dl className="mt-5 space-y-3.5">
            {pinned.map((field) => (
              <div key={field.id} className="flex items-baseline gap-3">
                <dt className="label-caps min-w-0 max-w-[45%] shrink-0 break-words">
                  {field.label}
                </dt>
                <span
                  aria-hidden
                  className="min-w-6 flex-1 -translate-y-1 border-b border-dotted border-border-strong"
                />
                <dd className="min-w-0 max-w-[55%] text-right text-[15px] break-words">
                  <FieldValue field={field} />
                </dd>
              </div>
            ))}
          </dl>
        </section>
      )}

      {/* Fields */}
      <section className="mt-12">
        <SectionRule
          title="Fields"
          count={orderedFields.length}
          action={
            <Button variant="ghost" size="sm" onClick={() => setAddingField(true)}>
              <Plus size={14} aria-hidden /> Add field
            </Button>
          }
        />
        {addingField && (
          <div className="mt-4">
            <AddFieldForm personId={detail.id} onDone={() => setAddingField(false)} />
          </div>
        )}
        <div aria-live="polite" className="sr-only">
          {moveAnnouncement}
        </div>
        {orderedFields.length === 0 && !addingField ? (
          <p className="py-6 text-sm text-muted">No fields yet.</p>
        ) : (
          <div className="mt-1 divide-y divide-border">
            {orderedFields.map((field, index) => {
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
            })}
          </div>
        )}
      </section>

      {/* Documents */}
      <section className="mt-12">
        <SectionRule
          title="Documents"
          count={detail.documents.length}
          action={
            <Button
              variant="ghost"
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
          <p role="alert" className="mt-2 text-sm text-danger">
            {uploadError}
          </p>
        )}
        {detail.documents.length === 0 ? (
          <p className="py-6 text-sm text-muted">No documents yet.</p>
        ) : (
          <div className="mt-1 divide-y divide-border">
            {detail.documents.map((document) => (
              <DocumentRow key={document.id} document={document} personId={detail.id} />
            ))}
          </div>
        )}
      </section>

      {/* Relationships */}
      <section className="mt-12">
        <RelationshipSection personId={detail.id} relationships={detail.relationships} />
      </section>

      {/* Archival stamp line. */}
      <p className="mt-16 text-center font-mono text-[11px] tracking-wider text-subtle uppercase">
        Last updated {detail.updated_at.slice(0, 10)}
      </p>

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
