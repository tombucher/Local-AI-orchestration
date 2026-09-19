/**
 * Page Formulaire Projet (Création / Édition)
 * - React Hook Form + Zod validation
 * - Configuration financière conditionnelle
 */

import { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useNavigate, useParams } from 'react-router-dom';
import { useProjectsStore } from '../../stores/projectsStore';
import { Navbar } from '../../components/Layout/Navbar';
import { Sidebar } from '../../components/Layout/Sidebar';
import { ProjectType } from '../../types/project.types';
import toast from 'react-hot-toast';
import Loader from '../../components/ui/Loader';

// Schéma de validation Zod
const projectSchema = z.object({
  name: z.string().min(3, 'Minimum 3 caractères'),
  description: z.string().optional(),
  type: z.enum(['professional', 'personal', 'research']),
  features: z.object({
    code_gen: z.boolean(),
    veille: z.boolean(),
    git_auto: z.boolean(),
  }),
  financial_config: z
    .object({
      // valueAsNumber donne NaN sur champ vide → converti en undefined
      hourly_rate: z.preprocess(
        (v) => (typeof v === 'number' && Number.isNaN(v) ? undefined : v),
        z.number().min(0, 'Doit être positif').optional()
      ),
      budget: z.preprocess(
        (v) => (typeof v === 'number' && Number.isNaN(v) ? undefined : v),
        z.number().min(0, 'Doit être positif').optional()
      ),
      currency: z.string(),
    })
    .optional(),
});

type ProjectFormData = z.infer<typeof projectSchema>;

export const ProjectForm = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { currentProject, loading, fetchProject, createProject, updateProject } =
    useProjectsStore();

  const isEditMode = Boolean(id);

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    formState: { errors },
  } = useForm<ProjectFormData>({
    resolver: zodResolver(projectSchema),
    defaultValues: {
      name: '',
      description: '',
      type: 'personal',
      features: {
        code_gen: true,
        veille: false,
        git_auto: false,
      },
      financial_config: {
        currency: 'EUR',
      },
    },
  });

  const projectType = watch('type');
  const isProfessional = projectType === 'professional';

  // Charger le projet en mode édition
  useEffect(() => {
    if (isEditMode && id) {
      fetchProject(parseInt(id));
    }
  }, [isEditMode, id, fetchProject]);

  // Pré-remplir le formulaire en mode édition
  useEffect(() => {
    if (isEditMode && currentProject) {
      setValue('name', currentProject.name);
      setValue('description', currentProject.description || '');
      setValue('type', currentProject.type);
      if (currentProject.features) {
        setValue('features', currentProject.features);
      }
      if (currentProject.financial_config) {
        setValue('financial_config', {
          currency: 'EUR',
          ...currentProject.financial_config,
        });
      }
    }
  }, [isEditMode, currentProject, setValue]);

  const onSubmit = async (data: ProjectFormData) => {
    try {
      // Nettoyer les données (le z.enum produit une union string → cast vers l'enum)
      const cleanData = {
        ...data,
        type: data.type as ProjectType,
        financial_config: isProfessional ? data.financial_config : undefined,
      };

      if (isEditMode && id) {
        await updateProject(parseInt(id), cleanData);
        toast.success('Projet modifié avec succès');
        navigate(`/projects/${id}`);
      } else {
        const newProject = await createProject(cleanData);
        toast.success('Projet créé avec succès');
        navigate(`/projects/${newProject.id}`);
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
              {isEditMode ? 'Modifier le projet' : 'Nouveau projet'}
            </h1>

            <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
              {/* Section 1 : Informations générales */}
              <div className="bg-paper-card rounded-none shadow-card border border-ink-line p-6">
                <h2 className="text-lg font-semibold text-ink mb-4">
                  Informations générales
                </h2>

                <div className="space-y-4">
                  {/* Nom */}
                  <div>
                    <label className="block text-sm font-medium text-ink-soft mb-1">
                      Nom du projet *
                    </label>
                    <input
                      {...register('name')}
                      type="text"
                      className="w-full px-3 py-2 border border-ink-line rounded-none focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
                      placeholder="Mon super projet"
                    />
                    {errors.name && (
                      <p className="mt-1 text-sm text-danger">{errors.name.message}</p>
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
                      placeholder="Décrivez votre projet..."
                    />
                  </div>

                  {/* Type */}
                  <div>
                    <label className="block text-sm font-medium text-ink-soft mb-1">
                      Type de projet *
                    </label>
                    <select
                      {...register('type')}
                      className="w-full px-3 py-2 border border-ink-line rounded-none focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
                    >
                      <option value="personal">Personnel</option>
                      <option value="professional">Professionnel</option>
                      <option value="research">Recherche</option>
                    </select>
                  </div>
                </div>
              </div>

              {/* Section 2 : Fonctionnalités */}
              <div className="bg-paper-card rounded-none shadow-card border border-ink-line p-6">
                <h2 className="text-lg font-semibold text-ink mb-4">Fonctionnalités</h2>

                <div className="space-y-3">
                  <label className="flex items-center gap-3 cursor-pointer">
                    <input
                      {...register('features.code_gen')}
                      type="checkbox"
                      className="w-4 h-4 text-primary border-ink-line rounded focus:ring-primary"
                    />
                    <div>
                      <p className="font-medium text-ink">Génération de code automatique</p>
                      <p className="text-sm text-ink-faint">
                        Utilise l'orchestrateur IA pour générer du code
                      </p>
                    </div>
                  </label>

                  <label className="flex items-center gap-3 cursor-pointer">
                    <input
                      {...register('features.veille')}
                      type="checkbox"
                      className="w-4 h-4 text-primary border-ink-line rounded focus:ring-primary"
                    />
                    <div>
                      <p className="font-medium text-ink">Veille technologique</p>
                      <p className="text-sm text-ink-faint">
                        Surveillance des nouvelles technologies et tendances
                      </p>
                    </div>
                  </label>

                  <label className="flex items-center gap-3 cursor-pointer">
                    <input
                      {...register('features.git_auto')}
                      type="checkbox"
                      className="w-4 h-4 text-primary border-ink-line rounded focus:ring-primary"
                    />
                    <div>
                      <p className="font-medium text-ink">Git automatique</p>
                      <p className="text-sm text-ink-faint">Commits et push automatiques</p>
                    </div>
                  </label>
                </div>
              </div>

              {/* Section 3 : Configuration financière (si PRO) */}
              {isProfessional && (
                <div className="bg-paper-card rounded-none shadow-card border border-ink-line p-6">
                  <h2 className="text-lg font-semibold text-ink mb-4">
                    Configuration financière
                  </h2>

                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-ink-soft mb-1">
                        Taux horaire (€/h)
                      </label>
                      <input
                        {...register('financial_config.hourly_rate', { valueAsNumber: true })}
                        type="number"
                        step="0.01"
                        className="w-full px-3 py-2 border border-ink-line rounded-none focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
                        placeholder="50.00"
                      />
                      {errors.financial_config?.hourly_rate && (
                        <p className="mt-1 text-sm text-danger">{errors.financial_config.hourly_rate.message}</p>
                      )}
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-ink-soft mb-1">
                        Budget total (€)
                      </label>
                      <input
                        {...register('financial_config.budget', { valueAsNumber: true })}
                        type="number"
                        step="0.01"
                        className="w-full px-3 py-2 border border-ink-line rounded-none focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
                        placeholder="5000.00"
                      />
                      {errors.financial_config?.budget && (
                        <p className="mt-1 text-sm text-danger">{errors.financial_config.budget.message}</p>
                      )}
                    </div>

                    <div className="bg-info/5 border border-info/30 rounded-none p-4">
                      <p className="text-sm text-info">
                        💡 Le tracking du temps sera automatique pour calculer les coûts réels
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {/* Actions */}
              <div className="flex gap-4">
                <button
                  type="button"
                  onClick={() => navigate('/projects')}
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
                    : 'Créer le projet'}
                </button>
              </div>
            </form>
          </div>
        </main>
      </div>
    </div>
  );
};
