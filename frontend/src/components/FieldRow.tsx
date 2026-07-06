/** A single field row on the ID-card: display, inline edit, pin, remove (Epic C). */

import { useMutation, useQueryClient } from '@tanstack/react-query'
import {
  ArrowUpDown,
  BadgeCheck,
  Check,
  Eye,
  EyeOff,
  Globe,
  IdCard,
  MapPin,
  Pencil,
  Pin,
  Trash2,
  X,
} from 'lucide-react'
import { type DragEvent, type FormEvent, type KeyboardEvent, useRef, useState } from 'react'

import { api } from '../lib/api'
import type { FieldOut, FieldType } from '../lib/types'
import { Button } from './ui'

const MONO_TYPES: FieldType[] = ['number', 'date', 'sensitive']

/** Icons for the seeded built-in fields; labels are locked server-side. */
const SYSTEM_FIELD_ICONS: Record<string, typeof IdCard> = {
  'Document number': IdCard,
  Address: MapPin,
  Nationality: Globe,
}

function FieldLabel({ field }: { field: FieldOut }) {
  if (!field.is_system) return <span className="label-caps">{field.label}</span>
  const Icon = SYSTEM_FIELD_ICONS[field.label] ?? BadgeCheck
  return (
    <span className="label-caps flex items-center gap-1.5">
      <Icon size={14} className="shrink-0 text-subtle" aria-hidden />
      {field.label}
    </span>
  )
}

export function FieldValue({ field }: { field: FieldOut }) {
  const [revealed, setRevealed] = useState(false)
  if (field.value === null || field.value === '') {
    return <span className="text-subtle">—</span>
  }
  if (field.type === 'boolean') {
    return <span>{field.value === 'true' ? 'Yes' : 'No'}</span>
  }
  if (field.type === 'sensitive') {
    return (
      <span className="inline-flex items-center gap-2 font-mono text-[15px]">
        {revealed ? field.value : '••••••••'}
        <button
          type="button"
          aria-label={revealed ? 'Hide value' : 'Reveal value'}
          className="text-seal hover:opacity-80"
          onClick={() => setRevealed((current) => !current)}
        >
          {revealed ? <EyeOff size={15} /> : <Eye size={15} />}
        </button>
      </span>
    )
  }
  return (
    <span className={MONO_TYPES.includes(field.type) ? 'font-mono text-[15px]' : undefined}>
      {field.value}
    </span>
  )
}

export function ValueInput({
  type,
  value,
  onChange,
}: {
  type: FieldType
  value: string
  onChange: (next: string) => void
}) {
  const base =
    'h-9 w-full rounded-sm border border-border bg-surface px-3 text-sm focus:border-accent'
  if (type === 'boolean') {
    return (
      <select className={base} value={value} onChange={(event) => onChange(event.target.value)}>
        <option value="">—</option>
        <option value="true">Yes</option>
        <option value="false">No</option>
      </select>
    )
  }
  if (type === 'textarea') {
    return (
      <textarea
        className={`${base} h-auto min-h-20 py-2`}
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
    )
  }
  const inputType = type === 'number' ? 'number' : type === 'date' ? 'date' : 'text'
  return (
    <input
      type={inputType}
      className={base}
      value={value}
      onChange={(event) => onChange(event.target.value)}
    />
  )
}

interface FieldRowProps {
  field: FieldOut
  personId: number
  position: number
  count: number
  onMoveUp: () => void
  onMoveDown: () => void
  onDragHandleStart: () => void
  onDragHandleEnd: () => void
  onRowDragOver: (event: DragEvent) => void
  onRowDrop: () => void
  isDragSource: boolean
  isDropTarget: boolean
  dropEdge: 'top' | 'bottom'
  rowRef: (el: HTMLElement | null) => void
}

export function FieldRow({
  field,
  personId,
  position,
  count,
  onMoveUp,
  onMoveDown,
  onDragHandleStart,
  onDragHandleEnd,
  onRowDragOver,
  onRowDrop,
  isDragSource,
  isDropTarget,
  dropEdge,
  rowRef,
}: FieldRowProps) {
  const rowEl = useRef<HTMLElement | null>(null)
  const [editing, setEditing] = useState(false)
  const [label, setLabel] = useState(field.label)
  const [value, setValue] = useState(field.value ?? '')
  const [error, setError] = useState<string | null>(null)
  const queryClient = useQueryClient()

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['person', personId] })

  const update = useMutation({
    mutationFn: (body: Partial<Pick<FieldOut, 'label' | 'value' | 'is_pinned'>>) =>
      api<FieldOut>(`/api/fields/${field.id}`, { method: 'PATCH', body }),
    onSuccess: () => {
      setEditing(false)
      setError(null)
      invalidate()
    },
    onError: (err) => setError(err.message),
  })

  const remove = useMutation({
    mutationFn: () => api<void>(`/api/fields/${field.id}`, { method: 'DELETE' }),
    onSuccess: invalidate,
  })

  const onSave = (event: FormEvent) => {
    event.preventDefault()
    update.mutate({ label, value: value === '' ? null : value })
  }

  const onHandleKeyDown = (event: KeyboardEvent<HTMLButtonElement>) => {
    if (event.key === 'ArrowUp') {
      event.preventDefault()
      onMoveUp()
    } else if (event.key === 'ArrowDown') {
      event.preventDefault()
      onMoveDown()
    }
  }

  const setRowEl = (el: HTMLElement | null) => {
    rowEl.current = el
    rowRef(el)
  }

  const rowDragProps = {
    onDragOver: onRowDragOver,
    onDrop: (event: DragEvent) => {
      event.preventDefault()
      onRowDrop()
    },
  }

  // The bar marks the true insertion edge: below the target when dragging
  // down, above it when dragging up.
  const dropIndicator = isDropTarget && (
    <span
      aria-hidden
      className={`absolute inset-x-3 h-0.5 origin-left rounded-full bg-accent motion-safe:animate-[drop-in_160ms_ease-out] ${dropEdge === 'bottom' ? 'bottom-0' : 'top-0'}`}
    />
  )

  if (editing) {
    return (
      <form
        ref={setRowEl}
        onSubmit={onSave}
        {...rowDragProps}
        className="relative grid grid-cols-1 items-start gap-2 px-4 py-2 sm:grid-cols-[minmax(160px,1fr)_2fr_auto]"
      >
        {dropIndicator}
        {field.is_system ? (
          <div className="pt-2.5">
            <FieldLabel field={field} />
          </div>
        ) : (
          <input
            aria-label="Field label"
            className="h-9 w-full rounded-sm border border-border bg-surface px-3 text-sm focus:border-accent"
            value={label}
            onChange={(event) => setLabel(event.target.value)}
            required
          />
        )}
        <div>
          <ValueInput type={field.type} value={value} onChange={setValue} />
          {error && (
            <p role="alert" className="mt-1 text-xs text-danger">
              {error}
            </p>
          )}
        </div>
        <div className="flex gap-1">
          <Button type="submit" size="sm" aria-label="Save field" disabled={update.isPending}>
            <Check size={15} />
          </Button>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            aria-label="Cancel edit"
            onClick={() => {
              setEditing(false)
              setLabel(field.label)
              setValue(field.value ?? '')
              setError(null)
            }}
          >
            <X size={15} />
          </Button>
        </div>
      </form>
    )
  }

  return (
    <div
      ref={setRowEl}
      {...rowDragProps}
      className={`group relative grid grid-cols-1 items-baseline gap-x-2 px-4 py-2.5 transition-[background-color,opacity] duration-150 odd:bg-surface-subtle hover:bg-surface-hover sm:grid-cols-[minmax(160px,1fr)_2fr_auto] ${isDragSource ? 'opacity-40' : ''}`}
    >
      {dropIndicator}
      <FieldLabel field={field} />
      <span className="text-[15px]">
        <FieldValue field={field} />
      </span>
      <div className="flex gap-0.5 opacity-0 transition-opacity duration-150 group-focus-within:opacity-100 group-hover:opacity-100">
        {!field.is_system && (
          <button
            type="button"
            draggable
            onDragStart={(event) => {
              // Firefox refuses to start a drag unless data is set (G-20).
              event.dataTransfer.setData('text/plain', field.label)
              event.dataTransfer.effectAllowed = 'move'
              if (rowEl.current) {
                const rect = rowEl.current.getBoundingClientRect()
                event.dataTransfer.setDragImage(
                  rowEl.current,
                  event.clientX - rect.left,
                  event.clientY - rect.top,
                )
              }
              onDragHandleStart()
            }}
            onDragEnd={() => onDragHandleEnd()}
            onKeyDown={onHandleKeyDown}
            aria-label={`Reorder ${field.label}, position ${position} of ${count}. Use arrow keys to move.`}
            className="cursor-grab rounded p-1.5 text-subtle hover:bg-surface-hover hover:text-ink active:cursor-grabbing"
          >
            <ArrowUpDown size={15} />
          </button>
        )}
        <button
          type="button"
          aria-label={field.is_pinned ? 'Unpin field' : 'Pin field to header'}
          className={`rounded p-1.5 hover:bg-surface-hover ${field.is_pinned ? 'text-seal' : 'text-subtle hover:text-ink'}`}
          onClick={() => update.mutate({ is_pinned: !field.is_pinned })}
        >
          <Pin size={15} />
        </button>
        <button
          type="button"
          aria-label="Edit field"
          className="rounded p-1.5 text-subtle hover:bg-surface-hover hover:text-ink"
          onClick={() => setEditing(true)}
        >
          <Pencil size={15} />
        </button>
        {!field.is_system && (
          <button
            type="button"
            aria-label="Remove field"
            className="rounded p-1.5 text-subtle hover:bg-surface-hover hover:text-danger"
            onClick={() => remove.mutate()}
          >
            <Trash2 size={15} />
          </button>
        )}
      </div>
    </div>
  )
}
