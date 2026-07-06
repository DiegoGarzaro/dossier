/** Shared UI primitives styled per docs/Design System.md. */

import { Component, type ButtonHTMLAttributes, type InputHTMLAttributes, type ReactNode } from 'react'

type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger'

const buttonVariants: Record<ButtonVariant, string> = {
  primary: 'bg-accent text-accent-on hover:bg-accent-hover active:bg-accent-active',
  secondary: 'bg-surface text-ink border border-border hover:bg-surface-hover',
  ghost: 'text-muted hover:bg-surface-hover hover:text-ink',
  danger: 'text-danger border border-danger/40 hover:bg-danger/10',
}

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
  size?: 'sm' | 'md'
}

export function Button({ variant = 'primary', size = 'md', className = '', ...rest }: ButtonProps) {
  const sizing = size === 'sm' ? 'h-8 px-3 text-[13px]' : 'h-10 px-4 text-sm'
  return (
    <button
      className={`inline-flex items-center justify-center gap-2 rounded-md font-medium transition-colors disabled:pointer-events-none disabled:opacity-50 ${sizing} ${buttonVariants[variant]} ${className}`}
      {...rest}
    />
  )
}

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string
}

export function Input({ label, id, className = '', ...rest }: InputProps) {
  const input = (
    <input
      id={id}
      className={`h-10 w-full rounded-sm border border-border bg-surface px-3 text-sm text-ink placeholder:text-subtle focus:border-accent ${className}`}
      {...rest}
    />
  )
  if (!label) return input
  return (
    <div className="space-y-1.5">
      <label htmlFor={id} className="label-caps block">
        {label}
      </label>
      {input}
    </div>
  )
}

export function SectionHeading({ title, action }: { title: string; action?: ReactNode }) {
  return (
    <div className="flex items-center justify-between border-b border-border px-4 py-3">
      <h2 className="font-display text-lg font-semibold">{title}</h2>
      {action}
    </div>
  )
}

export function Avatar({
  name,
  photoUrl,
  size = 56,
}: {
  name: string
  photoUrl?: string
  size?: number
}) {
  const initials = name
    .split(/\s+/)
    .filter(Boolean)
    .map((part) => part[0])
    .filter((_, index, parts) => index === 0 || index === parts.length - 1)
    .join('')
    .toUpperCase()
  // shrink-0: flex rows squeeze items below their explicit width when text
  // runs long, which left avatars subtly different sizes across cards.
  if (photoUrl) {
    return (
      <img
        src={photoUrl}
        alt={name}
        width={size}
        height={size}
        className="shrink-0 rounded-full border border-border object-cover"
        style={{ width: size, height: size }}
      />
    )
  }
  return (
    <div
      aria-hidden
      className="flex shrink-0 items-center justify-center rounded-full bg-accent-fill font-display font-semibold text-accent"
      style={{ width: size, height: size, fontSize: size * 0.36 }}
    >
      {initials}
    </div>
  )
}

export function Dialog({
  title,
  children,
  onClose,
}: {
  title: string
  children: ReactNode
  onClose: () => void
}) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ backgroundColor: 'var(--scrim)' }}
      onClick={onClose}
      role="presentation"
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className="w-full max-w-md rounded-lg border border-border bg-surface p-6 shadow-(--shadow-raised)"
        onClick={(event) => event.stopPropagation()}
      >
        <h2 className="mb-4 font-display text-xl font-semibold">{title}</h2>
        {children}
      </div>
    </div>
  )
}

export function Spinner() {
  return (
    <div className="flex justify-center py-16" role="status" aria-label="Loading">
      <div className="h-6 w-6 animate-spin rounded-full border-2 border-border border-t-accent" />
    </div>
  )
}

export function EmptyState({ icon, message, action }: { icon: ReactNode; message: string; action?: ReactNode }) {
  return (
    <div className="flex flex-col items-center gap-3 py-12 text-center">
      <div className="text-subtle">{icon}</div>
      <p className="text-sm text-muted">{message}</p>
      {action}
    </div>
  )
}

interface ErrorBoundaryState {
  error: Error | null
}

export class ErrorBoundary extends Component<{ children: ReactNode }, ErrorBoundaryState> {
  state: ErrorBoundaryState = { error: null }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { error }
  }

  render() {
    if (this.state.error) {
      return (
        <div className="flex min-h-svh flex-col items-center justify-center gap-4 p-8 text-center">
          <h1 className="font-display text-2xl font-semibold text-ink">Something went wrong</h1>
          <p className="max-w-md text-sm text-muted">An unexpected error occurred. Reload the page to continue.</p>
          <Button variant="secondary" onClick={() => window.location.reload()}>
            Reload
          </Button>
        </div>
      )
    }
    return this.props.children
  }
}
