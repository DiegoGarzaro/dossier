/** A single field row on the ID-card: display, inline edit, pin, remove (Epic C). */

import { useMutation, useQueryClient } from '@tanstack/react-query'
import {
  AlignLeft,
  ArrowUpDown,
  BadgeCheck,
  Calendar,
  Check,
  ChevronDown,
  ChevronUp,
  Eye,
  EyeOff,
  Globe,
  Hash,
  IdCard,
  MapPin,
  Pencil,
  Pin,
  ToggleLeft,
  Trash2,
  Type,
  X,
} from 'lucide-react'
import { type DragEvent, type FormEvent, type KeyboardEvent, useRef, useState } from 'react'

import { api } from '../lib/api'
import type { FieldOut, FieldType } from '../lib/types'
import { Button, IconButton } from './ui'

const MONO_TYPES: FieldType[] = ['number', 'date', 'sensitive']

/** Icons for the seeded built-in fields; labels are locked server-side. */
const SYSTEM_FIELD_ICONS: Record<string, typeof IdCard> = {
  'Document number': IdCard,
  Address: MapPin,
  Nationality: Globe,
}

/** Type badge per field type (§2.4): monochrome metadata — boolean picks up
 * the accent, sensitive a quieted seal (the eye toggle already carries the
 * full seal color; two loud ambers per row read as decoration). */
const TYPE_ICONS: Record<FieldType, { icon: typeof IdCard; tone: string }> = {
  text: { icon: Type, tone: 'text-subtle' },
  textarea: { icon: AlignLeft, tone: 'text-subtle' },
  number: { icon: Hash, tone: 'text-subtle' },
  date: { icon: Calendar, tone: 'text-subtle' },
  boolean: { icon: ToggleLeft, tone: 'text-accent' },
  sensitive: { icon: EyeOff, tone: 'text-seal/70' },
}

/** Zero-width break opportunities after punctuation, so long unbreakable
 * labels (emails, codes) wrap at natural points — "name@\nexample.com"
 * instead of "name@exa\nmple.com". Pure text, nothing is parsed as HTML. */
const breakable = (text: string) => text.replace(/([@.\-_/:])/g, '$1\u200B')

/** Icon + label with a hanging indent: the icon is pinned to the first line
 * (absolute, so it never drives the cell's baseline) and wrapped lines align
 * under the text. A flex row would take its baseline from the icon's bottom
 * edge instead — with a two-line label that re-anchored the value column to
 * the middle of the label (G-59). */
function FieldLabel({ field }: { field: FieldOut }) {
  // min-w-0 + break-words: long labels must wrap inside their grid column
  // instead of colliding with the value column.
  if (!field.is_system) {
    const { icon: TypeIcon, tone } = TYPE_ICONS[field.type]
    return (
      <span className="label-caps relative block min-w-0 pl-[19px] break-words">
        <TypeIcon size={13} className={`absolute top-[1.5px] left-0 ${tone}`} aria-hidden />
        {breakable(field.label)}
      </span>
    )
  }
  const Icon = SYSTEM_FIELD_ICONS[field.label] ?? BadgeCheck
  return (
    <span className="label-caps relative block min-w-0 pl-5 break-words">
      <Icon size={14} className="absolute top-px left-0 text-subtle" aria-hidden />
      {breakable(field.label)}
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
        {/* Hit area stays at 31px (-inset-2) on purpose: several sensitive
            rows can stack ~43px apart, and a 44px inset would bleed into the
            neighbour and risk revealing the *wrong* secret — worse than a
            smaller target. 31px still clears WCAG 2.5.8's 24px floor. */}
        <button
          type="button"
          aria-label={revealed ? 'Hide value' : 'Reveal value'}
          className="relative text-seal before:absolute before:-inset-2 before:content-[''] hover:opacity-80"
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
      className={`absolute inset-x-0 h-0.5 origin-left rounded-full bg-accent motion-safe:animate-[drop-in_160ms_ease-out] ${dropEdge === 'bottom' ? 'bottom-0' : 'top-0'}`}
    />
  )

  if (editing) {
    return (
      <form
        ref={setRowEl}
        onSubmit={onSave}
        {...rowDragProps}
        className="relative grid grid-cols-1 items-start gap-2 py-3 sm:grid-cols-[minmax(160px,1fr)_2fr_auto]"
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
      className={`group relative grid grid-cols-1 items-baseline gap-x-2 py-3 transition-[background-color,opacity] duration-150 hover:bg-surface sm:grid-cols-[minmax(160px,1fr)_2fr_auto] ${isDragSource ? 'opacity-40' : ''}`}
    >
      {dropIndicator}
      <FieldLabel field={field} />
      <span className="min-w-0 text-[15px] break-words">
        <FieldValue field={field} />
      </span>
      <div className="flex flex-wrap items-center gap-0.5 opacity-100 transition-opacity duration-150 can-hover:opacity-0 can-hover:group-focus-within:opacity-100 can-hover:group-hover:opacity-100">
        {!field.is_system && (
          <>
            {/* Touch: native HTML5 drag doesn't work on touchscreens, so these
                explicit buttons are the reorder path there — hidden once a
                mouse is available, where the drag handle below takes over. */}
            <IconButton
              label={`Move ${field.label} up`}
              disabled={position === 1}
              onClick={onMoveUp}
              className="inline-flex text-subtle hover:bg-surface-hover hover:text-ink can-hover:hidden"
            >
              <ChevronUp size={15} />
            </IconButton>
            <IconButton
              label={`Move ${field.label} down`}
              disabled={position === count}
              onClick={onMoveDown}
              className="inline-flex text-subtle hover:bg-surface-hover hover:text-ink can-hover:hidden"
            >
              <ChevronDown size={15} />
            </IconButton>
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
              className="hidden cursor-grab rounded p-1.5 text-subtle hover:bg-surface-hover hover:text-ink active:cursor-grabbing can-hover:inline-flex"
            >
              <ArrowUpDown size={15} />
            </button>
          </>
        )}
        {!field.is_system && (
          <IconButton
            label={field.is_pinned ? 'Unpin field' : 'Pin field to header'}
            className={`hover:bg-surface-hover ${field.is_pinned ? 'text-seal' : 'text-subtle hover:text-ink'}`}
            onClick={() => update.mutate({ is_pinned: !field.is_pinned })}
          >
            <Pin size={15} />
          </IconButton>
        )}
        <IconButton
          label="Edit field"
          className="text-subtle hover:bg-surface-hover hover:text-ink"
          onClick={() => setEditing(true)}
        >
          <Pencil size={15} />
        </IconButton>
        {!field.is_system && (
          <IconButton
            label="Remove field"
            className="text-subtle hover:bg-surface-hover hover:text-danger"
            onClick={() => remove.mutate()}
          >
            <Trash2 size={15} />
          </IconButton>
        )}
      </div>
    </div>
  )
}
