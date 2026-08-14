/** Routes with an auth gate: uninitialized → /setup, unauthenticated → /login. */

import { useQuery } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { Navigate, Outlet, type RouteObject, createBrowserRouter } from 'react-router-dom'

import { Spinner } from './components/ui'
import { TopBar } from './components/TopBar'
import { api } from './lib/api'
import type { AuthStatus } from './lib/types'
import { FirstRun } from './pages/FirstRun'
import { Login } from './pages/Login'
import { PeopleIndex } from './pages/PeopleIndex'
import { PersonPage } from './pages/PersonPage'
import { SettingsPage } from './pages/SettingsPage'
import { TreePage } from './pages/TreePage'

export function useAuthStatus() {
  return useQuery({
    queryKey: ['auth'],
    queryFn: () => api<AuthStatus>('/api/auth/status'),
  })
}

function Gate({ children }: { children: ReactNode }) {
  const { data, isPending } = useAuthStatus()
  if (isPending) return <Spinner />
  if (!data?.initialized) return <Navigate to="/setup" replace />
  if (!data.authenticated) return <Navigate to="/login" replace />
  return <>{children}</>
}

function AppLayout() {
  return (
    <Gate>
      <TopBar />
      <main className="mx-auto max-w-5xl px-4 py-8">
        <Outlet />
      </main>
    </Gate>
  )
}

/** The route table, exported so tests can mount it in a memory router. */
export const routes: RouteObject[] = [
  { path: '/login', element: <Login /> },
  { path: '/setup', element: <FirstRun /> },
  {
    element: <AppLayout />,
    children: [
      { path: '/', element: <PeopleIndex /> },
      { path: '/people/:id', element: <PersonPage /> },
      { path: '/people/:id/tree', element: <TreePage /> },
      { path: '/settings', element: <SettingsPage /> },
    ],
  },
]

export const router = createBrowserRouter(routes)
