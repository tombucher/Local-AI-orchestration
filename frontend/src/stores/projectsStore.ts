/**
 * Store Zustand pour la gestion des projets
 */

import { create } from 'zustand';
import { Project, ProjectCreate, ProjectUpdate, ProjectStats } from '../types/project.types';
import { projectsService } from '../services/projects';

interface ProjectsState {
  projects: Project[];
  currentProject: Project | null;
  currentProjectStats: ProjectStats | null;
  loading: boolean;
  error: string | null;

  // Actions
  fetchProjects: (filters?: { project_type?: string; search?: string }) => Promise<void>;
  fetchProject: (id: number) => Promise<void>;
  fetchProjectStats: (id: number) => Promise<void>;
  createProject: (data: ProjectCreate) => Promise<Project>;
  updateProject: (id: number, data: ProjectUpdate) => Promise<void>;
  deleteProject: (id: number) => Promise<void>;
  clearError: () => void;
  setCurrentProject: (project: Project | null) => void;
}

export const useProjectsStore = create<ProjectsState>((set) => ({
  projects: [],
  currentProject: null,
  currentProjectStats: null,
  loading: false,
  error: null,

  /**
   * Récupérer tous les projets
   */
  fetchProjects: async (filters) => {
    set({ loading: true, error: null });
    try {
      const data = await projectsService.getProjects(filters);
      // Ensure we always set an array
      const projects = Array.isArray(data) ? data : [];
      set({ projects, loading: false });
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || 'Erreur lors du chargement des projets';
      set({ error: errorMessage, loading: false, projects: [] });
    }
  },

  /**
   * Récupérer un projet spécifique
   */
  fetchProject: async (id) => {
    set({ loading: true, error: null });
    try {
      const project = await projectsService.getProject(id);
      set({ currentProject: project, loading: false });
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || 'Erreur lors du chargement du projet';
      set({ error: errorMessage, loading: false });
    }
  },

  /**
   * Récupérer les statistiques d'un projet
   */
  fetchProjectStats: async (id) => {
    set({ loading: true, error: null });
    try {
      const stats = await projectsService.getProjectStats(id);
      set({ currentProjectStats: stats, loading: false });
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || 'Erreur lors du chargement des statistiques';
      set({ error: errorMessage, loading: false });
    }
  },

  /**
   * Créer un nouveau projet
   */
  createProject: async (data) => {
    set({ loading: true, error: null });
    try {
      const project = await projectsService.createProject(data);
      set((state) => {
        const currentProjects = Array.isArray(state.projects) ? state.projects : [];
        return {
          projects: [...currentProjects, project],
          loading: false,
        };
      });
      return project;
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || 'Erreur lors de la création du projet';
      set({ error: errorMessage, loading: false });
      throw error;
    }
  },

  /**
   * Mettre à jour un projet
   */
  updateProject: async (id, data) => {
    set({ loading: true, error: null });
    try {
      const updated = await projectsService.updateProject(id, data);
      set((state) => {
        const currentProjects = Array.isArray(state.projects) ? state.projects : [];
        return {
          projects: currentProjects.map((p) => (p.id === id ? updated : p)),
          currentProject: state.currentProject?.id === id ? updated : state.currentProject,
          loading: false,
        };
      });
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || 'Erreur lors de la mise à jour du projet';
      set({ error: errorMessage, loading: false });
      throw error;
    }
  },

  /**
   * Supprimer un projet
   */
  deleteProject: async (id) => {
    set({ loading: true, error: null });
    try {
      await projectsService.deleteProject(id);
      set((state) => {
        const currentProjects = Array.isArray(state.projects) ? state.projects : [];
        return {
          projects: currentProjects.filter((p) => p.id !== id),
          currentProject: state.currentProject?.id === id ? null : state.currentProject,
          loading: false,
        };
      });
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || 'Erreur lors de la suppression du projet';
      set({ error: errorMessage, loading: false });
      throw error;
    }
  },

  /**
   * Réinitialiser l'erreur
   */
  clearError: () => set({ error: null }),

  /**
   * Définir le projet courant
   */
  setCurrentProject: (project) => set({ currentProject: project }),
}));
