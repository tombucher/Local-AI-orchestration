/**
 * Constantes de l'application
 */

/**
 * Base de l'API. Vide (défaut) = chemin relatif `/api/v1`, servi par le proxy
 * Vite vers le backend : même origine, pas de CORS, et l'app fonctionne depuis
 * n'importe quel hôte (Tailscale, téléphone). VITE_API_URL force une origine.
 */
const apiOrigin = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '');
export const API_ORIGIN = apiOrigin;
export const API_BASE_URL = `${apiOrigin}/api/v1`;

export const API_ROUTES = {
  AUTH: {
    LOGIN: '/auth/login', 
    REGISTER: '/auth/register',
    ME: '/auth/me',
  },
  PROJECTS: '/projects',
  TASKS: '/tasks',
  TIME: '/time',
  ORCHESTRATOR: '/orchestrator',
  SETTINGS: '/settings',        // On l'ajoute pour la propreté
} as const;

export const STORAGE_KEYS = {
  TOKEN: 'auth_token',
} as const;

export const APP_NAME = 'Orchestrateur IA';
