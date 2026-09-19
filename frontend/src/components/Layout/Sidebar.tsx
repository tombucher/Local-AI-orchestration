/**
 * Sidebar : sommaire du journal
 * - Rubriques numérotées façon sommaire de revue
 * - Mobile responsive (cachée < lg)
 */

import { Home, FolderKanban, CheckSquare, Settings } from 'lucide-react';
import { Link, useLocation } from 'react-router-dom';

const navItems = [
  { name: 'Le journal', href: '/dashboard', icon: Home },
  { name: 'Projets', href: '/projects', icon: FolderKanban },
  { name: 'Tâches', href: '/tasks', icon: CheckSquare },
  { name: 'Paramètres', href: '/settings', icon: Settings },
];

export const Sidebar = () => {
  const location = useLocation();

  return (
    <aside className="hidden lg:flex lg:flex-col w-60 bg-paper border-r border-ink-line">
      <nav className="flex-1 px-4 py-8 space-y-1">
        <p className="kicker px-3 mb-3">Sommaire</p>
        {navItems.map((item, index) => {
          const isActive = location.pathname.startsWith(item.href);
          const Icon = item.icon;

          return (
            <Link
              key={item.name}
              to={item.href}
              className={`
                group flex items-center gap-3 px-3 py-2.5 text-sm font-medium transition-colors border-l-2
                ${
                  isActive
                    ? 'border-accent text-ink bg-paper-warm'
                    : 'border-transparent text-ink-soft hover:text-ink hover:bg-paper-warm'
                }
              `}
            >
              <span className={`font-mono text-[10px] ${isActive ? 'text-accent' : 'text-ink-faint'}`}>
                {String(index + 1).padStart(2, '0')}
              </span>
              <Icon className="w-4 h-4" />
              <span>{item.name}</span>
            </Link>
          );
        })}
      </nav>

      <div className="px-7 py-4 border-t border-ink-line">
        <p className="text-[11px] text-ink-faint font-mono">
          IA locale · Ollama
        </p>
      </div>
    </aside>
  );
};
