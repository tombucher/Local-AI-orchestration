/**
 * Réglage de la notification du briefing du matin (navigateur, 100 % local).
 */

import { useEffect, useState } from 'react';
import { Bell, BellOff } from 'lucide-react';
import {
  notificationBriefingActive,
  notificationsSupportees,
  reglerNotificationBriefing,
} from '../Layout/BriefingNotifier';

type Navigateur = 'safari' | 'firefox' | 'chromium';

const detecterNavigateur = (): Navigateur => {
  const ua = navigator.userAgent;
  if (/Firefox\//.test(ua)) return 'firefox';
  if (/Safari\//.test(ua) && !/(Chrome|Chromium|CriOS|Edg)\//.test(ua)) return 'safari';
  return 'chromium'; // Chrome, Arc, Brave, Edge…
};

/**
 * Une permission refusée ne peut plus être redemandée par la page : seul le
 * navigateur peut la rétablir. On donne donc le chemin exact, selon le navigateur.
 */
const DebloquerNotifications = () => {
  const site = window.location.host;
  const etapes: Record<Navigateur, string[]> = {
    safari: [
      'Menu Safari → Réglages… → onglet « Sites web »',
      'Dans la colonne de gauche : « Notifications »',
      `En face de ${site} : choisir « Autoriser »`,
    ],
    chromium: [
      "Clique sur l'icône à gauche de l'adresse (réglages du site)",
      '« Notifications » → « Autoriser »',
      'Recharge la page',
    ],
    firefox: [
      "Clique sur l'icône à gauche de l'adresse (autorisations)",
      '« Envoyer des notifications » : clique sur la croix pour retirer le blocage',
      'Recharge la page',
    ],
  };
  return (
    <div className="mt-4 border border-warning bg-warning/10 p-4 text-sm">
      <p className="text-ink font-medium">
        Tu as refusé les notifications pour {site} : le navigateur ne laisse plus l'outil
        les redemander. Pour les rétablir :
      </p>
      <ol className="mt-2 list-decimal pl-5 space-y-1 text-ink-soft">
        {etapes[detecterNavigateur()].map((etape) => (
          <li key={etape}>{etape}</li>
        ))}
        <li>Reviens ici et clique sur « Activer la notification ».</li>
      </ol>
      <p className="mt-2 text-xs text-ink-faint">
        Si rien ne s'affiche ensuite : Réglages Système du Mac → Notifications → ton navigateur
        → « Autoriser les notifications ».
      </p>
    </div>
  );
};

export const BriefingSettings = () => {
  const [active, setActive] = useState(notificationBriefingActive());
  const [refusee, setRefusee] = useState(
    notificationsSupportees() && Notification.permission === 'denied',
  );

  // Au retour sur l'onglet (après être passé par les réglages du navigateur)
  useEffect(() => {
    if (!notificationsSupportees()) return;
    const reverifier = () => setRefusee(Notification.permission === 'denied');
    window.addEventListener('focus', reverifier);
    document.addEventListener('visibilitychange', reverifier);
    return () => {
      window.removeEventListener('focus', reverifier);
      document.removeEventListener('visibilitychange', reverifier);
    };
  }, []);

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
      {refusee && <DebloquerNotifications />}
    </div>
  );
};

export default BriefingSettings;
