/**
 * Widget chrono affiché dans la Navbar.
 * - Affiche le temps écoulé du timer en cours (tick local 1s)
 * - Bouton stop
 * - Se synchronise avec le backend au montage
 */

import { useEffect } from 'react';
import { Square } from 'lucide-react';
import toast from 'react-hot-toast';
import { useTimerStore } from '../stores/timerStore';

function formatElapsed(totalSeconds: number): string {
  const h = Math.floor(totalSeconds / 3600);
  const m = Math.floor((totalSeconds % 3600) / 60);
  const s = totalSeconds % 60;
  if (h > 0) return `${h}h ${String(m).padStart(2, '0')}m`;
  return `${m}:${String(s).padStart(2, '0')}`;
}

export const TimerWidget = () => {
  const { currentTimer, elapsedSeconds, fetchCurrentTimer, stopTimer, updateElapsedSeconds } =
    useTimerStore();

  useEffect(() => {
    fetchCurrentTimer();
  }, [fetchCurrentTimer]);

  // Tick local : incrémente chaque seconde tant qu'un timer tourne
  useEffect(() => {
    if (!currentTimer) return;
    const interval = setInterval(() => {
      updateElapsedSeconds(useTimerStore.getState().elapsedSeconds + 1);
    }, 1000);
    return () => clearInterval(interval);
  }, [currentTimer, updateElapsedSeconds]);

  if (!currentTimer) return null;

  const handleStop = async () => {
    try {
      await stopTimer();
      toast.success('Chrono arrêté');
    } catch {
      // Erreur déjà toastée par l'intercepteur API
    }
  };

  return (
    <div className="flex items-center gap-2 bg-paper-card border border-ink px-3 py-1.5">
      <span className="w-1.5 h-1.5 rounded-full bg-accent animate-pulse" />
      <span className="text-sm font-mono font-medium text-ink figures">
        {formatElapsed(elapsedSeconds)}
      </span>
      <button
        onClick={handleStop}
        title="Arrêter le chrono"
        className="p-1 hover:bg-paper-warm text-ink-soft hover:text-accent transition-colors"
      >
        <Square className="w-3.5 h-3.5 fill-current" />
      </button>
    </div>
  );
};

export default TimerWidget;
