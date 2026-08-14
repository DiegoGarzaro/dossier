/** Tags on the person record: a centered strip of chips under the masthead,
 * with a create-on-type pill input (Phase 3, tags & favorites). */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Plus, X } from 'lucide-react'
import { type FormEvent, useState } from 'react'

import { api } from '../lib/api'
import type { PersonDetail, Tag } from '../lib/types'
import { Button } from './ui'

/** Collapse whitespace the way the backend's `normalize_name` does, so the chip
 * shown optimistically is the chip the server echoes back.
 *
 * Args:
 *   name: The raw name as typed.
 *
 * Returns:
 *   The normalized name, e.g. `"  Close   Family "` -> `"Close Family"`.
 */
function normalizeName(name: string): string {
  return name.trim().split(/\s+/).join(' ')
}

const sameName = (a: string, b: string) => a.toLowerCase() === b.toLowerCase()

interface Rollback {
  previous?: PersonDetail
}

export function TagsSection({ personId, tags }: { personId: number; tags: Tag[] }) {
  const [name, setName] = useState('')
  const [error, setError] = useState<string | null>(null)
  const queryClient = useQueryClient()
  const personKey = ['person', personId]

  const allTags = useQuery({
    queryKey: ['tags'],
    queryFn: () => api<Tag[]>('/api/tags'),
  })

  /** Rewrite the cached person's tag list — the chips render from it. */
  const setPersonTags = (update: (current: Tag[]) => Tag[]) =>
    queryClient.setQueryData<PersonDetail>(personKey, (person) =>
      person ? { ...person, tags: update(person.tags) } : person,
    )

  /** Take a snapshot and stop any in-flight person fetch from landing on top
   * of the optimistic edit we are about to make. */
  const beginOptimistic = async (): Promise<Rollback> => {
    await queryClient.cancelQueries({ queryKey: personKey })
    setError(null)
    return { previous: queryClient.getQueryData<PersonDetail>(personKey) }
  }

  const rollback = (err: Error, _variables: unknown, context: Rollback | undefined) => {
    // A failed edit must never leave a chip that looks applied but isn't, nor
    // one that looks gone but isn't (G-21 lesson).
    if (context?.previous) queryClient.setQueryData(personKey, context.previous)
    setError(err.message)
  }

  /** The tag counts on the People index are derived data. Refetch them even
   * while that screen is unmounted, so its badges aren't stale on return (G-49). */
  const refreshLists = () => {
    queryClient.invalidateQueries({ queryKey: ['tags'], refetchType: 'all' })
    queryClient.invalidateQueries({ queryKey: ['people'], refetchType: 'all' })
  }

  const assign = useMutation<Tag, Error, string, Rollback>({
    mutationFn: (tagName) =>
      api<Tag>(`/api/people/${personId}/tags`, { method: 'POST', body: { name: tagName } }),
    onMutate: async (tagName) => {
      const context = await beginOptimistic()
      // Show the chip and empty the box now: a round-trip of unchanged UI is
      // what made this read as "the tag wasn't added" (G-49).
      const known = (allTags.data ?? []).find((tag) => sameName(tag.name, tagName))
      setPersonTags((current) => [
        ...current,
        known ?? { id: -Date.now(), name: tagName, person_count: 1 },
      ])
      setName('')
      return context
    },
    onError: rollback,
    onSuccess: (tag) => {
      // Swap the placeholder (negative id) for the server's row.
      setPersonTags((current) => [...current.filter((each) => each.id > 0 && each.id !== tag.id), tag])
      // The response carries the new person_count; write it straight into the
      // list the index badges read rather than waiting on a refetch.
      queryClient.setQueryData<Tag[]>(['tags'], (list) =>
        list &&
        [...list.filter((each) => each.id !== tag.id), tag].sort((a, b) =>
          a.name.localeCompare(b.name),
        ),
      )
    },
    onSettled: refreshLists,
  })

  const unassign = useMutation<void, Error, number, Rollback>({
    mutationFn: (tagId) =>
      api<void>(`/api/people/${personId}/tags/${tagId}`, { method: 'DELETE' }),
    onMutate: async (tagId) => {
      const context = await beginOptimistic()
      setPersonTags((current) => current.filter((tag) => tag.id !== tagId))
      return context
    },
    onError: rollback,
    onSettled: refreshLists,
  })

  /** A chip still carrying a placeholder id exists only on this client until
   * the assignment lands; `DELETE .../tags/-1738…` would 404 and surface a
   * bogus "Tag not found", while the in-flight assign put the chip back anyway
   * — a tag the user removed reappearing (G-54). Removal waits for the real id. */
  const isPending = (tag: Tag) => tag.id < 0

  const removeTag = (tag: Tag) => {
    if (isPending(tag)) return
    unassign.mutate(tag.id)
  }

  const onSubmit = (event: FormEvent) => {
    event.preventDefault()
    const trimmed = normalizeName(name)
    if (!trimmed) return
    // Already worn — including the chip we just added optimistically, which is
    // what an impatient second Enter would otherwise duplicate.
    if (tags.some((tag) => sameName(tag.name, trimmed))) {
      setName('')
      setError(null)
      return
    }
    assign.mutate(trimmed)
  }

  // Suggest only tags this person doesn't already wear.
  const suggestions = (allTags.data ?? []).filter(
    (tag) => !tags.some((worn) => sameName(worn.name, tag.name)),
  )

  const addForm = (
    <form onSubmit={onSubmit} className="flex items-center gap-1.5">
      <input
        aria-label="Add tag"
        list="tag-suggestions"
        placeholder="Add a tag…"
        className="h-8 w-32 rounded-full border border-border bg-surface px-3 text-[13px] transition-colors placeholder:text-subtle focus:border-accent"
        value={name}
        onChange={(event) => setName(event.target.value)}
      />
      <datalist id="tag-suggestions">
        {suggestions.map((tag) => (
          <option key={tag.id} value={tag.name} />
        ))}
      </datalist>
      <Button type="submit" variant="ghost" size="sm" className="rounded-full px-2.5">
        <Plus size={14} aria-hidden /> Add
      </Button>
    </form>
  )

  return (
    <div className="mt-5 flex flex-col items-center gap-2.5">
      {/* Chips and the add form share one centered row; the gap keeps the
          remove buttons' 44px pseudo hit areas from overlapping (see chip). */}
      <div className="flex flex-wrap items-center justify-center gap-x-4 gap-y-2">
        {tags.map((tag) => (
          <span
            key={tag.id}
            className="inline-flex items-center gap-1 rounded-full border border-border bg-surface py-1 pr-1 pl-3 text-[13px]"
          >
            {tag.name}
            {/* Visual size stays chip-scale; the pseudo-element grows the
                actual hit area to 44px without inflating the layout
                (WCAG 2.5.8 target-size technique) — chips are gap-x-4 apart
                so neighboring hit areas don't overlap. */}
            <button
              type="button"
              aria-label={`Remove tag ${tag.name}`}
              className="relative rounded-full p-1.5 text-subtle before:absolute before:-inset-2 before:content-[''] hover:bg-surface-hover hover:text-danger disabled:pointer-events-none disabled:opacity-40"
              disabled={isPending(tag)}
              onClick={() => removeTag(tag)}
            >
              <X size={13} />
            </button>
          </span>
        ))}
        {addForm}
      </div>
      {error && (
        <p role="alert" className="text-sm text-danger">
          {error}
        </p>
      )}
    </div>
  )
}
