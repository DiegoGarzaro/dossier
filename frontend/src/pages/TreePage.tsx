/** Read-only relationship tree: generation rows with drawn connectors (Phase 2b). */

import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, Users } from 'lucide-react'
import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { Avatar, Button, EmptyState, Spinner } from '../components/ui'
import { ApiError, api } from '../lib/api'
import type { RelationshipType, TreeEdge, TreeNode, TreeOut } from '../lib/types'

/** Stroke dash per link kind — solid parent/spouse, dashed sibling, dotted custom. */
const DASHES: Record<RelationshipType, string | undefined> = {
  parent: undefined,
  spouse: undefined,
  sibling: '5 4',
  custom: '2 4',
  child: undefined, // never stored; canonicalized to parent
}

const LEGEND: { kind: RelationshipType; word: string }[] = [
  { kind: 'parent', word: 'Parent · child' },
  { kind: 'spouse', word: 'Spouse' },
  { kind: 'sibling', word: 'Sibling' },
  { kind: 'custom', word: 'Custom' },
]

function generationLabel(generation: number): string {
  if (generation === 0) return 'This generation'
  const magnitude = Math.abs(generation)
  if (magnitude === 1) return generation < 0 ? 'Parents' : 'Children'
  const base = generation < 0 ? 'grandparents' : 'grandchildren'
  const word = 'great-'.repeat(magnitude - 2) + base
  return word[0].toUpperCase() + word.slice(1)
}

/** Order a generation row so spouse-linked people sit next to each other. */
function orderRow(nodes: TreeNode[], edges: TreeEdge[]): TreeNode[] {
  const ids = new Set(nodes.map((node) => node.id))
  const parent = new Map<number, number>()
  const find = (id: number): number => {
    let root = id
    while (parent.get(root) !== undefined && parent.get(root) !== root) root = parent.get(root)!
    return root
  }
  for (const edge of edges) {
    if (edge.type !== 'spouse' || !ids.has(edge.source_id) || !ids.has(edge.target_id)) continue
    parent.set(find(edge.source_id), find(edge.target_id))
  }
  const clusters = new Map<number, TreeNode[]>()
  for (const node of [...nodes].sort((a, b) => a.full_name.localeCompare(b.full_name))) {
    const root = find(node.id)
    const cluster = clusters.get(root)
    if (cluster) cluster.push(node)
    else clusters.set(root, [node])
  }
  return [...clusters.values()]
    .sort((a, b) => a[0].full_name.localeCompare(b[0].full_name))
    .flat()
}

interface DrawnLine {
  path: string
  kind: RelationshipType
  label: string | null
  midX: number
  midY: number
}

export function TreePage() {
  const { id } = useParams()
  const personId = Number(id)

  const tree = useQuery({
    queryKey: ['tree', personId],
    queryFn: () => api<TreeOut>(`/api/people/${personId}/tree`),
  })

  const chartRef = useRef<HTMLDivElement>(null)
  const nodeEls = useRef(new Map<number, HTMLElement>())
  const [lines, setLines] = useState<DrawnLine[]>([])
  const [chartSize, setChartSize] = useState({ width: 0, height: 0 })

  const measure = useCallback(() => {
    const chart = chartRef.current
    const data = tree.data
    if (!chart || !data) return
    const base = chart.getBoundingClientRect()
    const rectOf = (nodeId: number) => {
      const el = nodeEls.current.get(nodeId)
      if (!el) return null
      const rect = el.getBoundingClientRect()
      return {
        left: rect.left - base.left,
        top: rect.top - base.top,
        right: rect.right - base.left,
        bottom: rect.bottom - base.top,
        cx: rect.left - base.left + rect.width / 2,
        cy: rect.top - base.top + rect.height / 2,
      }
    }

    const generations = new Map(data.nodes.map((node) => [node.id, node.generation]))
    const drawn: DrawnLine[] = []
    for (const edge of data.edges) {
      const a = rectOf(edge.source_id)
      const b = rectOf(edge.target_id)
      if (!a || !b) continue
      const sameRow = generations.get(edge.source_id) === generations.get(edge.target_id)
      if (!sameRow) {
        // Older side on top (parent rows are canonical: source is the parent).
        const [top, bottom] = a.cy <= b.cy ? [a, b] : [b, a]
        const midY = (top.bottom + bottom.top) / 2
        drawn.push({
          path: `M ${top.cx} ${top.bottom} V ${midY} H ${bottom.cx} V ${bottom.top}`,
          kind: edge.type,
          label: edge.label,
          midX: (top.cx + bottom.cx) / 2,
          midY,
        })
      } else {
        const [left, right] = a.cx <= b.cx ? [a, b] : [b, a]
        const gap = right.left - left.right
        if (gap >= 0 && gap <= 56) {
          // Adjacent peers: a short straight tie between the chips. The label
          // pill (custom links) drops below the chips so it never covers a name.
          const y = (left.cy + right.cy) / 2
          drawn.push({
            path: `M ${left.right} ${y} H ${right.left}`,
            kind: edge.type,
            label: edge.label,
            midX: (left.right + right.left) / 2,
            midY: Math.max(left.bottom, right.bottom) + 10,
          })
        } else {
          // Distant peers: arc below the row so the line doesn't cross chips.
          const dip = Math.max(left.bottom, right.bottom) + 18
          drawn.push({
            path: `M ${left.cx} ${left.bottom} Q ${(left.cx + right.cx) / 2} ${dip} ${right.cx} ${right.bottom}`,
            kind: edge.type,
            label: edge.label,
            midX: (left.cx + right.cx) / 2,
            midY: dip - 6,
          })
        }
      }
    }
    setLines(drawn)
    setChartSize({ width: chart.scrollWidth, height: chart.scrollHeight })
  }, [tree.data])

  useLayoutEffect(() => {
    measure()
  }, [measure])

  useEffect(() => {
    window.addEventListener('resize', measure)
    return () => window.removeEventListener('resize', measure)
  }, [measure])

  if (tree.isPending) return <Spinner />
  if (tree.error instanceof ApiError && tree.error.status === 404) {
    return <p className="text-muted">This person no longer exists.</p>
  }
  if (!tree.data) return <Spinner />

  const data = tree.data
  const center = data.nodes.find((node) => node.id === data.center_id)
  const rows = [...new Set(data.nodes.map((node) => node.generation))]
    .sort((a, b) => a - b)
    .map((generation) => ({
      generation,
      people: orderRow(
        data.nodes.filter((node) => node.generation === generation),
        data.edges,
      ),
    }))
  const kindsPresent = new Set(data.edges.map((edge) => edge.type))

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <Link
            to={`/people/${personId}`}
            className="mb-1 inline-flex items-center gap-1.5 text-sm text-muted hover:text-ink"
          >
            <ArrowLeft size={14} aria-hidden /> Back to card
          </Link>
          <p className="label-caps">Relationship tree</p>
          <h1 className="font-display text-3xl leading-tight font-semibold">
            {center?.full_name}
          </h1>
        </div>
        {kindsPresent.size > 0 && (
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
            {LEGEND.filter((entry) => kindsPresent.has(entry.kind)).map((entry) => (
              <span key={entry.kind} className="inline-flex items-center gap-1.5 text-xs text-muted">
                <svg width="24" height="2" aria-hidden>
                  <line
                    x1="0"
                    y1="1"
                    x2="24"
                    y2="1"
                    stroke="var(--border-strong)"
                    strokeWidth="2"
                    strokeDasharray={DASHES[entry.kind]}
                  />
                </svg>
                {entry.word}
              </span>
            ))}
          </div>
        )}
      </div>

      {data.edges.length === 0 ? (
        <div className="rounded-lg border border-border bg-surface shadow-(--shadow-card)">
          <EmptyState
            icon={<Users size={32} aria-hidden />}
            message="No relationships yet. Add one from the card to grow the tree."
            action={
              <Link to={`/people/${personId}`}>
                <Button variant="secondary">Back to card</Button>
              </Link>
            }
          />
        </div>
      ) : (
        <div className="rounded-lg border border-border bg-surface shadow-(--shadow-card)">
          <div ref={chartRef} className="relative">
            <svg
              className="pointer-events-none absolute inset-0"
              width={chartSize.width}
              height={chartSize.height}
              aria-hidden
            >
              {lines.map((line, index) => (
                <path
                  key={index}
                  d={line.path}
                  fill="none"
                  stroke="var(--border-strong)"
                  strokeWidth="1.5"
                  strokeDasharray={DASHES[line.kind]}
                />
              ))}
            </svg>
            {lines
              .filter((line) => line.kind === 'custom' && line.label)
              .map((line, index) => (
                <span
                  key={index}
                  className="label-caps absolute z-10 -translate-x-1/2 -translate-y-1/2 rounded-full border border-border bg-surface px-2 py-0.5 text-[10px]"
                  style={{ left: line.midX, top: line.midY }}
                >
                  {line.label}
                </span>
              ))}
            {rows.map((row) => (
              <div
                key={row.generation}
                className="flex flex-col border-b border-border last:border-b-0 sm:flex-row"
              >
                <div className="w-36 shrink-0 px-4 pt-4 sm:py-6">
                  <span className="label-caps">{generationLabel(row.generation)}</span>
                </div>
                <div className="flex flex-1 flex-wrap items-center justify-center gap-x-8 gap-y-5 px-4 py-6">
                  {row.people.map((node) => (
                    <Link
                      key={node.id}
                      to={`/people/${node.id}`}
                      ref={(el) => {
                        if (el) nodeEls.current.set(node.id, el)
                        else nodeEls.current.delete(node.id)
                      }}
                      className={`inline-flex items-center gap-2 rounded-full border bg-surface py-1.5 pr-3.5 pl-1.5 text-sm font-medium shadow-(--shadow-card) transition-all hover:-translate-y-0.5 hover:shadow-(--shadow-raised) ${
                        node.id === data.center_id ? 'border-2 border-seal' : 'border-border'
                      }`}
                      aria-current={node.id === data.center_id ? 'page' : undefined}
                    >
                      <Avatar name={node.full_name} size={28} />
                      {node.full_name}
                    </Link>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
