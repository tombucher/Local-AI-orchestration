/**
 * Page Liste des Tâches
 * - Affiche toutes les tâches avec filtres
 * - Grid responsive
 * - Filtres par projet, status, priorité
 */

import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Plus, Filter, Search } from 'lucide-react';
import { useTasksStore } from '../../stores/tasksStore';
import { useProjectsStore } from '../../stores/projectsStore';
import { Navbar } from '../../components/Layout/Navbar';
import { Sidebar } from '../../components/Layout/Sidebar';
import { TaskCard } from '../../components/tasks/TaskCard';
import { EmptyState } from '../../components/EmptyState';
import { TaskStatus, TaskPriority } from '../../types/task.types';
import Loader from '../../components/ui/Loader';

const statusOptions = [
  { value: '', label: 'Tous les statuts' },
  { value: TaskStatus.CREATED, label: 'Créée' },
  { value: TaskStatus.READY, label: 'Prête' },
  { value: TaskStatus.GENERATING, label: 'Génération' },
  { value: TaskStatus.MANUAL_REVIEW, label: 'À valider' },
  { value: TaskStatus.COMPLETED, label: 'Terminée' },
  { value: TaskStatus.FAILED, label: 'Échec' },
  { value: TaskStatus.CANCELLED, label: 'Annulée' },
];

const priorityOptions = [
  { value: '', label: 'Toutes les priorités' },
  { value: TaskPriority.P1, label: 'P1 - Urgent' },
  { value: TaskPriority.P2, label: 'P2 - Important' },
  { value: TaskPriority.P3, label: 'P3 - Normal' },
];

export const TasksList = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { tasks, loading, fetchTasks } = useTasksStore();
  const { projects, fetchProjects } = useProjectsStore();

  const [searchQuery, setSearchQuery] = useState('');
  const [selectedProject, setSelectedProject] = useState<number | undefined>(
    searchParams.get('project_id') ? parseInt(searchParams.get('project_id')!) : undefined
  );
  const [selectedStatus, setSelectedStatus] = useState<TaskStatus | ''>('');
  const [selectedPriority, setSelectedPriority] = useState<TaskPriority | ''>('');

  useEffect(() => {
    fetchProjects();
  }, [fetchProjects]);

  useEffect(() => {
    const filters: any = {};
    if (selectedProject) filters.project_id = selectedProject;
    if (selectedStatus) filters.status = selectedStatus;
    if (selectedPriority) filters.priority = selectedPriority;

    fetchTasks(filters);
  }, [selectedProject, selectedStatus, selectedPriority, fetchTasks]);

  // Filtrer les tâches par recherche texte côté client
  const tasksArray = Array.isArray(tasks) ? tasks : [];

  // Filtrer les tâches annulées si l'utilisateur n'a pas explicitement filtré sur CANCELLED
  const activeTasks = selectedStatus === TaskStatus.CANCELLED
    ? tasksArray
    : tasksArray.filter(task => task.status !== TaskStatus.CANCELLED);

  const filteredTasks = activeTasks.filter((task) => {
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    return (
      task.title.toLowerCase().includes(query) ||
      task.description?.toLowerCase().includes(query)
    );
  });

  const handleCreateTask = () => {
    if (selectedProject) {
      navigate(`/tasks/new?project_id=${selectedProject}`);
    } else {
      navigate('/tasks/new');
    }
  };

  return (
    <div className="min-h-screen bg-paper">
      <Navbar />

      <div className="flex">
        <Sidebar />

        <main className="flex-1 p-6 lg:p-8">
          {/* Header */}
          <div className="mb-8">
            <h1 className="text-3xl font-bold text-ink">Tâches</h1>
            <p className="mt-2 text-ink-soft">Gérez vos tâches et suivez leur progression</p>
          </div>

          {/* Filtres */}
          <div className="bg-paper-card rounded-none shadow-card border border-ink-line p-4 mb-6">
            <div className="flex items-center gap-2 mb-4">
              <Filter className="w-5 h-5 text-ink-soft" />
              <h2 className="font-semibold text-ink">Filtres</h2>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {/* Recherche */}
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-ink-faint" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Rechercher..."
                  className="w-full pl-10 pr-3 py-2 border border-ink-line rounded-none focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
                />
              </div>

              {/* Filtre projet */}
              <select
                value={selectedProject || ''}
                onChange={(e) =>
                  setSelectedProject(e.target.value ? parseInt(e.target.value) : undefined)
                }
                className="px-3 py-2 border border-ink-line rounded-none focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
              >
                <option value="">Tous les projets</option>
                {projects.map((project) => (
                  <option key={project.id} value={project.id}>
                    {project.name}
                  </option>
                ))}
              </select>

              {/* Filtre status */}
              <select
                value={selectedStatus}
                onChange={(e) => setSelectedStatus(e.target.value as TaskStatus | '')}
                className="px-3 py-2 border border-ink-line rounded-none focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
              >
                {statusOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>

              {/* Filtre priorité */}
              <select
                value={selectedPriority}
                onChange={(e) => setSelectedPriority(e.target.value as TaskPriority | '')}
                className="px-3 py-2 border border-ink-line rounded-none focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
              >
                {priorityOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Bouton Nouvelle tâche */}
          <div className="mb-6">
            <button
              onClick={handleCreateTask}
              className="flex items-center gap-2 px-4 py-2 bg-primary text-white rounded-none hover:bg-primary/90 transition-colors font-medium"
            >
              <Plus className="w-4 h-4" />
              Nouvelle tâche
            </button>
          </div>

          {/* Liste des tâches */}
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader size="lg" />
            </div>
          ) : filteredTasks.length > 0 ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
              {filteredTasks.map((task) => (
                <TaskCard
                  key={task.id}
                  task={task}
                  onClick={(id) => navigate(`/tasks/${id}`)}
                />
              ))}
            </div>
          ) : (
            <EmptyState
              icon={Filter}
              message={
                searchQuery || selectedProject || selectedStatus || selectedPriority
                  ? 'Aucune tâche ne correspond à vos filtres'
                  : 'Aucune tâche pour le moment'
              }
              action={
                searchQuery || selectedProject || selectedStatus || selectedPriority
                  ? undefined
                  : {
                      label: 'Créer votre première tâche',
                      onClick: handleCreateTask,
                    }
              }
            />
          )}
        </main>
      </div>
    </div>
  );
};
