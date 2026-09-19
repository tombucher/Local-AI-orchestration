/**
 * Modal de validation pour la finalisation d'un projet
 *
 * Permet à l'utilisateur de:
 * - Modifier le titre et la description du projet
 * - Approuver/rejeter des tâches individuellement
 * - Modifier les détails des tâches (titre, description, priorité)
 * - Activer la veille avec sélection de mots-clés
 */
import React, { useState, useEffect } from 'react';
import { X, CheckCircle, XCircle, Sparkles, Eye, EyeOff } from 'lucide-react';
import toast from 'react-hot-toast';
import {
  ProjectFinalizationPreview,
  TaskValidationInput,
  FinalizeValidationRequest
} from '../types/project.types';
import { unifiedProjectService } from '../services/unifiedProject';

interface FinalizationValidationModalProps {
  isOpen: boolean;
  onClose: () => void;
  preview: ProjectFinalizationPreview | null;
  projectId: number;
  onFinalize: () => void;
}

export const FinalizationValidationModal: React.FC<FinalizationValidationModalProps> = ({
  isOpen,
  onClose,
  preview,
  projectId,
  onFinalize
}) => {
  // État local pour les modifications
  const [projectName, setProjectName] = useState('');
  const [projectDescription, setProjectDescription] = useState('');
  const [tasks, setTasks] = useState<TaskValidationInput[]>([]);
  const [enableVeille, setEnableVeille] = useState(false);
  const [selectedKeywords, setSelectedKeywords] = useState<string[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Initialiser l'état quand le preview change
  useEffect(() => {
    if (preview) {
      setProjectName(preview.suggested_name);
      setProjectDescription(preview.suggested_description);
      // Mapper explicitement les champs attendus par TaskValidationInput
      // (ne pas spreader TaskPreview qui contient 'subtasks' non attendu par le backend)
      setTasks(
        preview.tasks.map(task => ({
          title: task.title,
          description: task.description,
          task_type: task.task_type,
          priority: task.priority,
          estimated_duration: task.estimated_duration,
          llm_prompt: task.llm_prompt,
          approved: true // Par défaut, toutes les tâches sont approuvées
        }))
      );
      setSelectedKeywords([]);
      setEnableVeille(false);
    }
  }, [preview]);

  if (!isOpen || !preview) return null;

  const handleTaskApprovalToggle = (index: number) => {
    setTasks(prev => prev.map((task, i) =>
      i === index ? { ...task, approved: !task.approved } : task
    ));
  };

  const handleTaskFieldChange = (index: number, field: keyof TaskValidationInput, value: any) => {
    setTasks(prev => prev.map((task, i) =>
      i === index ? { ...task, [field]: value } : task
    ));
  };

  const handleKeywordToggle = (keyword: string) => {
    setSelectedKeywords(prev =>
      prev.includes(keyword)
        ? prev.filter(k => k !== keyword)
        : [...prev, keyword]
    );
  };

  const handleSubmit = async () => {
    // Validation
    if (!projectName.trim()) {
      toast.error('Le nom du projet est requis');
      return;
    }

    const approvedTasks = tasks.filter(t => t.approved);
    if (approvedTasks.length === 0) {
      toast.error('Veuillez approuver au moins une tâche');
      return;
    }

    if (enableVeille && selectedKeywords.length === 0) {
      toast.error('Veuillez sélectionner au moins un mot-clé pour la veille');
      return;
    }

    setIsSubmitting(true);

    try {
      const request: FinalizeValidationRequest = {
        project_id: projectId,
        project_name: projectName,
        project_description: projectDescription,
        tasks: tasks,
        enable_veille: enableVeille,
        veille_keywords: selectedKeywords
      };

      await unifiedProjectService.finalizeWithValidation(request);

      toast.success(`Projet créé avec ${approvedTasks.length} tâches !`);
      onFinalize();
    } catch (error: any) {
      console.error('Erreur lors de la finalisation:', error);
      toast.error(error.response?.data?.detail || 'Erreur lors de la finalisation');
    } finally {
      setIsSubmitting(false);
    }
  };

  const approvedCount = tasks.filter(t => t.approved).length;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black bg-opacity-50 transition-opacity"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="flex min-h-full items-center justify-center p-4">
        <div className="relative w-full max-w-4xl bg-paper-card rounded-2xl shadow-2xl">
          {/* Header */}
          <div className="sticky top-0 bg-gradient-to-r from-indigo-600 to-purple-600 text-white px-6 py-4 rounded-t-2xl">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Sparkles className="w-6 h-6" />
                <h2 className="text-2xl font-bold">Valider votre projet</h2>
              </div>
              <button
                onClick={onClose}
                className="p-1 hover:bg-paper-card/20 rounded-none transition-colors"
              >
                <X className="w-6 h-6" />
              </button>
            </div>
            <p className="text-white/80 text-sm mt-2">
              Modifiez les informations et approuvez les tâches avant de créer le projet
            </p>
          </div>

          {/* Content */}
          <div className="px-6 py-6 max-h-[70vh] overflow-y-auto">
            {/* Section 1: Informations du projet */}
            <div className="mb-8">
              <h3 className="text-lg font-semibold text-ink mb-4">Informations du projet</h3>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-ink-soft mb-2">
                    Nom du projet *
                  </label>
                  <input
                    type="text"
                    value={projectName}
                    onChange={(e) => setProjectName(e.target.value)}
                    className="w-full px-4 py-2 border border-ink-line rounded-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                    placeholder="Mon Super Projet"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-ink-soft mb-2">
                    Description
                  </label>
                  <textarea
                    value={projectDescription}
                    onChange={(e) => setProjectDescription(e.target.value)}
                    rows={3}
                    className="w-full px-4 py-2 border border-ink-line rounded-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent resize-none"
                    placeholder="Description détaillée du projet..."
                  />
                </div>
              </div>
            </div>

            {/* Section 2: Tâches */}
            <div className="mb-8">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-ink">
                  Tâches suggérées ({approvedCount}/{tasks.length})
                </h3>
                <span className="text-sm text-ink-soft">
                  Cliquez pour approuver/rejeter
                </span>
              </div>

              <div className="space-y-3">
                {tasks.map((task, index) => (
                  <div
                    key={index}
                    className={`border-2 rounded-none p-4 transition-all ${
                      task.approved
                        ? 'border-success/50 bg-success/5'
                        : 'border-ink-line bg-paper opacity-60'
                    }`}
                  >
                    <div className="flex items-start gap-3">
                      {/* Checkbox d'approbation */}
                      <button
                        onClick={() => handleTaskApprovalToggle(index)}
                        className={`flex-shrink-0 mt-1 p-1 rounded-full transition-colors ${
                          task.approved
                            ? 'text-success hover:bg-success/15'
                            : 'text-ink-faint hover:bg-paper-warm'
                        }`}
                      >
                        {task.approved ? (
                          <CheckCircle className="w-6 h-6" />
                        ) : (
                          <XCircle className="w-6 h-6" />
                        )}
                      </button>

                      {/* Contenu de la tâche */}
                      <div className="flex-1 space-y-3">
                        <div className="flex items-start gap-2">
                          <input
                            type="text"
                            value={task.title}
                            onChange={(e) => handleTaskFieldChange(index, 'title', e.target.value)}
                            disabled={!task.approved}
                            className={`flex-1 px-3 py-1 border rounded-none font-semibold ${
                              task.approved
                                ? 'border-ink-line text-ink'
                                : 'border-ink-line text-ink-faint bg-paper-warm'
                            }`}
                          />
                          <select
                            value={task.priority}
                            onChange={(e) => handleTaskFieldChange(index, 'priority', e.target.value)}
                            disabled={!task.approved}
                            className={`px-3 py-1 border rounded-none text-sm ${
                              task.priority === 'P1' ? 'bg-danger/10 text-danger border-danger/50' :
                              task.priority === 'P2' ? 'bg-warning/10 text-warning border-warning/50' :
                              'bg-info/10 text-info border-info/50'
                            } ${!task.approved && 'opacity-50'}`}
                          >
                            <option value="P1">P1</option>
                            <option value="P2">P2</option>
                            <option value="P3">P3</option>
                          </select>
                        </div>

                        <textarea
                          value={task.description}
                          onChange={(e) => handleTaskFieldChange(index, 'description', e.target.value)}
                          disabled={!task.approved}
                          rows={2}
                          className={`w-full px-3 py-2 border rounded-none text-sm resize-none ${
                            task.approved
                              ? 'border-ink-line text-ink-soft'
                              : 'border-ink-line text-ink-faint bg-paper-warm'
                          }`}
                        />

                        <div className="flex items-center gap-2 text-xs text-ink-faint">
                          <span className="px-2 py-1 bg-paper-warm rounded">
                            {task.task_type.replace('_', ' ')}
                          </span>
                          {task.estimated_duration && (
                            <span>⏱️ {Math.round(task.estimated_duration / 3600)}h</span>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Section 3: Veille (P1) */}
            {preview.veille_keywords.length > 0 && (
              <div className="mb-8">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-semibold text-ink">Veille automatique</h3>
                  <button
                    onClick={() => setEnableVeille(!enableVeille)}
                    className={`flex items-center gap-2 px-4 py-2 rounded-none font-medium transition-colors ${
                      enableVeille
                        ? 'bg-success/10 text-success'
                        : 'bg-paper-warm text-ink-soft'
                    }`}
                  >
                    {enableVeille ? <Eye className="w-4 h-4" /> : <EyeOff className="w-4 h-4" />}
                    {enableVeille ? 'Activée' : 'Désactivée'}
                  </button>
                </div>

                {enableVeille && (
                  <div>
                    <p className="text-sm text-ink-soft mb-3">
                      Sélectionnez les mots-clés pour la surveillance automatique
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {preview.veille_keywords.map(keyword => (
                        <button
                          key={keyword}
                          onClick={() => handleKeywordToggle(keyword)}
                          className={`px-3 py-1 rounded-full text-sm font-medium transition-colors ${
                            selectedKeywords.includes(keyword)
                              ? 'bg-accent text-white'
                              : 'bg-paper-warm text-ink-soft hover:bg-gray-300'
                          }`}
                        >
                          {keyword}
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="sticky bottom-0 bg-paper px-6 py-4 rounded-b-2xl border-t border-ink-line">
            <div className="flex items-center justify-between">
              <div className="text-sm text-ink-soft">
                {approvedCount} tâche{approvedCount > 1 ? 's' : ''} sera créée{approvedCount > 1 ? 's' : ''}
                {enableVeille && selectedKeywords.length > 0 && (
                  <span> • {selectedKeywords.length} mot{selectedKeywords.length > 1 ? 's' : ''}-clé pour la veille</span>
                )}
              </div>
              <div className="flex gap-3">
                <button
                  onClick={onClose}
                  disabled={isSubmitting}
                  className="px-6 py-2 border border-ink-line text-ink-soft rounded-none font-medium hover:bg-paper-warm transition-colors disabled:opacity-50"
                >
                  Annuler
                </button>
                <button
                  onClick={handleSubmit}
                  disabled={isSubmitting || approvedCount === 0}
                  className="flex items-center gap-2 px-6 py-2 bg-accent text-white rounded-none font-medium hover:bg-accent-deep transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isSubmitting ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                      Création...
                    </>
                  ) : (
                    <>
                      <CheckCircle className="w-5 h-5" />
                      Valider et créer le projet
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
