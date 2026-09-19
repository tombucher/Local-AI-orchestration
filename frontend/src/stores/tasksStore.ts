/**
 * Store Zustand pour la gestion des tâches
 */

import { create } from 'zustand';
import { tasksService } from '../services/tasks';
import { celebrateCompletion } from '../utils/celebrate';
import type { Task, TaskCreate, TaskUpdate, TaskFilters, TaskLog } from '../types/task.types';

interface TasksState {
  tasks: Task[];
  currentTask: Task | null;
  taskLogs: TaskLog[];
  filters: TaskFilters;
  loading: boolean;
  error: string | null;

  // Actions
  fetchTasks: (filters?: TaskFilters) => Promise<void>;
  fetchTask: (id: number) => Promise<void>;
  createTask: (data: TaskCreate) => Promise<Task>;
  updateTask: (id: number, data: TaskUpdate) => Promise<void>;
  deleteTask: (id: number) => Promise<void>;
  validateTask: (id: number, approved: boolean, notes?: string, editedCode?: string) => Promise<void>;
  rejectTask: (id: number, notes: string) => Promise<void>;
  cancelTask: (id: number) => Promise<void>;
  retryTask: (id: number) => Promise<void>;
  generateTask: (id: number) => Promise<void>;
  activateTask: (id: number) => Promise<void>;
  completeTask: (id: number) => Promise<void>;
  stopGeneration: (id: number) => Promise<void>;
  fetchTaskLogs: (id: number) => Promise<void>;
  setFilters: (filters: TaskFilters) => void;
  clearCurrentTask: () => void;
  clearError: () => void;
}

export const useTasksStore = create<TasksState>((set, get) => ({
  tasks: [],
  currentTask: null,
  taskLogs: [],
  filters: {},
  loading: false,
  error: null,

  /**
   * Récupérer toutes les tâches avec filtres
   */
  fetchTasks: async (filters) => {
    set({ loading: true, error: null });
    try {
      const mergedFilters = { ...get().filters, ...filters };
      const tasks = await tasksService.getTasks(mergedFilters);
      set({ tasks, filters: mergedFilters, loading: false });
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || 'Erreur lors du chargement des tâches';
      set({ error: errorMessage, loading: false });
    }
  },

  /**
   * Récupérer une tâche spécifique
   */
  fetchTask: async (id) => {
    set({ loading: true, error: null });
    try {
      const task = await tasksService.getTask(id);
      set({ currentTask: task, loading: false });
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || 'Erreur lors du chargement de la tâche';
      set({ error: errorMessage, loading: false });
    }
  },

  /**
   * Créer une nouvelle tâche
   */
  createTask: async (data) => {
    set({ loading: true, error: null });
    try {
      const task = await tasksService.createTask(data);
      set((state) => ({
        tasks: [task, ...state.tasks],
        loading: false,
      }));
      return task;
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || 'Erreur lors de la création de la tâche';
      set({ error: errorMessage, loading: false });
      throw error;
    }
  },

  /**
   * Mettre à jour une tâche
   */
  updateTask: async (id, data) => {
    set({ loading: true, error: null });
    try {
      const task = await tasksService.updateTask(id, data);
      set((state) => ({
        tasks: state.tasks.map((t) => (t.id === id ? task : t)),
        currentTask: state.currentTask?.id === id ? task : state.currentTask,
        loading: false,
      }));
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || 'Erreur lors de la mise à jour de la tâche';
      set({ error: errorMessage, loading: false });
      throw error;
    }
  },

  /**
   * Valider le code généré
   */
  validateTask: async (id, approved, notes, editedCode) => {
    set({ loading: true, error: null });
    try {
      const task = await tasksService.validateTask(id, approved, notes, editedCode);
      if (approved && task.status === 'completed') celebrateCompletion(task.title);
      set((state) => ({
        tasks: state.tasks.map((t) => (t.id === id ? task : t)),
        currentTask: task,
        loading: false,
      }));
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || 'Erreur lors de la validation de la tâche';
      set({ error: errorMessage, loading: false });
      throw error;
    }
  },

  /**
   * Rejeter le code généré
   */
  rejectTask: async (id, notes) => {
    set({ loading: true, error: null });
    try {
      const task = await tasksService.rejectTask(id, notes);
      set((state) => ({
        tasks: state.tasks.map((t) => (t.id === id ? task : t)),
        currentTask: task,
        loading: false,
      }));
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || 'Erreur lors du rejet de la tâche';
      set({ error: errorMessage, loading: false });
      throw error;
    }
  },

  /**
   * Supprimer une tâche
   */
  deleteTask: async (id) => {
    set({ loading: true, error: null });
    try {
      await tasksService.deleteTask(id);
      set((state) => ({
        tasks: state.tasks.filter((t) => t.id !== id),
        currentTask: state.currentTask?.id === id ? null : state.currentTask,
        loading: false,
      }));
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || 'Erreur lors de la suppression de la tâche';
      set({ error: errorMessage, loading: false });
      throw error;
    }
  },

  /**
   * Annuler une tâche
   */
  cancelTask: async (id) => {
    set({ loading: true, error: null });
    try {
      const task = await tasksService.cancelTask(id);
      set((state) => ({
        tasks: state.tasks.map((t) => (t.id === id ? task : t)),
        currentTask: task,
        loading: false,
      }));
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || 'Erreur lors de l\'annulation de la tâche';
      set({ error: errorMessage, loading: false });
      throw error;
    }
  },

  /**
   * Relancer une tâche FAILED ou CANCELLED
   */
  retryTask: async (id) => {
    set({ loading: true, error: null });
    try {
      const task = await tasksService.retryTask(id);
      set((state) => ({
        tasks: state.tasks.map((t) => (t.id === id ? task : t)),
        currentTask: task,
        loading: false,
      }));
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || 'Erreur lors de la relance de la tâche';
      set({ error: errorMessage, loading: false });
      throw error;
    }
  },

  /**
   * Forcer la génération immédiate
   */
  generateTask: async (id) => {
    set({ loading: true, error: null });
    try {
      const task = await tasksService.generateTask(id);
      set((state) => ({
        tasks: state.tasks.map((t) => (t.id === id ? task : t)),
        currentTask: task,
        loading: false,
      }));
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || 'Erreur lors de la génération de la tâche';
      set({ error: errorMessage, loading: false });
      throw error;
    }
  },

  /**
   * Activer une tâche (CREATED → READY)
   */
  activateTask: async (id) => {
    set({ loading: true, error: null });
    try {
      const task = await tasksService.activateTask(id);
      set((state) => ({
        tasks: state.tasks.map((t) => (t.id === id ? task : t)),
        currentTask: state.currentTask?.id === id ? task : state.currentTask,
        loading: false,
      }));
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || 'Erreur lors de l\'activation de la tâche';
      set({ error: errorMessage, loading: false });
      throw error;
    }
  },

  /**
   * Marquer une tâche comme terminée manuellement
   */
  completeTask: async (id) => {
    set({ loading: true, error: null });
    try {
      const task = await tasksService.completeTask(id);
      celebrateCompletion(task.title);
      set((state) => ({
        tasks: state.tasks.map((t) => (t.id === id ? task : t)),
        currentTask: state.currentTask?.id === id ? task : state.currentTask,
        loading: false,
      }));
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || 'Erreur lors de la complétion de la tâche';
      set({ error: errorMessage, loading: false });
      throw error;
    }
  },

  /**
   * Arrêter une génération en cours
   */
  stopGeneration: async (id) => {
    set({ loading: true, error: null });
    try {
      const task = await tasksService.stopGeneration(id);
      set((state) => ({
        tasks: state.tasks.map((t) => (t.id === id ? task : t)),
        currentTask: task,
        loading: false,
      }));
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || 'Erreur lors de l\'arrêt de la génération';
      set({ error: errorMessage, loading: false });
      throw error;
    }
  },

  /**
   * Récupérer les logs d'une tâche
   */
  fetchTaskLogs: async (id) => {
    set({ loading: true, error: null });
    try {
      const logs = await tasksService.getTaskLogs(id);
      set({ taskLogs: logs, loading: false });
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || 'Erreur lors du chargement des logs';
      set({ error: errorMessage, loading: false });
    }
  },

  /**
   * Définir les filtres
   */
  setFilters: (filters) => {
    set({ filters });
  },

  /**
   * Effacer la tâche courante
   */
  clearCurrentTask: () => {
    set({ currentTask: null });
  },

  /**
   * Effacer l'erreur
   */
  clearError: () => {
    set({ error: null });
  },
}));
