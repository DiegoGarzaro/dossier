/** Vitest DOM setup: jest-dom matchers + RTL auto-cleanup (G-04). */

import '@testing-library/jest-dom/vitest'

// jsdom doesn't implement matchMedia; several components (e.g. useFlip's
// prefers-reduced-motion check) call it unconditionally on mount.
if (typeof window !== 'undefined' && !window.matchMedia) {
  window.matchMedia = (query: string): MediaQueryList => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  })
}
