/** Pure layout engine for the relationship tree page (G-32).
 *
 * Turns the tree payload plus measured chip sizes into absolute chip
 * positions and SVG connector paths. The layout follows genealogy-chart
 * conventions: spouse/partner couples sit adjacent as one unit, each row is
 * ordered with barycenter sweeps to reduce line crossings, parents are
 * centered above their children, and every family gets a single "bus"
 * connector (a drop from the couple tie, a horizontal rail, then a drop to
 * each child) instead of one elbow per parent edge. Rows never wrap — wide
 * trees scroll horizontally.
 */

import type { RelationshipType, TreeEdge, TreeNode, TreeOut } from './types'

export interface ChipSize {
  width: number
  height: number
}

export interface ChipPosition {
  x: number
  y: number
}

export interface TreeRowLayout {
  generation: number
  y: number
  height: number
}

export interface DrawnLine {
  path: string
  kind: RelationshipType
  label: string | null
  midX: number
  midY: number
}

export interface TreeLayout {
  positions: Map<number, ChipPosition>
  rows: TreeRowLayout[]
  width: number
  height: number
  lines: DrawnLine[]
}

export const GUTTER = 156 // ledger label column reserved on the left
export const PAD = 24
export const COUPLE_GAP = 28 // between members of a couple unit (tie drawn here)
export const UNIT_GAP = 56 // between units within a row
export const ROW_GAP = 76 // vertical channel between rows where buses run
const BUS_OFFSET = 18 // first bus rail below a parent row
export const BUS_STEP = 9 // stagger between rails sharing a channel
const FALLBACK_SIZE: ChipSize = { width: 150, height: 44 }

interface Rect {
  left: number
  right: number
  top: number
  bottom: number
  cx: number
  cy: number
}

interface Unit {
  members: number[]
  width: number
  x: number
}

export function layoutTree(
  data: TreeOut,
  sizes: Map<number, ChipSize>,
  viewportWidth: number,
): TreeLayout {
  const generations = [...new Set(data.nodes.map((node) => node.generation))].sort((a, b) => a - b)
  const rowIndexOfGen = new Map(generations.map((generation, index) => [generation, index]))
  const rowOf = new Map(data.nodes.map((node) => [node.id, rowIndexOfGen.get(node.generation)!]))
  const nodesByRow: TreeNode[][] = generations.map(() => [])
  for (const node of data.nodes) nodesByRow[rowOf.get(node.id)!].push(node)
  const sizeOf = (id: number): ChipSize => sizes.get(id) ?? FALLBACK_SIZE

  // Blood components: everyone joined through parent edges is one family, so
  // a soft link (godparent, friend, …) between two blood relatives is
  // redundant with the structure already drawn and is dropped to cut clutter.
  const bloodParent = new Map<number, number>()
  const bloodRoot = (id: number): number => {
    let root = id
    while (bloodParent.get(root) !== undefined && bloodParent.get(root) !== root) {
      root = bloodParent.get(root)!
    }
    return root
  }
  for (const edge of data.edges) {
    if (edge.type !== 'parent') continue
    bloodParent.set(bloodRoot(edge.source_id), bloodRoot(edge.target_id))
  }
  const bloodConnected = (a: number, b: number): boolean =>
    bloodParent.has(a) && bloodParent.has(b) && bloodRoot(a) === bloodRoot(b)
  const isSoft = (type: RelationshipType): boolean =>
    type === 'godparent' || type === 'friend' || type === 'colleague' || type === 'custom'

  // Classify edges once: couples form units, canonical parent/godparent
  // edges spanning exactly one row become buses, same-row edges become
  // straight ties (adjacent) or channel elbows, and anything irregular
  // falls back to a generic elbow.
  const coupleEdges: TreeEdge[] = []
  const busParentEdges: TreeEdge[] = []
  const busGodEdges: TreeEdge[] = []
  const sameRowEdges: TreeEdge[] = []
  const oddEdges: TreeEdge[] = []
  for (const edge of data.edges) {
    const sourceRow = rowOf.get(edge.source_id)
    const targetRow = rowOf.get(edge.target_id)
    if (sourceRow === undefined || targetRow === undefined) continue
    // A soft tie between two blood relatives duplicates the family structure.
    if (isSoft(edge.type) && bloodConnected(edge.source_id, edge.target_id)) continue
    const diff = targetRow - sourceRow
    if (diff === 0 && (edge.type === 'spouse' || edge.type === 'partner')) coupleEdges.push(edge)
    else if (diff === 0) sameRowEdges.push(edge)
    else if (edge.type === 'parent' && diff === 1) busParentEdges.push(edge)
    else if (edge.type === 'godparent' && diff === 1) busGodEdges.push(edge)
    else if (edge.type === 'godparent') continue // multi-row godparent: drop, blood shows it
    else oddEdges.push(edge)
  }

  // Couple units via union-find, members and units alphabetical to start.
  const parentLink = new Map<number, number>()
  const find = (id: number): number => {
    let root = id
    while (parentLink.get(root) !== undefined && parentLink.get(root) !== root) {
      root = parentLink.get(root)!
    }
    return root
  }
  for (const edge of coupleEdges) parentLink.set(find(edge.source_id), find(edge.target_id))

  const unitsByRow: Unit[][] = nodesByRow.map((rowNodes) => {
    const clusters = new Map<number, TreeNode[]>()
    for (const node of [...rowNodes].sort((a, b) => a.full_name.localeCompare(b.full_name))) {
      const root = find(node.id)
      const cluster = clusters.get(root)
      if (cluster) cluster.push(node)
      else clusters.set(root, [node])
    }
    return [...clusters.values()]
      .sort((a, b) => a[0].full_name.localeCompare(b[0].full_name))
      .map((members) => ({ members: members.map((node) => node.id), width: 0, x: 0 }))
  })
  for (const units of unitsByRow) {
    for (const unit of units) {
      unit.width =
        unit.members.reduce((total, id) => total + sizeOf(id).width, 0) +
        COUPLE_GAP * (unit.members.length - 1)
    }
  }

  // Barycenter ordering: sweep down then up a few times, sorting each row's
  // units by the mean position of their cross-row neighbors.
  const neighbors = new Map<number, number[]>()
  for (const edge of [...busParentEdges, ...busGodEdges, ...oddEdges]) {
    neighbors.set(edge.source_id, [...(neighbors.get(edge.source_id) ?? []), edge.target_id])
    neighbors.set(edge.target_id, [...(neighbors.get(edge.target_id) ?? []), edge.source_id])
  }
  const orderPos = new Map<number, number>()
  const reindex = (row: number) => {
    let index = 0
    for (const unit of unitsByRow[row]) for (const member of unit.members) orderPos.set(member, index++)
  }
  unitsByRow.forEach((_, row) => reindex(row))
  const sortRow = (row: number) => {
    if (unitsByRow[row].length < 2) return
    const keyed = unitsByRow[row].map((unit) => {
      const positions: number[] = []
      for (const member of unit.members) {
        for (const other of neighbors.get(member) ?? []) positions.push(orderPos.get(other)!)
      }
      const key = positions.length
        ? positions.reduce((a, b) => a + b, 0) / positions.length
        : orderPos.get(unit.members[0])!
      return { unit, key }
    })
    keyed.sort((a, b) => a.key - b.key)
    unitsByRow[row] = keyed.map((entry) => entry.unit)
    reindex(row)
  }
  for (let pass = 0; pass < 3; pass++) {
    for (let row = 1; row < unitsByRow.length; row++) sortRow(row)
    for (let row = unitsByRow.length - 2; row >= 0; row--) sortRow(row)
  }

  // Vertical placement: fixed rows with a bus channel between them.
  const rowHeights = nodesByRow.map((rowNodes) =>
    Math.max(FALLBACK_SIZE.height, ...rowNodes.map((node) => sizeOf(node.id).height)),
  )
  const rowY: number[] = []
  {
    let y = PAD + 8
    for (const height of rowHeights) {
      rowY.push(y)
      y += height + ROW_GAP
    }
  }

  // Horizontal placement: pack every row, then align outward from the
  // center row — each unit moves toward the mean center of its relatives in
  // the already-placed reference row, never overlapping its left neighbor.
  const centers = new Map<number, number>()
  const setCenters = (row: number) => {
    for (const unit of unitsByRow[row]) {
      let x = unit.x
      for (const member of unit.members) {
        const width = sizeOf(member).width
        centers.set(member, x + width / 2)
        x += width + COUPLE_GAP
      }
    }
  }
  unitsByRow.forEach((units) => {
    let x = 0
    for (const unit of units) {
      unit.x = x
      x += unit.width + UNIT_GAP
    }
  })
  const alignRow = (row: number, referenceRow: number) => {
    let previousEnd = -Infinity
    for (const unit of unitsByRow[row]) {
      const targets: number[] = []
      for (const member of unit.members) {
        for (const other of neighbors.get(member) ?? []) {
          if (rowOf.get(other) !== referenceRow) continue
          const center = centers.get(other)
          if (center !== undefined) targets.push(center)
        }
      }
      const desired = targets.length
        ? targets.reduce((a, b) => a + b, 0) / targets.length - unit.width / 2
        : unit.x
      unit.x = Math.max(desired, previousEnd === -Infinity ? desired : previousEnd + UNIT_GAP)
      previousEnd = unit.x + unit.width
    }
    setCenters(row)
  }
  const centerRow = rowOf.get(data.center_id) ?? 0
  setCenters(centerRow)
  for (let row = centerRow - 1; row >= 0; row--) alignRow(row, row + 1)
  for (let row = centerRow + 1; row < unitsByRow.length; row++) alignRow(row, row - 1)

  // Final coordinates, shifted past the label gutter and centered when the
  // tree is narrower than the viewport.
  const positions = new Map<number, ChipPosition>()
  let minLeft = Infinity
  let maxRight = -Infinity
  unitsByRow.forEach((units, row) => {
    for (const unit of units) {
      let x = unit.x
      for (const member of unit.members) {
        const size = sizeOf(member)
        positions.set(member, { x, y: rowY[row] + (rowHeights[row] - size.height) / 2 })
        minLeft = Math.min(minLeft, x)
        maxRight = Math.max(maxRight, x + size.width)
        x += size.width + COUPLE_GAP
      }
    }
  })
  let shift = GUTTER + PAD - minLeft
  const contentWidth = maxRight + shift + PAD
  const width = Math.max(contentWidth, viewportWidth)
  shift += Math.max(0, (width - contentWidth) / 2)
  positions.forEach((position) => {
    position.x += shift
  })
  const height = rowY[rowY.length - 1] + rowHeights[rowHeights.length - 1] + PAD + 8

  const rectOf = (id: number): Rect => {
    const position = positions.get(id)!
    const size = sizeOf(id)
    return {
      left: position.x,
      right: position.x + size.width,
      top: position.y,
      bottom: position.y + size.height,
      cx: position.x + size.width / 2,
      cy: position.y + size.height / 2,
    }
  }
  const rowRects = nodesByRow.map((rowNodes) => rowNodes.map((node) => rectOf(node.id)))
  const nothingBetween = (row: number, a: Rect, b: Rect): boolean => {
    const [lo, hi] = a.cx <= b.cx ? [a, b] : [b, a]
    return !rowRects[row].some((rect) => rect.cx > lo.cx && rect.cx < hi.cx)
  }

  const lines: DrawnLine[] = []

  interface ChannelItem {
    row: number
    anchorX: number
    build: (busY: number) => DrawnLine
  }
  // Everything that runs through the channel below a row — family buses,
  // godparent drops, and peer elbows — is collected here first and then
  // assigned a staggered depth per row, so two connectors never share a y.
  const channelItems: ChannelItem[] = []

  /** Same-row link: straight tie between adjacent chips; otherwise a
   * right-angle elbow through the row's channel (down, across, up). The old
   * quadratic dip crossed the bus channel at a shallow angle, and two such
   * arcs in one channel ran a few pixels apart — visible as a scratchy
   * double line (G-60). */
  const pushPeerLine = (edge: TreeEdge) => {
    const row = rowOf.get(edge.source_id)!
    const a = rectOf(edge.source_id)
    const b = rectOf(edge.target_id)
    const [left, right] = a.cx <= b.cx ? [a, b] : [b, a]
    if (right.left - left.right <= UNIT_GAP + 1 && nothingBetween(row, a, b)) {
      const y = (left.cy + right.cy) / 2
      lines.push({
        path: `M ${left.right} ${y} H ${right.left}`,
        kind: edge.type,
        label: edge.label,
        midX: (left.right + right.left) / 2,
        midY: Math.max(left.bottom, right.bottom) + 10,
      })
    } else {
      channelItems.push({
        row,
        anchorX: (left.cx + right.cx) / 2,
        build: (busY) => ({
          path: `M ${left.cx} ${left.bottom} V ${busY} H ${right.cx} V ${right.bottom}`,
          kind: edge.type,
          label: edge.label,
          midX: (left.cx + right.cx) / 2,
          midY: busY,
        }),
      })
    }
  }

  for (const edge of coupleEdges) pushPeerLine(edge)

  // Family buses: children grouped by their (adjacent-row) parent set, one
  // rail per family, staggered within the channel so rails never overlap.
  const busParentsOfChild = new Map<number, number[]>()
  for (const edge of busParentEdges) {
    busParentsOfChild.set(edge.target_id, [
      ...(busParentsOfChild.get(edge.target_id) ?? []),
      edge.source_id,
    ])
  }

  const families = new Map<number, { parents: number[]; children: number[] }>()
  const familyKeys = new Map<string, number>()
  for (const [child, parents] of busParentsOfChild) {
    const sorted = [...new Set(parents)].sort((a, b) => a - b)
    const key = sorted.join(',')
    let familyId = familyKeys.get(key)
    if (familyId === undefined) {
      familyId = families.size
      familyKeys.set(key, familyId)
      families.set(familyId, { parents: sorted, children: [] })
    }
    families.get(familyId)!.children.push(child)
  }
  for (const family of families.values()) {
    const parentRow = rowOf.get(family.parents[0])!
    const parentRects = family.parents.map(rectOf)
    let coupleAnchor: { x: number; y: number } | null = null
    if (family.parents.length === 2 && find(family.parents[0]) === find(family.parents[1])) {
      const [left, right] = parentRects[0].cx <= parentRects[1].cx ? parentRects : [parentRects[1], parentRects[0]]
      if (right.left - left.right <= UNIT_GAP + 1 && nothingBetween(parentRow, left, right)) {
        coupleAnchor = { x: (left.right + right.left) / 2, y: (left.cy + right.cy) / 2 }
      }
    }
    const dropXs = coupleAnchor ? [coupleAnchor.x] : parentRects.map((rect) => rect.cx)
    const childRects = family.children.map(rectOf)
    channelItems.push({
      row: parentRow,
      anchorX: dropXs.reduce((a, b) => a + b, 0) / dropXs.length,
      build: (busY) => {
        const parts = coupleAnchor
          ? [`M ${coupleAnchor.x} ${coupleAnchor.y} V ${busY}`]
          : parentRects.map((rect) => `M ${rect.cx} ${rect.bottom} V ${busY}`)
        const xs = [...dropXs, ...childRects.map((rect) => rect.cx)]
        const lo = Math.min(...xs)
        const hi = Math.max(...xs)
        if (hi - lo > 0.5) parts.push(`M ${lo} ${busY} H ${hi}`)
        for (const rect of childRects) parts.push(`M ${rect.cx} ${busY} V ${rect.top}`)
        return {
          path: parts.join(' '),
          kind: 'parent',
          label: null,
          midX: (lo + hi) / 2,
          midY: busY,
        }
      },
    })
  }
  for (const edge of busGodEdges) {
    const god = rectOf(edge.source_id)
    const child = rectOf(edge.target_id)
    channelItems.push({
      row: rowOf.get(edge.source_id)!,
      anchorX: god.cx,
      build: (busY) => ({
        path: `M ${god.cx} ${god.bottom} V ${busY} H ${child.cx} V ${child.top}`,
        kind: 'godparent',
        label: edge.label,
        midX: (god.cx + child.cx) / 2,
        midY: busY,
      }),
    })
  }

  // Remaining same-row links; sibling ties are redundant when a family bus
  // already joins the two through a shared parent.
  const allParentsOfChild = new Map<number, Set<number>>()
  for (const edge of data.edges) {
    if (edge.type !== 'parent') continue
    const set = allParentsOfChild.get(edge.target_id) ?? new Set<number>()
    set.add(edge.source_id)
    allParentsOfChild.set(edge.target_id, set)
  }
  const shareParent = (a: number, b: number): boolean => {
    const parentsA = allParentsOfChild.get(a)
    const parentsB = allParentsOfChild.get(b)
    if (!parentsA || !parentsB) return false
    return [...parentsA].some((parent) => parentsB.has(parent))
  }
  for (const edge of sameRowEdges) {
    if (edge.type === 'sibling' && shareParent(edge.source_id, edge.target_id)) continue
    pushPeerLine(edge)
  }

  // Channel allocation: one staggered depth per connector, per row.
  const itemsByChannel = new Map<number, ChannelItem[]>()
  for (const item of channelItems) {
    itemsByChannel.set(item.row, [...(itemsByChannel.get(item.row) ?? []), item])
  }
  for (const [row, items] of itemsByChannel) {
    items.sort((a, b) => a.anchorX - b.anchorX)
    const channelTop = rowY[row] + rowHeights[row]
    const channelBottom = rowY[row + 1] ?? channelTop + ROW_GAP
    items.forEach((item, index) => {
      const busY = Math.min(channelTop + BUS_OFFSET + index * BUS_STEP, channelBottom - 10)
      lines.push(item.build(busY))
    })
  }

  // Irregular cross-row links (generation conflicts): plain elbow fallback.
  for (const edge of oddEdges) {
    const a = rectOf(edge.source_id)
    const b = rectOf(edge.target_id)
    const [top, bottom] = a.cy <= b.cy ? [a, b] : [b, a]
    const midY = (top.bottom + bottom.top) / 2
    lines.push({
      path: `M ${top.cx} ${top.bottom} V ${midY} H ${bottom.cx} V ${bottom.top}`,
      kind: edge.type,
      label: edge.label,
      midX: (top.cx + bottom.cx) / 2,
      midY,
    })
  }

  return {
    positions,
    rows: generations.map((generation, index) => ({
      generation,
      y: rowY[index],
      height: rowHeights[index],
    })),
    width,
    height,
    lines,
  }
}
