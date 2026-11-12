/**
 * « Ta réponse » : ce que l'utilisateur répond au résultat d'une tâche.
 *
 * Une tâche « préciser le périmètre » pose des questions ; l'utilisateur en a
 * les réponses et n'avait nulle part où les écrire. Ici, la réponse est lue par
 * les tâches qui dépendent de celle-ci, par toutes les veilles du projet (via
 * le carnet de projet), et peut faire évoluer leurs mots-clés tout de suite.
 */

import { useState } from 'react';
import { MessageSquare, Radar, Save } from 'lucide-react';
import toast from 'react-hot-toast';
import type { Task } from '../../types/task.types';
import { tasksService } from '../../services/tasks';
import { isVeilleTask } from './taskTypeUtils';

interface TaskUserNotesProps {
  task: Task;
  onSaved?: (notes: string) => void;
}

export const TaskUserNotes = ({ task, onSaved }: TaskUserNotesProps) => {
  const [notes, setNotes] = useState(task.user_notes ?? '');
  const [enregistre, setEnregistre] = useState(task.user_notes ?? '');
  const [occupe, setOccupe] = useState<'save' | 'veille' | null>(null);
  const modifie = notes !== enregistre;

  const enregistrer = async () => {
    setOccupe('save');
    try {
      await tasksService.updateTask(task.id, { user_notes: notes });
      setEnregistre(notes);
      onSaved?.(notes);
      toast.success('Réponse enregistrée : les tâches suivantes la liront');
    } catch {
      // déjà toastée
    } finally {
      setOccupe(null);
    }
  };

  const versLaVeille = async () => {
    setOccupe('veille');
    try {
      if (modifie) {
        await tasksService.updateTask(task.id, { user_notes: notes });
        setEnregistre(notes);
      }
      const { topics } = await tasksService.applyNotesToVeille(task.id);
      if (topics.length === 0) {
        toast('Ce projet n\'a pas de veille automatique.', { icon: 'ℹ️' });
        return;
      }
      for (const t of topics) {
        const detail = [
          t.added.length && `+ ${t.added.join(', ')}`,
          t.removed.length && `− ${t.removed.join(', ')}`,
          t.excluded.length && `exclus : ${t.excluded.join(', ')}`,
        ].filter(Boolean).join(' · ');
        toast.success(
          `Veille « ${t.name} » mise à jour${detail ? ` (${detail})` : ''}. Prochaine occurrence dans le quart d'heure.`,
          { duration: 9000 },
        );
      }
    } catch {
      // déjà toastée
    } finally {
      setOccupe(null);
    }
  };

  return (
    <div className="bg-paper-card shadow-card border border-ink-line border-l-2 border-l-accent p-6">
      <p className="kicker mb-1 flex items-center gap-1.5">
        <MessageSquare className="w-3.5 h-3.5" /> Ta réponse
      </p>
      <p className="text-sm text-ink-soft mb-3">
        Réponds aux questions posées, complète, corrige. Les tâches qui dépendent de celle-ci et les
        veilles du projet liront ces précisions avant le reste.
      </p>
      <textarea
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
        rows={5}
        placeholder="Ex. : zone Auvergne-Rhône-Alpes et Bourgogne ; identité visuelle et sites web, pas de signalétique ; marchés entre 3 000 et 40 000 € HT…"
        className="w-full px-3 py-2 border border-ink-line bg-paper text-sm text-ink focus:border-accent focus:outline-none"
      />
      <div className="mt-3 flex flex-wrap items-center gap-2">
        <button
          onClick={enregistrer}
          disabled={!modifie || occupe !== null}
          className="inline-flex items-center gap-2 px-4 py-2 bg-accent text-white text-sm font-medium hover:bg-accent-deep disabled:opacity-40 transition-colors"
        >
          <Save className="w-4 h-4" />
          {occupe === 'save' ? 'Enregistrement…' : 'Enregistrer'}
        </button>
        {!isVeilleTask(task.task_type) && (
          <button
            onClick={versLaVeille}
            disabled={!notes.trim() || occupe !== null}
            title="Traduit ta réponse en mots-clés pour les veilles du projet et relance la prochaine occurrence"
            className="inline-flex items-center gap-2 px-4 py-2 border border-accent text-accent text-sm font-medium hover:bg-accent hover:text-white disabled:opacity-40 transition-colors"
          >
            <Radar className="w-4 h-4" />
            {occupe === 'veille' ? 'Mise à jour…' : 'Mettre à jour la veille du projet'}
          </button>
        )}
        {enregistre && !modifie && (
          <span className="text-xs text-ink-faint">Enregistrée</span>
        )}
      </div>
    </div>
  );
};
