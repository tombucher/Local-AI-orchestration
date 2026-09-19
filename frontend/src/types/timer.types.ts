/**
 * Types pour le timer et les time entries
 */

export interface TimeEntry {
  id: number;
  user_id: number;
  project_id: number;
  task_id: number | null;
  start_time: string;
  end_time: string | null;
  duration_seconds: number | null;
  notes: string | null;
  created_at: string;
}

export interface TimeEntryCreate {
  project_id: number;
  task_id?: number;
  notes?: string;
}

export interface TimeEntryUpdate {
  notes?: string;
}

export interface CurrentTimer {
  entry: TimeEntry;
  elapsed_seconds: number;
}

export interface TimerStats {
  today_total_seconds: number;
  week_total_seconds: number;
  month_total_seconds: number;
  entries_count: number;
}
