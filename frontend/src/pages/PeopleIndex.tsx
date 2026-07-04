/** People index — responsive grid of person cards with search (FR-10/26). */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Plus, Search, Users } from 'lucide-react'
import { type FormEvent, useDeferredValue, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { Avatar, Button, Dialog, EmptyState, Input, Spinner } from '../components/ui'
import { api } from '../lib/api'
import type { PersonDetail, PersonSummary } from '../lib/types'

export function PeopleIndex() {
  const [query, setQuery] = useState('')
  const deferredQuery = useDeferredValue(query)
  const [adding, setAdding] = useState(false)
  const [newName, setNewName] = useState('')
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const people = useQuery({
    queryKey: ['people', deferredQuery],
    queryFn: () =>
      api<PersonSummary[]>(`/api/people${deferredQuery ? `?q=${encodeURIComponent(deferredQuery)}` : ''}`),
  })

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
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="font-display text-3xl font-semibold">People</h1>
        <div className="flex-1" />
        <div className="relative">
          <Search size={16} className="absolute top-1/2 left-3 -translate-y-1/2 text-subtle" aria-hidden />
          <Input
            aria-label="Search people by name"
            placeholder="Search…"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            className="w-56 pl-9"
          />
        </div>
        <Button onClick={() => setAdding(true)}>
          <Plus size={16} aria-hidden /> Add person
        </Button>
      </div>

      {people.isPending ? (
        <Spinner />
      ) : people.data && people.data.length > 0 ? (
        <div className="grid grid-cols-[repeat(auto-fill,minmax(240px,1fr))] gap-5">
          {people.data.map((person) => (
            <Link
              key={person.id}
              to={`/people/${person.id}`}
              className="rounded-lg border border-border bg-surface p-5 shadow-(--shadow-card) transition-all hover:-translate-y-0.5 hover:shadow-(--shadow-raised)"
            >
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
                  <h2 className="truncate font-display text-lg font-semibold">{person.full_name}</h2>
                  {person.pinned_fields.map((field) => (
                    <p key={field.id} className="truncate text-sm text-muted">
                      {field.value}
                    </p>
                  ))}
                </div>
              </div>
            </Link>
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
