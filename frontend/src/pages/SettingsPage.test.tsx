/** Component tests for Settings: tags admin, encrypted backup/restore, data
 * summary (G-04). */

import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { ApiError } from '../lib/api'
import type { SystemSummary, Tag } from '../lib/types'
import { renderWithProviders } from '../test/utils'
import { SettingsPage } from './SettingsPage'

const { mockApi, mockApiBlob } = vi.hoisted(() => ({ mockApi: vi.fn(), mockApiBlob: vi.fn() }))

// Mock the network at the api.ts boundary (never stub global fetch); keep the
// real ApiError class so `error instanceof ApiError` checks in components work.
vi.mock('../lib/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../lib/api')>()
  return { ...actual, api: mockApi, apiBlob: mockApiBlob }
})

const familyTag: Tag = { id: 10, name: 'Family', person_count: 3 }
const workTag: Tag = { id: 11, name: 'Work', person_count: 0 }

function summary(overrides: Partial<SystemSummary> = {}): SystemSummary {
  return {
    people: 3,
    fields: 10,
    documents: 2,
    relationships: 1,
    tags: 2,
    uploads_bytes: 1024,
    database_bytes: 2048,
    last_backup_at: null,
    ...overrides,
  }
}

async function renderSettingsPage() {
  const result = renderWithProviders(<SettingsPage />)
  await screen.findByRole('heading', { name: 'Settings' })
  return result
}

beforeEach(() => {
  mockApi.mockReset()
  mockApiBlob.mockReset()
})

describe('SettingsPage — tags admin', () => {
  it('lists each tag with its person_count and shows an empty state when there are none', async () => {
    mockApi.mockImplementation(async (path: string) => {
      if (path === '/api/tags') return []
      if (path === '/api/system/summary') return summary()
      throw new Error(`Unhandled request: ${path}`)
    })

    await renderSettingsPage()

    expect(await screen.findByText(/No tags yet/)).toBeInTheDocument()
  })

  it('renames a tag via the pencil → input → save flow, calling PATCH /api/tags/{id}', async () => {
    mockApi.mockImplementation(async (path: string, options: { method?: string } = {}) => {
      const method = options.method ?? 'GET'
      if (path === '/api/tags' && method === 'GET') return [familyTag]
      if (path === '/api/system/summary' && method === 'GET') return summary()
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
      if (path === '/api/system/summary' && method === 'GET') return summary()
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
      if (path === '/api/system/summary' && method === 'GET') return summary()
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

describe('SettingsPage — encrypted backup', () => {
  it('keeps the backup button disabled until both passphrases match and meet the length minimum', async () => {
    mockApi.mockImplementation(async (path: string) => {
      if (path === '/api/tags') return []
      if (path === '/api/system/summary') return summary()
      throw new Error(`Unhandled request: ${path}`)
    })

    await renderSettingsPage()

    const button = screen.getByRole('button', { name: 'Create encrypted backup' })
    const passphraseInput = screen.getByLabelText('Passphrase (minimum 12 characters)')
    const confirmInput = screen.getByLabelText('Confirm passphrase')
    expect(button).toBeDisabled()

    // Too short, even though it matches.
    await userEvent.type(passphraseInput, 'short')
    await userEvent.type(confirmInput, 'short')
    expect(button).toBeDisabled()

    // Long enough, but mismatched.
    await userEvent.clear(passphraseInput)
    await userEvent.clear(confirmInput)
    await userEvent.type(passphraseInput, 'long-enough-passphrase')
    await userEvent.type(confirmInput, 'a-different-passphrase')
    expect(button).toBeDisabled()

    // Long enough and matching.
    await userEvent.clear(confirmInput)
    await userEvent.type(confirmInput, 'long-enough-passphrase')
    expect(button).toBeEnabled()
  })

  it('submits the passphrase to the backup endpoint and triggers a file download', async () => {
    const blob = new Blob(['encrypted-bytes'], { type: 'application/octet-stream' })
    mockApi.mockImplementation(async (path: string) => {
      if (path === '/api/tags') return []
      if (path === '/api/system/summary') return summary()
      throw new Error(`Unhandled request: ${path}`)
    })
    mockApiBlob.mockImplementation(async (path: string) => {
      if (path === '/api/backup') return blob
      throw new Error(`Unhandled request: ${path}`)
    })

    // jsdom doesn't implement the object-URL/file-download APIs; stub them
    // (a fallback assignment first, since the methods may not exist at all).
    if (!URL.createObjectURL) URL.createObjectURL = () => ''
    if (!URL.revokeObjectURL) URL.revokeObjectURL = () => {}
    const createObjectURLSpy = vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:mock-url')
    const revokeObjectURLSpy = vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {})
    const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})

    try {
      await renderSettingsPage()

      await userEvent.type(
        screen.getByLabelText('Passphrase (minimum 12 characters)'),
        'correct-horse-battery',
      )
      await userEvent.type(screen.getByLabelText('Confirm passphrase'), 'correct-horse-battery')
      await userEvent.click(screen.getByRole('button', { name: 'Create encrypted backup' }))

      await waitFor(() =>
        expect(mockApiBlob).toHaveBeenCalledWith('/api/backup', {
          body: { passphrase: 'correct-horse-battery' },
        }),
      )
      expect(createObjectURLSpy).toHaveBeenCalledWith(blob)
      expect(clickSpy).toHaveBeenCalled()
      await waitFor(() => expect(revokeObjectURLSpy).toHaveBeenCalledWith('blob:mock-url'))
    } finally {
      createObjectURLSpy.mockRestore()
      revokeObjectURLSpy.mockRestore()
      clickSpy.mockRestore()
    }
  })
})

describe('SettingsPage — restore from backup', () => {
  it('shows the server message inline and keeps the dialog + file selection on a wrong passphrase', async () => {
    mockApi.mockImplementation(async (path: string, options: { method?: string } = {}) => {
      const method = options.method ?? 'GET'
      if (path === '/api/tags' && method === 'GET') return []
      if (path === '/api/system/summary' && method === 'GET') return summary()
      if (path === '/api/restore' && method === 'POST') {
        throw new ApiError(400, 'Wrong passphrase, or this backup file is damaged')
      }
      throw new Error(`Unhandled request: ${method} ${path}`)
    })

    await renderSettingsPage()

    const file = new File(['encrypted-bytes'], 'backup.dossier', {
      type: 'application/octet-stream',
    })
    await userEvent.upload(screen.getByLabelText('Backup file (.dossier)'), file)
    await userEvent.type(screen.getByLabelText('Passphrase'), 'a-wrong-passphrase')
    await userEvent.click(screen.getByRole('button', { name: 'Restore' }))

    const dialog = await screen.findByRole('dialog', { name: 'Restore from backup' })
    await userEvent.click(within(dialog).getByRole('button', { name: 'Restore' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Wrong passphrase, or this backup file is damaged',
    )
    // Must stay put: dialog open, file selection intact, so the user can retry.
    expect(screen.getByRole('dialog', { name: 'Restore from backup' })).toBeInTheDocument()
    // Appears both in the dialog's confirmation text and the file-selection
    // badge behind it, so assert presence rather than a single match.
    expect(screen.getAllByText('backup.dossier').length).toBeGreaterThan(0)
  })
})

describe('SettingsPage — data summary', () => {
  it('renders the counts and sizes, and the "No backup taken yet" empty state', async () => {
    mockApi.mockImplementation(async (path: string) => {
      if (path === '/api/tags') return []
      if (path === '/api/system/summary') {
        return summary({
          people: 12,
          fields: 84,
          documents: 5,
          relationships: 9,
          tags: 3,
          last_backup_at: null,
        })
      }
      throw new Error(`Unhandled request: ${path}`)
    })

    await renderSettingsPage()

    expect(await screen.findByText('12')).toBeInTheDocument()
    expect(screen.getByText('84')).toBeInTheDocument()
    expect(screen.getByText('5')).toBeInTheDocument()
    expect(screen.getByText('9')).toBeInTheDocument()
    expect(screen.getByText('No backup taken yet')).toBeInTheDocument()
  })
})
