/**
 * En-tête de la page projet : titre, type, description, dépôt, actions.
 */

import { Edit, FileText, Image, Sparkles, Trash2 } from 'lucide-react';
import type { Project } from '../../types/project.types';
import { Badge } from '../Badge';

interface ProjectHeaderProps {
  project: Project;
  onAnalyze: () => void;
  onEdit: () => void;
  onMoodboard: () => void;
  onDelete: () => void;
}

const typeLabels: Record<string, string> = {
  professional: 'Professionnel',
  personal: 'Personnel',
  research: 'Recherche',
};

export const ProjectHeader = ({ project, onAnalyze, onEdit, onMoodboard, onDelete }: ProjectHeaderProps) => (
  <div className="bg-paper-card shadow-card border border-ink-line p-6 mb-6">
    {/* Quand la place manque, les boutons passent sous le titre au lieu de l'écraser */}
    <div className="flex flex-wrap items-start justify-between gap-4 mb-4">
      <div className="flex-1 min-w-[16rem]">
        <h1 className="font-display text-3xl text-ink mb-3">{project.name}</h1>
        <Badge label={typeLabels[project.type] || project.type} variant={project.type} />
      </div>
      <div className="flex flex-wrap gap-2 justify-end">
        <button onClick={onAnalyze} className="flex items-center gap-2 px-4 py-2 text-white bg-accent hover:bg-accent-deep transition-colors">
          <Sparkles className="w-4 h-4" />
          Analyser avec l'IA
        </button>
        <button onClick={onEdit} className="flex items-center gap-2 px-4 py-2 text-ink-soft bg-paper-warm hover:text-ink transition-colors">
          <Edit className="w-4 h-4" />
          Modifier
        </button>
        <button onClick={onMoodboard} className="flex items-center gap-2 px-4 py-2 text-ink border border-ink-line bg-paper-card hover:border-accent hover:text-accent transition-colors">
          <Image className="w-4 h-4" />
          Moodboard
        </button>
        <button onClick={onDelete} className="flex items-center gap-2 px-4 py-2 text-white bg-danger hover:opacity-90 transition-colors">
          <Trash2 className="w-4 h-4" />
          Supprimer
        </button>
      </div>
    </div>

    {project.description && <p className="text-ink-soft mb-4 whitespace-pre-line">{project.description}</p>}

    {project.source_path && (
      <p className="flex items-center gap-2 text-sm text-ink-faint mb-4 min-w-0">
        <FileText className="w-4 h-4 shrink-0" />
        <span className="shrink-0">Tenu dans</span>
        <code className="font-mono text-xs truncate">{project.source_path}</code>
        <span className="hidden sm:inline shrink-0">— modifie la fiche, le projet suit.</span>
      </p>
    )}

    {project.repository_url && (
      <div className="text-sm text-ink-faint">
        <span className="font-medium">Dépôt :</span>{' '}
        <a href={project.repository_url} target="_blank" rel="noopener noreferrer" className="text-accent hover:underline">
          {project.repository_url}
        </a>
      </div>
    )}
  </div>
);
