/** Component tests for the ID-card: tags, favorites, sensitive-field masking (G-04). */

import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { FieldOut, PersonDetail, Tag } from '../lib/types'
import { renderWithProviders } from '../test/utils'
import { PersonPage } from './PersonPage'

const { mockApi } = vi.hoisted(() => ({ mockApi: vi.fn() }))

// Mock the network at the api.ts boundary (never stub global fetch); keep the
// real ApiError class so `error instanceof ApiError` checks in components work.
vi.mock('../lib/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../lib/api')>()
  return { ...actual, api: mockApi }
})

function sensitiveField(overrides: Partial<FieldOut> = {}): FieldOut {
  return {
    id: 5,
    label: 'Passport number',
    value: '123-45-6789',
    type: 'sensitive',
    is_pinned: false,
    is_system: false,
    position: 0,
    updated_at: '2026-01-01T00:00:00Z',
    ...overrides,
  }
}

function person(overrides: Partial<PersonDetail> = {}): PersonDetail {
  return {
    id: 1,
    full_name: 'Ada Lovelace',
    has_photo: false,
    fields: [],
    documents: [],
    relationships: [],
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    is_favorite: false,
    tags: [],
    ...overrides,
  }
}

async function renderPersonPage() {
  const result = renderWithProviders(<PersonPage />, {
    route: '/people/1',
    path: '/people/:id',
  })
  // Wait for the initial GET to resolve and the card to render.
  await screen.findByRole('heading', { name: 'Ada Lovelace' })
  return result
}

beforeEach(() => {
  mockApi.mockReset()
})

describe('PersonPage — tags', () => {
  it('renders a chip per tag and unassigns it when its × is clicked', async () => {
    const family: Tag = { id: 10, name: 'Family', person_count: 3 }
    mockApi.mockImplementation(async (path: string, options: { method?: string } = {}) => {
      const method = options.method ?? 'GET'
      if (path === '/api/people/1' && method === 'GET') return person({ tags: [family] })
      if (path === '/api/tags' && method === 'GET') return [family]
      if (path === '/api/people/1/tags/10' && method === 'DELETE') return undefined
      throw new Error(`Unhandled request: ${method} ${path}`)
    })

    await renderPersonPage()

    expect(await screen.findByText('Family')).toBeInTheDocument()

    const removeButton = screen.getByRole('button', { name: 'Remove tag Family' })
    await userEvent.click(removeButton)

    await waitFor(() =>
      expect(mockApi).toHaveBeenCalledWith('/api/people/1/tags/10', { method: 'DELETE' }),
    )
  })

  it('POSTs a new tag when a name is typed and submitted', async () => {
    mockApi.mockImplementation(async (path: string, options: { method?: string } = {}) => {
      const method = options.method ?? 'GET'
      if (path === '/api/people/1' && method === 'GET') return person()
      if (path === '/api/tags' && method === 'GET') return []
      if (path === '/api/people/1/tags' && method === 'POST') {
        return { id: 99, name: 'Godparents', person_count: 1 }
      }
      throw new Error(`Unhandled request: ${method} ${path}`)
    })

    await renderPersonPage()

    const input = await screen.findByRole('combobox', { name: 'Add tag' })
    await userEvent.type(input, 'Godparents{Enter}')

    await waitFor(() =>
      expect(mockApi).toHaveBeenCalledWith('/api/people/1/tags', {
        method: 'POST',
        body: { name: 'Godparents' },
      }),
    )
  })

  it('ignores a whitespace-only submission without calling the API', async () => {
    mockApi.mockImplementation(async (path: string, options: { method?: string } = {}) => {
      const method = options.method ?? 'GET'
      if (path === '/api/people/1' && method === 'GET') return person()
      if (path === '/api/tags' && method === 'GET') return []
      throw new Error(`Unhandled request: ${method} ${path}`)
    })

    await renderPersonPage()

    const input = await screen.findByRole('combobox', { name: 'Add tag' })
    await userEvent.type(input, '   {Enter}')

    expect(mockApi).not.toHaveBeenCalledWith(
      '/api/people/1/tags',
      expect.objectContaining({ method: 'POST' }),
    )
  })
})

describe('PersonPage — favorites', () => {
  it('reflects is_favorite in the star label and toggles it via PATCH', async () => {
    mockApi.mockImplementation(async (path: string, options: { method?: string } = {}) => {
      const method = options.method ?? 'GET'
      if (path === '/api/people/1' && method === 'GET') return person({ is_favorite: false })
      if (path === '/api/tags' && method === 'GET') return []
      if (path === '/api/people/1' && method === 'PATCH') return person({ is_favorite: true })
      throw new Error(`Unhandled request: ${method} ${path}`)
    })

    await renderPersonPage()

    const star = await screen.findByRole('button', { name: 'Add to favorites' })
    await userEvent.click(star)

    await waitFor(() =>
      expect(mockApi).toHaveBeenCalledWith('/api/people/1', {
        method: 'PATCH',
        body: { is_favorite: true },
      }),
    )
  })
})

describe('PersonPage — letterhead chrome', () => {
  it('shows the file number and a link back to the index in the masthead', async () => {
    mockApi.mockImplementation(async (path: string, options: { method?: string } = {}) => {
      const method = options.method ?? 'GET'
      if (path === '/api/people/1' && method === 'GET') return person()
      if (path === '/api/tags' && method === 'GET') return []
      throw new Error(`Unhandled request: ${method} ${path}`)
    })

    await renderPersonPage()

    expect(screen.getByText(/File № 0001 · Added 2026-01-01/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'All people' })).toHaveAttribute('href', '/')
  })

  it('tucks rename, export and delete behind a "More actions" menu', async () => {
    mockApi.mockImplementation(async (path: string, options: { method?: string } = {}) => {
      const method = options.method ?? 'GET'
      if (path === '/api/people/1' && method === 'GET') return person()
      if (path === '/api/tags' && method === 'GET') return []
      throw new Error(`Unhandled request: ${method} ${path}`)
    })

    await renderPersonPage()

    // Nothing leaks before the menu is opened.
    expect(screen.queryByRole('link', { name: 'Export vCard' })).not.toBeInTheDocument()
    expect(screen.queryByRole('menuitem', { name: 'Delete person' })).not.toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'More actions' }))

    expect(screen.getByRole('menuitem', { name: 'Rename person' })).toBeInTheDocument()
    expect(screen.getByRole('menuitem', { name: 'Export vCard' })).toHaveAttribute(
      'href',
      '/api/people/1/vcard',
    )
    expect(screen.getByRole('menuitem', { name: 'Export JSON' })).toHaveAttribute(
      'href',
      '/api/people/1/export',
    )

    await userEvent.click(screen.getByRole('menuitem', { name: 'Delete person' }))
    expect(await screen.findByRole('dialog', { name: 'Delete person?' })).toBeInTheDocument()
  })

  it('opens the rename dialog from the menu', async () => {
    mockApi.mockImplementation(async (path: string, options: { method?: string } = {}) => {
      const method = options.method ?? 'GET'
      if (path === '/api/people/1' && method === 'GET') return person()
      if (path === '/api/tags' && method === 'GET') return []
      throw new Error(`Unhandled request: ${method} ${path}`)
    })

    await renderPersonPage()

    await userEvent.click(screen.getByRole('button', { name: 'More actions' }))
    await userEvent.click(screen.getByRole('menuitem', { name: 'Rename person' }))

    expect(await screen.findByRole('dialog', { name: 'Rename person' })).toBeInTheDocument()
  })
})

describe('PersonPage — sensitive fields (SEC-7 regression guard)', () => {
  it('masks a sensitive field value until the reveal control is clicked', async () => {
    mockApi.mockImplementation(async (path: string, options: { method?: string } = {}) => {
      const method = options.method ?? 'GET'
      if (path === '/api/people/1' && method === 'GET') {
        return person({ fields: [sensitiveField()] })
      }
      if (path === '/api/tags' && method === 'GET') return []
      throw new Error(`Unhandled request: ${method} ${path}`)
    })

    await renderPersonPage()

    await screen.findByText('Passport number')
    expect(screen.getByText('••••••••')).toBeInTheDocument()
    expect(screen.queryByText('123-45-6789')).not.toBeInTheDocument()

    const reveal = screen.getByRole('button', { name: 'Reveal value' })
    await userEvent.click(reveal)

    expect(await screen.findByText('123-45-6789')).toBeInTheDocument()
    expect(screen.queryByText('••••••••')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Hide value' })).toBeInTheDocument()
  })
})
