/**
 * Un projet sur une ligne, dépliable.
 *
 * Les cartes en grille imposaient de longs défilements pour avoir une vue
 * d'ensemble. Une ligne donne l'essentiel — rang, nom, espace, état, ce qui
 * attend, avancement, prochaine échéance — et se déplie sur la description et
 * les prochaines tâches.
 */

import { useState, type HTMLAttributes } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ChevronDown, ChevronRight, GripVertical, MessagesSquare } from 'lucide-react';
import type { Project } from '../../types/project.types';
import { TaskStatus, type Task } from '../../types/task.types';
import { tasksService } from '../../services/tasks';
import { libelleEtat } from '../../utils/projectState';

interface Props {
  project: Project;
  rang?: number;
  afficherEspace?: boolean;
  /** Ligne rangeable par glisser-déposer (projets actifs) */
  rangeable?: boolean;
  /** Gestionnaires du glisser-déposer, posés sur la ligne */
  dragProps?: HTMLAttributes<HTMLLIElement>;
}

const JOUR = 24 * 3600 * 1000;

/** « 2 nov. », en rouge si dépassée, en ocre si dans la semaine */
const Echeance = ({ iso }: { iso?: string | null }) => {
  if (!iso) return <span className="text-ink-faint">—</span>;
  const date = new Date(iso);
  const reste = date.getTime() - Date.now();
  const ton = reste < 0 ? 'text-danger' : reste < 7 * JOUR ? 'text-warning' : 'text-ink-soft';
  return (
    <span className={ton} title={date.toLocaleDateString('fr-FR', { dateStyle: 'full' })}>
      {date.toLocaleDateString('fr-FR', { day: 'numeric', month: 'short' })}
    </span>
  );
};

/** Ce qui demande une action : « 4 à activer · 1 à valider » */
const enAttente = (p: Project) =>
  [
    [p.tasks_to_review, 'à valider'],
    [p.tasks_failed, 'en échec'],
    [p.tasks_to_activate, 'à activer'],
    [p.tasks_running, 'en cours'],
  ]
    .filter(([n]) => (n as number) > 0)
    .map(([n, libelle]) => `${n} ${libelle}`)
    .join(' · ');

export const ProjectRow = ({ project, rang, afficherEspace = false, rangeable = false, dragProps }: Props) => {
  const navigate = useNavigate();
  const [ouvert, setOuvert] = useState(false);
  const [taches, setTaches] = useState<Task[] | null>(null);

  const total = project.tasks_total ?? 0;
  const faites = project.tasks_completed ?? 0;
  const etat = libelleEtat(project);
  const attente = enAttente(project);

  const basculer = async () => {
    const ouvrir = !ouvert;
    setOuvert(ouvrir);
    if (ouvrir && taches === null) {
      try {
        const toutes = await tasksService.getTasks({ project_id: project.id, limit: 100 });
        // Les prochaines à faire : non terminées, la plus proche échéance d'abord
        const ouvertes = toutes
          .filter((t) => t.status !== TaskStatus.COMPLETED && t.status !== TaskStatus.CANCELLED)
          .sort((a, b) => (a.due_date ?? '9999').localeCompare(b.due_date ?? '9999') || a.id - b.id);
        setTaches(ouvertes);
      } catch {
        setTaches([]);
      }
    }
  };

  return (
    <li {...dragProps} className={`bg-paper-card ${dragProps?.className ?? ''}`}>
      <div className="flex items-center gap-2 sm:gap-3 px-2 sm:px-3 py-2.5 min-w-0">
        {rangeable ? (
          <GripVertical className="w-4 h-4 text-ink-faint shrink-0 cursor-grab" aria-hidden />
        ) : (
          <span className="w-4 shrink-0" />
        )}
        <span className="w-6 text-right text-sm text-accent figures shrink-0">{rang ? `${rang}.` : ''}</span>
        <button
          onClick={basculer}
          aria-expanded={ouvert}
          title={ouvert ? 'Replier' : 'Déplier'}
          className="p-0.5 text-ink-faint hover:text-accent shrink-0"
        >
          {ouvert ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
        </button>

        <div className="min-w-0 flex-1">
          <Link to={`/projects/${project.id}`} className="font-medium text-ink hover:text-accent truncate block">
            {project.name}
          </Link>
          <p className="text-xs text-ink-faint truncate">
            {[afficherEspace && project.space, etat, attente].filter(Boolean).join(' · ') || (total === 0 ? 'Aucune tâche' : '')}
          </p>
        </div>

        {/* Avancement */}
        <div className="hidden sm:flex items-center gap-2 w-28 shrink-0" title={`${faites} tâche(s) terminée(s) sur ${total}`}>
          <div className="flex-1 h-1.5 bg-paper-warm">
            <div className="h-full bg-success" style={{ width: total ? `${(100 * faites) / total}%` : '0%' }} />
          </div>
          <span className="text-xs text-ink-faint figures w-9 text-right">{total ? `${faites}/${total}` : ''}</span>
        </div>

        {/* Prochaine échéance */}
        <div className="w-14 text-right text-xs shrink-0">
          <Echeance iso={project.next_due_date} />
        </div>
      </div>

      {ouvert && (
        <div className="pl-12 sm:pl-[4.5rem] pr-3 pb-4 space-y-3">
          {project.description && (
            <p className="text-sm text-ink-soft line-clamp-3 max-w-3xl whitespace-pre-line">{project.description}</p>
          )}
          <div>
            <p className="text-xs uppercase tracking-wider text-ink-faint mb-1">Prochaines tâches</p>
            {taches === null ? (
              <p className="text-sm text-ink-faint">Chargement…</p>
            ) : taches.length === 0 ? (
              <p className="text-sm text-ink-faint">Aucune tâche en cours.</p>
            ) : (
              <ul className="text-sm space-y-1">
                {taches.slice(0, 5).map((t) => (
                  <li key={t.id} className="flex items-baseline gap-3 min-w-0">
                    <Link to={`/tasks/${t.id}`} className="truncate text-ink hover:text-accent">{t.title}</Link>
                    {t.due_date && <span className="text-xs shrink-0"><Echeance iso={t.due_date} /></span>}
                  </li>
                ))}
                {taches.length > 5 && <li className="text-xs text-ink-faint">… et {taches.length - 5} autre(s)</li>}
              </ul>
            )}
          </div>
          <div className="flex flex-wrap gap-2">
            <Link
              to={`/projects/${project.id}`}
              className="px-3 py-1.5 border border-ink-line text-sm text-ink hover:border-accent hover:text-accent"
            >
              Ouvrir le projet
            </Link>
            <button
              onClick={() => navigate(`/projects/${project.id}?onglet=discussion`)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 border border-ink-line text-sm text-ink hover:border-accent hover:text-accent"
            >
              <MessagesSquare className="w-3.5 h-3.5" />
              Discuter avec l'IA
            </button>
          </div>
        </div>
      )}
    </li>
  );
};

export default ProjectRow;
