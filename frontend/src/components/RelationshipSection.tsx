/** Relationships section on the person record: grouped chips, add/remove
 * (Epic E, Design System §5.5). */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Network, Plus, X } from 'lucide-react'
import { type FormEvent, useDeferredValue, useState } from 'react'
import { Link } from 'react-router-dom'

import { api } from '../lib/api'
import type {
  PersonSummary,
  RelationshipOut,
  RelationshipRole,
  RelationshipType,
} from '../lib/types'
import { Avatar, Button, Dialog, Input, SectionRule } from './ui'

/** What the related person is *to* this card's person; a role implies its type (G-31). */
interface RelationshipOption {
  value: string
  label: string
  type: RelationshipType
  role?: RelationshipRole
}

const RELATIONSHIP_GROUPS: { group: string; options: RelationshipOption[] }[] = [
  {
    group: 'Family',
    options: [
      { value: 'mother', label: 'Mother', type: 'parent', role: 'mother' },
      { value: 'father', label: 'Father', type: 'parent', role: 'father' },
      { value: 'parent', label: 'Parent', type: 'parent' },
      { value: 'daughter', label: 'Daughter', type: 'child', role: 'daughter' },
      { value: 'son', label: 'Son', type: 'child', role: 'son' },
      { value: 'child', label: 'Child', type: 'child' },
      { value: 'sister', label: 'Sister', type: 'sibling', role: 'sister' },
      { value: 'brother', label: 'Brother', type: 'sibling', role: 'brother' },
      { value: 'sibling', label: 'Sibling', type: 'sibling' },
    ],
  },
  {
    group: 'Partners',
    options: [
      { value: 'wife', label: 'Wife', type: 'spouse', role: 'wife' },
      { value: 'husband', label: 'Husband', type: 'spouse', role: 'husband' },
      { value: 'spouse', label: 'Spouse', type: 'spouse' },
      { value: 'partner', label: 'Partner', type: 'partner' },
    ],
  },
  {
    group: 'Godfamily',
    options: [
      { value: 'godmother', label: 'Godmother', type: 'godparent', role: 'godmother' },
      { value: 'godfather', label: 'Godfather', type: 'godparent', role: 'godfather' },
      { value: 'godparent', label: 'Godparent', type: 'godparent' },
      { value: 'goddaughter', label: 'Goddaughter', type: 'godchild', role: 'goddaughter' },
      { value: 'godson', label: 'Godson', type: 'godchild', role: 'godson' },
      { value: 'godchild', label: 'Godchild', type: 'godchild' },
    ],
  },
  {
    group: 'Social',
    options: [
      { value: 'friend', label: 'Friend', type: 'friend' },
      { value: 'colleague', label: 'Colleague', type: 'colleague' },
    ],
  },
  {
    group: 'Other',
    options: [{ value: 'custom', label: 'Custom…', type: 'custom' }],
  },
]

const OPTIONS_BY_VALUE = new Map(
  RELATIONSHIP_GROUPS.flatMap((entry) => entry.options).map((option) => [option.value, option]),
)

function groupByLabel(relationships: RelationshipOut[]): [string, RelationshipOut[]][] {
  const groups = new Map<string, RelationshipOut[]>()
  for (const item of relationships) {
    const group = groups.get(item.label)
    if (group) group.push(item)
    else groups.set(item.label, [item])
  }
  return [...groups.entries()]
}

function RelationshipChip({
  relationship,
  onRemove,
}: {
  relationship: RelationshipOut
  onRemove: () => void
}) {
  return (
    <Link
      to={`/people/${relationship.person_id}`}
      className="group inline-flex items-center gap-1.5 rounded-full border border-border bg-surface py-2 pr-1.5 pl-1.5 text-sm transition-colors hover:bg-surface-hover"
    >
      <Avatar name={relationship.person_name} size={20} />
      {relationship.person_name}
      <button
        type="button"
        aria-label={`Remove relationship with ${relationship.person_name}`}
        className="relative rounded-full p-2 text-subtle opacity-100 before:absolute before:-inset-2 before:content-[''] transition-opacity hover:bg-surface-hover hover:text-danger can-hover:opacity-0 can-hover:group-hover:opacity-100"
        onClick={(event) => {
          event.preventDefault()
          event.stopPropagation()
          onRemove()
        }}
      >
        <X size={13} />
      </button>
    </Link>
  )
}

function AddRelationshipDialog({ personId, onClose }: { personId: number; onClose: () => void }) {
  const [query, setQuery] = useState('')
  const [selected, setSelected] = useState<PersonSummary | null>(null)
  const [choice, setChoice] = useState('spouse')
  const [customLabel, setCustomLabel] = useState('')
  const [error, setError] = useState<string | null>(null)
  const queryClient = useQueryClient()
  const deferredQuery = useDeferredValue(query)

  const results = useQuery({
    queryKey: ['people-search', deferredQuery],
    queryFn: () => api<PersonSummary[]>(`/api/people?q=${encodeURIComponent(deferredQuery)}`),
    enabled: deferredQuery.trim().length > 0,
  })

  const option = OPTIONS_BY_VALUE.get(choice)!

  const create = useMutation({
    mutationFn: () =>
      api<RelationshipOut>('/api/relationships', {
        method: 'POST',
        body: {
          person_id: personId,
          related_person_id: selected?.id,
          type: option.type,
          related_role: option.role,
          custom_label: option.type === 'custom' ? customLabel : undefined,
        },
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['person', personId] })
      onClose()
    },
    onError: (err) => setError(err.message),
  })

  const onSubmit = (event: FormEvent) => {
    event.preventDefault()
    if (selected) create.mutate()
  }

  const candidates = (results.data ?? []).filter((person) => person.id !== personId)

  return (
    <Dialog title="Add relationship" onClose={onClose}>
      <form onSubmit={onSubmit} className="space-y-4">
        {selected ? (
          <div className="flex items-center justify-between rounded-sm border border-border px-3 py-2">
            <span className="flex items-center gap-2 text-sm">
              <Avatar name={selected.full_name} size={24} />
              {selected.full_name}
            </span>
            <Button type="button" variant="ghost" size="sm" onClick={() => setSelected(null)}>
              Change
            </Button>
          </div>
        ) : (
          <div className="space-y-1.5">
            <Input
              id="relationship-search"
              label="Person"
              placeholder="Search by name…"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              autoFocus
            />
            {candidates.length > 0 && (
              <ul className="max-h-48 divide-y divide-border overflow-y-auto rounded-sm border border-border">
                {candidates.map((person) => (
                  <li key={person.id}>
                    <button
                      type="button"
                      onClick={() => setSelected(person)}
                      className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm hover:bg-surface-hover"
                    >
                      <Avatar name={person.full_name} size={24} />
                      {person.full_name}
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}

        <div className="space-y-1.5">
          <label htmlFor="relationship-type" className="label-caps block">
            Relationship
          </label>
          <select
            id="relationship-type"
            className="h-10 w-full rounded-sm border border-border bg-surface px-3 text-sm focus:border-accent"
            value={choice}
            onChange={(event) => setChoice(event.target.value)}
          >
            {RELATIONSHIP_GROUPS.map((group) => (
              <optgroup key={group.group} label={group.group}>
                {group.options.map((entry) => (
                  <option key={entry.value} value={entry.value}>
                    {entry.label}
                  </option>
                ))}
              </optgroup>
            ))}
          </select>
        </div>

        {option.type === 'custom' && (
          <Input
            id="relationship-custom-label"
            label="Label"
            placeholder="e.g. Godmother"
            value={customLabel}
            onChange={(event) => setCustomLabel(event.target.value)}
            required
          />
        )}

        {error && (
          <p role="alert" className="text-sm text-danger">
            {error}
          </p>
        )}

        <div className="flex justify-end gap-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button
            type="submit"
            disabled={
              !selected || create.isPending || (option.type === 'custom' && !customLabel.trim())
            }
          >
            Add
          </Button>
        </div>
      </form>
    </Dialog>
  )
}

export function RelationshipSection({
  personId,
  relationships,
}: {
  personId: number
  relationships: RelationshipOut[]
}) {
  const [adding, setAdding] = useState(false)
  const queryClient = useQueryClient()

  const remove = useMutation({
    mutationFn: (relationshipId: number) =>
      api<void>(`/api/relationships/${relationshipId}`, { method: 'DELETE' }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['person', personId] }),
  })

  return (
    <>
      <SectionRule
        title="Relationships"
        count={relationships.length}
        action={
          /* Labels hide below sm: two full-length buttons plus the rule would
             overflow a phone viewport; the icons carry the action there. */
          <div className="flex items-center">
            {relationships.length > 0 && (
              <Link to={`/people/${personId}/tree`} aria-label="View tree">
                <Button variant="ghost" size="sm" aria-label="View tree">
                  <Network size={14} aria-hidden />
                  <span className="hidden sm:inline">View tree</span>
                </Button>
              </Link>
            )}
            <Button
              variant="ghost"
              size="sm"
              aria-label="Add relationship"
              onClick={() => setAdding(true)}
            >
              <Plus size={14} aria-hidden />
              <span className="hidden sm:inline">Add relationship</span>
            </Button>
          </div>
        }
      />
      {relationships.length === 0 ? (
        <p className="py-6 text-sm text-muted">No relationships yet.</p>
      ) : (
        <div className="mt-4 space-y-4">
          {groupByLabel(relationships).map(([label, items]) => (
            <div key={label}>
              <p className="label-caps mb-2">{label}</p>
              <div className="flex flex-wrap gap-4">
                {items.map((relationship) => (
                  <RelationshipChip
                    key={relationship.id}
                    relationship={relationship}
                    onRemove={() => remove.mutate(relationship.id)}
                  />
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
      {adding && <AddRelationshipDialog personId={personId} onClose={() => setAdding(false)} />}
    </>
  )
}
