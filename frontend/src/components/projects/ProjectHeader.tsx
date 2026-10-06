/**
 * En-tête de la page projet : l'essentiel d'un coup d'œil.
 *
 * Titre et espace, description repliée, où en sont les tâches, et deux actions
 * visibles (discuter avec l'IA, la fiche .md). Le reste — modifier, moodboard,
 * analyse, archiver — passe dans le menu « ⋯ » : cinq boutons de même poids
 * rendaient la page difficile à lire.
 */

import { useEffect, useRef, useState } from 'react';
import { Archive, Edit, FileText, Image, MessagesSquare, Moon, MoreHorizontal, Pause, Play, Sparkles } from 'lucide-react';
import { ProjectStatus, type Project } from '../../types/project.types';
import { etatDe, libelleEtat } from '../../utils/projectState';
import { TaskStatus, type Task } from '../../types/task.types';
import { Badge } from '../Badge';
import WriteMarkdownButton from './WriteMarkdownButton';

interface ProjectHeaderProps {
  project: Project;
  tasks: Task[];
  onDiscuss: () => void;
  onAnalyze: () => void;
  onEdit: () => void;
  onMoodboard: () => void;
  onDelete: () => void;
  onFileWritten: () => void;
  /** Pause (date de reprise facultative), sommeil, ou retour aux actifs */
  onChangeState: (status: ProjectStatus, resumeOn?: string | null) => void;
}

const typeLabels: Record<string, string> = {
  professional: 'Professionnel',
  personal: 'Personnel',
  research: 'Recherche',
};

/** « 12 tâches · 4 à activer · 2 en cours · 6 terminées » */
const resumeDesTaches = (tasks: Task[]): string[] => {
  const actives = tasks.filter((t) => t.status !== TaskStatus.CANCELLED);
  if (actives.length === 0) return ['Aucune tâche'];
  const compte = (...statuts: TaskStatus[]) => actives.filter((t) => statuts.includes(t.status)).length;
  const morceaux: [number, string][] = [
    [compte(TaskStatus.CREATED), 'à activer'],
    [compte(TaskStatus.READY, TaskStatus.GENERATING), 'en cours'],
    [compte(TaskStatus.MANUAL_REVIEW), 'à valider'],
    [compte(TaskStatus.FAILED), 'en échec'],
    [compte(TaskStatus.COMPLETED), 'terminée'],
  ];
  return [
    `${actives.length} tâche${actives.length > 1 ? 's' : ''}`,
    // Seul « terminée » s'accorde ; « à activer », « en cours »… sont invariables
    ...morceaux
      .filter(([n]) => n > 0)
      .map(([n, libelle]) => `${n} ${libelle === 'terminée' && n > 1 ? 'terminées' : libelle}`),
  ];
};

const MenuItem = ({ icon: Icone, label, onClick, danger = false }: {
  icon: typeof Edit; label: string; onClick: () => void; danger?: boolean;
}) => (
  <button
    role="menuitem"
    onClick={onClick}
    className={`w-full flex items-center gap-2 px-3 py-2 text-sm text-left hover:bg-paper-warm ${
      danger ? 'text-danger' : 'text-ink'
    }`}
  >
    <Icone className="w-4 h-4 shrink-0" />
    {label}
  </button>
);

export const ProjectHeader = ({
  project, tasks, onDiscuss, onAnalyze, onEdit, onMoodboard, onDelete, onFileWritten, onChangeState,
}: ProjectHeaderProps) => {
  const etat = etatDe(project);
  const [pauseOuverte, setPauseOuverte] = useState(false);
  const [reprise, setReprise] = useState('');
  const [menu, setMenu] = useState(false);
  const [descriptionEntiere, setDescriptionEntiere] = useState(false);
  const zoneMenu = useRef<HTMLDivElement>(null);

  // Fermer le menu au clic ailleurs ou sur Échap
  useEffect(() => {
    if (!menu) return;
    const ailleurs = (e: MouseEvent) => {
      if (!zoneMenu.current?.contains(e.target as Node)) setMenu(false);
    };
    const echap = (e: KeyboardEvent) => e.key === 'Escape' && setMenu(false);
    document.addEventListener('mousedown', ailleurs);
    document.addEventListener('keydown', echap);
    return () => {
      document.removeEventListener('mousedown', ailleurs);
      document.removeEventListener('keydown', echap);
    };
  }, [menu]);

  const choisir = (action: () => void) => () => {
    setMenu(false);
    action();
  };

  const description = project.description?.trim() ?? '';
  const longue = description.length > 280 || description.split('\n').length > 3;

  return (
    <div className="bg-paper-card shadow-card border border-ink-line p-6 mb-4">
      {/* Quand la place manque, les boutons passent sous le titre au lieu de l'écraser */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex-1 min-w-[16rem]">
          {project.space && <p className="kicker mb-1">{project.space}</p>}
          <h1 className="font-display text-3xl text-ink leading-tight">{project.name}</h1>
          {etat !== 'actif' && (
            <div className="mt-2">
              <p className="inline-flex items-center gap-2 text-sm text-warning">
                {etat === 'sommeil' ? <Moon className="w-4 h-4" /> : <Pause className="w-4 h-4" />}
                {libelleEtat(project)}
              </p>
              <p className="text-xs text-ink-faint">Hors du briefing, veilles automatiques arrêtées.</p>
            </div>
          )}
          <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-ink-soft">
            <Badge label={typeLabels[project.type] || project.type} variant={project.type} />
            <span>{resumeDesTaches(tasks).join(' · ')}</span>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2 justify-end">
          <button
            onClick={onDiscuss}
            className="flex items-center gap-2 px-4 py-2 text-white bg-accent hover:bg-accent-deep transition-colors"
          >
            <MessagesSquare className="w-4 h-4" />
            Discuter avec l'IA
          </button>
          <WriteMarkdownButton projectId={project.id} hasFile={!!project.source_path} onWritten={onFileWritten} />
          <div className="relative" ref={zoneMenu}>
            <button
              onClick={() => setMenu((v) => !v)}
              aria-haspopup="menu"
              aria-expanded={menu}
              title="Autres actions"
              className="p-2 border border-ink-line text-ink hover:border-accent hover:text-accent transition-colors"
            >
              <MoreHorizontal className="w-5 h-5" />
            </button>
            {menu && (
              <div
                role="menu"
                className="absolute right-0 z-20 mt-1 w-72 bg-paper-card border border-ink-line shadow-card py-1"
              >
                <MenuItem icon={Edit} label="Modifier le projet" onClick={choisir(onEdit)} />
                <MenuItem icon={Image} label="Moodboard" onClick={choisir(onMoodboard)} />
                <MenuItem icon={Sparkles} label="Proposer des tâches (analyse IA)" onClick={choisir(onAnalyze)} />
                <div className="my-1 border-t border-ink-line" />
                {etat === 'actif' ? (
                  <>
                    <MenuItem icon={Pause} label="Mettre en pause…" onClick={choisir(() => setPauseOuverte(true))} />
                    <MenuItem icon={Moon} label="Mettre en sommeil" onClick={choisir(() => onChangeState(ProjectStatus.DORMANT))} />
                  </>
                ) : (
                  <MenuItem icon={Play} label="Réactiver le projet" onClick={choisir(() => onChangeState(ProjectStatus.ACTIVE))} />
                )}
                <div className="my-1 border-t border-ink-line" />
                <MenuItem icon={Archive} label="Archiver le projet" onClick={choisir(onDelete)} danger />
              </div>
            )}
          </div>
        </div>
      </div>

      {pauseOuverte && (
        <div className="mt-4 border border-ink-line bg-paper-warm p-4 flex flex-wrap items-end gap-3">
          <div>
            <label htmlFor="date-reprise" className="block text-sm text-ink mb-1">
              Reprendre le (facultatif)
            </label>
            <input
              id="date-reprise"
              type="date"
              value={reprise}
              min={new Date().toLocaleDateString('en-CA')}
              onChange={(e) => setReprise(e.target.value)}
              className="px-3 py-1.5 border border-ink-line bg-paper-card text-sm"
            />
          </div>
          <p className="text-xs text-ink-faint max-w-xs">
            Ce jour-là, le projet revient seul dans les actifs et le briefing te le signale.
          </p>
          <div className="flex gap-2 ml-auto">
            <button
              onClick={() => setPauseOuverte(false)}
              className="px-3 py-1.5 text-sm text-ink-soft hover:text-ink"
            >
              Annuler
            </button>
            <button
              onClick={() => {
                setPauseOuverte(false);
                onChangeState(ProjectStatus.PAUSED, reprise || null);
              }}
              className="px-3 py-1.5 bg-accent text-white text-sm hover:opacity-90"
            >
              Mettre en pause
            </button>
          </div>
        </div>
      )}

      {description && (
        <div className="mt-4">
          <p className={`text-ink-soft whitespace-pre-line max-w-3xl ${!descriptionEntiere && longue ? 'line-clamp-3' : ''}`}>
            {description}
          </p>
          {longue && (
            <button
              onClick={() => setDescriptionEntiere((v) => !v)}
              className="mt-1 text-sm text-accent hover:underline"
            >
              {descriptionEntiere ? 'Replier' : 'Lire la suite'}
            </button>
          )}
        </div>
      )}

      {project.source_path && (
        <p className="mt-3 flex items-center gap-2 text-xs text-ink-faint min-w-0">
          <FileText className="w-3.5 h-3.5 shrink-0" />
          <span className="shrink-0">Tenu dans</span>
          <code className="font-mono truncate">{project.source_path}</code>
        </p>
      )}

      {project.repository_url && (
        <p className="mt-2 text-sm text-ink-faint">
          <span className="font-medium">Dépôt :</span>{' '}
          <a href={project.repository_url} target="_blank" rel="noopener noreferrer" className="text-accent hover:underline">
            {project.repository_url}
          </a>
        </p>
      )}
    </div>
  );
};
