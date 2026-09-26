/**
 * Notification du navigateur quand le briefing du jour est prêt.
 *
 * 100 % local : l'API Notification affiche une notification système depuis la
 * page elle-même, sans serveur de push (le Web Push passerait par les serveurs
 * d'Apple ou de Google). Contrepartie : un onglet de l'outil doit être ouvert,
 * même en arrière-plan.
 *
 * Désactivable ici (Paramètres) et dans les réglages du navigateur.
 */

import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../../services/api';
import { useAuthStore } from '../../stores/authStore';
import type { DailyReport } from '../../types/daily-report.types';

const CLE_ACTIVE = 'briefing-notification';
const CLE_DEJA_NOTIFIE = 'briefing-notifie';
const INTERVALLE_MS = 10 * 60 * 1000;

const lire = (cle: string): string | null => {
  try {
    return localStorage.getItem(cle);
  } catch {
    return null;
  }
};

const ecrire = (cle: string, valeur: string) => {
  try {
    localStorage.setItem(cle, valeur);
  } catch {
    // stockage indisponible (navigation privée) : on notifiera peut-être deux fois
  }
};

export const notificationsSupportees = () => typeof window !== 'undefined' && 'Notification' in window;

export const notificationBriefingActive = () =>
  notificationsSupportees() && Notification.permission === 'granted' && lire(CLE_ACTIVE) === 'on';

/** Active ou coupe la notification. Renvoie l'état obtenu (le navigateur peut refuser). */
export const reglerNotificationBriefing = async (activer: boolean): Promise<boolean> => {
  if (!activer || !notificationsSupportees()) {
    ecrire(CLE_ACTIVE, 'off');
    return false;
  }
  const permission =
    Notification.permission === 'granted' ? 'granted' : await Notification.requestPermission();
  const active = permission === 'granted';
  ecrire(CLE_ACTIVE, active ? 'on' : 'off');
  return active;
};

/** Date du jour au format AAAA-MM-JJ, dans le fuseau de la machine */
export const aujourdhui = () => new Date().toLocaleDateString('en-CA');

export const BriefingNotifier = () => {
  const { isAuthenticated } = useAuthStore();
  const navigate = useNavigate();

  useEffect(() => {
    if (!isAuthenticated) return;

    const verifier = async () => {
      if (!notificationBriefingActive()) return;
      try {
        // Prépare le briefing s'il manque (le Mac dormait à l'heure prévue…)
        await api.post('/reports/daily/ensure', null, { silentError: true });
        const { data } = await api.get<DailyReport | null>('/reports/daily/latest', { silentError: true });
        if (!data || data.date !== aujourdhui() || lire(CLE_DEJA_NOTIFIE) === String(data.id)) return;
        ecrire(CLE_DEJA_NOTIFIE, String(data.id));

        // Déjà sous les yeux : inutile de le notifier
        if (document.visibilityState === 'visible' && window.location.pathname === '/dashboard') return;

        const priorites = (data.top_priorities ?? []).slice(0, 3);
        const notification = new Notification('Le briefing du matin', {
          body: priorites.length ? priorites.map((p, i) => `${i + 1}. ${p}`).join('\n') : data.summary,
          icon: '/icon.svg',
          tag: 'briefing',
        });
        notification.onclick = () => {
          window.focus();
          navigate('/dashboard');
          notification.close();
        };
      } catch {
        // hors ligne ou session expirée : on réessaiera au prochain passage
      }
    };

    verifier();
    const timer = setInterval(verifier, INTERVALLE_MS);
    return () => clearInterval(timer);
  }, [isAuthenticated, navigate]);

  return null;
};

export default BriefingNotifier;
