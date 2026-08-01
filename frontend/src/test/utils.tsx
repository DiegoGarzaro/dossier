/** Shared component-test render helper: wraps a tree with the providers real
 * pages depend on (TanStack Query + router) so tests don't repeat the setup (G-04). */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render } from '@testing-library/react'
import type { ReactElement, ReactNode } from 'react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'

/** A fresh QueryClient per test: no retries/caching bleed between tests. */
export function createTestQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false, staleTime: 0 },
      mutations: { retry: false },
    },
  })
}

interface RenderWithProvidersOptions {
  /** Current router location, e.g. "/people/1". Defaults to "/". */
  route?: string
  /** Route pattern to match, e.g. "/people/:id", so `useParams` resolves. */
  path?: string
  queryClient?: QueryClient
}

/** Renders `ui` inside a QueryClientProvider and a MemoryRouter.
 *
 * Args:
 *   ui: The element under test.
 *   options: Optional route/path (for components using `useParams`/`useNavigate`)
 *     and a pre-built QueryClient (defaults to a fresh no-retry client).
 *
 * Returns:
 *   The Testing Library render result, plus the QueryClient used (so a test
 *   can inspect cache state if needed).
 */
export function renderWithProviders(
  ui: ReactElement,
  { route = '/', path, queryClient = createTestQueryClient() }: RenderWithProvidersOptions = {},
) {
  function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={[route]}>
          {path ? (
            <Routes>
              <Route path={path} element={children} />
            </Routes>
          ) : (
            children
          )}
        </MemoryRouter>
      </QueryClientProvider>
    )
  }
  return { queryClient, ...render(ui, { wrapper: Wrapper }) }
}
