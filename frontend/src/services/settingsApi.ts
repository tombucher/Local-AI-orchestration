/**
 * API Settings
 * - Récupère les modèles Ollama disponibles
 * - Récupère et met à jour les paramètres utilisateur
 */

import api from './api';
import {
  FeedCheckResult, OllamaModel, RssFeed, RssFeedCreate, RssFeedUpdate,
  UserSettings, UserSettingsUpdate,
} from '../types/settings';

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

export const feedsApi = {
  /** Flux enregistrés par l'utilisateur */
  list: async (): Promise<RssFeed[]> => {
    const response = await api.get<RssFeed[]>('/settings/feeds');
    return response.data;
  },

  /** Vérifie un flux sans l'enregistrer (aperçu avant ajout) */
  preview: async (url: string): Promise<FeedCheckResult> => {
    // silentError : l'aperçu affiche lui-même le diagnostic dans le formulaire
    const response = await api.post<FeedCheckResult>('/settings/feeds/preview', { url }, { silentError: true });
    return response.data;
  },

  add: async (payload: RssFeedCreate): Promise<RssFeed> => {
    const response = await api.post<RssFeed>('/settings/feeds', payload);
    return response.data;
  },

  update: async (id: number, payload: RssFeedUpdate): Promise<RssFeed> => {
    const response = await api.patch<RssFeed>(`/settings/feeds/${id}`, payload);
    return response.data;
  },

  /** Re-vérifie un flux : les sources meurent sans prévenir */
  check: async (id: number): Promise<RssFeed> => {
    const response = await api.post<RssFeed>(`/settings/feeds/${id}/check`);
    return response.data;
  },

  remove: async (id: number): Promise<void> => {
    await api.delete(`/settings/feeds/${id}`);
  },
};
