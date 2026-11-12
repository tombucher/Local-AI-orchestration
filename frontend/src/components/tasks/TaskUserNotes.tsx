/**
 * « Ta réponse » : ce que l'utilisateur répond au résultat d'une tâche.
 *
 * Une tâche « préciser le périmètre » pose des questions ; l'utilisateur en a
 * les réponses et n'avait nulle part où les écrire. Ici, la réponse est lue par
 * les tâches qui dépendent de celle-ci, par toutes les veilles du projet (via
 * le carnet de projet), écrite dans la fiche .md sous la tâche, et peut faire
 * évoluer les mots-clés des veilles tout de suite.
 *
 * Le panneau « Veilles du projet » montre l'état réel des sujets (mots-clés,
 * prochaine occurrence, dernier affinage) : sans lui, un clic sur « Mettre à
 * jour la veille » ne laissait qu'un toast de neuf secondes, et l'utilisateur
 * recliquait en croyant que rien ne s'était passé.
 */

import { useCallback, useEffect, useState } from 'react';
import { MessageSquare, Radar, Save } from 'lucide-react';
import toast from 'react-hot-toast';
import type { Task } from '../../types/task.types';
import { tasksService } from '../../services/tasks';
import { api } from '../../services/api';
import { isVeilleTask } from './taskTypeUtils';

interface TaskUserNotesProps {
  task: Task;
  onSaved?: (notes: string) => void;
}

interface SujetDeVeille {
  id: number;
  name: string;
  enabled: boolean;
  keywords: string[];
  excluded_keywords: string[];
  scan_frequency: string;
  next_scan: string | null;
  last_refinement: { date?: string; source_task_id?: number; user_notes?: string } | null;
}

const FREQUENCES: Record<string, string> = { daily: 'quotidienne', weekly: 'hebdomadaire', monthly: 'mensuelle', once: 'ponctuelle' };

const dateHeure = (iso: string) =>
  new Date(iso).toLocaleString('fr-FR', { day: 'numeric', month: 'long', hour: '2-digit', minute: '2-digit' });

/** « dans le quart d'heure », « le 18 novembre à 13:13 », « passée » */
const prochaine = (iso: string | null) => {
  if (!iso) return 'au prochain lancement manuel';
  const delta = new Date(iso).getTime() - Date.now();
  if (delta < 15 * 60 * 1000) return 'dans le quart d\'heure';
  return `le ${dateHeure(iso)}`;
};

export const TaskUserNotes = ({ task, onSaved }: TaskUserNotesProps) => {
  const [notes, setNotes] = useState(task.user_notes ?? '');
  const [enregistre, setEnregistre] = useState(task.user_notes ?? '');
  const [occupe, setOccupe] = useState<'save' | 'veille' | null>(null);
  const [sujets, setSujets] = useState<SujetDeVeille[] | null>(null);
  const modifie = notes !== enregistre;

  const chargerSujets = useCallback(async () => {
    try {
      const r = await api.get<SujetDeVeille[]>(`/projects/${task.project_id}/veille-topics`, { silentError: true });
      setSujets(r.data.filter((s) => s.enabled));
    } catch {
      setSujets([]);
    }
  }, [task.project_id]);

  useEffect(() => { chargerSujets(); }, [chargerSujets]);

  const enregistrer = async () => {
    setOccupe('save');
    try {
      await tasksService.updateTask(task.id, { user_notes: notes });
      setEnregistre(notes);
      onSaved?.(notes);
      toast.success('Réponse enregistrée, et écrite dans la fiche sous la tâche');
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
      } else if (topics.every((t) => t.unchanged)) {
        toast('Cette réponse est déjà appliquée : rien à changer.', { icon: '✓' });
      } else {
        toast.success('Veille mise à jour : mots-clés écrits dans la fiche, prochaine occurrence dans le quart d\'heure.', { duration: 7000 });
      }
      await chargerSujets();
    } catch {
      // déjà toastée
    } finally {
      setOccupe(null);
    }
  };

  const aDesSujets = (sujets?.length ?? 0) > 0;

  return (
    <div className="bg-paper-card shadow-card border border-ink-line border-l-2 border-l-accent p-6">
      <p className="kicker mb-1 flex items-center gap-1.5">
        <MessageSquare className="w-3.5 h-3.5" /> Ta réponse
      </p>
      <p className="text-sm text-ink-soft mb-3">
        Réponds aux questions posées, complète, corrige. Écrite dans la fiche sous cette tâche, lue par les
        tâches qui en dépendent{aDesSujets ? ' et par les veilles du projet' : ''}.
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
        {!isVeilleTask(task.task_type) && aDesSujets && (
          <button
            onClick={versLaVeille}
            disabled={!notes.trim() || occupe !== null}
            title="Traduit ta réponse en mots-clés pour les veilles du projet et relance la prochaine occurrence"
            className="inline-flex items-center gap-2 px-4 py-2 border border-accent text-accent text-sm font-medium hover:bg-accent hover:text-white disabled:opacity-40 transition-colors"
          >
            <Radar className="w-4 h-4" />
            {occupe === 'veille' ? 'Le modèle relit ta réponse…' : 'Mettre à jour la veille du projet'}
          </button>
        )}
        {enregistre && !modifie && <span className="text-xs text-ink-faint">Enregistrée</span>}
      </div>

      {aDesSujets && (
        <div className="mt-5 pt-4 border-t border-ink-line/60 space-y-3">
          <p className="kicker flex items-center gap-1.5"><Radar className="w-3.5 h-3.5" /> Veilles du projet</p>
          {sujets!.map((s) => {
            const depuisIci = s.last_refinement?.source_task_id === task.id;
            return (
              <div key={s.id} className="text-sm">
                <p className="text-ink">
                  <span className="font-medium">{s.name}</span>
                  <span className="text-ink-faint"> · {FREQUENCES[s.scan_frequency] ?? s.scan_frequency} · prochaine occurrence {prochaine(s.next_scan)}</span>
                </p>
                <p className="mt-1 flex flex-wrap gap-1.5">
                  {s.keywords.map((k) => (
                    <span key={k} className="px-2 py-0.5 text-xs border border-ink-line bg-paper text-ink-soft">{k}</span>
                  ))}
                  {s.excluded_keywords.map((k) => (
                    <span key={`x-${k}`} className="px-2 py-0.5 text-xs border border-danger/40 text-danger line-through">{k}</span>
                  ))}
                </p>
                {s.last_refinement?.date && (
                  <p className="mt-1 text-xs text-ink-faint">
                    Dernier affinage le {dateHeure(s.last_refinement.date)}{depuisIci ? ', à partir de cette réponse' : ''}.
                  </p>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
