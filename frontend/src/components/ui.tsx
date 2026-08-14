/** Shared UI primitives styled per docs/Design System.md. */

import {
  Component,
  type ButtonHTMLAttributes,
  type HTMLAttributes,
  type InputHTMLAttributes,
  type ReactNode,
  useEffect,
} from 'react'

type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger'

const buttonVariants: Record<ButtonVariant, string> = {
  primary:
    'bg-accent text-accent-on shadow-sm hover:bg-accent-hover active:bg-accent-active active:shadow-none',
  secondary: 'bg-surface text-ink border border-border hover:border-border-strong hover:bg-surface-hover',
  ghost: 'text-muted hover:bg-surface-hover hover:text-ink',
  danger: 'text-danger border border-danger/40 hover:bg-danger/10',
}

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
  size?: 'sm' | 'md'
}

// Touch target min 44px (Design System §5.1); desktop keeps the tighter
// sm/md heights since a mouse pointer doesn't need the extra hit area.
export function Button({ variant = 'primary', size = 'md', className = '', ...rest }: ButtonProps) {
  const sizing = size === 'sm' ? 'h-11 px-3 text-[13px] sm:h-8' : 'h-11 px-4 text-sm sm:h-10'
  return (
    <button
      className={`inline-flex items-center justify-center gap-2 rounded-md font-medium transition-all disabled:pointer-events-none disabled:opacity-50 ${sizing} ${buttonVariants[variant]} ${className}`}
      {...rest}
    />
  )
}

interface IconButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  label: string
}

/** Icon-only control sized for a thumb (44px) on mobile, mouse-density (32px)
 * on desktop. Callers supply color/hover classes via `className` — this only
 * standardizes shape, size and the required `aria-label`. */
export function IconButton({ label, className = '', ...rest }: IconButtonProps) {
  return (
    <button
      type="button"
      aria-label={label}
      className={`inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-full transition-colors disabled:pointer-events-none disabled:opacity-50 sm:h-8 sm:w-8 ${className}`}
      {...rest}
    />
  )
}

/** The product's surface: a warm panel with a hairline border and low paper
 * shadow (§4). Padding and overflow stay with the caller. */
export function Card({ className = '', ...rest }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={`rounded-lg border border-border bg-surface shadow-card ${className}`}
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
      className={`h-10 w-full rounded-sm border border-border bg-surface px-3 text-sm text-ink transition-colors placeholder:text-subtle hover:border-border-strong focus:border-accent ${className}`}
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

/** Section bar on the ID-card: serif h2 + optional label-style count, action
 * right-aligned (§5.3). */
export function SectionHeading({
  title,
  count,
  action,
}: {
  title: string
  count?: number
  action?: ReactNode
}) {
  return (
    <div className="flex items-center justify-between gap-3 border-b border-border px-4 py-3 sm:px-6">
      <h2 className="flex min-w-0 items-baseline gap-2 font-display text-h2 font-semibold">
        <span className="truncate">{title}</span>
        {count !== undefined && count > 0 && <span className="label-caps shrink-0">{count}</span>}
      </h2>
      {action}
    </div>
  )
}

/** Letterhead section marker (person record): a small-caps label with an
 * optional mono count, a hairline rule filling the row, and the section
 * action at the right — the "form section" cue without any box chrome. */
export function SectionRule({
  title,
  count,
  action,
}: {
  title: string
  count?: number
  action?: ReactNode
}) {
  return (
    <div className="flex items-center gap-3">
      <h2 className="label-caps flex shrink-0 items-baseline gap-2">
        {title}
        {count !== undefined && count > 0 && (
          <span className="font-mono text-[11px] font-medium tracking-normal text-subtle normal-case">
            {count}
          </span>
        )}
      </h2>
      <span aria-hidden className="h-px min-w-8 flex-1 bg-border" />
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
  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [onClose])

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center sm:items-center sm:p-4"
      style={{ backgroundColor: 'var(--scrim)' }}
      onClick={onClose}
      role="presentation"
    >
      {/* Mobile: edge-to-edge sheet anchored to the bottom, scrollable if the
          form is tall. Desktop: the original centered card. */}
      <div
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className="max-h-[85vh] w-full overflow-y-auto rounded-t-lg border border-border bg-surface p-4 pb-6 shadow-raised sm:max-w-md sm:rounded-lg sm:p-6"
        onClick={(event) => event.stopPropagation()}
      >
        {/* Sheet grip — the mobile affordance that this panel drags down. */}
        <div aria-hidden className="mx-auto mb-3 h-1 w-10 rounded-full bg-border sm:hidden" />
        <h2 className="mb-4 font-display text-h2 font-semibold">{title}</h2>
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

export function EmptyState({
  icon,
  message,
  action,
}: {
  icon: ReactNode
  message: string
  action?: ReactNode
}) {
  return (
    <div className="flex flex-col items-center gap-3 py-14 text-center">
      <div className="flex h-14 w-14 items-center justify-center rounded-full border border-border bg-surface-subtle text-subtle">
        {icon}
      </div>
      <p className="max-w-64 text-sm text-muted">{message}</p>
      {action && <div className="mt-1">{action}</div>}
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
        <div className="flex min-h-svh flex-col items-center justify-center p-8 text-center">
          <Card className="flex max-w-md flex-col items-center gap-4 p-8">
            <h1 className="font-display text-h1 font-semibold text-ink">Something went wrong</h1>
            <p className="text-sm text-muted">
              An unexpected error occurred. Reload the page to continue.
            </p>
            <Button variant="secondary" onClick={() => window.location.reload()}>
              Reload
            </Button>
          </Card>
        </div>
      )
    }
    return this.props.children
  }
}
