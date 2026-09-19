/**
 * Service API pour la gestion du timer et des time entries
 */

import api from './api';
import type { TimeEntry, TimeEntryUpdate, CurrentTimer, TimerStats } from '../types/timer.types';

export const timerService = {
  /**
   * Démarrer un nouveau timer
   */
  startTimer: async (projectId: number, taskId?: number): Promise<TimeEntry> => {
    const response = await api.post<TimeEntry>('/time/start', {
      project_id: projectId,
      task_id: taskId,
    });
    return response.data;
  },

  /**
   * Arrêter le timer actif
   */
  stopTimer: async (): Promise<TimeEntry> => {
    const response = await api.post<TimeEntry>('/time/stop');
    return response.data;
  },

  /**
   * Récupérer le timer actuellement actif
   */
  getCurrentTimer: async (): Promise<CurrentTimer | null> => {
    try {
      // silentError : un 404 signifie simplement qu'aucun timer ne tourne
      const response = await api.get<CurrentTimer>('/time/current', { silentError: true });
      return response.data;
    } catch (error: any) {
      if (error.response?.status === 404) {
        return null;
      }
      throw error;
    }
  },

  /**
   * Récupérer les entrées du jour
   */
  getTodayEntries: async (): Promise<TimeEntry[]> => {
    const response = await api.get<TimeEntry[]>('/time/today');
    return response.data;
  },

  /**
   * Récupérer toutes les time entries avec filtres
   */
  getTimeEntries: async (filters?: {
    project_id?: number;
    task_id?: number;
    start_date?: string;
    end_date?: string;
  }): Promise<TimeEntry[]> => {
    const params = new URLSearchParams();
    if (filters?.project_id) params.append('project_id', filters.project_id.toString());
    if (filters?.task_id) params.append('task_id', filters.task_id.toString());
    if (filters?.start_date) params.append('start_date', filters.start_date);
    if (filters?.end_date) params.append('end_date', filters.end_date);

    const response = await api.get<TimeEntry[]>(`/time/entries?${params.toString()}`);
    return response.data;
  },

  /**
   * Mettre à jour une time entry
   */
  updateTimeEntry: async (id: number, data: TimeEntryUpdate): Promise<TimeEntry> => {
    const response = await api.put<TimeEntry>(`/time/${id}`, data);
    return response.data;
  },

  /**
   * Supprimer une time entry
   */
  deleteTimeEntry: async (id: number): Promise<void> => {
    await api.delete(`/time/${id}`);
  },

  /**
   * Récupérer les statistiques de temps
   */
  getTimerStats: async (): Promise<TimerStats> => {
    const response = await api.get<TimerStats>('/time/stats');
    return response.data;
  },
};
