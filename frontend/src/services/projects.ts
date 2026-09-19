/**
 * Service API pour la gestion des projets
 */

import api from './api';
import { Project, ProjectCreate, ProjectUpdate, ProjectStats } from '../types/project.types';

export const projectsService = {
  /**
   * Récupérer tous les projets avec filtres optionnels
   */
  getProjects: async (filters?: {
    type?: string;
    search?: string;
  }): Promise<Project[]> => {
    const params = new URLSearchParams();
    if (filters?.type) params.append('type', filters.type);
    if (filters?.search) params.append('search', filters.search);

    const response = await api.get<{ items: Project[]; total: number; page: number; page_size: number }>(`/projects/?${params}`);
    // Le backend retourne un objet avec items, on extrait le tableau
    return response.data.items || [];
  },

  /**
   * Récupérer un projet par ID
   */
  getProject: async (id: number): Promise<Project> => {
    const response = await api.get<Project>(`/projects/${id}`);
    return response.data;
  },

  /**
   * Créer un nouveau projet
   */
  createProject: async (data: ProjectCreate): Promise<Project> => {
    const response = await api.post<Project>('/projects/', data);
    return response.data;
  },

  /**
   * Mettre à jour un projet
   */
  updateProject: async (id: number, data: ProjectUpdate): Promise<Project> => {
    const response = await api.put<Project>(`/projects/${id}`, data);
    return response.data;
  },

  /**
   * Supprimer un projet
   */
  deleteProject: async (id: number): Promise<void> => {
    await api.delete(`/projects/${id}`);
  },

  /**
   * Récupérer les statistiques d'un projet
   */
  getProjectStats: async (id: number): Promise<ProjectStats> => {
    const response = await api.get<ProjectStats>(`/projects/${id}/stats`);
    return response.data;
  },
};
