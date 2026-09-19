/**
 * Store Zustand pour l'authentification
 * - Gestion état user/token
 * - Méthodes login, register, logout, checkAuth
 * - Persistance localStorage
 */

import { create } from 'zustand';
import { api } from '../services/api';
import { API_ROUTES, STORAGE_KEYS } from '../utils/constants';
import { User, RegisterRequest, TokenResponse } from '../types/auth.types';

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;

  // Actions
  login: (email: string, password: string) => Promise<void>;
  register: (data: RegisterRequest) => Promise<void>;
  logout: () => void;
  checkAuth: () => Promise<void>;
  clearError: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  token: localStorage.getItem(STORAGE_KEYS.TOKEN),
  isAuthenticated: false,
  isLoading: false,
  error: null,

  /**
   * Login : Authentification utilisateur
   * 1. POST /auth/login avec username (email) + password
   * 2. Récupérer access_token
   * 3. Sauvegarder dans localStorage
   * 4. GET /auth/me pour récupérer user
   */
  login: async (email: string, password: string) => {
    set({ isLoading: true, error: null });

    try {
      // POST login (JSON avec email/password)
      const { data: tokenData } = await api.post<TokenResponse>(
        API_ROUTES.AUTH.LOGIN,
        {
          email,
          password,
        }
      );

      const { access_token } = tokenData;

      // Sauvegarder token
      localStorage.setItem(STORAGE_KEYS.TOKEN, access_token);

      // Récupérer infos user
      const { data: userData } = await api.get<User>(API_ROUTES.AUTH.ME);

      set({
        user: userData,
        token: access_token,
        isAuthenticated: true,
        isLoading: false,
        error: null,
      });
    } catch (error: any) {
      // Gestion des erreurs de validation FastAPI (422)
      let errorMessage = 'Erreur de connexion';

      if (error.response?.data?.detail) {
        // Si detail est un array (erreur de validation FastAPI)
        if (Array.isArray(error.response.data.detail)) {
          errorMessage = error.response.data.detail
            .map((err: any) => err.msg || 'Erreur de validation')
            .join(', ');
        } else if (typeof error.response.data.detail === 'string') {
          errorMessage = error.response.data.detail;
        }
      }

      set({
        user: null,
        token: null,
        isAuthenticated: false,
        isLoading: false,
        error: errorMessage,
      });
      localStorage.removeItem(STORAGE_KEYS.TOKEN);
      throw error;
    }
  },

  /**
   * Register : Inscription nouvel utilisateur
   * 1. POST /auth/register
   * 2. Auto-login après succès
   */
  register: async (data: RegisterRequest) => {
    set({ isLoading: true, error: null });

    try {
      await api.post(API_ROUTES.AUTH.REGISTER, data);

      // Auto-login après inscription
      const { login } = useAuthStore.getState();
      await login(data.email, data.password);
    } catch (error: any) {
      // Gestion des erreurs de validation FastAPI (422)
      let errorMessage = 'Erreur lors de l\'inscription';

      if (error.response?.data?.detail) {
        // Si detail est un array (erreur de validation FastAPI)
        if (Array.isArray(error.response.data.detail)) {
          errorMessage = error.response.data.detail
            .map((err: any) => err.msg || 'Erreur de validation')
            .join(', ');
        } else if (typeof error.response.data.detail === 'string') {
          errorMessage = error.response.data.detail;
        }
      }

      set({
        isLoading: false,
        error: errorMessage,
      });
      throw error;
    }
  },

  /**
   * Logout : Déconnexion
   */
  logout: () => {
    localStorage.removeItem(STORAGE_KEYS.TOKEN);
    set({
      user: null,
      token: null,
      isAuthenticated: false,
      error: null,
    });
  },

  /**
   * CheckAuth : Vérifier si token valide au chargement app
   */
  checkAuth: async () => {
    const token = localStorage.getItem(STORAGE_KEYS.TOKEN);

    if (!token) {
      set({ isAuthenticated: false, user: null });
      return;
    }

    try {
      const { data: userData } = await api.get<User>(API_ROUTES.AUTH.ME);

      set({
        user: userData,
        token,
        isAuthenticated: true,
        error: null,
      });
    } catch (error) {
      // Token invalide ou expiré
      localStorage.removeItem(STORAGE_KEYS.TOKEN);
      set({
        user: null,
        token: null,
        isAuthenticated: false,
      });
    }
  },

  clearError: () => set({ error: null }),
}));
