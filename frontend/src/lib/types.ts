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

export type RelationshipType = 'spouse' | 'parent' | 'child' | 'sibling' | 'custom'

export interface RelationshipOut {
  id: number
  person_id: number
  person_name: string
  person_has_photo: boolean
  label: string
}

export interface PersonSummary {
  id: number
  full_name: string
  has_photo: boolean
  updated_at: string
  pinned_fields: FieldOut[]
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
}

export interface AuthStatus {
  initialized: boolean
  authenticated: boolean
  username: string | null
}
