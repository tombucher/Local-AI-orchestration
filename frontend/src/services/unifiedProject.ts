/**
 * Service pour la création de projet en mode dialogue unifié
 */
import { api } from './api';
import { STORAGE_KEYS } from '../utils/constants';
import {
  ProjectFinalizationPreview,
  FinalizeValidationRequest,
  ProjectFinalizeResponse
} from '../types/project.types';

export interface StartProjectChatResponse {
  project_id: number;
  conversation_id: number;
  welcome_message: string;
  initial_question: string;
}

export interface TaskGenerated {
  id: number;
  title: string;
  description: string;
  task_type: string;
  priority: string;
  estimated_duration?: number;
}

export interface FinalizeProjectResponse {
  project_id: number;
  project_name: string;
  project_description: string;
  tasks_count: number;
  tasks: TaskGenerated[];
  message: string;
}

class UnifiedProjectService {
  /**
   * Démarre un nouveau projet en mode dialogue
   */
  async startProjectChat(): Promise<StartProjectChatResponse> {
    const token = localStorage.getItem(STORAGE_KEYS.TOKEN);

    const response = await api.post('/projects/start-chat', {}, {
      headers: {
        Authorization: `Bearer ${token}`
      }
    });

    return response.data;
  }

  /**
   * Finalise un projet et génère les tâches automatiquement
   */
  async finalizeProject(projectId: number): Promise<FinalizeProjectResponse> {
    const token = localStorage.getItem(STORAGE_KEYS.TOKEN);

    const response = await api.post('/projects/finalize',
      { project_id: projectId },
      {
        headers: {
          Authorization: `Bearer ${token}`
        }
      }
    );

    return response.data;
  }

  /**
   * Génère un aperçu de finalisation sans persister en base
   * @param projectId - ID du projet en phase IDEATION
   */
  async previewFinalization(projectId: number): Promise<ProjectFinalizationPreview> {
    const token = localStorage.getItem(STORAGE_KEYS.TOKEN);

    const response = await api.post('/projects/preview-finalization',
      { project_id: projectId },
      {
        headers: {
          Authorization: `Bearer ${token}`
        }
      }
    );

    return response.data;
  }

  /**
   * Finalise un projet avec validation utilisateur
   * @param data - Données validées par l'utilisateur (nom, description, tâches approuvées, veille)
   */
  async finalizeWithValidation(data: FinalizeValidationRequest): Promise<ProjectFinalizeResponse> {
    const token = localStorage.getItem(STORAGE_KEYS.TOKEN);

    const response = await api.post('/projects/finalize-with-validation',
      data,
      {
        headers: {
          Authorization: `Bearer ${token}`
        }
      }
    );

    return response.data;
  }
}

export const unifiedProjectService = new UnifiedProjectService();
