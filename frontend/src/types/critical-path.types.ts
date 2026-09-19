/**
 * Types pour les données du chemin critique (Critical Path Method)
 */

export interface CriticalPathTaskData {
  task_id: number;
  title: string;
  status: string;
  early_start: number;
  early_finish: number;
  late_start: number;
  late_finish: number;
  is_critical: boolean;
  slack: number;
  /** Dates projetées (ISO) calculées par le backend depuis aujourd'hui */
  projected_start: string;
  projected_end: string;
  due_date: string | null;
  /** IDs des tâches dont celle-ci dépend */
  depends_on: number[];
}

export interface CriticalPathData {
  ordered_tasks: CriticalPathTaskData[];
  critical_tasks: number[];
  total_duration: number;
  projected_end_date: string | null;
  has_cycle: boolean;
}
