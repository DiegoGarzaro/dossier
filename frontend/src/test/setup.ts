/** Vitest DOM setup: jest-dom matchers + RTL auto-cleanup (G-04). */

import '@testing-library/jest-dom/vitest'

// Node 22+ ships its own experimental `localStorage` global, which shadows
// jsdom's and throws ("getItem is not a function") unless the process was
// started with a valid --localstorage-file. Give the theme helpers a real
// in-memory store instead (G-52).
if (typeof globalThis.localStorage?.getItem !== 'function') {
  const store = new Map<string, string>()
  Object.defineProperty(globalThis, 'localStorage', {
    configurable: true,
    value: {
      getItem: (key: string) => store.get(key) ?? null,
      setItem: (key: string, value: string) => void store.set(key, String(value)),
      removeItem: (key: string) => void store.delete(key),
      clear: () => store.clear(),
      key: (index: number) => [...store.keys()][index] ?? null,
      get length() {
        return store.size
      },
    },
  })
}

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
