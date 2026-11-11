/**
 * Navbar : bandeau supérieur du « journal d'atelier »
 * - Marque en Fraunces + filet fort
 * - Chrono en cours, utilisateur, déconnexion
 * - Sous lg, la barre latérale disparaît : le bouton ☰ ouvre le sommaire en
 *   tiroir (il n'ouvrait rien, l'app était sans navigation sur téléphone)
 */

import { useEffect, useState } from 'react';
import { LogOut, Menu, X } from 'lucide-react';
import { Link, useLocation } from 'react-router-dom';
import { useAuthStore } from '../../stores/authStore';
import { APP_NAME } from '../../utils/constants';
import { TimerWidget } from '../TimerWidget';
import { navItems } from './Sidebar';

export const Navbar = () => {
  const { user, logout } = useAuthStore();
  const location = useLocation();
  const [sommaire, setSommaire] = useState(false);

  // Changer de page referme le tiroir
  useEffect(() => setSommaire(false), [location.pathname]);

  return (
    <nav className="bg-paper border-b-2 border-ink relative">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Marque */}
          <div className="flex items-center space-x-3">
            <button
              onClick={() => setSommaire((v) => !v)}
              aria-label={sommaire ? 'Fermer le sommaire' : 'Ouvrir le sommaire'}
              aria-expanded={sommaire}
              className="lg:hidden p-2 text-ink-soft hover:bg-paper-warm"
            >
              {sommaire ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
            </button>
            <Link to="/dashboard" className="flex items-baseline gap-2">
              <h1 className="font-display text-2xl font-semibold text-ink tracking-tight">
                {APP_NAME}
              </h1>
              <span className="hidden sm:block kicker">journal d'atelier</span>
            </Link>
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
                onClick={logout}
                className="flex items-center space-x-2 px-3 py-2 text-sm font-medium text-ink-soft hover:bg-paper-warm transition-colors"
              >
                <LogOut className="w-4 h-4" />
                <span className="hidden sm:inline">Déconnexion</span>
              </button>
            </div>
          )}
        </div>
      </div>

      {sommaire && (
        <div className="lg:hidden absolute inset-x-0 top-full z-30 bg-paper border-b-2 border-ink shadow-card">
          <p className="kicker px-6 pt-4 pb-2">Sommaire</p>
          {navItems.map((item) => {
            const actif = location.pathname.startsWith(item.href);
            const Icone = item.icon;
            return (
              <Link
                key={item.href}
                to={item.href}
                className={`flex items-center gap-3 px-6 py-3 text-base border-l-2 ${
                  actif ? 'border-accent text-ink bg-paper-warm' : 'border-transparent text-ink-soft'
                }`}
              >
                <Icone className="w-5 h-5" />
                {item.name}
              </Link>
            );
          })}
          <div className="h-2" />
        </div>
      )}
    </nav>
  );
};
