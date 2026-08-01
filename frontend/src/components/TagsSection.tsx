/** Tags section on the ID-card: chips + create-on-type input (Phase 3, tags & favorites). */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Plus, X } from 'lucide-react'
import { type FormEvent, useState } from 'react'

import { api } from '../lib/api'
import type { Tag } from '../lib/types'
import { Button, SectionHeading } from './ui'

export function TagsSection({ personId, tags }: { personId: number; tags: Tag[] }) {
  const [name, setName] = useState('')
  const [error, setError] = useState<string | null>(null)
  const queryClient = useQueryClient()

  const allTags = useQuery({
    queryKey: ['tags'],
    queryFn: () => api<Tag[]>('/api/tags'),
  })

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['person', personId] })
    queryClient.invalidateQueries({ queryKey: ['tags'] })
    queryClient.invalidateQueries({ queryKey: ['people'] })
  }

  const assign = useMutation({
    mutationFn: (tagName: string) =>
      api<Tag>(`/api/people/${personId}/tags`, { method: 'POST', body: { name: tagName } }),
    onSuccess: () => {
      setName('')
      setError(null)
      invalidate()
    },
    onError: (err) => setError(err.message),
  })

  const unassign = useMutation({
    mutationFn: (tagId: number) =>
      api<void>(`/api/people/${personId}/tags/${tagId}`, { method: 'DELETE' }),
    onSuccess: invalidate,
    // A failed removal must not leave a chip that looks gone but isn't (G-21 lesson).
    onError: invalidate,
  })

  const onSubmit = (event: FormEvent) => {
    event.preventDefault()
    const trimmed = name.trim()
    if (!trimmed) return
    assign.mutate(trimmed)
  }

  return (
    <>
      <SectionHeading title="Tags" />
      <div className="space-y-3 px-4 py-4">
        <div className="flex flex-wrap gap-2">
          {tags.length === 0 ? (
            <p className="text-sm text-muted">No tags yet.</p>
          ) : (
            tags.map((tag) => (
              <span
                key={tag.id}
                className="inline-flex items-center gap-1.5 rounded-full border border-border bg-surface-subtle py-1 pr-1 pl-3 text-sm"
              >
                {tag.name}
                <button
                  type="button"
                  aria-label={`Remove tag ${tag.name}`}
                  className="rounded-full p-0.5 text-subtle hover:bg-surface-hover hover:text-danger"
                  onClick={() => unassign.mutate(tag.id)}
                >
                  <X size={13} />
                </button>
              </span>
            ))
          )}
        </div>
        <form onSubmit={onSubmit} className="flex items-center gap-2">
          <input
            aria-label="Add tag"
            list="tag-suggestions"
            placeholder="Add a tag…"
            className="h-9 w-full max-w-56 rounded-sm border border-border bg-surface px-3 text-sm focus:border-accent"
            value={name}
            onChange={(event) => setName(event.target.value)}
          />
          <datalist id="tag-suggestions">
            {(allTags.data ?? []).map((tag) => (
              <option key={tag.id} value={tag.name} />
            ))}
          </datalist>
          <Button type="submit" variant="secondary" size="sm" disabled={assign.isPending}>
            <Plus size={14} aria-hidden /> Add
          </Button>
        </form>
        {error && (
          <p role="alert" className="text-sm text-danger">
            {error}
          </p>
        )}
      </div>
    </>
  )
}
