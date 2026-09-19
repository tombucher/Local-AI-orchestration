/**
 * Navbar : bandeau supérieur du « journal d'atelier »
 * - Marque en Fraunces + filet fort
 * - Chrono en cours, utilisateur, déconnexion
 */

import { LogOut, Menu } from 'lucide-react';
import { useAuthStore } from '../../stores/authStore';
import { APP_NAME } from '../../utils/constants';
import { TimerWidget } from '../TimerWidget';

export const Navbar = () => {
  const { user, logout } = useAuthStore();

  const handleLogout = () => {
    logout();
  };

  return (
    <nav className="bg-paper border-b-2 border-ink">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Marque */}
          <div className="flex items-center space-x-3">
            <button className="lg:hidden p-2 text-ink-soft hover:bg-paper-warm">
              <Menu className="w-6 h-6" />
            </button>
            <div className="flex items-baseline gap-2">
              <h1 className="font-display text-2xl font-semibold text-ink tracking-tight">
                {APP_NAME}
              </h1>
              <span className="hidden sm:block kicker">journal d'atelier</span>
            </div>
          </div>

          {/* Chrono + User + Logout */}
          {user && (
            <div className="flex items-center space-x-4">
              <TimerWidget />
              <div className="hidden md:block text-right">
                <p className="text-sm font-medium text-ink">
                  {user.full_name}
                </p>
                <p className="text-xs text-ink-faint">{user.email}</p>
              </div>

              <button
                onClick={handleLogout}
                className="flex items-center space-x-2 px-3 py-2 text-sm font-medium text-ink-soft hover:bg-paper-warm transition-colors"
              >
                <LogOut className="w-4 h-4" />
                <span className="hidden sm:inline">Déconnexion</span>
              </button>
            </div>
          )}
        </div>
      </div>
    </nav>
  );
};
