/**
 * API Settings
 * - Récupère les modèles Ollama disponibles
 * - Récupère et met à jour les paramètres utilisateur
 */

import api from './api';
import { OllamaModel, UserSettings, UserSettingsUpdate } from '../types/settings';

export const settingsApi = {
  /**
   * Liste tous les modèles Ollama disponibles
   */
  getOllamaModels: async (): Promise<OllamaModel[]> => {
    const response = await api.get<OllamaModel[]>('/settings/ollama-models');
    return response.data;
  },

  /**
   * Récupère les paramètres de l'utilisateur connecté
   */
  getUserSettings: async (): Promise<UserSettings> => {
    const response = await api.get<UserSettings>('/settings');
    return response.data;
  },

  /**
   * Met à jour les paramètres de l'utilisateur
   */
  updateUserSettings: async (settings: UserSettingsUpdate): Promise<UserSettings> => {
    const response = await api.put<UserSettings>('/settings', settings);
    return response.data;
  },
};
