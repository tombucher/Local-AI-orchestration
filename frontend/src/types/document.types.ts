/**
 * Espace documents d'un projet : notes, extraits de code et images de référence
 * que l'orchestrateur prend en compte lors des générations.
 */

export type DocumentKind = 'text' | 'code' | 'image';

export interface ProjectDocument {
  id: number;
  project_id: number;
  name: string;
  kind: DocumentKind;
  mime_type: string;
  note: string | null;
  enabled: boolean;
  size_bytes: number;
  created_at: string;
  /** Premiers caractères, pour l'aperçu en liste (null pour une image) */
  excerpt: string | null;
  has_image: boolean;
}

export interface ProjectDocumentDetail extends ProjectDocument {
  content: string | null;
}

export interface DocumentTextCreate {
  name: string;
  content: string;
  kind?: DocumentKind;
  note?: string;
}

export interface DocumentUpdate {
  name?: string;
  note?: string;
  enabled?: boolean;
  content?: string;
}
