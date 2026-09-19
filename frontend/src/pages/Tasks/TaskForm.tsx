/**
 * Page Formulaire Tâche (Création / Édition)
 */

import { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { useTasksStore } from '../../stores/tasksStore';
import { useProjectsStore } from '../../stores/projectsStore';
import { Navbar } from '../../components/Layout/Navbar';
import { Sidebar } from '../../components/Layout/Sidebar';
import { TaskPriority, TaskType } from '../../types/task.types';
import toast from 'react-hot-toast';
import Loader from '../../components/ui/Loader';

// Schéma de validation Zod
const taskSchema = z.object({
  project_id: z.number({ required_error: 'Projet requis' }),
  title: z.string().min(3, 'Minimum 3 caractères'),
  description: z.string().optional(),
  task_type: z.enum(['code_generation', 'document_writing', 'funding_search', 'veille', 'veille_tech', 'veille_cultural', 'veille_events', 'administrative', 'research']).optional(),
  priority: z.enum(['P1', 'P2', 'P3']),
  llm_prompt: z.string().optional(),
  keywords: z.string().optional(),
  frequency: z.enum(['once', 'daily', 'weekly', 'monthly']).optional(),
  veille_scope: z.enum(['news', 'tech', 'cultural', 'funding', 'academic', 'visual']).optional(),
  excluded_keywords: z.string().optional(),
});

type TaskFormData = z.infer<typeof taskSchema>;

export const TaskForm = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { currentTask, loading, fetchTask, createTask, updateTask } = useTasksStore();
  const { projects, fetchProjects } = useProjectsStore();

  const isEditMode = Boolean(id);
  const preselectedProjectId = searchParams.get('project_id');

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    formState: { errors },
  } = useForm<TaskFormData>({
    resolver: zodResolver(taskSchema),
    defaultValues: {
      project_id: preselectedProjectId ? parseInt(preselectedProjectId) : undefined,
      title: '',
      description: '',
      task_type: TaskType.CODE_GENERATION,
      priority: TaskPriority.P3,
      llm_prompt: '',
      keywords: '',
      frequency: 'weekly',
      veille_scope: 'news',
      excluded_keywords: '',
    },
  });

  const taskType = watch('task_type');

  useEffect(() => {
    fetchProjects();
  }, [fetchProjects]);

  useEffect(() => {
    if (isEditMode && id) {
      fetchTask(parseInt(id));
    }
  }, [isEditMode, id, fetchTask]);

  useEffect(() => {
    if (isEditMode && currentTask) {
      setValue('project_id', currentTask.project_id);
      setValue('title', currentTask.title);
      setValue('description', currentTask.description || '');
      setValue('task_type', currentTask.task_type);
      setValue('priority', currentTask.priority);
      setValue('llm_prompt', currentTask.llm_prompt || '');

      // Restaurer les keywords depuis metadata
      if (currentTask.metadata?.keywords) {
        const keywordsString = Array.isArray(currentTask.metadata.keywords)
          ? currentTask.metadata.keywords.join(', ')
          : currentTask.metadata.keywords;
        setValue('keywords', keywordsString);
      }
      if (currentTask.metadata?.scope) {
        setValue('veille_scope', currentTask.metadata.scope);
      }
    }
  }, [isEditMode, currentTask, setValue]);

  const onSubmit = async (data: TaskFormData) => {
    try {
      // Préparer les metadata selon le type de tâche
      // En mode édition, fusionner avec les metadata existantes
      const metadata: Record<string, any> = isEditMode && currentTask?.metadata
        ? { ...currentTask.metadata }
        : {};

      if (data.keywords) {
        metadata.keywords = data.keywords.split(',').map((k: string) => k.trim()).filter(Boolean);
      } else {
        // Si keywords est vide, le supprimer des metadata
        delete metadata.keywords;
      }

      // Fréquence de veille
      if (data.veille_scope) {
        metadata.scope = data.veille_scope;
      }
      if (data.frequency) {
        metadata.frequency = data.frequency;
      }

      // Keywords exclus
      if (data.excluded_keywords) {
        metadata.excluded_keywords = data.excluded_keywords.split(',').map((k: string) => k.trim()).filter(Boolean);
      }

      const taskData = {
        project_id: data.project_id,
        title: data.title,
        description: data.description,
        task_type: data.task_type as TaskType,
        priority: data.priority as TaskPriority,
        llm_prompt: data.llm_prompt,
        metadata,
      };

      if (isEditMode && id) {
        await updateTask(parseInt(id), taskData);
        toast.success('Tâche modifiée avec succès');
        navigate(`/tasks/${id}`);
      } else {
        const newTask = await createTask(taskData);
        toast.success('Tâche créée avec succès');
        navigate(`/tasks/${newTask.id}`);
      }
    } catch {
      // Erreur déjà toastée par l'intercepteur API
    }
  };

  if (loading && isEditMode) {
    return (
      <div className="min-h-screen bg-paper">
        <Navbar />
        <div className="flex">
          <Sidebar />
          <main className="flex-1 p-6 lg:p-8">
            <div className="flex items-center justify-center py-12">
              <Loader size="lg" />
            </div>
          </main>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-paper">
      <Navbar />

      <div className="flex">
        <Sidebar />

        <main className="flex-1 p-6 lg:p-8">
          <div className="max-w-3xl mx-auto">
            <h1 className="text-3xl font-bold text-ink mb-8">
              {isEditMode ? 'Modifier la tâche' : 'Nouvelle tâche'}
            </h1>

            <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
              {/* Section Informations générales */}
              <div className="bg-paper-card rounded-none shadow-card border border-ink-line p-6">
                <h2 className="text-lg font-semibold text-ink mb-4">
                  Informations générales
                </h2>

                <div className="space-y-4">
                  {/* Projet */}
                  <div>
                    <label className="block text-sm font-medium text-ink-soft mb-1">
                      Projet *
                    </label>
                    <select
                      {...register('project_id', { valueAsNumber: true })}
                      className="w-full px-3 py-2 border border-ink-line rounded-none focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
                    >
                      <option value="">Sélectionnez un projet</option>
                      {projects.map((project) => (
                        <option key={project.id} value={project.id}>
                          {project.name}
                        </option>
                      ))}
                    </select>
                    {errors.project_id && (
                      <p className="mt-1 text-sm text-danger">{errors.project_id.message}</p>
                    )}
                  </div>

                  {/* Titre */}
                  <div>
                    <label className="block text-sm font-medium text-ink-soft mb-1">
                      Titre *
                    </label>
                    <input
                      {...register('title')}
                      type="text"
                      className="w-full px-3 py-2 border border-ink-line rounded-none focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
                      placeholder="Ex: Créer une page de login"
                    />
                    {errors.title && (
                      <p className="mt-1 text-sm text-danger">{errors.title.message}</p>
                    )}
                  </div>

                  {/* Description */}
                  <div>
                    <label className="block text-sm font-medium text-ink-soft mb-1">
                      Description
                    </label>
                    <textarea
                      {...register('description')}
                      rows={4}
                      className="w-full px-3 py-2 border border-ink-line rounded-none focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
                      placeholder="Décrivez la tâche..."
                    />
                  </div>

                  {/* Type de tâche */}
                  <div>
                    <label className="block text-sm font-medium text-ink-soft mb-1">
                      Type de tâche *
                    </label>
                    <select
                      {...register('task_type')}
                      className="w-full px-3 py-2 border border-ink-line rounded-none focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
                    >
                      <option value={TaskType.CODE_GENERATION}>💻 Génération de Code</option>
                      <option value={TaskType.DOCUMENT_WRITING}>📄 Rédaction de Document</option>
                      <option value={TaskType.FUNDING_SEARCH}>💰 Recherche de Financements</option>
                      <option value={TaskType.VEILLE}>🔍 Veille (Monitoring récurrent)</option>
                      <option value={TaskType.ADMINISTRATIVE}>📋 Tâche Administrative</option>
                      <option value={TaskType.RESEARCH}>🔬 Recherche</option>
                    </select>
                  </div>

                  {/* Priorité */}
                  <div>
                    <label className="block text-sm font-medium text-ink-soft mb-1">
                      Priorité *
                    </label>
                    <select
                      {...register('priority')}
                      className="w-full px-3 py-2 border border-ink-line rounded-none focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
                    >
                      <option value="P1">P1 - Urgent</option>
                      <option value="P2">P2 - Important</option>
                      <option value="P3">P3 - Normal</option>
                    </select>
                  </div>
                </div>
              </div>

              {/* Section Paramètres de veille */}
              {(taskType === TaskType.VEILLE ||
                taskType === TaskType.VEILLE_TECH ||
                taskType === TaskType.VEILLE_CULTURAL ||
                taskType === TaskType.VEILLE_EVENTS ||
                taskType === TaskType.FUNDING_SEARCH) && (
                <div className="bg-paper-card rounded-none shadow-card border border-ink-line p-6">
                  <h2 className="text-lg font-semibold text-ink mb-4">
                    🔍 Paramètres de recherche
                  </h2>

                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-ink-soft mb-1">
                        Mots-clés (séparés par des virgules)
                      </label>
                      <input
                        {...register('keywords')}
                        type="text"
                        className="w-full px-3 py-2 border border-ink-line rounded-none focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
                        placeholder="Ex: art numérique, compostage, creative coding"
                      />
                      <p className="mt-1 text-xs text-ink-faint">
                        L'IA recherchera automatiquement des informations liées à ces mots-clés
                      </p>
                    </div>

                    {/* Fréquence (uniquement pour VEILLE) */}
                    {taskType === TaskType.VEILLE && (
                      <div>
                        <label className="block text-sm font-medium text-ink-soft mb-1">
                          Fréquence de la veille
                        </label>
                        <select
                          {...register('frequency')}
                          className="w-full px-3 py-2 border border-ink-line rounded-none focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
                        >
                          <option value="once">🎯 Une seule fois (one-shot)</option>
                          <option value="daily">📅 Quotidienne</option>
                          <option value="weekly">📆 Hebdomadaire</option>
                          <option value="monthly">🗓️ Mensuelle</option>
                        </select>
                        <p className="mt-1 text-xs text-ink-faint">
                          « Une seule fois » lance un scan unique sans récurrence ; sinon la prochaine occurrence est programmée automatiquement
                        </p>
                      </div>
                    )}

                    {/* Type de veille */}
                    {taskType === TaskType.VEILLE && (
                      <div>
                        <label className="block text-sm font-medium text-ink-soft mb-1">
                          Type de veille
                        </label>
                        <select
                          {...register('veille_scope')}
                          className="w-full px-3 py-2 border border-ink-line rounded-none focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
                        >
                          <option value="news">📰 Actualités / généraliste</option>
                          <option value="tech">⚙️ Technologique</option>
                          <option value="cultural">🎭 Culturelle (festivals, expos)</option>
                          <option value="funding">💰 Financements / appels à projets</option>
                          <option value="academic">📚 Académique</option>
                          <option value="visual">🖼 Visuelle (images, moodboard)</option>
                        </select>
                        <p className="mt-1 text-xs text-ink-faint">
                          La veille visuelle collecte des images libres de droits (Openverse, musées) dans le moodboard du projet
                        </p>
                      </div>
                    )}

                    {/* Keywords exclus (optionnel) */}
                    {taskType === TaskType.VEILLE && (
                      <div>
                        <label className="block text-sm font-medium text-ink-soft mb-1">
                          Mots-clés à exclure (optionnel)
                        </label>
                        <input
                          {...register('excluded_keywords')}
                          type="text"
                          className="w-full px-3 py-2 border border-ink-line rounded-none focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
                          placeholder="Ex: github, npm, framework"
                        />
                        <p className="mt-1 text-xs text-ink-faint">
                          Ces termes seront exclus des résultats de veille
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Section Génération de code */}
              {taskType === TaskType.CODE_GENERATION && (
                <div className="bg-paper-card rounded-none shadow-card border border-ink-line p-6">
                  <h2 className="text-lg font-semibold text-ink mb-4">
                    💻 Génération de code (optionnel)
                  </h2>

                  <div>
                    <label className="block text-sm font-medium text-ink-soft mb-1">
                      Prompt pour le LLM
                    </label>
                    <textarea
                      {...register('llm_prompt')}
                      rows={6}
                      className="w-full px-3 py-2 border border-ink-line rounded-none focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
                      placeholder="Décrivez ce que le LLM doit générer comme code..."
                    />
                    <p className="mt-1 text-xs text-ink-faint">
                      Si vous remplissez ce champ, l'orchestrateur IA générera automatiquement le code
                    </p>
                  </div>
                </div>
              )}

              {/* Section Rédaction de document */}
              {taskType === TaskType.DOCUMENT_WRITING && (
                <div className="bg-paper-card rounded-none shadow-card border border-ink-line p-6">
                  <h2 className="text-lg font-semibold text-ink mb-4">
                    📄 Rédaction de document
                  </h2>

                  <div>
                    <label className="block text-sm font-medium text-ink-soft mb-1">
                      Instructions pour l'IA
                    </label>
                    <textarea
                      {...register('llm_prompt')}
                      rows={6}
                      className="w-full px-3 py-2 border border-ink-line rounded-none focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
                      placeholder="Décrivez le document à rédiger (dossier de financement, rapport d'activité, budget, etc.)..."
                    />
                    <p className="mt-1 text-xs text-ink-faint">
                      L'IA rédigera automatiquement le document selon vos instructions
                    </p>
                  </div>
                </div>
              )}

              {/* Actions */}
              <div className="flex gap-4">
                <button
                  type="button"
                  onClick={() => navigate('/tasks')}
                  className="flex-1 px-4 py-2 border border-ink-line text-ink-soft rounded-none hover:bg-paper-warm transition-colors font-medium"
                >
                  Annuler
                </button>
                <button
                  type="submit"
                  disabled={loading}
                  className="flex-1 px-4 py-2 bg-primary text-white rounded-none hover:bg-primary/90 transition-colors font-medium disabled:opacity-50"
                >
                  {loading
                    ? 'Enregistrement...'
                    : isEditMode
                    ? 'Sauvegarder'
                    : 'Créer la tâche'}
                </button>
              </div>
            </form>
          </div>
        </main>
      </div>
    </div>
  );
};
