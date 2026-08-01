/** Component tests for the Settings "Tags" admin block: rename, delete, 409 handling (G-04). */

import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { ApiError } from '../lib/api'
import type { Tag } from '../lib/types'
import { renderWithProviders } from '../test/utils'
import { SettingsPage } from './SettingsPage'

const { mockApi } = vi.hoisted(() => ({ mockApi: vi.fn() }))

// Mock the network at the api.ts boundary (never stub global fetch); keep the
// real ApiError class so `error instanceof ApiError` checks in components work.
vi.mock('../lib/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../lib/api')>()
  return { ...actual, api: mockApi }
})

const familyTag: Tag = { id: 10, name: 'Family', person_count: 3 }
const workTag: Tag = { id: 11, name: 'Work', person_count: 0 }

async function renderSettingsPage() {
  const result = renderWithProviders(<SettingsPage />)
  await screen.findByRole('heading', { name: 'Settings' })
  return result
}

beforeEach(() => {
  mockApi.mockReset()
})

describe('SettingsPage — tags admin', () => {
  it('lists each tag with its person_count and shows an empty state when there are none', async () => {
    mockApi.mockImplementation(async (path: string) => {
      if (path === '/api/tags') return []
      throw new Error(`Unhandled request: ${path}`)
    })

    await renderSettingsPage()

    expect(await screen.findByText(/No tags yet/)).toBeInTheDocument()
  })

  it('renames a tag via the pencil → input → save flow, calling PATCH /api/tags/{id}', async () => {
    mockApi.mockImplementation(async (path: string, options: { method?: string } = {}) => {
      const method = options.method ?? 'GET'
      if (path === '/api/tags' && method === 'GET') return [familyTag]
      if (path === '/api/tags/10' && method === 'PATCH') {
        return { ...familyTag, name: 'Relatives' }
      }
      throw new Error(`Unhandled request: ${method} ${path}`)
    })

    await renderSettingsPage()

    expect(await screen.findByText('Family')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Rename Family' }))

    const input = screen.getByRole('textbox', { name: 'Tag name' })
    await userEvent.clear(input)
    await userEvent.type(input, 'Relatives')
    await userEvent.click(screen.getByRole('button', { name: 'Save tag name' }))

    await waitFor(() =>
      expect(mockApi).toHaveBeenCalledWith('/api/tags/10', {
        method: 'PATCH',
        body: { name: 'Relatives' },
      }),
    )
  })

  it('surfaces a 409 rename collision message inline instead of failing silently', async () => {
    mockApi.mockImplementation(async (path: string, options: { method?: string } = {}) => {
      const method = options.method ?? 'GET'
      if (path === '/api/tags' && method === 'GET') return [familyTag, workTag]
      if (path === '/api/tags/10' && method === 'PATCH') {
        throw new ApiError(409, 'A tag named "Work" already exists.')
      }
      throw new Error(`Unhandled request: ${method} ${path}`)
    })

    await renderSettingsPage()

    await screen.findByText('Family')
    await userEvent.click(screen.getByRole('button', { name: 'Rename Family' }))

    const input = screen.getByRole('textbox', { name: 'Tag name' })
    await userEvent.clear(input)
    await userEvent.type(input, 'Work')
    await userEvent.click(screen.getByRole('button', { name: 'Save tag name' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'A tag named "Work" already exists.',
    )
    // The row must stay in edit mode rather than silently discarding the attempt.
    expect(screen.getByRole('textbox', { name: 'Tag name' })).toBeInTheDocument()
  })

  it('deletes a tag after confirmation, calling DELETE /api/tags/{id}', async () => {
    mockApi.mockImplementation(async (path: string, options: { method?: string } = {}) => {
      const method = options.method ?? 'GET'
      if (path === '/api/tags' && method === 'GET') return [familyTag]
      if (path === '/api/tags/10' && method === 'DELETE') return undefined
      throw new Error(`Unhandled request: ${method} ${path}`)
    })

    await renderSettingsPage()

    await screen.findByText('Family')
    await userEvent.click(screen.getByRole('button', { name: 'Delete Family' }))

    const dialog = await screen.findByRole('dialog', { name: 'Delete tag?' })
    expect(dialog).toHaveTextContent('3')
    expect(dialog).toHaveTextContent('does not delete any person')

    await userEvent.click(within(dialog).getByRole('button', { name: 'Delete' }))

    await waitFor(() => expect(mockApi).toHaveBeenCalledWith('/api/tags/10', { method: 'DELETE' }))
  })
})
