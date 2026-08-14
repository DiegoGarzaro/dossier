/** App-wide top bar: wordmark, theme toggle, settings, logout. */

import { useMutation, useQueryClient } from '@tanstack/react-query'
import { FolderLock, LogOut, Moon, Settings, Sun } from 'lucide-react'
import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { api } from '../lib/api'
import type { AuthStatus } from '../lib/types'
import { currentTheme, toggleTheme } from '../theme/theme'
import { IconButton } from './ui'

export function TopBar() {
  const [theme, setTheme] = useState(currentTheme())
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const logout = useMutation({
    mutationFn: () => api<void>('/api/auth/logout', { method: 'POST' }),
    onSuccess: () => {
      // Drop every cached record first — people, tags and documents from the
      // session that just ended must not linger in memory for the next one
      // (G-50) — then state the known auth result so the gate doesn't have to
      // ask the server what it already told us (G-48).
      queryClient.clear()
      queryClient.setQueryData<AuthStatus>(['auth'], {
        initialized: true,
        authenticated: false,
        username: null,
      })
      navigate('/login', { replace: true })
    },
  })

  return (
    <header className="sticky top-0 z-40 border-b border-border bg-surface/85 backdrop-blur-sm">
      <div className="mx-auto flex h-14 max-w-5xl items-center gap-1 px-2 sm:gap-2 sm:px-4">
        <Link
          to="/"
          className="flex min-w-0 items-center gap-2.5 truncate font-display text-h3 font-semibold"
        >
          <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-accent-fill text-accent">
            <FolderLock size={16} aria-hidden />
          </span>
          <span className="truncate">Dossier</span>
        </Link>
        <div className="flex-1" />
        <IconButton
          label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
          className="text-muted hover:bg-surface-hover hover:text-ink"
          onClick={() => setTheme(toggleTheme())}
        >
          {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
        </IconButton>
        <Link to="/settings">
          <IconButton label="Settings" className="text-muted hover:bg-surface-hover hover:text-ink">
            <Settings size={18} />
          </IconButton>
        </Link>
        <IconButton
          label="Log out"
          className="text-muted hover:bg-surface-hover hover:text-ink"
          onClick={() => logout.mutate()}
        >
          <LogOut size={18} />
        </IconButton>
      </div>
    </header>
  )
}
