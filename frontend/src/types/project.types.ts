/**
 * Types pour les projets
 */

export enum ProjectType {
  PROFESSIONAL = 'professional',
  PERSONAL = 'personal',
  RESEARCH = 'research',
}

export enum ProjectStatus {
  IDEATION = 'IDEATION',
  PLANNING = 'PLANNING',
  ACTIVE = 'ACTIVE',
  ARCHIVED = 'ARCHIVED',
  PAUSED = 'PAUSED',
}

export interface ProjectFeatures {
  code_gen: boolean;
  veille: boolean;
  git_auto: boolean;
}

export interface FinancialConfig {
  hourly_rate?: number;
  budget?: number;
  currency?: string;
}

export interface Project {
  id: number;
  user_id: number;
  name: string;
  description: string | null;
  type: ProjectType;
  status: ProjectStatus;
  features: ProjectFeatures;
  financial_config: FinancialConfig | null;
  maturity_score: number;  // Score de maturité (0-100)
  repository_url?: string | null;
  created_at: string;
  updated_at: string;
  // Statistiques renvoyées par la liste de projets
  tasks_total?: number | null;
  tasks_completed?: number | null;
}

export interface ProjectStats {
  total_tasks: number;
  tasks_by_status: Record<string, number>;
  tasks_by_priority: Record<string, number>;
  total_time_seconds?: number;
  estimated_cost?: number;
  tasks_pending?: number;
  tasks_in_progress?: number;
  tasks_completed?: number;
}

export interface ProjectCreate {
  name: string;
  description?: string;
  type: ProjectType;
  features: ProjectFeatures;
  financial_config?: FinancialConfig;
}

export interface ProjectUpdate {
  name?: string;
  description?: string;
  type?: ProjectType;
  status?: ProjectStatus;
  features?: ProjectFeatures;
  financial_config?: FinancialConfig;
}

export interface ProjectStats {
  total_tasks: number;
  tasks_by_status: Record<string, number>;
  tasks_by_priority: Record<string, number>;
  total_time_seconds?: number;
  estimated_cost?: number;
}

export interface ProjectList {
  items: Project[];
  total: number;
  page: number;
  page_size: number;
}

// ============================================================================
// Types pour le workflow "Finaliser la Vision" avec validation
// ============================================================================

export interface TaskPreview {
  title: string;
  description: string;
  task_type: string;
  priority: string;
  estimated_duration?: number;
  llm_prompt?: string;
  subtasks: string[];
}

export interface ProjectFinalizationPreview {
  suggested_name: string;
  suggested_description: string;
  project_type: string;
  tasks: TaskPreview[];
  veille_keywords: string[];
}

export interface TaskValidationInput {
  title: string;
  description: string;
  task_type: string;
  priority: string;
  estimated_duration?: number;
  llm_prompt?: string;
  approved: boolean;
}

export interface FinalizeValidationRequest {
  project_id: number;
  project_name: string;
  project_description: string;
  tasks: TaskValidationInput[];
  enable_veille: boolean;
  veille_keywords: string[];
}

export interface TaskGenerated {
  id: number;
  title: string;
  description: string;
  task_type: string;
  priority: string;
  estimated_duration?: number;
}

export interface ProjectFinalizeResponse {
  project_id: number;
  project_name: string;
  project_description: string;
  tasks_count: number;
  tasks: TaskGenerated[];
  message: string;
}
