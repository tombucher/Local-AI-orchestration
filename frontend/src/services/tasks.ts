/**
 * Service API pour la gestion des tâches
 */

import api from './api';
import type { Task, TaskCreate, TaskUpdate, TaskFilters, TaskLog, VeilleResult, VeilleResultList, VeilleRefinePayload } from '../types/task.types';

export const tasksService = {
  /**
   * Récupérer toutes les tâches avec filtres optionnels
   */
  getTasks: async (filters?: TaskFilters): Promise<Task[]> => {
    const params = new URLSearchParams();
    if (filters?.project_id) params.append('project_id', filters.project_id.toString());
    if (filters?.status) params.append('status', filters.status);
    if (filters?.priority) params.append('priority', filters.priority);
    if (filters?.limit) params.append('limit', filters.limit.toString());
    if (filters?.offset) params.append('offset', filters.offset.toString());

    const response = await api.get<{ items: Task[]; total: number; page: number; page_size: number }>(`/tasks/?${params.toString()}`);
    // Le backend retourne un objet paginé, on extrait le tableau
    return response.data.items || [];
  },

  /**
   * Récupérer une tâche par ID
   */
  getTask: async (id: number): Promise<Task> => {
    const response = await api.get<Task>(`/tasks/${id}`);
    return response.data;
  },

  /**
   * Créer une nouvelle tâche
   */
  createTask: async (data: TaskCreate): Promise<Task> => {
    const response = await api.post<Task>('/tasks/', data);
    return response.data;
  },

  /**
   * Mettre à jour une tâche
   */
  updateTask: async (id: number, data: TaskUpdate): Promise<Task> => {
    const response = await api.put<Task>(`/tasks/${id}`, data);
    return response.data;
  },

  /**
   * Valider le code généré (avec code modifié en option)
   */
  validateTask: async (id: number, approved: boolean, notes?: string, editedCode?: string): Promise<Task> => {
    const response = await api.post<Task>(`/tasks/${id}/validate`, {
      approved,
      notes,
      edited_code: editedCode,
    });
    return response.data;
  },

  /**
   * Rejeter le code généré
   */
  rejectTask: async (id: number, notes: string): Promise<Task> => {
    const response = await api.post<Task>(`/tasks/${id}/reject`, {
      approved: false,
      notes,
    });
    return response.data;
  },

  /**
   * Annuler une tâche
   */
  cancelTask: async (id: number): Promise<Task> => {
    const response = await api.post<Task>(`/tasks/${id}/cancel`);
    return response.data;
  },

  /**
   * Forcer la génération immédiate (bypass queue) — accepte CREATED ou READY
   */
  generateTask: async (id: number): Promise<Task> => {
    const response = await api.post<Task>(`/tasks/${id}/generate`);
    return response.data;
  },

  /**
   * Activer une tâche : CREATED → READY (la met dans la file du scheduler)
   */
  activateTask: async (id: number): Promise<Task> => {
    const response = await api.post<Task>(`/tasks/${id}/activate`);
    return response.data;
  },

  /**
   * Marquer manuellement une tâche comme terminée
   */
  completeTask: async (id: number): Promise<Task> => {
    const response = await api.post<Task>(`/tasks/${id}/complete`);
    return response.data;
  },

  /**
   * Relancer une tâche FAILED ou CANCELLED → READY
   */
  retryTask: async (id: number): Promise<Task> => {
    const response = await api.post<Task>(`/tasks/${id}/retry`);
    return response.data;
  },

  /**
   * Arrêter une génération en cours
   */
  stopGeneration: async (id: number): Promise<Task> => {
    const response = await api.post<Task>(`/tasks/${id}/stop`);
    return response.data;
  },

  /**
   * Récupérer l'historique des logs d'une tâche
   */
  getTaskLogs: async (id: number): Promise<TaskLog[]> => {
    const response = await api.get<TaskLog[]>(`/tasks/${id}/logs`);
    return response.data;
  },

  /**
   * Supprimer une tâche
   */
  deleteTask: async (id: number): Promise<void> => {
    await api.delete(`/tasks/${id}`);
  },

  /**
   * Récupérer les résultats de veille associés à une tâche
   */
  getVeilleResults: async (id: number): Promise<VeilleResultList> => {
    const response = await api.get<VeilleResultList>(`/tasks/${id}/veille-results`);
    return response.data;
  },

  /**
   * Mettre à jour un résultat de veille (épingler, écarter, noter)
   */
  updateVeilleResult: async (
    resultId: number,
    update: { status?: string; user_notes?: string; user_rating?: number }
  ): Promise<VeilleResult> => {
    const response = await api.put<VeilleResult>(`/tasks/veille-results/${resultId}`, update);
    return response.data;
  },

  /**
   * Relancer immédiatement la veille du topic lié (nouvelle occurrence READY)
   */
  rescanVeille: async (id: number): Promise<{ status: string; task_id: number }> => {
    const response = await api.post(`/tasks/${id}/veille-rescan`);
    return response.data;
  },

  /**
   * Affiner les paramètres de veille pour les prochaines occurrences
   */
  refineVeille: async (id: number, refinement: VeilleRefinePayload): Promise<void> => {
    await api.put(`/tasks/${id}/veille-refine`, refinement);
  },

  /**
   * Récupérer les statistiques du service (tâches en cours, en attente, etc.)
   */
  getServiceStats: async (): Promise<{
    ready: number;
    generating: number;
    manual_review: number;
    completed: number;
    cancelled: number;
  }> => {
    // silentError : appelé en polling, un raté ne doit pas toaster
    const response = await api.get('/tasks/stats/service', { silentError: true });
    return response.data;
  },
};
