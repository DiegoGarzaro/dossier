/** End-to-end-ish routing tests: the auth gate must hand a freshly logged-in
 * user straight to the app, without a manual page refresh (G-48). */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { RouterProvider, createMemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { AuthStatus } from './lib/types'
import { routes } from './router'

const { mockApi } = vi.hoisted(() => ({ mockApi: vi.fn() }))

vi.mock('./lib/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('./lib/api')>()
  return { ...actual, api: mockApi }
})

/** Stands in for the server: `/api/auth/status` reflects whatever the last
 * `/api/auth/login` did, exactly like a real session cookie would. */
function mockServer(): { loggedIn: () => boolean } {
  let loggedIn = false
  mockApi.mockImplementation(async (path: string, options: { method?: string } = {}) => {
    const method = options.method ?? 'GET'
    if (path === '/api/auth/status') {
      return {
        initialized: true,
        authenticated: loggedIn,
        username: loggedIn ? 'diego' : null,
      } satisfies AuthStatus
    }
    if (path === '/api/auth/login' && method === 'POST') {
      loggedIn = true
      return { initialized: true, authenticated: true, username: 'diego' } satisfies AuthStatus
    }
    if (path === '/api/auth/logout' && method === 'POST') {
      loggedIn = false
      return undefined
    }
    if (path.startsWith('/api/people')) return []
    if (path === '/api/tags') return []
    throw new Error(`Unhandled request: ${method} ${path}`)
  })
  return { loggedIn: () => loggedIn }
}

function renderApp(route: string) {
  const queryClient = new QueryClient({
    // Mirror main.tsx: a non-zero staleTime is what production actually runs.
    defaultOptions: { queries: { retry: false, staleTime: 10_000 }, mutations: { retry: false } },
  })
  const router = createMemoryRouter(routes, { initialEntries: [route] })
  return {
    queryClient,
    ...render(
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>,
    ),
  }
}

beforeEach(() => {
  mockApi.mockReset()
})

describe('auth gate', () => {
  it('lands on the people index right after signing in, with no refresh', async () => {
    mockServer()
    const user = userEvent.setup()
    renderApp('/login')

    await user.type(await screen.findByLabelText('Username'), 'diego')
    await user.type(screen.getByLabelText('Password'), 'correct-horse-battery')
    await user.click(screen.getByRole('button', { name: 'Sign in' }))

    expect(await screen.findByRole('heading', { name: 'People' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Sign in' })).not.toBeInTheDocument()
  })

  it('sends an unauthenticated visitor to the login screen', async () => {
    mockServer()
    renderApp('/')

    expect(await screen.findByRole('button', { name: 'Sign in' })).toBeInTheDocument()
  })

  // G-48: the login response is itself the authoritative AuthStatus. Re-deriving
  // it from a second `GET /api/auth/status` round-trip meant one flaky refetch
  // dropped the user back onto a freshly-mounted (= cleared) login form, with
  // the session cookie already set and no error shown — "only a refresh logs me
  // in". The sign-in must not depend on that second request succeeding.
  it('stays signed in even when the auth-status refetch fails right after login', async () => {
    let loggedIn = false
    mockApi.mockImplementation(async (path: string, options: { method?: string } = {}) => {
      const method = options.method ?? 'GET'
      if (path === '/api/auth/status') {
        if (loggedIn) throw new Error('network blip')
        return { initialized: true, authenticated: false, username: null } satisfies AuthStatus
      }
      if (path === '/api/auth/login' && method === 'POST') {
        loggedIn = true
        return { initialized: true, authenticated: true, username: 'diego' } satisfies AuthStatus
      }
      if (path.startsWith('/api/people')) return []
      if (path === '/api/tags') return []
      throw new Error(`Unhandled request: ${method} ${path}`)
    })
    const user = userEvent.setup()
    renderApp('/login')

    await user.type(await screen.findByLabelText('Username'), 'diego')
    await user.type(screen.getByLabelText('Password'), 'correct-horse-battery')
    await user.click(screen.getByRole('button', { name: 'Sign in' }))

    expect(await screen.findByRole('heading', { name: 'People' })).toBeInTheDocument()
  })

  it('drops the previous session out of the cache on logout', async () => {
    mockServer()
    const user = userEvent.setup()
    const { queryClient } = renderApp('/login')

    await user.type(await screen.findByLabelText('Username'), 'diego')
    await user.type(screen.getByLabelText('Password'), 'correct-horse-battery')
    await user.click(screen.getByRole('button', { name: 'Sign in' }))
    await screen.findByRole('heading', { name: 'People' })

    await user.click(screen.getByRole('button', { name: 'Log out' }))
    await screen.findByRole('button', { name: 'Sign in' })

    // Nothing about the person the previous user was looking at may survive.
    const keys = queryClient.getQueryCache().getAll().map((query) => query.queryKey[0])
    expect(keys).not.toContain('people')
    expect(keys).not.toContain('person')
  })
})
