/**
 * État du service de génération — registre éditorial :
 * lignes fines, compteurs tabulaires, point d'activité.
 */

import { useState } from 'react';
import { Activity } from 'lucide-react';
import { tasksService } from '../services/tasks';
import { usePolling } from '../hooks/usePolling';
import Loader from './ui/Loader';

interface ServiceStats {
  ready: number;
  generating: number;
  manual_review: number;
  completed: number;
  cancelled: number;
}

const Row = ({ label, value, tone, pulse }: { label: string; value: number; tone: string; pulse?: boolean }) => (
  <div className="flex items-center justify-between py-2 border-b border-ink-line/60 last:border-b-0">
    <span className="flex items-center gap-2 text-sm text-ink-soft">
      <span className={`w-1.5 h-1.5 rounded-full ${tone} ${pulse ? 'animate-pulse' : ''}`} />
      {label}
    </span>
    <span className="font-mono text-sm font-semibold text-ink figures">{value}</span>
  </div>
);

export const ServiceStatus = () => {
  const [stats, setStats] = useState<ServiceStats | null>(null);
  const [loading, setLoading] = useState(true);

  // Rafraîchi toutes les 30 s, en pause quand l'onglet est caché
  usePolling(async () => {
    try {
      const data = await tasksService.getServiceStats();
      setStats(data);
    } catch {
      // Silencieux : un raté de polling ne doit pas spammer l'utilisateur
    } finally {
      setLoading(false);
    }
  }, 30000);

  return (
    <div className="bg-paper-card border border-ink-line shadow-card p-5">
      <div className="flex items-center gap-2 mb-3 pb-2 rule">
        <Activity className="w-4 h-4 text-ink-soft" />
        <h2 className="font-display text-lg text-ink">L'atelier tourne</h2>
        {stats && stats.generating > 0 && (
          <span className="ml-auto kicker text-warning">en cours</span>
        )}
      </div>

      {loading || !stats ? (
        <div className="py-4 flex justify-center">
          <Loader size="sm" label="Lecture du registre…" />
        </div>
      ) : (
        <div>
          {stats.generating > 0 && (
            <Row label="En génération" value={stats.generating} tone="bg-warning" pulse />
          )}
          {stats.manual_review > 0 && (
            <Row label="En attente de validation" value={stats.manual_review} tone="bg-highlight" pulse />
          )}
          {stats.ready > 0 && (
            <Row label="En file d'attente" value={stats.ready} tone="bg-info" />
          )}
          <Row label="Terminées" value={stats.completed} tone="bg-success" />

          {stats.generating === 0 && stats.manual_review === 0 && stats.ready === 0 && (
            <p className="text-xs text-ink-faint mt-3">Rien en cours — l'atelier est calme.</p>
          )}
        </div>
      )}
    </div>
  );
};
