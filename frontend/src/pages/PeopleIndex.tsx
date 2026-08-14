/** People index — responsive grid of person cards with search (FR-10/26). */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Plus, Search, Star, Users, X } from 'lucide-react'
import { type FormEvent, useDeferredValue, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { Avatar, Button, Dialog, EmptyState, IconButton, Input, Spinner } from '../components/ui'
import { api } from '../lib/api'
import type { PersonDetail, PersonSummary, Tag } from '../lib/types'

function PersonCard({ person }: { person: PersonSummary }) {
  const queryClient = useQueryClient()

  const favorite = useMutation({
    mutationFn: (next: boolean) =>
      api<PersonDetail>(`/api/people/${person.id}`, { method: 'PATCH', body: { is_favorite: next } }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['people'] }),
    // A failed toggle must not leave the star showing a state the server rejected (G-21 lesson).
    onError: () => queryClient.invalidateQueries({ queryKey: ['people'] }),
  })

  return (
    <Link
      to={`/people/${person.id}`}
      className="relative rounded-lg border border-border bg-surface p-5 shadow-card transition-all hover:-translate-y-0.5 hover:border-border-strong hover:shadow-raised"
    >
      <IconButton
        label={person.is_favorite ? 'Remove from favorites' : 'Add to favorites'}
        className={`absolute top-2 right-2 hover:bg-surface-hover ${person.is_favorite ? 'text-seal' : 'text-subtle hover:text-ink'}`}
        disabled={favorite.isPending}
        onClick={(event) => {
          // The card itself is a link; the star must act without navigating.
          event.preventDefault()
          event.stopPropagation()
          favorite.mutate(!person.is_favorite)
        }}
      >
        <Star size={16} fill={person.is_favorite ? 'currentColor' : 'none'} />
      </IconButton>
      <div className="flex items-center gap-4">
        <Avatar
          name={person.full_name}
          photoUrl={
            person.has_photo
              ? `/api/people/${person.id}/photo?v=${encodeURIComponent(person.updated_at)}`
              : undefined
          }
        />
        <div className="min-w-0">
          <h2 className="truncate pr-9 font-display text-h3 font-semibold">{person.full_name}</h2>
          {person.pinned_fields.map((field) => (
            <p key={field.id} className="truncate text-sm text-muted">
              {field.value}
            </p>
          ))}
          {person.matched_fields?.map((field) => (
            <p key={`m-${field.id}`} className="truncate text-sm text-accent">
              <span className="text-subtle">{field.label}:</span> {field.value}
            </p>
          ))}
          {person.tags.length > 0 && (
            <div className="mt-1.5 flex flex-wrap gap-1">
              {person.tags.map((tag) => (
                <span
                  key={tag.id}
                  className="rounded-full bg-accent-fill px-2 py-0.5 text-xs text-accent"
                >
                  {tag.name}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>
    </Link>
  )
}

function TagFilterBar({
  tags,
  selected,
  onToggle,
  favoritesOnly,
  onToggleFavorites,
  onClear,
}: {
  tags: Tag[]
  selected: number[]
  onToggle: (id: number) => void
  favoritesOnly: boolean
  onToggleFavorites: () => void
  onClear: () => void
}) {
  const active = selected.length > 0 || favoritesOnly
  return (
    <div className="-mx-4 flex snap-x gap-2 overflow-x-auto px-4 pb-1 sm:mx-0 sm:flex-wrap sm:overflow-visible sm:px-0 sm:pb-0">
      <button
        type="button"
        aria-pressed={favoritesOnly}
        onClick={onToggleFavorites}
        className={`inline-flex h-11 shrink-0 snap-start items-center gap-1.5 rounded-full border px-3 text-xs font-medium transition-colors sm:h-8 ${
          favoritesOnly
            ? 'border-seal bg-seal-fill text-seal'
            : 'border-border bg-surface text-muted hover:bg-surface-hover hover:text-ink'
        }`}
      >
        <Star size={12} aria-hidden fill={favoritesOnly ? 'currentColor' : 'none'} />
        Favorites only
      </button>
      {tags.map((tag) => {
        const isSelected = selected.includes(tag.id)
        return (
          <button
            key={tag.id}
            type="button"
            aria-pressed={isSelected}
            onClick={() => onToggle(tag.id)}
            className={`inline-flex h-11 shrink-0 snap-start items-center gap-1.5 rounded-full border px-3 text-xs font-medium transition-colors sm:h-8 ${
              isSelected
                ? 'border-accent bg-accent-fill text-accent'
                : 'border-border bg-surface text-muted hover:bg-surface-hover hover:text-ink'
            }`}
          >
            {tag.name}
            <span className={isSelected ? 'text-accent/70' : 'text-subtle'}>{tag.person_count}</span>
          </button>
        )
      })}
      {active && (
        <button
          type="button"
          onClick={onClear}
          className="inline-flex h-11 shrink-0 snap-start items-center gap-1 px-2 text-xs text-muted hover:text-ink sm:h-8"
        >
          <X size={12} aria-hidden /> Clear filters
        </button>
      )}
    </div>
  )
}

export function PeopleIndex() {
  const [query, setQuery] = useState('')
  const [searchFields, setSearchFields] = useState(false)
  const deferredQuery = useDeferredValue(query)
  const [adding, setAdding] = useState(false)
  const [newName, setNewName] = useState('')
  const [selectedTags, setSelectedTags] = useState<number[]>([])
  const [favoritesOnly, setFavoritesOnly] = useState(false)
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const tags = useQuery({
    queryKey: ['tags'],
    queryFn: () => api<Tag[]>('/api/tags'),
  })

  const people = useQuery({
    queryKey: ['people', deferredQuery, searchFields, selectedTags, favoritesOnly],
    queryFn: () => {
      const params = new URLSearchParams()
      if (deferredQuery) params.set('q', deferredQuery)
      if (searchFields) params.set('fields', 'true')
      for (const tagId of selectedTags) params.append('tags', String(tagId))
      if (favoritesOnly) params.set('favorites', 'true')
      const suffix = params.toString()
      return api<PersonSummary[]>(`/api/people${suffix ? `?${suffix}` : ''}`)
    },
  })

  const toggleTag = (id: number) =>
    setSelectedTags((current) =>
      current.includes(id) ? current.filter((tagId) => tagId !== id) : [...current, id],
    )

  const clearFilters = () => {
    setSelectedTags([])
    setFavoritesOnly(false)
  }

  const create = useMutation({
    mutationFn: () =>
      api<PersonDetail>('/api/people', { method: 'POST', body: { full_name: newName } }),
    onSuccess: async (person) => {
      await queryClient.invalidateQueries({ queryKey: ['people'] })
      navigate(`/people/${person.id}`)
    },
  })

  const onCreate = (event: FormEvent) => {
    event.preventDefault()
    if (newName.trim()) create.mutate()
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-3">
        <h1 className="font-display text-h2 font-semibold sm:text-h1">People</h1>
        <Button onClick={() => setAdding(true)} className="shrink-0">
          <Plus size={16} aria-hidden /> Add person
        </Button>
      </div>

      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-end">
        <label className="order-2 flex min-h-11 w-full items-center gap-1.5 text-xs text-muted select-none sm:order-1 sm:min-h-0 sm:w-auto">
          <input
            type="checkbox"
            checked={searchFields}
            onChange={(event) => setSearchFields(event.target.checked)}
            className="h-4 w-4 accent-accent"
          />
          Search field values too
        </label>
        <div className="relative order-1 w-full sm:order-2 sm:w-64">
          <Search size={16} className="absolute top-1/2 left-3 -translate-y-1/2 text-subtle" aria-hidden />
          <Input
            aria-label={searchFields ? 'Search people by name or field value' : 'Search people by name'}
            placeholder={searchFields ? 'Search name & fields…' : 'Search…'}
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            className="w-full pl-9"
          />
        </div>
      </div>

      <TagFilterBar
        tags={tags.data ?? []}
        selected={selectedTags}
        onToggle={toggleTag}
        favoritesOnly={favoritesOnly}
        onToggleFavorites={() => setFavoritesOnly((current) => !current)}
        onClear={clearFilters}
      />

      {people.isPending ? (
        <Spinner />
      ) : people.data && people.data.length > 0 ? (
        <div className="grid grid-cols-[repeat(auto-fill,minmax(240px,1fr))] gap-5">
          {people.data.map((person) => (
            <PersonCard key={person.id} person={person} />
          ))}
        </div>
      ) : (
        <EmptyState
          icon={<Users size={32} aria-hidden />}
          message={query ? 'No one matches that search.' : 'No one here yet. Add the first person.'}
          action={
            !query ? (
              <Button onClick={() => setAdding(true)}>
                <Plus size={16} aria-hidden /> Add person
              </Button>
            ) : undefined
          }
        />
      )}

      {adding && (
        <Dialog title="Add person" onClose={() => setAdding(false)}>
          <form onSubmit={onCreate} className="space-y-4">
            <Input
              id="new-name"
              label="Full name"
              value={newName}
              onChange={(event) => setNewName(event.target.value)}
              autoFocus
              required
            />
            <div className="flex justify-end gap-2">
              <Button type="button" variant="secondary" onClick={() => setAdding(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={create.isPending}>
                {create.isPending ? 'Creating…' : 'Create'}
              </Button>
            </div>
          </form>
        </Dialog>
      )}
    </div>
  )
}
