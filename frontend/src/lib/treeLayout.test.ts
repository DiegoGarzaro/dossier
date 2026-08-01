/** Unit tests for the relationship-tree layout engine (G-32). */

import { describe, expect, it } from 'vitest'

import type { TreeEdge, TreeNode, TreeOut } from './types'
import { COUPLE_GAP, layoutTree } from './treeLayout'

const CHIP = { width: 100, height: 40 }

function node(id: number, generation: number, name?: string): TreeNode {
  return { id, full_name: name ?? `Person ${String.fromCharCode(64 + id)}`, generation, kinship: null }
}

function edge(source: number, target: number, type: TreeEdge['type'], label: string | null = null): TreeEdge {
  return { source_id: source, target_id: target, type, label }
}

function layout(data: TreeOut) {
  const sizes = new Map(data.nodes.map((n) => [n.id, CHIP]))
  return layoutTree(data, sizes, 0)
}

describe('layoutTree', () => {
  it('seats a couple adjacent with the couple gap', () => {
    const result = layout({
      center_id: 1,
      nodes: [node(1, 0), node(2, 0)],
      edges: [edge(1, 2, 'spouse')],
    })
    const [a, b] = [result.positions.get(1)!, result.positions.get(2)!].sort((p, q) => p.x - q.x)
    expect(b.x - (a.x + CHIP.width)).toBe(COUPLE_GAP)
    expect(a.y).toBe(b.y)
  })

  it('centers a parent couple over their children', () => {
    const result = layout({
      center_id: 3,
      nodes: [node(1, -1), node(2, -1), node(3, 0), node(4, 0)],
      edges: [
        edge(1, 2, 'spouse'),
        edge(1, 3, 'parent'),
        edge(2, 3, 'parent'),
        edge(1, 4, 'parent'),
        edge(2, 4, 'parent'),
      ],
    })
    const center = (id: number) => result.positions.get(id)!.x + CHIP.width / 2
    const parentsMid = (center(1) + center(2)) / 2
    const childrenMid = (center(3) + center(4)) / 2
    expect(Math.abs(parentsMid - childrenMid)).toBeLessThan(1)
  })

  it('draws one family bus and suppresses the sibling tie for shared parents', () => {
    const result = layout({
      center_id: 3,
      nodes: [node(1, -1), node(2, -1), node(3, 0), node(4, 0)],
      edges: [
        edge(1, 2, 'spouse'),
        edge(1, 3, 'parent'),
        edge(2, 3, 'parent'),
        edge(1, 4, 'parent'),
        edge(2, 4, 'parent'),
        edge(3, 4, 'sibling'),
      ],
    })
    expect(result.lines.filter((line) => line.kind === 'parent')).toHaveLength(1)
    expect(result.lines.filter((line) => line.kind === 'sibling')).toHaveLength(0)
    expect(result.lines.filter((line) => line.kind === 'spouse')).toHaveLength(1)
  })

  it('keeps a sibling tie when no parent is shared', () => {
    const result = layout({
      center_id: 1,
      nodes: [node(1, 0), node(2, 0)],
      edges: [edge(1, 2, 'sibling')],
    })
    expect(result.lines.filter((line) => line.kind === 'sibling')).toHaveLength(1)
  })

  it('never overlaps chips within a row', () => {
    const result = layout({
      center_id: 5,
      nodes: [node(1, -1), node(2, -1), node(3, -1), node(4, -1), node(5, 0), node(6, 0)],
      edges: [
        edge(1, 2, 'spouse'),
        edge(3, 4, 'spouse'),
        edge(2, 5, 'parent'),
        edge(3, 5, 'parent'),
        edge(5, 6, 'sibling'),
      ],
    })
    for (const generation of [-1, 0]) {
      const xs = [1, 2, 3, 4, 5, 6]
        .filter((id) => result.positions.has(id))
        .map((id) => ({ id, x: result.positions.get(id)!.x }))
        .filter(({ id }) => (generation === -1 ? id <= 4 : id >= 5))
        .map(({ x }) => x)
        .sort((a, b) => a - b)
      for (let i = 1; i < xs.length; i++) expect(xs[i] - xs[i - 1]).toBeGreaterThanOrEqual(CHIP.width)
    }
  })

  it('gives godparent links their own dotted rail between rows', () => {
    const result = layout({
      center_id: 2,
      nodes: [node(1, -1), node(2, 0)],
      edges: [edge(1, 2, 'godparent')],
    })
    expect(result.lines.filter((line) => line.kind === 'godparent')).toHaveLength(1)
  })

  it('drops a godparent link when the pair is already blood-connected', () => {
    // Grandpa is both the kid's grandfather (via dad) and godfather.
    const result = layout({
      center_id: 3,
      nodes: [node(1, -2), node(2, -1), node(3, 0)],
      edges: [
        edge(1, 2, 'parent'), // grandpa -> dad
        edge(2, 3, 'parent'), // dad -> kid
        edge(1, 3, 'godparent'), // grandpa -> kid (redundant with blood)
      ],
    })
    expect(result.lines.filter((line) => line.kind === 'godparent')).toHaveLength(0)
    expect(result.lines.filter((line) => line.kind === 'parent')).toHaveLength(2)
  })

  it('keeps a godparent link when there is no blood connection', () => {
    const result = layout({
      center_id: 2,
      nodes: [node(1, -1), node(2, 0)],
      edges: [edge(1, 2, 'godparent')],
    })
    expect(result.lines.filter((line) => line.kind === 'godparent')).toHaveLength(1)
  })

  it('staggers rails so two families in one channel never share a y', () => {
    const result = layout({
      center_id: 5,
      nodes: [node(1, -1), node(2, -1), node(3, -1), node(4, -1), node(5, 0), node(6, 0)],
      edges: [
        edge(1, 2, 'spouse'),
        edge(3, 4, 'spouse'),
        edge(1, 5, 'parent'),
        edge(2, 5, 'parent'),
        edge(3, 6, 'parent'),
        edge(4, 6, 'parent'),
      ],
    })
    const rails = result.lines.filter((line) => line.kind === 'parent')
    expect(rails).toHaveLength(2)
    expect(rails[0].midY).not.toBe(rails[1].midY)
  })
})
