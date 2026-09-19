/**
 * Page Détail d'un projet — composition :
 * - ProjectHeader (titre, type, actions)
 * - IdeationChat en phase d'idéation
 * - ProjectFeaturesPanel / ProjectFinancialPanel
 * - ProjectHealthDashboard (maturité, stats, chemin critique, Gantt)
 * - ProjectTasksBoard (liste des tâches)
 */

import { useEffect, useMemo, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { ChevronRight, Home } from 'lucide-react';
import toast from 'react-hot-toast';
import { useProjectsStore } from '../../stores/projectsStore';
import { Navbar } from '../../components/Layout/Navbar';
import { Sidebar } from '../../components/Layout/Sidebar';
import { IdeationChat } from '../../components/IdeationChat';
import { ProjectHeader } from '../../components/projects/ProjectHeader';
import { ProjectFeaturesPanel, ProjectFinancialPanel } from '../../components/projects/ProjectInfoPanels';
import { ProjectHealthDashboard } from '../../components/projects/ProjectHealthDashboard';
import { ProjectTasksBoard } from '../../components/projects/ProjectTasksBoard';
import ConfirmDialog from '../../components/ui/ConfirmDialog';
import Loader from '../../components/ui/Loader';
import { tasksService } from '../../services/tasks';
import api from '../../services/api';
import { ProjectStatus } from '../../types/project.types';
import type { Task } from '../../types/task.types';
import type { CriticalPathData, CriticalPathTaskData } from '../../types/critical-path.types';

const PageShell = ({ children }: { children: React.ReactNode }) => (
  <div className="min-h-screen bg-paper">
    <Navbar />
    <div className="flex">
      <Sidebar />
      <main className="flex-1 p-6 lg:p-8">{children}</main>
    </div>
  </div>
);

export const ProjectDetail = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { currentProject, currentProjectStats, loading, fetchProject, fetchProjectStats, deleteProject } = useProjectsStore();
  const [tasks, setTasks] = useState<Task[]>([]);
  const [tasksLoading, setTasksLoading] = useState(false);
  const [criticalPathData, setCriticalPathData] = useState<CriticalPathData | null>(null);
  const [confirmDelete, setConfirmDelete] = useState(false);
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

  if (loading) {
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
        onAnalyze={() => navigate(`/projects/${id}/analyze`)}
        onEdit={() => navigate(`/projects/${id}/edit`)}
        onMoodboard={() => navigate(`/projects/${id}/moodboard`)}
        onDelete={() => setConfirmDelete(true)}
      />

      {inIdeation ? (
        <div className="mb-6">
          <IdeationChat projectId={project.id} onComplete={() => fetchProject(project.id)} />
        </div>
      ) : (
        <>
          <ProjectFeaturesPanel project={project} />
          <ProjectHealthDashboard
            project={project}
            stats={currentProjectStats}
            criticalPath={criticalPathData}
            onResizeTask={handleResizeTask}
            onLinkTasks={handleLinkTasks}
          />
          <ProjectFinancialPanel project={project} />
          <ProjectTasksBoard projectId={project.id} tasks={tasks} loading={tasksLoading} criticalPathMap={criticalPathMap} />
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
