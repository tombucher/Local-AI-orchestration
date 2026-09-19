/**
 * Types pour l'analyse intelligente de projets
 */

import { TaskType, TaskPriority } from './task.types';

export interface TaskSuggestion {
  title: string;
  description: string;
  task_type: TaskType;
  priority: TaskPriority;
  estimated_duration?: number;
  subtasks: string[];
  llm_prompt?: string;
  keywords: string[];
}

export interface VeilleSuggestion {
  scope: string;
  keywords: string[];
  scan_frequency: string;
  reason: string;
}

export interface Blocker {
  type: string;
  description: string;
  severity: 'low' | 'medium' | 'high';
  suggestion: string;
}

export interface ProjectAnalysis {
  project_id: number;
  analyzed_at: string;
  summary: string;
  task_suggestions: TaskSuggestion[];
  veille_suggestions: VeilleSuggestion[];
  blockers: Blocker[];
  next_actions: string[];
  estimated_total_hours?: number;
}

export interface CreateTasksRequest {
  task_indices: number[];
}

export interface CreateTasksResponse {
  created_count: number;
  task_ids: number[];
  message: string;
}

export interface RefineTaskRequest {
  task_data: TaskSuggestion;
  user_prompt: string;
}

export interface RefineTaskResponse {
  refined_task: TaskSuggestion;
}
