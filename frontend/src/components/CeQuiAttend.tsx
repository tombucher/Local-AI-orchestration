/**
 * « Ce qui t'attend » : les tâches qui ne bougeront pas sans toi.
 *
 * L'outil ne lance rien de lui-même : une tâche créée (par l'analyse, une
 * fiche .md, une discussion) attend qu'on la lance, un résultat attend qu'on
 * le valide, un échec attend qu'on le relance. Le journal ne montrait que les
 * validations : soixante tâches pouvaient dormir sans qu'on le voie, et
 * l'atelier paraissait « calme ».
 */

import { useState } from 'react';
import { Link } from 'react-router-dom';
import { AlertTriangle, Eye, Loader2, Lock, Play, RefreshCw, Rocket } from 'lucide-react';
import toast from 'react-hot-toast';
import { TaskStatus, type Task } from '../types/task.types';
import type { Project } from '../types/project.types';
import { tasksService } from '../services/tasks';
import { dateLisible } from '../utils/projectState';

interface CeQuiAttendProps {
  tasks: Task[];
  /** Dans l'ordre de priorité choisi (tel que l'API les renvoie) */
  projects: Project[];
  onChanged: () => void;
}

const PAR_PROJET = 3;
const PROJETS_MAX = 6;
const RANG = { P1: 0, P2: 1, P3: 2 } as const;
const FINIES = new Set<string>([TaskStatus.COMPLETED, TaskStatus.CANCELLED]);

const pluriel = (n: number, mot: string) => `${n} ${mot}${n > 1 ? 's' : ''}`;

export const CeQuiAttend = ({ tasks, projects, onChanged }: CeQuiAttendProps) => {
  const [enCours, setEnCours] = useState<Set<number>>(new Set());

  const statut = new Map(tasks.map((t) => [t.id, t.status as string]));
  /** Dépendances pas encore terminées : la tâche ne devrait pas démarrer */
  const bloquePar = (t: Task): Task[] =>
    (t.dependencies ?? [])
      .filter((id) => statut.has(id) && !FINIES.has(statut.get(id) as string))
      .map((id) => tasks.find((x) => x.id === id))
      .filter((x): x is Task => Boolean(x));

  const aValider = tasks.filter((t) => t.status === TaskStatus.MANUAL_REVIEW);
  const enEchec = tasks.filter((t) => t.status === TaskStatus.FAILED);
  const enGeneration = tasks.filter((t) => t.status === TaskStatus.GENERATING);
  const aLancer = tasks.filter((t) => t.status === TaskStatus.CREATED || t.status === TaskStatus.READY);

  // À lancer, par projet dans l'ordre de priorité ; dans un projet : les
  // libres avant les bloquées, puis priorité, échéance, ancienneté
  const parProjet = projects
    .map((p) => ({
      projet: p,
      taches: aLancer
        .filter((t) => t.project_id === p.id)
        .sort((a, b) =>
          Number(bloquePar(a).length > 0) - Number(bloquePar(b).length > 0)
          || RANG[a.priority] - RANG[b.priority]
          || (a.due_date ?? '9999').localeCompare(b.due_date ?? '9999')
          || a.id - b.id),
    }))
    .filter((g) => g.taches.length > 0);

  const agir = async (t: Task, action: 'lancer' | 'relancer') => {
    setEnCours((prev) => new Set(prev).add(t.id));
    try {
      if (action === 'lancer') await tasksService.generateTask(t.id);
      else await tasksService.retryTask(t.id);
      toast.success(`« ${t.title} » ${action === 'lancer' ? 'lancée' : 'relancée'}`);
      onChanged();
    } catch {
      // l'intercepteur API affiche déjà l'erreur
    } finally {
      setEnCours((prev) => {
        const next = new Set(prev);
        next.delete(t.id);
        return next;
      });
    }
  };

  const Bouton = ({ t, action }: { t: Task; action: 'lancer' | 'relancer' }) => {
    const attente = enCours.has(t.id);
    return (
      <button
        onClick={() => agir(t, action)}
        disabled={attente}
        title={action === 'lancer' ? 'Générer maintenant avec le modèle local' : 'Relancer la génération'}
        className="shrink-0 inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-semibold uppercase tracking-wide border border-accent text-accent hover:bg-accent hover:text-white disabled:opacity-40 transition-colors"
      >
        {attente ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
          : action === 'lancer' ? <Play className="w-3.5 h-3.5" /> : <RefreshCw className="w-3.5 h-3.5" />}
        {action === 'lancer' ? 'Lancer' : 'Relancer'}
      </button>
    );
  };

  const total = aValider.length + enEchec.length + aLancer.length;
  const resume = [
    aValider.length > 0 && `${aValider.length} à valider`,
    enEchec.length > 0 && `${enEchec.length} en échec`,
    aLancer.length > 0 && `${aLancer.length} à lancer`,
    enGeneration.length > 0 && `${enGeneration.length} en cours`,
  ].filter(Boolean).join(' · ');

  return (
    <section className="mb-10 animate-fade-up" style={{ animationDelay: '120ms' }}>
      <div className="flex items-end justify-between gap-4 mb-4 pb-2 rule">
        <h2 className="font-display text-2xl text-ink">Ce qui t'attend</h2>
        {resume && <p className="text-xs text-ink-faint figures">{resume}</p>}
      </div>

      {total === 0 && enGeneration.length === 0 ? (
        <p className="text-sm text-ink-faint">
          Rien ne t'attend : tout est lancé ou validé. Ouvre un projet pour en discuter avec l'IA et en tirer des tâches.
        </p>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Colonne gauche : ce qui demande une décision */}
          {(aValider.length > 0 || enEchec.length > 0 || enGeneration.length > 0) && (
            <div className="space-y-5">
              {aValider.length > 0 && (
                <div className="bg-paper-card border border-ink-line border-t-2 border-t-highlight shadow-card p-4">
                  <p className="kicker flex items-center gap-1.5 mb-2">
                    <Eye className="w-3.5 h-3.5" /> À valider
                  </p>
                  <ul className="space-y-2">
                    {aValider.map((t) => (
                      <li key={t.id}>
                        <Link to={`/tasks/${t.id}`} className="block text-sm text-ink hover:text-accent leading-snug">
                          {t.title}
                          <span className="block text-[11px] text-ink-faint">{t.project_name} · relire et valider →</span>
                        </Link>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {enEchec.length > 0 && (
                <div className="bg-paper-card border border-ink-line border-t-2 border-t-danger shadow-card p-4">
                  <p className="kicker flex items-center gap-1.5 mb-2 text-danger">
                    <AlertTriangle className="w-3.5 h-3.5" /> En échec
                  </p>
                  <ul className="space-y-2">
                    {enEchec.map((t) => (
                      <li key={t.id} className="flex items-start justify-between gap-3">
                        <Link to={`/tasks/${t.id}`} className="min-w-0 text-sm text-ink hover:text-accent leading-snug">
                          {t.title}
                          <span className="block text-[11px] text-ink-faint truncate">
                            {t.project_name}{t.validation_notes ? ` · ${t.validation_notes}` : ''}
                          </span>
                        </Link>
                        <Bouton t={t} action="relancer" />
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {enGeneration.length > 0 && (
                <div className="bg-paper-card border border-ink-line border-t-2 border-t-warning shadow-card p-4">
                  <p className="kicker flex items-center gap-1.5 mb-2 text-warning">
                    <span className="inline-block w-2 h-2 bg-warning animate-pulse" /> En cours
                  </p>
                  <ul className="space-y-2">
                    {enGeneration.map((t) => (
                      <li key={t.id}>
                        <Link to={`/tasks/${t.id}`} className="block text-sm text-ink hover:text-accent leading-snug">
                          {t.title}
                          <span className="block text-[11px] text-ink-faint">
                            {t.project_name}{t.progress?.label ? ` · ${t.progress.label}` : ''}
                          </span>
                        </Link>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          {/* À lancer : par projet, dans l'ordre de priorité */}
          {aLancer.length > 0 && (
            <div className={aValider.length > 0 || enEchec.length > 0 || enGeneration.length > 0 ? 'lg:col-span-2' : 'lg:col-span-3'}>
              <p className="kicker flex items-center gap-1.5 mb-3">
                <Rocket className="w-3.5 h-3.5" /> À lancer — {pluriel(aLancer.length, 'tâche')} qui attendent ton feu vert
              </p>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {parProjet.slice(0, PROJETS_MAX).map(({ projet, taches }) => (
                  <div key={projet.id} className="bg-paper-card border border-ink-line shadow-card p-4">
                    <Link to={`/projects/${projet.id}`} className="font-display text-lg text-ink hover:text-accent leading-tight block mb-2">
                      {projet.name}
                    </Link>
                    <ul className="space-y-2">
                      {taches.slice(0, PAR_PROJET).map((t) => {
                        const attente = bloquePar(t);
                        return (
                          <li key={t.id} className="flex items-start justify-between gap-3">
                            <Link to={`/tasks/${t.id}`} className="min-w-0 text-sm text-ink-soft hover:text-accent leading-snug">
                              {t.title}
                              {(attente.length > 0 || t.due_date) && (
                                <span className="block text-[11px] text-ink-faint">
                                  {attente.length > 0
                                    ? <span className="inline-flex items-center gap-1 text-warning"><Lock className="w-3 h-3" />après « {attente[0].title} »</span>
                                    : `pour le ${dateLisible(t.due_date as string)}`}
                                </span>
                              )}
                            </Link>
                            {attente.length === 0 && <Bouton t={t} action="lancer" />}
                          </li>
                        );
                      })}
                    </ul>
                    {taches.length > PAR_PROJET && (
                      <Link to={`/projects/${projet.id}`} className="block mt-2 text-xs text-accent hover:underline">
                        et {pluriel(taches.length - PAR_PROJET, 'autre')} →
                      </Link>
                    )}
                  </div>
                ))}
              </div>
              {parProjet.length > PROJETS_MAX && (
                <Link to="/projects" className="inline-block mt-3 text-sm text-accent hover:underline">
                  et {pluriel(parProjet.length - PROJETS_MAX, 'autre projet')} avec des tâches à lancer →
                </Link>
              )}
            </div>
          )}
        </div>
      )}
    </section>
  );
};
