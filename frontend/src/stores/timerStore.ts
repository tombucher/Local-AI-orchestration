/**
 * Store Zustand pour la gestion du timer
 */

import { create } from 'zustand';
import { timerService } from '../services/timer';
import type { TimeEntry, CurrentTimer, TimerStats } from '../types/timer.types';

interface TimerState {
  currentTimer: CurrentTimer | null;
  todayEntries: TimeEntry[];
  stats: TimerStats | null;
  elapsedSeconds: number;
  loading: boolean;
  error: string | null;

  // Actions
  startTimer: (projectId: number, taskId?: number) => Promise<void>;
  stopTimer: () => Promise<void>;
  fetchCurrentTimer: () => Promise<void>;
  fetchTodayEntries: () => Promise<void>;
  fetchStats: () => Promise<void>;
  updateElapsedSeconds: (seconds: number) => void;
  clearError: () => void;
}

export const useTimerStore = create<TimerState>((set, get) => ({
  currentTimer: null,
  todayEntries: [],
  stats: null,
  elapsedSeconds: 0,
  loading: false,
  error: null,

  /**
   * Démarrer un nouveau timer
   */
  startTimer: async (projectId, taskId) => {
    set({ loading: true, error: null });
    try {
      const entry = await timerService.startTimer(projectId, taskId);
      const currentTimer: CurrentTimer = {
        entry,
        elapsed_seconds: 0,
      };
      set({ currentTimer, elapsedSeconds: 0, loading: false });
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || 'Erreur lors du démarrage du timer';
      set({ error: errorMessage, loading: false });
      throw error;
    }
  },

  /**
   * Arrêter le timer actif
   */
  stopTimer: async () => {
    set({ loading: true, error: null });
    try {
      await timerService.stopTimer();
      set({ currentTimer: null, elapsedSeconds: 0, loading: false });
      // Recharger les entrées du jour
      get().fetchTodayEntries();
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || 'Erreur lors de l\'arrêt du timer';
      set({ error: errorMessage, loading: false });
      throw error;
    }
  },

  /**
   * Récupérer le timer actuellement actif
   */
  fetchCurrentTimer: async () => {
    set({ loading: true, error: null });
    try {
      const currentTimer = await timerService.getCurrentTimer();
      if (currentTimer) {
        set({
          currentTimer,
          elapsedSeconds: currentTimer.elapsed_seconds,
          loading: false
        });
      } else {
        set({ currentTimer: null, elapsedSeconds: 0, loading: false });
      }
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || 'Erreur lors du chargement du timer';
      set({ error: errorMessage, loading: false });
    }
  },

  /**
   * Récupérer les entrées du jour
   */
  fetchTodayEntries: async () => {
    set({ loading: true, error: null });
    try {
      const entries = await timerService.getTodayEntries();
      set({ todayEntries: entries, loading: false });
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || 'Erreur lors du chargement des entrées';
      set({ error: errorMessage, loading: false });
    }
  },

  /**
   * Récupérer les statistiques
   */
  fetchStats: async () => {
    set({ loading: true, error: null });
    try {
      const stats = await timerService.getTimerStats();
      set({ stats, loading: false });
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || 'Erreur lors du chargement des stats';
      set({ error: errorMessage, loading: false });
    }
  },

  /**
   * Mettre à jour les secondes écoulées (appelé chaque seconde)
   */
  updateElapsedSeconds: (seconds) => {
    set({ elapsedSeconds: seconds });
  },

  /**
   * Effacer l'erreur
   */
  clearError: () => {
    set({ error: null });
  },
}));
