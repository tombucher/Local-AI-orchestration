/**
 * Contenu produit par une tâche, selon son type :
 * - veille → RadarViewer (ou résultats bruts)
 * - texte (recherche, admin, document, financement) → Markdown (+ opportunités)
 * - code → CodeViewer
 * Gère aussi le mode édition inline (code ou texte).
 */

import { Pencil } from 'lucide-react';
import type { Task, VeilleResult, VeilleRefinePayload } from '../../types/task.types';
import { TaskStatus, TaskType } from '../../types/task.types';
import { CodeViewer } from './CodeViewer';
import { RadarViewer } from './RadarViewer';
import { VeilleResultsViewer } from './VeilleResultsViewer';
import { MarkdownViewer, isTextTask, isVeilleTask } from './taskTypeUtils';
import Loader from '../ui/Loader';

interface TaskResultPanelProps {
  task: Task;
  veilleResults: VeilleResult[];
  veilleTotal: number;
  veilleLoading: boolean;
  isEditing: boolean;
  editedCode: string;
  onEditedCodeChange: (value: string) => void;
  onStartEditing: () => void;
  onCancelEditing: () => void;
  onRefine?: (refinement: VeilleRefinePayload) => Promise<void>;
}

/** Y a-t-il quelque chose à afficher ? */
export const hasGeneratedContent = (task: Task, veilleResults: VeilleResult[]): boolean => {
  if (task.generated_code) return true;
  if (task.radar_report) return true;
  return isVeilleTask(task.task_type) && veilleResults.length > 0;
};

const Card = ({ children }: { children: React.ReactNode }) => (
  <div className="bg-paper-card shadow-card border border-ink-line p-6">{children}</div>
);

const EditButton = ({ onClick }: { onClick: () => void }) => (
  <button onClick={onClick} className="flex items-center gap-1 text-sm text-accent hover:text-accent-deep">
    <Pencil className="w-4 h-4" />
    Éditer
  </button>
);

/** Langage Prism déduit du fichier produit par la tâche (défaut : texte brut). */
const LANGUAGE_BY_EXTENSION: Record<string, string> = {
  html: 'markup', htm: 'markup', svg: 'markup', vue: 'markup',
  css: 'css', scss: 'scss', sass: 'sass',
  js: 'javascript', mjs: 'javascript', cjs: 'javascript', jsx: 'jsx',
  ts: 'typescript', tsx: 'tsx',
  py: 'python', json: 'json', yml: 'yaml', yaml: 'yaml', md: 'markdown',
  sh: 'bash', sql: 'sql', toml: 'toml', rs: 'rust', go: 'go', php: 'php', rb: 'ruby',
};

const languageFromPath = (path?: string): string => {
  const extension = path?.split('.').pop()?.toLowerCase();
  return (extension && LANGUAGE_BY_EXTENSION[extension]) || 'python';
};

export const TaskResultPanel = ({
  task, veilleResults, veilleTotal, veilleLoading,
  isEditing, editedCode, onEditedCodeChange, onStartEditing, onCancelEditing, onRefine,
}: TaskResultPanelProps) => {
  if (!hasGeneratedContent(task, veilleResults)) return null;

  const canEdit = task.status === TaskStatus.MANUAL_REVIEW && !isVeilleTask(task.task_type);

  // Veille → rapport radar, sinon résultats bruts (anciennes tâches)
  if (isVeilleTask(task.task_type)) {
    if (task.radar_report) {
      return (
        <Card>
          <RadarViewer report={task.radar_report} taskId={task.id} onRefine={task.veille_topic_id ? onRefine : undefined} />
        </Card>
      );
    }
    return (
      <div className="space-y-6">
        {task.generated_code && (
          <Card>
            <h2 className="font-display text-xl text-ink mb-4">Résumé de la veille</h2>
            <MarkdownViewer content={task.generated_code} />
          </Card>
        )}
        <Card>
          <h2 className="font-display text-xl text-ink mb-4">Résultats trouvés</h2>
          {veilleLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader size="lg" label="Chargement des résultats…" />
            </div>
          ) : (
            <VeilleResultsViewer results={veilleResults} total={veilleTotal} projectId={task.project_id} />
          )}
        </Card>
      </div>
    );
  }

  // Édition inline
  if (isEditing && canEdit) {
    return (
      <div className="bg-paper-card shadow-card border border-accent p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-display text-xl text-ink flex items-center gap-2">
            <Pencil className="w-5 h-5 text-accent" />
            Édition en cours
          </h2>
          <button onClick={onCancelEditing} className="text-sm text-ink-faint hover:text-ink-soft">
            Annuler l'édition
          </button>
        </div>
        <textarea
          value={editedCode}
          onChange={(e) => onEditedCodeChange(e.target.value)}
          className="w-full h-96 font-mono text-sm p-4 border border-ink-line bg-paper focus:outline-none focus:border-ink focus:ring-1 focus:ring-ink"
          spellCheck={false}
        />
        <p className="mt-2 text-xs text-ink-faint figures">
          {editedCode.length} caractères — modifie directement puis valide
        </p>
      </div>
    );
  }

  // Texte
  if (isTextTask(task.task_type)) {
    return (
      <div className="space-y-6">
        {task.task_type === TaskType.FUNDING_SEARCH && veilleResults.length > 0 && (
          <Card>
            <h2 className="font-display text-xl text-ink mb-4">Opportunités trouvées</h2>
            <VeilleResultsViewer results={veilleResults} total={veilleTotal} projectId={task.project_id} />
          </Card>
        )}
        <Card>
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-display text-xl text-ink">Contenu généré</h2>
            {canEdit && <EditButton onClick={onStartEditing} />}
          </div>
          <MarkdownViewer content={task.generated_code || ''} />
        </Card>
      </div>
    );
  }

  // Code
  // Le fichier cible est fixé par le plan d'atelier du projet (backend :
  // project_workspace) ; il détermine aussi la coloration syntaxique.
  const artifactPath: string | undefined = task.metadata?.artifact_path;

  return (
    <Card>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-baseline gap-3">
          <h2 className="font-display text-xl text-ink">Code généré</h2>
          {artifactPath && (
            <span className="font-mono text-xs text-ink-soft bg-paper-warm border border-ink-line px-2 py-0.5">
              {artifactPath}
            </span>
          )}
        </div>
        {canEdit && <EditButton onClick={onStartEditing} />}
      </div>
      <CodeViewer code={task.generated_code || ''} language={languageFromPath(artifactPath)} />
    </Card>
  );
};
