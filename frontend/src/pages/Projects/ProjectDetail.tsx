/**
 * Page Détail d'un projet — composition :
 * - ProjectHeader (titre, type, actions)
 * - IdeationChat en phase d'idéation
 * - ProjectFeaturesPanel / ProjectFinancialPanel
 * - ProjectHealthDashboard (maturité, stats, chemin critique, Gantt)
 * - ProjectTasksBoard (liste des tâches)
 */

import { useEffect, useMemo, useState } from 'react';
import { useParams, useNavigate, useSearchParams, Link } from 'react-router-dom';
import { ChevronRight, Home, MessagesSquare } from 'lucide-react';
import toast from 'react-hot-toast';
import { useProjectsStore } from '../../stores/projectsStore';
import { Navbar } from '../../components/Layout/Navbar';
import { Sidebar } from '../../components/Layout/Sidebar';
import { IdeationChat } from '../../components/IdeationChat';
import { ProjectHeader } from '../../components/projects/ProjectHeader';
import { ProjectFeaturesPanel, ProjectFinancialPanel } from '../../components/projects/ProjectInfoPanels';
import { ProjectHealthDashboard } from '../../components/projects/ProjectHealthDashboard';
import { ProjectTasksBoard } from '../../components/projects/ProjectTasksBoard';
import ProjectDocuments from '../../components/projects/ProjectDocuments';
import ProjectOutputs from '../../components/projects/ProjectOutputs';
import ProjectDiscussion from '../../components/projects/ProjectDiscussion';
import ConfirmDialog from '../../components/ui/ConfirmDialog';
import Loader from '../../components/ui/Loader';
import { tasksService } from '../../services/tasks';
import api from '../../services/api';
import { ProjectStatus } from '../../types/project.types';
import { TaskStatus, type Task } from '../../types/task.types';
import type { CriticalPathData, CriticalPathTaskData } from '../../types/critical-path.types';

const PageShell = ({ children }: { children: React.ReactNode }) => (
  <div className="min-h-screen bg-paper">
    <Navbar />
    <div className="flex">
      <Sidebar />
      <main className="flex-1 min-w-0 p-6 lg:p-8">{children}</main>
    </div>
  </div>
);

const ONGLETS = [
  { id: 'taches', libelle: 'Tâches' },
  { id: 'discussion', libelle: 'Discussion' },
  { id: 'production', libelle: 'Production' },
  { id: 'documents', libelle: 'Documents' },
  { id: 'suivi', libelle: 'Suivi' },
] as const;
type Onglet = (typeof ONGLETS)[number]['id'];

export const ProjectDetail = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { currentProject, currentProjectStats, loading, fetchProject, fetchProjectStats, deleteProject, updateProject } = useProjectsStore();
  const [tasks, setTasks] = useState<Task[]>([]);
  const [tasksLoading, setTasksLoading] = useState(false);
  const [criticalPathData, setCriticalPathData] = useState<CriticalPathData | null>(null);
  const [confirmDelete, setConfirmDelete] = useState(false);

  // Onglet dans l'adresse (?onglet=production) : un lien ou le retour arrière y ramène
  const [parametres, setParametres] = useSearchParams();
  const demande = parametres.get('onglet');
  const onglet: Onglet = ONGLETS.some((o) => o.id === demande) ? (demande as Onglet) : 'taches';
  const choisirOnglet = (cle: Onglet) =>
    setParametres(cle === 'taches' ? {} : { onglet: cle }, { replace: true });
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    if (!id) return;
    const projectId = parseInt(id);
    fetchProject(projectId);
    fetchProjectStats(projectId);
    loadTasks(projectId);
    loadCriticalPath(projectId);
  }, [id, fetchProject, fetchProjectStats]);

  const loadTasks = async (projectId: number) => {
    setTasksLoading(true);
    try {
      setTasks(await tasksService.getTasks({ project_id: projectId }));
    } catch (error) {
      console.error('Error loading tasks:', error);
    } finally {
      setTasksLoading(false);
    }
  };

  const loadCriticalPath = async (projectId: number) => {
    try {
      const response = await api.get<CriticalPathData>(`/projects/${projectId}/critical-path`, { silentError: true });
      setCriticalPathData(response.data);
    } catch (error: any) {
      if (error.response?.status === 400) {
        // 400 = cycle dans les dépendances
        setCriticalPathData({ ordered_tasks: [], critical_tasks: [], total_duration: 0, projected_end_date: null, has_cycle: true });
      } else {
        console.error('Error loading critical path:', error);
      }
    }
  };

  const criticalPathMap = useMemo(() => {
    if (!criticalPathData) return new Map<number, CriticalPathTaskData>();
    return new Map(criticalPathData.ordered_tasks.map((t) => [t.task_id, t]));
  }, [criticalPathData]);

  /** Ordre d'exécution conseillé : le backend renvoie un tri topologique */
  const taskOrder = useMemo(() => {
    if (!criticalPathData || criticalPathData.has_cycle) return undefined;
    return new Map(criticalPathData.ordered_tasks.map((t, index) => [t.task_id, index]));
  }, [criticalPathData]);

  const reloadPlanning = async (projectId: number) => {
    await Promise.all([loadTasks(projectId), loadCriticalPath(projectId), fetchProjectStats(projectId)]);
  };

  /** Étirement d'une barre du Gantt → nouvelle estimation (secondes) */
  const handleResizeTask = async (taskId: number, seconds: number) => {
    try {
      await tasksService.updateTask(taskId, { estimated_duration: Math.round(seconds) });
      toast.success(`Estimation mise à jour : ${Math.max(1, Math.round(seconds / 3600))} h`);
      if (id) await reloadPlanning(parseInt(id));
    } catch {
      // Erreur déjà toastée par l'intercepteur API
    }
  };

  /** Glisser une barre sur une autre → `taskId` dépend de `dependsOnId` */
  const handleLinkTasks = async (taskId: number, dependsOnId: number) => {
    const target = tasks.find((t) => t.id === taskId);
    const source = tasks.find((t) => t.id === dependsOnId);
    const current = target?.dependencies ?? [];
    if (current.includes(dependsOnId)) {
      toast('Cette dépendance existe déjà', { icon: 'ℹ️' });
      return;
    }
    try {
      await tasksService.updateTask(taskId, { dependency_ids: [...current, dependsOnId] });
      toast.success(`« ${target?.title ?? 'Tâche'} » dépend maintenant de « ${source?.title ?? 'tâche'} »`);
      if (id) await reloadPlanning(parseInt(id));
    } catch {
      // 400 si cycle : déjà toasté par l'intercepteur
    }
  };

  const handleDelete = async () => {
    if (!currentProject) return;
    setDeleting(true);
    try {
      await deleteProject(currentProject.id);
      toast.success('Projet archivé');
      navigate('/projects');
    } catch {
      // Erreur déjà toastée par l'intercepteur API
    } finally {
      setDeleting(false);
      setConfirmDelete(false);
    }
  };

  // Uniquement au tout premier chargement : sur un rafraîchissement (Gantt étiré,
  // dépendance créée…) remplacer la page par un loader démonte le contenu et
  // renvoie le navigateur en haut de page.
  if (loading && !currentProject) {
    return (
      <PageShell>
        <div className="flex items-center justify-center py-12"><Loader size="lg" /></div>
      </PageShell>
    );
  }

  if (!currentProject) {
    return (
      <PageShell>
        <div className="text-center py-12">
          <p className="text-ink-faint">Projet non trouvé</p>
          <Link to="/projects" className="mt-4 inline-block text-accent hover:underline">Retour aux projets</Link>
        </div>
      </PageShell>
    );
  }

  const project = currentProject;
  const inIdeation = project.status === ProjectStatus.IDEATION;

  const changerEtat = async (statut: ProjectStatus, reprise?: string | null) => {
    try {
      await updateProject(project.id, { status: statut, resume_on: statut === ProjectStatus.PAUSED ? reprise ?? null : null });
      toast.success(
        statut === ProjectStatus.PAUSED
          ? reprise ? 'Projet en pause jusqu\'à la date choisie' : 'Projet en pause'
          : statut === ProjectStatus.DORMANT ? 'Projet mis en sommeil' : 'Projet réactivé',
      );
    } catch {
      // l'intercepteur affiche déjà l'erreur
    }
  };
  const tasksActives = tasks.filter((t) => t.status !== TaskStatus.CANCELLED).length;

  return (
    <PageShell>
      {/* Fil d'Ariane */}
      <nav className="flex items-center gap-2 text-sm text-ink-soft mb-6">
        <Link to="/dashboard" className="hover:text-accent"><Home className="w-4 h-4" /></Link>
        <ChevronRight className="w-4 h-4" />
        <Link to="/projects" className="hover:text-accent">Projets</Link>
        <ChevronRight className="w-4 h-4" />
        <span className="text-ink font-medium">{project.name}</span>
      </nav>

      <ProjectHeader
        project={project}
        tasks={tasks}
        onDiscuss={() => choisirOnglet('discussion')}
        onAnalyze={() => navigate(`/projects/${id}/analyze`)}
        onEdit={() => navigate(`/projects/${id}/edit`)}
        onMoodboard={() => navigate(`/projects/${id}/moodboard`)}
        onDelete={() => setConfirmDelete(true)}
        onFileWritten={() => fetchProject(project.id)}
        onChangeState={changerEtat}
      />

      {inIdeation ? (
        <div className="mb-6">
          <IdeationChat projectId={project.id} onComplete={() => fetchProject(project.id)} />
        </div>
      ) : (
        <>
          {/* Onglets : la page empilait neuf blocs, les tâches tout en bas */}
          <div className="flex flex-wrap gap-x-1 border-b border-ink-line mb-6" role="tablist">
            {ONGLETS.map(({ id: cle, libelle }) => {
              const actif = onglet === cle;
              const nombre = cle === 'taches' ? tasksActives : null;
              return (
                <button
                  key={cle}
                  role="tab"
                  aria-selected={actif}
                  onClick={() => choisirOnglet(cle)}
                  className={`px-4 py-2.5 -mb-px text-sm font-medium border-b-2 transition-colors ${
                    actif ? 'border-accent text-ink' : 'border-transparent text-ink-soft hover:text-ink hover:border-ink-line'
                  }`}
                >
                  {libelle}
                  {nombre !== null && <span className="ml-1.5 text-xs text-ink-faint figures">{nombre}</span>}
                </button>
              );
            })}
          </div>

          {onglet === 'taches' && (
            <>
              {!tasksLoading && tasksActives === 0 && (
                <div className="bg-paper-card border border-accent p-6 mb-6 flex flex-wrap items-center justify-between gap-4">
                  <div className="min-w-0">
                    <p className="font-display text-lg text-ink">Pas encore de tâches</p>
                    <p className="text-sm text-ink-soft mt-1 max-w-xl">
                      Le plus simple : en discuter avec l'IA. Elle connaît la description du projet,
                      te pose des questions, puis te propose des tâches que tu choisis.
                    </p>
                  </div>
                  <button
                    onClick={() => choisirOnglet('discussion')}
                    className="shrink-0 inline-flex items-center gap-2 px-4 py-2 bg-accent text-white hover:opacity-90 text-sm font-medium"
                  >
                    <MessagesSquare className="w-4 h-4" />
                    Discuter avec l'IA
                  </button>
                </div>
              )}
              <ProjectTasksBoard projectId={project.id} tasks={tasks} loading={tasksLoading} criticalPathMap={criticalPathMap} taskOrder={taskOrder} />
            </>
          )}

          {onglet === 'discussion' && (
            <ProjectDiscussion
              key={project.id}
              projectId={project.id}
              sansTaches={tasksActives === 0}
              ouverteDemblee
            />
          )}

          {onglet === 'production' && <ProjectOutputs projectId={project.id} afficherSiVide />}

          {onglet === 'documents' && <ProjectDocuments projectId={project.id} />}

          {onglet === 'suivi' && (
            <>
              <ProjectHealthDashboard
                project={project}
                stats={currentProjectStats}
                criticalPath={criticalPathData}
                onResizeTask={handleResizeTask}
                onLinkTasks={handleLinkTasks}
              />
              <ProjectFinancialPanel project={project} />
              <ProjectFeaturesPanel project={project} />
            </>
          )}
        </>
      )}

      <ConfirmDialog
        open={confirmDelete}
        title="Archiver ce projet ?"
        message={`« ${project.name} » sera archivé ; ses tâches seront annulées.`}
        confirmLabel="Archiver"
        loading={deleting}
        onCancel={() => setConfirmDelete(false)}
        onConfirm={handleDelete}
      />
    </PageShell>
  );
};
