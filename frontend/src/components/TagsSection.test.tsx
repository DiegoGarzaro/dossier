/** Tags on the ID-card: the chip, the input and the tag counts must react to
 * the user's action immediately, not two network round-trips later (G-49). */

import { QueryClient, QueryClientProvider, useQuery } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { PersonDetail, Tag } from '../lib/types'
import { TagsSection } from './TagsSection'

const { mockApi } = vi.hoisted(() => ({ mockApi: vi.fn() }))

vi.mock('../lib/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../lib/api')>()
  return { ...actual, api: mockApi }
})

const family: Tag = { id: 10, name: 'Family', person_count: 3 }

function person(tags: Tag[]): PersonDetail {
  return {
    id: 1,
    full_name: 'Ana Silva',
    has_photo: false,
    fields: [],
    documents: [],
    relationships: [],
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    is_favorite: false,
    tags,
  }
}

/** Renders the section exactly the way PersonPage wires it: the chips are a
 * prop derived from the cached `['person', 1]` query. */
function renderTags(tags: Tag[] = []) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, staleTime: 10_000 }, mutations: { retry: false } },
  })
  queryClient.setQueryData(['person', 1], person(tags))

  function Host() {
    const detail = useQuery({
      queryKey: ['person', 1],
      queryFn: () => mockApi('/api/people/1') as Promise<PersonDetail>,
    })
    if (!detail.data) return null
    return <TagsSection personId={1} tags={detail.data.tags} />
  }
  function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  }
  return { queryClient, ...render(<Host />, { wrapper: Wrapper }) }
}

const chipNames = () =>
  screen
    .queryAllByRole('button', { name: /^Remove tag / })
    .map((button) => button.getAttribute('aria-label')!.replace('Remove tag ', ''))

beforeEach(() => {
  mockApi.mockReset()
})

describe('TagsSection', () => {
  it('shows the new chip and clears the input before the person refetch resolves', async () => {
    // The assignment succeeds, but the follow-up person/tags refetches never
    // settle — exactly what a slow link looks like to the user.
    mockApi.mockImplementation(async (path: string, options: { method?: string } = {}) => {
      const method = options.method ?? 'GET'
      if (path === '/api/people/1/tags' && method === 'POST') {
        return { id: 10, name: 'Family', person_count: 4 } satisfies Tag
      }
      if (path === '/api/tags' && method === 'GET') return []
      return new Promise(() => {}) // never resolves
    })
    const user = userEvent.setup()
    renderTags()

    await user.type(screen.getByLabelText('Add tag'), 'Family')
    await user.click(screen.getByRole('button', { name: /Add/ }))

    await waitFor(() => expect(chipNames()).toEqual(['Family']))
    expect(screen.getByLabelText('Add tag')).toHaveValue('')
  })

  it('drops the chip immediately when a tag is removed', async () => {
    mockApi.mockImplementation(async (path: string, options: { method?: string } = {}) => {
      const method = options.method ?? 'GET'
      if (path === '/api/people/1/tags/10' && method === 'DELETE') return undefined
      if (path === '/api/tags' && method === 'GET') return []
      return new Promise(() => {})
    })
    const user = userEvent.setup()
    renderTags([family])

    await user.click(screen.getByRole('button', { name: 'Remove tag Family' }))

    await waitFor(() => expect(chipNames()).toEqual([]))
  })

  it('puts the chip back and reports the error when the server rejects the tag', async () => {
    mockApi.mockImplementation(async (path: string, options: { method?: string } = {}) => {
      const method = options.method ?? 'GET'
      if (path === '/api/people/1/tags' && method === 'POST') throw new Error('Tag name too long')
      if (path === '/api/tags' && method === 'GET') return []
      if (path === '/api/people/1' && method === 'GET') return person([])
      return new Promise(() => {})
    })
    const user = userEvent.setup()
    renderTags()

    await user.type(screen.getByLabelText('Add tag'), 'Family')
    await user.click(screen.getByRole('button', { name: /Add/ }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Tag name too long')
    await waitFor(() => expect(chipNames()).toEqual([]))
  })

  it('refreshes the tag counts from the assignment response', async () => {
    // The tag list is served once and then hangs, so only a count taken from
    // the mutation response itself can satisfy this.
    let tagListServed = false
    mockApi.mockImplementation(async (path: string, options: { method?: string } = {}) => {
      const method = options.method ?? 'GET'
      if (path === '/api/people/1/tags' && method === 'POST') {
        return { id: 10, name: 'Family', person_count: 4 } satisfies Tag
      }
      if (path === '/api/tags' && method === 'GET' && !tagListServed) {
        tagListServed = true
        return [family]
      }
      return new Promise(() => {})
    })
    const user = userEvent.setup()
    const { queryClient } = renderTags()

    await user.type(screen.getByLabelText('Add tag'), 'Family')
    await user.click(screen.getByRole('button', { name: /Add/ }))

    // The badge on the people index reads this cache entry; it must not stay
    // at 3 until the next manual refresh.
    await waitFor(() =>
      expect(queryClient.getQueryData<Tag[]>(['tags'])).toEqual([
        { id: 10, name: 'Family', person_count: 4 },
      ]),
    )
  })

  // G-54: while the assignment is in flight the chip carries a client-only
  // placeholder id. Removing it then would DELETE a non-existent tag (404 →
  // bogus "Tag not found") while the in-flight assign put the chip back — a
  // tag the user removed reappearing.
  it('does not let a still-pending chip be removed with a placeholder id', async () => {
    let resolveAssign: (tag: Tag) => void = () => {}
    mockApi.mockImplementation(async (path: string, options: { method?: string } = {}) => {
      const method = options.method ?? 'GET'
      if (path === '/api/people/1/tags' && method === 'POST') {
        return new Promise<Tag>((resolve) => {
          resolveAssign = resolve
        })
      }
      if (path === '/api/tags' && method === 'GET') return []
      if (method === 'DELETE') throw new Error('Tag not found')
      return new Promise(() => {})
    })
    const user = userEvent.setup()
    renderTags()

    await user.type(screen.getByLabelText('Add tag'), 'Family')
    await user.click(screen.getByRole('button', { name: /Add/ }))
    await waitFor(() => expect(chipNames()).toEqual(['Family']))

    // The user changes their mind before the POST lands.
    const remove = screen.getByRole('button', { name: 'Remove tag Family' })
    expect(remove).toBeDisabled()
    await user.click(remove)

    expect(mockApi).not.toHaveBeenCalledWith(
      expect.stringContaining('/tags/-'),
      expect.objectContaining({ method: 'DELETE' }),
    )
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()

    // Once the real id lands the chip becomes removable.
    resolveAssign({ id: 10, name: 'Family', person_count: 1 })
    await waitFor(() =>
      expect(screen.getByRole('button', { name: 'Remove tag Family' })).toBeEnabled(),
    )
  })

  it('ignores a blank submission instead of posting an empty tag', async () => {
    mockApi.mockImplementation(async (path: string) => {
      if (path === '/api/tags') return []
      return new Promise(() => {})
    })
    const user = userEvent.setup()
    renderTags()

    await user.type(screen.getByLabelText('Add tag'), '   ')
    await user.click(screen.getByRole('button', { name: /Add/ }))

    expect(mockApi).not.toHaveBeenCalledWith('/api/people/1/tags', expect.anything())
  })
})
