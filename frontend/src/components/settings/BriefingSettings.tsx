/**
 * Réglage de la notification du briefing du matin (navigateur, 100 % local).
 */

import { useState } from 'react';
import { Bell, BellOff } from 'lucide-react';
import {
  notificationBriefingActive,
  notificationsSupportees,
  reglerNotificationBriefing,
} from '../Layout/BriefingNotifier';

export const BriefingSettings = () => {
  const [active, setActive] = useState(notificationBriefingActive());
  const [refusee, setRefusee] = useState(
    notificationsSupportees() && Notification.permission === 'denied',
  );

  const basculer = async () => {
    const resultat = await reglerNotificationBriefing(!active);
    setActive(resultat);
    setRefusee(!resultat && !active && notificationsSupportees() && Notification.permission === 'denied');
  };

  return (
    <div className="bg-paper-card shadow-card border border-ink-line p-6 mb-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex items-start gap-3 min-w-0">
          {active ? (
            <Bell className="w-5 h-5 text-accent mt-1 shrink-0" />
          ) : (
            <BellOff className="w-5 h-5 text-ink-faint mt-1 shrink-0" />
          )}
          <div className="min-w-0">
            <h2 className="font-display text-xl text-ink">Briefing du matin</h2>
            <p className="text-sm text-ink-soft mt-1 max-w-2xl">
              Chaque matin à 8 h, l'outil prépare le résumé de ce que tu as à faire. Il t'attend
              en tête du journal ; s'il a été manqué (Mac en veille), il se prépare dès que tu
              ouvres l'outil. En option, une notification te prévient quand il est prêt.
            </p>
            <p className="text-xs text-ink-faint mt-2 max-w-2xl">
              La notification reste sur ta machine : elle ne s'affiche que si un onglet de
              l'outil est ouvert, même en arrière-plan. Tu peux aussi la couper dans les
              réglages de ton navigateur.
            </p>
          </div>
        </div>
        {notificationsSupportees() ? (
          <button
            onClick={basculer}
            className={`inline-flex items-center gap-2 px-4 py-2 text-sm font-medium transition-colors ${
              active
                ? 'border border-ink-line text-ink hover:border-accent hover:text-accent'
                : 'bg-accent text-white hover:opacity-90'
            }`}
          >
            {active ? 'Couper la notification' : 'Activer la notification'}
          </button>
        ) : (
          <p className="text-sm text-ink-faint">Ce navigateur ne gère pas les notifications.</p>
        )}
      </div>
      {refusee && (
        <p className="mt-3 text-sm text-warning">
          Le navigateur a bloqué les notifications pour ce site : autorise-les dans ses
          réglages, puis réessaie.
        </p>
      )}
    </div>
  );
};

export default BriefingSettings;
