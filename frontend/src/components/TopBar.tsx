/** App-wide top bar: wordmark, theme toggle, settings, logout. */

import { useMutation, useQueryClient } from '@tanstack/react-query'
import { FolderLock, LogOut, Moon, Settings, Sun } from 'lucide-react'
import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { api } from '../lib/api'
import { currentTheme, toggleTheme } from '../theme/theme'
import { Button } from './ui'

export function TopBar() {
  const [theme, setTheme] = useState(currentTheme())
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const logout = useMutation({
    mutationFn: () => api<void>('/api/auth/logout', { method: 'POST' }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['auth'] })
      navigate('/login')
    },
  })

  return (
    <header className="border-b border-border bg-surface">
      <div className="mx-auto flex h-14 max-w-5xl items-center gap-2 px-4">
        <Link to="/" className="flex items-center gap-2 font-display text-lg font-semibold">
          <FolderLock size={20} className="text-accent" aria-hidden />
          Dossier
        </Link>
        <div className="flex-1" />
        <Button
          variant="ghost"
          size="sm"
          aria-label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
          onClick={() => setTheme(toggleTheme())}
        >
          {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
        </Button>
        <Link to="/settings" aria-label="Settings">
          <Button variant="ghost" size="sm">
            <Settings size={18} />
          </Button>
        </Link>
        <Button variant="ghost" size="sm" aria-label="Log out" onClick={() => logout.mutate()}>
          <LogOut size={18} />
        </Button>
      </div>
    </header>
  )
}
