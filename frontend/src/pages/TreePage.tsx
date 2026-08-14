/** Read-only relationship tree: positioned genealogy layout with family buses (Phase 2b, G-32). */

import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, Users } from 'lucide-react'
import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { Avatar, Button, Card, EmptyState, Spinner } from '../components/ui'
import { ApiError, api } from '../lib/api'
import { ROW_GAP, layoutTree, type ChipSize, type TreeLayout } from '../lib/treeLayout'
import type { RelationshipType, TreeOut } from '../lib/types'

/** Stroke dash per link kind — solid family core, dashed/dotted for the rest. */
const DASHES: Record<RelationshipType, string | undefined> = {
  parent: undefined,
  spouse: undefined,
  partner: '10 4',
  sibling: '5 4',
  godparent: '2 2',
  friend: '1 4',
  colleague: '7 2 2 2',
  custom: '2 4',
  child: undefined, // never stored; canonicalized to parent
  godchild: undefined, // never stored; canonicalized to godparent
}

const LEGEND: { kind: RelationshipType; word: string }[] = [
  { kind: 'parent', word: 'Parent · child' },
  { kind: 'spouse', word: 'Spouse' },
  { kind: 'partner', word: 'Partner' },
  { kind: 'sibling', word: 'Sibling' },
  { kind: 'godparent', word: 'Godparent · godchild' },
  { kind: 'friend', word: 'Friend' },
  { kind: 'colleague', word: 'Colleague' },
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

export function TreePage() {
  const { id } = useParams()
  const personId = Number(id)

  const tree = useQuery({
    queryKey: ['tree', personId],
    queryFn: () => api<TreeOut>(`/api/people/${personId}/tree`),
  })

  const scrollRef = useRef<HTMLDivElement>(null)
  const nodeEls = useRef(new Map<number, HTMLElement>())
  const [layout, setLayout] = useState<TreeLayout | null>(null)

  // Two-pass render: chips mount hidden so their natural sizes can be
  // measured, then the pure layout engine assigns absolute positions.
  const compute = useCallback(() => {
    const data = tree.data
    const scroller = scrollRef.current
    if (!data || !scroller) return
    const sizes = new Map<number, ChipSize>()
    nodeEls.current.forEach((el, nodeId) => {
      sizes.set(nodeId, { width: el.offsetWidth, height: el.offsetHeight })
    })
    setLayout(layoutTree(data, sizes, scroller.clientWidth))
  }, [tree.data])

  useLayoutEffect(() => {
    compute()
  }, [compute])

  useEffect(() => {
    window.addEventListener('resize', compute)
    return () => window.removeEventListener('resize', compute)
  }, [compute])

  if (tree.isPending) return <Spinner />
  if (tree.error instanceof ApiError && tree.error.status === 404) {
    return <p className="text-muted">This person no longer exists.</p>
  }
  if (!tree.data) return <Spinner />

  const data = tree.data
  const center = data.nodes.find((node) => node.id === data.center_id)
  const centerFirstName = center?.full_name.split(' ')[0] ?? ''
  // Legend reflects the links actually drawn (soft ties duplicating blood are
  // dropped by the layout), falling back to the raw edge kinds pre-measure.
  const kindsPresent = layout
    ? new Set(layout.lines.map((line) => line.kind))
    : new Set(data.edges.map((edge) => edge.type))

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <Link
            to={`/people/${personId}`}
            className="relative mb-1 inline-flex items-center gap-1.5 text-sm text-muted before:absolute before:-inset-3 before:content-[''] hover:text-ink"
          >
            <ArrowLeft size={14} aria-hidden /> Back to card
          </Link>
          <p className="label-caps">Relationship tree</p>
          <h1 className="font-display text-h1 leading-tight font-semibold text-balance sm:text-display">
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
        <Card>
          <EmptyState
            icon={<Users size={32} aria-hidden />}
            message="No relationships yet. Add one from the card to grow the tree."
            action={
              <Link to={`/people/${personId}`}>
                <Button variant="secondary">Back to card</Button>
              </Link>
            }
          />
        </Card>
      ) : (
        <Card>
          <div ref={scrollRef} className="overflow-x-auto">
            <div
              className="relative"
              style={{ width: layout?.width, height: layout?.height, minWidth: '100%' }}
            >
              {layout?.rows.map((row, index) => (
                <div key={row.generation}>
                  {index > 0 && (
                    <div
                      aria-hidden
                      className="absolute border-t border-border"
                      style={{ top: row.y - ROW_GAP / 2, left: 0, width: layout.width }}
                    />
                  )}
                  <span className="label-caps absolute left-4 w-32" style={{ top: row.y }}>
                    {generationLabel(row.generation)}
                  </span>
                </div>
              ))}
              <svg
                className="pointer-events-none absolute inset-0"
                width={layout?.width ?? 0}
                height={layout?.height ?? 0}
                aria-hidden
              >
                {(layout?.lines ?? []).map((line, index) => (
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
              {(layout?.lines ?? [])
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
              {data.nodes.map((node) => {
                const position = layout?.positions.get(node.id)
                return (
                  <Link
                    key={node.id}
                    to={`/people/${node.id}`}
                    ref={(el) => {
                      if (el) nodeEls.current.set(node.id, el)
                      else nodeEls.current.delete(node.id)
                    }}
                    style={position ? { left: position.x, top: position.y } : undefined}
                    className={`absolute inline-flex items-center gap-2 rounded-full border bg-surface py-1.5 pr-3.5 pl-1.5 text-sm font-medium whitespace-nowrap shadow-card transition-all hover:-translate-y-0.5 hover:shadow-raised ${
                      node.id === data.center_id ? 'border-2 border-seal' : 'border-border'
                    } ${position ? '' : 'invisible'}`}
                    aria-current={node.id === data.center_id ? 'page' : undefined}
                  >
                    <Avatar name={node.full_name} size={28} />
                    <span className="flex flex-col leading-tight">
                      {node.full_name}
                      {node.kinship && node.id !== data.center_id && (
                        <span className="text-[10px] font-normal text-muted">
                          {node.kinship} of {centerFirstName}
                        </span>
                      )}
                    </span>
                  </Link>
                )
              })}
            </div>
          </div>
        </Card>
      )}
    </div>
  )
}
