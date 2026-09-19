/**
 * Helpers partagés sur le type de tâche + rendu Markdown.
 * Extraits de TaskDetail pour être réutilisés par les sous-composants.
 */

import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { FileText, Search, ClipboardList } from 'lucide-react';
import { TaskType } from '../../types/task.types';

/** Tâche de veille (tous scopes) */
export const isVeilleTask = (taskType: TaskType): boolean =>
  [TaskType.VEILLE, TaskType.VEILLE_TECH, TaskType.VEILLE_CULTURAL, TaskType.VEILLE_EVENTS].includes(taskType);

/** Tâche dont le résultat est du texte (pas du code) */
export const isTextTask = (taskType: TaskType): boolean =>
  [TaskType.RESEARCH, TaskType.ADMINISTRATIVE, TaskType.DOCUMENT_WRITING, TaskType.FUNDING_SEARCH].includes(taskType);

export const getTaskTypeLabel = (taskType: TaskType): string => {
  const labels: Partial<Record<TaskType, string>> = {
    [TaskType.CODE_GENERATION]: 'Code',
    [TaskType.DOCUMENT_WRITING]: 'Document',
    [TaskType.FUNDING_SEARCH]: 'Recherche de financement',
    [TaskType.VEILLE]: 'Veille',
    [TaskType.VEILLE_TECH]: 'Veille',
    [TaskType.VEILLE_CULTURAL]: 'Veille',
    [TaskType.VEILLE_EVENTS]: 'Veille',
    [TaskType.ADMINISTRATIVE]: 'Administratif',
    [TaskType.RESEARCH]: 'Recherche',
  };
  return labels[taskType] || taskType;
};

export const getTaskTypeIcon = (taskType: TaskType) => {
  if (isVeilleTask(taskType)) return <Search className="w-4 h-4" />;
  if (isTextTask(taskType)) return <FileText className="w-4 h-4" />;
  return <ClipboardList className="w-4 h-4" />;
};

/** Libellé du bouton de validation selon le type */
export const getValidateLabel = (taskType: TaskType): string => {
  if (isVeilleTask(taskType)) return 'Valider les résultats';
  if (isTextTask(taskType)) return 'Valider le contenu';
  return 'Valider le code';
};

/** Rendu Markdown (GFM) aux couleurs du design system */
export const MarkdownViewer = ({ content }: { content: string }) => (
  <div className="markdown-body prose prose-sm max-w-none text-ink
    prose-headings:font-semibold prose-headings:text-ink
    prose-h1:text-2xl prose-h1:mt-6 prose-h1:mb-4 prose-h1:border-b prose-h1:pb-2
    prose-h2:text-xl prose-h2:mt-5 prose-h2:mb-3
    prose-h3:text-lg prose-h3:mt-4 prose-h3:mb-2
    prose-p:my-3 prose-p:leading-relaxed
    prose-ul:my-3 prose-ol:my-3 prose-li:my-1
    prose-strong:text-ink prose-strong:font-semibold
    prose-code:bg-paper-warm prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:text-accent prose-code:before:content-none prose-code:after:content-none
    prose-pre:bg-ink prose-pre:text-paper
    prose-blockquote:border-l-4 prose-blockquote:border-accent prose-blockquote:bg-paper-warm prose-blockquote:py-1 prose-blockquote:px-4 prose-blockquote:not-italic
    prose-a:text-accent prose-a:no-underline hover:prose-a:underline
    prose-table:border prose-th:bg-paper-warm prose-th:p-2 prose-td:p-2 prose-td:border">
    <ReactMarkdown remarkPlugins={[remarkGfm]}>{content || ''}</ReactMarkdown>
  </div>
);
