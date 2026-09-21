/**
 * Types pour les tâches
 */

export enum TaskPriority {
  P1 = 'P1',
  P2 = 'P2',
  P3 = 'P3',
}

export enum TaskStatus {
  CREATED = 'created',
  READY = 'ready',
  GENERATING = 'generating',
  MANUAL_REVIEW = 'manual_review',
  COMPLETED = 'completed',
  FAILED = 'failed',
  CANCELLED = 'cancelled',
}

export enum TaskType {
  CODE_GENERATION = 'code_generation',
  DOCUMENT_WRITING = 'document_writing',
  FUNDING_SEARCH = 'funding_search',
  VEILLE = 'veille',                     // Type unifié
  VEILLE_TECH = 'veille_tech',           // DEPRECATED — compat DB
  VEILLE_CULTURAL = 'veille_cultural',   // DEPRECATED — compat DB
  VEILLE_EVENTS = 'veille_events',       // DEPRECATED — compat DB
  ADMINISTRATIVE = 'administrative',
  RESEARCH = 'research',
}

/** Étape en cours d'une tâche longue, servie par le backend à chaque poll */
export interface TaskProgress {
  phase: string;
  label: string;
  current: number | null;
  total: number | null;
  percent: number | null;
}

export interface Task {
  id: number;
  project_id: number;
  project_name?: string;  // Nom du projet (pour affichage)
  retry_count?: number;
  last_failed_at?: string | null;
  /** IDs des tâches dont celle-ci dépend */
  dependencies?: number[];
  title: string;
  description: string | null;
  task_type: TaskType;
  priority: TaskPriority;
  status: TaskStatus;
  llm_prompt: string | null;
  generated_code: string | null;
  validation_notes: string | null;
  estimated_duration: number | null;
  actual_duration: number | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  metadata: Record<string, any>;
  // Veille
  radar_report: RadarReport | null;
  veille_topic_id: number | null;
  /** Avancement d'une tâche en cours (null si rien ne tourne) */
  progress: TaskProgress | null;
}

export interface TaskCreate {
  project_id: number;
  title: string;
  description?: string;
  task_type?: TaskType;
  priority: TaskPriority;
  llm_prompt?: string;
  metadata?: Record<string, any>;
}

export interface TaskUpdate {
  title?: string;
  description?: string;
  priority?: TaskPriority;
  task_type?: TaskType;
  llm_prompt?: string;
  status?: TaskStatus;
  estimated_duration?: number | null;
  due_date?: string | null;
  dependency_ids?: number[];
  metadata?: Record<string, any>;
}

export interface TaskFilters {
  project_id?: number;
  status?: TaskStatus;
  priority?: TaskPriority;
  limit?: number;
  offset?: number;
}

export interface TaskLog {
  id: number;
  task_id: number;
  event_type: string;
  message: string;
  metadata: Record<string, any>;
  created_at: string;
}

/**
 * Types pour les résultats de veille
 */
export enum VeilleResultType {
  FUNDING_OPPORTUNITY = 'funding_opportunity',
  TECH_ARTICLE = 'tech_article',
  TECH_TOOL = 'tech_tool',
  EVENT = 'event',
  COLLABORATION = 'collaboration',
  ACADEMIC_PAPER = 'academic_paper',
  NEWS_ARTICLE = 'news_article',
  ARTIST_WORK = 'artist_work',
  CALL_FOR_PROPOSALS = 'call_for_proposals',
}

export enum VeilleResultStatus {
  NEW = 'new',
  READ = 'read',
  SAVED = 'saved',
  ACTIONABLE = 'actionable',
  DISMISSED = 'dismissed',
}

export interface VeilleResult {
  /** « veille » (collectée) ou « document » (déposée dans l'espace documents) */
  source_kind?: 'veille' | 'document';
  id: number;
  topic_id: number;
  result_type: VeilleResultType;
  title: string;
  url: string | null;
  description: string | null;
  ai_summary: string | null;
  relevance_score: number;
  key_points: string[];
  relevance_reason: string | null;
  metadata: Record<string, any>;
  source: string | null;
  source_platform: string | null;
  published_at: string | null;
  found_at: string;
  status: VeilleResultStatus;
  /** Veille avancée : échéance (appels à projets) et références visuelles */
  deadline?: string | null;
  image_url?: string | null;
  thumbnail_url?: string | null;
  license?: string | null;
  user_notes: string | null;
  user_rating: number | null;
  task_created: boolean;
  task_id: number | null;
  created_at: string;
  updated_at: string;
}

export interface VeilleResultList {
  items: VeilleResult[];
  total: number;
  task_id: number;
}


/**
 * Types pour le Rapport Radar
 */
export interface RadarPepite {
  name: string;
  synthesis: string;
  link: string | null;
  relevance_score: number;
  result_id: number | null;
}

export interface RadarStats {
  total_scanned: number;
  total_relevant: number;
  avg_score: number;
  top_sources: string[];
  scan_date: string;
}

export interface RadarAffinage {
  current_keywords: string[];
  suggested_additions: string[];
  suggested_removals: string[];
  suggested_exclusions: string[];
  reasoning: string;
}

export interface RadarReport {
  pepites: RadarPepite[];
  stats: RadarStats;
  affinage: RadarAffinage;
}

export interface VeilleRefinePayload {
  add_keywords: string[];
  remove_keywords: string[];
  add_excluded: string[];
  remove_excluded: string[];
  user_notes?: string;
}
