/**
 * Client API Axios configuré
 * - Intercepteur pour ajouter JWT automatiquement
 * - Gestion des erreurs 401 (redirect login)
 * - Toast automatique sur les autres erreurs (opt-out via config.silentError)
 */

import axios, { AxiosError } from 'axios';
import toast from 'react-hot-toast';
import { API_BASE_URL, STORAGE_KEYS } from '../utils/constants';

declare module 'axios' {
  export interface AxiosRequestConfig {
    /** Désactive le toast d'erreur automatique pour cette requête */
    silentError?: boolean;
  }
}

// Instance Axios configurée
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Intercepteur Request : Ajouter JWT si disponible
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem(STORAGE_KEYS.TOKEN);
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

/**
 * Extrait un message lisible d'une erreur FastAPI (detail string, message, ou erreurs de validation 422).
 * Accepte `unknown` : c'est le type d'un `catch` en TypeScript strict, et cette
 * fonction est justement faite pour y être appelée directement.
 */
function extractErrorMessage(error: unknown): string {
  const err = (error ?? {}) as AxiosError;
  const data = err.response?.data as any;
  if (data) {
    if (typeof data.detail === 'string') return data.detail;
    if (typeof data.message === 'string') return data.message;
    if (Array.isArray(data.detail)) {
      return data.detail
        .map((e: any) => `${(e.loc || []).join(' → ')}: ${e.msg}`)
        .join(' ; ');
    }
    if (data.details?.errors?.length) {
      return data.details.errors
        .map((e: any) => `${e.field}: ${e.message}`)
        .join(' ; ');
    }
  }
  if (err.code === 'ERR_NETWORK') {
    return 'Serveur injoignable — vérifiez que le backend tourne.';
  }
  return err.message || 'Une erreur est survenue';
}

// Intercepteur Response : 401 → login, autres erreurs → toast
api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    // Si 401 Unauthorized, supprimer token et rediriger vers login
    if (error.response?.status === 401) {
      localStorage.removeItem(STORAGE_KEYS.TOKEN);

      // Éviter boucle infinie si déjà sur /login
      if (window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
      return Promise.reject(error);
    }

    if (!error.config?.silentError) {
      toast.error(extractErrorMessage(error), { id: `api-error-${error.config?.url}` });
    }
    return Promise.reject(error);
  }
);

export { api, extractErrorMessage };
export default api;
