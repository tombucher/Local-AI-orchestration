/**
 * « Ta réponse » : ce que l'utilisateur répond au résultat d'une tâche.
 *
 * Une tâche « préciser le périmètre » pose des questions ; l'utilisateur en a
 * les réponses et n'avait nulle part où les écrire. Ici, la réponse est lue par
 * les tâches qui dépendent de celle-ci, par toutes les veilles du projet (via
 * le carnet de projet), et écrite dans la fiche .md sous la tâche.
 *
 * « Reporter dans le projet » va plus loin : la description du projet est
 * réécrite pour intégrer la réponse (ce qui y était « à préciser » l'est), les
 * mots-clés des veilles évoluent, et la fiche .md reçoit les deux. Le panneau
 * montre l'état réel : sans lui, un clic ne laissait qu'un toast de neuf
 * secondes, et l'utilisateur recliquait en croyant que rien ne s'était passé.
 */

import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { FileText, MessageSquare, Radar, Save } from 'lucide-react';
import toast from 'react-hot-toast';
import type { Task } from '../../types/task.types';
import { tasksService } from '../../services/tasks';
import { api } from '../../services/api';

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

interface FicheProjet {
  name: string;
  description: string | null;
  description_history?: { date?: string; source_task_id?: number }[] | null;
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
  const [occupe, setOccupe] = useState<'save' | 'projet' | null>(null);
  const [sujets, setSujets] = useState<SujetDeVeille[] | null>(null);
  const [projet, setProjet] = useState<FicheProjet | null>(null);
  const modifie = notes !== enregistre;

  const charger = useCallback(async () => {
    try {
      const [p, s] = await Promise.all([
        api.get<FicheProjet>(`/projects/${task.project_id}`, { silentError: true }),
        api.get<SujetDeVeille[]>(`/projects/${task.project_id}/veille-topics`, { silentError: true }),
      ]);
      setProjet(p.data);
      setSujets(s.data.filter((x) => x.enabled));
    } catch {
      setSujets((prev) => prev ?? []);
    }
  }, [task.project_id]);

  useEffect(() => { charger(); }, [charger]);

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

  const reporter = async () => {
    setOccupe('projet');
    try {
      if (modifie) {
        await tasksService.updateTask(task.id, { user_notes: notes });
        setEnregistre(notes);
      }
      const { topics, description } = await tasksService.applyNotesToProject(task.id);
      const veilleChangee = topics.some((t) => !t.unchanged);
      if (description.unchanged && !veilleChangee) {
        toast('Cette réponse est déjà reportée dans le projet : rien à changer.', { icon: '✓' });
      } else {
        const quoi = [
          !description.unchanged && (description.mode === 'ajout'
            ? 'réponse ajoutée à la description (le modèle n\'a pas répondu)'
            : 'description réécrite'),
          veilleChangee && 'mots-clés de veille mis à jour, prochaine occurrence dans le quart d\'heure',
        ].filter(Boolean).join(' · ');
        toast.success(`Projet et fiche mis à jour : ${quoi}.`, { duration: 8000 });
      }
      await charger();
    } catch {
      // déjà toastée
    } finally {
      setOccupe(null);
    }
  };

  const aDesSujets = (sujets?.length ?? 0) > 0;
  const derniereReecriture = projet?.description_history?.[projet.description_history.length - 1];
  const descriptionDepuisIci = derniereReecriture?.source_task_id === task.id;

  return (
    <div className="bg-paper-card shadow-card border border-ink-line border-l-2 border-l-accent p-6">
      <p className="kicker mb-1 flex items-center gap-1.5">
        <MessageSquare className="w-3.5 h-3.5" /> Ta réponse
      </p>
      <p className="text-sm text-ink-soft mb-3">
        Réponds aux questions posées, complète, corrige. Enregistrée dans la fiche sous cette tâche et lue
        par les tâches qui en dépendent. <em>Reporter dans le projet</em> réécrit aussi la description du
        projet{aDesSujets ? ' et les mots-clés de ses veilles' : ''}.
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
        <button
          onClick={reporter}
          disabled={!notes.trim() || occupe !== null}
          title="Réécrit la description du projet avec ta réponse, fait évoluer les mots-clés de ses veilles, et écrit le tout dans la fiche .md"
          className="inline-flex items-center gap-2 px-4 py-2 border border-accent text-accent text-sm font-medium hover:bg-accent hover:text-white disabled:opacity-40 transition-colors"
        >
          <FileText className="w-4 h-4" />
          {occupe === 'projet' ? 'Le modèle relit ta réponse…' : 'Reporter dans le projet'}
        </button>
        {enregistre && !modifie && <span className="text-xs text-ink-faint">Enregistrée</span>}
      </div>

      {projet && (
        <div className="mt-5 pt-4 border-t border-ink-line/60">
          <p className="kicker flex items-center gap-1.5">
            <FileText className="w-3.5 h-3.5" /> Description du projet
            {descriptionDepuisIci && <span className="normal-case tracking-normal text-accent"> · réécrite à partir de cette réponse</span>}
          </p>
          <p className="mt-1 text-sm text-ink-soft whitespace-pre-line line-clamp-6">
            {projet.description?.trim() || 'Pas encore de description.'}
          </p>
          <Link to={`/projects/${task.project_id}`} className="mt-1 inline-block text-xs text-accent hover:underline">
            Voir le projet
          </Link>
        </div>
      )}

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
