/**
 * Service API pour le module d'idéation socratique
 */

import api from './api';
import { API_ORIGIN, STORAGE_KEYS } from '../utils/constants';
import type {
  IdeationConversation,
  IdeationStartRequest,
  IdeationStartResponse,
  IdeationCompleteResponse,
} from '../types/ideation.types';

export const ideationService = {
  /**
   * Démarre la phase d'idéation pour un projet
   */
  startIdeation: async (projectId: number): Promise<IdeationStartResponse> => {
    const request: IdeationStartRequest = { project_id: projectId };
    const response = await api.post<IdeationStartResponse>('/ideation/start', request);
    return response.data;
  },

  /**
   * Récupère l'historique de conversation d'un projet
   */
  getConversation: async (projectId: number): Promise<IdeationConversation> => {
    const response = await api.get<IdeationConversation>(`/ideation/conversation/${projectId}`);
    return response.data;
  },

  /**
   * Envoie un message utilisateur et stream la réponse de l'assistant
   * Utilise Server-Sent Events (SSE) pour le streaming
   *
   * @param projectId ID du projet
   * @param message Message utilisateur
   * @param onChunk Callback appelé pour chaque chunk de texte reçu
   * @param onComplete Callback appelé quand le streaming est terminé
   * @param onError Callback appelé en cas d'erreur
   */
  sendMessageStream: async (
    projectId: number,
    message: string,
    onChunk: (chunk: string) => void,
    onComplete: () => void,
    onError: (error: Error) => void
  ): Promise<void> => {
    try {
      const token = localStorage.getItem(STORAGE_KEYS.TOKEN);
      const baseURL = API_ORIGIN;

      const response = await fetch(`${baseURL}/api/v1/ideation/send-stream/${projectId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({ message }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('No response body');
      }

      const decoder = new TextDecoder();

      // Lire le stream chunk par chunk
      while (true) {
        const { done, value } = await reader.read();

        if (done) {
          onComplete();
          break;
        }

        // Décoder le chunk
        const text = decoder.decode(value, { stream: true });

        // Parser les lignes SSE (format: "data: <contenu>\n\n")
        const lines = text.split('\n');
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const content = line.slice(6); // Enlever "data: "

            // Vérifier si c'est le signal de fin
            if (content === '[DONE]') {
              onComplete();
              return;
            }

            // Envoyer le chunk au callback
            if (content.trim()) {
              onChunk(content);
            }
          }
        }
      }
    } catch (error) {
      console.error('Stream error:', error);
      onError(error instanceof Error ? error : new Error('Unknown error'));
    }
  },

  /**
   * Finalise la phase d'idéation et passe le projet en statut PLANNING
   */
  completeIdeation: async (projectId: number): Promise<IdeationCompleteResponse> => {
    const response = await api.post<IdeationCompleteResponse>(`/ideation/complete/${projectId}`);
    return response.data;
  },
};
