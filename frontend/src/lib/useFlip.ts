/** FLIP hook: elements registered by id slide to their new positions when a
 * list reorders (Design System §1: calm motion, 120–200ms ease-out). */

import { useLayoutEffect, useRef } from 'react'

export function useFlip() {
  const nodes = useRef(new Map<number, HTMLElement>())
  const rects = useRef(new Map<number, DOMRect>())

  useLayoutEffect(() => {
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    for (const [id, el] of nodes.current) {
      const prev = rects.current.get(id)
      const next = el.getBoundingClientRect()
      const dy = prev ? prev.top - next.top : 0
      if (dy !== 0 && !reduced) {
        el.animate(
          [{ transform: `translateY(${dy}px)` }, { transform: 'translateY(0)' }],
          { duration: 180, easing: 'ease-out' },
        )
      }
      rects.current.set(id, next)
    }
  })

  return (id: number) => (el: HTMLElement | null) => {
    if (el) {
      nodes.current.set(id, el)
    } else {
      nodes.current.delete(id)
      rects.current.delete(id)
    }
  }
}
