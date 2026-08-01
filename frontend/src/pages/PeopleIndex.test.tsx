/** Component tests for the people index: tag filter, favorites filter, card star (G-04). */

import { QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { PersonSummary, Tag } from '../lib/types'
import { createTestQueryClient, renderWithProviders } from '../test/utils'
import { PeopleIndex } from './PeopleIndex'

const { mockApi } = vi.hoisted(() => ({ mockApi: vi.fn() }))

// Mock the network at the api.ts boundary (never stub global fetch).
vi.mock('../lib/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../lib/api')>()
  return { ...actual, api: mockApi }
})

function personSummary(overrides: Partial<PersonSummary> = {}): PersonSummary {
  return {
    id: 1,
    full_name: 'Ada Lovelace',
    has_photo: false,
    updated_at: '2026-01-01T00:00:00Z',
    pinned_fields: [],
    is_favorite: false,
    tags: [],
    ...overrides,
  }
}

const familyTag: Tag = { id: 1, name: 'Family', person_count: 2 }
const workTag: Tag = { id: 2, name: 'Work', person_count: 1 }

beforeEach(() => {
  mockApi.mockReset()
})

describe('PeopleIndex — tag filter', () => {
  it('includes the selected tag id in the people request', async () => {
    mockApi.mockImplementation(async (path: string) => {
      if (path === '/api/tags') return [familyTag, workTag]
      if (path.startsWith('/api/people')) return [personSummary()]
      throw new Error(`Unhandled request: ${path}`)
    })

    renderWithProviders(<PeopleIndex />)

    const chip = await screen.findByRole('button', { name: /Family/ })
    await userEvent.click(chip)

    await waitFor(() => expect(mockApi).toHaveBeenCalledWith('/api/people?tags=1'))
  })
})

describe('PeopleIndex — favorites filter', () => {
  it('includes favorites=true in the people request once toggled on', async () => {
    mockApi.mockImplementation(async (path: string) => {
      if (path === '/api/tags') return []
      if (path.startsWith('/api/people')) return [personSummary({ is_favorite: true })]
      throw new Error(`Unhandled request: ${path}`)
    })

    renderWithProviders(<PeopleIndex />)

    const toggle = await screen.findByRole('button', { name: 'Favorites only' })
    await userEvent.click(toggle)

    await waitFor(() => expect(mockApi).toHaveBeenCalledWith('/api/people?favorites=true'))
  })
})

describe('PeopleIndex — favorite star on a card', () => {
  it('toggles favorite via PATCH and does not navigate to the person', async () => {
    mockApi.mockImplementation(async (path: string, options: { method?: string } = {}) => {
      const method = options.method ?? 'GET'
      if (path === '/api/tags') return []
      if (path.startsWith('/api/people') && method === 'GET') return [personSummary()]
      if (path === '/api/people/1' && method === 'PATCH') {
        return personSummary({ is_favorite: true })
      }
      throw new Error(`Unhandled request: ${method} ${path}`)
    })

    // A custom two-route render (rather than the shared helper) so navigation
    // away from "/" would actually be observable in the DOM.
    const queryClient = createTestQueryClient()
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/']}>
          <Routes>
            <Route path="/" element={<PeopleIndex />} />
            <Route path="/people/:id" element={<div>PERSON PAGE MARKER</div>} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>,
    )

    await screen.findByRole('heading', { name: 'People' })
    const star = await screen.findByRole('button', { name: 'Add to favorites' })
    await userEvent.click(star)

    await waitFor(() =>
      expect(mockApi).toHaveBeenCalledWith('/api/people/1', {
        method: 'PATCH',
        body: { is_favorite: true },
      }),
    )
    expect(screen.queryByText('PERSON PAGE MARKER')).not.toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'People' })).toBeInTheDocument()
  })
})
