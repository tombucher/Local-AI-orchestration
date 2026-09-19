/**
 * Types pour les rapports quotidiens
 */

export interface Blocker {
  type: string;
  description: string;
  severity: 'low' | 'medium' | 'high';
  suggestion: string;
}

export interface ProjectStatus {
  project_id: number;
  project_name: string;
  total_tasks: number;
  completed_tasks: number;
  in_progress_tasks: number;
  ready_tasks: number;
  failed_tasks: number;
  completion_rate: number;
  p1_tasks: number;
  blockers: Blocker[];
  recommended_actions: string[];
  health_status: 'healthy' | 'warning' | 'critical';
  /** Action concrète démarrable en 5 min, générée par l'IA */
  next_obvious_action?: string | null;
  ready_task_titles?: string[];
  /** Projet sans activité récente + suggestions de relance */
  is_stagnant?: boolean;
  suggested_tasks?: SuggestedTask[];
}

export interface SuggestedTask {
  title: string;
  description: string;
  task_type: string;
  priority: string;
  estimated_duration?: number | null;
  subtasks?: string[];
  llm_prompt?: string | null;
  keywords?: string[];
}

export interface DailyReport {
  id: number;
  user_id: number;
  date: string;
  summary: string;
  total_projects: number;
  active_projects: number;
  total_tasks: number;
  completed_today: number;
  blockers_count: number;
  projects: ProjectStatus[];
  top_priorities: string[];
  recommendations: string[];
  created_at: string;
}

export interface DailyReportListResponse {
  total: number;
  reports: DailyReport[];
}
