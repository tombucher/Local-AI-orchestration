/**
 * ProtectedRoute : Route protégée par authentification
 * - Vérifie si user authentifié via store Zustand
 * - Fallback : vérifie localStorage si le store est réinitialisé (ex: Vite HMR reload)
 * - Redirect /login si non authentifié ET pas de token
 */

import { Navigate } from 'react-router-dom';
import { useAuthStore } from '../../stores/authStore';
import { STORAGE_KEYS } from '../../utils/constants';
import Loader from '../ui/Loader';

interface ProtectedRouteProps {
  children: React.ReactNode;
}

export const ProtectedRoute = ({ children }: ProtectedRouteProps) => {
  const { isAuthenticated } = useAuthStore();

  if (!isAuthenticated) {
    // Vérifier localStorage avant de rediriger vers login
    // Cas: Vite HMR reload réinitialise le store Zustand mais le token JWT persiste
    const token = localStorage.getItem(STORAGE_KEYS.TOKEN);
    if (token) {
      // Token existe → checkAuth() est en cours dans App.tsx useEffect
      // Afficher un loader temporaire au lieu de rediriger vers /login
      return (
        <div className="flex items-center justify-center min-h-screen">
          <Loader size="lg" />
        </div>
      );
    }
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
};
