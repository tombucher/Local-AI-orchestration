/**
 * Page Liste des projets
 * - Grid de cartes
 * - Filtres par type
 * - Recherche
 * - Bouton créer projet
 */

import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { FolderDown, Plus, Search, FolderKanban } from 'lucide-react';
import toast from 'react-hot-toast';
import { projectFoldersApi } from '../../services/projectFoldersApi';
import { useProjectsStore } from '../../stores/projectsStore';
import { Navbar } from '../../components/Layout/Navbar';
import { Sidebar } from '../../components/Layout/Sidebar';
import { ProjectCard } from '../../components/ProjectCard';
import { EmptyState } from '../../components/EmptyState';
import { ProjectStatus, ProjectType } from '../../types/project.types';
import Loader from '../../components/ui/Loader';
import MarkdownImport from '../../components/projects/MarkdownImport';

const projectTypes: { value: ProjectType | 'all'; label: string }[] = [
  { value: 'all', label: 'Tous' },
  { value: ProjectType.PROFESSIONAL, label: 'Professionnel' },
  { value: ProjectType.PERSONAL, label: 'Personnel' },
  { value: ProjectType.RESEARCH, label: 'Recherche' },
];

export const ProjectsList = () => {
  const navigate = useNavigate();
  const { projects, loading, fetchProjects } = useProjectsStore();

  const [selectedType, setSelectedType] = useState<ProjectType | 'all'>('all');
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    const filters: any = {};
    if (selectedType !== 'all') filters.type = selectedType;
    if (searchQuery) filters.search = searchQuery;

    fetchProjects(filters);
  }, [selectedType, searchQuery, fetchProjects]);

  const [ecriture, setEcriture] = useState(false);
  const sansFiche = (Array.isArray(projects) ? projects : []).filter(
    (p) => !p.source_path && p.status !== ProjectStatus.ARCHIVED,
  ).length;

  // Dossier + fiche .md pour chaque projet de l'outil qui n'en a pas encore
  const ecrireToutesLesFiches = async () => {
    setEcriture(true);
    try {
      const { written } = await projectFoldersApi.writeAll();
      toast.success(
        written.length
          ? `${written.length} fiche(s) écrite(s) dans ton dossier de projets`
          : 'Tous tes projets ont déjà leur fiche',
      );
      fetchProjects();
    } catch {
      // l'intercepteur affiche l'erreur (ex. : aucun dossier de projets choisi)
    } finally {
      setEcriture(false);
    }
  };

  const handleCreateProject = () => {
    navigate('/projects/new');
  };

  const handleViewProject = (id: number) => {
    navigate(`/projects/${id}`);
  };

  return (
    <div className="min-h-screen bg-paper">
      <Navbar />

      <div className="flex">
        <Sidebar />

        <main className="flex-1 p-6 lg:p-8">
          {/* Header */}
          <div className="mb-8">
            <div className="flex flex-wrap items-center justify-between gap-4 mb-6">
              <div>
                <h1 className="text-3xl font-bold text-ink">Projets</h1>
                <p className="mt-2 text-ink-soft">Gérez vos projets et suivez leur progression</p>
              </div>
              <div className="flex flex-wrap gap-2 justify-end">
                {sansFiche > 0 && (
                  <button
                    onClick={ecrireToutesLesFiches}
                    disabled={ecriture}
                    title="Crée un dossier et une fiche .md, dans ton dossier de projets, pour chaque projet qui n'en a pas"
                    className="flex items-center gap-2 px-4 py-2 border border-ink-line text-ink hover:border-accent hover:text-accent disabled:opacity-40 transition-colors font-medium"
                  >
                    <FolderDown className="w-5 h-5" />
                    {ecriture ? 'Écriture…' : `Écrire les fiches (${sansFiche})`}
                  </button>
                )}
                <MarkdownImport />
                <button
                  onClick={handleCreateProject}
                  className="flex items-center gap-2 px-4 py-2 bg-primary text-white rounded-none hover:bg-primary/90 transition-colors font-medium"
                >
                  <Plus className="w-5 h-5" />
                  Nouveau projet
                </button>
              </div>
            </div>

            {/* Filtres */}
            <div className="flex flex-col sm:flex-row gap-4">
              {/* Recherche */}
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-ink-faint" />
                <input
                  type="text"
                  placeholder="Rechercher un projet..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 border border-ink-line rounded-none focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
                />
              </div>

              {/* Filtres type */}
              <div className="flex gap-2">
                {projectTypes.map((type) => (
                  <button
                    key={type.value}
                    onClick={() => setSelectedType(type.value)}
                    className={`px-4 py-2 rounded-none font-medium text-sm transition-colors ${
                      selectedType === type.value
                        ? 'bg-primary text-white'
                        : 'bg-paper-card text-ink-soft hover:bg-paper-warm border border-ink-line'
                    }`}
                  >
                    {type.label}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Loading State */}
          {loading && (
            <div className="flex items-center justify-center py-12">
              <Loader size="lg" />
            </div>
          )}

          {/* Empty State */}
          {!loading && projects.length === 0 && (
            <EmptyState
              icon={FolderKanban}
              title={searchQuery ? 'Aucun projet trouvé' : 'Aucun projet'}
              description={
                searchQuery
                  ? 'Essayez de modifier vos critères de recherche'
                  : 'Créez votre premier projet pour commencer'
              }
              action={
                !searchQuery
                  ? {
                      label: 'Créer un projet',
                      onClick: handleCreateProject,
                    }
                  : undefined
              }
            />
          )}

          {/* Projects Grid */}
          {!loading && projects.length > 0 && (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
              {projects.map((project) => (
                <ProjectCard key={project.id} project={project} onView={handleViewProject} />
              ))}
            </div>
          )}
        </main>
      </div>
    </div>
  );
};
