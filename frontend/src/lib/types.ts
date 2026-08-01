/** API types mirroring the backend schemas. */

export type FieldType = 'text' | 'textarea' | 'number' | 'date' | 'boolean' | 'sensitive'

export interface FieldOut {
  id: number
  label: string
  value: string | null
  type: FieldType
  is_pinned: boolean
  is_system: boolean
  position: number
  updated_at: string
}

export interface DocumentOut {
  id: number
  title: string
  original_filename: string
  mime_type: string
  size_bytes: number
  uploaded_at: string
}

export type RelationshipType =
  | 'spouse'
  | 'partner'
  | 'parent'
  | 'child'
  | 'sibling'
  | 'friend'
  | 'colleague'
  | 'godparent'
  | 'godchild'
  | 'custom'

/** Gendered role for the related person, refining its structural type (G-31). */
export type RelationshipRole =
  | 'father'
  | 'mother'
  | 'son'
  | 'daughter'
  | 'brother'
  | 'sister'
  | 'husband'
  | 'wife'
  | 'godfather'
  | 'godmother'
  | 'godson'
  | 'goddaughter'

export interface RelationshipOut {
  id: number
  person_id: number
  person_name: string
  person_has_photo: boolean
  label: string
}

export interface TreeNode {
  id: number
  full_name: string
  generation: number
  /** Derived relationship to the center person ("Mother", "Uncle", …) or null. */
  kinship: string | null
}

export interface TreeEdge {
  source_id: number
  target_id: number
  type: RelationshipType
  label: string | null
}

export interface TreeOut {
  center_id: number
  nodes: TreeNode[]
  edges: TreeEdge[]
}

/** A user-defined label a person can be tagged with (Phase 3, tags & favorites). */
export interface Tag {
  id: number
  name: string
  person_count: number
}

export interface PersonSummary {
  id: number
  full_name: string
  has_photo: boolean
  updated_at: string
  pinned_fields: FieldOut[]
  /** Fields whose value matched a field-value search, shown as the match reason (FR-27). */
  matched_fields?: FieldOut[]
  is_favorite: boolean
  tags: Tag[]
}

export interface PersonDetail {
  id: number
  full_name: string
  has_photo: boolean
  fields: FieldOut[]
  documents: DocumentOut[]
  relationships: RelationshipOut[]
  created_at: string
  updated_at: string
  is_favorite: boolean
  tags: Tag[]
}

/** Summary returned after a JSON import or an encrypted-backup restore
 * (Phase 3, FR-30 / G3; `documents_restored` added for encrypted restore). */
export interface ImportReport {
  schema_version: number
  people_created: number
  people_skipped: number
  fields_created: number
  relationships_created: number
  relationships_skipped: number
  documents_skipped: number
  documents_restored: number
  sensitive_values_missing: number
  warnings: string[]
}

/** Counts and sizes for the "Your data" summary card (Phase 3, encrypted backup). */
export interface SystemSummary {
  people: number
  fields: number
  documents: number
  relationships: number
  tags: number
  uploads_bytes: number
  database_bytes: number
  last_backup_at: string | null
}

export interface AuthStatus {
  initialized: boolean
  authenticated: boolean
  username: string | null
}
